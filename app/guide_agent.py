"""
Agente Guía (capa cognitiva proactiva). Dos momentos del producto, dos
métodos separados en la misma clase:

- `generate_welcome`: el PRIMER mensaje que ve el usuario al abrir la app.
  Cambia de tono según el estado real (insolvencia próxima > quincena mañana
  con un gasto esencial sin apartar > todo bien) y, cuando toca, propone
  crear una Cajita para la renta/servicios antes de que se gaste ese dinero.
- `generate_withdrawal_warning`: cuando quiere sacar dinero de una Cajita
  antes de la fecha en que lo necesita. No bloquea (es su dinero): genera
  conciencia sobre la decisión.

Separado de CognitiveFinancialAgent (app/agent.py): aquel diagnostica y arma
el plan de rescate; este acompaña decisiones en el momento. Mismo patrón:
Gemini con Structured Outputs, pero el TONO, los MONTOS y las FECHAS los
decide Python antes del prompt — Gemini solo redacta y lo que devuelve se
vuelve a pisar con los números nuestros. Si Gemini falla o tarda hay respaldo
fijo: este agente nunca tira un 500 (si truena aquí, truena la demo desde el
segundo 1).
"""

from datetime import date

from google import genai
from google.genai import errors, types

from app.config import GEMINI_API_KEY
from app.schemas import (
    CajitaOut,
    CajitaProposal,
    EssentialExpense,
    ForecastMetrics,
    PaydayInfo,
    WelcomeMessage,
    WithdrawalWarning,
)

MODEL = "gemini-flash-lite-latest"

# Reglas de negocio del saludo (Python, no el LLM).
INSOLVENCY_ALERT_DAYS = 15  # insolvencia a ≤ 15 días manda sobre cualquier propuesta de cajita
PAYDAY_WINDOW_DAYS = 1  # se propone apartar cuando la nómina cae hoy o mañana
# Reglas de la advertencia de retiro.
HIGH_SEVERITY_DAYS = 7  # > 7 días de anticipación = high; 1-7 = medium; 0 = low

PERSONA = (
    "Eres el acompañante de bienestar integral de una persona de ingreso medio-bajo en "
    "México (montos en pesos mexicanos, MXN; nunca digas dólares). Sabes de finanzas, "
    "pero te importa cómo vive: menos ansiedad, más control, dormir tranquilo. Tono "
    "cercano y cálido, tuteando, sin culpa, sin sermones, sin frases motivacionales "
    "vacías. Concreto: usa los montos y fechas reales que te doy, no inventes otros."
)


def _fmt_date(d: date) -> str:
    return d.strftime("%d/%m")


class GuideAgent:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY no está configurada. Sácala gratis en "
                "aistudio.google.com/apikey y ponla en .env."
            )
        # Mismo criterio que CognitiveFinancialAgent: sin reintentos (503 del
        # tier gratis → respaldo de inmediato). Timeout más corto porque las
        # salidas son chicas (un saludo, una advertencia), no un plan de 10 puntos.
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=20_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    # ------------------------------------------------------------------ welcome

    def decide_welcome(
        self,
        forecast: ForecastMetrics,
        essential_expenses: list[EssentialExpense],
        payday: PaydayInfo,
        covered: set[str] | None = None,
    ) -> tuple[str, str, list[CajitaProposal]]:
        """
        Decide (situation, tone, proposals) con reglas, sin LLM. `covered` son
        los nombres de gastos que YA tienen una cajita activa para su próxima
        fecha (no se vuelven a proponer). Prioridad:
        1. insolvencia a ≤ INSOLVENCY_ALERT_DAYS → warning, sin propuestas (una
           alarma a la vez).
        2. nómina hoy/mañana y hay esencial sin cajita → warning + una propuesta
           por gasto pendiente (apartar el día que cae la nómina).
        3. insolvencia más lejana → neutral (aviso suave).
        4. todo bien → positive.
        """
        covered = covered or set()
        pending = [e for e in essential_expenses if e.name not in covered]

        if (
            forecast.insolvency_date is not None
            and forecast.days_remaining is not None
            and forecast.days_remaining <= INSOLVENCY_ALERT_DAYS
        ):
            return "insolvency", "warning", []

        if payday.days_until_payday <= PAYDAY_WINDOW_DAYS and pending:
            proposals = [
                CajitaProposal(
                    expense_name=e.name,
                    suggested_amount=e.amount,
                    reserve_by_date=payday.next_payday_date.isoformat(),
                    reasoning=(
                        f"{e.payee or e.name} se cobra el {_fmt_date(e.next_due_date)}; si lo apartas el "
                        f"{_fmt_date(payday.next_payday_date)} que cae la nómina, no te lo gastas sin querer."
                    ),
                    cta_label=f"Apartar ${e.amount:,.0f}",
                )
                for e in pending
            ]
            return "payday", "warning", proposals

        if forecast.insolvency_date is not None:
            return "watch", "neutral", []

        return "ok", "positive", []

    async def generate_welcome(
        self,
        forecast: ForecastMetrics,
        essential_expenses: list[EssentialExpense],
        payday: PaydayInfo,
        covered: set[str] | None = None,
        balance: float | None = None,
        today: date | None = None,
    ) -> tuple[WelcomeMessage, bool]:
        """Regresa (mensaje, exito). exito=False si se usó el respaldo — no cachearlo."""
        today = today or date.today()
        situation, tone, proposals = self.decide_welcome(forecast, essential_expenses, payday, covered)
        fallback = self._fallback_welcome(situation, tone, proposals, forecast, essential_expenses, payday)
        prompt = self._build_welcome_prompt(
            situation, tone, proposals, forecast, essential_expenses, payday, covered or set(), balance, today
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=WelcomeMessage,
                    # Sin thinking_config: ver nota en app/agent.py (400 con este modelo).
                ),
            )
            drafted: WelcomeMessage = response.parsed
        except errors.APIError as e:
            print(f"[guide] Gemini falló generando el saludo ({type(e).__name__}): {e}")
            return fallback, False
        except Exception as e:
            print(f"[guide] Error inesperado generando el saludo ({type(e).__name__}): {e}")
            return fallback, False

        if not drafted or not (drafted.greeting or "").strip():
            return fallback, False

        # Gemini redacta; los números, fechas y el tono son nuestros.
        merged_proposals: list[CajitaProposal] = []
        for i, ours in enumerate(proposals):
            theirs = drafted.cajita_proposals[i] if i < len(drafted.cajita_proposals) else None
            merged_proposals.append(
                CajitaProposal(
                    expense_name=ours.expense_name,
                    suggested_amount=ours.suggested_amount,
                    reserve_by_date=ours.reserve_by_date,
                    reasoning=(theirs.reasoning.strip() if theirs and theirs.reasoning.strip() else ours.reasoning),
                    cta_label=(theirs.cta_label.strip() if theirs and theirs.cta_label.strip() else ours.cta_label),
                )
            )
        return WelcomeMessage(greeting=drafted.greeting.strip(), tone=tone, cajita_proposals=merged_proposals), True

    def _build_welcome_prompt(
        self,
        situation: str,
        tone: str,
        proposals: list[CajitaProposal],
        forecast: ForecastMetrics,
        essential_expenses: list[EssentialExpense],
        payday: PaydayInfo,
        covered: set[str],
        balance: float | None,
        today: date,
    ) -> str:
        facts: list[str] = [f"Hoy es {today.isoformat()}."]
        if balance is not None:
            facts.append(f"Saldo disponible: ${balance:,.2f}.")
        facts.append(
            f"Próxima nómina: {payday.next_payday_date.isoformat()} (en {payday.days_until_payday} día(s)), "
            f"≈ ${payday.amount:,.0f}" + (" — fecha estimada, no confirmada." if payday.is_estimated else ".")
        )
        if forecast.insolvency_date:
            facts.append(
                f"Proyección: se queda sin saldo el {forecast.insolvency_date.isoformat()} "
                f"(en {forecast.days_remaining} días) si sigue igual."
            )
        else:
            facts.append("Proyección: no se queda sin saldo en los próximos 90 días.")
        if forecast.lowest_balance is not None and forecast.lowest_balance_date:
            facts.append(f"Punto más bajo proyectado: ${forecast.lowest_balance:,.0f} el {forecast.lowest_balance_date.isoformat()}.")

        essentials = (
            "\n".join(
                f"- {e.payee or e.name} ({e.category}): ${e.amount:,.0f}, próximo cobro {e.next_due_date.isoformat()}"
                + (" — YA tiene dinero apartado en una Cajita." if e.name in covered else "")
                for e in essential_expenses
            )
            or "- (no se detectaron gastos fijos esenciales)"
        )

        instructions = {
            "insolvency": (
                "SITUACIÓN: insolvencia próxima. Eso manda. greeting (2 frases, ≤ 45 palabras): saluda, di "
                "con claridad y sin dramatizar la fecha/días en que se queda sin saldo, y cierra con UNA "
                "frase que baje la ansiedad (hay margen de maniobra, el plan de rescate está en la app). "
                "No propongas cajitas ahora: una alarma a la vez. cajita_proposals: lista vacía."
            ),
            "payday": (
                "SITUACIÓN: la nómina cae hoy o mañana y hay gastos esenciales sin apartar. greeting (2 "
                "frases, ≤ 45 palabras): saluda cálido y explica que mañana/hoy entra la quincena y que "
                "es el mejor momento para apartar lo de esos gastos ANTES de que se diluya en el día a día. "
                "cajita_proposals: EXACTAMENTE " + str(len(proposals)) + ", en este orden y con estos datos "
                "fijos (no los cambies): "
                + "; ".join(
                    f"[{i + 1}] expense_name=\"{p.expense_name}\", suggested_amount={p.suggested_amount}, "
                    f"reserve_by_date=\"{p.reserve_by_date}\""
                    for i, p in enumerate(proposals)
                )
                + ". Para cada una redacta reasoning (1 frase concreta: cuándo se cobra, por qué apartarlo "
                "el día de la nómina, qué tranquilidad le da) y cta_label (≤ 5 palabras, imperativo, con el "
                "monto, p. ej. \"Apartar $7,000 para la renta\")."
            ),
            "watch": (
                "SITUACIÓN: sin urgencia hoy, pero la proyección se pone en negativo más adelante. greeting "
                "(2 frases, ≤ 40 palabras): saluda tranquilo, reconoce algo que hace bien, y menciona con "
                "suavidad la fecha proyectada como algo a vigilar, no como alarma. cajita_proposals: vacía."
            ),
            "ok": (
                "SITUACIÓN: todo en orden. greeting (1-2 frases, ≤ 35 palabras): saludo simple y humano, "
                "reconoce que va bien; sin consejos no pedidos, sin proponer nada. cajita_proposals: vacía."
            ),
        }[situation]

        return (
            f"{PERSONA}\n\n"
            f"## Datos\n" + "\n".join(facts) + "\n\n"
            f"## Gastos fijos esenciales\n{essentials}\n\n"
            f"## Qué generar\n{instructions}\n"
            f"tone: \"{tone}\" (ya está decidido; no lo cambies)."
        )

    def _fallback_welcome(
        self,
        situation: str,
        tone: str,
        proposals: list[CajitaProposal],
        forecast: ForecastMetrics,
        essential_expenses: list[EssentialExpense],
        payday: PaydayInfo,
    ) -> WelcomeMessage:
        """Saludo fijo por situación, con los números reales (sin LLM)."""
        if situation == "insolvency":
            greeting = (
                f"Hola. Ojo: si sigues igual, te quedas sin saldo el {_fmt_date(forecast.insolvency_date)} "
                f"(en {forecast.days_remaining} días). Hay margen para moverlo: tu plan de rescate está listo aquí abajo."
            )
        elif situation == "payday":
            names = ", ".join(p.expense_name.lower() for p in proposals)
            when = "hoy" if payday.days_until_payday <= 0 else "mañana"
            greeting = (
                f"Hola. {when.capitalize()} cae tu quincena: aprovecha ese momento para apartar lo de {names} "
                f"antes de que se vaya en el día a día."
            )
        elif situation == "watch":
            greeting = (
                f"Hola. Hoy vas bien; solo ten en el radar el {_fmt_date(forecast.insolvency_date)}, "
                f"que es donde la proyección se aprieta."
            )
        else:
            greeting = "Hola. Todo en orden por hoy: tus cuentas van bien y no hay nada urgente que atender."
        return WelcomeMessage(greeting=greeting, tone=tone, cajita_proposals=proposals)

    # --------------------------------------------------------------- withdrawal

    @staticmethod
    def severity_for(days_early: int) -> str:
        if days_early > HIGH_SEVERITY_DAYS:
            return "high"
        if days_early >= 1:
            return "medium"
        return "low"

    async def generate_withdrawal_warning(
        self,
        cajita: CajitaOut,
        days_early: int,
        today: date | None = None,
    ) -> tuple[WithdrawalWarning, bool]:
        """Regresa (advertencia, exito). Nunca bloquea: si Gemini falla, respaldo genérico."""
        today = today or date.today()
        severity = self.severity_for(days_early)
        requires_double = severity in ("medium", "high")
        fallback = self._fallback_withdrawal_warning(cajita, days_early, severity, requires_double)

        prompt = (
            f"{PERSONA}\n\n"
            "## Contexto\n"
            f"Hoy es {today.isoformat()}. La persona apartó ${cajita.target_amount:,.2f} en una Cajita llamada "
            f"\"{cajita.name}\" para pagar {cajita.linked_expense_name} el {cajita.reserve_date.isoformat()}. "
            f"Quiere sacar ese dinero HOY, {days_early} día(s) antes de esa fecha. Severidad ya decidida: {severity}.\n\n"
            "## Qué generar\n"
            "message: advertencia principal en tono de coach (2 frases, ≤ 40 palabras): recuérdale para qué "
            "era ese dinero y cuántos días faltan; sin regaño, sin prohibir — es su dinero y puede decidir.\n"
            "reminder: 1 frase corta de refuerzo: qué pasa si lo usa ahora (tendrá que cubrir ese pago con "
            "otro dinero que quizá no tenga).\n"
            f"days_early: {days_early}. severity: \"{severity}\". requires_double_confirmation: "
            f"{'true' if requires_double else 'false'}. (Estos tres ya están decididos; no los cambies.)"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=WithdrawalWarning,
                ),
            )
            drafted: WithdrawalWarning = response.parsed
        except errors.APIError as e:
            print(f"[guide] Gemini falló generando la advertencia ({type(e).__name__}): {e}")
            return fallback, False
        except Exception as e:
            print(f"[guide] Error inesperado generando la advertencia ({type(e).__name__}): {e}")
            return fallback, False

        if not drafted or not (drafted.message or "").strip():
            return fallback, False

        return (
            WithdrawalWarning(
                message=drafted.message.strip(),
                days_early=days_early,
                severity=severity,
                reminder=(drafted.reminder or "").strip() or fallback.reminder,
                requires_double_confirmation=requires_double,
            ),
            True,
        )

    def _fallback_withdrawal_warning(
        self, cajita: CajitaOut, days_early: int, severity: str, requires_double: bool
    ) -> WithdrawalWarning:
        return WithdrawalWarning(
            message=(
                f"Este dinero está reservado para {cajita.linked_expense_name} del "
                f"{_fmt_date(cajita.reserve_date)} — todavía faltan {days_early} días. Es tuyo y puedes usarlo, "
                f"pero vale la pena pensarlo dos veces."
            ),
            days_early=days_early,
            severity=severity,
            reminder=(
                f"Si lo usas ahora, vas a tener que cubrir {cajita.linked_expense_name} con otro dinero que quizá no tengas."
            ),
            requires_double_confirmation=requires_double,
        )
