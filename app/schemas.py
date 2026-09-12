"""
Modelos Pydantic compartidos entre la capa cuantitativa (forecaster.py) y la
capa cognitiva (agent.py). No tienen lógica, solo forma de datos.
"""

from datetime import date

from pydantic import BaseModel


class ForecastMetrics(BaseModel):
    burn_rate_daily: float
    insolvency_date: date | None
    days_remaining: int | None
    confidence: float | None  # R² de la regresión de purchases; None si no hubo regresión


class Action(BaseModel):
    description: str
    estimated_impact: str


class FinancialRescuePlan(BaseModel):
    summary: str
    insolvency_warning: str
    recommended_actions: list[Action]
