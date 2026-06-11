"""
app.py

Benefits Navigator for Families - NJ MVP. Streamlit Databricks App.

Data flow:
  1. Family describes their situation in free text.
  2. Claude extracts a structured profile + clarifying questions (agent.py).
  3. Trusted programs load from Unity Catalog via SQL Warehouse, with a local
     JSON fallback (databricks_client.py / benefits_rules.py).
  4. A deterministic rules engine screens programs (benefits_rules.py).
  5. Claude narrates a grounded action plan (agent.py).
  6. App-state is written to Lakebase first, SQLite fallback second
     (lakebase_client.py / local_state_client.py).

No secrets are read or logged here; all persistence degrades gracefully.
"""

from __future__ import annotations

import logging
import os

import streamlit as st

from agent import (
    MODEL,
    extract_profile_from_text,
    generate_action_plan,
    generate_clarifying_questions,
    merge_profile_with_answers,
)
from benefits_rules import (
    CATEGORY_LABELS,
    group_by_category,
    load_programs,
    screen_programs,
)
from databricks_client import get_benefit_programs_from_databricks
import lakebase_client
import local_state_client as local_state

logger = logging.getLogger(__name__)


# ── Trusted data loading (Unity Catalog first, local JSON fallback) ────────────
def _adapt_databricks_programs(rows: list[dict]) -> list[dict]:
    """Map trusted Unity Catalog rows to the keys the rules engine/UI expect."""
    adapted = []
    for r in rows:
        apply_bits = []
        if r.get("apply_url"):
            apply_bits.append(f"Apply online at {r['apply_url']}")
        if r.get("apply_phone"):
            apply_bits.append(f"call {r['apply_phone']}")
        how_to_apply = (
            " or ".join(apply_bits)
            if apply_bits
            else (r.get("eligibility_summary") or "Contact the program for details.")
        )
        income_limit = r.get("income_limit_pct_fpl")
        adapted.append(
            {
                "id": r.get("rule_key") or r.get("program_id"),
                "program_id": r.get("program_id"),
                "name": r.get("program_name"),
                "category": r.get("category"),
                "description": r.get("description") or "",
                "eligibility_notes": r.get("eligibility_summary") or "",
                "how_to_apply": how_to_apply,
                "url": r.get("apply_url") or r.get("source_url") or "",
                "income_limit_pct_fpl": 999 if income_limit is None else income_limit,
                "accepts_undocumented": bool(r.get("accepts_undocumented")),
                "source_name": r.get("source_name"),
                "source_url": r.get("source_url"),
                "source_type": r.get("source_type"),
            }
        )
    return adapted


@st.cache_data(show_spinner=False)
def load_benefit_programs() -> tuple[list[dict], str]:
    """Return (programs, source). source is "databricks" or "local".

    BENEFITS_DATA_MODE controls behavior:
      * "json_only"        -> always use the bundled local JSON (deterministic Test A)
      * "databricks_first" -> try Unity Catalog, fall back to local JSON (default)
    """
    mode = os.environ.get("BENEFITS_DATA_MODE", "databricks_first").lower()
    if mode != "json_only":
        rows = get_benefit_programs_from_databricks()
        if rows:
            return _adapt_databricks_programs(rows), "databricks"
    return load_programs(), "local"


# ── Page setup ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Benefits Navigator NJ",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .badge { display:inline-block; background:#e8f4fd; color:#1a3a5c; font-size:0.75rem;
             font-weight:700; padding:3px 10px; border-radius:20px; margin-bottom:0.5rem;
             letter-spacing:0.5px; text-transform:uppercase; }
    .hero-title { font-size:2.2rem; font-weight:800; color:#1a3a5c; line-height:1.2; }
    .hero-sub { font-size:1.05rem; color:#4a6a8a; margin-bottom:1rem; }
    .step-indicator { background:#2e86de; color:white; font-weight:700; font-size:0.8rem;
                      padding:4px 14px; border-radius:20px; display:inline-block;
                      margin-bottom:0.75rem; }
    .program-card { background:#fff; border:1px solid #dce8f5; border-left:5px solid #2e86de;
                    border-radius:10px; padding:1rem 1.25rem; margin-bottom:0.85rem; }
    .program-name { font-weight:700; font-size:1rem; color:#1a3a5c; margin-bottom:0.2rem; }
    .program-desc { font-size:0.88rem; color:#4a6a8a; margin-bottom:0.4rem; }
    .reason-tag { display:inline-block; background:#eaf7ec; color:#256a35; font-size:0.75rem;
                  font-weight:600; padding:2px 8px; border-radius:12px; margin:0 4px 4px 0; }
    .apply-link { font-size:0.82rem; color:#2e86de; font-weight:600; }
    .action-plan-box { background:#f0f7ff; border:1px solid #c0d9f0; border-radius:12px;
                       padding:1.5rem; margin-top:1rem; font-size:0.95rem; line-height:1.7;
                       color:#1a3a5c; white-space:pre-wrap; }
    .disclaimer { font-size:0.78rem; color:#8aa0b8; margin-top:2rem; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="badge">🗽 New Jersey · Free · Confidential</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">🧭 Benefits Navigator for Families</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Tell us about your family - we\'ll find the right support '
    "programs and build your action plan.</div>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Load trusted data and label the source ─────────────────────────────────────
programs_data, data_source = load_benefit_programs()
if data_source == "databricks":
    st.caption("🔒 Using trusted Databricks benefits data")
else:
    st.caption("📁 Using local fallback benefits data")

# ── Session state ──────────────────────────────────────────────────────────────
_DEFAULT_KEYS = [
    "stage", "profile", "questions", "eligible_programs", "action_plan",
    "raw_user_text", "intake_id", "state_storage_mode", "feedback_saved_where",
    "feedback_submitted",
]
for key in _DEFAULT_KEYS:
    st.session_state.setdefault(key, None)
if st.session_state.stage is None:
    st.session_state.stage = "intake"


def _save_app_state(profile, raw_text, eligible, plan) -> tuple[str | None, str]:
    """Write state to Lakebase first, then SQLite. Returns (intake_id, storage_mode)."""
    try:
        intake_id = lakebase_client.write_family_intake_event(profile, raw_text or "")
        if intake_id:
            matches_ok = lakebase_client.write_program_matches(intake_id, eligible)
            plan_id = lakebase_client.write_action_plan(intake_id, plan, MODEL)
            if matches_ok and plan_id:
                return intake_id, "lakebase"
    except Exception:  # noqa: BLE001 - never surface internals to the UI
        pass

    logger.warning("Lakebase app-state unavailable; using local SQLite fallback.")
    try:
        local_intake_id = local_state.write_family_intake_event(profile, raw_text or "")
        if local_intake_id:
            local_state.write_program_matches(local_intake_id, eligible)
            local_state.write_action_plan(local_intake_id, plan, MODEL)
            return local_intake_id, "sqlite_fallback"
    except Exception:  # noqa: BLE001
        pass

    logger.error("App-state saving failed in BOTH Lakebase and SQLite.")
    return None, "none"


# ════════════════════════════ STAGE 1 - INTAKE ════════════════════════════════
if st.session_state.stage == "intake":
    st.markdown('<div class="step-indicator">Step 1 of 3 - Tell us about your family</div>', unsafe_allow_html=True)
    user_text = st.text_area(
        "Describe your family situation in your own words:",
        placeholder=(
            "For example: I'm a single mom with two kids ages 3 and 7. I work part-time "
            "and make about $1,800 a month. We don't have health insurance right now and "
            "I need childcare help."
        ),
        height=140,
        key="intake_text",
    )
    if st.button("Find Benefits →"):
        if not user_text.strip():
            st.warning("Please describe your situation first.")
        else:
            with st.spinner("Understanding your situation..."):
                st.session_state.profile = extract_profile_from_text(user_text)
                st.session_state.questions = generate_clarifying_questions(
                    user_text, st.session_state.profile
                )
                st.session_state.raw_user_text = user_text
                st.session_state.stage = "clarify"
                st.rerun()

# ════════════════════════ STAGE 2 - CLARIFYING QUESTIONS ══════════════════════
elif st.session_state.stage == "clarify":
    st.markdown('<div class="step-indicator">Step 2 of 3 - A few quick questions</div>', unsafe_allow_html=True)
    st.markdown("Just a couple more details to make your plan as accurate as possible.")

    questions = st.session_state.questions or []
    answers = [st.text_input(q, key=f"clarify_{i}") for i, q in enumerate(questions)]

    col1, col2 = st.columns([1, 3])
    next_btn = col1.button("Build My Plan →")
    skip_btn = col2.button("Skip - use what you have")

    if next_btn or skip_btn:
        with st.spinner("Screening programs and building your plan..."):
            profile = st.session_state.profile
            if next_btn and any(a.strip() for a in answers):
                profile = merge_profile_with_answers(profile, questions, answers)
            st.session_state.profile = profile

            eligible = screen_programs(profile, programs_data)
            st.session_state.eligible_programs = eligible

            if eligible:
                plan = generate_action_plan(profile, eligible)
            else:
                plan = (
                    "We weren't able to match specific programs right now - but don't "
                    "give up! Call NJ 2-1-1 (dial 2-1-1 or text your zip to 898-211) "
                    "anytime for free, expert help finding local resources."
                )
            st.session_state.action_plan = plan

            intake_id, storage_mode = _save_app_state(
                profile, st.session_state.raw_user_text, eligible, plan
            )
            st.session_state.intake_id = intake_id
            st.session_state.state_storage_mode = storage_mode
            st.session_state.stage = "results"
            st.rerun()

# ════════════════════════════ STAGE 3 - RESULTS ═══════════════════════════════
elif st.session_state.stage == "results":
    st.markdown('<div class="step-indicator">Step 3 of 3 - Your Personalized Action Plan</div>', unsafe_allow_html=True)

    st.markdown("### 📋 Your Action Plan")
    st.markdown(f'<div class="action-plan-box">{st.session_state.action_plan}</div>', unsafe_allow_html=True)

    mode = st.session_state.state_storage_mode
    if mode == "lakebase":
        st.success("Plan saved to Lakebase app-state tables.")
    elif mode == "sqlite_fallback":
        st.info(
            "Plan generated successfully. Lakebase is unavailable, so this session was "
            "saved locally in SQLite for demo fallback."
        )
    elif mode == "none":
        st.warning("Plan generated successfully, but app-state saving failed.")

    st.markdown("---")

    eligible = st.session_state.eligible_programs or []
    if eligible:
        st.markdown(f"### 🎯 Programs You May Qualify For ({len(eligible)} found)")
        grouped = group_by_category(eligible)
        for cat, label in CATEGORY_LABELS.items():
            progs = grouped.get(cat, [])
            if not progs:
                continue
            st.markdown(f"#### {label}")
            for p in progs:
                reasons_html = "".join(
                    f'<span class="reason-tag">✓ {r}</span>' for r in p.get("match_reasons", [])
                )
                st.markdown(
                    f"""
                    <div class="program-card">
                        <div class="program-name">{p['name']}</div>
                        <div class="program-desc">{p['description']}</div>
                        {reasons_html}<br/><br/>
                        <span class="apply-link">📌 How to apply: {p['how_to_apply']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No programs matched. Try calling NJ 2-1-1 for personalized help.")

    st.markdown("---")

    # ── Feedback ───────────────────────────────────────────────────────────────
    st.markdown("### 💬 Was this helpful?")
    if st.session_state.feedback_submitted:
        if st.session_state.feedback_saved_where == "sqlite_fallback":
            st.success("Thanks for your feedback! Saved locally in SQLite for demo fallback.")
        else:
            st.success("Thanks for your feedback! Saved to Lakebase.")
    else:
        rating = st.slider("Rate your plan (1 = not helpful, 5 = very helpful)", 1, 5, 5, key="fb_rating")
        comment = st.text_area("Any comments? (optional)", key="fb_comment")
        if st.button("Submit Feedback"):
            feedback_id, saved_where = None, None
            if st.session_state.state_storage_mode != "sqlite_fallback":
                try:
                    feedback_id = lakebase_client.write_user_feedback(
                        st.session_state.intake_id, rating, comment
                    )
                except Exception:  # noqa: BLE001
                    feedback_id = None
                if feedback_id:
                    saved_where = "lakebase"
            if not feedback_id:
                try:
                    feedback_id = local_state.write_user_feedback(
                        st.session_state.intake_id, rating, comment
                    )
                except Exception:  # noqa: BLE001
                    feedback_id = None
                if feedback_id:
                    saved_where = "sqlite_fallback"
            if feedback_id:
                st.session_state.feedback_saved_where = saved_where
                st.session_state.feedback_submitted = True
                st.rerun()
            else:
                st.warning("Feedback could not be saved right now.")

    st.markdown("---")
    if st.button("🔄 Start Over"):
        for key in _DEFAULT_KEYS:
            st.session_state[key] = None
        for wkey in ["intake_text", "fb_rating", "fb_comment"]:
            st.session_state.pop(wkey, None)
        st.rerun()

    if os.environ.get("SHOW_LOCAL_STATE_DEBUG", "").lower() == "true":
        with st.expander("Local SQLite fallback state counts"):
            st.write("Database path:", local_state.get_db_path())
            st.write(local_state.get_local_state_counts())

    st.markdown(
        '<div class="disclaimer">⚠️ This tool provides general information only and does '
        "not constitute legal or financial advice. Eligibility is determined by the "
        "relevant agency. Always verify directly with program administrators.</div>",
        unsafe_allow_html=True,
    )
