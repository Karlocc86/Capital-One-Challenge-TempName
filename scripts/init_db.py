"""
Crea (si no existen) las tablas de cache en Postgres: accounts_cache,
purchases_cache, bills_cache. Idempotente.

Uso: python scripts/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection, release_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts_cache (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT,
    nickname TEXT,
    type TEXT,
    balance NUMERIC,
    raw JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS purchases_cache (
    purchase_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts_cache(account_id),
    merchant_id TEXT,
    amount NUMERIC,
    purchase_date DATE,
    description TEXT,
    status TEXT,
    raw JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bills_cache (
    bill_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts_cache(account_id),
    payee TEXT,
    nickname TEXT,
    payment_amount NUMERIC,
    payment_date DATE,
    recurring_date INTEGER,
    status TEXT,
    raw JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rescue_plans_cache (
    account_id TEXT PRIMARY KEY REFERENCES accounts_cache(account_id),
    plan JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def run() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        release_connection(conn)
    print(
        "[init_db] Tablas listas: accounts_cache, purchases_cache, bills_cache, "
        "rescue_plans_cache"
    )


if __name__ == "__main__":
    run()
