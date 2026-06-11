"""
lakebase_client.py

PRIMARY durable app-state store: Lakebase (managed Postgres) for the deployed
Databricks App. SQLite is the local fallback only.

V12 auth decision (mock hackathon + demo): use native Lakebase/Postgres PASSWORD
auth. Prefer PG* variables injected by the Databricks App + Lakebase resource; also
accept LAKEBASE_* aliases for local/manual testing. Credentials are supplied via
Databricks secrets/app config - never hardcoded, never logged. OAuth
generate-database-credential token refresh is a future enhancement, intentionally
NOT implemented here.

Every writer degrades gracefully (returns None/False, never raises) so app-state
persistence can never crash the app or block the user.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Connection env vars, in (PG*, LAKEBASE_*) preference order.
_PARAM_SOURCES = {
    "host": ("PGHOST", "LAKEBASE_HOST"),
    "port": ("PGPORT", "LAKEBASE_PORT"),
    "dbname": ("PGDATABASE", "LAKEBASE_DATABASE"),
    "user": ("PGUSER", "LAKEBASE_USER"),
    "password": ("PGPASSWORD", "LAKEBASE_PASSWORD"),
    "sslmode": ("PGSSLMODE", "LAKEBASE_SSLMODE"),
}


def _env(*names: str) -> Optional[str]:
    """Return the first non-empty environment variable value among names."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _connection_params() -> Optional[dict[str, Any]]:
    """Resolve psycopg connection params from PG*/LAKEBASE_* env vars, or None."""
    params = {key: _env(*sources) for key, sources in _PARAM_SOURCES.items()}
    params["port"] = params["port"] or "5432"
    params["sslmode"] = params["sslmode"] or "require"

    required = ("host", "dbname", "user", "password")
    missing = [k for k in required if not params.get(k)]
    if missing:
        logger.info("Lakebase not configured; missing %s. Using fallback.", ", ".join(missing))
        return None
    return params


def is_configured() -> bool:
    """True if enough env vars are present to attempt a Lakebase connection."""
    return _connection_params() is not None


def _connect():
    """Connect to Lakebase with a short retry for scale-to-zero wake-up. None on failure."""
    params = _connection_params()
    if not params:
        return None
    try:
        import psycopg  # lazy import
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase unavailable: psycopg import failed: %s", type(exc).__name__)
        return None

    last_exc: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            return psycopg.connect(**params)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("Lakebase connect attempt %d failed: %s.", attempt, type(exc).__name__)
            time.sleep(min(attempt, 3))
    logger.error(
        "Lakebase connection failed after retries: %s",
        type(last_exc).__name__ if last_exc else "unknown",
    )
    return None


def init_lakebase_tables() -> bool:
    """Create app-state tables if they do not already exist. Returns True/False."""
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn, conn.cursor() as cur:
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
        logger.error("Lakebase table init failed: %s: %s", type(exc).__name__, exc)
        return False
    finally:
        conn.close()


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False)


def _match_reasons(match: dict[str, Any]) -> str:
    payload = {
        "match_reasons": match.get("match_reasons", []),
        "rule_key": match.get("rule_key") or match.get("id"),
    }
    return _json_dumps(payload)


def write_family_intake_event(profile: dict[str, Any], raw_user_text: str) -> Optional[str]:
    """Write an intake event. Returns intake_id or None."""
    conn = _connect()
    if conn is None:
        return None
    intake_id = uuid.uuid4().hex
    try:
        init_lakebase_tables()
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO family_intake_events (intake_id, raw_user_text, profile)
                VALUES (%s, %s, %s::jsonb)
                """,
                (intake_id, raw_user_text, _json_dumps(profile)),
            )
        logger.info("Lakebase: wrote intake event %s.", intake_id)
        return intake_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: intake write failed: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()


def write_program_matches(intake_id: str, matches: list[dict[str, Any]]) -> bool:
    """Write matched programs (one row each). Returns True/False."""
    if not matches:
        return True
    conn = _connect()
    if conn is None:
        return False
    try:
        with conn, conn.cursor() as cur:
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
        logger.info("Lakebase: wrote %d match(es) for intake %s.", len(matches), intake_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: matches write failed: %s: %s", type(exc).__name__, exc)
        return False
    finally:
        conn.close()


def write_action_plan(intake_id: str, action_plan_text: str, generated_by_model: str) -> Optional[str]:
    """Write the generated action plan. Returns plan_id or None."""
    conn = _connect()
    if conn is None:
        return None
    plan_id = uuid.uuid4().hex
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO action_plans
                  (plan_id, intake_id, action_plan_text, generated_by_model)
                VALUES (%s, %s, %s, %s)
                """,
                (plan_id, intake_id, action_plan_text, generated_by_model),
            )
        logger.info("Lakebase: wrote action plan %s for intake %s.", plan_id, intake_id)
        return plan_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: action-plan write failed: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()


def write_user_feedback(intake_id: str, rating: int, feedback_text: str) -> Optional[str]:
    """Write user feedback. Returns feedback_id or None."""
    conn = _connect()
    if conn is None:
        return None
    feedback_id = uuid.uuid4().hex
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_feedback
                  (feedback_id, intake_id, rating, feedback_text)
                VALUES (%s, %s, %s, %s)
                """,
                (feedback_id, intake_id, rating, feedback_text),
            )
        logger.info("Lakebase: wrote feedback %s for intake %s.", feedback_id, intake_id)
        return feedback_id
    except Exception as exc:  # noqa: BLE001
        logger.error("Lakebase: feedback write failed: %s: %s", type(exc).__name__, exc)
        return None
    finally:
        conn.close()
