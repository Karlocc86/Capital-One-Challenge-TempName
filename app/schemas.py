"""
Modelos Pydantic compartidos entre la capa cuantitativa (forecaster.py) y la
capa cognitiva (agent.py). No tienen lógica, solo forma de datos.
"""

from datetime import date

from pydantic import BaseModel


class ProjectionPoint(BaseModel):
    date: date
    balance: float
    # Cargos/abonos puntuales de ese día (bills y nómina), para que la UI pueda marcar los eventos.
    events: list[str] = []


class ForecastMetrics(BaseModel):
    burn_rate_daily: float
    insolvency_date: date | None
    days_remaining: int | None
    confidence: float | None  # R² de la regresión de purchases; None si no hubo regresión
    next_paycheck_date: date | None = None
    paycheck_amount: float | None = None
    lowest_balance: float | None = None
    lowest_balance_date: date | None = None
    projection: list[ProjectionPoint] = []


class Action(BaseModel):
    description: str
    estimated_impact: str


class FinancialRescuePlan(BaseModel):
    summary: str
    insolvency_warning: str
    recommended_actions: list[Action]
