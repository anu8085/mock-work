-- ============================================================================
-- 05_program_leader_analytics.sql
--
-- Privacy-safe AGGREGATE analytics for the Program Leader Dashboard, run against
-- the Lakebase (Postgres) app-state tables the live app writes:
--   family_intake_events(intake_id, event_ts, raw_user_text, profile JSONB)
--   program_matches(match_id, intake_id, event_ts, program_id, program_name,
--                   category, match_reasons JSONB)
--   action_plans(plan_id, intake_id, event_ts, action_plan_text, generated_by_model)
--   user_feedback(feedback_id, intake_id, event_ts, rating, feedback_text)
--
-- These mirror analytics_client.py. ALL queries are read-only and return only
-- aggregates / non-free-text attributes. raw_user_text, action_plan_text, and
-- feedback_text are NEVER selected for display.
-- ============================================================================

-- 1. KPI headline counts ------------------------------------------------------
SELECT
  (SELECT COUNT(*) FROM family_intake_events)                       AS families_served,
  (SELECT COUNT(*) FROM program_matches)                            AS total_matches,
  ROUND((SELECT COUNT(*) FROM program_matches)::numeric
        / NULLIF((SELECT COUNT(*) FROM family_intake_events),0), 1) AS avg_matches_per_family,
  (SELECT ROUND(AVG(rating)::numeric,2) FROM user_feedback WHERE rating IS NOT NULL) AS avg_feedback_rating;

-- 2. Program matches by category (demand) -------------------------------------
SELECT category, COUNT(*) AS matches
FROM program_matches
GROUP BY category
ORDER BY matches DESC;

-- 3. Top matched programs -----------------------------------------------------
SELECT program_name, COUNT(*) AS matches
FROM program_matches
GROUP BY program_name
ORDER BY matches DESC
LIMIT 8;

-- 4. Family profile trends (from profile JSONB) -------------------------------
SELECT
  ROUND(AVG(NULLIF(profile->>'household_size','')::numeric), 1)                          AS avg_household_size,
  ROUND(100.0*AVG(CASE WHEN profile->>'has_children'='true' THEN 1 ELSE 0 END))          AS pct_with_children,
  ROUND(100.0*AVG(CASE WHEN profile->>'pregnant'='true'     THEN 1 ELSE 0 END))          AS pct_pregnant,
  ROUND(100.0*AVG(CASE WHEN profile->>'is_working'='true'   THEN 1 ELSE 0 END))          AS pct_working
FROM family_intake_events;

-- 4a. Household size distribution
SELECT profile->>'household_size' AS household_size, COUNT(*) AS families
FROM family_intake_events
GROUP BY household_size
ORDER BY household_size;

-- 4b. Monthly income band distribution
SELECT band, COUNT(*) AS families
FROM (
  SELECT CASE
    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 1000 THEN '< $1k'
    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 2000 THEN '$1k-2k'
    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 3000 THEN '$2k-3k'
    ELSE '$3k+' END AS band
  FROM family_intake_events
) t
GROUP BY band
ORDER BY band;

-- 5. Feedback & trust ---------------------------------------------------------
SELECT ROUND(AVG(rating)::numeric,2) AS avg_rating,
       COUNT(*)                      AS responses,
       MIN(rating) AS min_rating, MAX(rating) AS max_rating
FROM user_feedback
WHERE rating IS NOT NULL;

-- 5a. Rating distribution
SELECT rating, COUNT(*) AS responses
FROM user_feedback
WHERE rating IS NOT NULL
GROUP BY rating
ORDER BY rating;

-- 6. Service gaps -------------------------------------------------------------
-- 6a. Journeys that produced no program matches (unmet need)
SELECT COUNT(*) AS journeys_zero_matches
FROM family_intake_events fie
WHERE NOT EXISTS (SELECT 1 FROM program_matches pm WHERE pm.intake_id = fie.intake_id);

-- 6b. Families who needed childcare but matched no childcare program
SELECT
  COUNT(*) FILTER (WHERE profile->>'needs_childcare'='true') AS childcare_need_total,
  COUNT(*) FILTER (
    WHERE profile->>'needs_childcare'='true'
      AND NOT EXISTS (SELECT 1 FROM program_matches pm
                      WHERE pm.intake_id = fie.intake_id AND pm.category='childcare')
  ) AS childcare_need_unmet
FROM family_intake_events fie;

-- 7. Recent journeys (PRIVACY-SAFE: no raw_user_text / plan / feedback text) ---
SELECT
  to_char(fie.event_ts,'YYYY-MM-DD') AS date,
  COALESCE(NULLIF(fie.profile->>'household_size','')::int,0) AS household_size,
  CASE WHEN jsonb_typeof(fie.profile->'children_ages')='array'
       THEN jsonb_array_length(fie.profile->'children_ages') ELSE 0 END AS children,
  (SELECT pm.category FROM program_matches pm WHERE pm.intake_id=fie.intake_id
     GROUP BY pm.category ORDER BY COUNT(*) DESC LIMIT 1) AS top_category,
  (SELECT COUNT(*) FROM program_matches pm WHERE pm.intake_id=fie.intake_id) AS matches,
  (SELECT uf.rating FROM user_feedback uf WHERE uf.intake_id=fie.intake_id
     ORDER BY uf.event_ts DESC LIMIT 1) AS rating
FROM family_intake_events fie
ORDER BY fie.event_ts DESC
LIMIT 10;
