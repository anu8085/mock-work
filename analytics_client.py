"""
analytics_client.py

Read-only, privacy-safe analytics layer for the Program Leader Dashboard.

It returns ONLY aggregates derived from the Lakebase app-state tables
(family_intake_events, program_matches, action_plans, user_feedback). It never
returns raw_user_text, action_plan_text, or feedback_text - no free-text user
content is ever surfaced.

Connection is reused from lakebase_client (same PG*/LAKEBASE_* resolution), so
lakebase_client is NOT modified. This module imports no Streamlit, so it can be
unit-tested headlessly.

Fallback: if Lakebase is unavailable -> sample data with source "sample". If
Lakebase is reachable but has no journeys yet -> sample data with source
"sample_empty". Otherwise live data with source "lakebase".
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import lakebase_client

logger = logging.getLogger(__name__)

_CATEGORY_LABEL = {
    "food": "Food",
    "healthcare": "Healthcare",
    "childcare": "Childcare",
    "cash": "Cash & Basic",
    "family": "Family Resources",
}
_INCOME_BAND_ORDER = ["< $1k", "$1k-2k", "$2k-3k", "$3k+"]


def _label(category: Optional[str]) -> str:
    return _CATEGORY_LABEL.get(category or "", (category or "—").title())


# ── Sample / fallback data (synthetic aggregates; NO real or raw data) ─────────
def _sample_data() -> dict[str, Any]:
    return {
        "kpis": {
            "families_served": 24,
            "total_matches": 152,
            "avg_matches_per_family": 6.3,
            "top_need_category": "Healthcare",
            "avg_feedback_rating": 4.4,
            "lakebase_journeys_captured": 24,
        },
        "category_demand": [
            {"category": "healthcare", "label": "Healthcare", "matches": 38},
            {"category": "food", "label": "Food", "matches": 34},
            {"category": "childcare", "label": "Childcare", "matches": 30},
            {"category": "cash", "label": "Cash & Basic", "matches": 28},
            {"category": "family", "label": "Family Resources", "matches": 22},
        ],
        "top_programs": [
            {"program": "NJ FamilyCare (Medicaid)", "matches": 22},
            {"program": "NJ SNAP", "matches": 21},
            {"program": "NJ 2-1-1 Helpline", "matches": 20},
            {"program": "WIC", "matches": 18},
            {"program": "NJ FamilyCare - CHIP", "matches": 16},
            {"program": "NJ Child Care Assistance (CCDF)", "matches": 15},
            {"program": "LIHEAP (Energy Assistance)", "matches": 14},
            {"program": "NJ Preschool (PEA)", "matches": 12},
        ],
        "profile_trends": {
            "avg_household_size": 3.4,
            "pct_with_children": 83.0,
            "pct_pregnant": 17.0,
            "pct_working": 71.0,
            "household_size": [
                {"bucket": "2", "families": 5},
                {"bucket": "3", "families": 8},
                {"bucket": "4", "families": 6},
                {"bucket": "5", "families": 3},
                {"bucket": "6", "families": 2},
            ],
            "income_bands": [
                {"band": "< $1k", "families": 4},
                {"band": "$1k-2k", "families": 11},
                {"band": "$2k-3k", "families": 6},
                {"band": "$3k+", "families": 3},
            ],
        },
        "feedback": {
            "avg_rating": 4.4,
            "responses": 21,
            "distribution": [
                {"rating": 1, "count": 0},
                {"rating": 2, "count": 1},
                {"rating": 3, "count": 2},
                {"rating": 4, "count": 6},
                {"rating": 5, "count": 12},
            ],
        },
        "gaps": {
            "journeys_zero_matches": 2,
            "childcare_need_total": 14,
            "childcare_need_unmet": 3,
        },
        "recent_journeys": [
            {"date": "2026-06-10", "household_size": 3, "children": 2, "top_category": "Childcare", "matches": 8, "rating": 5},
            {"date": "2026-06-10", "household_size": 2, "children": 1, "top_category": "Food", "matches": 5, "rating": 4},
            {"date": "2026-06-09", "household_size": 5, "children": 3, "top_category": "Healthcare", "matches": 7, "rating": 5},
            {"date": "2026-06-09", "household_size": 4, "children": 2, "top_category": "Cash & Basic", "matches": 6, "rating": 4},
            {"date": "2026-06-08", "household_size": 1, "children": 0, "top_category": "Family Resources", "matches": 2, "rating": 3},
            {"date": "2026-06-08", "household_size": 6, "children": 4, "top_category": "Food", "matches": 8, "rating": 5},
            {"date": "2026-06-07", "household_size": 3, "children": 1, "top_category": "Healthcare", "matches": 6, "rating": 4},
            {"date": "2026-06-07", "household_size": 2, "children": 1, "top_category": "Childcare", "matches": 5, "rating": 5},
        ],
    }


def _with_source(data: dict[str, Any], source: str) -> dict[str, Any]:
    out = dict(data)
    out["source"] = source
    return out


# ── Live Lakebase analytics (aggregates only) ─────────────────────────────────
def _fetch_live() -> Optional[dict[str, Any]]:
    """Return live aggregates, {"_empty": True}, or None (unavailable)."""
    if not lakebase_client.is_configured():
        return None
    conn = lakebase_client._connect()
    if conn is None:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM family_intake_events")
            families = cur.fetchone()[0] or 0
            if families == 0:
                return {"_empty": True}

            cur.execute("SELECT COUNT(*) FROM program_matches")
            total_matches = cur.fetchone()[0] or 0

            cur.execute(
                "SELECT category, COUNT(*) AS m FROM program_matches "
                "GROUP BY category ORDER BY m DESC"
            )
            category_demand = [
                {"category": c, "label": _label(c), "matches": m}
                for (c, m) in cur.fetchall()
            ]

            cur.execute(
                "SELECT program_name, COUNT(*) AS m FROM program_matches "
                "GROUP BY program_name ORDER BY m DESC LIMIT 8"
            )
            top_programs = [{"program": p, "matches": m} for (p, m) in cur.fetchall()]

            cur.execute(
                """
                SELECT
                  AVG(NULLIF(profile->>'household_size','')::numeric),
                  100.0*AVG(CASE WHEN profile->>'has_children'='true' THEN 1 ELSE 0 END),
                  100.0*AVG(CASE WHEN profile->>'pregnant'='true' THEN 1 ELSE 0 END),
                  100.0*AVG(CASE WHEN profile->>'is_working'='true' THEN 1 ELSE 0 END)
                FROM family_intake_events
                """
            )
            avg_hh, pct_children, pct_pregnant, pct_working = cur.fetchone()

            cur.execute(
                "SELECT profile->>'household_size' AS hh, COUNT(*) "
                "FROM family_intake_events GROUP BY hh ORDER BY hh"
            )
            household_size = [
                {"bucket": (hh or "?"), "families": n} for (hh, n) in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT band, COUNT(*) FROM (
                  SELECT CASE
                    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 1000 THEN '< $1k'
                    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 2000 THEN '$1k-2k'
                    WHEN COALESCE(NULLIF(profile->>'monthly_income','')::numeric,0) < 3000 THEN '$2k-3k'
                    ELSE '$3k+' END AS band
                  FROM family_intake_events
                ) t GROUP BY band
                """
            )
            band_counts = {b: n for (b, n) in cur.fetchall()}
            income_bands = [
                {"band": b, "families": band_counts.get(b, 0)} for b in _INCOME_BAND_ORDER
            ]

            cur.execute(
                "SELECT ROUND(AVG(rating)::numeric,2), COUNT(*) "
                "FROM user_feedback WHERE rating IS NOT NULL"
            )
            avg_rating, responses = cur.fetchone()

            cur.execute(
                "SELECT rating, COUNT(*) FROM user_feedback "
                "WHERE rating IS NOT NULL GROUP BY rating"
            )
            dist_counts = {int(r): n for (r, n) in cur.fetchall()}
            distribution = [
                {"rating": r, "count": dist_counts.get(r, 0)} for r in range(1, 6)
            ]

            cur.execute(
                "SELECT COUNT(*) FROM family_intake_events fie "
                "WHERE NOT EXISTS (SELECT 1 FROM program_matches pm "
                "WHERE pm.intake_id = fie.intake_id)"
            )
            zero_matches = cur.fetchone()[0] or 0

            cur.execute(
                "SELECT COUNT(*) FROM family_intake_events "
                "WHERE profile->>'needs_childcare'='true'"
            )
            childcare_total = cur.fetchone()[0] or 0

            cur.execute(
                "SELECT COUNT(*) FROM family_intake_events fie "
                "WHERE profile->>'needs_childcare'='true' "
                "AND NOT EXISTS (SELECT 1 FROM program_matches pm "
                "WHERE pm.intake_id = fie.intake_id AND pm.category='childcare')"
            )
            childcare_unmet = cur.fetchone()[0] or 0

            # Privacy-safe recent journeys: NO raw_user_text / plan / feedback text.
            cur.execute(
                """
                SELECT
                  to_char(fie.event_ts,'YYYY-MM-DD') AS d,
                  COALESCE(NULLIF(fie.profile->>'household_size','')::int,0) AS hh,
                  CASE WHEN jsonb_typeof(fie.profile->'children_ages')='array'
                       THEN jsonb_array_length(fie.profile->'children_ages') ELSE 0 END AS kids,
                  (SELECT pm.category FROM program_matches pm WHERE pm.intake_id=fie.intake_id
                     GROUP BY pm.category ORDER BY COUNT(*) DESC LIMIT 1) AS topcat,
                  (SELECT COUNT(*) FROM program_matches pm WHERE pm.intake_id=fie.intake_id) AS m,
                  (SELECT uf.rating FROM user_feedback uf WHERE uf.intake_id=fie.intake_id
                     ORDER BY uf.event_ts DESC LIMIT 1) AS rating
                FROM family_intake_events fie
                ORDER BY fie.event_ts DESC
                LIMIT 10
                """
            )
            recent_journeys = [
                {
                    "date": d,
                    "household_size": hh,
                    "children": kids,
                    "top_category": _label(topcat),
                    "matches": m,
                    "rating": rating,
                }
                for (d, hh, kids, topcat, m, rating) in cur.fetchall()
            ]

        top_need = category_demand[0]["label"] if category_demand else "—"
        return {
            "kpis": {
                "families_served": families,
                "total_matches": total_matches,
                "avg_matches_per_family": round(total_matches / families, 1) if families else 0,
                "top_need_category": top_need,
                "avg_feedback_rating": float(avg_rating) if avg_rating is not None else 0.0,
                "lakebase_journeys_captured": families,
            },
            "category_demand": category_demand,
            "top_programs": top_programs,
            "profile_trends": {
                "avg_household_size": round(float(avg_hh), 1) if avg_hh is not None else 0.0,
                "pct_with_children": round(float(pct_children), 0) if pct_children is not None else 0.0,
                "pct_pregnant": round(float(pct_pregnant), 0) if pct_pregnant is not None else 0.0,
                "pct_working": round(float(pct_working), 0) if pct_working is not None else 0.0,
                "household_size": household_size,
                "income_bands": income_bands,
            },
            "feedback": {
                "avg_rating": float(avg_rating) if avg_rating is not None else 0.0,
                "responses": responses or 0,
                "distribution": distribution,
            },
            "gaps": {
                "journeys_zero_matches": zero_matches,
                "childcare_need_total": childcare_total,
                "childcare_need_unmet": childcare_unmet,
            },
            "recent_journeys": recent_journeys,
        }
    except Exception as exc:  # noqa: BLE001 - degrade to sample on any failure
        logger.warning("Live analytics unavailable (%s); using sample data.", type(exc).__name__)
        return None
    finally:
        conn.close()


def get_dashboard_data() -> dict[str, Any]:
    """Return dashboard analytics with a 'source' flag.

    source: "lakebase" (live rows), "sample_empty" (Lakebase up, no journeys),
    or "sample" (Lakebase unavailable).
    """
    try:
        live = _fetch_live()
    except Exception:  # noqa: BLE001
        live = None

    if live is None:
        return _with_source(_sample_data(), "sample")
    if live.get("_empty"):
        return _with_source(_sample_data(), "sample_empty")
    return _with_source(live, "lakebase")


if __name__ == "__main__":
    d = get_dashboard_data()
    print("source=", d["source"])
    print("kpi_keys=", sorted(d["kpis"]))
