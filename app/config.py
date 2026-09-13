import os

from dotenv import load_dotenv

load_dotenv()

NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
NESSIE_BASE_URL = os.getenv("NESSIE_BASE_URL", "https://api.nessieisreal.com")
DATABASE_URL = os.getenv("DATABASE_URL")

if not NESSIE_API_KEY:
    raise RuntimeError(
        "NESSIE_API_KEY no está configurada. Copia .env.example a .env y pon tu API key."
    )

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está configurada. Crea un proyecto en supabase.com, copia la "
        "connection string (Session pooler) y ponla en .env."
    )

# Opcional a propósito: a diferencia de NESSIE_API_KEY/DATABASE_URL, esta no
# hace fallar el import de config.py. Nada del resto del backend depende de
# Gemini — solo CognitiveFinancialAgent, que valida su propia key al usarse.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Account del usuario demo (lo imprime `python scripts/seed.py`). Opcional:
# los endpoints reciben el account_id en la URL; esto lo usan los scripts de
# prueba para no repetir el literal.
DEMO_ACCOUNT_ID = os.getenv("DEMO_ACCOUNT_ID")

# Orígenes permitidos por CORS, separados por coma. Default cubre dev local;
# en producción se sobreescribe con el dominio real del frontend desplegado.
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
