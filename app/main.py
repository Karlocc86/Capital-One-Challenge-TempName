from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent import CognitiveFinancialAgent
from app.cajitas import (
    create_cajita,
    get_active_total,
    get_cajita,
    get_cajitas_for_account,
    has_active_cajita_for_date,
    mark_released,
)
from app.categories import bill_category
from app.cache import (
    get_account,
    get_accounts_for_customer,
    get_bills,
    get_cached_rescue_plan,
    get_deposits,
    get_merchants,
    get_purchases,
    save_rescue_plan,
)
from app.demo_data import DEMO_DECORATIVE_CREDIT_CARD, DEMO_EMPLOYER, DEMO_MONTHLY_INCOME, DISCRETIONARY_BILLS
from app.essential_expenses import EssentialExpenseDetector
from app.forecaster import FinancialForecaster
from app.guide_agent import GuideAgent
from app.ledger import compute_balance, next_bill_date
from app.payday import PaydayDetector

# Las pantallas por tipo de cuenta (savings, credit-cards, loans, rewards)
# pegan a Nessie en vivo; se importan con alias para no pisar las funciones
# homónimas de cache.py que usa el resto de los endpoints.
from app.nessie_client import NessieError
from app.nessie_client import get_accounts_for_customer as nessie_get_accounts_for_customer
from app.nessie_client import get_loans_for_account as nessie_get_loans_for_account
from app.nessie_client import get_purchases_for_account as nessie_get_purchases_for_account

CURRENCY = "MXN"
SUMMARY_WINDOW_DAYS = 30

app = FastAPI(title="Fin de Mes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],  # POST: crear cajitas y pedir/confirmar retiros
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


@app.get("/health")
def health():
    return {"data": {"status": "ok"}, "meta": {}}


@app.get("/summary/{account_id}")
def summary(account_id: str):
    """
    Saldo disponible (saldo inicial + depósitos − compras, ver app/ledger.py)
    e ingresos/egresos de los últimos 30 días (ventana móvil, no mes
    calendario: el seed usa fechas relativas a hoy, y con mes calendario el
    día 1 los egresos serían ~0).
    """
    account = _load_account(account_id)
    purchases = get_purchases(account_id)
    deposits = get_deposits(account_id)
    bills = get_bills(account_id)
    ledger = compute_balance(account["balance"], deposits, purchases, bills)

    today = date.today()
    window_start = today - timedelta(days=SUMMARY_WINDOW_DAYS)
    in_window = lambda d: date.fromisoformat(d) >= window_start  # noqa: E731

    money_out = sum(p["amount"] for p in purchases if in_window(p["purchase_date"]))
    money_in = sum(d["amount"] for d in deposits if in_window(d["transaction_date"]))
    bills_monthly_total = sum(b["payment_amount"] for b in bills if b["status"] == "recurring")

    return {
        "data": {
            "account_id": account["_id"],
            "nickname": account["nickname"],
            "balance": ledger["balance"],
            "opening_balance": ledger["opening_balance"],
            "bills_charged": ledger["bills_charged"],
            "account_number_masked": _mask(account["account_number"]),
            "total_spent": ledger["money_out"],
            "total_deposited": ledger["money_in"],
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
    # Solo la cuenta actual tiene movimientos en cache; las demás (Ahorro)
    # muestran el balance tal cual lo reporta Nessie.
    current_balance = compute_balance(
        account["balance"], get_deposits(account_id), get_purchases(account_id), get_bills(account_id)
    )["balance"]

    data = [
        {
            "account_id": a["_id"],
            "nickname": a["nickname"],
            "type": a["type"],
            "balance": current_balance if a["_id"] == account_id else a["balance"],
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
        next_date = next_bill_date(b["recurring_date"], today)
        data.append(
            {
                "id": b["_id"],
                "payee": b["payee"],
                "nickname": b["nickname"],
                "amount": b["payment_amount"],
                "recurring_date": b["recurring_date"],
                "next_payment_date": next_date.isoformat(),
                "days_until": (next_date - today).days,
                "category": bill_category(b["nickname"], DISCRETIONARY_BILLS),
                "discretionary": b["nickname"] in DISCRETIONARY_BILLS,
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


@app.get("/merchants")
def merchants():
    """Todos los comercios en cache, con su categoría (la etiqueta que pinta la UI)."""
    data = [
        {
            "merchant_id": m["_id"],
            "name": m["name"],
            "category": m["category"],
            "address": m["address"],
        }
        for m in get_merchants()
    ]
    return {"data": data, "meta": {"count": len(data)}}


@app.get("/purchases/{account_id}")
def purchases(account_id: str):
    """
    Todas las compras de la cuenta (más reciente primero) con su comercio, más
    la lista de comercios que aparecen en ellas con el total gastado en cada
    uno. El dashboard usa las primeras N como "Transacciones recientes".
    """
    _load_account(account_id)
    rows = get_purchases(account_id)

    data = [
        {
            "id": p["_id"],
            "direction": "out",
            "amount": p["amount"],
            "date": p["purchase_date"],
            "merchant_id": p["merchant_id"],
            "merchant": p["merchant_name"] or p["description"] or "Compra",
            # Categoría de la compra (refinada: un refresco en OXXO es "Comida chatarra").
            "category": p["category"] or "Otros",
            "merchant_category": p["merchant_category"] or "Otros",
            "description": p["description"],
            "status": p["status"],
        }
        for p in rows
    ]

    by_merchant: dict[str, dict] = {}
    for p in data:
        entry = by_merchant.setdefault(
            p["merchant_id"] or p["merchant"],
            {
                "merchant_id": p["merchant_id"],
                "name": p["merchant"],
                "category": p["merchant_category"],
                "total_spent": 0.0,
                "purchase_count": 0,
            },
        )
        entry["total_spent"] = round(entry["total_spent"] + p["amount"], 2)
        entry["purchase_count"] += 1
    merchants_used = sorted(by_merchant.values(), key=lambda m: m["total_spent"], reverse=True)

    return {
        "data": {"purchases": data, "merchants": merchants_used},
        "meta": {
            "account_id": account_id,
            "purchase_count": len(data),
            "merchant_count": len(merchants_used),
            "total_spent": round(sum(p["amount"] for p in data), 2),
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
        accounts = nessie_get_accounts_for_customer(customer_id)
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
            purchases = nessie_get_purchases_for_account(account["_id"])
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener purchases de la account {account['_id']} de Nessie: {e.body}",
            )
        total_spent = sum(purchase["amount"] for purchase in purchases)
        cards.append({**account, "total_spent": round(total_spent, 2), "purchase_count": len(purchases), "decorative": False})

    # La decorativa siempre va al final (ver app/demo_data.py).
    cards.append(dict(DEMO_DECORATIVE_CREDIT_CARD))

    return {"data": cards, "meta": {"decorative_count": 1}}


@app.get("/loans/{customer_id}")
def loans(customer_id: str):
    try:
        accounts = nessie_get_accounts_for_customer(customer_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener accounts del customer {customer_id} de Nessie: {e.body}",
        )

    all_loans = []
    for account in accounts:
        try:
            all_loans.extend(nessie_get_loans_for_account(account["_id"]))
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener loans de la account {account['_id']} de Nessie: {e.body}",
            )

    return {"data": all_loans, "meta": {}}


@app.get("/rewards/{customer_id}")
def rewards(customer_id: str):
    try:
        accounts = nessie_get_accounts_for_customer(customer_id)
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
    spent_by_category: dict[str, float] = {}
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
        for p in purchases:
            cat = p.get("category") or "Otros"
            spent_by_category[cat] = round(spent_by_category.get(cat, 0.0) + p["amount"], 2)

    all_loans = []
    for a in accounts:
        try:
            all_loans.extend(nessie_get_loans_for_account(a["_id"]))
        except NessieError as e:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo obtener loans de la account {a['_id']} de Nessie: {e.body}",
            )

    summary = {
        "checking_balance": checking_balance,
        "total_spent": round(total_spent, 2),
        "purchase_count": purchase_count,
        # Ordenado de mayor a menor gasto — Gemini usa esto para el insight general.
        "spent_by_category": dict(sorted(spent_by_category.items(), key=lambda kv: -kv[1])),
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


# Saludo del Agente Guía: cache en memoria POR DÍA (el saludo depende de "¿la
# quincena es mañana?", que cambia a diario) — misma idea que _insights_memory_cache,
# pero con la fecha en la llave. Solo se guarda si Gemini respondió de verdad.
_welcome_memory_cache: dict[tuple[str, str], dict] = {}


@app.get("/guide/welcome/{account_id}")
async def guide_welcome(account_id: str, force_refresh: bool = False):
    """
    Primer mensaje al abrir la app. Orquesta: cache → detectores (gastos
    esenciales + quincena) + forecast cuantitativo → GuideAgent. Solo usa la
    capa cuantitativa (FinancialForecaster), NO el plan de rescate de
    /forecast: es otra llamada a Gemini y el saludo no la necesita.
    """
    account = _load_account(account_id)
    purchases = get_purchases(account_id)
    deposits = get_deposits(account_id)
    bills = get_bills(account_id)
    balance = compute_balance(account["balance"], deposits, purchases, bills)["balance"]
    today = date.today()

    forecast_result = FinancialForecaster(balance, purchases, bills, deposits, today).calculate_forecast()
    essentials = EssentialExpenseDetector().detect(bills, today)
    payday = PaydayDetector().detect(deposits, today)
    covered = {e.name for e in essentials if has_active_cajita_for_date(account_id, e.name, e.next_due_date)}

    cache_key = (account_id, today.isoformat())
    welcome_data = None if force_refresh else _welcome_memory_cache.get(cache_key)
    if welcome_data:
        print("[guide] usando saludo cacheado en memoria (sin llamar a Gemini)")
    else:
        agent = GuideAgent()
        welcome, success = await agent.generate_welcome(
            forecast_result, essentials, payday, covered, balance=balance, today=today
        )
        welcome_data = welcome.model_dump(mode="json")
        if success:
            _welcome_memory_cache[cache_key] = welcome_data

    return {
        "data": welcome_data,
        "meta": {
            "currency": CURRENCY,
            "as_of": today.isoformat(),
            "balance": balance,
            "payday": payday.model_dump(mode="json"),
            "essential_expenses": [e.model_dump(mode="json") for e in essentials],
            "covered_by_cajita": sorted(covered),
            "insolvency_date": forecast_result.insolvency_date.isoformat() if forecast_result.insolvency_date else None,
            "days_remaining": forecast_result.days_remaining,
        },
    }


# ----------------------------------------------------------------- Cajitas
# Registro propio en Postgres (app/cajitas.py); no mueve dinero en Nessie.


class CajitaCreateRequest(BaseModel):
    account_id: str
    name: str = Field(min_length=1)
    target_amount: float = Field(gt=0)
    linked_expense_name: str = Field(min_length=1)  # nickname de la bill ("Renta", "Servicios")
    reserve_date: date  # fecha en que se necesita el dinero de verdad


def _load_cajita(cajita_id: int):
    cajita = get_cajita(cajita_id)
    if cajita is None:
        raise HTTPException(status_code=404, detail=f"No existe la cajita {cajita_id}.")
    return cajita


@app.post("/cajitas")
def cajitas_create(body: CajitaCreateRequest):
    """
    Crea una Cajita (el usuario aceptó la propuesta del saludo). Idempotente:
    si ya hay una ACTIVA con el mismo `linked_expense_name` para la cuenta,
    regresa esa (meta.created = false) en vez de duplicarla.
    """
    _load_account(body.account_id)  # 404 si la cuenta no existe (y asegura el snapshot para la FK)
    cajita, created = create_cajita(
        body.account_id, body.name, body.target_amount, body.linked_expense_name, body.reserve_date
    )
    return {
        "data": cajita.model_dump(mode="json"),
        "meta": {"created": created, "currency": CURRENCY},
    }


@app.get("/cajitas/{account_id}")
def cajitas_list(account_id: str):
    """Cajitas de la cuenta (activas primero). meta.active_total es lo que hay que restar al saldo para el disponible."""
    _load_account(account_id)
    items = get_cajitas_for_account(account_id)
    return {
        "data": [c.model_dump(mode="json") for c in items],
        "meta": {
            "count": len(items),
            "active_total": get_active_total(account_id),
            "currency": CURRENCY,
        },
    }


@app.post("/cajitas/{cajita_id}/request-withdrawal")
async def cajitas_request_withdrawal(cajita_id: int):
    """
    Evalúa la solicitud de retiro. Si la fecha de uso ya llegó (hoy o antes),
    libera directo sin fricción. Si es antes de tiempo, NO libera: regresa la
    advertencia del Agente Guía para que el frontend la muestre y el usuario
    confirme (doble confirmación si `requires_double_confirmation`).
    """
    cajita = _load_cajita(cajita_id)
    if cajita.status != "active":
        raise HTTPException(status_code=409, detail=f"La cajita {cajita_id} ya está {cajita.status}.")

    today = date.today()
    days_early = (cajita.reserve_date - today).days

    if days_early <= 0:
        released = mark_released(cajita_id, was_early_withdrawal=False, days_early=0)
        return {
            "data": {"released": True, "warning": None, "cajita": released.model_dump(mode="json")},
            "meta": {"days_early": 0, "currency": CURRENCY},
        }

    agent = GuideAgent()
    warning, _success = await agent.generate_withdrawal_warning(cajita, days_early, today)
    return {
        "data": {"released": False, "warning": warning.model_dump(mode="json"), "cajita": cajita.model_dump(mode="json")},
        "meta": {"days_early": days_early, "currency": CURRENCY},
    }


@app.post("/cajitas/{cajita_id}/confirm-withdrawal")
def cajitas_confirm_withdrawal(cajita_id: int):
    """
    Libera el dinero: status → released y el monto vuelve a sumar al
    disponible. Se llama después de que el usuario vio la advertencia y
    confirmó. `days_early` se recalcula aquí (no se confía en el cliente)
    para la métrica de "cuántas veces ignoró la advertencia".
    """
    cajita = _load_cajita(cajita_id)
    if cajita.status != "active":
        raise HTTPException(status_code=409, detail=f"La cajita {cajita_id} ya está {cajita.status}.")

    days_early = max((cajita.reserve_date - date.today()).days, 0)
    released = mark_released(cajita_id, was_early_withdrawal=days_early > 0, days_early=days_early)
    return {
        "data": released.model_dump(mode="json"),
        "meta": {"days_early": days_early, "currency": CURRENCY},
    }


@app.get("/forecast/{account_id}")
async def forecast(account_id: str, force_refresh: bool = False):
    try:
        print(f"[forecast] ingesta: leyendo cache para account {account_id}")
        account = get_account(account_id)
        purchases = get_purchases(account_id)
        deposits = get_deposits(account_id)
        bills = get_bills(account_id)
        balance = compute_balance(account["balance"], deposits, purchases, bills)["balance"]
    except NessieError as e:
        print(f"[forecast] ingesta falló: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener el account {account_id} de Nessie: {e.body}",
        )

    try:
        print("[forecast] capa cuantitativa: calculando forecast")
        forecast_result = FinancialForecaster(balance, purchases, bills, deposits).calculate_forecast()

        rescue_plan_data = None if force_refresh else get_cached_rescue_plan(account_id)
        if rescue_plan_data:
            print("[forecast] usando rescue_plan cacheado (sin llamar a Gemini)")
        else:
            print("[forecast] capa cognitiva: generando plan de rescate")
            agent = CognitiveFinancialAgent()
            rescue_plan, success = await agent.generate_rescue_plan(forecast_result, purchases, bills, balance)
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
