# Testing

Three required test gates (run in order). Full env setup is in [SETUP.md](SETUP.md).

## Main demo scenario

Intake text:

```
I am a single mom in New Jersey with two kids ages 3 and 7. I work part-time and make
about $1,800 per month. I do not have health insurance right now. I need help with
food, childcare, and paying bills.
```

Clarifying answers:

```
Middlesex County
My 7-year-old is in school. My 3-year-old needs daycare or preschool.
No, I am not currently receiving any government assistance or benefits.
```

Expected: a plan is generated and **8** programs match (SNAP, WIC, NJ FamilyCare,
CHIP, CCDF, NJ Preschool, LIHEAP, NJ 2-1-1).

## Test A — JSON + SQLite

- Caption: "📁 Using local fallback benefits data"
- Results: "saved locally in SQLite for demo fallback"
- Verify SQLite row counts:

```powershell
python -c "import sqlite3; db='.local_state/benefits_navigator_state.db'; c=sqlite3.connect(db); [print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]) for t in ['family_intake_events','program_matches','action_plans','user_feedback']]; c.close()"
```

Expected after one full run with feedback:

```
family_intake_events 1
program_matches 8
action_plans 1
user_feedback 1
```

## Test B — Unity Catalog (SQL Warehouse) + SQLite

- Caption: "🔒 Using trusted Databricks benefits data"
- Trusted table row count = 12:

```sql
SELECT COUNT(*) AS total_programs FROM benefits_navigator.trusted.benefit_programs;
```

- State still saves to SQLite (Lakebase not configured locally).

## Test C — Databricks App + Unity Catalog + Lakebase

- App opens at its Databricks App URL.
- Caption: "🔒 Using trusted Databricks benefits data"
- Results: "Plan saved to Lakebase app-state tables."
- Lakebase analytics return rows (see `sql/04_demo_analytics.sql`).

## What to screenshot

Source caption · matched program cards · storage-mode message · feedback confirmation ·
SQLite counts (Test A) · Lakebase analytics (Test C).
