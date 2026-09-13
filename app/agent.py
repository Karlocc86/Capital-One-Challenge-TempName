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
from app.schemas import Action, FinancialRescuePlan, ForecastMetrics

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
        self,
        forecast: ForecastMetrics,
        purchases: list[dict],
        bills: list[dict] | None = None,
        balance: float | None = None,
    ) -> tuple[FinancialRescuePlan, bool]:
        """Regresa (plan, exito). exito=False si se usó el plan de respaldo —
        el llamador no debe cachear un plan con exito=False."""
        prompt = self._build_prompt(forecast, purchases, bills or [], balance)

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=FinancialRescuePlan,
                    # Antes se mandaba thinking_config=ThinkingConfig(thinking_budget=0)
                    # para bajar latencia, pero el modelo al que apunta hoy
                    # `gemini-flash-lite-latest` responde 400 INVALID_ARGUMENT
                    # con ese parámetro (verificado 2026-09-12). Sin él funciona.
                ),
            )
            return response.parsed, True
        except errors.APIError as e:
            print(f"[agent] Gemini falló ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast), False
        except Exception as e:
            print(f"[agent] Error inesperado generando el plan ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast), False

    def _build_prompt(
        self,
        forecast: ForecastMetrics,
        purchases: list[dict],
        bills: list[dict],
        balance: float | None,
    ) -> str:
        purchases_summary = (
            "\n".join(
                f"- {p.get('purchase_date')}: {p.get('merchant_name') or p.get('description') or 'compra'}"
                f"{' [' + p['category'] + ']' if p.get('category') else ''} (${p.get('amount', 0):.2f})"
                for p in purchases[:15]
            )
            or "Sin compras registradas."
        )
        bills_summary = (
            "\n".join(
                f"- {b.get('payee') or b.get('nickname')}: ${b.get('payment_amount', 0):.2f} el día {b.get('recurring_date')} de cada mes"
                for b in bills
                if b.get("status") == "recurring"
            )
            or "Sin pagos fijos registrados."
        )

        context_lines = []
        if balance is not None:
            context_lines.append(f"Saldo disponible hoy: ${balance:,.2f} MXN.")
        if forecast.next_paycheck_date:
            context_lines.append(
                f"Próxima nómina esperada: {forecast.next_paycheck_date} (${forecast.paycheck_amount or 0:,.2f})."
            )
        if forecast.insolvency_date:
            context_lines.append(
                f"Se proyecta insolvencia el {forecast.insolvency_date} "
                f"(en {forecast.days_remaining} días), con un gasto promedio de "
                f"${forecast.burn_rate_daily:.2f}/día (compras + pagos fijos prorrateados)."
            )
        else:
            context_lines.append("No se proyecta insolvencia en los próximos 90 días con la tendencia actual.")
        if forecast.lowest_balance is not None and forecast.lowest_balance_date:
            context_lines.append(
                f"Punto más bajo proyectado: ${forecast.lowest_balance:,.2f} el {forecast.lowest_balance_date}."
            )
        # Los cargos puntuales de las próximas semanas son lo que el usuario
        # necesita ver venir (la renta pega de golpe, no prorrateada).
        upcoming = [
            f"- {pt.date}: {', '.join(pt.events)} → saldo ${pt.balance:,.2f}"
            for pt in forecast.projection[1:31]
            if pt.events
        ]
        if upcoming:
            context_lines.append("Movimientos fijos de los próximos 30 días:\n" + "\n".join(upcoming))

        return (
            "Eres un asesor financiero para una persona de ingreso medio-bajo en México "
            "(montos en pesos mexicanos). Con base en este análisis, genera un plan de "
            "rescate breve, concreto y realista para el usuario.\n\n"
            + "\n".join(context_lines)
            + "\n\nPagos fijos mensuales:\n"
            f"{bills_summary}\n\n"
            "Compras recientes (comercio [categoría]):\n"
            f"{purchases_summary}\n\n"
            "Genera: un resumen breve (summary), una advertencia de insolvencia en "
            "lenguaje claro para el usuario (insolvency_warning), y 2-3 acciones "
            "concretas recomendadas (recommended_actions) que se puedan ejecutar esta "
            "semana — menciona comercios o categorías específicas del historial cuando "
            "aplique — cada una con su descripción y el impacto estimado en texto simple "
            '(ej. "+$500/mes" o "retrasa insolvencia 5 días").'
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
