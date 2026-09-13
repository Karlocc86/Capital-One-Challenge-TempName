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

El customer demo dejó de ser "Demo HackMTY" genérico. Ahora es **"Ricardo Torres"**, un perfil calibrado con datos reales del **INEGI (ENIGH 2024, decil III de ingreso)**: ~$12,282 MXN/mes de ingreso, balance en cuenta $3,200 MXN, bills de Renta ($7,000), Servicios ($650) y **7 suscripciones prescindibles** (streaming, gym, videojuegos, ~$1,533/mes) — un patrón de vulnerabilidad muy común y con una salida obvia que el agente puede ejecutar: cancelar. Con este perfil, el forecast proyecta insolvencia en **10 días**, dos días antes de la quincena.

Fuente citable: [ENIGH 2024, INEGI](https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/enigh/ENIGH2024_RR.pdf).

`account_id` demo actual: **`0ce1d6a3-551f-420f-af8a-62971a612f0f`** ("Cuenta de Cheques"). Vive en `.env` (`DEMO_ACCOUNT_ID`, lo leen los scripts de prueba vía `app/config.py`) y en `web/.env.local` (`NEXT_PUBLIC_DEMO_ACCOUNT_ID`). La cuenta anterior `e8f0c102-…` ("Cuenta Principal", 15 compras aleatorias) **se borró de Nessie** porque era del mismo customer y aparecía en `/accounts`.

## Dataset demo determinista (recalibrado 2026-09-12, egresos > ingresos)

El seed dejó de ser aleatorio. `app/demo_data.py` es la fuente de verdad y `scripts/seed.py` lo siembra en Nessie:

- **2 cuentas**: Checking "Cuenta de Cheques" (saldo inicial **$5,170**) y Savings "Ahorro" ($500, base para la acción "mover a ahorro").
- **9 merchants de Monterrey** (OXXO, Soriana Híper, Pemex, Camión Urbano MTY, Tacos El Güero, **Las Alitas**, Telcel, Farmacias Guadalajara, Coppel). La `category` del merchant en Nessie es la etiqueta base de la UI; `app/categories.py` la refina por palabra clave: alitas/tacos/botana/refresco → **"Comida chatarra"** aunque el comercio sea OXXO. El seed actualiza la category en Nessie si cambia en el dataset (`PUT /merchants/{id}` sí persiste).
- **35 purchases** con día relativo a hoy, monto y descripción fijos (total **$5,903.50** / 30 días ≈ 48 % del ingreso). De eso, **comida chatarra ≈ $2,132** en 12 compras (Las Alitas $1,257 en 3 visitas, Tacos El Güero $606, botanas/refrescos OXXO) y **gastos hormiga ≈ $517 en 9 visitas al OXXO** (compras < $150 en tiendas/súper según la categoría del comercio; los tacos no cuentan como hormiga para no duplicar con chatarra).
- **2 depósitos de nómina** ($6,141 c/u, hace 18 y 3 días = $12,282/mes). El forecaster infiere la siguiente quincena en 12 días.
- **9 bills** ($9,183/mes): Renta 7,000 día 1 · CFE e Internet 650 día 15 · y **7 suscripciones prescindibles** ($1,533/mes, categoría "Suscripciones", `discretionary: true` en `/bills`): Netflix 249 (día 8), HBO Max 149 (12), Disney+ 179 (3), Spotify 129 (20), Amazon Prime 99 (18), Xbox Game Pass 229 (22), Smart Fit 499 (7). `DISCRETIONARY_BILLS` en `demo_data.py` es la base para la acción "cancelar suscripción".
- **Egresos mensuales $15,087 > ingresos $12,282**: déficit estructural **$2,805/mes**. Saldo hoy $2,365.50 → **insolvencia el día 9 (21 sep, tres días ANTES de la quincena)**; la renta del día 1 lo manda a ~−$3,000; `month_end`: NO llega a fin de mes. `scripts/test_forecaster.py` asegura `10 <= days_remaining <= 16`.

Idempotencia: customer/cuentas/merchants/bills por nombre; purchases/deposits por `(fecha, parte entera del monto, descripción)`. **Las fechas son relativas al día del seed**: si se detectan movimientos de otro día el seed se detiene y pide `python scripts/seed.py --reset`. Como **Nessie no permite borrar ni editar purchases** (todas las rutas `/purchases/{id}` responden 403) ni cambiar `balance` (el PUT lo ignora), `--reset` **borra y recrea la cuenta de cheques** (nuevo `account_id`) y reescribe `DEMO_ACCOUNT_ID` en `.env` y `NEXT_PUBLIC_DEMO_ACCOUNT_ID` en `web/.env.local`. Después: `python scripts/sync.py <id>` y reiniciar backend y `pnpm dev`.

### Saldo y proyección (2026-09-12)

- **`app/ledger.py`** — Nessie no mueve `account.balance` con deposits/purchases, así que el saldo se reconstruye: `saldo = saldo inicial + Σ depósitos − Σ compras − Σ bills ya cobradas` (una ocurrencia por bill entre el primer movimiento e hoy). El saldo inicial de la cuenta demo viene de `DEMO_CHECKING_BALANCE` (Nessie no deja cambiarlo). Lo usan `/summary`, `/accounts` y `/forecast`.
- **`app/forecaster.py` reescrito**: proyección **día a día a 90 días** — gasto variable = pendiente de la regresión lineal (sklearn) sobre compras acumuladas; **bills como cargos puntuales en su `recurring_date`** (la renta pega de golpe el día 1); **quincenas futuras inferidas del historial de depósitos** (intervalo mediano + monto). Insolvencia = primer día con saldo negativo. `ForecastMetrics` ahora trae también `next_paycheck_date`, `paycheck_amount`, `lowest_balance(_date)` y `projection[]` (fecha, saldo, eventos del día) para graficar.
- **Plan de rescate estructurado por áreas, enfoque de bienestar integral** (`schemas.FinancialRescuePlan`): la persona del agente ya no es "asesor financiero" sino acompañante de bienestar (tono cercano, tuteo, sin culpa; el dinero es el medio, el bienestar el fin). `summary`, `insolvency_warning` y `recommendations[]` — **exactamente 10, una por área**: `paso_de_hoy` (una acción chica para hoy contra la ansiedad), `fin_de_mes`, `suscripciones` (+ descanso/pantallas), `comida_chatarra` (+ salud), `gastos_hormiga` (+ hábitos), `vida_social` (no aislarse: convivir gastando menos), `movimiento` (transporte → caminar/bici), `salud_preventiva` (farmacia recurrente → chequeo IMSS), `ahorro` (colchón = tranquilidad), `integral`. Cada una: `title`, `description` (montos y nombres reales), **`wellbeing_benefit`** (qué gana en salud/descanso/relaciones/tranquilidad), `estimated_impact`, `priority` (1-10). `categories.spending_breakdown` aporta además transporte, farmacia y salidas sociales. Timeout de Gemini subido a 40 s (el plan tarda ~10-25 s; se cachea). Los números vienen del backend: `forecast.month_end` (`MonthEndAnalysis`: ingreso vs egreso mensual, déficit, saldo proyectado al 30, ¿llega?) y `categories.spending_breakdown` (totales de chatarra / hormiga / suscripciones); Gemini solo redacta. El fallback sin LLM produce las mismas 6 áreas con los números reales. `web/components/ForecastCard.tsx` ya pinta esta lista (aún sin montar en el dashboard).

### Endpoints de lectura para la UI (nuevos)

Todos `{"data", "meta"}`, `meta.currency = "MXN"`, fechas ISO, montos positivos + `direction: "in"|"out"`. `initial`/color del badge se derivan en el frontend (del nombre del merchant / la categoría).

- `GET /accounts/{account_id}` → cuentas del customer (sidebar): `nickname, type, balance, account_number_masked ("•••• 8601"), is_current`.
- `GET /transactions/{account_id}?limit=20&type=all|purchase|deposit` → purchases + deposits mezclados DESC: `id, type, direction, amount, date, merchant, category, description, status`. Los depósitos salen como merchant "Nómina - Maquilas del Norte SA de CV", categoría "Ingresos".
- `GET /bills/{account_id}` → bills con `next_payment_date`, `days_until`, `category` (Vivienda / Servicios y facturas / Deuda); `meta.monthly_total`.
- `GET /summary/{account_id}` extendido (compatible): agrega `account_number_masked, money_in, money_out, deposit_count, money_in_goal (12,282), bills_monthly_total`; `meta.period` = **ventana móvil de 30 días** (no mes calendario, porque el seed es relativo a hoy).
- `GET /purchases/{account_id}` → **todas** las compras con comercio/categoría + `merchants` (resumen por comercio: `total_spent`, `purchase_count`); `meta.total_spent`.
- `GET /merchants` → catálogo completo de comercios con categoría.
- CreditWise no tiene fuente en Nessie → sigue estático en el frontend.

Fixtures de los 5 endpoints en `/fixtures` (ver su README).

## Bugs/decisiones técnicas descubiertas (importante para el pitch/documentación)

1. **Puerto 80 (HTTP) bloqueado en la red del hackathon** — se usa HTTPS contra Nessie.
2. **`merchant.category` debe ser un string**, no una lista.
3. **`purchase.status` es requerido en el POST** aunque no está documentado — si falta, el GET truena al leer.
4. **Conexiones Postgres sin pool eran el cuello de botella real de latencia** (15s → ~2s) — no el LLM.
5. **Gemini `gemini-2.5-flash` dejó de estar disponible para keys nuevas** a mitad de desarrollo (404, "no longer available to new users").
6. **`gemini-3.6-flash` tiene un límite de cuota gratis de solo 20 requests/día** — se agotó durante las pruebas de este mismo día. Se cambió a **`gemini-flash-lite-latest`** (cuota separada, y es un alias que Google mantiene apuntando al modelo lite vigente, para no repetir el problema del punto 5).
7. **El tier gratis de Gemini tiene fallos reales de disponibilidad** (429 cuota, 503 alta demanda, 504 timeout) — confirmado en vivo durante las pruebas, no es un escenario hipotético. El fallback, el timeout corto de 10s, y el cache de Fase 5 existen porque de verdad hacen falta.
8. **Nessie devuelve los montos de purchases/deposits sin decimales** (se manda 348.60, el GET regresa 348). Por eso `app/demo_data.py` guarda los montos reales y `cache.sync_snapshot` los restaura al escribir en Postgres (`raw` conserva lo que dijo Nessie). Los cálculos y la UI usan los montos con centavos.
9. **Deposits NO modifican `account.balance` en Nessie** (igual que las purchases): el balance es un número fijo que se setea al crear la cuenta. Verificado con un deposit de prueba antes de sembrar.
10. **`GET /accounts/{id}/transfers` devuelve 404 cuando la lista está vacía** (`/deposits` devuelve `[]`). `nessie_client._get_list` convierte ese 404 en `[]`.
11. **`thinking_config=ThinkingConfig(thinking_budget=0)` (PR #6) ya no lo acepta `gemini-flash-lite-latest`**: todas las llamadas daban `400 INVALID_ARGUMENT` y el forecast caía siempre al fallback. Se quitó el parámetro (2026-09-12); el plan real volvió a generarse. El alias apunta ahora a un modelo que no permite apagar el thinking.
12. **Bug preexistente en `cache.py`**: si el sync fallaba dentro de un `get_*`, la conexión se devolvía al pool dos veces (`PoolError: trying to put unkeyed connection`) y tapaba el error real. Ahora `_ensure_snapshot` corre antes de tomar la conexión de lectura.

## Convenciones que se están respetando

- Toda respuesta de FastAPI va envuelta en `{"data": ..., "meta": {...}}`.
- Un solo `customer_id`/`account_id` demo fijo, sin autenticación real.
- `nessie_client.py` sin lógica de negocio; `cache.py` orquesta pero no hace requests HTTP directos.
- Secretos (`.env`, `web/.env.local`) fuera de git.

## Pendiente / próximo paso

1. ~~Cerrar `perf/gemini-thinking-budget`~~ → el `thinking_budget=0` se revirtió (ver bug 11); la rama ya no aplica.
2. **Dashboard `/` conectado al backend (2026-09-12)** vía `web/lib/api.ts` (fetchers tipados + formato es-MX/MXN + badge por categoría): Mi Balance ← `/summary.balance` · Transacciones recientes ← `/purchases` (7 más recientes) · Próximas ← `/bills` · Ingresos ← `/summary.money_in` de `money_in_goal` (= `DEMO_MONTHLY_INCOME`) · Egresos ← `/summary.total_spent`. `mockData.ts` solo conserva `creditWise`. "Ver todo" lleva a `/transacciones` (todas las compras, filtro por categoría, desglose por comercio) y `/proximas` (pagos programados con "en N días" y saldo después de pagos). Se quitaron los menús "···" de todas las tarjetas (`CardMenu.tsx` eliminado). Layout a **pantalla completa** (`AppShell`): header sticky, sidebar sticky a toda la altura y lienzo `brand-canvas` cubriendo todo el viewport (sin la "isla" redondeada con margen); `body` usa el mismo azul para que no haya franjas. **Pendiente**: montar `ForecastCard` (`/forecast`, el "momento de valor") en el dashboard — ahora `forecast.projection[]` permite graficar el saldo día a día con los eventos (nómina, renta) marcados; las 4 páginas nuevas (`/ahorros`, `/tarjetas-de-credito`, `/prestamos`, `/recompensas`) siguen formateando en USD y pegan a Nessie en vivo (no pasan por cache) — necesitan `NEXT_PUBLIC_DEMO_CUSTOMER_ID` en `web/.env.local`.
3. **Prompt del agente**: `get_purchases` ya devuelve `merchant_name` y `category`; `agent._build_prompt` todavía manda solo `description`. Cambiar a `"- {date}: {merchant_name} [{category}] (${amount})"` y agregar una línea con los ingresos de los últimos 30 días. Requiere `?force_refresh=true` y regenerar el fixture.
4. ~~Recalibrar la narrativa~~ → hecho (dataset con egresos > ingresos, insolvencia el día 11).
5. ~~El forecaster ignora la nómina~~ → hecho (quincenas inferidas + bills puntuales, proyección día a día).
6. `/actions` (bloquear categoría, mover a ahorro) **no está implementado todavía**. Ya existe la base: cuenta Savings sembrada y `nessie_client.create_transfer` (Checking → Savings). CORS solo permite `GET`; habrá que abrir `POST`.
7. Diseño real de frontend: sigue pendiente, el actual es solo funcional.

## Importante para el día del pitch

**Resiembra relativo a hoy**: `python scripts/seed.py --reset` (recrea la cuenta y actualiza `.env` + `web/.env.local` solo) → `python scripts/sync.py <id nuevo>` → reiniciar `uvicorn` y `pnpm dev`. Las fechas del dataset son relativas al día del seed; sin esto la quincena inferida y los días a la insolvencia se corren.

**Calienta el cache antes de salir al escenario**: haz una sola llamada a `GET /forecast/{account_id}` (o abre el frontend una vez, cuando esté conectado) unos minutos antes de presentar. Eso guarda el plan de rescate en Postgres, y durante la demo en vivo la respuesta será de ~2 segundos en vez de 10-13. Si necesitas forzar un plan nuevo (por ejemplo, después de cambiar el prompt), usa `?force_refresh=true`.
