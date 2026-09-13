"""
Saldo disponible de una cuenta a partir de sus movimientos.

Nessie NO mueve `account.balance` cuando se crean deposits o purchases (es un
número fijo que se setea al crear la cuenta — verificado). Por eso aquí se
trata ese número como el *saldo inicial* (al arranque del historial) y el
saldo real se reconstruye:

    saldo = inicial + Σ depósitos − Σ compras − Σ bills ya cobradas

Una bill recurrente se cobra el día `recurring_date` de cada mes; se cuentan
las ocurrencias entre el primer movimiento del historial y hoy. Solo cálculo,
sin I/O — lo comparten main.py (saldo) y forecaster.py (proyección).
"""

import calendar
from datetime import date, timedelta


def _parse(d) -> date:
    return d if isinstance(d, date) else date.fromisoformat(str(d)[:10])


def bill_charges(bills: list[dict], start: date, end: date) -> list[tuple[date, dict]]:
    """Ocurrencias (fecha, bill) de las bills recurrentes entre start y end, inclusive."""
    charges: list[tuple[date, dict]] = []
    for bill in bills:
        if bill.get("status") != "recurring":
            continue
        day_of_month = int(bill.get("recurring_date") or 0)
        if day_of_month <= 0:
            continue
        year, month = start.year, start.month
        while (year, month) <= (end.year, end.month):
            day = min(day_of_month, calendar.monthrange(year, month)[1])
            when = date(year, month, day)
            if start <= when <= end:
                charges.append((when, bill))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    charges.sort(key=lambda c: c[0])
    return charges


def compute_balance(
    opening_balance: float,
    deposits: list[dict],
    purchases: list[dict],
    bills: list[dict] | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    bills = bills or []

    movement_dates = [_parse(d["transaction_date"]) for d in deposits] + [
        _parse(p["purchase_date"]) for p in purchases
    ]
    history_start = min(movement_dates) if movement_dates else today

    money_in = round(sum(float(d.get("amount", 0.0)) for d in deposits), 2)
    money_out = round(sum(float(p.get("amount", 0.0)) for p in purchases), 2)
    charged = bill_charges(bills, history_start, today)
    bills_charged = round(sum(float(b.get("payment_amount", 0.0)) for _, b in charged), 2)

    return {
        "opening_balance": round(float(opening_balance), 2),
        "history_start": history_start,
        "money_in": money_in,
        "money_out": money_out,
        "bills_charged": bills_charged,
        "balance": round(float(opening_balance) + money_in - money_out - bills_charged, 2),
    }


def infer_income_schedule(deposits: list[dict], today: date, horizon_days: int) -> list[tuple[date, float]]:
    """
    Próximos depósitos esperados a partir del historial: si hay ≥2 depósitos,
    el intervalo es la mediana de días entre ellos (15 = quincena) y el monto
    el promedio de los dos últimos. Con 1 depósito se asume quincena. Sin
    depósitos no se proyecta ingreso.
    """
    if not deposits:
        return []
    history = sorted((_parse(d["transaction_date"]), float(d.get("amount", 0.0))) for d in deposits)
    if len(history) >= 2:
        gaps = sorted((b[0] - a[0]).days for a, b in zip(history, history[1:]))
        interval = max(1, gaps[len(gaps) // 2])
        amount = (history[-1][1] + history[-2][1]) / 2
    else:
        interval, amount = 15, history[-1][1]

    schedule: list[tuple[date, float]] = []
    when = history[-1][0] + timedelta(days=interval)
    while when <= today:
        when += timedelta(days=interval)
    end = today + timedelta(days=horizon_days)
    while when <= end:
        schedule.append((when, round(amount, 2)))
        when += timedelta(days=interval)
    return schedule
