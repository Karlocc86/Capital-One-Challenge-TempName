"""
Siembra el "mundo" del usuario demo en Nessie: un customer, una cuenta
Checking y una Savings, 8 merchants de Monterrey, 26 purchases fijas de los
últimos 30 días, 2 depósitos de nómina (quincenas) y 4 bills recurrentes.

El dataset es DETERMINISTA (nada de random): cada purchase tiene su comercio,
monto y día relativo a hoy escritos a mano. Así el forecast siempre proyecta
lo mismo (~11 días a la insolvencia) y la UI siempre muestra las mismas
transacciones.

Perfil demo: "Ricardo Torres", trabajador de ingreso medio-bajo en Monterrey.
Los montos están calibrados con datos reales del INEGI (ENIGH 2024, decil
III de ingreso: $36,845 MXN de ingreso corriente trimestral promedio, ~$12,282
MXN/mes) — no son números arbitrarios, representan un perfil de vulnerabilidad
financiera real, incluyendo un pago recurrente a una casa de empeño/préstamo
personal informal, justo el tipo de señal que el forecast debe detectar.

Idempotencia:
- customer / accounts / merchants / bills: find-or-create por nombre.
- purchases / deposits: se comparan por (fecha, monto, descripción) contra lo
  que ya hay en Nessie y solo se crean las faltantes. Como las fechas son
  relativas a hoy, si se detectan movimientos de una siembra de otro día el
  script se detiene y pide correr con --reset.

Uso:
    python scripts/seed.py            # siembra (o completa) el dataset
    python scripts/seed.py --reset    # recrea la cuenta de cheques (nuevo account_id,
                                      # actualiza .env y web/.env.local) y resiembra
                                      # relativo a hoy (correr la mañana del pitch;
                                      # después: init_db + sync + reiniciar backend/frontend)
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import nessie_client as nc
from app.demo_data import (
    BILLS,
    DEMO_CHECKING_BALANCE,
    DEMO_CHECKING_NICKNAME,
    DEMO_FIRST_NAME,
    DEMO_LAST_NAME,
    DEMO_SAVINGS_BALANCE,
    DEMO_SAVINGS_NICKNAME,
    DEPOSITS,
    MERCHANTS,
    PURCHASES,
    movement_key,
)


def _date_str(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")


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


def find_or_create_account(customer_id: str, account_type: str, nickname: str, balance: float) -> dict:
    accounts = nc.get_accounts_for_customer(customer_id)
    for account in accounts:
        if account.get("nickname") == nickname and account.get("type") == account_type:
            print(f"[seed] Account '{nickname}' ya existe: {account['_id']}")
            return account

    result = nc.create_account(
        customer_id=customer_id,
        account_type=account_type,
        nickname=nickname,
        balance=balance,
    )
    account = result["objectCreated"]
    print(f"[seed] Account '{nickname}' ({account_type}) creada: {account['_id']}")
    return account


def find_or_create_merchants() -> dict[str, dict]:
    """Devuelve {nombre: merchant}. Los merchants en Nessie son por API key, no hay colisión con otros equipos."""
    existing = {m.get("name"): m for m in nc.get_merchants()}
    merchants: dict[str, dict] = {}
    for spec in MERCHANTS:
        if spec["name"] in existing:
            merchants[spec["name"]] = existing[spec["name"]]
            continue
        result = nc.create_merchant(
            name=spec["name"],
            category=spec["category"],
            address=spec["address"],
        )
        merchants[spec["name"]] = result["objectCreated"]
        print(f"[seed] Merchant '{spec['name']}' creado: {merchants[spec['name']]['_id']}")
    print(f"[seed] Merchants listos: {len(merchants)}")
    return merchants


def _key(date_str: str, amount: float, description: str) -> tuple:
    # Nessie devuelve los montos sin decimales (348.60 → 348); se compara la
    # parte entera para no duplicar movimientos (ver app/demo_data.py).
    return (date_str, *movement_key(amount, description))


def seed_purchases(account_id: str, merchants: dict[str, dict]) -> None:
    existing = nc.get_purchases_for_account(account_id)
    existing_keys = {_key(p["purchase_date"], p["amount"], p.get("description", "")) for p in existing}
    expected = {
        _key(_date_str(days_ago), amount, description): (merchant_name, days_ago)
        for days_ago, merchant_name, amount, description in PURCHASES
    }

    stale = existing_keys - set(expected)
    if stale:
        print(
            f"[seed] Purchases de otra siembra detectadas ({len(stale)}); las fechas ya no "
            "coinciden con hoy. Corre: python scripts/seed.py --reset"
        )
        return

    missing = [k for k in expected if k not in existing_keys]
    if not missing:
        print(f"[seed] Purchases ya sembradas ({len(existing)}), nada que crear.")
        return

    for i, key in enumerate(missing, start=1):
        purchase_date, amount, description = key
        merchant_name, _ = expected[key]
        nc.create_purchase(
            account_id=account_id,
            merchant_id=merchants[merchant_name]["_id"],
            medium="balance",
            purchase_date=purchase_date,
            amount=amount,
            description=description,
            status="completed",
        )
        print(f"[seed] Purchase {i}/{len(missing)}: {merchant_name} ${amount:.2f} ({purchase_date}) - {description}")


def seed_deposits(account_id: str) -> None:
    existing = nc.get_deposits_for_account(account_id)
    existing_keys = {_key(d["transaction_date"], d["amount"], d.get("description", "")) for d in existing}
    expected = {_key(_date_str(days_ago), amount, description) for days_ago, amount, description in DEPOSITS}

    stale = existing_keys - expected
    if stale:
        print(
            f"[seed] Deposits de otra siembra detectados ({len(stale)}). "
            "Corre: python scripts/seed.py --reset"
        )
        return

    missing = [k for k in expected if k not in existing_keys]
    if not missing:
        print(f"[seed] Deposits ya sembrados ({len(existing)}), nada que crear.")
        return

    for transaction_date, amount, description in sorted(missing):
        nc.create_deposit(
            account_id=account_id,
            amount=amount,
            transaction_date=transaction_date,
            description=description,
        )
        print(f"[seed] Deposit: ${amount:.2f} ({transaction_date}) - {description}")


def seed_bills(account_id: str) -> None:
    existing = {b.get("nickname") for b in nc.get_bills_for_account(account_id)}
    today_str = _date_str(0)
    for nickname, payee, amount, recurring_date in BILLS:
        if nickname in existing:
            print(f"[seed] Bill '{nickname}' ya existe.")
            continue
        nc.create_bill(
            account_id=account_id,
            status="recurring",
            payee=payee,
            nickname=nickname,
            payment_date=today_str,
            recurring_date=recurring_date,
            payment_amount=amount,
        )
        print(f"[seed] Bill '{nickname}' creada: ${amount:.2f} el día {recurring_date}.")


def recreate_checking(customer_id: str, old_account: dict) -> dict:
    """
    En este Nessie las purchases NO se pueden borrar ni editar (todas las rutas
    /purchases/{id} responden 403), pero sí se puede borrar la cuenta completa.
    Así que --reset borra la cuenta de cheques y la crea de nuevo (nuevo
    account_id) para resembrar relativo a hoy con los montos actuales.
    """
    nc.delete_account(old_account["_id"])
    print(f"[seed] --reset: cuenta '{old_account['nickname']}' {old_account['_id']} borrada (con sus movimientos).")
    result = nc.create_account(
        customer_id=customer_id,
        account_type="Checking",
        nickname=DEMO_CHECKING_NICKNAME,
        balance=DEMO_CHECKING_BALANCE,
    )
    account = result["objectCreated"]
    print(f"[seed] --reset: cuenta '{DEMO_CHECKING_NICKNAME}' recreada: {account['_id']}")
    return account


ENV_FILES = (
    (Path(__file__).resolve().parent.parent / ".env", "DEMO_ACCOUNT_ID"),
    (Path(__file__).resolve().parent.parent / "web" / ".env.local", "NEXT_PUBLIC_DEMO_ACCOUNT_ID"),
)


def update_env_files(account_id: str) -> None:
    """Deja el account_id nuevo en .env y web/.env.local (solo esas líneas; si no existe el archivo, no lo crea)."""
    for path, key in ENV_FILES:
        if not path.exists():
            print(f"[seed] {path.name} no existe; agrega a mano {key}={account_id}")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        new_line = f"{key}={account_id}"
        if any(line.startswith(f"{key}=") for line in lines):
            lines = [new_line if line.startswith(f"{key}=") else line for line in lines]
        else:
            lines.append(new_line)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[seed] {path.relative_to(path.parent.parent)}: {new_line}")


def run(reset: bool = False) -> dict:
    customer = find_or_create_customer()
    checking = find_or_create_account(customer["_id"], "Checking", DEMO_CHECKING_NICKNAME, DEMO_CHECKING_BALANCE)
    savings = find_or_create_account(customer["_id"], "Savings", DEMO_SAVINGS_NICKNAME, DEMO_SAVINGS_BALANCE)
    merchants = find_or_create_merchants()

    if reset:
        checking = recreate_checking(customer["_id"], checking)
        update_env_files(checking["_id"])

    seed_purchases(checking["_id"], merchants)
    seed_deposits(checking["_id"])
    seed_bills(checking["_id"])

    # "account" y "merchant" se mantienen por compatibilidad con test_connection.py
    return {
        "customer": customer,
        "account": checking,
        "savings": savings,
        "merchant": next(iter(merchants.values())),
        "merchants": merchants,
    }


def _print_summary(seeded: dict) -> None:
    checking = nc.get_account(seeded["account"]["_id"])
    savings = nc.get_account(seeded["savings"]["_id"])
    purchases = nc.get_purchases_for_account(checking["_id"])
    deposits = nc.get_deposits_for_account(checking["_id"])
    bills = nc.get_bills_for_account(checking["_id"])
    number = str(checking.get("account_number", ""))

    print("\n=== SEED LISTO ===")
    print(f"Customer : {seeded['customer']['_id']}")
    print(f"Checking : {checking['_id']}  ('{checking['nickname']}' •••• {number[-4:]}, balance ${checking['balance']})")
    print(f"Savings  : {savings['_id']}  ('{savings['nickname']}', balance ${savings['balance']})")
    print(f"Merchants: {len(seeded['merchants'])}")
    print(f"Purchases: {len(purchases)} (total ${sum(p['amount'] for p in purchases):.2f})")
    print(f"Deposits : {len(deposits)} (total ${sum(d['amount'] for d in deposits):.2f})")
    print(f"Bills    : {len(bills)}")
    print("\nSiguientes pasos:")
    print(f"  1) DEMO_ACCOUNT_ID={checking['_id']} en .env  y  NEXT_PUBLIC_DEMO_ACCOUNT_ID={checking['_id']} en web/.env.local")
    print(f"  2) python scripts/init_db.py && python scripts/sync.py {checking['_id']}")
    print(f"  3) curl http://localhost:8000/summary/{checking['_id']}")


if __name__ == "__main__":
    seeded = run(reset="--reset" in sys.argv)
    _print_summary(seeded)
