"""
Siembra un customer demo, una account Checking, ~15 purchases de los últimos
30 días y bills recurrentes. Idempotente: si ya existe el customer demo
(buscado por nombre), reutiliza sus IDs en vez de duplicar.

Perfil demo: "Ricardo Torres", trabajador de ingreso medio-bajo en Monterrey.
Los montos están calibrados con datos reales del INEGI (ENIGH 2024, decil
III de ingreso: $36,845 MXN de ingreso corriente trimestral promedio, ~$12,282
MXN/mes) — no son números arbitrarios, representan un perfil de vulnerabilidad
financiera real, incluyendo un pago recurrente a una casa de empeño/préstamo
personal informal, justo el tipo de señal que el forecast debe detectar.

Uso: python scripts/seed.py
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import nessie_client as nc

DEMO_FIRST_NAME = "Ricardo"
DEMO_LAST_NAME = "Torres"
DEMO_ACCOUNT_NICKNAME = "Cuenta Principal"
DEMO_MERCHANT_NAME = "Comercio Local Monterrey"

# (descripción, monto mínimo, monto máximo) en MXN — proporciones inspiradas
# en ENIGH 2024: alimentos ~38%, transporte ~19.5% del gasto de un hogar.
PURCHASE_CATEGORIES = [
    ("Abarrotes", 150.0, 450.0),
    ("Abarrotes", 150.0, 450.0),
    ("Transporte (camión urbano)", 20.0, 45.0),
    ("Transporte (camión urbano)", 20.0, 45.0),
    ("Transporte (camión urbano)", 20.0, 45.0),
    ("Gasolina", 200.0, 400.0),
    ("Comida en la calle (tacos, comida corrida)", 40.0, 90.0),
    ("Comida en la calle (tacos, comida corrida)", 40.0, 90.0),
    ("Comida en la calle (tacos, comida corrida)", 40.0, 90.0),
    ("Recarga celular", 100.0, 200.0),
    ("Farmacia", 80.0, 250.0),
    ("Ropa", 200.0, 500.0),
]


def find_or_create_customer() -> dict:
    customers = nc.get_customers()
    for customer in customers:
        if (
            customer.get("first_name") == DEMO_FIRST_NAME
            and customer.get("last_name") == DEMO_LAST_NAME
        ):
            print(f"[seed] Customer demo ya existe: {customer['_id']}")
            return customer

    result = nc.create_customer(DEMO_FIRST_NAME, DEMO_LAST_NAME)
    customer = result["objectCreated"]
    print(f"[seed] Customer demo creado: {customer['_id']}")
    return customer


def find_or_create_account(customer_id: str) -> dict:
    accounts = nc.get_accounts_for_customer(customer_id)
    for account in accounts:
        if account.get("nickname") == DEMO_ACCOUNT_NICKNAME and account.get("type") == "Checking":
            print(f"[seed] Account demo ya existe: {account['_id']}")
            return account

    result = nc.create_account(
        customer_id=customer_id,
        account_type="Checking",
        nickname=DEMO_ACCOUNT_NICKNAME,
        balance=3200.00,
    )
    account = result["objectCreated"]
    print(f"[seed] Account demo creada: {account['_id']}")
    return account


def find_or_create_merchant() -> dict:
    merchants = nc.get_merchants()
    for merchant in merchants:
        if merchant.get("name") == DEMO_MERCHANT_NAME:
            print(f"[seed] Merchant demo ya existe: {merchant['_id']}")
            return merchant

    result = nc.create_merchant(
        name=DEMO_MERCHANT_NAME,
        category="food",
        address={
            "street_number": "123",
            "street_name": "Av HackMTY",
            "city": "Monterrey",
            "state": "NL",
            "zip": "64000",
        },
    )
    merchant = result["objectCreated"]
    print(f"[seed] Merchant demo creado: {merchant['_id']}")
    return merchant


def seed_purchases(account_id: str, merchant_id: str) -> None:
    existing = nc.get_purchases_for_account(account_id)
    if existing:
        print(f"[seed] Ya hay {len(existing)} purchases, no se siembran más.")
        return

    today = datetime.now()
    for i in range(15):
        days_ago = random.randint(0, 29)
        purchase_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        description, min_amount, max_amount = random.choice(PURCHASE_CATEGORIES)
        amount = round(random.uniform(min_amount, max_amount), 2)

        nc.create_purchase(
            account_id=account_id,
            merchant_id=merchant_id,
            medium="balance",
            purchase_date=purchase_date,
            amount=amount,
            description=description,
            status="completed",
        )
        print(f"[seed] Purchase {i + 1}/15 creada: {description} ${amount} ({purchase_date})")


def seed_bills(account_id: str) -> None:
    existing = nc.get_bills_for_account(account_id)
    if existing:
        print(f"[seed] Ya hay {len(existing)} bills, no se siembran más.")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    nc.create_bill(
        account_id=account_id,
        status="recurring",
        payee="Renta Departamento",
        nickname="Renta",
        payment_date=today_str,
        recurring_date=1,
        payment_amount=3500.00,
    )
    print("[seed] Bill 'Renta' creada.")

    nc.create_bill(
        account_id=account_id,
        status="recurring",
        payee="CFE e Internet",
        nickname="Servicios",
        payment_date=today_str,
        recurring_date=15,
        payment_amount=450.00,
    )
    print("[seed] Bill 'Servicios' creada.")

    nc.create_bill(
        account_id=account_id,
        status="recurring",
        payee="Casa de Empeño - Préstamo Personal",
        nickname="Préstamo",
        payment_date=today_str,
        recurring_date=10,
        payment_amount=800.00,
    )
    print("[seed] Bill 'Préstamo' creada (señal de vulnerabilidad financiera).")


def run() -> dict:
    customer = find_or_create_customer()
    account = find_or_create_account(customer["_id"])
    merchant = find_or_create_merchant()
    seed_purchases(account["_id"], merchant["_id"])
    seed_bills(account["_id"])
    return {"customer": customer, "account": account, "merchant": merchant}


if __name__ == "__main__":
    run()
    print("[seed] Listo.")
