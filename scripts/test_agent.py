"""
Checkpoint 3 de BACKEND.md: llama a CognitiveFinancialAgent con el forecast
de los 3 casos del Checkpoint 2 y confirma que siempre regresa un
FinancialRescuePlan válido, incluso en el caso "sin datos" y cuando Claude
falla (key inválida).

Uso: python scripts/test_agent.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import CognitiveFinancialAgent
from app.forecaster import FinancialForecaster

DEMO_ACCOUNT_ID = "e8f0c102-eb26-4baf-ad78-629cc03c4d74"


async def case_datos_normales(agent: CognitiveFinancialAgent) -> None:
    from app.cache import get_account, get_bills, get_purchases

    account = get_account(DEMO_ACCOUNT_ID)
    purchases = get_purchases(DEMO_ACCOUNT_ID)
    bills = get_bills(DEMO_ACCOUNT_ID)

    forecast = FinancialForecaster(account["balance"], purchases, bills).calculate_forecast()
    plan, success = await agent.generate_rescue_plan(forecast, purchases)
    print(f"[caso a: datos normales] (exito={success})\n{plan.model_dump_json(indent=2)}\n")


async def case_un_solo_dato(agent: CognitiveFinancialAgent) -> None:
    purchases = [
        {
            "_id": "test-1",
            "amount": 50.0,
            "purchase_date": "2026-09-01",
            "description": "compra única de prueba",
            "status": "completed",
        }
    ]
    forecast = FinancialForecaster(100.0, purchases, []).calculate_forecast()
    plan, success = await agent.generate_rescue_plan(forecast, purchases)
    print(f"[caso b: 1 solo dato] (exito={success})\n{plan.model_dump_json(indent=2)}\n")


async def case_cero_datos(agent: CognitiveFinancialAgent) -> None:
    forecast = FinancialForecaster(100.0, [], []).calculate_forecast()
    plan, success = await agent.generate_rescue_plan(forecast, [])
    print(f"[caso c: 0 datos] (exito={success})\n{plan.model_dump_json(indent=2)}\n")


async def case_gemini_caido() -> None:
    """Fuerza un fallo de Gemini (key inválida) y confirma que el fallback funciona."""
    agent = CognitiveFinancialAgent(api_key="invalid-test-key")

    forecast = FinancialForecaster(100.0, [], []).calculate_forecast()
    plan, success = await agent.generate_rescue_plan(forecast, [])
    print(f"[caso d: Gemini caído / key inválida -> fallback] (exito={success})\n{plan.model_dump_json(indent=2)}\n")
    assert success is False, "el caso de key inválida debería marcar exito=False"


async def main() -> None:
    agent = CognitiveFinancialAgent()
    await case_datos_normales(agent)
    await case_un_solo_dato(agent)
    await case_cero_datos(agent)
    await case_gemini_caido()
    print("[test_agent] Los 4 casos respondieron un FinancialRescuePlan válido sin excepción — Checkpoint 3 OK.")


if __name__ == "__main__":
    asyncio.run(main())
