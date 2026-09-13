"""
Capa de detección (sin IA): cuándo cae la próxima nómina, a partir del
historial real de depósitos — nunca asumiendo quincena fija sin mirar los
datos primero.

Reusa `ledger.infer_income_schedule` (la misma inferencia que usa el
forecaster: mediana del intervalo entre depósitos, monto promedio de los dos
últimos; con un solo depósito asume quincena). Aquí solo se agrega lo que el
Agente Guía necesita encima: días que faltan y si el dato es estimado.

`is_estimated` es True cuando hay menos de 2 depósitos (no hay patrón real
que verificar) o cuando no hay ninguno y se cae al fallback calendario:
próxima quincena "de calendario" (día 15 o último día del mes). Nunca lanza
excepción ni regresa None — el saludo depende de esto.

Puro cómputo, sin I/O.
"""

import calendar
from datetime import date

from app.demo_data import DEMO_MONTHLY_INCOME
from app.ledger import infer_income_schedule
from app.schemas import PaydayInfo

# Suficiente para cubrir 3 quincenas: si en 45 días no aparece un depósito
# inferido, el patrón no es útil y se usa el fallback calendario.
HORIZON_DAYS = 45


class PaydayDetector:
    def detect(
        self,
        deposits: list[dict],
        today: date | None = None,
        fallback_amount: float = DEMO_MONTHLY_INCOME / 2,
    ) -> PaydayInfo:
        today = today or date.today()

        schedule = infer_income_schedule(deposits, today, HORIZON_DAYS) if deposits else []
        if schedule:
            when, amount = schedule[0]
            return PaydayInfo(
                next_payday_date=when,
                days_until_payday=(when - today).days,
                amount=round(float(amount), 2),
                is_estimated=len(deposits) < 2,
            )

        # Sin depósitos (o con un intervalo tan largo que no cae nada en el
        # horizonte): quincena de calendario. Si hay historial, el monto es su
        # promedio; si no, la mitad del ingreso mensual de referencia.
        if deposits:
            amounts = [float(d.get("amount") or 0.0) for d in deposits]
            fallback_amount = sum(amounts) / len(amounts)
        when = self._calendar_fallback(today)
        return PaydayInfo(
            next_payday_date=when,
            days_until_payday=(when - today).days,
            amount=round(float(fallback_amount), 2),
            is_estimated=True,
        )

    @staticmethod
    def _calendar_fallback(today: date) -> date:
        """Próxima quincena de calendario estrictamente después de hoy: el 15 o el último día del mes."""
        last_day = calendar.monthrange(today.year, today.month)[1]
        if today.day < 15:
            return date(today.year, today.month, 15)
        if today.day < last_day:
            return date(today.year, today.month, last_day)
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return date(year, month, 15)
