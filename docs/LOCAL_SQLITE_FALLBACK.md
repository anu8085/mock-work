# Local SQLite fallback

SQLite is a **development/demo fallback only**. Lakebase (Postgres) is the primary,
durable app-state store. When a Lakebase write fails (e.g. local testing with no
Lakebase configured), the same records are written to a local SQLite database so a demo
journey is never lost.

## Location

```
.local_state/benefits_navigator_state.db
```

This path is **git-ignored** and must never be committed.

## Tables

`family_intake_events` · `program_matches` · `action_plans` · `user_feedback`
(each row tagged `storage_mode = "sqlite_fallback"`).

## Durability

- **Laptop:** the SQLite file persists across runs.
- **Deployed Databricks App:** local disk is **ephemeral** — SQLite data does NOT
  survive restarts/redeploys. The client logs a warning if it detects a deployed App.
  In production, Lakebase is the source of truth.

## Inspect counts

```powershell
python -c "import sqlite3; db='.local_state/benefits_navigator_state.db'; c=sqlite3.connect(db); [print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ['family_intake_events','program_matches','action_plans','user_feedback']]; c.close()"
```

Or enable the in-app debug expander with `SHOW_LOCAL_STATE_DEBUG=true`.
