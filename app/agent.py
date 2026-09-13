"""
Capa cognitiva: usa Gemini (google-genai) para convertir un ForecastMetrics
+ movimientos en un FinancialRescuePlan con salida estructurada
(response_schema): resumen, advertencia y una lista de recomendaciones por
área (fin de mes, suscripciones, comida chatarra, gastos hormiga, ahorro,
integral). Los números (saldo, déficit, totales por área) los calcula el
backend; Gemini solo redacta sobre ellos.

Si Gemini falla (timeout, rate limit, key inválida, lo que sea) regresa un
plan de respaldo en vez de dejar que la excepción suba — este agente nunca
debe tirar un 500.
"""

from google import genai
from google.genai import errors, types

from app.categories import HORMIGA_MAX, spending_breakdown
from app.config import GEMINI_API_KEY
from app.demo_data import DISCRETIONARY_BILLS
from app.schemas import FinancialRescuePlan, ForecastMetrics, Recommendation, SectionInsights

MODEL = "gemini-flash-lite-latest"

# Cada área debe aparecer exactamente una vez en el plan.
AREAS = (
    ("fin_de_mes", "Análisis de fin de mes: ¿llega a fin de mes a este paso? ¿cuánto tiene que recortar al mes?"),
    ("suscripciones", "Suscripciones prescindibles: cuáles cancelar o pausar primero y cuánto libera."),
    ("comida_chatarra", "Comida chatarra: reducirla por dinero Y por salud (menciona el beneficio de salud concreto, sin sermonear)."),
    ("gastos_hormiga", f"Gastos hormiga (compras chicas < ${HORMIGA_MAX:.0f} en OXXO/tiendas que se acumulan sin sentirse): cómo cortarlos."),
    ("ahorro", "Ahorro: qué hacer con lo que sobre cuando cierre un mes en positivo (apartar automático a la cuenta de Ahorro)."),
    ("integral", "Recomendación integral: el cambio de fondo más importante para su situación (uno solo, el que más mueve la aguja)."),
)


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
                timeout=15_000,
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
        bills = bills or []
        breakdown = spending_breakdown(purchases, bills, DISCRETIONARY_BILLS)
        prompt = self._build_prompt(forecast, purchases, bills, balance, breakdown)

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
            plan: FinancialRescuePlan = response.parsed
            plan.recommendations.sort(key=lambda r: r.priority)
            return plan, True
        except errors.APIError as e:
            print(f"[agent] Gemini falló ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast, breakdown), False
        except Exception as e:
            print(f"[agent] Error inesperado generando el plan ({type(e).__name__}): {e}")
            return self._fallback_plan(forecast, breakdown), False

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

    def _build_prompt(
        self,
        forecast: ForecastMetrics,
        purchases: list[dict],
        bills: list[dict],
        balance: float | None,
        breakdown: dict,
    ) -> str:
        purchases_summary = (
            "\n".join(
                f"- {p.get('purchase_date')}: {p.get('merchant_name') or p.get('description') or 'compra'}"
                f"{' [' + p['category'] + ']' if p.get('category') else ''} (${p.get('amount', 0):.2f})"
                for p in purchases[:20]
            )
            or "Sin compras registradas."
        )
        bills_summary = (
            "\n".join(
                f"- {b.get('payee') or b.get('nickname')}: ${b.get('payment_amount', 0):.2f} el día {b.get('recurring_date')}"
                f"{' (prescindible)' if b.get('nickname') in DISCRETIONARY_BILLS else ''}"
                for b in bills
                if b.get("status") == "recurring"
            )
            or "Sin pagos fijos registrados."
        )

        context: list[str] = []
        if balance is not None:
            context.append(f"Saldo disponible hoy: ${balance:,.2f} MXN.")
        if forecast.next_paycheck_date:
            context.append(
                f"Próxima nómina esperada: {forecast.next_paycheck_date} (${forecast.paycheck_amount or 0:,.2f})."
            )
        if forecast.insolvency_date:
            context.append(
                f"Se proyecta insolvencia el {forecast.insolvency_date} (en {forecast.days_remaining} días); "
                f"gasto promedio ${forecast.burn_rate_daily:.2f}/día (compras + pagos fijos prorrateados)."
            )
        else:
            context.append("No se proyecta insolvencia en los próximos 90 días con la tendencia actual.")
        if forecast.lowest_balance is not None and forecast.lowest_balance_date:
            context.append(f"Punto más bajo proyectado: ${forecast.lowest_balance:,.2f} el {forecast.lowest_balance_date}.")

        me = forecast.month_end
        if me:
            verdict = "SÍ llega a fin de mes" if me.reaches_month_end else "NO llega a fin de mes"
            context.append(
                f"Fin de mes ({me.month_end_date}): {verdict}. Saldo proyectado ese día ${me.projected_balance:,.2f}; "
                f"punto más bajo antes de fin de mes ${me.lowest_balance_until_month_end:,.2f}. "
                f"Ingreso mensual ${me.monthly_income:,.2f} vs egresos mensuales ${me.monthly_outflow:,.2f} "
                f"→ déficit estructural ${me.monthly_deficit:,.2f}/mes (lo mínimo que hay que recortar)."
            )

        upcoming = [
            f"- {pt.date}: {', '.join(pt.events)} → saldo ${pt.balance:,.2f}"
            for pt in forecast.projection[1:31]
            if pt.events
        ]
        if upcoming:
            context.append("Movimientos fijos de los próximos 30 días:\n" + "\n".join(upcoming))

        def _top(items: list[tuple[str, float, int]]) -> str:
            return ", ".join(f"{name} ${total:,.0f} ({n})" for name, total, n in items) or "ninguno"

        diagnosis = (
            f"- Suscripciones prescindibles: ${breakdown['subscriptions_total']:,.2f}/mes → "
            + (", ".join(f"{n} ${a:,.0f}" for n, a in breakdown["subscriptions"]) or "ninguna")
            + f"\n- Comida chatarra (últimos 30 días): ${breakdown['junk_food_total']:,.2f} en "
            f"{breakdown['junk_food_count']} compras → {_top(breakdown['junk_food_top'])}"
            f"\n- Gastos hormiga (< ${HORMIGA_MAX:.0f}, últimos 30 días): ${breakdown['hormiga_total']:,.2f} en "
            f"{breakdown['hormiga_count']} compras → {_top(breakdown['hormiga_top'])}"
        )

        areas = "\n".join(f'- area="{key}": {what}' for key, what in AREAS)

        return (
            "Eres un asesor financiero para una persona de ingreso medio-bajo en México "
            "(montos en pesos mexicanos). Con base en este análisis, genera un plan de "
            "rescate breve, concreto y realista.\n\n"
            "## Situación\n" + "\n".join(context) + "\n\n"
            "## Diagnóstico por área\n" + diagnosis + "\n\n"
            "## Pagos fijos mensuales\n" + bills_summary + "\n\n"
            "## Compras recientes (comercio [categoría])\n" + purchases_summary + "\n\n"
            "## Qué generar\n"
            "1. summary: 1-2 frases con la situación (usa los números).\n"
            "2. insolvency_warning: advertencia clara para el usuario (fecha, días, qué la provoca).\n"
            "3. recommendations: EXACTAMENTE 6, una por área, en este orden de áreas:\n"
            f"{areas}\n"
            "Cada recomendación: title (≤ 8 palabras, imperativo), description (1-2 frases, "
            "concreta, con montos y nombres reales del historial), estimated_impact (ej. "
            '"+$1,034/mes", "retrasa insolvencia 6 días"), priority (1 = la más importante; '
            "asigna prioridades distintas del 1 al 6 según cuánto mueve la aguja para ESTE usuario). "
            "Sé conciso: nada de relleno ni frases motivacionales."
        )

    def _fallback_plan(self, forecast: ForecastMetrics, breakdown: dict) -> FinancialRescuePlan:
        """Plan de respaldo con los números reales del diagnóstico (sin LLM)."""
        me = forecast.month_end
        if forecast.insolvency_date:
            warning = (
                f"Tu tendencia actual apunta a quedarte sin saldo el {forecast.insolvency_date} "
                f"(en {forecast.days_remaining} días)."
            )
        else:
            warning = "No se detecta una tendencia de insolvencia inminente."

        if me and not me.reaches_month_end:
            month_end_desc = (
                f"A este paso no llegas a fin de mes: tu punto más bajo antes del {me.month_end_date} "
                f"es ${me.lowest_balance_until_month_end:,.0f}. Necesitas recortar al menos "
                f"${me.monthly_deficit:,.0f} al mes."
            )
        elif me:
            month_end_desc = (
                f"Sí llegas a fin de mes: saldo proyectado ${me.projected_balance:,.0f} el {me.month_end_date}."
            )
        else:
            month_end_desc = "No hay suficientes datos para proyectar el fin de mes."

        subs = breakdown.get("subscriptions", [])
        recs = [
            Recommendation(
                area="fin_de_mes", title="Recorta el déficit mensual", description=month_end_desc,
                estimated_impact=f"-${me.monthly_deficit:,.0f}/mes de déficit" if me else "Variable", priority=1,
            ),
            Recommendation(
                area="suscripciones", title="Cancela las suscripciones prescindibles",
                description="Pausa hoy " + (", ".join(n for n, _ in subs) or "tus suscripciones de streaming/gym") + ".",
                estimated_impact=f"+${breakdown.get('subscriptions_total', 0):,.0f}/mes", priority=2,
            ),
            Recommendation(
                area="comida_chatarra", title="Reduce la comida chatarra a la mitad",
                description=(
                    f"Gastaste ${breakdown.get('junk_food_total', 0):,.0f} en alitas, tacos y botanas este mes. "
                    "Cocinar en casa baja el gasto y el consumo de sodio, grasa y azúcar."
                ),
                estimated_impact=f"+${breakdown.get('junk_food_total', 0) / 2:,.0f}/mes", priority=3,
            ),
            Recommendation(
                area="gastos_hormiga", title="Frena los gastos hormiga",
                description=(
                    f"{breakdown.get('hormiga_count', 0)} compras chicas sumaron ${breakdown.get('hormiga_total', 0):,.0f}. "
                    "Ponte un tope semanal en efectivo para OXXO y antojos."
                ),
                estimated_impact=f"+${breakdown.get('hormiga_total', 0) / 2:,.0f}/mes", priority=4,
            ),
            Recommendation(
                area="ahorro", title="Aparta el sobrante el día de la nómina",
                description="Cuando un mes cierre en positivo, mueve el excedente a tu cuenta de Ahorro el mismo día que cae la quincena.",
                estimated_impact="Colchón de 1 renta en ~6 meses", priority=5,
            ),
            Recommendation(
                area="integral", title="Alinea tus gastos fijos con tu ingreso",
                description="Tus pagos fijos más la comida fuera superan lo que ganas; sin bajar uno de los dos, ningún ajuste chico alcanza.",
                estimated_impact="Cierra el déficit estructural", priority=6,
            ),
        ]
        return FinancialRescuePlan(
            summary=(
                "No pudimos generar un plan personalizado con IA en este momento; estas "
                "recomendaciones se calcularon directamente de tus movimientos."
            ),
            insolvency_warning=warning,
            recommendations=recs,
        )
