"""
lakebase_client.py - V12 hackathon-safe Lakebase writer

Lakebase is the PRIMARY durable app-state store for the deployed Databricks App.
SQLite remains the local fallback only when Lakebase is unavailable.

V12 Lakebase auth decision:
- Use native Lakebase/Postgres password for the mock hackathon and demo.
- Store the password as a Databricks secret/app secret, never in GitHub.
- Prefer PG* variables injected/provided by Databricks App + Lakebase resource.
- Also support LAKEBASE_* aliases for local/manual testing.
- Do not implement OAuth token refresh here. Document generate-database-credential
  as a future production enhancement after the Python SDK/API path is verified.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _env(*names: str) -> Optional[str]:
    """Return the first non-empty environment variable value."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _safe_status() -> Dict[str, str]:
    """Presence-only diagnostics. Never log secret values."""
    names = [
        "PGHOST", "PGPORT", "PGDATABASE", "PGSSLMODE", "PGUSER", "PGPASSWORD",
        "LAKEBASE_HOST", "LAKEBASE_PORT", "LAKEBASE_DATABASE", "LAKEBASE_SSLMODE",
        "LAKEBASE_USER", "LAKEBASE_PASSWORD",
    ]
    return {name: ("present" if os.environ.get(name) else "missing") for name in names}


def _connection_params() -> Optional[Dict[str, Any]]:
    """Resolve psycopg connection parameters from PG* or LAKEBASE_* env vars."""
    host = _env("PGHOST", "LAKEBASE_HOST")
    port = _env("PGPORT", "LAKEBASE_PORT") or "5432"
    dbname = _env("PGDATABASE", "LAKEBASE_DATABASE")
    user = _env("PGUSER", "LAKEBASE_USER")
    password = _env("PGPASSWORD", "LAKEBASE_PASSWORD")
    sslmode = _env("PGSSLMODE", "LAKEBASE_SSLMODE") or "require"

    missing = []
    if not host:
        missing.append("PGHOST/LAKEBASE_HOST")
    if not dbname:
        missing.append("PGDATABASE/LAKEBASE_DATABASE")
    if not user:
        missing.append("PGUSER/LAKEBASE_USER")
    if not password:
        missing.append("PGPASSWORD/LAKEBASE_PASSWORD")

    if missing:
        logger.info("Lakebase not configured. Missing: %s. Status: %s", ", ".join(missing), _safe_status())
        return None

    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
        "sslmode": sslmode,
    }


def is_configured() -> bool:
    """Return True if Lakebase env vars are sufficient to attempt a connection."""
    return _connection_params() is not None


def _connect():
    """Connect to Lakebase with a short retry for scale-to-zero wake-up."""
    params = _connection_params()
    if not params:
        return None

    try:
        import psycopg
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase unavailable: psycopg import failed: %s", type(exc).__name__)
        return None

    last_exc: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            return psycopg.connect(**params)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "Lakebase connection attempt %s failed: %s. Retrying if attempts remain.",
                attempt,
                type(exc).__name__,
            )
            time.sleep(min(attempt, 3))
    logger.error("Lakebase connection failed after retries: %s", type(last_exc).__name__ if last_exc else "unknown")
    return None


def init_lakebase_tables() -> bool:
    """Create app-state tables if they do not already exist."""
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS family_intake_events (
                      intake_id TEXT PRIMARY KEY,
                      event_ts TIMESTAMPTZ DEFAULT now(),
                      raw_user_text TEXT,
                      profile JSONB
                    );
                    CREATE TABLE IF NOT EXISTS program_matches (
                      match_id TEXT PRIMARY KEY,
                      intake_id TEXT REFERENCES family_intake_events(intake_id),
                      event_ts TIMESTAMPTZ DEFAULT now(),
                      program_id TEXT,
                      program_name TEXT,
                      category TEXT,
                      match_reasons JSONB
                    );
                    CREATE TABLE IF NOT EXISTS action_plans (
                      plan_id TEXT PRIMARY KEY,
                      intake_id TEXT REFERENCES family_intake_events(intake_id),
                      event_ts TIMESTAMPTZ DEFAULT now(),
                      action_plan_text TEXT,
                      generated_by_model TEXT
                    );
                    CREATE TABLE IF NOT EXISTS user_feedback (
                      feedback_id TEXT PRIMARY KEY,
                      intake_id TEXT REFERENCES family_intake_events(intake_id),
                      event_ts TIMESTAMPTZ DEFAULT now(),
                      rating INTEGER,
                      feedback_text TEXT
                    );
                    """
                )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase table initialization failed: %s: %s", type(exc).__name__, exc)
        return False
    finally:
        conn.close()


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _match_reasons(match: Dict[str, Any]) -> str:
    if match.get("qualification_reason") is not None or match.get("confidence_label") is not None:
        payload = {
            "qualification_reason": match.get("qualification_reason"),
            "confidence_label": match.get("confidence_label"),
            "rule_key": match.get("rule_key"),
        }
    else:
        payload = {
            "match_reasons": match.get("match_reasons", []),
            "rule_key": match.get("rule_key"),
        }
    return _json_dumps(payload)


def write_family_intake_event(profile: Dict[str, Any], raw_user_text: str) -> Optional[str]:
    """Write an intake event. Return intake_id or None."""
    conn = _connect()
    if conn is None:
        return None
    intake_id = uuid.uuid4().hex
    try:
        init_lakebase_tables()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO family_intake_events (intake_id, raw_user_text, profile)
                    VALUES (%s, %s, %s::jsonb)
                    """,
                    (intake_id, raw_user_text, _json_dumps(profile)),
                )
        logger.info("Lakebase: wrote intake event %s", intake_id)
        return intake_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: failed to write intake event: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()


def write_program_matches(intake_id: str, matches: List[Dict[str, Any]]) -> bool:
    """Write matched programs. Return True/False."""
    if not matches:
        return True
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                for match in matches:
                    cur.execute(
                        """
                        INSERT INTO program_matches
                          (match_id, intake_id, program_id, program_name, category, match_reasons)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            uuid.uuid4().hex,
                            intake_id,
                            match.get("id") or match.get("program_id"),
                            match.get("name") or match.get("program_name"),
                            match.get("category"),
                            _match_reasons(match),
                        ),
                    )
        logger.info("Lakebase: wrote %s program matches for intake %s", len(matches), intake_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: failed to write program matches: %s: %s", type(exc).__name__, exc)
        return False
    finally:
        conn.close()


def write_action_plan(intake_id: str, action_plan_text: str, generated_by_model: str) -> Optional[str]:
    """Write generated action plan. Return plan_id or None."""
    conn = _connect()
    if conn is None:
        return None
    plan_id = uuid.uuid4().hex
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO action_plans
                      (plan_id, intake_id, action_plan_text, generated_by_model)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (plan_id, intake_id, action_plan_text, generated_by_model),
                )
        logger.info("Lakebase: wrote action plan %s for intake %s", plan_id, intake_id)
        return plan_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: failed to write action plan: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()


def write_user_feedback(intake_id: str, rating: int, feedback_text: str) -> Optional[str]:
    """Write user feedback. Return feedback_id or None."""
    conn = _connect()
    if conn is None:
        return None
    feedback_id = uuid.uuid4().hex
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_feedback
                      (feedback_id, intake_id, rating, feedback_text)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (feedback_id, intake_id, rating, feedback_text),
                )
        logger.info("Lakebase: wrote feedback %s for intake %s", feedback_id, intake_id)
        return feedback_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: failed to write feedback: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()
