"""
Capa cognitiva: usa Gemini (google-genai) para convertir un ForecastMetrics
+ purchases en un FinancialRescuePlan con salida estructurada (response_schema).
Si Gemini falla (timeout, rate limit, key inválida, lo que sea) regresa un
plan de respaldo genérico en vez de dejar que la excepción suba — este agente
nunca debe tirar un 500.
"""

from google import genai
from google.genai import errors, types

from app.config import GEMINI_API_KEY
from app.schemas import Action, FinancialRescuePlan, ForecastMetrics, SectionInsights

MODEL = "gemini-flash-lite-latest"


class CognitiveFinancialAgent:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY no está configurada. Sácala gratis en "
                "aistudio.google.com/apikey y ponla en .env."
            )
        # attempts=1 (sin reintentos) + timeout corto: si Gemini está lento o
        # devuelve 503 ("alta demanda", real en el tier gratis), preferimos
        # caer al plan de respaldo en ~10s en vez de esperar ~30s a que el
        # SDK agote sus reintentos por default — crítico en vivo en el pitch.
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=10_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    async def generate_rescue_plan(
        self, forecast: ForecastMetrics, purchases: list[dict]
    ) -> tuple[FinancialRescuePlan, bool]:
        """Regresa (plan, exito). exito=False si se usó el plan de respaldo —
        el llamador no debe cachear un plan con exito=False."""
        prompt = self._build_prompt(forecast, purchases)

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FinancialRescuePlan,
                    # Los modelos 2.5 razonan ("thinking") antes de responder por
                    # default, lo que agrega latencia sin aportar al output
                    # estructurado que ya pedimos. flash-lite permite apagarlo.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return response.parsed, True
        except errors.APIError as e:
            print(f"[agent] Gemini falló ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast), False
        except Exception as e:
            print(f"[agent] Error inesperado generando el plan ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast), False

    async def generate_section_insights(self, summary: dict) -> tuple[SectionInsights, bool]:
        """Una conclusión corta por widget del dashboard, para el avatar canica.
        Regresa (insights, exito) — mismo contrato que generate_rescue_plan."""
        prompt = self._build_insights_prompt(summary)

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SectionInsights,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return response.parsed, True
        except errors.APIError as e:
            print(f"[agent] Gemini falló generando insights ({type(e).__name__}): {e}")
            return self._fallback_insights(summary), False
        except Exception as e:
            print(f"[agent] Error inesperado generando insights ({type(e).__name__}): {e}")
            return self._fallback_insights(summary), False

    def _build_insights_prompt(self, summary: dict) -> str:
        return (
            "Eres un asesor financiero. Con base en estos datos del usuario, genera "
            "UNA conclusión breve (máximo 1 frase, lenguaje simple, sin tecnicismos) "
            "por cada sección del dashboard:\n\n"
            f"- Saldo en checking: ${summary['checking_balance']:.2f}\n"
            f"- Gasto total ({summary['purchase_count']} compras): ${summary['total_spent']:.2f}\n"
            f"- Total en ahorros: ${summary['savings_total']:.2f}\n"
            f"- Saldo en tarjetas de crédito: ${summary['credit_total']:.2f}\n"
            f"- Préstamos activos: {summary['loan_count']}\n"
            f"- Puntos de recompensa acumulados: {summary['rewards_total']}\n\n"
            "Genera: balance (conclusión sobre el saldo), transactions (sobre el "
            "historial de movimientos), spending (sobre el patrón de gasto), "
            "banking_features (un tip general de uso del banco), savings (sobre "
            "los ahorros), credit (sobre las tarjetas), loans (sobre los "
            "préstamos), rewards (sobre las recompensas)."
        )

    def _fallback_insights(self, summary: dict) -> SectionInsights:
        return SectionInsights(
            balance=f"Tu saldo actual en checking es ${summary['checking_balance']:.2f}.",
            transactions=f"Registramos {summary['purchase_count']} movimientos recientes.",
            spending=f"Has gastado ${summary['total_spent']:.2f} en total.",
            banking_features="Explora las demás secciones para ver el resto de tus productos.",
            savings=f"Tienes ${summary['savings_total']:.2f} guardados en ahorros.",
            credit=f"Tu saldo en tarjetas de crédito es ${summary['credit_total']:.2f}.",
            loans=f"Tienes {summary['loan_count']} préstamo(s) registrado(s).",
            rewards=f"Acumulas {summary['rewards_total']} puntos de recompensa.",
        )

    def _build_prompt(self, forecast: ForecastMetrics, purchases: list[dict]) -> str:
        purchases_summary = (
            "\n".join(
                f"- {p.get('purchase_date')}: {p.get('description') or 'compra'} "
                f"(${p.get('amount', 0):.2f})"
                for p in purchases[:15]
            )
            or "Sin compras registradas."
        )

        if forecast.insolvency_date:
            insolvency_line = (
                f"Se proyecta insolvencia el {forecast.insolvency_date} "
                f"(en {forecast.days_remaining} días), con un burn rate de "
                f"${forecast.burn_rate_daily:.2f}/día."
            )
        else:
            insolvency_line = "No se proyecta insolvencia con la tendencia actual."

        return (
            "Eres un asesor financiero. Con base en este análisis, genera un plan de "
            "rescate breve y accionable para el usuario.\n\n"
            f"{insolvency_line}\n\n"
            "Historial de compras recientes:\n"
            f"{purchases_summary}\n\n"
            "Genera: un resumen breve (summary), una advertencia de insolvencia en "
            "lenguaje claro para el usuario (insolvency_warning), y 2-3 acciones "
            "concretas recomendadas (recommended_actions), cada una con su "
            "descripción y el impacto estimado en texto simple "
            '(ej. "+$50/mes" o "retrasa insolvencia 5 días").'
        )

    def _fallback_plan(self, forecast: ForecastMetrics) -> FinancialRescuePlan:
        if forecast.insolvency_date:
            warning = (
                "No pudimos generar un análisis detallado en este momento, pero tu "
                f"tendencia actual apunta a quedarte sin saldo alrededor del "
                f"{forecast.insolvency_date}."
            )
        else:
            warning = (
                "No pudimos generar un análisis detallado en este momento, pero no "
                "se detecta una tendencia de insolvencia inminente."
            )

        return FinancialRescuePlan(
            summary=(
                "No pudimos generar un plan personalizado en este momento. Aquí "
                "tienes recomendaciones generales mientras se restablece el servicio."
            ),
            insolvency_warning=warning,
            recommended_actions=[
                Action(
                    description=(
                        "Revisa tus gastos recurrentes (bills) y considera pausar "
                        "los que no sean esenciales."
                    ),
                    estimated_impact="Variable",
                ),
                Action(
                    description="Evita compras no esenciales hasta tu próximo ingreso.",
                    estimated_impact="Variable",
                ),
            ],
        )
