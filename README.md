# Predictor "¿Llego a fin de mes?" — Capital One Challenge, HackMTY 2026

Track B2C. Proyecta el saldo futuro del usuario a partir de sus movimientos bancarios y, a diferencia de un simple aviso, **acompaña**: un agente de bienestar integral (Gemini) convierte el forecast en un plan de 10 recomendaciones concretas —dinero, salud, descanso, vida social— que el avatar "canica" va narrando sobre el dashboard. Usa la API de Nessie (Capital One) como fuente de datos bancarios simulados.

> Estado detallado, decisiones y pendientes: ver [STATUS.md](STATUS.md).

## Estado actual (13 de septiembre de 2026)

**Funciona de punta a punta:** seed → Nessie → cache Postgres → ledger + forecast (sklearn) → agente (Gemini) → API → dashboard Next.js conectado a datos reales.

- **Persona demo:** Ricardo Torres, Monterrey, ingreso INEGI decil III ($12,282 MXN/mes en dos quincenas). Dataset determinista en `app/demo_data.py`: 2 cuentas (Cheques + Ahorro), 9 comercios con categoría, 35 compras, 2 depósitos de nómina y 9 bills (renta $7,000, servicios y 7 suscripciones prescindibles: Netflix, HBO Max, Disney+, Spotify, Amazon Prime, Xbox Game Pass, Smart Fit). Calibrado para que **egresos > ingresos** y el forecast proyecte insolvencia en ~2 semanas.
- **Saldo real por ledger:** `saldo = inicial + Σ depósitos − Σ compras − Σ bills cobradas` (`app/ledger.py`). Nessie no descuenta compras del balance, así que el backend lo calcula.
- **Forecast día a día a 90 días** (`app/forecaster.py`): gasto variable por regresión lineal, bills como cargos puntuales en su fecha, quincenas futuras inferidas de los depósitos; incluye análisis de fin de mes (ingreso, egreso y déficit mensual a recortar).
- **Categorización** (`app/categories.py`): comida chatarra, gastos hormiga (compras < $150 en OXXO/tiendas), suscripciones, transporte, salud, salidas.
- **Agente de bienestar** (`app/agent.py`, Gemini con Structured Outputs): exactamente 10 recomendaciones, una por área — *Tu paso de hoy, Fin de mes, Suscripciones, Comida chatarra, Gastos hormiga, Vida social, Movimiento, Salud preventiva, Ahorro, Integral* — cada una con `wellbeing_benefit` e impacto estimado; tono cercano, tuteo, sin culpa. Plan de respaldo con números reales si Gemini falla; el plan se cachea en Postgres.
- **Dashboard** (`web/`): pantalla completa, sidebar de cuentas, Mi Balance (saldo ledger + ingresos/egresos vs. meta), Recientes (vista previa de 7 + `/transacciones`), Próximas (5 bills + `/proximas`), Gastos, secciones de Ahorros / Tarjetas / Préstamos / Recompensas. Todo formateado es-MX / MXN.
- **Avatar canica** (`web/components/AvatarCanica.tsx`): recorre las tarjetas blancas anclándose a su esquina superior derecha; muestra el insight de la sección (12 s) y luego cada recomendación (15 s); click en la canica salta a la siguiente. Los insights por sección se muestran desde el primer segundo con texto de respaldo, aunque el backend tarde o falle.

**Pendiente / no implementado:**
- `/actions` (bloquear categoría, mover a ahorro) — la propuesta de acción existe en el plan, la ejecución simulada no.
- `ForecastCard` (días restantes + lista completa de recomendaciones) está construido pero no montado en el dashboard.
- Las secciones Ahorros/Tarjetas/Préstamos/Recompensas leen Nessie en vivo desde el backend (no pasan por la cache) y `CreditWiseCard` sigue siendo estático.
- `/insights` cachea solo en memoria del proceso: cada reinicio del backend vuelve a llamar a Gemini (~5–10 s la primera vez).

## Stack

- **Backend**: FastAPI, Python 3.11+
- **DB**: Postgres (Supabase) — cache de accounts/merchants/purchases/deposits/bills + rescue plans
- **IA**: `scikit-learn` (regresión lineal) para el forecast + Gemini (`google-genai`, Structured Outputs) para el plan de bienestar y los insights por sección
- **Frontend**: Next.js 14 + Tailwind (`/web`)
- **Datos**: [Nessie API](http://api.nessieisreal.com) de Capital One

## Arquitectura

```
Nessie API → nessie_client.py → cache.py (Postgres) → ledger.py + categories.py
           → forecaster.py (sklearn) → agent.py (Gemini) → FastAPI {"data","meta"} → Next.js (web/lib/api.ts)
```

El frontend nunca llama a Nessie directamente; todo pasa por el backend. `nessie_client.py` es el único módulo HTTP y no contiene lógica de negocio. Roadmap original del backend en [BACKEND.md](BACKEND.md).

## Cómo correr el proyecto

### Backend (FastAPI, puerto 8000)

```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # completar API keys: Nessie, Postgres (Supabase), Gemini
python scripts/init_db.py
python scripts/seed.py              # idempotente; imprime el account_id demo
python scripts/sync.py <account_id> # Nessie → Postgres
python scripts/test_connection.py   # debe imprimir el customer demo y su balance
uvicorn app.main:app --reload --port 8000
```

**Rutina de la mañana del pitch** (las fechas del dataset son relativas al día del seed y Nessie no permite borrar compras):

```bash
python scripts/seed.py --reset                 # recrea la cuenta de cheques y actualiza DEMO_ACCOUNT_ID en .env y web/.env.local
python scripts/sync.py <account_id nuevo>
# reiniciar backend y frontend, luego calentar el plan:
curl "localhost:8000/forecast/<account_id nuevo>?force_refresh=true"
```

Verificación de cada capa: `python scripts/test_forecaster.py` (asegura insolvencia en 10–16 días) y `python scripts/test_agent.py` (una llamada real a Gemini).

### Endpoints (todos `{"data", "meta"}`, montos en MXN)

| Endpoint | Qué devuelve |
|---|---|
| `GET /health` | ping |
| `GET /summary/{account_id}` | saldo ledger, saldo inicial, bills cobradas, ingresos/egresos últimos 30 días, meta de ingreso |
| `GET /accounts/{account_id}` | cuentas del customer (Cheques, Ahorro) con número enmascarado |
| `GET /transactions/{account_id}?limit=20&type=all\|purchase\|deposit` | compras + depósitos con comercio y categoría |
| `GET /purchases/{account_id}` | todas las compras + resumen por comercio |
| `GET /merchants` | catálogo de comercios con categoría |
| `GET /bills/{account_id}` | bills con próxima fecha de cobro y bandera `discretionary` (suscripciones) |
| `GET /forecast/{account_id}` | proyección a 90 días, insolvencia, próxima nómina, análisis de fin de mes + plan de 10 recomendaciones (`?force_refresh=true` regenera el plan) |
| `GET /savings|credit-cards|loans|rewards/{customer_id}` | datos por sección para las páginas secundarias |
| `GET /insights/{customer_id}` | un insight corto por widget para el avatar canica |
| `GET /guide/welcome/{account_id}` | saludo del Agente Guía al abrir la app: tono según insolvencia próxima / quincena mañana / todo bien, con propuestas de Cajita para renta y servicios (`meta` trae quincena y gastos esenciales detectados) |
| `POST /cajitas` | crea una Cajita (dinero apartado para un gasto esencial); idempotente por `linked_expense_name` |
| `GET /cajitas/{account_id}` | cajitas de la cuenta; `meta.active_total` = lo que hay que restar al saldo para el disponible |
| `POST /cajitas/{id}/request-withdrawal` | evalúa el retiro: si ya llegó la fecha libera directo; si es antes, regresa la advertencia del agente (`severity`, `requires_double_confirmation`) sin liberar |
| `POST /cajitas/{id}/confirm-withdrawal` | libera el dinero y guarda si fue retiro anticipado y con cuántos días |

### Frontend (Next.js, puerto 3000)

```bash
cd web
pnpm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_DEMO_ACCOUNT_ID, NEXT_PUBLIC_DEMO_CUSTOMER_ID
pnpm dev                            # o `pnpm dev:clean` si .next quedó corrupto (nunca correr dos `next dev` a la vez)
```

Abre [http://localhost:3000](http://localhost:3000).

## Estructura

```
app/            backend FastAPI: nessie_client, cache, ledger, categories, forecaster, agent, schemas, demo_data, main
scripts/        seed (--reset), init_db, sync y tests manuales de cada capa
fixtures/       respaldo JSON de cada endpoint (incl. plan de bienestar) para demoar sin Nessie/Gemini en vivo
web/            frontend Next.js: app/ (dashboard, transacciones, proximas, secciones), components/ (AvatarCanica, Dashboard...), lib/api.ts
STATUS.md       estado del proyecto, decisiones y pendientes
BACKEND.md      roadmap original del backend, por fases
```
