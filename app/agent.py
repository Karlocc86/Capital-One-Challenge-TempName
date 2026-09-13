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

# Cada área debe aparecer exactamente una vez en el plan. El enfoque es
# bienestar integral: en cada área hay un ángulo de dinero y uno de vida.
AREAS = (
    ("paso_de_hoy", "Tu paso de hoy: UNA sola acción chica y concreta para hacer HOY (≤ 15 minutos) que baje la ansiedad de estar a pocos días de cero y devuelva sensación de control. No es un recorte más: es el primer paso."),
    ("fin_de_mes", "Fin de mes: ¿llega a fin de mes a este paso? ¿cuánto tiene que recortar al mes? Dilo con claridad y sin alarmismo; la tranquilidad de saber el número exacto es parte del bienestar."),
    ("suscripciones", "Suscripciones prescindibles: cuáles pausar/cancelar primero y cuánto libera. Ángulo de vida: menos pantallas = más descanso y sueño; sugiere quedarse con UNA que de verdad disfrute."),
    ("comida_chatarra", "Comida chatarra: reducirla por dinero Y por salud (energía, digestión, sodio/grasa, riesgo cardiovascular). Propón el reemplazo concreto, no solo la prohibición."),
    ("gastos_hormiga", f"Gastos hormiga (compras chicas < ${HORMIGA_MAX:.0f} en OXXO/tiendas): son hábitos automáticos, no falta de voluntad. Propón un reemplazo (termo de café, botella de agua) y un tope semanal en efectivo."),
    ("vida_social", "Vida social: las salidas con amigos (alitas, partido) importan para su bienestar emocional — NO recomiendes aislarse. Propón cómo mantener la convivencia gastando menos (partido en casa, cooperacha, un plato compartido)."),
    ("movimiento", "Movimiento: con base en su gasto de transporte (camión, gasolina), propón sustituir tramos cortos por caminar o bici. Ángulo de vida: actividad física diaria, menos estrés; ángulo de dinero: cuánto ahorra."),
    ("salud_preventiva", "Salud preventiva: si gasta seguido en farmacia (medicamentos, analgésicos), sugiere atender la causa (chequeo gratuito en IMSS/centro de salud, sueño, alimentación) antes de que se vuelva un gasto mayor. Sin diagnosticar."),
    ("ahorro", "Ahorro: qué hacer con lo que sobre cuando cierre un mes en positivo (apartar automático a su cuenta de Ahorro el día de la nómina). Ángulo de vida: un colchón es dormir tranquilo."),
    ("integral", "Recomendación integral: el cambio de fondo más importante para su situación (uno solo, el que más mueve la aguja), conectando dinero y bienestar."),
)


class CognitiveFinancialAgent:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY no está configurada. Sácala gratis en "
                "aistudio.google.com/apikey y ponla en .env."
            )
        # attempts=1 (sin reintentos): si Gemini devuelve 503 ("alta demanda",
        # real en el tier gratis) caemos al plan de respaldo en vez de esperar
        # a que el SDK agote sus reintentos. El timeout es generoso (40 s)
        # porque el plan completo (10 recomendaciones con bienestar) tarda
        # ~15-25 s en flash-lite; en el pitch nunca se llama en vivo: el plan
        # se calienta antes y se sirve desde rescue_plans_cache en ~2 s.
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=40_000,
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
                    # Sin thinking_config: ver nota en generate_rescue_plan (400 con este modelo).
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
        categories = summary.get("spent_by_category") or {}
        categories_text = (
            "\n".join(f"  - {cat}: ${amt:.2f}" for cat, amt in categories.items())
            or "  - (sin compras)"
        )
        return (
            "Eres un acompañante de bienestar integral, cercano y humano (sabes de finanzas, "
            "pero te importa cómo vive la persona). Todos los montos están en pesos "
            "mexicanos (MXN); nunca digas dólares. Con base en estos datos del "
            "usuario, genera UNA conclusión breve (máximo 1 frase, lenguaje simple, "
            "sin tecnicismos, tuteando, sin culpa) por cada sección del dashboard:\n\n"
            f"- Saldo en checking: ${summary['checking_balance']:.2f}\n"
            f"- Gasto total ({summary['purchase_count']} compras): ${summary['total_spent']:.2f}\n"
            f"- Gasto por categoría:\n{categories_text}\n"
            f"- Total en ahorros: ${summary['savings_total']:.2f}\n"
            f"- Saldo en tarjetas de crédito: ${summary['credit_total']:.2f}\n"
            f"- Préstamos activos: {summary['loan_count']}\n"
            f"- Puntos de recompensa acumulados: {summary['rewards_total']}\n\n"
            "Genera: general (una observación que NO pertenezca a ninguna sección "
            "del banco: algo sobre los hábitos o el bienestar de la persona que se "
            "deduzca de sus categorías de compra — p. ej. mucha comida chatarra, "
            "gasto en salud, transporte — dicho con empatía), balance (conclusión "
            "sobre el saldo), transactions (sobre el historial de movimientos), "
            "spending (sobre el patrón de gasto), banking_features (un tip general "
            "de uso del banco), savings (sobre los ahorros), credit (sobre las "
            "tarjetas), loans (sobre los préstamos), rewards (sobre las recompensas)."
        )

    def _fallback_insights(self, summary: dict) -> SectionInsights:
        categories = summary.get("spent_by_category") or {}
        if categories:
            top_cat, top_amt = next(iter(categories.items()))
            general = f"Noté que donde más gastas es en {top_cat.lower()} (${top_amt:.2f}). ¿Todo bien por ahí?"
        else:
            general = "Aún no veo compras registradas; cuando las haya te cuento qué noto."
        return SectionInsights(
            general=general,
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
            f"\n- Salidas sociales (restaurantes): ${breakdown['outings_total']:,.2f} en {breakdown['outings_count']} → "
            + ("; ".join(breakdown["outings_items"]) or "ninguna")
            + f"\n- Transporte: ${breakdown['transport_total']:,.2f} → {_top(breakdown['transport_top'])}"
            f"\n- Salud/farmacia: ${breakdown['health_total']:,.2f} en {breakdown['health_count']} compras → "
            + (", ".join(breakdown["health_items"]) or "ninguna")
        )

        areas = "\n".join(f'- area="{key}": {what}' for key, what in AREAS)

        return (
            "Eres un acompañante de bienestar integral para una persona de ingreso medio-bajo "
            "en México (montos en pesos mexicanos). Sabes de finanzas personales, pero tu "
            "objetivo no es solo que le alcance el dinero: es que viva mejor — con menos "
            "ansiedad, más salud, mejor descanso y sin perder a su gente. El dinero es el "
            "medio; el bienestar es el fin.\n\n"
            "Tono: cercano y cálido, tuteando, como un amigo que sabe del tema y se preocupa "
            "por él. Sin culpa, sin sermones, sin frases motivacionales vacías. Reconoce lo "
            "que ya hace bien (p. ej. paga su renta, tiene ingreso estable) antes de pedir "
            "cambios. Cada recomendación debe ser realista para su vida real, no ideal.\n\n"
            "## Situación\n" + "\n".join(context) + "\n\n"
            "## Diagnóstico por área (últimos 30 días)\n" + diagnosis + "\n\n"
            "## Pagos fijos mensuales\n" + bills_summary + "\n\n"
            "## Compras recientes (comercio [categoría])\n" + purchases_summary + "\n\n"
            "## Qué generar\n"
            "1. summary: 2 frases: cómo está (con los números clave) y un mensaje de que tiene "
            "salida — sin minimizar ni dramatizar.\n"
            "2. insolvency_warning: advertencia clara y humana (fecha, días, qué la provoca), "
            "seguida de una frase que baje la ansiedad: qué es lo primero que haría hoy.\n"
            f"3. recommendations: EXACTAMENTE {len(AREAS)}, una por área, cubriendo todas estas áreas:\n"
            f"{areas}\n"
            "Cada recomendación: title (≤ 8 palabras, imperativo y cálido), description (1-2 "
            "frases concretas, con montos y nombres reales del historial), wellbeing_benefit "
            "(1 frase: qué gana en salud, descanso, relaciones o tranquilidad — específico, "
            "no genérico), estimated_impact (ej. \"+$1,034/mes\", \"retrasa insolvencia 6 "
            "días\", \"+30 min de caminata al día\"), priority (1 = la más importante; "
            f"prioridades distintas del 1 al {len(AREAS)} según cuánto mejora la vida de ESTE "
            "usuario, no solo su saldo). Sé conciso: nada de relleno."
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
        junk = breakdown.get("junk_food_total", 0)
        hormiga_total = breakdown.get("hormiga_total", 0)
        outings = breakdown.get("outings_total", 0)
        transport = breakdown.get("transport_total", 0)
        health = breakdown.get("health_total", 0)
        recs = [
            Recommendation(
                area="paso_de_hoy", title="Hoy: pausa una suscripción y respira",
                description="Entra a la app de la suscripción que menos uses y pásala a pausa. Son 5 minutos y ya diste el primer paso.",
                wellbeing_benefit="Recuperar sensación de control baja la ansiedad más que cualquier número.",
                estimated_impact="+$99–$499/mes desde hoy", priority=1,
            ),
            Recommendation(
                area="fin_de_mes", title="Conoce tu número y quítate el peso", description=month_end_desc,
                wellbeing_benefit="Saber exactamente cuánto falta quita la incertidumbre que no te deja dormir.",
                estimated_impact=f"-${me.monthly_deficit:,.0f}/mes de déficit" if me else "Variable", priority=2,
            ),
            Recommendation(
                area="suscripciones", title="Quédate con una suscripción, pausa el resto",
                description="Pausa " + (", ".join(n for n, _ in subs) or "tus suscripciones de streaming/gym") + " y conserva solo la que de verdad disfrutes.",
                wellbeing_benefit="Menos pantallas en la noche = mejor sueño y más tiempo para ti.",
                estimated_impact=f"+${breakdown.get('subscriptions_total', 0):,.0f}/mes", priority=3,
            ),
            Recommendation(
                area="comida_chatarra", title="Cambia la mitad de las alitas por comida casera",
                description=f"Gastaste ${junk:,.0f} en alitas, tacos y botanas este mes. Empieza con dos cenas en casa a la semana.",
                wellbeing_benefit="Menos sodio y grasa: más energía en el día y menos malestar estomacal.",
                estimated_impact=f"+${junk / 2:,.0f}/mes", priority=4,
            ),
            Recommendation(
                area="gastos_hormiga", title="Lleva termo y botella: adiós hormigas",
                description=f"{breakdown.get('hormiga_count', 0)} compras chicas en OXXO sumaron ${hormiga_total:,.0f}. Café de casa en termo y agua en botella cubren la mayoría.",
                wellbeing_benefit="Rompes el piloto automático del antojo; menos azúcar y cafeína de más.",
                estimated_impact=f"+${hormiga_total * 0.7:,.0f}/mes", priority=5,
            ),
            Recommendation(
                area="vida_social", title="Sigue viendo a tus amigos, cambia el plan",
                description=f"Las salidas sumaron ${outings:,.0f}. Propón el partido en casa con cooperacha o compartir un plato: la convivencia se queda, el gasto baja.",
                wellbeing_benefit="Tu gente es tu red de apoyo; aislarte para ahorrar sale más caro emocionalmente.",
                estimated_impact=f"+${outings / 2:,.0f}/mes", priority=6,
            ),
            Recommendation(
                area="movimiento", title="Camina los tramos cortos",
                description=f"Gastas ${transport:,.0f} en camión y gasolina. Sustituye los trayectos de menos de 2 km por caminata o bici.",
                wellbeing_benefit="30 minutos de caminata al día bajan el estrés y mejoran el sueño.",
                estimated_impact=f"+${transport * 0.3:,.0f}/mes y +30 min de actividad", priority=7,
            ),
            Recommendation(
                area="salud_preventiva", title="Atiende la causa, no solo el síntoma",
                description=f"Llevas ${health:,.0f} en farmacia este mes (analgésicos, medicamento). Agenda un chequeo gratuito en tu clínica del IMSS o centro de salud.",
                wellbeing_benefit="Detectar a tiempo evita un gasto grande y te da paz mental.",
                estimated_impact="Evita gastos médicos mayores", priority=8,
            ),
            Recommendation(
                area="ahorro", title="Aparta el sobrante el día de la nómina",
                description="Cuando un mes cierre en positivo, mueve el excedente a tu cuenta de Ahorro el mismo día que cae la quincena.",
                wellbeing_benefit="Un colchón de una renta es dormir tranquilo aunque algo falle.",
                estimated_impact="Colchón de 1 renta en ~6 meses", priority=9,
            ),
            Recommendation(
                area="integral", title="Alinea tus gastos fijos con tu vida",
                description="Tus pagos fijos más la comida fuera superan lo que ganas; sin bajar uno de los dos, ningún ajuste chico alcanza.",
                wellbeing_benefit="Vivir dentro de tu ingreso es la base de todo lo demás: salud, descanso y relaciones.",
                estimated_impact="Cierra el déficit estructural", priority=10,
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
