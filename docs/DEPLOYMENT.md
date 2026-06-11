# Deployment — Benefits Navigator (Databricks App: Streamlit + Lakebase + Unity Catalog)

All Databricks commands use the **`hackathon-free`** (Free Edition) profile ONLY — never `dev`.
This file is a runbook; it contains **no secret values** (placeholders / `put-secret` only).

## Auth decisions (V12, verified in Prompt 6A)
- **Lakebase app-state:** native Postgres **password** auth (owner role). No OAuth token
  refresh. `lakebase_client.py` uses injected `PG*` + secret `PGUSER`/`PGPASSWORD`.
- **Trusted data (Unity Catalog via SQL Warehouse):** Option A — `DATABRICKS_TOKEN` PAT
  stored as an app secret. (Service-principal SQL auth is a future hardening step.)

## Auto-injected at runtime (do NOT set these as values)
- Platform: `DATABRICKS_HOST`, `DATABRICKS_APP_PORT`, `DATABRICKS_APP_NAME`,
  `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`, `DATABRICKS_WORKSPACE_ID`.
- Lakebase resource: `PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE`.

## Values configured as app secrets (scope: `benefits-navigator`)
`anthropic-api-key` · `databricks-token` · `lakebase-user` · `lakebase-password`

## Files
- `app.yaml` — copy from `app.yaml.template`; fill `<workspace-host-without-https>` and
  `<warehouse-id>` (non-secrets). Streamlit binds `${DATABRICKS_APP_PORT}` on `0.0.0.0`
  with CORS + XSRF disabled. `app.yaml` is **git-ignored** as defense-in-depth so a real
  token can never be committed by accident; `app.yaml.template` is the committed reference.
- `databricks.yml` — DABs bundle (target `hackathon-free`).

## Lakebase project (provisioned in Prompt 5)
- Project: `projects/benefits-navigator` · Branch: `production`
- Endpoint host: `ep-soft-sea-d847s8h5.database.us-east-2.cloud.databricks.com`
- Database: `databricks_postgres`
- Tables are created + owned by the app's connecting role on first write via
  `lakebase_client.init_lakebase_tables()` (deploy-first). `sql/02` is the manual
  fallback; `sql/03` grants only if a permission error appears.

## Deploy steps (Prompt 7 — run on approval, with `--profile hackathon-free`)
1. Enable native login on the Lakebase project and set the owner-role password in the
   Lakebase **Branch Overview** UI. (Confirm the exact `update-project` flag with
   `databricks postgres update-project -h` first.)
2. Create the secret scope and put secrets (values entered in-shell, never in a file):
   ```
   databricks secrets create-scope benefits-navigator --profile hackathon-free
   databricks secrets put-secret benefits-navigator anthropic-api-key --profile hackathon-free
   databricks secrets put-secret benefits-navigator databricks-token   --profile hackathon-free
   databricks secrets put-secret benefits-navigator lakebase-user      --profile hackathon-free
   databricks secrets put-secret benefits-navigator lakebase-password  --profile hackathon-free
   ```
3. Create the app, attach resources (Lakebase database, SQL warehouse, the 4 secrets),
   then deploy:
   ```
   databricks apps create benefits-navigator --profile hackathon-free
   databricks apps deploy benefits-navigator --profile hackathon-free
   ```
4. Verify and capture the service principal id:
   ```
   databricks apps get benefits-navigator -o json --profile hackathon-free
   ```

## Local checks (no secrets, safe to run)
```powershell
python -c "import lakebase_client; print('Lakebase configured:', lakebase_client.is_configured()); print('imports OK')"
```
Expected (no Lakebase vars set locally):
```text
Lakebase configured: False
imports OK
```

## Test C (deployed app)
Run one demo journey → expect **"Plan saved to Lakebase app-state tables."** Then:
```sql
SELECT 'family_intake_events' AS table_name, COUNT(*) FROM family_intake_events
UNION ALL SELECT 'program_matches', COUNT(*) FROM program_matches
UNION ALL SELECT 'action_plans',    COUNT(*) FROM action_plans
UNION ALL SELECT 'user_feedback',   COUNT(*) FROM user_feedback;
```
Expected after one journey: 1 / 8 / 1 / 1. Analytics: `sql/04_demo_analytics.sql`.

## Future hardening (out of scope for the mock demo)
- Service-principal SQL auth (drop the PAT) via SDK `Config` + `credentials_provider`.
- OAuth `generate-database-credential` for Lakebase (with token refresh).
