TODO Backend — Capital One Challenge (HackMTY 2026)
Solo tú, solo backend. Orden real de dependencias, no orden "bonito".

Regla de oro: no avances de fase sin marcar el checkpoint de la fase anterior. Si algo falla, es mejor detectarlo en la Fase 1 que en la Fase 5, 4 horas antes del pitch.

FASE 1 — Cimientos: Nessie + Cache (nada de IA todavía)
nessie_client.py con funciones: get_account, get_purchases, get_bills, get_merchants (ya deberías tener esto del scaffold inicial — si no, es lo primero).
Tabla(s) en Supabase/Postgres para la instantánea/snapshot de Nessie: accounts_cache, purchases_cache, bills_cache (o una sola tabla JSONB si quieres ir rápido).
Script/función sync_snapshot(account_id) que llama a Nessie UNA vez y guarda todo en Postgres.
Modifica nessie_client (o crea una capa encima) para que siempre lea de Postgres primero, y solo pegue a Nessie si no hay snapshot o si tú lo fuerzas manualmente.
Checkpoint 1: corre sync_snapshot con tu customer demo, apaga tu wifi, y confirma que puedes seguir leyendo los datos desde Postgres. Si esto no funciona, no sigas — es tu seguro de vida para la demo.
FASE 2 — Capa Cuantitativa: FinancialForecaster
Clase FinancialForecaster(current_balance, purchases, bills).
Convierte purchases (lista de compras puntuales) a serie de tiempo diaria con pandas.resample('D').
Aplica forward fill para rellenar días sin compras (no dejar NaN entre eventos).
Ajusta una Regresión Lineal Ordinaria sobre esa serie para obtener el burn rate diario.
Con el burn rate + current_balance, despeja la fecha de insolvencia (día en que el saldo proyectado llega a cero).
Método calculate_forecast() que regresa un objeto Pydantic (ej. ForecastMetrics) con: burn_rate_daily, insolvency_date, days_remaining, confidence (opcional).
Guardia defensiva obligatoria: if len(df) < 2: return estado_neutro — sin esto, sklearn truena con pocos datos y te tira un 500 en vivo.
Checkpoint 2: prueba calculate_forecast() con (a) datos normales, (b) 1 solo dato, (c) 0 datos. Los tres casos deben responder sin excepción.
FASE 3 — Capa Cognitiva: CognitiveFinancialAgent
Clase CognitiveFinancialAgent usando AsyncAnthropic (no el cliente síncrono — bloquearía el event loop de FastAPI).
Define el schema Pydantic FinancialRescuePlan (ej. summary, insolvency_warning, recommended_actions: list[Action], cada Action con description, estimated_impact).
Usa Structured Outputs de Anthropic inyectando ese schema — esto es lo que garantiza JSON válido siempre, sin parsear texto libre ni rezar por el formato.
Método generate_rescue_plan(forecast, purchases, merchants) que arma el prompt con el resultado de la Fase 2 + las compras/comercios, y regresa el FinancialRescuePlan ya validado.
Manejo de error explícito: si la llamada a Claude falla (timeout, rate limit), regresa un plan de rescate genérico de respaldo, NO un 500.
Checkpoint 3: llama al agente con el forecast de Checkpoint 2 (los 3 casos) y confirma que siempre regresa un FinancialRescuePlan válido, incluso en el caso "sin datos".
FASE 4 — Orquestador: endpoint /forecast/{account_id}
Implementa el router tal cual el patrón que ya tienes: Ingesta (desde cache, Fase 1) → Capa Cuantitativa (Fase 2) → Capa Cognitiva (Fase 3) → retorno {"data": {...}, "meta": {...}}.
Try/except general en el endpoint: cualquier excepción no controlada devuelve 500 con mensaje genérico (no expongas el stack trace al frontend).
Log interno (print o logger) de cada paso del pipeline — cuando el frontend te diga "no carga", necesitas saber en qué capa se rompió sin adivinar.
Checkpoint 4: pega el endpoint completo con Postman/curl/Thunder Client, no solo con el frontend. Debe responder <3 segundos con datos cacheados.
FASE 5 — Blindaje para la demo (esto es lo que te salva en vivo)
Confirma que ningún endpoint llama a Nessie en tiempo real durante la demo — todo pasa por Postgres cache (Fase 1).
Congela/hardcodea el account_id del usuario demo (Sofía) en una constante o variable de entorno, para que el frontend no dependa de un flujo de login.
Corre /forecast/{account_id} 5 veces seguidas rápido — confirma que no hay rate limiting inesperado de Anthropic ni fugas de conexión a Postgres.
Prueba el escenario de "Nessie caído": desconecta el acceso a Nessie por completo y confirma que /forecast sigue funcionando 100% desde cache.
Ten un JSON de respaldo estático del /forecast ya generado, listo para servir manualmente si algo truena a la hora del pitch (último recurso, no lo uses si no hace falta).
Checkpoint 5 (final): corre el flujo completo de principio a fin, cronometrado, simulando exactamente lo que el frontend hará en la demo real.
