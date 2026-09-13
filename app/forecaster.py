"""
Capa cuantitativa: proyecta el saldo futuro a partir de purchases, bills y
deposits ya cargados en memoria. Puro cómputo — no importa nessie_client,
cache, ni db.

Cómo proyecta (día a día, `HORIZON_DAYS` hacia adelante):
- Gasto variable: pendiente de una regresión lineal (sklearn) sobre el gasto
  acumulado de purchases → $/día constante.
- Bills: cargos puntuales el día `recurring_date` de cada mes (la renta pega
  de golpe el día 1, no prorrateada).
- Ingresos: próximas quincenas inferidas del historial de deposits
  (intervalo y monto), ver ledger.infer_income_schedule.
La insolvencia es el primer día en que el saldo proyectado queda en negativo.
"""

from datetime import date, timedelta

import pandas as pd
from sklearn.linear_model import LinearRegression

from app.ledger import bill_charges, infer_income_schedule
from app.schemas import ForecastMetrics, ProjectionPoint

DAYS_PER_MONTH = 30
HORIZON_DAYS = 90


class FinancialForecaster:
    def __init__(
        self,
        current_balance: float,
        purchases: list[dict],
        bills: list[dict],
        deposits: list[dict] | None = None,
        today: date | None = None,
    ):
        self.current_balance = current_balance
        self.purchases = purchases
        self.bills = bills
        self.deposits = deposits or []
        self.today = today or date.today()

    def _purchases_burn_rate(self) -> tuple[float, float | None]:
        if not self.purchases:
            return 0.0, None

        df = pd.DataFrame(self.purchases)
        df["purchase_date"] = pd.to_datetime(df["purchase_date"])
        daily_spend = df.groupby("purchase_date")["amount"].sum()

        if len(daily_spend) < 2:
            # Sin al menos 2 días distintos con compras no hay nada que
            # regresionar con sentido — sklearn no truena aquí a propósito.
            return 0.0, None

        full_range = pd.date_range(daily_spend.index.min(), self.today)
        daily_spend = daily_spend.reindex(full_range, fill_value=0)
        cumulative = daily_spend.cumsum()

        x = pd.Series(range(len(cumulative))).to_frame()
        y = cumulative.values

        model = LinearRegression().fit(x, y)
        burn_rate = float(model.coef_[0])
        confidence = float(model.score(x, y))

        return max(burn_rate, 0.0), confidence

    def _bills_daily_equivalent(self) -> float:
        recurring_total = sum(
            bill.get("payment_amount", 0.0)
            for bill in self.bills
            if bill.get("status") == "recurring"
        )
        return recurring_total / DAYS_PER_MONTH

    def calculate_forecast(self) -> ForecastMetrics:
        purchases_burn_rate, confidence = self._purchases_burn_rate()
        # Burn rate "promedio" (compras + bills prorrateadas): resumen de una
        # sola cifra para la UI y el prompt; la proyección real va por días.
        total_burn_rate = purchases_burn_rate + self._bills_daily_equivalent()

        horizon_end = self.today + timedelta(days=HORIZON_DAYS)
        charges_by_day: dict[date, list[dict]] = {}
        for when, bill in bill_charges(self.bills, self.today + timedelta(days=1), horizon_end):
            charges_by_day.setdefault(when, []).append(bill)
        income = infer_income_schedule(self.deposits, self.today, HORIZON_DAYS)
        income_by_day: dict[date, float] = {}
        for when, amount in income:
            income_by_day[when] = income_by_day.get(when, 0.0) + amount

        balance = float(self.current_balance)
        projection = [ProjectionPoint(date=self.today, balance=round(balance, 2))]
        insolvency_date: date | None = None
        lowest_balance, lowest_date = balance, self.today

        for offset in range(1, HORIZON_DAYS + 1):
            day = self.today + timedelta(days=offset)
            events: list[str] = []
            if day in income_by_day:
                balance += income_by_day[day]
                events.append(f"+nómina ${income_by_day[day]:,.0f}")
            balance -= purchases_burn_rate
            for bill in charges_by_day.get(day, []):
                balance -= float(bill.get("payment_amount", 0.0))
                events.append(f"-{bill.get('nickname') or bill.get('payee')} ${bill.get('payment_amount', 0):,.0f}")

            projection.append(ProjectionPoint(date=day, balance=round(balance, 2), events=events))
            if balance < lowest_balance:
                lowest_balance, lowest_date = balance, day
            if insolvency_date is None and balance < 0:
                insolvency_date = day

        return ForecastMetrics(
            burn_rate_daily=total_burn_rate,
            insolvency_date=insolvency_date,
            days_remaining=(insolvency_date - self.today).days if insolvency_date else None,
            confidence=confidence,
            next_paycheck_date=income[0][0] if income else None,
            paycheck_amount=income[0][1] if income else None,
            lowest_balance=round(lowest_balance, 2),
            lowest_balance_date=lowest_date,
            projection=projection,
        )
