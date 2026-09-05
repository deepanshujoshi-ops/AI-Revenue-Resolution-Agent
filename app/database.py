import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, "revenue_agent.db")

print("DATABASE FILE:", DB_NAME)

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS merchant_orders (
            order_id TEXT PRIMARY KEY,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            payment_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resolutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            payment_id TEXT,
            issue_type TEXT NOT NULL,
            action TEXT NOT NULL,
            amount_at_risk INTEGER DEFAULT 0,
            amount_recovered INTEGER DEFAULT 0,
            reason TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            failed_payment_id TEXT NOT NULL UNIQUE,
            amount INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'OPEN',
            recovery_link_id TEXT,
            recovery_link_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def create_order(order_id, amount, status="PENDING", payment_id=None):
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    conn.execute("""
        INSERT OR REPLACE INTO merchant_orders
        (order_id, amount, status, payment_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, amount, status, payment_id, now, now))

    conn.commit()
    conn.close()


def get_order(order_id):
    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM merchant_orders WHERE order_id = ?",
            (order_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


def update_order(order_id, status, payment_id=None):
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    cursor = conn.execute("""
        UPDATE merchant_orders
        SET status = ?, payment_id = ?, updated_at = ?
        WHERE order_id = ?
    """, (status, payment_id, now, order_id))

    conn.commit()

    rows_updated = cursor.rowcount

    conn.close()

    return rows_updated


def add_resolution(
    order_id,
    payment_id,
    issue_type,
    action,
    amount_at_risk,
    amount_recovered,
    reason
):
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    conn.execute("""
        INSERT INTO resolutions
        (
            order_id,
            payment_id,
            issue_type,
            action,
            amount_at_risk,
            amount_recovered,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        payment_id,
        issue_type,
        action,
        amount_at_risk,
        amount_recovered,
        reason,
        now
    ))
def get_recovery_case(failed_payment_id):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM recovery_cases
            WHERE failed_payment_id = ?
            """,
            (failed_payment_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


def create_recovery_case(
    order_id,
    failed_payment_id,
    amount,
    recovery_link_id,
    recovery_link_url
):
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    try:
        conn.execute(
            """
            INSERT INTO recovery_cases
            (
                order_id,
                failed_payment_id,
                amount,
                attempts,
                status,
                recovery_link_id,
                recovery_link_url,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 1, 'LINK_CREATED', ?, ?, ?, ?)
            """,
            (
                order_id,
                failed_payment_id,
                amount,
                recovery_link_id,
                recovery_link_url,
                now,
                now
            )
        )

        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    finally:
        conn.close()

def get_recovery_case_by_link_id(recovery_link_id):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM recovery_cases
            WHERE recovery_link_id = ?
            """,
            (recovery_link_id,)
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


def mark_recovery_recovered(
    recovery_link_id,
    payment_id
):
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    try:
        cursor = conn.execute(
            """
            UPDATE recovery_cases
            SET status = 'RECOVERED',
                updated_at = ?
            WHERE recovery_link_id = ?
              AND status = 'LINK_CREATED'
            """,
            (
                now,
                recovery_link_id
            )
        )

        conn.commit()

        return cursor.rowcount

    finally:
        conn.close()

def get_open_recovery_case():
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT *
            FROM recovery_cases
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()

def get_dashboard_data():
    conn = get_connection()

    try:
        # Money that is still genuinely at risk.
        at_risk = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM recovery_cases
            WHERE status = 'LINK_CREATED'
        """).fetchone()

        # Money that has actually been recovered.
        recovered = conn.execute("""
            SELECT COALESCE(SUM(amount_recovered), 0) AS total
            FROM resolutions
            WHERE action = 'RECOVERED'
        """).fetchone()

        # Successfully completed resolution actions.
        resolved = conn.execute("""
            SELECT COUNT(*) AS total
            FROM resolutions
            WHERE action IN ('RECOVERED', 'MARK_ORDER_PAID')
        """).fetchone()

        # Cases that required escalation.
        escalated = conn.execute("""
            SELECT COUNT(*) AS total
            FROM resolutions
            WHERE action = 'ESCALATE'
        """).fetchone()

        # Recent resolution activity.
        resolutions = conn.execute("""
            SELECT
                order_id,
                payment_id,
                issue_type,
                action,
                amount_at_risk,
                amount_recovered,
                reason,
                created_at
            FROM resolutions
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()

        # Recovery cases, including their current status.
        recovery_cases = conn.execute("""
            SELECT
                order_id,
                failed_payment_id,
                amount,
                attempts,
                status,
                recovery_link_id,
                recovery_link_url,
                created_at,
                updated_at
            FROM recovery_cases
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()

        return {
            "stats": {
                "at_risk": at_risk["total"],
                "recovered": recovered["total"],
                "resolved": resolved["total"],
                "escalated": escalated["total"]
            },

            "resolutions": [
                dict(row)
                for row in resolutions
            ],

            "recovery_cases": [
                dict(row)
                for row in recovery_cases
            ]
        }

    finally:
        conn.close()
def recovery_resolution_exists(order_id):
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT 1
            FROM resolutions
            WHERE order_id = ?
              AND issue_type = 'PAYMENT_RECOVERY'
              AND action = 'RECOVERED'
            LIMIT 1
            """,
            (order_id,)
        ).fetchone()

        return row is not None

    finally:
        conn.close()


def reset_database():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM recovery_cases")
        conn.execute("DELETE FROM resolutions")
        conn.execute("DELETE FROM merchant_orders")
        conn.commit()
    finally:
        conn.close()