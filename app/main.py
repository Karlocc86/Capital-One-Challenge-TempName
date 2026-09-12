from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.nessie_client import NessieError, get_account, get_purchases_for_account

app = FastAPI(title="Fin de Mes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"data": {"status": "ok"}, "meta": {}}


@app.get("/summary/{account_id}")
def summary(account_id: str):
    try:
        account = get_account(account_id)
        purchases = get_purchases_for_account(account_id)
    except NessieError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo obtener el account {account_id} de Nessie: {e.body}",
        )

    total_spent = sum(purchase["amount"] for purchase in purchases)

    return {
        "data": {
            "account_id": account["_id"],
            "nickname": account["nickname"],
            "balance": account["balance"],
            "total_spent": round(total_spent, 2),
            "purchase_count": len(purchases),
        },
        "meta": {},
    }
