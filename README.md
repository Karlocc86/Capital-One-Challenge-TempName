# Predictor "¿Llego a fin de mes?" — Capital One Challenge, HackMTY 2026

Track B2C. Proyecta el saldo futuro del usuario a partir de sus movimientos bancarios y, a diferencia de un simple aviso, **actúa**: propone un plan de rescate concreto (bloquear una categoría de gasto, mover dinero a un "ahorro") usando la API de Nessie (Capital One) como fuente de datos bancarios simulados.

> Estado actual, avances por fase y pendientes: ver [STATUS.md](STATUS.md).

## Qué hace

1. Siembra (`scripts/seed.py`, dataset fijo en `app/demo_data.py`) un customer demo en Nessie con cuenta de cheques y de ahorro, 8 comercios de Monterrey con categoría, 26 compras, 2 depósitos de nómina y bills recurrentes, calibrado con datos reales del INEGI (ENIGH 2024) para que el escenario de riesgo financiero sea creíble.
2. El backend cachea ese snapshot en Postgres (nunca depende de una llamada en vivo a Nessie durante la demo).
3. `FinancialForecaster` proyecta el saldo **día a día** a 90 días: gasto variable por regresión lineal (`scikit-learn`), bills como cargos puntuales en su fecha y quincenas futuras inferidas de los depósitos. La insolvencia es el primer día con saldo negativo.
4. `CognitiveFinancialAgent` (Gemini, Structured Outputs) traduce ese forecast en un plan de rescate en lenguaje natural con acciones concretas.
5. `GET /forecast/{account_id}` expone ambas capas ya combinadas; el resultado del plan de rescate se cachea en Postgres para que la demo en vivo responda en ~2s.

## Qué muestra la interfaz hoy

El frontend (`/web`) es un dashboard estilo banca (header, sidebar de cuentas, CreditWise) con:

- **Balance general** de la cuenta (saldo, número de cuenta enmascarado).
- **Transacciones recientes y próximas** con categoría, monto y comercio.
- **Gastos**: barras de ingresos vs. egresos contra una meta.
- **Funciones bancarias** (enviar dinero, transferir, bloquear tarjeta, estados de cuenta) y un bubble de asistente flotante.

⚠️ Ahora mismo esta UI corre sobre datos mock (`web/lib/mockData.ts`), **todavía no está conectada a `/forecast`**.

## Qué mostrará (próximo paso)

- El dashboard conectado a `GET /forecast/{account_id}`: el forecast real (días restantes, fecha de insolvencia) y el plan de rescate generado por Gemini, en vez de las tarjetas con datos mock.
- Acciones ejecutables desde la UI (`/actions`, aún no implementado en el backend): bloquear una categoría de gasto o mover dinero a un "ahorro" simulado dentro de Nessie.

## Stack

- **Backend**: FastAPI, Python 3.11+
- **DB**: Postgres (Supabase) — cache de accounts/purchases/bills/rescue_plans
- **IA**: `scikit-learn` (regresión lineal) para el forecast + Gemini (`gemini-flash-lite-latest`) para el plan de rescate en lenguaje natural
- **Frontend**: Next.js 14 + Tailwind (`/web`)
- **Datos**: [Nessie API](http://api.nessieisreal.com) de Capital One

## Arquitectura

```
Nessie API → nessie_client.py → cache.py (Postgres) → forecaster.py (sklearn) → agent.py (Gemini) → /forecast/{account_id} → Next.js
```

El frontend nunca llama a Nessie directamente; todo pasa por el backend. Detalle completo del roadmap de backend en [BACKEND.md](BACKEND.md).

## Cómo correr el proyecto

### Backend (FastAPI, puerto 8000)

```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # completar API keys: Nessie, Postgres (Supabase), Gemini
python scripts/init_db.py
python scripts/seed.py              # imprime el account_id demo → ponlo en .env (DEMO_ACCOUNT_ID) y web/.env.local
python scripts/sync.py <account_id> # Nessie → Postgres
python scripts/test_connection.py   # debe imprimir el customer demo y su balance
uvicorn app.main:app --reload --port 8000
```

Las fechas del dataset son relativas al día del seed: la mañana del pitch corre `python scripts/seed.py --reset` (recrea la cuenta y actualiza `.env`/`web/.env.local`), luego `python scripts/sync.py <account_id nuevo>` y reinicia backend y frontend.

Endpoints disponibles (todos `{"data", "meta"}`, montos en MXN):

- `GET /health`
- `GET /summary/{account_id}` — saldo disponible calculado (inicial + depósitos − compras − bills cobradas), gasto total, ingresos/egresos de los últimos 30 días
- `GET /accounts/{account_id}` — cuentas del customer (Cheques, Ahorro) con número enmascarado
- `GET /transactions/{account_id}?limit=20&type=all|purchase|deposit` — compras + depósitos con comercio y categoría
- `GET /purchases/{account_id}` — todas las compras con comercio + resumen por comercio
- `GET /merchants` — catálogo de comercios con categoría
- `GET /bills/{account_id}` — bills recurrentes con próxima fecha de cobro
- `GET /forecast/{account_id}` — proyección día a día (90 días), días a la insolvencia, próxima nómina + plan de rescate (agrega `?force_refresh=true` para regenerar el plan en vez de usar el cacheado)

### Frontend (Next.js, puerto 3000)

```bash
cd web
pnpm install
cp .env.local.example .env.local   # completar la URL del backend y el account_id demo
pnpm dev
```

Abre [http://localhost:3000](http://localhost:3000).

## Estructura

```
app/            backend FastAPI (nessie_client, cache, forecaster, agent, main)
scripts/        seed, init_db, sync y tests manuales de cada capa
fixtures/       respaldo estático de cada endpoint para la demo si algo falla en vivo
web/            frontend Next.js (dashboard, hoy con datos mock — ver "Qué muestra la interfaz hoy")
STATUS.md       estado actual del proyecto, decisiones y pendientes
BACKEND.md      roadmap detallado del backend, por fases
```
