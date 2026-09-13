"""
Capa de orquestación entre Nessie y Postgres. No hace requests HTTP directos
(eso vive solo en nessie_client.py) — llama a nessie_client y guarda/lee de
Postgres. El resto del backend debe leer datos de aquí, no de nessie_client
directamente, para no depender de Nessie en vivo durante la demo.
"""

import json

from app.db import get_connection, release_connection
from app.categories import classify_purchase
from app.demo_data import opening_balance_for, real_amount
from app.nessie_client import get_account as nessie_get_account
from app.nessie_client import (
    get_accounts_for_customer as nessie_get_accounts_for_customer,
)
from app.nessie_client import get_merchants as nessie_get_merchants
from app.nessie_client import (
    get_bills_for_account,
    get_deposits_for_account,
    get_purchases_for_account,
)


def _upsert_account(cur, account: dict) -> None:
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
            # Saldo inicial: para la cuenta demo viene de demo_data (Nessie no
            # deja actualizarlo); raw conserva lo que dijo Nessie.
            opening_balance_for(account),
            json.dumps(account),
        ),
    )


def sync_snapshot(account_id: str) -> None:
    """
    Llama a Nessie una vez y guarda en Postgres: la cuenta, las demás cuentas
    del mismo customer (p. ej. "Ahorro"), los merchants, y las purchases,
    deposits y bills de la cuenta. Upsert por id, y borra del cache los
    movimientos de la cuenta que ya no existen en Nessie (p. ej. tras
    `seed.py --reset`), para que el forecast no sume datos viejos.
    """
    account = nessie_get_account(account_id)
    customer_id = account.get("customer_id")
    sibling_accounts = nessie_get_accounts_for_customer(customer_id) if customer_id else []
    merchants = nessie_get_merchants()
    purchases = get_purchases_for_account(account_id)
    deposits = get_deposits_for_account(account_id)
    bills = get_bills_for_account(account_id)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            _upsert_account(cur, account)
            for sibling in sibling_accounts:
                if sibling["_id"] != account_id:
                    _upsert_account(cur, sibling)

            for merchant in merchants:
                cur.execute(
                    """
                    INSERT INTO merchants_cache (merchant_id, name, category, raw, synced_at)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (merchant_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        raw = EXCLUDED.raw,
                        synced_at = now()
                    """,
                    (
                        merchant["_id"],
                        merchant.get("name"),
                        merchant.get("category"),
                        json.dumps(merchant),
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
                        # Nessie devuelve los montos sin decimales; el cache
                        # guarda el monto real del dataset (raw conserva el
                        # de Nessie tal cual).
                        real_amount(purchase.get("amount", 0), purchase.get("description", "")),
                        purchase.get("purchase_date"),
                        purchase.get("description"),
                        purchase.get("status"),
                        json.dumps(purchase),
                    ),
                )

            for deposit in deposits:
                cur.execute(
                    """
                    INSERT INTO deposits_cache
                        (deposit_id, account_id, amount, transaction_date, description, status, raw, synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (deposit_id) DO UPDATE SET
                        account_id = EXCLUDED.account_id,
                        amount = EXCLUDED.amount,
                        transaction_date = EXCLUDED.transaction_date,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        raw = EXCLUDED.raw,
                        synced_at = now()
                    """,
                    (
                        deposit["_id"],
                        account_id,
                        real_amount(deposit.get("amount", 0), deposit.get("description", "")),
                        deposit.get("transaction_date"),
                        deposit.get("description"),
                        deposit.get("status"),
                        json.dumps(deposit),
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

            # Huérfanos: lo que está en el cache pero ya no en Nessie.
            if customer_id:
                live_ids = [a["_id"] for a in sibling_accounts] + [account_id]
                cur.execute(
                    "SELECT account_id FROM accounts_cache WHERE customer_id = %s AND account_id <> ALL(%s)",
                    (customer_id, live_ids),
                )
                for (dead_id,) in cur.fetchall():
                    # `cajitas` también referencia accounts_cache: si la cuenta
                    # muere (seed --reset), sus cajitas se van con ella.
                    for table in ("purchases_cache", "deposits_cache", "bills_cache", "rescue_plans_cache", "cajitas"):
                        cur.execute(f"DELETE FROM {table} WHERE account_id = %s", (dead_id,))
                    cur.execute("DELETE FROM accounts_cache WHERE account_id = %s", (dead_id,))

            cur.execute(
                "DELETE FROM purchases_cache WHERE account_id = %s AND purchase_id <> ALL(%s)",
                (account_id, [p["_id"] for p in purchases]),
            )
            cur.execute(
                "DELETE FROM deposits_cache WHERE account_id = %s AND deposit_id <> ALL(%s)",
                (account_id, [d["_id"] for d in deposits]),
            )
            cur.execute(
                "DELETE FROM bills_cache WHERE account_id = %s AND bill_id <> ALL(%s)",
                (account_id, [b["_id"] for b in bills]),
            )

        conn.commit()
    finally:
        release_connection(conn)


def _has_snapshot(account_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM accounts_cache WHERE account_id = %s", (account_id,))
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def _ensure_snapshot(account_id: str, force_sync: bool) -> None:
    """Sincroniza desde Nessie si no hay snapshot (o si se fuerza). No retiene ninguna conexión mientras tanto."""
    if force_sync or not _has_snapshot(account_id):
        sync_snapshot(account_id)


def _account_row_to_dict(row) -> dict:
    account_id, customer_id, nickname, type_, balance, raw = row
    return {
        "_id": account_id,
        "customer_id": customer_id,
        "nickname": nickname,
        "type": type_,
        "balance": float(balance),
        "account_number": (raw or {}).get("account_number"),
    }


def get_account(account_id: str, force_sync: bool = False) -> dict:
    _ensure_snapshot(account_id, force_sync)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT account_id, customer_id, nickname, type, balance, raw "
                "FROM accounts_cache WHERE account_id = %s",
                (account_id,),
            )
            row = cur.fetchone()
    finally:
        release_connection(conn)

    return _account_row_to_dict(row)


def get_accounts_for_customer(customer_id: str) -> list[dict]:
    """Todas las cuentas del customer que ya estén en cache (las sincroniza sync_snapshot)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT account_id, customer_id, nickname, type, balance, raw "
                "FROM accounts_cache WHERE customer_id = %s ORDER BY type, nickname",
                (customer_id,),
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [_account_row_to_dict(r) for r in rows]


def get_purchases(account_id: str, force_sync: bool = False) -> list[dict]:
    _ensure_snapshot(account_id, force_sync)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.purchase_id, p.amount, p.purchase_date, p.description, p.status,
                       p.merchant_id, m.name, m.category
                FROM purchases_cache p
                LEFT JOIN merchants_cache m ON m.merchant_id = p.merchant_id
                WHERE p.account_id = %s
                ORDER BY p.purchase_date DESC, p.purchase_id
                """,
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
            "merchant_id": r[5],
            "merchant_name": r[6],
            "merchant_category": r[7],
            # Categoría refinada (p. ej. un refresco en el OXXO es "Comida chatarra").
            "category": classify_purchase(r[7], r[3]),
        }
        for r in rows
    ]


def get_merchants() -> list[dict]:
    """Todos los merchants en cache (los sincroniza sync_snapshot; son por API key, no por cuenta)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT merchant_id, name, category, raw FROM merchants_cache ORDER BY name"
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [
        {
            "_id": r[0],
            "name": r[1],
            "category": r[2],
            "address": (r[3] or {}).get("address"),
        }
        for r in rows
    ]


def get_deposits(account_id: str, force_sync: bool = False) -> list[dict]:
    _ensure_snapshot(account_id, force_sync)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT deposit_id, amount, transaction_date, description, status "
                "FROM deposits_cache WHERE account_id = %s "
                "ORDER BY transaction_date DESC, deposit_id",
                (account_id,),
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [
        {
            "_id": r[0],
            "amount": float(r[1]),
            "transaction_date": str(r[2]),
            "description": r[3],
            "status": r[4],
        }
        for r in rows
    ]


def get_bills(account_id: str, force_sync: bool = False) -> list[dict]:
    _ensure_snapshot(account_id, force_sync)
    conn = get_connection()
    try:
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