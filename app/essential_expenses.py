"""
Capa de detección (sin IA): qué gastos fijos son ESENCIALES — los que tienen
fecha de pago puntual y no se pueden dejar de pagar (renta, servicios) — y
cuándo cae el próximo cobro de cada uno. Es lo que el Agente Guía usa para
proponer apartar el dinero en una Cajita antes de que llegue la fecha.

Reglas:
- Solo bills recurrentes. Una bill es esencial si NO está en
  DISCRETIONARY_BILLS (las suscripciones prescindibles: streaming, gym).
  Ese conjunto ya es la fuente de verdad de "prescindible" en todo el
  backend (agente, /bills), así que aquí no hay una segunda lista que
  mantener.
- Alcance acotado a bills a propósito: son los únicos gastos con UNA fecha de
  pago a la que tiene sentido apartarle dinero. El gasto de transporte o súper
  es continuo (casi diario), no encaja en "aparta antes del día X".
- Guardias: monto ≤ 0 o día de cobro fuera de 1-31 se ignoran (mejor un falso
  negativo que proponer una cajita para un dato roto).

Puro cómputo, sin I/O.
"""

from datetime import date

from app.categories import bill_category
from app.demo_data import DISCRETIONARY_BILLS
from app.ledger import next_bill_date
from app.schemas import EssentialExpense


class EssentialExpenseDetector:
    def __init__(self, discretionary_bills: set[str] | None = None):
        self.discretionary_bills = DISCRETIONARY_BILLS if discretionary_bills is None else discretionary_bills

    def detect(self, bills: list[dict], today: date | None = None) -> list[EssentialExpense]:
        """Gastos esenciales ordenados por próxima fecha de cobro (el más urgente primero)."""
        today = today or date.today()
        found: list[EssentialExpense] = []

        for bill in bills:
            if bill.get("status") != "recurring":
                continue
            nickname = bill.get("nickname") or bill.get("payee") or ""
            if not nickname or nickname in self.discretionary_bills:
                continue

            try:
                amount = float(bill.get("payment_amount") or 0.0)
                recurring_date = int(bill.get("recurring_date") or 0)
            except (TypeError, ValueError):
                continue
            if amount <= 0 or not 1 <= recurring_date <= 31:
                continue

            found.append(
                EssentialExpense(
                    name=nickname,
                    payee=bill.get("payee") or nickname,
                    category=bill_category(nickname, self.discretionary_bills),
                    amount=round(amount, 2),
                    recurring_date=recurring_date,
                    next_due_date=next_bill_date(recurring_date, today),
                )
            )

        found.sort(key=lambda e: (e.next_due_date, -e.amount))
        return found
