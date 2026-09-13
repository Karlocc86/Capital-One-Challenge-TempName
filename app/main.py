from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent import CognitiveFinancialAgent
from app.cache import (
    get_account,
    get_bills,
    get_cached_rescue_plan,
    get_purchases,
    save_rescue_plan,
)
from app.forecaster import FinancialForecaster
from app.nessie_client import (
    NessieError,
    get_accounts_for_customer,
    get_loans_for_account,
    get_purchases_for_account,
)

app = FastAPI(title="Fin de Mes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"data": {"status": "ok"}, "meta": {}}


@app.get("/summary/{account_id}")
def summary(account_id: str):
    try:
        account = get_account(account_id)
        purchases = get_purchases(account_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener el account {account_id} de Nessie: {e.body}",
        )

    total_spent = sum(purchase["amount"] for purchase in purchases)

    return {
        "data": {
            "account_id": account["_id"],
            "nickname": account["nickname"],
            "balance": account["balance"],
            "total_spent": round(total_spent, 2),
            "purchase_count": len(purchases),
        },
        "meta": {},
    }


# Nessie no tiene endpoint "accounts por tipo" directo, así que filtramos
# sobre todas las accounts del customer. Usado por las 4 pantallas nuevas
# (ahorros, tarjetas, préstamos, recompensas). Pega directo a Nessie (no pasa
# por cache.py) porque el cache solo cubre snapshots por account, no listados
# por customer ni loans todavía.
def _accounts_by_type(customer_id: str, account_type: str) -> list[dict]:
    try:
        accounts = get_accounts_for_customer(customer_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener accounts del customer {customer_id} de Nessie: {e.body}",
        )
    return [a for a in accounts if a.get("type") == account_type]


@app.get("/savings/{customer_id}")
def savings(customer_id: str):
    accounts = _accounts_by_type(customer_id, "Savings")
    return {"data": accounts, "meta": {}}


@app.get("/credit-cards/{customer_id}")
def credit_cards(customer_id: str):
    accounts = _accounts_by_type(customer_id, "Credit Card")

    cards = []
    for account in accounts:
        try:
            purchases = get_purchases_for_account(account["_id"])
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener purchases de la account {account['_id']} de Nessie: {e.body}",
            )
        total_spent = sum(purchase["amount"] for purchase in purchases)
        cards.append({**account, "total_spent": round(total_spent, 2), "purchase_count": len(purchases)})

    return {"data": cards, "meta": {}}


@app.get("/loans/{customer_id}")
def loans(customer_id: str):
    try:
        accounts = get_accounts_for_customer(customer_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener accounts del customer {customer_id} de Nessie: {e.body}",
        )

    all_loans = []
    for account in accounts:
        try:
            all_loans.extend(get_loans_for_account(account["_id"]))
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener loans de la account {account['_id']} de Nessie: {e.body}",
            )

    return {"data": all_loans, "meta": {}}


@app.get("/rewards/{customer_id}")
def rewards(customer_id: str):
    try:
        accounts = get_accounts_for_customer(customer_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener accounts del customer {customer_id} de Nessie: {e.body}",
        )

    return {
        "data": [
            {"account_id": a["_id"], "nickname": a["nickname"], "rewards": a["rewards"]}
            for a in accounts
        ],
        "meta": {},
    }


# Cache en memoria del proceso (no Postgres) — se pierde al reiniciar el
# servidor, pero evita llamar a Gemini de nuevo en cada cambio de página
# durante la demo. No requiere tocar el esquema de Supabase.
_insights_memory_cache: dict[str, dict] = {}


@app.get("/insights/{customer_id}")
async def insights(customer_id: str, force_refresh: bool = False):
    """Una conclusión corta por widget del dashboard, para el avatar canica.
    Agrega datos de todas las accounts del customer en un solo call a Gemini."""
    try:
        accounts = get_accounts_for_customer(customer_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener accounts del customer {customer_id} de Nessie: {e.body}",
        )

    checking_account = next((a for a in accounts if a.get("type") == "Checking"), None)
    savings_accounts = [a for a in accounts if a.get("type") == "Savings"]
    credit_accounts = [a for a in accounts if a.get("type") == "Credit Card"]

    checking_balance = 0.0
    total_spent = 0.0
    purchase_count = 0
    if checking_account:
        try:
            account = get_account(checking_account["_id"])
            purchases = get_purchases(checking_account["_id"])
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener la account checking de Nessie: {e.body}",
            )
        checking_balance = account["balance"]
        total_spent = sum(p["amount"] for p in purchases)
        purchase_count = len(purchases)

    all_loans = []
    for a in accounts:
        try:
            all_loans.extend(get_loans_for_account(a["_id"]))
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener loans de la account {a['_id']} de Nessie: {e.body}",
            )

    summary = {
        "checking_balance": checking_balance,
        "total_spent": round(total_spent, 2),
        "purchase_count": purchase_count,
        "savings_total": sum(a.get("balance", 0) for a in savings_accounts),
        "credit_total": sum(a.get("balance", 0) for a in credit_accounts),
        "loan_count": len(all_loans),
        "rewards_total": sum(a.get("rewards", 0) for a in accounts),
    }

    insights_data = None if force_refresh else _insights_memory_cache.get(customer_id)
    if insights_data:
        print("[insights] usando insights cacheados en memoria (sin llamar a Gemini)")
    else:
        agent = CognitiveFinancialAgent()
        section_insights, success = await agent.generate_section_insights(summary)
        insights_data = section_insights.model_dump(mode="json")
        if success:
            _insights_memory_cache[customer_id] = insights_data

    return {"data": insights_data, "meta": {}}


@app.get("/forecast/{account_id}")
async def forecast(account_id: str, force_refresh: bool = False):
    try:
        print(f"[forecast] ingesta: leyendo cache para account {account_id}")
        account = get_account(account_id)
        purchases = get_purchases(account_id)
        bills = get_bills(account_id)
    except NessieError as e:
        print(f"[forecast] ingesta falló: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener el account {account_id} de Nessie: {e.body}",
        )

    try:
        print("[forecast] capa cuantitativa: calculando forecast")
        forecast_result = FinancialForecaster(
            account["balance"], purchases, bills
        ).calculate_forecast()

        rescue_plan_data = None if force_refresh else get_cached_rescue_plan(account_id)
        if rescue_plan_data:
            print("[forecast] usando rescue_plan cacheado (sin llamar a Gemini)")
        else:
            print("[forecast] capa cognitiva: generando plan de rescate")
            agent = CognitiveFinancialAgent()
            rescue_plan, success = await agent.generate_rescue_plan(forecast_result, purchases)
            rescue_plan_data = rescue_plan.model_dump(mode="json")
            if success:
                save_rescue_plan(account_id, rescue_plan_data)
    except Exception as e:
        print(f"[forecast] ERROR inesperado ({type(e).__name__}): {e}")
        raise HTTPException(status_code=500, detail="Error interno generando el forecast.")

    print("[forecast] listo")
    return {
        "data": {
            "account_id": account["_id"],
            "forecast": forecast_result.model_dump(mode="json"),
            "rescue_plan": rescue_plan_data,
        },
        "meta": {},
    }
