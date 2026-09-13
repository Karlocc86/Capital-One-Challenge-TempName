"""
Checkpoint 2 de BACKEND.md: prueba calculate_forecast() con (a) datos
normales, (b) 1 solo dato, (c) 0 datos. Los tres casos deben responder
sin excepción.

Uso: python scripts/test_forecaster.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DEMO_ACCOUNT_ID as _ENV_ACCOUNT_ID
from app.forecaster import FinancialForecaster

DEMO_ACCOUNT_ID = _ENV_ACCOUNT_ID or "98f6dab5-9b48-4ebe-8f71-13e7308d5b2d"


def case_datos_normales() -> None:
    from app.cache import get_account, get_bills, get_deposits, get_purchases
    from app.ledger import compute_balance

    account = get_account(DEMO_ACCOUNT_ID)
    purchases = get_purchases(DEMO_ACCOUNT_ID)
    deposits = get_deposits(DEMO_ACCOUNT_ID)
    bills = get_bills(DEMO_ACCOUNT_ID)
    # Mismo saldo que usa /forecast: inicial + depósitos − compras − bills cobradas.
    balance = compute_balance(account["balance"], deposits, purchases, bills)["balance"]

    forecaster = FinancialForecaster(balance, purchases, bills, deposits)
    result = forecaster.calculate_forecast()
    print(f"[caso a: datos normales] {result}")
    # El dataset demo (app/demo_data.py) está calibrado para ~13 días; si esto
    # falla, el seed o el sync están sirviendo datos distintos a los esperados.
    assert result.days_remaining is not None and 10 <= result.days_remaining <= 16, (
        f"days_remaining={result.days_remaining}, se esperaba entre 10 y 16 "
        "(¿corriste seed.py --reset y sync.py hoy?)"
    )


def case_un_solo_dato() -> None:
    purchases = [
        {
            "_id": "test-1",
            "amount": 50.0,
            "purchase_date": "2026-09-01",
            "description": "compra única de prueba",
            "status": "completed",
        }
    ]
    forecaster = FinancialForecaster(current_balance=100.0, purchases=purchases, bills=[])
    result = forecaster.calculate_forecast()
    print(f"[caso b: 1 solo dato] {result}")


def case_cero_datos() -> None:
    forecaster = FinancialForecaster(current_balance=100.0, purchases=[], bills=[])
    result = forecaster.calculate_forecast()
    print(f"[caso c: 0 datos] {result}")


def main() -> None:
    case_datos_normales()
    case_un_solo_dato()
    case_cero_datos()
    print("\n[test_forecaster] Los 3 casos respondieron sin excepción — Checkpoint 2 OK.")


if __name__ == "__main__":
    main()
