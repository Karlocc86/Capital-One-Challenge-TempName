# Predictor "¿Llego a fin de mes?" — Capital One Challenge, HackMTY 2026

Track B2C. Proyecta el saldo futuro del usuario a partir de sus movimientos bancarios y, a diferencia de un simple aviso, **actúa**: propone un plan de rescate concreto (bloquear una categoría de gasto, mover dinero a un "ahorro") usando la API de Nessie (Capital One) como fuente de datos bancarios simulados.

> Estado actual, avances por fase y pendientes: ver [STATUS.md](STATUS.md).

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

## Setup

```bash
# Backend
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # completar API keys (Nessie, Supabase, Gemini)
python scripts/init_db.py
python scripts/seed.py
python scripts/test_connection.py   # debe imprimir el customer demo y su balance
uvicorn app.main:app --reload --port 8000

# Frontend
cd web && pnpm install && pnpm dev
```

## Estructura

```
app/            backend FastAPI (nessie_client, cache, forecaster, agent, main)
scripts/        seed, init_db, sync y tests manuales de cada capa
fixtures/       respaldo estático de /forecast para la demo si algo falla en vivo
web/            frontend Next.js
STATUS.md       estado actual del proyecto, decisiones y pendientes
BACKEND.md      roadmap detallado del backend, por fases
```
