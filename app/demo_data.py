"""
Dataset demo de "Ricardo Torres": la fuente de verdad de lo que se siembra en
Nessie (scripts/seed.py) y de los montos reales que se guardan en el cache
(app/cache.py).

¿Por qué vive aquí y no solo en el seed? Nessie devuelve los montos de
purchases/deposits sin decimales (348.60 se guarda como 348). Para que la UI y
el forecast usen los números reales, el sync recupera el monto con centavos
desde este módulo (ver `real_amount`). Solo datos, sin lógica de negocio.

Perfil: trabajador de ingreso medio-bajo en Monterrey, calibrado con INEGI
(ENIGH 2024, decil III: ~$12,282 MXN/mes). Está calibrado para que sus
EGRESOS mensuales superen a sus INGRESOS (≈ $15,087 vs $12,282): compras
variables ≈ 48 % del ingreso — súper y transporte (proporciones ENIGH) más
~$2,100 de comida chatarra (Las Alitas, tacos, botanas del OXXO) — más renta,
servicios y 7 suscripciones prescindibles (~$1,533/mes). Con el saldo inicial
de abajo el forecaster proyecta insolvencia ~9 días después del seed (antes de
la quincena) y la renta del día 1 lo vuelve a hundir — la señal de
vulnerabilidad que el pitch quiere mostrar, con salidas obvias: cancelar
suscripciones y recortar chatarra/hormiga.
"""

DEMO_FIRST_NAME = "Ricardo"
DEMO_LAST_NAME = "Torres"
DEMO_CHECKING_NICKNAME = "Cuenta de Cheques"
DEMO_CHECKING_BALANCE = 5170.00  # saldo inicial al arranque del historial (hace 30 días)
DEMO_SAVINGS_NICKNAME = "Ahorro"
DEMO_SAVINGS_BALANCE = 500.00
DEMO_EMPLOYER = "Maquilas del Norte SA de CV"
DEMO_MONTHLY_INCOME = 12282.00  # ENIGH 2024, decil III

# La `category` que se manda a Nessie es directamente la etiqueta que pinta la
# UI (una sola fuente de verdad, sin tabla de mapeo).
MERCHANTS = [
    {"name": "OXXO", "category": "Supermercado",
     "address": {"street_number": "1234", "street_name": "Av. Ruiz Cortines", "city": "Monterrey", "state": "NL", "zip": "64320"}},
    {"name": "Soriana Híper", "category": "Supermercado",
     "address": {"street_number": "3000", "street_name": "Av. Lincoln", "city": "Monterrey", "state": "NL", "zip": "64610"}},
    {"name": "Pemex", "category": "Transporte y combustible",
     "address": {"street_number": "500", "street_name": "Av. Gonzalitos", "city": "Monterrey", "state": "NL", "zip": "64620"}},
    {"name": "Camión Urbano MTY", "category": "Transporte y combustible",
     "address": {"street_number": "100", "street_name": "Av. Colón", "city": "Monterrey", "state": "NL", "zip": "64000"}},
    {"name": "Tacos El Güero", "category": "Comida chatarra",
     "address": {"street_number": "800", "street_name": "Calle Aramberri", "city": "Monterrey", "state": "NL", "zip": "64000"}},
    {"name": "Las Alitas", "category": "Comida chatarra",
     "address": {"street_number": "2500", "street_name": "Av. Eugenio Garza Sada", "city": "Monterrey", "state": "NL", "zip": "64840"}},
    {"name": "Telcel", "category": "Servicios y facturas",
     "address": {"street_number": "2400", "street_name": "Av. Garza Sada", "city": "Monterrey", "state": "NL", "zip": "64700"}},
    {"name": "Farmacias Guadalajara", "category": "Salud",
     "address": {"street_number": "1500", "street_name": "Av. Simón Bolívar", "city": "Monterrey", "state": "NL", "zip": "64460"}},
    {"name": "Coppel", "category": "Ropa",
     "address": {"street_number": "500", "street_name": "Av. Juárez", "city": "Monterrey", "state": "NL", "zip": "64000"}},
]

# (días atrás, comercio, monto MXN, descripción). Total: $5,903.50 en 30 días
# (≈ 48 % del ingreso). Comida chatarra (alitas, tacos, botanas) ≈ $2,250 y
# gastos hormiga (compras < $150 en OXXO: café, chicles, papas...) ≈ $517.
PURCHASES = [
    (29, "Soriana Híper", 610.00, "Despensa semanal"),
    (28, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (27, "OXXO", 113.00, "Botana y refresco"),
    (26, "Tacos El Güero", 136.50, "Cena tacos"),
    (25, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (25, "OXXO", 45.00, "Café y donas"),
    (24, "Pemex", 525.00, "Gasolina"),
    (23, "OXXO", 73.50, "Agua y pan"),
    (22, "Las Alitas", 389.00, "Alitas y cerveza con amigos"),
    (21, "Farmacias Guadalajara", 266.00, "Medicamento"),
    (20, "Camión Urbano MTY", 38.50, "Camión con transbordo"),
    (20, "OXXO", 38.50, "Chicles y agua"),
    (19, "Tacos El Güero", 114.00, "Comida corrida"),
    (18, "Telcel", 175.00, "Recarga Amigo"),
    (17, "Soriana Híper", 459.00, "Despensa semanal"),
    (16, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (15, "OXXO", 154.00, "Leche, huevo y tortillas"),
    (14, "OXXO", 58.00, "Papas y refresco"),
    (13, "Tacos El Güero", 126.00, "Cena tacos"),
    (12, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (11, "Las Alitas", 456.00, "Alitas boneless y refrescos"),
    (10, "Coppel", 331.00, "Playera y calcetines"),
    (9, "OXXO", 61.00, "Refresco"),
    (8, "Camión Urbano MTY", 38.50, "Camión con transbordo"),
    (7, "OXXO", 49.00, "Pan dulce y jugo"),
    (6, "Soriana Híper", 423.00, "Despensa semanal"),
    (5, "Tacos El Güero", 121.00, "Comida corrida"),
    (4, "Farmacias Guadalajara", 137.50, "Analgésicos"),
    (3, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (3, "OXXO", 42.00, "Galletas y café"),
    (2, "OXXO", 168.00, "Despensa rápida"),
    (1, "Las Alitas", 412.00, "Alitas y papas, partido de futbol"),
    (1, "Tacos El Güero", 108.50, "Cena tacos"),
    (0, "Camión Urbano MTY", 33.00, "Camión ida y vuelta"),
    (0, "OXXO", 37.00, "Refresco y chocolate"),
]

# (días atrás, monto, descripción). Dos quincenas = DEMO_MONTHLY_INCOME.
# La última cayó hace 3 días: el forecaster infiere la siguiente en 12 días.
DEPOSITS = [
    (18, 6141.00, "Nómina quincenal - Maquilas del Norte"),
    (3, 6141.00, "Nómina quincenal - Maquilas del Norte"),
]

# (nickname, payee, monto, día del mes en que se cobra). Total: $9,183/mes.
# Además de renta y servicios, 7 suscripciones prescindibles (precios MXN
# 2026): son justo lo que el agente puede proponer cancelar/pausar.
BILLS = [
    ("Renta", "Renta Departamento", 7000.00, 1),
    ("Servicios", "CFE e Internet", 650.00, 15),
    ("Netflix", "Netflix", 249.00, 8),
    ("HBO Max", "HBO Max", 149.00, 12),
    ("Disney+", "Disney+", 179.00, 3),
    ("Spotify", "Spotify Premium", 129.00, 20),
    ("Amazon Prime", "Amazon Prime", 99.00, 18),
    ("Xbox Game Pass", "Xbox Game Pass Ultimate", 229.00, 22),
    ("Smart Fit", "Smart Fit Gimnasio", 499.00, 7),
]

# Bills que el usuario puede cancelar sin consecuencias graves (para /actions
# y para que el agente las distinga de renta/servicios).
DISCRETIONARY_BILLS = {"Netflix", "HBO Max", "Disney+", "Spotify", "Amazon Prime", "Xbox Game Pass", "Smart Fit"}


def movement_key(amount: float, description: str) -> tuple[int, str]:
    """Llave para reconocer un movimiento de Nessie: parte entera del monto + descripción."""
    return (int(float(amount)), description or "")


# {(monto entero, descripción): monto real con centavos}. Las descripciones
# repetidas ("Camión ida y vuelta") tienen siempre el mismo monto entero, así
# que la llave es suficiente.
_REAL_AMOUNTS: dict[tuple[int, str], float] = {}
for _, _, _amount, _description in PURCHASES:
    _REAL_AMOUNTS[movement_key(_amount, _description)] = float(_amount)
for _, _amount, _description in DEPOSITS:
    _REAL_AMOUNTS[movement_key(_amount, _description)] = float(_amount)


def real_amount(amount: float, description: str) -> float:
    """Monto con centavos del dataset si el movimiento es del seed; si no, el que venga de Nessie."""
    return _REAL_AMOUNTS.get(movement_key(amount, description), float(amount))


def opening_balance_for(account: dict) -> float:
    """
    Saldo inicial de una cuenta. Nessie no permite cambiar `balance` después
    de crear la cuenta (el PUT lo ignora), así que para la cuenta demo el
    saldo inicial vive aquí y no en Nessie; las demás cuentas usan el suyo.
    """
    if account.get("nickname") == DEMO_CHECKING_NICKNAME and account.get("type") == "Checking":
        return DEMO_CHECKING_BALANCE
    return float(account.get("balance") or 0.0)
