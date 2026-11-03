"""Process each payment exactly once, enforced by the database.

An in-process lock does not survive multiple workers or servers. A unique constraint
does. Call ``claim_payment`` inside the same transaction that credits the order, so the
claim and the credit commit or roll back together:

    with conn:  # one transaction
        if claim_payment(conn, verdict.payment_id):
            credit_order(conn, order_id)

PostgreSQL equivalent:

    INSERT INTO processed_payments (payment_id) VALUES ($1)
    ON CONFLICT (payment_id) DO NOTHING
    RETURNING payment_id;   -- a row back means this caller won the claim
"""

from __future__ import annotations

import sqlite3

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_payments (
    payment_id   TEXT PRIMARY KEY,
    processed_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SQLITE_SCHEMA)


def claim_payment(conn: sqlite3.Connection, payment_id: str) -> bool:
    """Return True for exactly one caller per payment_id; every other caller gets False."""
    if not payment_id:
        raise ValueError("payment_id is required")
    cursor = conn.execute(
        "INSERT OR IGNORE INTO processed_payments (payment_id) VALUES (?)", (payment_id,)
    )
    return cursor.rowcount == 1
