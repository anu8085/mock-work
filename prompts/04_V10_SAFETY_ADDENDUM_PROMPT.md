# Prompt 4 - V10 Safety Addendum

Use this before the final deployment prompt.

Please review the project for V10 hackathon safety and deployment readiness.

Requirements:
1. Confirm no real API keys, PATs, workspace IDs, warehouse IDs, connection strings, or personal repo URLs are present in committed files.
2. Confirm `.gitignore` blocks `.env`, `.venv`, `.local_state`, SQLite DB files, `__pycache__`, and local logs.
3. Confirm `agent.py` uses `CLAUDE_MODEL` from environment with a safe default.
4. Confirm local Databricks SQL uses `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, and `DATABRICKS_TOKEN`.
5. Confirm deployed Lakebase prefers Databricks App resource-injected PG variables: `PGHOST`, `PGDATABASE`, `PGPORT`, `PGSSLMODE`, and `PGUSER`.
6. Confirm manual `LAKEBASE_*` variables are fallback/local-only, not the preferred deployed path.
7. Confirm trusted program total row validation expects 12 rows, while the main demo scenario can match about 8 programs.
8. Do not commit automatically. Show exact diffs and validation commands first.
