"""
local_state_client.py

LOCAL SQLite fallback for app-state. Lakebase (Postgres) is the PRIMARY store; this
module is used ONLY when a Lakebase write fails (e.g. local laptop testing with no
Lakebase configured). It mirrors lakebase_client's public write-function names so it
is a drop-in fallback.

Uses only the standard-library sqlite3 (no new dependency). NEVER logs secrets. The
database file lives under .local_state/ and is git-ignored - never commit it.

Durability note: on a laptop the SQLite file persists across runs. Inside a DEPLOYED
Databricks App local disk is EPHEMERAL, so SQLite there is an emergency fallback only
and the logs say so.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_LOCAL_DIR = Path(".local_state")
_DB_PATH = _LOCAL_DIR / "benefits_navigator_state.db"
_STORAGE_MODE = "sqlite_fallback"


def get_db_path() -> str:
    """Return the SQLite database path as a string."""
    return str(_DB_PATH)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _is_deployed_app() -> bool:
    """Best-effort detection of a deployed Databricks App (presence only)."""
    return bool(
        os.environ.get("DATABRICKS_APP_NAME")
        or os.environ.get("DATABRICKS_CLIENT_ID")
        or os.environ.get("LAKEBASE_ENDPOINT")
    )


def _warn_if_deployed() -> None:
    if _is_deployed_app():
        logger.warning(
            "Using local SQLite fallback inside what looks like a DEPLOYED Databricks "
            "App. This storage is EPHEMERAL - use it only as an emergency fallback."
        )


def init_local_db() -> None:
    """Create the SQLite database and tables if they do not already exist."""
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS family_intake_events (
                intake_id     TEXT PRIMARY KEY,
                event_ts      TEXT,
                raw_user_text TEXT,
                profile_json  TEXT,
                storage_mode  TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS program_matches (
                match_id           TEXT PRIMARY KEY,
                intake_id          TEXT,
                event_ts           TEXT,
                program_id         TEXT,
                program_name       TEXT,
                category           TEXT,
                match_reasons_json TEXT,
                storage_mode       TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS action_plans (
                plan_id            TEXT PRIMARY KEY,
                intake_id          TEXT,
                event_ts           TEXT,
                action_plan_text   TEXT,
                generated_by_model TEXT,
                storage_mode       TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_feedback (
                feedback_id   TEXT PRIMARY KEY,
                intake_id     TEXT,
                event_ts      TEXT,
                rating        INTEGER,
                feedback_text TEXT,
                storage_mode  TEXT
            )
            """
        )
        conn.commit()


def _match_reasons_json(match: dict[str, Any]) -> str:
    payload = {
        "match_reasons": match.get("match_reasons", []),
        "rule_key": match.get("rule_key") or match.get("id"),
    }
    return json.dumps(payload, ensure_ascii=False)


def write_family_intake_event(profile: dict[str, Any], raw_user_text: str) -> Optional[str]:
    """Persist an intake event locally. Returns intake_id or None."""
    _warn_if_deployed()
    intake_id = _new_id()
    try:
        init_local_db()
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO family_intake_events
                    (intake_id, event_ts, raw_user_text, profile_json, storage_mode)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    intake_id,
                    _now_iso(),
                    raw_user_text,
                    json.dumps(profile or {}, ensure_ascii=False),
                    _STORAGE_MODE,
                ),
            )
            conn.commit()
        logger.info("SQLite fallback: wrote intake event %s.", intake_id)
        return intake_id
    except Exception as exc:  # noqa: BLE001 - never crash the app
        logger.error("SQLite fallback: intake write failed: %s: %s", type(exc).__name__, exc)
        return None


def write_program_matches(intake_id: str, matches: list[dict[str, Any]]) -> bool:
    """Persist program matches locally (one row per match). Returns True/False."""
    if not matches:
        return True
    try:
        init_local_db()
        ts = _now_iso()
        rows = [
            (
                _new_id(),
                intake_id,
                ts,
                m.get("id") or m.get("program_id"),
                m.get("name") or m.get("program_name"),
                m.get("category"),
                _match_reasons_json(m),
                _STORAGE_MODE,
            )
            for m in matches
        ]
        with sqlite3.connect(_DB_PATH) as conn:
            conn.executemany(
                """
                INSERT INTO program_matches
                    (match_id, intake_id, event_ts, program_id, program_name,
                     category, match_reasons_json, storage_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        logger.info("SQLite fallback: wrote %d match(es) for intake %s.", len(rows), intake_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("SQLite fallback: matches write failed: %s: %s", type(exc).__name__, exc)
        return False


def write_action_plan(intake_id: str, action_plan_text: str, generated_by_model: str) -> Optional[str]:
    """Persist the action plan locally. Returns plan_id or None."""
    plan_id = _new_id()
    try:
        init_local_db()
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO action_plans
                    (plan_id, intake_id, event_ts, action_plan_text,
                     generated_by_model, storage_mode)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (plan_id, intake_id, _now_iso(), action_plan_text, generated_by_model, _STORAGE_MODE),
            )
            conn.commit()
        logger.info("SQLite fallback: wrote action plan %s for intake %s.", plan_id, intake_id)
        return plan_id
    except Exception as exc:  # noqa: BLE001
        logger.error("SQLite fallback: action-plan write failed: %s: %s", type(exc).__name__, exc)
        return None


def write_user_feedback(intake_id: str, rating: Any, feedback_text: str) -> Optional[str]:
    """Persist user feedback locally. Returns feedback_id or None."""
    feedback_id = _new_id()
    try:
        init_local_db()
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO user_feedback
                    (feedback_id, intake_id, event_ts, rating, feedback_text, storage_mode)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (feedback_id, intake_id, _now_iso(), rating, feedback_text, _STORAGE_MODE),
            )
            conn.commit()
        logger.info("SQLite fallback: wrote feedback %s for intake %s.", feedback_id, intake_id)
        return feedback_id
    except Exception as exc:  # noqa: BLE001
        logger.error("SQLite fallback: feedback write failed: %s: %s", type(exc).__name__, exc)
        return None


def get_local_state_counts() -> dict[str, int]:
    """Return row counts per app-state table (zeros on any error). Debug helper."""
    tables = ["family_intake_events", "program_matches", "action_plans", "user_feedback"]
    counts = {t: 0 for t in tables}
    try:
        init_local_db()
        with sqlite3.connect(_DB_PATH) as conn:
            for t in tables:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        logger.error("SQLite fallback: count read failed: %s: %s", type(exc).__name__, exc)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_local_db()
    print("Local SQLite state DB:", get_db_path())
    print("Counts:", get_local_state_counts())
