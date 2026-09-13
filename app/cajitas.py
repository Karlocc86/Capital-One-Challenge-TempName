"""
Cajitas: una porción del saldo marcada como "apartada" para un gasto esencial
(renta, servicios), ligada a la fecha en que se necesita de verdad.

Es un registro NUESTRO en Postgres — no mueve dinero en Nessie (ni transfers
ni cuentas nuevas). El saldo disponible que debe ver el usuario es:

    disponible = saldo del ledger − Σ cajitas activas   (ver get_active_total)

Ciclo de vida: se crea "active" cuando el usuario acepta la propuesta del
Agente Guía; pasa a "released" cuando retira el dinero (a tiempo o antes —
`was_early_withdrawal` y `days_early_at_withdrawal` guardan cuántas veces se
ignoró la advertencia). "pending" existe en el enum por completitud pero
ninguna ruta lo usa hoy. Solo CRUD; las decisiones (¿advertir? ¿qué tono?)
viven en guide_agent.py y main.py.
"""

from datetime import date

from app.db import get_connection, release_connection
from app.schemas import CajitaOut

_COLUMNS = (
    "id, account_id, name, target_amount, linked_expense_name, reserve_date, "
    "status, was_early_withdrawal, days_early_at_withdrawal, created_at"
)


def _row_to_cajita(row) -> CajitaOut:
    return CajitaOut(
        id=row[0],
        account_id=row[1],
        name=row[2],
        target_amount=float(row[3]),
        linked_expense_name=row[4],
        reserve_date=row[5],
        status=row[6],
        was_early_withdrawal=bool(row[7]),
        days_early_at_withdrawal=row[8],
        created_at=row[9].isoformat(),
    )


def create_cajita(
    account_id: str,
    name: str,
    target_amount: float,
    linked_expense_name: str,
    reserve_date: date,
) -> tuple[CajitaOut, bool]:
    """
    Regresa (cajita, creada). Idempotente: si ya hay una cajita ACTIVA con el
    mismo `linked_expense_name` para la cuenta, la regresa tal cual (creada=False)
    en vez de duplicarla.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM cajitas "
                "WHERE account_id = %s AND linked_expense_name = %s AND status = 'active' "
                "ORDER BY created_at DESC LIMIT 1",
                (account_id, linked_expense_name),
            )
            row = cur.fetchone()
            if row:
                return _row_to_cajita(row), False

            cur.execute(
                "INSERT INTO cajitas (account_id, name, target_amount, linked_expense_name, reserve_date, status) "
                f"VALUES (%s, %s, %s, %s, %s, 'active') RETURNING {_COLUMNS}",
                (account_id, name, round(float(target_amount), 2), linked_expense_name, reserve_date),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        release_connection(conn)

    return _row_to_cajita(row), True


def get_cajitas_for_account(account_id: str) -> list[CajitaOut]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM cajitas WHERE account_id = %s "
                "ORDER BY (status = 'active') DESC, reserve_date, id",
                (account_id,),
            )
            rows = cur.fetchall()
    finally:
        release_connection(conn)

    return [_row_to_cajita(r) for r in rows]


def get_cajita(cajita_id: int) -> CajitaOut | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_COLUMNS} FROM cajitas WHERE id = %s", (cajita_id,))
            row = cur.fetchone()
    finally:
        release_connection(conn)

    return _row_to_cajita(row) if row else None


def get_active_total(account_id: str) -> float:
    """Σ target_amount de las cajitas activas: lo que hay que restar al saldo para obtener el disponible."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(target_amount), 0) FROM cajitas WHERE account_id = %s AND status = 'active'",
                (account_id,),
            )
            (total,) = cur.fetchone()
    finally:
        release_connection(conn)

    return round(float(total), 2)


def has_active_cajita_for_date(account_id: str, linked_expense_name: str, reserve_date: date) -> bool:
    """¿Ya se apartó dinero para este gasto en este ciclo? (para no repetir una propuesta ya aceptada)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM cajitas WHERE account_id = %s AND linked_expense_name = %s "
                "AND status = 'active' AND reserve_date >= %s LIMIT 1",
                (account_id, linked_expense_name, reserve_date),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def mark_released(cajita_id: int, was_early_withdrawal: bool, days_early: int) -> CajitaOut | None:
    """Libera la cajita: el monto vuelve a contar como disponible. Regresa None si no existe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE cajitas SET status = 'released', was_early_withdrawal = %s, days_early_at_withdrawal = %s "
                f"WHERE id = %s RETURNING {_COLUMNS}",
                (was_early_withdrawal, max(int(days_early), 0), cajita_id),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        release_connection(conn)

    return _row_to_cajita(row) if row else None
