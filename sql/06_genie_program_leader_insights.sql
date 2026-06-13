-- ============================================================================
-- 06_genie_program_leader_insights.sql
--
-- Creates a simple, PRIVACY-SAFE Unity Catalog analytics table for a Databricks
-- Genie Space (Program Leader persona). Run in Databricks SQL against the
-- hackathon-free (Free Edition) workspace + the Serverless Starter Warehouse.
--
-- SYNTHETIC DEMO DATA ONLY. No names, emails, phones, addresses, raw user text,
-- or secrets. Grain = one row per (journey, matched program); journey-level
-- attributes repeat across that journey's program rows.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS benefits_navigator.analytics
  COMMENT 'Privacy-safe aggregate analytics for Benefits Navigator (Genie/BI).';

CREATE OR REPLACE TABLE benefits_navigator.analytics.program_leader_insights (
  journey_id          STRING COMMENT 'Synthetic journey id. Repeats across the journey''s matched-program rows. Count DISTINCT for number of families served.',
  journey_date        DATE   COMMENT 'Date the synthetic journey was captured.',
  household_size      INT    COMMENT 'Number of people in the household.',
  children_count      INT    COMMENT 'Number of children in the household.',
  monthly_income_band STRING COMMENT 'Banded gross monthly household income: one of "< $1k", "$1k-2k", "$2k-3k", "$3k+".',
  insurance_status    STRING COMMENT 'Health insurance status: "uninsured", "insured", or "unknown".',
  primary_need        STRING COMMENT 'The family''s top stated need: one of food, healthcare, childcare, cash, family.',
  program_category    STRING COMMENT 'Category of the matched program: food, healthcare, childcare, cash, family.',
  program_name        STRING COMMENT 'Name of the matched benefit program (e.g., NJ SNAP, NJ FamilyCare).',
  match_count         INT    COMMENT 'Total number of programs matched for this journey (repeats across the journey''s rows).',
  feedback_rating     INT    COMMENT 'User feedback rating for the journey, 1 (low) to 5 (high). Repeats across the journey''s rows.'
)
USING DELTA
COMMENT 'SYNTHETIC, privacy-safe Benefits Navigator analytics for a Program Leader Genie Space. One row per (journey, matched program). Use only aggregates; never identify individuals or expose raw text. Covers benefit demand, program demand, family profiles, service gaps, and feedback trends.';

DELETE FROM benefits_navigator.analytics.program_leader_insights;

INSERT INTO benefits_navigator.analytics.program_leader_insights VALUES
-- J001 - single working parent, 2 kids, uninsured, needs childcare (6 matches, ★5)
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'food',       'NJ SNAP',                       6, 5),
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'food',       'WIC',                           6, 5),
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'healthcare', 'NJ FamilyCare',                 6, 5),
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'healthcare', 'NJ FamilyCare CHIP',            6, 5),
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'childcare',  'NJ Child Care Assistance (CCDF)', 6, 5),
('J001', DATE'2026-06-01', 3, 2, '$1k-2k', 'uninsured', 'childcare', 'childcare',  'NJ Preschool (PEA)',            6, 5),
-- J002 - small family, infant, uninsured, food need (5 matches, ★4)
('J002', DATE'2026-06-02', 2, 1, '$1k-2k', 'uninsured', 'food',      'food',       'NJ SNAP',                       5, 4),
('J002', DATE'2026-06-02', 2, 1, '$1k-2k', 'uninsured', 'food',      'food',       'WIC',                           5, 4),
('J002', DATE'2026-06-02', 2, 1, '$1k-2k', 'uninsured', 'food',      'healthcare', 'NJ FamilyCare',                 5, 4),
('J002', DATE'2026-06-02', 2, 1, '$1k-2k', 'uninsured', 'food',      'childcare',  'NJ Child Care Assistance (CCDF)', 5, 4),
('J002', DATE'2026-06-02', 2, 1, '$1k-2k', 'uninsured', 'food',      'family',     'NJ 2-1-1 Helpline',             5, 4),
-- J003 - large family, insured, healthcare need (7 matches, ★5)
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','food',       'NJ SNAP',                       7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','food',       'WIC',                           7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','healthcare', 'NJ FamilyCare',                 7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','healthcare', 'NJ FamilyCare CHIP',            7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','childcare',  'NJ Child Care Assistance (CCDF)', 7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','cash',       'LIHEAP',                        7, 5),
('J003', DATE'2026-06-03', 5, 3, '$2k-3k', 'insured',   'healthcare','family',     'NJ 2-1-1 Helpline',             7, 5),
-- J004 - family of 4, insured, cash/utility need (5 matches, ★4)
('J004', DATE'2026-06-04', 4, 2, '$2k-3k', 'insured',   'cash',      'food',       'NJ SNAP',                       5, 4),
('J004', DATE'2026-06-04', 4, 2, '$2k-3k', 'insured',   'cash',      'healthcare', 'NJ FamilyCare',                 5, 4),
('J004', DATE'2026-06-04', 4, 2, '$2k-3k', 'insured',   'cash',      'healthcare', 'NJ FamilyCare CHIP',            5, 4),
('J004', DATE'2026-06-04', 4, 2, '$2k-3k', 'insured',   'cash',      'cash',       'LIHEAP',                        5, 4),
('J004', DATE'2026-06-04', 4, 2, '$2k-3k', 'insured',   'cash',      'family',     'NJ 2-1-1 Helpline',             5, 4),
-- J005 - single adult, very low income, few matches (2 matches, ★3) -> service-gap example
('J005', DATE'2026-06-05', 1, 0, '< $1k',  'uninsured', 'cash',      'cash',       'NJ General Assistance',         2, 3),
('J005', DATE'2026-06-05', 1, 0, '< $1k',  'uninsured', 'cash',      'family',     'NJ 2-1-1 Helpline',             2, 3),
-- J006 - large family, higher income, food need (7 matches, ★5)
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'food',       'NJ SNAP',                       7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'food',       'WIC',                           7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'healthcare', 'NJ FamilyCare',                 7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'healthcare', 'NJ FamilyCare CHIP',            7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'childcare',  'NJ Child Care Assistance (CCDF)', 7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'childcare',  'NJ Preschool (PEA)',            7, 5),
('J006', DATE'2026-06-06', 6, 4, '$3k+',   'insured',   'food',      'family',     'NJ 2-1-1 Helpline',             7, 5),
-- J007 - small family, uninsured, childcare need (5 matches, ★4)
('J007', DATE'2026-06-07', 3, 1, '$1k-2k', 'uninsured', 'childcare', 'food',       'NJ SNAP',                       5, 4),
('J007', DATE'2026-06-07', 3, 1, '$1k-2k', 'uninsured', 'childcare', 'food',       'WIC',                           5, 4),
('J007', DATE'2026-06-07', 3, 1, '$1k-2k', 'uninsured', 'childcare', 'healthcare', 'NJ FamilyCare',                 5, 4),
('J007', DATE'2026-06-07', 3, 1, '$1k-2k', 'uninsured', 'childcare', 'childcare',  'NJ Child Care Assistance (CCDF)', 5, 4),
('J007', DATE'2026-06-07', 3, 1, '$1k-2k', 'uninsured', 'childcare', 'family',     'NJ 2-1-1 Helpline',             5, 4),
-- J008 - newborn, very low income, family/safety need (4 matches, ★5)
('J008', DATE'2026-06-08', 2, 1, '< $1k',  'uninsured', 'family',    'food',       'NJ SNAP',                       4, 5),
('J008', DATE'2026-06-08', 2, 1, '< $1k',  'uninsured', 'family',    'food',       'WIC',                           4, 5),
('J008', DATE'2026-06-08', 2, 1, '< $1k',  'uninsured', 'family',    'healthcare', 'NJ FamilyCare',                 4, 5),
('J008', DATE'2026-06-08', 2, 1, '< $1k',  'uninsured', 'family',    'family',     'NJ Domestic Violence Services', 4, 5),
-- J009 - family of 4, insured, childcare need (5 matches, ★4)
('J009', DATE'2026-06-09', 4, 2, '$2k-3k', 'insured',   'childcare', 'food',       'NJ SNAP',                       5, 4),
('J009', DATE'2026-06-09', 4, 2, '$2k-3k', 'insured',   'childcare', 'healthcare', 'NJ FamilyCare',                 5, 4),
('J009', DATE'2026-06-09', 4, 2, '$2k-3k', 'insured',   'childcare', 'healthcare', 'NJ FamilyCare CHIP',            5, 4),
('J009', DATE'2026-06-09', 4, 2, '$2k-3k', 'insured',   'childcare', 'childcare',  'NJ Child Care Assistance (CCDF)', 5, 4),
('J009', DATE'2026-06-09', 4, 2, '$2k-3k', 'insured',   'childcare', 'family',     'NJ 2-1-1 Helpline',             5, 4),
-- J010 - family of 3, insured, healthcare need (4 matches, ★5)
('J010', DATE'2026-06-10', 3, 2, '$2k-3k', 'insured',   'healthcare','healthcare', 'NJ FamilyCare',                 4, 5),
('J010', DATE'2026-06-10', 3, 2, '$2k-3k', 'insured',   'healthcare','healthcare', 'NJ FamilyCare CHIP',            4, 5),
('J010', DATE'2026-06-10', 3, 2, '$2k-3k', 'insured',   'healthcare','cash',       'LIHEAP',                        4, 5),
('J010', DATE'2026-06-10', 3, 2, '$2k-3k', 'insured',   'healthcare','family',     'NJ 2-1-1 Helpline',             4, 5);

-- ── Validation ───────────────────────────────────────────────────────────────
-- Expect: 50 rows, 10 distinct families.
SELECT COUNT(*) AS total_rows, COUNT(DISTINCT journey_id) AS families
FROM benefits_navigator.analytics.program_leader_insights;

-- Demand by program category (rows = matches).
SELECT program_category, COUNT(*) AS matches
FROM benefits_navigator.analytics.program_leader_insights
GROUP BY program_category ORDER BY matches DESC;

-- Top matched programs.
SELECT program_name, COUNT(*) AS matches
FROM benefits_navigator.analytics.program_leader_insights
GROUP BY program_name ORDER BY matches DESC;

-- Average feedback by category (one rating per journey).
SELECT program_category, ROUND(AVG(feedback_rating), 2) AS avg_rating
FROM benefits_navigator.analytics.program_leader_insights
GROUP BY program_category ORDER BY avg_rating DESC;
