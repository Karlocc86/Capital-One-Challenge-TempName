# Siguientes pasos — Agente Guía / Cajitas

_Al 13 de septiembre de 2026, tras cerrar backend Fase A + Fase B (commits `e271a58`, `3f8f79c`, `5a8be63`)._

## Ya está (backend, verificado por curl, nada conectado a `web/` todavía)

- `GET /guide/welcome/{account_id}` — saludo del Agente Guía con tono adaptado (insolvencia próxima / quincena mañana con gasto esencial sin apartar / todo bien) y propuestas de Cajita.
- `POST /cajitas`, `GET /cajitas/{account_id}` — creación idempotente y listado (`meta.active_total`).
- `POST /cajitas/{id}/request-withdrawal`, `POST /cajitas/{id}/confirm-withdrawal` — retiro anticipado con advertencia de conciencia (`severity`, `requires_double_confirmation`) sin bloquear al usuario.
- Sidebar solo navegación, CreditWise movido a Tarjetas de Crédito, página `/cajitas` como placeholder ("Próximamente.").

## Pendiente — conectar el frontend

1. **Saludo del Agente Guía al abrir el dashboard**
   - Llamar a `GET /guide/welcome/{account_id}` una vez al montar `Dashboard.tsx`.
   - Mostrarlo con `AvatarCanica` (ya tiene la infraestructura de burbujas) o como banner encima del balance, según el `tone` (`positive`/`neutral`/`warning`).
   - Si `cajita_proposals` no viene vacío, mostrar tarjetas de propuesta con el `cta_label` → botón que dispare el paso 2.

2. **Página `/cajitas` real**
   - Reemplazar el placeholder: `GET /cajitas/{account_id}` para listar las cajitas (activas primero), con `target_amount`, `linked_expense_name`, `reserve_date`, `status`.
   - Botón "Crear cajita" a partir de una propuesta del saludo → `POST /cajitas`.
   - Botón "Retirar" en cada cajita activa → `POST /cajitas/{id}/request-withdrawal`:
     - Si `released: true` → refrescar la lista, sin fricción.
     - Si `released: false` → mostrar el `warning` (mensaje, reminder, severity) y pedir confirmación (doble si `requires_double_confirmation`) antes de llamar `POST /cajitas/{id}/confirm-withdrawal`.
   - `data-avatar-target="cajitas"` en la tarjeta blanca para que la canica también la cubra (falta agregar un insight para esta sección en `/insights` o en el tour de recomendaciones).

3. **Saldo disponible descontando Cajitas**
   - Hoy "Mi Balance" muestra el saldo del ledger sin restar las cajitas activas.
   - Usar `GET /cajitas/{account_id}` → `meta.active_total` y mostrar `disponible = saldo - active_total` (o pedirlo directo si se decide exponerlo en `/summary`/`/accounts` — ver nota abajo).

## Pendiente — backend (más chico)

- `/summary` y `/accounts` **no** restan `active_total` del balance mostrado (decisión explícita del plan de Cajitas, para no tocar esos dos endpoints a la vez que se armaba el backend). Evaluar si conviene sumarlo ahí directamente en vez de que el frontend haga la resta.
- `/insights` no tiene un insight para la sección Cajitas — el avatar canica no dirá nada ahí hasta que se agregue.
- El saludo se cachea en memoria por proceso y por día (`_welcome_memory_cache` en `app/main.py`) — se pierde al reiniciar el backend, igual que `/insights`. Si se vuelve molesto en el pitch, mover a Postgres como `rescue_plans_cache`.

## Recordatorio de mantenimiento

- El dataset envejece a diario (fechas relativas al día del seed). Rutina de la mañana del pitch: `python scripts/seed.py --reset` → `python scripts/sync.py <account_id nuevo>` → reiniciar backend y frontend → `curl "localhost:8000/forecast/<id>?force_refresh=true"`.
- Nunca correr dos `pnpm dev`/`uvicorn --reload` a la vez (quedan procesos huérfanos ocupando el puerto — ya pasó dos veces esta semana).
