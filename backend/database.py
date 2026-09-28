import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_FILE = Path(__file__).parent / "tutor.db"

def get_connection(db_path: Path = DB_FILE) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory configured for dictionary-like access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Path = DB_FILE) -> None:
    """Initializes the SQLite database schema if tables do not exist."""
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS state_snapshots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                state_json TEXT NOT NULL,
                mastery_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()

def create_session(session_id: Optional[str] = None, db_path: Path = DB_FILE) -> str:
    """Creates a new tutoring session."""
    sid = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?);",
            (sid, now),
        )
        conn.commit()
    return sid

def save_message(session_id: str, role: str, content: str, db_path: Path = DB_FILE) -> str:
    """Saves a message (user or assistant) and returns the message ID."""
    mid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, ?, ?, ?);",
            (mid, session_id, role, content, now),
        )
        conn.commit()
    return mid

def save_state_snapshot(
    session_id: str,
    message_id: str,
    state: Dict[str, Any],
    mastery: Dict[str, float],
    db_path: Path = DB_FILE,
) -> str:
    """Saves a cognitive state snapshot linked to a specific session and message."""
    snap_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO state_snapshots (id, session_id, message_id, state_json, mastery_json, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            (snap_id, session_id, message_id, json.dumps(state), json.dumps(mastery), now),
        )
        conn.commit()
    return snap_id

def get_latest_snapshot(session_id: str, db_path: Path = DB_FILE) -> Optional[Dict[str, Any]]:
    """Fetches the most recent state snapshot for a session."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, session_id, message_id, state_json, mastery_json, created_at
            FROM state_snapshots
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "message_id": row["message_id"],
            "state": json.loads(row["state_json"]),
            "mastery": json.loads(row["mastery_json"]),
            "created_at": row["created_at"],
        }

def get_snapshot_history(session_id: str, db_path: Path = DB_FILE) -> List[Dict[str, Any]]:
    """Fetches all state snapshots for a session in chronological order."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, session_id, message_id, state_json, mastery_json, created_at
            FROM state_snapshots
            WHERE session_id = ?
            ORDER BY created_at ASC;
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "message_id": r["message_id"],
                "state": json.loads(r["state_json"]),
                "mastery": json.loads(r["mastery_json"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

def get_messages(session_id: str, db_path: Path = DB_FILE) -> List[Dict[str, Any]]:
    """Retrieves all conversation messages for a session."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, session_id, role, content, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC;
            """,
            (session_id,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
