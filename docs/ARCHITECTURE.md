# Architecture

## Overview

Benefits Navigator is a Streamlit Databricks App that turns a free-text description of
a family's situation into an explainable set of benefit matches and a personalized
action plan, then persists the journey for social-impact analytics.

```
User free text
      │
      ▼
agent.extract_profile_from_text()      ← Claude (structured JSON profile)
agent.generate_clarifying_questions()  ← Claude (2–3 follow-ups)
      │  (user answers)
      ▼
agent.merge_profile_with_answers()     ← Claude (profile update)
      │
      ▼
load_benefit_programs()                ← Unity Catalog (SQL Warehouse) → JSON fallback
      │
      ▼
benefits_rules.screen_programs()       ← deterministic, explainable rules
      │
      ▼
agent.generate_action_plan()           ← Claude (grounded narrative)
      │
      ▼
app-state write-back                   ← Lakebase (primary) → SQLite (fallback)
```

## Design principles

- **Claude reasons, rules decide.** The LLM extracts, asks, and narrates. Eligibility
  is decided only by the deterministic rules engine, so matches are explainable and
  reproducible.
- **Every dependency degrades gracefully.** Trusted data → local JSON; Lakebase →
  SQLite. The app never dead-ends, and the UI always states which path was used.
- **Secrets stay in the environment.** No credential is hardcoded or logged. Lakebase
  uses native Postgres password auth supplied via Databricks secrets/app resources.

## Components

| File | Responsibility |
|---|---|
| `app.py` | Streamlit stages (intake → clarify → results), data/source labeling, state write-back, feedback. |
| `agent.py` | Anthropic Claude calls; lazy client; defensive JSON parsing. |
| `benefits_rules.py` | FPL math + per-program rules; shared `income_limit_pct_fpl` key. |
| `databricks_client.py` | Read-only Unity Catalog query via `databricks-sql-connector`. |
| `lakebase_client.py` | Primary Postgres writers; retry for scale-to-zero wake-up. |
| `local_state_client.py` | SQLite fallback mirroring the Lakebase writer signatures. |

## App-state tables

`family_intake_events` · `program_matches` · `action_plans` · `user_feedback`
(created by `sql/02_create_lakebase_tables.sql`, or idempotently at first write).

Analytics over these tables live in `sql/04_demo_analytics.sql`.
