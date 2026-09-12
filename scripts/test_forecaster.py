"""
Checkpoint 2 de BACKEND.md: prueba calculate_forecast() con (a) datos
normales, (b) 1 solo dato, (c) 0 datos. Los tres casos deben responder
sin excepción.

Uso: python scripts/test_forecaster.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.forecaster import FinancialForecaster

DEMO_ACCOUNT_ID = "e8f0c102-eb26-4baf-ad78-629cc03c4d74"


def case_datos_normales() -> None:
    from app.cache import get_account, get_bills, get_purchases

    account = get_account(DEMO_ACCOUNT_ID)
    purchases = get_purchases(DEMO_ACCOUNT_ID)
    bills = get_bills(DEMO_ACCOUNT_ID)

    forecaster = FinancialForecaster(account["balance"], purchases, bills)
    result = forecaster.calculate_forecast()
    print(f"[caso a: datos normales] {result}")


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
