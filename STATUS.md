# Estado del proyecto — Capital One Challenge, HackMTY 2026

_Última actualización: 12 de septiembre de 2026_

## Qué estamos construyendo

Track B2C. Un predictor de "¿llego a fin de mes?": proyecta el saldo futuro del usuario a partir de sus movimientos bancarios y, a diferencia de un simple aviso, **actúa** — propone y ejecuta acciones simuladas como bloquear una categoría de gasto o mover dinero a un "ahorro". Usa la API de Nessie (Capital One) como fuente de datos bancarios simulados.

## Stack

- Backend: FastAPI, Python 3.11+
- DB: Postgres (Supabase) — todavía no implementada
- IA: scikit-learn para el forecast (regresión) + Claude API para explicaciones en lenguaje natural — todavía no implementada
- Frontend: Next.js 14 + Tailwind — scaffold provisional ya funcionando (ver Paso 3)
- Datos: Nessie API (api.nessieisreal.com), consumida vía HTTPS por un firewall de red que bloquea el puerto 80

## Arquitectura objetivo (pipeline)

Nessie API → backend (ingest) → Postgres cache → pandas (features) → modelo forecast (sklearn) + LLM (explicación) → FastAPI (`/forecast`, `/insights`, `/actions`) → dashboard Next.js.

Regla dura: el frontend nunca llama a Nessie directamente, todo pasa por el backend.

## Progreso: walking skeleton completo (pasos 1–3 de 4)

Siguiendo el "Orden de construcción" definido en `CLAUDE.md`, ya completamos y **verificamos contra la API real de Nessie** (no mockeada) todo el camino de datos, de punta a punta: Nessie → backend → navegador.

**Paso 1 — cliente Nessie + seed de datos, DONE**

- `app/nessie_client.py`: único módulo que habla con Nessie (customers, accounts, purchases, bills, merchants — crear y leer). Cualquier error de Nessie se loguea con status code y body completo.
- `scripts/seed.py`: idempotente. Crea (o reutiliza) 1 customer demo ("Demo HackMTY"), 1 account tipo Checking, 1 merchant, 15 purchases de los últimos 30 días, 2 bills recurrentes.
- `scripts/test_connection.py`: corre el seed y confirma datos reales.
- Resultado confirmado: Customer "Demo HackMTY", account "Cuenta Principal" con balance $2500, 15 purchases, 2 bills.

**Paso 2 — endpoints de solo lectura, DONE**

- `app/main.py`: expone `GET /health` (no toca Nessie) y `GET /summary/{account_id}` (balance + gasto total sumando purchases, sin ningún modelo todavía).
- Probado en vivo: `/summary/{account_id}` devuelve balance $2500, total_spent $1328, purchase_count 15 sobre la cuenta real sembrada. Un account_id inválido devuelve 404 controlado, no 500.

**Paso 3 — frontend provisional, DONE**

- Scaffold Next.js 14 + TypeScript + Tailwind (App Router) en `web/`, instalado con pnpm.
- `web/app/page.tsx`: Client Component que hace `fetch` en el navegador a `GET /summary/{account_id}` y muestra balance, gasto total y conteo de purchases — con estados de carga y error.
- `app/main.py` ahora tiene `CORSMiddleware` habilitado para `http://localhost:3000`.
- Verificado visualmente en navegador (screenshot): se ve "Cuenta Principal — $2,500 — Gasto total: $1,328 (15 compras)", el mismo dato real que devuelve el backend.
- Todavía es puramente provisional: sin diseño elaborado, sin selector de cuenta/usuario, un solo account_id hardcodeado por variable de entorno.

**Pendiente:**

- Paso 4: `/forecast` (regresión sklearn), `/insights` (Claude API) y `/actions` (acciones simuladas, ej. bloquear categoría o mover a ahorro) — el "momento de valor" del proyecto. Explícitamente no se ha tocado nada de esto todavía.
- Postgres/Supabase como cache: todavía no implementado (por ahora se llama a Nessie directo desde el backend en cada request).
- Diseño real del frontend: el actual es solo para confirmar que el dato llega, no la UI final.

## Bugs de Nessie descubiertos y ya resueltos (importante documentarlos, no están en la doc pública)

1. **Puerto 80 (HTTP) bloqueado en la red del hackathon.** Nessie funciona igual de bien por HTTPS — se cambió `NESSIE_BASE_URL` a `https://api.nessieisreal.com`.
2. **`merchant.category` debe ser un string**, no una lista (ej. `"food"`, no `["food"]"`) — la doc pública sugiere lista.
3. **`purchase.status` es requerido en el POST** aunque no aparece documentado. Si se crea un purchase sin `status`, Nessie lo guarda pero después el GET truena al intentar deserializarlo (error de validación interno de Nessie) — y como el GET falla para toda la lista, ni siquiera se pueden recuperar los IDs para borrarlos uno por uno. La única salida fue borrar la account completa y recrearla. Ahora `create_purchase` siempre manda `status` (`"completed"` en el seed).

## Convenciones que se están respetando

- Toda respuesta de FastAPI va envuelta en `{"data": ..., "meta": {...}}`, nunca el JSON crudo de Nessie.
- Un solo `customer_id` demo fijo, sin autenticación real de usuarios.
- `nessie_client.py` no tiene lógica de negocio (nada de forecast/scoring ahí).
- `.env` (backend) y `web/.env.local` (frontend), con secretos e IDs reales, están en `.gitignore` — nunca se suben a git.

## Estado del repo

- `master` tiene ambas features mergeadas (PR de la rama `backend`, que incluyó también el commit del frontend provisional).
- `app/`, `scripts/`, `requirements.txt` y `web/` ya están en `master`.
- `CLAUDE.md`, `STATUS.md` y `.env.example` (raíz) siguen sin commitear todavía — quedaron fuera del commit de backend a propósito o por descuido, revisar antes de la próxima ronda de commits.

## Próximo paso inmediato

Empezar el Paso 4: diseñar el modelo de forecast (regresión con `scikit-learn` sobre los datos de purchases/bills ya sembrados) y el endpoint `/forecast`, seguido de `/insights` (explicación en lenguaje natural vía Claude API) y `/actions` (acciones simuladas). Este es el "momento de valor" real del proyecto para el pitch.
