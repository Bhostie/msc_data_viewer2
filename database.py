import sqlite3
from typing import List, Dict, Optional

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
