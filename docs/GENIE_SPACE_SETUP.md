# Databricks Genie Space — Program Leader (mock)

A simple **Databricks Genie Space** that lets a Program Leader ask natural-language
questions about Benefits Navigator demand trends, backed by one privacy-safe Unity
Catalog table. This is an **additive** analytics layer — it does not change the
Streamlit app, Lakebase, or the rules engine.

## 1. Purpose
Give a non-technical program leader a chat box to explore **aggregate** benefit-demand
insights (no SQL required): benefit demand, program demand, family profiles, service
gaps, and feedback trends — all from synthetic, privacy-safe data.

## 2. Persona
**Program Leader / Benefits Operations Director** — wants to know what families need,
which programs carry the load, where the gaps are, and whether guidance is trusted.

## 3. Databricks UI steps to create the Genie Space
> Menu labels vary slightly by workspace version; this is the Free Edition flow.
1. Run `sql/06_genie_program_leader_insights.sql` first (see §4) so the table exists.
2. In the Databricks workspace left nav, open **Genie** (under **SQL** / **AI/BI**).
3. Click **New** → **Genie space** (or **Create**).
4. **Name:** `Benefits Navigator Program Leader Genie`.
5. **SQL warehouse:** select the **Serverless Starter Warehouse**.
6. **Add data / tables:** add `benefits_navigator.analytics.program_leader_insights`.
7. **General instructions:** paste the Genie instructions in §6.
8. *(Optional)* add the §7 questions as **sample questions** and save a couple as
   example SQL so Genie answers consistently.
9. **Save**, then test with the §7 questions.

## 4. Table & exact SQL to run
**Table:** `benefits_navigator.analytics.program_leader_insights`
(schema `benefits_navigator.analytics`, 50 synthetic rows across 10 families).

Run the file in the **Databricks SQL editor** (paste its contents) against the
Serverless Starter Warehouse — recommended because it is multi-statement:
```
sql/06_genie_program_leader_insights.sql
```
Or via CLI, one statement at a time (Free Edition profile only):
```
databricks experimental aitools tools query "CREATE SCHEMA IF NOT EXISTS benefits_navigator.analytics" --profile hackathon-free
databricks experimental aitools tools query "<paste each statement from sql/06>" --profile hackathon-free
```
Validation (expect 50 rows / 10 families):
```
databricks experimental aitools tools query "SELECT COUNT(*) total_rows, COUNT(DISTINCT journey_id) families FROM benefits_navigator.analytics.program_leader_insights" --profile hackathon-free
```

## 5. Genie instructions (paste into the space)
> This data is **synthetic and aggregate**. Always answer with **privacy-safe
> aggregates**. **Never identify individuals** and **never expose raw user text**.
> Each row is one matched program within a journey; `journey_id` repeats across a
> journey's rows, so use `COUNT(DISTINCT journey_id)` for "families". `match_count`
> and `feedback_rating` are per-journey (repeat across rows) — de-duplicate by
> `journey_id` before averaging them. Focus on benefit demand, program demand, family
> profiles, service gaps, and feedback trends.

## 6. Sample Genie questions
- Which benefit category is most requested?
- Which programs are matched most often?
- What types of families need childcare support?
- How many families have healthcare needs?
- Which user profiles have the fewest program matches?
- What should a program leader prioritize next?
- Show average feedback rating by benefit category.

## 7. Demo script (10–15 seconds)
> "Beyond the dashboard, a program leader can just **ask**. Here in Genie —
> *'Which benefit category is most requested?'*" *(show answer)* "— and *'Which user
> profiles have the fewest program matches?'*" *(show the gap)* "Natural-language
> insight over governed Databricks data, no SQL needed."

## 8. Safety notes
- **Synthetic data only** — generated for the demo; not real families.
- **No secrets** — none referenced or stored here.
- **No PII** — no names, emails, phones, addresses, or raw user text; aggregates only.
- **Mock / reference only** — this is dry-run practice.
- **Recreate fresh during the official hackathon Project Period** — do not reuse this
  mock table/space as the official submission.
