"""
Modelos Pydantic compartidos entre la capa cuantitativa (forecaster.py) y la
capa cognitiva (agent.py). No tienen lógica, solo forma de datos.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class ProjectionPoint(BaseModel):
    date: date
    balance: float
    # Cargos/abonos puntuales de ese día (bills y nómina), para que la UI pueda marcar los eventos.
    events: list[str] = []


class MonthEndAnalysis(BaseModel):
    """¿Llega a fin de mes a este paso? Calculado por el forecaster, no por el LLM."""

    month_end_date: date
    projected_balance: float  # saldo proyectado el último día del mes
    lowest_balance_until_month_end: float
    reaches_month_end: bool  # True si nunca queda en negativo antes de fin de mes
    monthly_income: float
    monthly_outflow: float  # compras del último mes + bills mensuales
    monthly_deficit: float  # max(0, outflow - income): lo que hay que recortar al mes


class ForecastMetrics(BaseModel):
    burn_rate_daily: float
    insolvency_date: date | None
    days_remaining: int | None
    confidence: float | None  # R² de la regresión de purchases; None si no hubo regresión
    next_paycheck_date: date | None = None
    paycheck_amount: float | None = None
    lowest_balance: float | None = None
    lowest_balance_date: date | None = None
    month_end: MonthEndAnalysis | None = None
    projection: list[ProjectionPoint] = []


# Áreas fijas de recomendación: el agente debe cubrir todas, exactamente una
# vez cada una. La prioridad final la decide él según los números. El enfoque
# es bienestar integral: cada área tiene un ángulo de dinero y uno de vida
# (salud, descanso, relaciones, tranquilidad).
RecommendationArea = Literal[
    "paso_de_hoy",        # una sola acción chica para hoy: bajar la ansiedad y recuperar control
    "fin_de_mes",         # ¿llega a fin de mes? ¿cuánto recortar?
    "suscripciones",      # streaming/gym prescindibles: dinero + tiempo de pantalla/descanso
    "comida_chatarra",    # alitas, tacos, botanas: dinero + salud
    "gastos_hormiga",     # compras chicas en OXXO: dinero + hábitos automáticos
    "vida_social",        # salidas con amigos: no aislarse, convivir gastando menos
    "movimiento",         # transporte: caminar/bici en tramos cortos = ahorro + actividad física
    "salud_preventiva",   # farmacia recurrente: chequeo gratuito antes de que sea gasto mayor
    "ahorro",             # apartar el sobrante: colchón = tranquilidad
    "integral",           # el cambio de fondo que más mueve la aguja
]


class Recommendation(BaseModel):
    area: RecommendationArea
    title: str  # ≤ 8 palabras, imperativo y cálido ("Cancela 4 suscripciones esta semana")
    description: str  # 1-2 frases concretas, con montos y nombres reales del historial
    wellbeing_benefit: str  # 1 frase: qué gana en salud, descanso, relaciones o tranquilidad
    estimated_impact: str  # ej. "+$1,034/mes" o "retrasa insolvencia 6 días"
    priority: int  # 1 = lo más importante


class FinancialRescuePlan(BaseModel):
    summary: str
    insolvency_warning: str
    recommendations: list[Recommendation]


class SectionInsights(BaseModel):
    """Una conclusión corta (1 frase) por widget del dashboard — las usa el
    avatar canica para mostrar un análisis distinto en cada parada.

    `general` es lo que NO pertenece a ningún widget (p. ej. una observación
    de hábitos deducida de las categorías de compra) — la canica lo muestra en
    su "casita" del sidebar."""

    general: str
    balance: str
    transactions: str
    spending: str
    banking_features: str
    savings: str
    credit: str
    loans: str
    rewards: str
