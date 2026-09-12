"""
Capa de orquestación entre Nessie y Postgres. No hace requests HTTP directos
(eso vive solo en nessie_client.py) — llama a nessie_client y guarda/lee de
Postgres. El resto del backend debe leer datos de aquí, no de nessie_client
directamente, para no depender de Nessie en vivo durante la demo.
"""

import json

from app.db import get_connection, release_connection
from app.nessie_client import get_account as nessie_get_account
from app.nessie_client import get_bills_for_account, get_purchases_for_account


def sync_snapshot(account_id: str) -> None:
    """Llama a Nessie una vez y guarda accounts/purchases/bills en Postgres."""
    account = nessie_get_account(account_id)
    purchases = get_purchases_for_account(account_id)
    bills = get_bills_for_account(account_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts_cache
                    (account_id, customer_id, nickname, type, balance, raw, synced_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (account_id) DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    nickname = EXCLUDED.nickname,
                    type = EXCLUDED.type,
                    balance = EXCLUDED.balance,
                    raw = EXCLUDED.raw,
                    synced_at = now()
                """,
                (
                    account["_id"],
                    account.get("customer_id"),
                    account.get("nickname"),
                    account.get("type"),
                    account.get("balance"),
                    json.dumps(account),
                ),
            )

            for purchase in purchases:
                cur.execute(
                    """
                    INSERT INTO purchases_cache
                        (purchase_id, account_id, merchant_id, amount, purchase_date, description, status, raw, synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (purchase_id) DO UPDATE SET
                        account_id = EXCLUDED.account_id,
                        merchant_id = EXCLUDED.merchant_id,
                        amount = EXCLUDED.amount,
                        purchase_date = EXCLUDED.purchase_date,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        raw = EXCLUDED.raw,
                        synced_at = now()
                    """,
                    (
                        purchase["_id"],
                        account_id,
                        purchase.get("merchant_id"),
                        purchase.get("amount"),
                        purchase.get("purchase_date"),
                        purchase.get("description"),
                        purchase.get("status"),
                        json.dumps(purchase),
                    ),
                )

            for bill in bills:
                cur.execute(
                    """
                    INSERT INTO bills_cache
                        (bill_id, account_id, payee, nickname, payment_amount, payment_date, recurring_date, status, raw, synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (bill_id) DO UPDATE SET
                        account_id = EXCLUDED.account_id,
                        payee = EXCLUDED.payee,
                        nickname = EXCLUDED.nickname,
                        payment_amount = EXCLUDED.payment_amount,
                        payment_date = EXCLUDED.payment_date,
                        recurring_date = EXCLUDED.recurring_date,
                        status = EXCLUDED.status,
                        raw = EXCLUDED.raw,
                        synced_at = now()
                    """,
                    (
                        bill["_id"],
                        account_id,
                        bill.get("payee"),
                        bill.get("nickname"),
                        bill.get("payment_amount"),
                        bill.get("payment_date"),
                        bill.get("recurring_date"),
                        bill.get("status"),
                        json.dumps(bill),
                    ),
                )

        conn.commit()
    finally:
        release_connection(conn)


def _has_snapshot(conn, account_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM accounts_cache WHERE account_id = %s", (account_id,))
        return cur.fetchone() is not None


def get_account(account_id: str, force_sync: bool = False) -> dict:
    conn = get_connection()
    try:
        if force_sync or not _has_snapshot(conn, account_id):
            release_connection(conn)
            sync_snapshot(account_id)
            conn = get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT account_id, nickname, type, balance FROM accounts_cache WHERE account_id = %s",
                (account_id,),
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)

    return {
        "_id": row[0],
        "nickname": row[1],
        "type": row[2],
        "balance": float(row[3]),
    }


def get_purchases(account_id: str, force_sync: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        if force_sync or not _has_snapshot(conn, account_id):
            release_connection(conn)
            sync_snapshot(account_id)
            conn = get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT purchase_id, amount, purchase_date, description, status "
                "FROM purchases_cache WHERE account_id = %s",
                (account_id,),
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [
        {
            "_id": r[0],
            "amount": float(r[1]),
            "purchase_date": str(r[2]),
            "description": r[3],
            "status": r[4],
        }
        for r in rows
    ]


def get_bills(account_id: str, force_sync: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        if force_sync or not _has_snapshot(conn, account_id):
            release_connection(conn)
            sync_snapshot(account_id)
            conn = get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT bill_id, payee, nickname, payment_amount, payment_date, recurring_date, status "
                "FROM bills_cache WHERE account_id = %s",
                (account_id,),
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [
        {
            "_id": r[0],
            "payee": r[1],
            "nickname": r[2],
            "payment_amount": float(r[3]),
            "payment_date": str(r[4]),
            "recurring_date": r[5],
            "status": r[6],
        }
        for r in rows
    ]


def get_cached_rescue_plan(account_id: str) -> dict | None:
    """Solo se llena con planes generados de verdad por Gemini (ver save_rescue_plan)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan FROM rescue_plans_cache WHERE account_id = %s", (account_id,)
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)

    return row[0] if row else None


def save_rescue_plan(account_id: str, plan: dict) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rescue_plans_cache (account_id, plan, generated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (account_id) DO UPDATE SET
                    plan = EXCLUDED.plan,
                    generated_at = now()
                """,
                (account_id, json.dumps(plan)),
            )
        conn.commit()
    finally:
        release_connection(conn)
