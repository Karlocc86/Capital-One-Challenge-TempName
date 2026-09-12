# Estado del proyecto — Capital One Challenge, HackMTY 2026

_Última actualización: 12 de septiembre de 2026 (rama `perf/gemini-thinking-budget`, pendiente de commit)_

## Qué estamos construyendo

Track B2C. Un predictor de "¿llego a fin de mes?": proyecta el saldo futuro del usuario a partir de sus movimientos bancarios y, a diferencia de un simple aviso, **actúa** — propone acciones concretas de rescate. Usa la API de Nessie (Capital One) como fuente de datos bancarios simulados.

## Stack (actualizado — difiere de la idea original en un punto)

- Backend: FastAPI, Python 3.11+
- DB: **Postgres (Supabase), implementado** — cache de accounts/purchases/bills, con connection pooling.
- IA: `scikit-learn` (regresión lineal) para el forecast + **Gemini (`gemini-flash-lite-latest`, Google)**, no Claude — cambio de proveedor por costo: Anthropic no tiene tier gratis y Gemini sí.
- Frontend: Next.js 14 + Tailwind — scaffold provisional funcionando, todavía sin conectar a `/forecast`.
- Datos: Nessie API (api.nessieisreal.com) vía HTTPS (puerto 80 bloqueado en la red del hackathon).

## Arquitectura actual (ya implementada, no solo objetivo)

Nessie API → `nessie_client.py` (único módulo HTTP) → `cache.py` (sync_snapshot + lecturas cache-first) → Postgres (accounts_cache/purchases_cache/bills_cache) → `forecaster.py` (regresión sklearn) → `agent.py` (Gemini, Structured Outputs) → `GET /forecast/{account_id}` → `{"data": {...}, "meta": {...}}`.

Reglas duras que se mantienen: el frontend nunca llama a Nessie directamente; `nessie_client.py` no tiene lógica de negocio; ningún endpoint llama a Nessie en vivo si ya hay snapshot en Postgres.

## Progreso: BACKEND.md Fases 1-5 completas

`BACKEND.md` (el roadmap detallado del backend, escrito aparte de `CLAUDE.md`) define 5 fases con checkpoints obligatorios. Las 5 están hechas y verificadas contra servicios reales (Nessie, Supabase, Gemini) — nada mockeado.

**Fase 1 — Cimientos: Nessie + Cache Postgres, DONE**
- `app/db.py` (connection pool a Supabase), `app/cache.py` (`sync_snapshot`, `get_account/get_purchases/get_bills` cache-first), `scripts/init_db.py`, `scripts/sync.py`.
- Checkpoint 1 (ajustado): con `NESSIE_BASE_URL` apuntando a un host inválido, los endpoints siguen respondiendo el dato real 100% desde Postgres.

**Fase 2 — Capa Cuantitativa: `FinancialForecaster`, DONE**
- `app/forecaster.py`: convierte purchases a serie diaria acumulada, regresión lineal (sklearn) → `burn_rate_daily`; bills recurrentes se suman como gasto diario equivalente; guardia si hay <2 días de datos.
- Checkpoint 2: datos normales, 1 dato, 0 datos — los 3 responden sin excepción (`scripts/test_forecaster.py`).

**Fase 3 — Capa Cognitiva: `CognitiveFinancialAgent`, DONE (con Gemini, no Claude)**
- `app/agent.py`: Structured Outputs (`response_schema=FinancialRescuePlan`) contra Gemini. `generate_rescue_plan` regresa `(plan, exito)` — `exito=False` cuando se usó el plan de respaldo, para que el llamador nunca cachee un fallback.
- Se descubrió que el tier gratis de Gemini **sí falla con cierta frecuencia** (503 "alta demanda", 504 timeout, y hasta un 429 de cuota diaria agotada) — se configuró `attempts=1` + `timeout=10s` en el cliente para fallar rápido al respaldo en vez de esperar ~30s de reintentos por default del SDK.
- Checkpoint 3: los 3 casos de Fase 2 + un 4to caso con key inválida — los 4 devuelven un `FinancialRescuePlan` válido (`scripts/test_agent.py`).
- **En curso (rama `perf/gemini-thinking-budget`, sin commitear)**: se agregó `thinking_config=types.ThinkingConfig(thinking_budget=0)` en `agent.py`. Los modelos 2.5 de Gemini razonan ("thinking") antes de responder por default, lo cual suma latencia sin aportar nada al output ya forzado por `response_schema`; `flash-lite` permite desactivarlo. Objetivo: recortar los ~10-13s de la primera llamada (ver Fase 5). Falta medir el impacto real y correr `scripts/test_agent.py` con el cambio antes de dar por cerrado.

**Fase 4 — Orquestador `/forecast/{account_id}`, DONE**
- Pipeline completo en `app/main.py`: ingesta (cache) → cuantitativa → cognitiva → respuesta envuelta. Try/except: errores de Nessie → 404, cualquier otra falla → 500 genérico. Logs por etapa.
- **Bug real encontrado y arreglado en el camino**: `db.py` abría una conexión TCP nueva a Supabase por query, sin cerrarla — `/forecast` tardaba 15s. Con connection pooling bajó a ~1-2s de cache + la latencia inherente de Gemini (~6-11s). El requisito de <3s de BACKEND.md se aceptó como no aplicable a la parte de LLM (se escribió antes de que existiera la llamada a Gemini).

**Fase 5 — Blindaje para demo, DONE**
- Confirmado: ningún endpoint toca Nessie en vivo si hay snapshot (probado con Nessie bloqueado, tanto en `/summary` como en `/forecast`).
- account_id demo congelado vía variable de entorno (`web/.env.local`), sin flujo de login.
- 5 requests seguidas a `/forecast`: sin fugas de conexión (tiempos estables), aunque sí se encontró rate limiting real de Gemini (ver abajo).
- `fixtures/forecast_ricardo_torres_backup.json`: respuesta real capturada de `/forecast`, lista para servir manualmente si todo falla en vivo (ver `fixtures/README.md`).
- **Nuevo: cache del `rescue_plan` en Postgres** (`rescue_plans_cache`, funciones `get_cached_rescue_plan`/`save_rescue_plan` en `cache.py`). `GET /forecast/{account_id}` solo llama a Gemini si no hay plan cacheado (o si se pasa `?force_refresh=true`); solo se cachean planes generados de verdad (`exito=True`), nunca el fallback. Primera llamada real ~10-13s, llamadas repetidas **~2s**. Esto es crítico para la demo: permite "calentar" el cache antes de salir a presentar y que el pitch en vivo sea instantáneo.

## Persona demo (cambiada, con base real)

El customer demo dejó de ser "Demo HackMTY" genérico. Ahora es **"Ricardo Torres"**, un perfil calibrado con datos reales del **INEGI (ENIGH 2024, decil III de ingreso)**: ~$12,282 MXN/mes de ingreso, balance en cuenta $3,200 MXN, bills de Renta ($3,500), Servicios ($450) y **un pago recurrente a una casa de empeño/préstamo personal ($800)** — la señal de vulnerabilidad financiera que el pitch quiere mostrar que el modelo detecta. Con este perfil, el forecast proyecta insolvencia en **13 días**, no 33 — mucho más urgente y defendible frente a un jurado.

Fuente citable: [ENIGH 2024, INEGI](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/enigh/ENIGH2024_RR.pdf).

`account_id` demo actual: `e8f0c102-eb26-4baf-ad78-629cc03c4d74` (reemplazó al anterior `fea9ad73-...`, ya actualizado en todos los scripts y en `web/.env.local`). La cuenta vieja "Demo HackMTY" quedó huérfana en Nessie, sin usarse — no se borró, es inofensiva.

## Bugs/decisiones técnicas descubiertas (importante para el pitch/documentación)

1. **Puerto 80 (HTTP) bloqueado en la red del hackathon** — se usa HTTPS contra Nessie.
2. **`merchant.category` debe ser un string**, no una lista.
3. **`purchase.status` es requerido en el POST** aunque no está documentado — si falta, el GET truena al leer.
4. **Conexiones Postgres sin pool eran el cuello de botella real de latencia** (15s → ~2s) — no el LLM.
5. **Gemini `gemini-2.5-flash` dejó de estar disponible para keys nuevas** a mitad de desarrollo (404, "no longer available to new users").
6. **`gemini-3.6-flash` tiene un límite de cuota gratis de solo 20 requests/día** — se agotó durante las pruebas de este mismo día. Se cambió a **`gemini-flash-lite-latest`** (cuota separada, y es un alias que Google mantiene apuntando al modelo lite vigente, para no repetir el problema del punto 5).
7. **El tier gratis de Gemini tiene fallos reales de disponibilidad** (429 cuota, 503 alta demanda, 504 timeout) — confirmado en vivo durante las pruebas, no es un escenario hipotético. El fallback, el timeout corto de 10s, y el cache de Fase 5 existen porque de verdad hacen falta.

## Convenciones que se están respetando

- Toda respuesta de FastAPI va envuelta en `{"data": ..., "meta": {...}}`.
- Un solo `customer_id`/`account_id` demo fijo, sin autenticación real.
- `nessie_client.py` sin lógica de negocio; `cache.py` orquesta pero no hace requests HTTP directos.
- Secretos (`.env`, `web/.env.local`) fuera de git.

## Pendiente / próximo paso

1. **Cerrar `perf/gemini-thinking-budget`**: confirmar que `thinking_budget=0` no rompe `scripts/test_agent.py`, medir la latencia real de la primera llamada (antes vs. después) y hacer commit/push/PR.
2. El frontend (Paso 3 original) **todavía no está conectado a `/forecast`** — solo muestra `/summary` (balance + gasto total, sin IA). Conectar la UI al forecast + rescue plan es el siguiente "momento de valor" visual para el pitch.
3. `/actions` (bloquear categoría, mover a ahorro) mencionado en la idea original y en `CLAUDE.md` **no está en BACKEND.md ni implementado todavía** — pendiente decidir si entra al alcance antes del pitch.
4. Diseño real de frontend: sigue pendiente, el actual es solo funcional.

## Importante para el día del pitch

**Calienta el cache antes de salir al escenario**: haz una sola llamada a `GET /forecast/{account_id}` (o abre el frontend una vez, cuando esté conectado) unos minutos antes de presentar. Eso guarda el plan de rescate en Postgres, y durante la demo en vivo la respuesta será de ~2 segundos en vez de 10-13. Si necesitas forzar un plan nuevo (por ejemplo, después de cambiar el prompt), usa `?force_refresh=true`.
