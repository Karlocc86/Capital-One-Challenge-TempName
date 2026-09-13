# Fixtures — respaldo para la demo

Respuestas **reales** de la API para el usuario demo (Ricardo Torres, account `0ce1d6a3-551f-420f-af8a-62971a612f0f`), capturadas y verificadas — no son mocks inventados.

| Archivo | Endpoint | Qué alimenta en la UI |
|---|---|---|
| `forecast_ricardo_torres_backup.json` | `GET /forecast/{account_id}` | Días a la insolvencia + plan de rescate (Gemini) |
| `summary_ricardo_torres.json` | `GET /summary/{account_id}` | Saldo, `money_in`/`money_out` (barras de Gastos) |
| `transactions_ricardo_torres.json` | `GET /transactions/{account_id}?limit=20` | Transacciones recientes (compras + nómina) |
| `purchases_ricardo_torres.json` | `GET /purchases/{account_id}` | Todas las compras con comercio + resumen por comercio (el dashboard muestra las 7 más recientes) |
| `merchants.json` | `GET /merchants` | Catálogo de comercios con categoría |
| `bills_ricardo_torres.json` | `GET /bills/{account_id}` | Próximas transacciones (bills con `next_payment_date`) |
| `accounts_ricardo_torres.json` | `GET /accounts/{account_id}` | Sidebar (Cheques + Ahorro, número enmascarado) |

Todos van envueltos en `{"data": ..., "meta": {...}}`, con `meta.currency = "MXN"`, fechas ISO (`YYYY-MM-DD`) y montos positivos + `direction: "in" | "out"`.

## Cuándo usarlos

Último recurso si algo truena en vivo durante el pitch (Nessie, Supabase o Gemini caídos al mismo tiempo, sin internet, etc.). **No los uses si el endpoint real funciona** — siempre es mejor mostrar el dato en vivo.

## Cómo usarlos en una emergencia

Servirlos manualmente en vez del endpoint real (deja un servidor HTTP simple sirviendo los JSON):

```bash
cd fixtures
python -m http.server 8001
# luego apunta el frontend a http://localhost:8001/<archivo>.json
# en vez de http://localhost:8000/<endpoint>/{account_id}
```

## Cómo regenerarlos

Con el backend corriendo y Nessie/Postgres/Gemini sanos (las fechas de las transacciones son relativas al día del seed: si pasaron días, corre antes `python scripts/seed.py --reset` y `python scripts/sync.py <account_id>`):

```bash
ID=0ce1d6a3-551f-420f-af8a-62971a612f0f
curl -s "http://localhost:8000/forecast/$ID?force_refresh=true" -o fixtures/forecast_ricardo_torres_backup.json
curl -s "http://localhost:8000/summary/$ID"                     -o fixtures/summary_ricardo_torres.json
curl -s "http://localhost:8000/transactions/$ID?limit=20"       -o fixtures/transactions_ricardo_torres.json
curl -s "http://localhost:8000/purchases/$ID"                   -o fixtures/purchases_ricardo_torres.json
curl -s "http://localhost:8000/merchants"                        -o fixtures/merchants.json
curl -s "http://localhost:8000/bills/$ID"                       -o fixtures/bills_ricardo_torres.json
curl -s "http://localhost:8000/accounts/$ID"                    -o fixtures/accounts_ricardo_torres.json
```

Revisa que el forecast traiga un plan real de Gemini: si `rescue_plan.summary` empieza con "No pudimos generar…", es el fallback — repite con `?force_refresh=true`.
