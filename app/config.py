import os

from dotenv import load_dotenv

load_dotenv()

NESSIE_API_KEY = os.getenv("NESSIE_API_KEY")
NESSIE_BASE_URL = os.getenv("NESSIE_BASE_URL", "https://api.nessieisreal.com")

if not NESSIE_API_KEY:
    raise RuntimeError(
        "NESSIE_API_KEY no está configurada. Copia .env.example a .env y pon tu API key."
    )
