# Setup

All Databricks CLI commands use the **`hackathon-free`** profile (Free Edition) only.

## Prerequisites

- Python 3.11, Git, Databricks CLI `v1.0.0+`
- An Anthropic API key
- Databricks Free Edition workspace with a SQL Warehouse (for Test B/C) and Lakebase
  (for Test C)

## Local environment (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Never commit `.env`, `.venv/`, `.local_state/`, or any `*.db`/`*.sqlite` file.
> Use environment variables (below) or a private, git-ignored `.env`.

## Test A — local JSON + SQLite

```powershell
$env:ANTHROPIC_API_KEY="<your_anthropic_api_key>"
$env:CLAUDE_MODEL="claude-sonnet-4-5-20250929"
$env:BENEFITS_DATA_MODE="json_only"
$env:SHOW_LOCAL_STATE_DEBUG="true"
streamlit run app.py
```

Expected: caption reads **"📁 Using local fallback benefits data"**; after a full run,
the results page shows **"saved locally in SQLite for demo fallback."**

## Test B — Unity Catalog (SQL Warehouse) + SQLite

First load the trusted table (12 rows) via `sql/01_create_trusted_benefit_programs.sql`
in Databricks SQL. Then:

```powershell
$env:BENEFITS_DATA_MODE="databricks_first"
$env:DATABRICKS_SERVER_HOSTNAME="<workspace-host-without-https>"
$env:DATABRICKS_HTTP_PATH="/sql/1.0/warehouses/<warehouse-id>"
$env:DATABRICKS_TOKEN="<your_local_databricks_pat>"
streamlit run app.py
```

Expected: caption reads **"🔒 Using trusted Databricks benefits data"**; state still
saves to SQLite (Lakebase not configured locally).

## Test C — deployed Databricks App + Lakebase

Deploy with `app.yaml` (from `app.yaml.template`), attach the Lakebase resource and the
`anthropic-api-key` / `databricks-token` / `lakebase-user` / `lakebase-password`
secrets. The app uses injected `PG*` variables. Expected: **"Plan saved to Lakebase
app-state tables."** See [DEPLOYMENT — covered at Prompt 6/7].

## Lakebase auth (V12)

Native Postgres password via Databricks secrets. The exact Python/psycopg credential
pattern is verified at **Prompt 6A** using the DevHub Docs MCP + Databricks skills
before deployment. OAuth token refresh is a future enhancement, not implemented.
