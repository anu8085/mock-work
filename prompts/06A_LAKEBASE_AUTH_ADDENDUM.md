# Prompt 6A - Lakebase Auth Addendum - V12 Final Decision

Run this after Prompt 5 and before Prompt 6 / Prompt 7 Databricks App deployment testing.

## Goal

Finalize the Lakebase authentication pattern for the deployed Python/Streamlit Databricks App using `psycopg`, without guessing and without changing the overall architecture.

## Verified DevHub MCP findings to use

The DevHub Lakebase docs confirm:

1. Lakebase is standard Postgres from the client perspective.
2. A Databricks App with an attached Lakebase resource can receive injected Postgres connection values such as:
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGSSLMODE`
3. `PGUSER` and `PGPASSWORD` / password credential are not something we should hardcode.
4. Lakebase supports native Postgres password authentication.
5. Lakebase also supports OAuth token credentials generated with `generate-database-credential`, but OAuth tokens expire after about 1 hour and require refresh/cache logic.
6. The DevHub AppKit examples are Node/TypeScript-centric and must not be blindly copied into this Python/Streamlit project.

## Approved V12 decision

Use **Option A - native Lakebase/Postgres password** for the mock hackathon and live demo.

Why:
- Lowest risk for a live demo.
- No 1-hour token refresh risk.
- No guessed Python SDK method names.
- Works cleanly with `psycopg`.
- Can still be stored securely as a Databricks App secret.

Document **Option B - OAuth token / generate-database-credential** only as a future production enhancement.

Do not implement OAuth token refresh now.
Do not guess SDK method names.
Do not switch to Node/TypeScript/AppKit.

## Patch to apply

Please apply the smallest safe patch for:

- `lakebase_client.py`
- root `app.yaml.template`
- `.env.example`
- `.gitignore`
- `docs/DEPLOYMENT.md` or existing deployment notes
- README/setup note only if needed

## Required implementation behavior

`lakebase_client.py` should:

1. Prefer deployed Databricks App PG variables where present:
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGSSLMODE`
   - `PGUSER`
   - `PGPASSWORD`
2. Also support local/manual aliases:
   - `LAKEBASE_HOST`
   - `LAKEBASE_PORT`
   - `LAKEBASE_DATABASE`
   - `LAKEBASE_SSLMODE`
   - `LAKEBASE_USER`
   - `LAKEBASE_PASSWORD`
3. Never log passwords, tokens, API keys, raw connection strings, or secrets.
4. Add a short retry/backoff around the first connection to absorb Lakebase scale-to-zero wake-up.
5. Keep the same public write function names so `app.py` does not need a business-logic refactor.
6. Keep SQLite fallback unchanged.

## app.yaml guidance

`app.yaml.template` should:

1. Attach the Lakebase resource.
2. Reference secrets using `valueFrom`; do not hardcode secrets.
3. Use secret-backed `PGUSER` and `PGPASSWORD` or `LAKEBASE_USER` and `LAKEBASE_PASSWORD`.
4. Keep `BENEFITS_DATA_MODE=databricks_first`.
5. Keep `SHOW_LOCAL_STATE_DEBUG=false` for deployed app.

## .env.example / .gitignore guidance

1. Add safe `.env.example` with placeholders only.
2. Keep `.env` and `.env.*` ignored.
3. Add `!.env.example` so the safe example file can be committed.

## Constraints

- Do not commit automatically.
- Do not make broad unrelated refactors.
- Do not change business logic.
- Do not change the rules engine.
- Do not change SQLite fallback behavior.
- Do not add real secrets, tokens, PATs, passwords, workspace IDs, or personal values.
- Use placeholders only.
- Keep Test A and Test B working.

## After patch, show me

1. Exact files changed.
2. Diff summary.
3. Validation commands.
4. Expected results.
5. Rollback steps if Test A or Test B breaks.

## Validation command

Run locally without Lakebase env vars:

```powershell
python -c "import lakebase_client; print('Lakebase configured:', lakebase_client.is_configured()); print('imports OK')"
```

Expected:

```text
Lakebase configured: False
imports OK
```

This confirms local SQLite fallback remains available until Lakebase is configured.
