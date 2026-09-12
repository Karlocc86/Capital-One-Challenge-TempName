"""
Confirma que la conexión con Nessie funciona de verdad: corre el seed si
hace falta y luego imprime datos reales del customer demo.

Uso: python scripts/test_connection.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import nessie_client as nc
from scripts.seed import run as seed_run


def main() -> None:
    print("[test_connection] Sembrando (o reutilizando) datos demo...")
    seeded = seed_run()

    customer = nc.get_customer(seeded["customer"]["_id"])
    account = nc.get_account(seeded["account"]["_id"])
    purchases = nc.get_purchases_for_account(account["_id"])
    bills = nc.get_bills_for_account(account["_id"])

    print("\n=== CONEXIÓN NESSIE OK ===")
    print(f"Customer: {customer['first_name']} {customer['last_name']} (id={customer['_id']})")
    print(f"Account: {account['nickname']} (id={account['_id']})")
    print(f"Balance: ${account['balance']}")
    print(f"Purchases encontradas: {len(purchases)}")
    print(f"Bills encontradas: {len(bills)}")


if __name__ == "__main__":
    main()
