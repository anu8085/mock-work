# Deployment Notes - V12 Lakebase Auth Decision

## Recommended hackathon/demo path

Use **native Lakebase/Postgres password authentication** for the mock hackathon and live demo.

Why this is the recommended V12 path:

- It is reliable for a live demo.
- It works directly with Python `psycopg`.
- It avoids implementing a 1-hour OAuth token refresh flow during the hackathon.
- It avoids guessing Databricks SDK method names.
- The password can still be stored securely as a Databricks App secret.

## Databricks App + Lakebase runtime variables

When Lakebase is attached as a Databricks App resource, the platform may inject Postgres connection values such as:

- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGSSLMODE`

Supply the remaining credential values securely as Databricks secrets/app config:

- `PGUSER` or `LAKEBASE_USER`
- `PGPASSWORD` or `LAKEBASE_PASSWORD`

Do not hardcode these values in `app.yaml`, GitHub, screenshots, prompts, or docs.

## Local development

For local laptop testing, either leave Lakebase unset and use SQLite fallback, or set local environment variables privately:

```powershell
$env:PGHOST="<your_lakebase_host>"
$env:PGPORT="5432"
$env:PGDATABASE="<your_database>"
$env:PGSSLMODE="require"
$env:PGUSER="<your_lakebase_user>"
$env:PGPASSWORD="<your_lakebase_native_password>"
```

Equivalent `LAKEBASE_*` aliases are also supported by the V12 client:

```powershell
$env:LAKEBASE_HOST="<your_lakebase_host>"
$env:LAKEBASE_PORT="5432"
$env:LAKEBASE_DATABASE="<your_database>"
$env:LAKEBASE_SSLMODE="require"
$env:LAKEBASE_USER="<your_lakebase_user>"
$env:LAKEBASE_PASSWORD="<your_lakebase_native_password>"
```

## Future production enhancement

Lakebase also supports OAuth token credentials using `generate-database-credential`. That path is documented as a future enhancement only.

Do not implement OAuth token refresh in the hackathon demo unless you have verified the Python SDK/API method and tested refresh/caching end to end.

Reason: OAuth tokens expire after about 1 hour, so new connections require fresh credentials. That is unnecessary demo risk.

## Validation

Without Lakebase variables configured, this should still import and show fallback-ready state:

```powershell
python -c "import lakebase_client; print('Lakebase configured:', lakebase_client.is_configured()); print('imports OK')"
```

Expected:

```text
Lakebase configured: False
imports OK
```

After deployed Databricks App + Lakebase setup, run one scenario and confirm rows increase:

```sql
SELECT 'family_intake_events' AS table_name, COUNT(*) FROM family_intake_events
UNION ALL SELECT 'program_matches', COUNT(*) FROM program_matches
UNION ALL SELECT 'action_plans', COUNT(*) FROM action_plans
UNION ALL SELECT 'user_feedback', COUNT(*) FROM user_feedback;
```
