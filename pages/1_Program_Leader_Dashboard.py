"""
pages/1_Program_Leader_Dashboard.py

Program Leader Analytics Dashboard (Streamlit multipage). Persona: a nonprofit /
state Benefits Operations Director who needs to understand benefit demand, family
profile patterns, service gaps, and trust - from completed Benefits Navigator
journeys.

All figures are PRIVACY-SAFE AGGREGATES from the Lakebase app-state tables. No raw
user text is ever shown. Data comes from analytics_client; if Lakebase is
unavailable (or has no journeys yet) the page shows clearly-labeled sample data.
"""

import pandas as pd  # transitive dependency of streamlit; not imported in analytics_client
import streamlit as st

import analytics_client

st.set_page_config(page_title="Program Leader Analytics", page_icon="🏛️", layout="wide")


@st.cache_data(ttl=60, show_spinner=False)
def _load():
    return analytics_client.get_dashboard_data()


data = _load()
source = data["source"]

st.title("🏛️ Program Leader Analytics")
st.caption("Operational insight for a Benefits Operations Director — benefit demand, family patterns, and service gaps.")

if source == "lakebase":
    st.success("🟢 Live Lakebase analytics — aggregated from captured journeys.")
elif source == "sample_empty":
    st.info("No live journeys yet — showing sample dashboard data.")
else:
    st.warning("Using sample dashboard data because Lakebase analytics is unavailable.")

# ── KPI cards ─────────────────────────────────────────────────────────────────
k = data["kpis"]
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Families Served", f"{k['families_served']:,}")
c2.metric("Total Program Matches", f"{k['total_matches']:,}")
c3.metric("Avg Matches / Family", f"{k['avg_matches_per_family']:.1f}")
c4.metric("Top Need Category", k["top_need_category"])
c5.metric("Avg Feedback Rating", f"{k['avg_feedback_rating']:.1f} ★")
c6.metric("Lakebase Journeys Captured", f"{k['lakebase_journeys_captured']:,}")

st.divider()

# ── Demand: category + top programs ───────────────────────────────────────────
left, right = st.columns(2)
with left:
    st.subheader("Program Matches by Category")
    st.caption("Which kinds of benefits families are matched to most.")
    cat_df = pd.DataFrame(data["category_demand"])
    if not cat_df.empty:
        st.bar_chart(cat_df.set_index("label")["matches"], color="#2e86de")
with right:
    st.subheader("Top Matched Programs")
    st.caption("Individual programs doing the most work for families.")
    prog_df = pd.DataFrame(data["top_programs"])
    if not prog_df.empty:
        st.bar_chart(prog_df.set_index("program")["matches"], horizontal=True, color="#256a35")

st.divider()

# ── Family profile trends ─────────────────────────────────────────────────────
st.subheader("Family Profile Trends")
st.caption("Privacy-safe aggregates — no individual is identifiable.")
pt = data["profile_trends"]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Avg Household Size", f"{pt['avg_household_size']:.1f}")
m2.metric("With Children", f"{pt['pct_with_children']:.0f}%")
m3.metric("Pregnant", f"{pt['pct_pregnant']:.0f}%")
m4.metric("Working", f"{pt['pct_working']:.0f}%")

t1, t2 = st.columns(2)
with t1:
    st.caption("Household size distribution")
    hh_df = pd.DataFrame(pt["household_size"])
    if not hh_df.empty:
        st.bar_chart(hh_df.set_index("bucket")["families"], color="#7e57c2")
with t2:
    st.caption("Income band (monthly)")
    inc_df = pd.DataFrame(pt["income_bands"])
    if not inc_df.empty:
        st.bar_chart(inc_df.set_index("band")["families"], color="#ef8c43")

st.divider()

# ── Feedback & trust ──────────────────────────────────────────────────────────
st.subheader("Feedback & Trust")
fb = data["feedback"]
f1, f2 = st.columns([1, 2])
with f1:
    st.metric("Average Rating", f"{fb['avg_rating']:.1f} ★")
    st.metric("Responses", f"{fb['responses']:,}")
with f2:
    st.caption("Rating distribution (1–5)")
    fb_df = pd.DataFrame(fb["distribution"])
    if not fb_df.empty:
        st.bar_chart(fb_df.set_index("rating")["count"], color="#2e86de")

st.divider()

# ── Service gaps ──────────────────────────────────────────────────────────────
st.subheader("Where Are the Gaps?")
g = data["gaps"]
unmet_pct = (
    100.0 * g["childcare_need_unmet"] / g["childcare_need_total"]
    if g["childcare_need_total"]
    else 0.0
)
g1, g2, g3 = st.columns(3)
g1.metric("Journeys With 0 Matches", f"{g['journeys_zero_matches']:,}")
g2.metric("Families Needing Childcare", f"{g['childcare_need_total']:,}")
g3.metric("Childcare Need Unmet", f"{g['childcare_need_unmet']:,}", f"{unmet_pct:.0f}% of need")
st.caption(
    "Gaps highlight where demand outpaces matches — useful for prioritizing outreach, "
    "partnerships, and program coverage."
)

st.divider()

# ── Recent journeys (privacy-safe) ────────────────────────────────────────────
st.subheader("Recent Journeys")
st.caption("Aggregate attributes only — no names, contact details, or free-text input is shown.")
rj_df = pd.DataFrame(data["recent_journeys"])
if not rj_df.empty:
    rj_df = rj_df.rename(
        columns={
            "date": "Date",
            "household_size": "Household",
            "children": "Children",
            "top_category": "Top Need",
            "matches": "Matches",
            "rating": "Rating",
        }
    )
    st.dataframe(rj_df, use_container_width=True, hide_index=True)

st.caption(
    "🔒 Privacy: this dashboard shows synthetic, aggregate analytics only. It never "
    "displays raw user text, action-plan text, or feedback comments. Refreshes every 60s."
)
