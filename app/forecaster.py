"""
Capa cuantitativa: proyecta el saldo futuro a partir de purchases/bills ya
cargados en memoria. Puro cómputo — no importa nessie_client, cache, ni db.
"""

import math
from datetime import date, timedelta

import pandas as pd
from sklearn.linear_model import LinearRegression

from app.schemas import ForecastMetrics

DAYS_PER_MONTH = 30


class FinancialForecaster:
    def __init__(self, current_balance: float, purchases: list[dict], bills: list[dict]):
        self.current_balance = current_balance
        self.purchases = purchases
        self.bills = bills

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

        full_range = pd.date_range(daily_spend.index.min(), date.today())
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
        bills_daily_equivalent = self._bills_daily_equivalent()
        total_burn_rate = purchases_burn_rate + bills_daily_equivalent

        if total_burn_rate <= 0:
            return ForecastMetrics(
                burn_rate_daily=0.0,
                insolvency_date=None,
                days_remaining=None,
                confidence=confidence,
            )

        days_remaining = math.floor(self.current_balance / total_burn_rate)
        insolvency_date = date.today() + timedelta(days=days_remaining)

        return ForecastMetrics(
            burn_rate_daily=total_burn_rate,
            insolvency_date=insolvency_date,
            days_remaining=days_remaining,
            confidence=confidence,
        )
