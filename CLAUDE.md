# Proyecto: [NOMBRE] — Capital One Challenge, HackMTY 2026

## Resumen

Track: B2C. Idea: predictor de "¿llego a fin de mes?" — proyecta el saldo futuro del usuario y actúa (no solo avisa): propone y ejecuta acciones simuladas como bloquear una categoría de gasto o mover dinero a un "ahorro" dentro de Nessie. Usa la API de Nessie de Capital One como fuente de datos bancarios simulados.

## Stack (no cambiar sin discutirlo)

- Backend: FastAPI, Python 3.11+
- DB: Postgres (Supabase) — cache de datos de Nessie + resultados de modelos
- IA: scikit-learn para el forecast (regresión); Gemini API (Google, `google-genai`) para explicaciones/recomendaciones en lenguaje natural — se cambió de Claude a Gemini por costo: Anthropic no tiene tier gratis (ver STATUS.md)
- Frontend: Next.js 14 + Tailwind (repo o carpeta /web aparte)
- Gestor de paquetes: pip + venv en backend, pnpm en frontend

## Arquitectura (pipeline, en este orden siempre)

Nessie API → (seed + ingest, SOLO desde el backend) → Postgres cache → pandas (feature engineering) → modelo forecast (sklearn) + LLM (explicación) → FastAPI expone /forecast, /insights, /actions → Next.js dashboard.

NUNCA llames a Nessie directamente desde el frontend. Nessie es HTTP (no HTTPS) y causa errores de contenido mixto desde un frontend en HTTPS. Todo pasa por el backend.

## Nessie API — lo esencial (ya verificado, no reinventar)

- Base URL: http://api.nessieisreal.com
- Auth: API key como query param en CADA request: ?key=API_KEY
- Endpoints clave: /customers, /accounts, /accounts/{id}/purchases, /accounts/{id}/bills, /accounts/{id}/deposits, /accounts/{id}/transfers, /merchants
- Nessie NO genera transacciones automáticamente → hay que sembrarlas (POST) con fechas manuales (purchase_date, formato YYYY-MM-DD)
- account.type válidos: "Credit Card", "Savings", "Checking"
- medium válido: "balance" o "rewards" (nada más)
- Los IDs son ObjectId de Mongo (24 caracteres hex) → guardar siempre como string
- Nessie no tiene SLA público → cachear TODO, nunca depender de una llamada en vivo durante el pitch/demo

## Convenciones

- UN solo módulo app/nessie_client.py centraliza TODAS las llamadas a Nessie. Nadie más en el proyecto hace requests/httpx directo a Nessie.
- El seeding vive en scripts/seed.py y debe ser idempotente (si el customer demo ya existe, no lo duplica — busca por nombre antes de crear).
- Cada endpoint de FastAPI devuelve {"data": ..., "meta": {...}}, nunca el JSON crudo de Nessie sin envolver.
- La API key SIEMPRE en .env, nunca hardcodeada, nunca en el frontend.
- Un solo customer_id fijo (el "usuario demo") — no construyan login/auth real.

## Testing / verificación

- python scripts/test_connection.py debe imprimir el customer y su balance ANTES de seguir construyendo nada más.
- Cachear las respuestas de Nessie usadas en la demo como JSON en /fixtures para poder demoar sin depender de internet/Nessie en vivo.

## Comandos exactos

```
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
python scripts/seed.py
python scripts/test_connection.py
```

## Anti-patrones (NO HACER)

- NO llamar a Nessie en vivo durante el pitch — usar los fixtures cacheados.
- NO construir autenticación de usuarios real.
- NO empezar por el modelo de ML antes de tener el walking skeleton end-to-end funcionando (seed → endpoint → frontend mostrando UN número real).
- NO meter lógica de negocio dentro de nessie_client.py — ese módulo solo habla con la API, nada de forecast ni scoring ahí.

## Orden de construcción (walking skeleton primero, siempre)

1. nessie_client.py + scripts/seed.py (1 customer, 1 account, ~15 purchases, 2-3 bills)
2. Endpoint /summary/{account_id} que regresa balance + gasto total (SIN IA todavía)
3. Frontend mínimo que muestre ese número real
4. Recién ahí: /forecast (regresión) y /insights (LLM) para el "momento de valor"

## Flujo de Github

- **Antes de implementar algo**: propón primero en qué rama se debería trabajar (nueva feature branch vs. seguir en la actual) y espera confirmación antes de tocar código.
- **Después de cada feature terminada**, dame listos para copiar/pegar (yo decido cuándo correrlos):
  - `git add <archivos específicos>` (no `git add .` a ciegas — primero revisa qué se va a incluir)
  - `git commit -m "tipo: qué se hizo"` (tipo = feat, fix, docs, chore, refactor, etc.)
  - `git push` indicando explícitamente a qué rama y remoto
- **Antes de empezar a trabajar en algo nuevo**, dime si hace falta un `git pull` (por ejemplo, si la rama remota pudo haber cambiado) y de dónde.
