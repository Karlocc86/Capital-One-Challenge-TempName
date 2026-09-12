"""
Corre el sync manual de un account: Nessie -> Postgres cache.

Uso: python scripts/sync.py <account_id>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cache import sync_snapshot
from app.db import get_connection, release_connection


def count_rows(account_id: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM accounts_cache WHERE customer_id = "
                "(SELECT customer_id FROM accounts_cache WHERE account_id = %s)",
                (account_id,),
            )
            accounts = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM purchases_cache WHERE account_id = %s", (account_id,))
            purchases = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM deposits_cache WHERE account_id = %s", (account_id,))
            deposits = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM bills_cache WHERE account_id = %s", (account_id,))
            bills = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM merchants_cache")
            merchants = cur.fetchone()[0]
    finally:
        release_connection(conn)
    return {
        "accounts": accounts,
        "purchases": purchases,
        "deposits": deposits,
        "bills": bills,
        "merchants": merchants,
    }


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/sync.py <account_id>")
        sys.exit(1)

    account_id = sys.argv[1]
    print(f"[sync] Sincronizando account {account_id} desde Nessie...")
    sync_snapshot(account_id)

    counts = count_rows(account_id)
    print(
        f"[sync] Listo: {counts['accounts']} accounts del customer, "
        f"{counts['purchases']} purchases, {counts['deposits']} deposits, "
        f"{counts['bills']} bills, {counts['merchants']} merchants"
    )


if __name__ == "__main__":
    main()
