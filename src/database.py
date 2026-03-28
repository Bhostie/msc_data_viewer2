import sqlite3
from typing import List, Dict, Optional, Sequence

# SQLite has a compile-time limit on bound parameters (default 999 on Windows).
# We chunk IN-clause queries to stay safely under this limit.
SQLITE_MAX_VARS = 900

def list_tables(conn: sqlite3.Connection) -> List[str]:
    """List all tables in the database."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall()]

def table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Get column names for a table."""
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    return [r[1] for r in cur.fetchall()]

def detect_keyboard_table(conn: sqlite3.Connection) -> Optional[str]:
    """Detect the most likely keyboard data table."""
    candidates = list_tables(conn)
    # Common AWARE plugin names
    preferred = [
        "plugin_keyboard",
        "keyboard",
        "aware_keyboard",
        "applications_keyboard",
    ]
    for p in preferred:
        if p in candidates:
            return p
    # Fallback: pick any table that has likely keyboard columns
    for t in candidates:
        cols = set(table_columns(conn, t))
        if {"timestamp"}.intersection(cols) and {"key_code", "key_character", "text"}.intersection(cols):
            return t
    return candidates[0] if candidates else None

def detect_pk_column(conn: sqlite3.Connection, table: str) -> str:
    """Detect the primary key column."""
    cols = set(table_columns(conn, table))
    for c in ["_id", "id", "ID"]:
        if c in cols:
            return c
    return "rowid"

def guess_columns(cols: List[str]) -> Dict[str, Optional[str]]:
    """Attempt to map standard column names to found columns."""
    lower = {c.lower(): c for c in cols}
    
    def pick(*names):
        for n in names:
            if n in lower:
                return lower[n]
        return None
    
    mapping = {
        "timestamp": pick("timestamp", "time", "ts"),
        "key_code": pick("key_code", "code", "keycode"),
        "key_character": pick("key_character", "character", "char", "key_char", "unicode"),
        "text": pick("text", "current_text", "message", "content", "field_text"),
        "package": pick("package_name", "package", "app", "application", "app_package"),
        "label": pick("label", "field", "hint", "view_label"),
        "action": pick("key_action", "action", "event"),
    }
    return mapping


def select_by_ids(
    conn: sqlite3.Connection,
    table: str,
    pk: str,
    ids: Sequence,
    columns: str = "*",
    order_by: Optional[str] = None,
) -> List[tuple]:
    """SELECT rows by primary-key IDs, chunked to avoid SQLite variable limits.

    Args:
        conn:     Open SQLite connection.
        table:    Table name.
        pk:       Primary-key column name.
        ids:      Sequence of row IDs to fetch.
        columns:  Column expression for SELECT (default ``"*"``).
        order_by: Optional ORDER BY expression (e.g. ``"timestamp"``).

    Returns:
        List of row tuples matching the given IDs.
    """
    all_rows: List[tuple] = []
    ids_list = list(ids)
    suffix = f" ORDER BY {order_by}" if order_by else ""
    for i in range(0, len(ids_list), SQLITE_MAX_VARS):
        chunk = ids_list[i : i + SQLITE_MAX_VARS]
        placeholders = ",".join("?" for _ in chunk)
        query = f'SELECT {columns} FROM "{table}" WHERE {pk} IN ({placeholders}){suffix}'
        all_rows.extend(conn.execute(query, chunk).fetchall())
    return all_rows
