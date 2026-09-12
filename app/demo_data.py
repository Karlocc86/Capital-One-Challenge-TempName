"""
Dataset demo de "Ricardo Torres": la fuente de verdad de lo que se siembra en
Nessie (scripts/seed.py) y de los montos reales que se guardan en el cache
(app/cache.py).

¿Por qué vive aquí y no solo en el seed? Nessie devuelve los montos de
purchases/deposits sin decimales (348.60 se guarda como 348). Para que la UI y
el forecast usen los números reales, el sync recupera el monto con centavos
desde este módulo (ver `real_amount`). Solo datos, sin lógica de negocio.

Perfil: trabajador de ingreso medio-bajo en Monterrey, calibrado con INEGI
(ENIGH 2024, decil III: ~$12,282 MXN/mes). Incluye un pago recurrente a una
casa de empeño — la señal de vulnerabilidad que el forecast debe detectar.
"""

DEMO_FIRST_NAME = "Ricardo"
DEMO_LAST_NAME = "Torres"
DEMO_CHECKING_NICKNAME = "Cuenta de Cheques"
DEMO_CHECKING_BALANCE = 3200.00
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
    {"name": "Tacos El Güero", "category": "Comida y bebida",
     "address": {"street_number": "800", "street_name": "Calle Aramberri", "city": "Monterrey", "state": "NL", "zip": "64000"}},
    {"name": "Telcel", "category": "Servicios y facturas",
     "address": {"street_number": "2400", "street_name": "Av. Garza Sada", "city": "Monterrey", "state": "NL", "zip": "64700"}},
    {"name": "Farmacias Guadalajara", "category": "Salud",
     "address": {"street_number": "1500", "street_name": "Av. Simón Bolívar", "city": "Monterrey", "state": "NL", "zip": "64460"}},
    {"name": "Coppel", "category": "Ropa",
     "address": {"street_number": "500", "street_name": "Av. Juárez", "city": "Monterrey", "state": "NL", "zip": "64000"}},
]

# (días atrás, comercio, monto MXN, descripción). Total: $2,501.70 en 30 días.
# Alimentos + súper ≈ 61%, transporte ≈ 18% (proporciones ENIGH decil III).
# Con las bills de abajo el forecaster da ~235/día → insolvencia en ~13 días.
PURCHASES = [
    (29, "Soriana Híper", 348.60, "Despensa semanal"),
    (28, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
    (27, "OXXO", 64.50, "Botana y refresco"),
    (26, "Tacos El Güero", 78.00, "Cena tacos"),
    (25, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
    (24, "Pemex", 300.00, "Gasolina"),
    (23, "OXXO", 42.00, "Agua y pan"),
    (21, "Farmacias Guadalajara", 152.00, "Medicamento"),
    (20, "Camión Urbano MTY", 22.00, "Camión con transbordo"),
    (19, "Tacos El Güero", 65.00, "Comida corrida"),
    (18, "Telcel", 100.00, "Recarga Amigo"),
    (17, "Soriana Híper", 262.30, "Despensa semanal"),
    (16, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
    (15, "OXXO", 88.00, "Leche, huevo y tortillas"),
    (13, "Tacos El Güero", 72.00, "Cena tacos"),
    (12, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
    (10, "Coppel", 189.00, "Playera y calcetines"),
    (9, "OXXO", 35.00, "Refresco"),
    (8, "Camión Urbano MTY", 22.00, "Camión con transbordo"),
    (6, "Soriana Híper", 241.80, "Despensa semanal"),
    (5, "Tacos El Güero", 69.00, "Comida corrida"),
    (4, "Farmacias Guadalajara", 78.50, "Analgésicos"),
    (3, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
    (2, "OXXO", 96.00, "Despensa rápida"),
    (1, "Tacos El Güero", 62.00, "Cena tacos"),
    (0, "Camión Urbano MTY", 19.00, "Camión ida y vuelta"),
]

# (días atrás, monto, descripción). Dos quincenas = DEMO_MONTHLY_INCOME.
DEPOSITS = [
    (25, 6141.00, "Nómina quincenal - Maquilas del Norte"),
    (10, 6141.00, "Nómina quincenal - Maquilas del Norte"),
]

# (nickname, payee, monto, día del mes en que se cobra)
BILLS = [
    ("Renta", "Renta Departamento", 3500.00, 1),
    ("Servicios", "CFE e Internet", 450.00, 15),
    ("Préstamo", "Casa de Empeño - Préstamo Personal", 800.00, 10),
]


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
