import os

from dotenv import load_dotenv

load_dotenv()

NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
NESSIE_BASE_URL = os.getenv("NESSIE_BASE_URL", "http://api.nessieisreal.com")
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
