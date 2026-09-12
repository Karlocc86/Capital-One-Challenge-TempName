import calendar
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.agent import CognitiveFinancialAgent
from app.cache import (
    get_account,
    get_accounts_for_customer,
    get_bills,
    get_cached_rescue_plan,
    get_deposits,
    get_purchases,
    save_rescue_plan,
)
from app.demo_data import DEMO_EMPLOYER, DEMO_MONTHLY_INCOME
from app.forecaster import FinancialForecaster
from app.nessie_client import (
    NessieError,
    get_accounts_for_customer,
    get_loans_for_account,
    get_purchases_for_account,
)

CURRENCY = "MXN"
SUMMARY_WINDOW_DAYS = 30

# Etiqueta de UI para las bills, por nickname. Las purchases traen la suya del
# merchant; las bills en Nessie no tienen categoría.
BILL_CATEGORIES = {
    "Renta": "Vivienda",
    "Servicios": "Servicios y facturas",
    "Préstamo": "Deuda",
}

app = FastAPI(title="Fin de Mes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _mask(account_number: str | None) -> str | None:
    return f"•••• {str(account_number)[-4:]}" if account_number else None


def _load_account(account_id: str) -> dict:
    try:
        return get_account(account_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener el account {account_id} de Nessie: {e.body}",
        )


def _next_payment_date(recurring_date: int, today: date) -> date:
    """Próxima fecha en que se cobra una bill que se paga el día `recurring_date` de cada mes."""
    year, month = today.year, today.month
    if recurring_date < today.day:
        month += 1
        if month > 12:
            year, month = year + 1, 1
    day = min(recurring_date, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@app.get("/health")
def health():
    return {"data": {"status": "ok"}, "meta": {}}


@app.get("/summary/{account_id}")
def summary(account_id: str):
    """
    Saldo + ingresos/egresos de los últimos 30 días (ventana móvil, no mes
    calendario: el seed usa fechas relativas a hoy, y con mes calendario el
    día 1 los egresos serían ~0).
    """
    account = _load_account(account_id)
    purchases = get_purchases(account_id)
    deposits = get_deposits(account_id)
    bills = get_bills(account_id)

    today = date.today()
    window_start = today - timedelta(days=SUMMARY_WINDOW_DAYS)
    in_window = lambda d: date.fromisoformat(d) >= window_start  # noqa: E731

    total_spent = sum(p["amount"] for p in purchases)
    money_out = sum(p["amount"] for p in purchases if in_window(p["purchase_date"]))
    money_in = sum(d["amount"] for d in deposits if in_window(d["transaction_date"]))
    bills_monthly_total = sum(b["payment_amount"] for b in bills if b["status"] == "recurring")

    return {
        "data": {
            "account_id": account["_id"],
            "nickname": account["nickname"],
            "balance": account["balance"],
            "account_number_masked": _mask(account["account_number"]),
            "total_spent": round(total_spent, 2),
            "purchase_count": len(purchases),
            "money_in": round(money_in, 2),
            "money_out": round(money_out, 2),
            "deposit_count": len(deposits),
            "money_in_goal": DEMO_MONTHLY_INCOME,
            "bills_monthly_total": round(bills_monthly_total, 2),
        },
        "meta": {
            "currency": CURRENCY,
            "period": {
                "from": window_start.isoformat(),
                "to": today.isoformat(),
                "days": SUMMARY_WINDOW_DAYS,
            },
        },
    }


@app.get("/accounts/{account_id}")
def accounts(account_id: str):
    """Todas las cuentas del customer dueño de `account_id` (sidebar: Cheques, Ahorro...)."""
    account = _load_account(account_id)
    siblings = get_accounts_for_customer(account["customer_id"])

    data = [
        {
            "account_id": a["_id"],
            "nickname": a["nickname"],
            "type": a["type"],
            "balance": a["balance"],
            "account_number_masked": _mask(a["account_number"]),
            "is_current": a["_id"] == account_id,
        }
        for a in siblings
    ]
    # La cuenta actual primero, luego el resto en el orden del cache.
    data.sort(key=lambda a: not a["is_current"])

    return {
        "data": {"customer_id": account["customer_id"], "accounts": data},
        "meta": {"currency": CURRENCY, "count": len(data)},
    }


@app.get("/transactions/{account_id}")
def transactions(
    account_id: str,
    limit: int = Query(20, ge=1, le=100),
    type: str = Query("all", pattern="^(all|purchase|deposit)$"),
):
    """Purchases y deposits mezclados, del más reciente al más antiguo. Montos positivos + `direction`."""
    _load_account(account_id)

    items: list[dict] = []
    if type in ("all", "purchase"):
        for p in get_purchases(account_id):
            items.append(
                {
                    "id": p["_id"],
                    "type": "purchase",
                    "direction": "out",
                    "amount": p["amount"],
                    "date": p["purchase_date"],
                    "merchant": p["merchant_name"] or p["description"] or "Compra",
                    "category": p["category"] or "Otros",
                    "description": p["description"],
                    "status": p["status"],
                }
            )
    if type in ("all", "deposit"):
        for d in get_deposits(account_id):
            items.append(
                {
                    "id": d["_id"],
                    "type": "deposit",
                    "direction": "in",
                    "amount": d["amount"],
                    "date": d["transaction_date"],
                    "merchant": f"Nómina - {DEMO_EMPLOYER}",
                    "category": "Ingresos",
                    "description": d["description"],
                    "status": d["status"],
                }
            )

    # Más reciente primero; en empate de fecha, los depósitos antes que las compras.
    items.sort(key=lambda t: (t["date"], t["type"] == "deposit"), reverse=True)

    return {
        "data": items[:limit],
        "meta": {
            "account_id": account_id,
            "count": min(limit, len(items)),
            "limit": limit,
            "total_available": len(items),
            "currency": CURRENCY,
        },
    }


@app.get("/bills/{account_id}")
def bills(account_id: str):
    """Bills recurrentes con su próxima fecha de cobro (próximas transacciones)."""
    _load_account(account_id)
    today = date.today()

    data = []
    for b in get_bills(account_id):
        next_date = _next_payment_date(b["recurring_date"], today)
        data.append(
            {
                "id": b["_id"],
                "payee": b["payee"],
                "nickname": b["nickname"],
                "amount": b["payment_amount"],
                "recurring_date": b["recurring_date"],
                "next_payment_date": next_date.isoformat(),
                "days_until": (next_date - today).days,
                "category": BILL_CATEGORIES.get(b["nickname"], "Servicios y facturas"),
                "status": b["status"],
                "direction": "out",
            }
        )
    data.sort(key=lambda b: b["next_payment_date"])

    return {
        "data": data,
        "meta": {
            "account_id": account_id,
            "count": len(data),
            "monthly_total": round(sum(b["amount"] for b in data if b["status"] == "recurring"), 2),
            "as_of": today.isoformat(),
            "currency": CURRENCY,
        },
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
