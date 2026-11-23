import json
import os
import sqlite3
from datetime import UTC, datetime

# Default database file (git-ignored). Override with RESUME_DB_PATH, which the
# tests use to point at a temporary file.
DEFAULT_DB_PATH = os.environ.get("RESUME_DB_PATH", "resume_analyses.db")


class ResumeRepository:
    """Data tier: persists analysis results to SQLite.

    The Service tier depends on this class to save each completed analysis, so
    the "logic then storage" path of the use case is real. SQLite is used
    because it needs no running server -- anyone who clones the repo can run the
    system with zero database setup (see ADR-004). The table is created on first
    use, so there is no separate migration step.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DEFAULT_DB_PATH
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS analyses ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "created_at TEXT NOT NULL, "
                "filename TEXT NOT NULL, "
                "ats_score REAL NOT NULL, "
                "matched_keywords TEXT NOT NULL, "
                "missing_keywords TEXT NOT NULL)"
            )

    def save_analysis(self, filename: str, result: dict) -> int:
        """Save one analysis result and return its new row id.

        Keyword lists are stored as JSON strings so they round-trip cleanly.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO analyses "
                "(created_at, filename, ats_score, matched_keywords, missing_keywords) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.now(UTC).isoformat(),
                    filename,
                    float(result.get("ats_score", 0.0)),
                    json.dumps(result.get("matched_keywords", [])),
                    json.dumps(result.get("missing_keywords", [])),
                ),
            )
            return cursor.lastrowid

    def count(self) -> int:
        """Return how many analyses have been stored (used by tests/demo)."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()
            return row[0]
