"""
databricks_client.py

Reads TRUSTED benefit-program data from Unity Catalog via a Databricks SQL Warehouse
using the official databricks-sql-connector. This module only READS.

Credentials come from the environment and are NEVER logged or printed:
    DATABRICKS_SERVER_HOSTNAME   e.g. "<workspace-host-without-https>"
    DATABRICKS_HTTP_PATH         e.g. "/sql/1.0/warehouses/<warehouse-id>"
    DATABRICKS_TOKEN             a Databricks personal access token (secret)

On any misconfiguration or failure the problem is logged (without secrets) and an
empty list is returned, so app.py can fall back to the bundled local JSON.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_ENV_VARS = (
    "DATABRICKS_SERVER_HOSTNAME",
    "DATABRICKS_HTTP_PATH",
    "DATABRICKS_TOKEN",
)

# Fully-qualified trusted table; overridable for testing without code changes.
_BENEFITS_TABLE = os.environ.get(
    "BENEFITS_TABLE", "benefits_navigator.trusted.benefit_programs"
)

_QUERY = f"""
SELECT program_id, program_name, category, description,
       eligibility_summary, apply_url, apply_phone,
       source_name, source_url, source_type,
       state, active_flag, last_verified_date,
       rule_key, income_limit_pct_fpl, accepts_undocumented,
       min_child_age, max_child_age, requires_work_or_school
FROM {_BENEFITS_TABLE}
WHERE active_flag = true
ORDER BY category, program_name
""".strip()


def get_benefit_programs_from_databricks() -> list[dict[str, Any]]:
    """Return active trusted programs as a list of dicts, or [] on any failure."""
    missing = [name for name in _REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        # Report only NAMES, never values.
        logger.info(
            "Databricks not configured; missing env var(s): %s. Using local fallback.",
            ", ".join(missing),
        )
        return []

    try:
        from databricks import sql as databricks_sql  # lazy import
    except ImportError:
        logger.error(
            "databricks-sql-connector is not installed; cannot read trusted data."
        )
        return []

    server_hostname = os.environ["DATABRICKS_SERVER_HOSTNAME"]
    http_path = os.environ["DATABRICKS_HTTP_PATH"]
    access_token = os.environ["DATABRICKS_TOKEN"]  # secret - never logged

    programs: list[dict[str, Any]] = []
    try:
        with databricks_sql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            access_token=access_token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(_QUERY)
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    programs.append(dict(zip(columns, row)))
    except Exception as exc:  # noqa: BLE001 - degrade gracefully on any failure
        logger.error(
            "Failed to read trusted programs from %s: %s", _BENEFITS_TABLE, exc
        )
        return []

    logger.info("Loaded %d trusted benefit program(s) from Unity Catalog.", len(programs))
    return programs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = get_benefit_programs_from_databricks()
    print(f"Retrieved {len(rows)} trusted benefit program(s).")
    if rows:
        print("Columns:", ", ".join(rows[0].keys()))
