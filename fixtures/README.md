# Fixtures — respaldo para la demo

`forecast_ricardo_torres_backup.json` es una respuesta **real** de `GET /forecast/{account_id}` para el usuario demo (Ricardo Torres, `e8f0c102-eb26-4baf-ad78-629cc03c4d74`), capturada y verificada — no es un mock inventado.

## Cuándo usarlo

Último recurso si algo truena en vivo durante el pitch (Nessie, Supabase o Gemini caídos al mismo tiempo, sin internet, etc.). **No lo uses si el endpoint real funciona** — siempre es mejor mostrar el dato en vivo.

## Cómo usarlo en una emergencia

Si necesitas servirlo manualmente en vez del endpoint real, la forma más rápida es correr esto en tu máquina antes del pitch (deja un servidor HTTP simple sirviendo el JSON):

```bash
cd fixtures
python -m http.server 8001
# luego apunta el frontend a http://localhost:8001/forecast_ricardo_torres_backup.json
# en vez de http://localhost:8000/forecast/{account_id}
```

O simplemente ábrelo y copia/pega el JSON si el frontend permite un modo "datos de ejemplo" hardcodeado.

## Cómo regenerar este archivo

Con el backend corriendo y Nessie/Postgres/Gemini sanos:

```bash
curl -s http://localhost:8000/forecast/e8f0c102-eb26-4baf-ad78-629cc03c4d74 -o fixtures/forecast_ricardo_torres_backup.json
```
