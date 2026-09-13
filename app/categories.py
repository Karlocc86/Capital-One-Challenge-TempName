"""
Clasificación de movimientos para el análisis y las recomendaciones.

La categoría base de una compra es la del merchant en Nessie (Supermercado,
Transporte y combustible, ...). Aquí se refina con reglas simples y
generalizables (no dependen del dataset demo):

- "Comida chatarra": el merchant ya lo es (alitas, taquería) o la descripción
  menciona botana, refresco, papas, pizza, hamburguesa, etc. Así una compra de
  refresco en el OXXO cuenta como chatarra aunque el OXXO sea "Supermercado".
- "Gasto hormiga": compra chica (< HORMIGA_MAX) en tiendas de conveniencia,
  súper o similares (según la categoría del COMERCIO, no de la compra): el café
  y las papas del OXXO cuentan; los tacos o las alitas no (son comidas y ya
  viven en "Comida chatarra"); transporte y salud tampoco.

Puro cómputo, sin I/O.
"""

JUNK_FOOD = "Comida chatarra"
HORMIGA_MAX = 150.0

JUNK_FOOD_KEYWORDS = (
    "alitas", "boneless", "taco", "botana", "refresco", "papas", "pizza",
    "hamburguesa", "hot dog", "frituras", "dulces", "chocolate", "cerveza",
    "gansito", "sabritas", "coca",
)

# Categorías de COMERCIO donde una compra chica se considera hormiga.
HORMIGA_MERCHANT_CATEGORIES = {"Supermercado", "Comida y bebida", "Ropa", "Otros"}


def classify_purchase(merchant_category: str | None, description: str | None) -> str:
    """Categoría final de una compra a partir de la del merchant y su descripción."""
    text = (description or "").lower()
    if merchant_category == JUNK_FOOD or any(k in text for k in JUNK_FOOD_KEYWORDS):
        return JUNK_FOOD
    return merchant_category or "Otros"


def is_hormiga(amount: float, merchant_category: str | None) -> bool:
    return 0 < float(amount) < HORMIGA_MAX and (merchant_category or "Otros") in HORMIGA_MERCHANT_CATEGORIES


def spending_breakdown(purchases: list[dict], bills: list[dict], discretionary_bills: set[str]) -> dict:
    """
    Totales por área para el diagnóstico del agente. `purchases` ya traen
    `category` (ver cache.get_purchases) y `amount`.
    """
    junk = [p for p in purchases if p.get("category") == JUNK_FOOD]
    hormiga = [p for p in purchases if is_hormiga(p.get("amount", 0), p.get("merchant_category"))]
    subs = [b for b in bills if b.get("status") == "recurring" and b.get("nickname") in discretionary_bills]

    def _top(items: list[dict], key: str, n: int = 3) -> list[tuple[str, float, int]]:
        acc: dict[str, list[float]] = {}
        for it in items:
            acc.setdefault(it.get(key) or "?", []).append(float(it.get("amount", 0)))
        ranked = sorted(acc.items(), key=lambda kv: sum(kv[1]), reverse=True)[:n]
        return [(name, round(sum(v), 2), len(v)) for name, v in ranked]

    # Áreas de bienestar: transporte (moverse), salud (farmacia) y salidas
    # sociales (restaurantes de comida chatarra: alitas, tacos con amigos).
    transport = [p for p in purchases if p.get("merchant_category") == "Transporte y combustible"]
    health = [p for p in purchases if p.get("merchant_category") == "Salud"]
    outings = [p for p in purchases if p.get("merchant_category") == JUNK_FOOD]

    return {
        "transport_total": round(sum(p["amount"] for p in transport), 2),
        "transport_top": _top(transport, "merchant_name"),
        "health_total": round(sum(p["amount"] for p in health), 2),
        "health_count": len(health),
        "health_items": [p.get("description") for p in health if p.get("description")][:5],
        "outings_total": round(sum(p["amount"] for p in outings), 2),
        "outings_count": len(outings),
        "outings_items": [f"{p.get('merchant_name')}: {p.get('description')}" for p in outings if p.get("description")][:5],
        "junk_food_total": round(sum(p["amount"] for p in junk), 2),
        "junk_food_count": len(junk),
        "junk_food_top": _top(junk, "merchant_name"),
        "hormiga_total": round(sum(p["amount"] for p in hormiga), 2),
        "hormiga_count": len(hormiga),
        "hormiga_top": _top(hormiga, "merchant_name"),
        "subscriptions_total": round(sum(float(b.get("payment_amount", 0)) for b in subs), 2),
        "subscriptions": [(b.get("payee") or b.get("nickname"), float(b.get("payment_amount", 0))) for b in subs],
    }
