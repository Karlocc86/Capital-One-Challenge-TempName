"""
Crea (si no existen) las tablas de cache en Postgres: accounts_cache,
purchases_cache, bills_cache, rescue_plans_cache, merchants_cache,
deposits_cache — y la tabla propia `cajitas`. Idempotente.

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

-- La categoría de una purchase se resuelve con JOIN a merchants_cache (la
-- `category` del merchant en Nessie es la etiqueta que pinta la UI). Sin FK
-- desde purchases_cache.merchant_id a propósito: el orden del sync no debe
-- poder romper el upsert.
CREATE TABLE IF NOT EXISTS merchants_cache (
    merchant_id TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    raw JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deposits_cache (
    deposit_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts_cache(account_id),
    amount NUMERIC,
    transaction_date DATE,
    description TEXT,
    status TEXT,
    raw JSONB,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS purchases_cache_account_date_idx
    ON purchases_cache (account_id, purchase_date DESC);
CREATE INDEX IF NOT EXISTS deposits_cache_account_date_idx
    ON deposits_cache (account_id, transaction_date DESC);

-- Cajitas: dinero "apartado" para un gasto esencial. Registro propio (no es
-- cache de Nessie): el saldo disponible = saldo del ledger − Σ cajitas activas.
-- Ver app/cajitas.py.
CREATE TABLE IF NOT EXISTS cajitas (
    id BIGSERIAL PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts_cache(account_id),
    name TEXT NOT NULL,
    target_amount NUMERIC NOT NULL,
    linked_expense_name TEXT NOT NULL,
    reserve_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    was_early_withdrawal BOOLEAN NOT NULL DEFAULT false,
    days_early_at_withdrawal INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cajitas_account_status_idx ON cajitas (account_id, status);
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
        "rescue_plans_cache, merchants_cache, deposits_cache, cajitas"
    )


if __name__ == "__main__":
    run()
