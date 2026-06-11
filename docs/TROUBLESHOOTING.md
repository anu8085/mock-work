# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Caption shows "local fallback" in Test B | Databricks env vars missing/invalid, or warehouse asleep | Verify `DATABRICKS_SERVER_HOSTNAME` / `DATABRICKS_HTTP_PATH` / `DATABRICKS_TOKEN`; start the SQL Warehouse. |
| `databricks-sql-connector` ImportError | Dependency not installed | `pip install -r requirements.txt`. |
| Plan shows "app-state saving failed" | Both Lakebase and SQLite writes failed | Check Lakebase env vars; ensure the working dir is writable for `.local_state/`. |
| Results show "saved locally in SQLite" in Test C | Lakebase not reachable from the deployed App | Confirm the Lakebase resource is attached and `PG*`/secrets are injected. |
| Claude call errors / JSON parse failure | Missing/invalid `ANTHROPIC_API_KEY` or model id | Set a valid key; check `CLAUDE_MODEL`. Profile merge falls back to the prior profile. |
| Lakebase first write slow then succeeds | Scale-to-zero wake-up | Expected; the client retries up to 3 times. Pre-warm before demos. |
| Trusted table count ≠ 12 | Table not (re)loaded | Re-run `sql/01_create_trusted_benefit_programs.sql`. |

## Safety reminders

- All Databricks CLI commands use `--profile hackathon-free` (Free Edition) only.
- Never paste real keys/PATs/passwords into code, docs, logs, or screenshots.
- Never commit `.env`, `.venv/`, `.local_state/`, or `*.db`/`*.sqlite` files.
