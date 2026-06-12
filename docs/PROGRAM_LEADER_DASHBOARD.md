# Program Leader Analytics Dashboard

A second Streamlit page (`pages/1_Program_Leader_Dashboard.py`) for a **nonprofit /
state Program Leader — a Benefits Operations Director** — to understand benefit
demand, family-profile patterns, service gaps, and trust from completed Benefits
Navigator journeys.

## Questions it answers
1. **Which benefits are needed most?** → Program Matches by Category.
2. **Which programs are matched most often?** → Top Matched Programs.
3. **What kinds of families are using the app?** → Family Profile Trends.
4. **Where are the need gaps?** → "Where Are the Gaps?" section.
5. **Are users finding the guidance helpful?** → Feedback & Trust.

## Sections
- **KPI cards:** Families Served · Total Program Matches · Avg Matches/Family ·
  Top Need Category · Avg Feedback Rating · Lakebase Journeys Captured.
- **Program Matches by Category** (bar chart).
- **Top Matched Programs** (horizontal bar chart, top 8).
- **Family Profile Trends:** avg household size, % with children, % pregnant, %
  working, household-size distribution, monthly income bands.
- **Feedback & Trust:** average rating, responses, 1–5 distribution.
- **Where Are the Gaps?:** journeys with 0 matches; childcare need vs. unmet.
- **Recent Journeys:** privacy-safe table (date, household, children, top need,
  matches, rating).

## Data source & flow
- Reads the **Lakebase** app-state tables: `family_intake_events`,
  `program_matches`, `action_plans`, `user_feedback`.
- `analytics_client.py` runs **read-only aggregate** queries (see
  `sql/05_program_leader_analytics.sql`) and reuses `lakebase_client`'s connection
  (no changes to `lakebase_client`). It imports no Streamlit, so it is
  headless-testable.

## Fallback behavior
| Situation | `source` | Caption |
|---|---|---|
| Lakebase reachable + has rows | `lakebase` | 🟢 Live Lakebase analytics |
| Lakebase reachable, 0 journeys | `sample_empty` | "No live journeys yet — showing sample dashboard data." |
| Lakebase unavailable | `sample` | "Using sample dashboard data because Lakebase analytics is unavailable." |

Sample data is **synthetic aggregates** — never real or raw data.

## Privacy
- Shows **aggregates only**. Never displays `raw_user_text`, `action_plan_text`, or
  `feedback_text`. No names, contact details, or free-text input appear anywhere.

## Seeding demo data (optional)
`scripts/seed_demo_journeys.py` inserts **synthetic, PII-free** journeys into
Lakebase (via `lakebase_client` writers + the real rules engine) so the deployed
dashboard shows live trends. It does **not** call Claude and needs no API key.

```bash
python scripts/seed_demo_journeys.py            # add the default synthetic set
python scripts/seed_demo_journeys.py --count 6  # add the first 6
```
> Header: "Synthetic demo data for hackathon dashboard only." NOT idempotent —
> re-running ADDS more journeys. Requires Lakebase to be reachable.

## Run locally
```powershell
streamlit run app.py
```
A **"Program Leader Dashboard"** entry appears in the sidebar nav. Without Lakebase
configured locally, it shows the sample dashboard with the fallback caption.

> Note: adding `pages/` enables Streamlit's multipage **sidebar nav** on the main
> navigator (collapsed by default). `app.py` itself is unchanged.

## Validate
```powershell
py -3.11 -m py_compile analytics_client.py pages/1_Program_Leader_Dashboard.py scripts/seed_demo_journeys.py
py -3.11 -c "import analytics_client as a; d=a.get_dashboard_data(); print('source=', d['source']); print('kpi_keys=', sorted(d['kpis']))"
```
Expected: clean compile; `source= sample` locally; the 6 KPI keys printed.
