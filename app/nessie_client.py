"""
Único módulo que habla con la API de Nessie. No meter lógica de negocio aquí
(nada de forecast, scoring, ni feature engineering) — solo requests HTTP.
"""

import httpx

from app.config import NESSIE_API_KEY, NESSIE_BASE_URL


class NessieError(Exception):
    def __init__(self, method: str, url: str, status_code: int, body: str):
        self.method = method
        self.url = url
        self.status_code = status_code
        self.body = body
        super().__init__(
            f"Nessie error: {method} {url} -> {status_code}\nBody: {body}"
        )


def _request(method: str, path: str, params: dict | None = None, json: dict | None = None) -> dict:
    url = f"{NESSIE_BASE_URL}{path}"
    query = {"key": NESSIE_API_KEY, **(params or {})}

    with httpx.Client(timeout=15.0) as client:
        response = client.request(method, url, params=query, json=json)

    if response.status_code >= 400:
        print(f"[NESSIE ERROR] {method} {url}")
        print(f"[NESSIE ERROR] status_code={response.status_code}")
        print(f"[NESSIE ERROR] body={response.text}")
        raise NessieError(method, url, response.status_code, response.text)

    if not response.text:
        return {}

    return response.json()


# ---------- Customers ----------

def create_customer(first_name: str, last_name: str) -> dict:
    payload = {"first_name": first_name, "last_name": last_name}
    return _request("POST", "/customers", json=payload)


def get_customers() -> list[dict]:
    return _request("GET", "/customers")


def get_customer(customer_id: str) -> dict:
    return _request("GET", f"/customers/{customer_id}")


# ---------- Accounts ----------

def create_account(
    customer_id: str,
    account_type: str,
    nickname: str,
    balance: float,
    rewards: int = 0,
) -> dict:
    """account_type debe ser uno de: 'Credit Card', 'Savings', 'Checking'."""
    payload = {
        "type": account_type,
        "nickname": nickname,
        "rewards": rewards,
        "balance": balance,
    }
    return _request("POST", f"/customers/{customer_id}/accounts", json=payload)


def get_accounts_for_customer(customer_id: str) -> list[dict]:
    return _request("GET", f"/customers/{customer_id}/accounts")


def get_account(account_id: str) -> dict:
    return _request("GET", f"/accounts/{account_id}")


def delete_account(account_id: str) -> dict:
    return _request("DELETE", f"/accounts/{account_id}")


# ---------- Purchases ----------

def create_purchase(
    account_id: str,
    merchant_id: str,
    medium: str,
    purchase_date: str,
    amount: float,
    description: str = "",
    status: str = "pending",
) -> dict:
    """
    medium debe ser 'balance' o 'rewards'. purchase_date en formato YYYY-MM-DD.
    status es requerido por Nessie aunque no aparece en la doc pública del POST
    (el GET falla al deserializar purchases creados sin status) — usar
    'pending', 'completed' o 'cancelled'.
    """
    payload = {
        "merchant_id": merchant_id,
        "medium": medium,
        "purchase_date": purchase_date,
        "amount": amount,
        "description": description,
        "status": status,
    }
    return _request("POST", f"/accounts/{account_id}/purchases", json=payload)


def get_purchases_for_account(account_id: str) -> list[dict]:
    return _request("GET", f"/accounts/{account_id}/purchases")


def get_purchase(purchase_id: str) -> dict:
    return _request("GET", f"/purchases/{purchase_id}")


def delete_purchase(purchase_id: str) -> dict:
    return _request("DELETE", f"/purchases/{purchase_id}")


# ---------- Bills ----------

def create_bill(
    account_id: str,
    status: str,
    payee: str,
    nickname: str,
    payment_date: str,
    recurring_date: int,
    payment_amount: float,
) -> dict:
    """status debe ser 'cancelled', 'pending' o 'recurring'."""
    payload = {
        "status": status,
        "payee": payee,
        "nickname": nickname,
        "payment_date": payment_date,
        "recurring_date": recurring_date,
        "payment_amount": payment_amount,
    }
    return _request("POST", f"/accounts/{account_id}/bills", json=payload)


def get_bills_for_account(account_id: str) -> list[dict]:
    return _request("GET", f"/accounts/{account_id}/bills")


def get_bill(bill_id: str) -> dict:
    return _request("GET", f"/bills/{bill_id}")


# ---------- Merchants ----------

def get_merchants() -> list[dict]:
    return _request("GET", "/merchants")


def create_merchant(name: str, category: str, address: dict, geocode: dict | None = None) -> dict:
    payload = {"name": name, "category": category, "address": address}
    if geocode:
        payload["geocode"] = geocode
    return _request("POST", "/merchants", json=payload)
