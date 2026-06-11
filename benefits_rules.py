"""
benefits_rules.py

Deterministic, explainable eligibility pre-screening for NJ benefit programs.

This is a transparent rules engine - NOT a legal eligibility determination. Every
match carries human-readable reasons so the app can explain *why* a program was
surfaced. The LLM never decides eligibility; it only narrates the rule output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# 2024 Federal Poverty Level - approximate gross MONTHLY income by household size.
FPL_MONTHLY = {
    1: 1255,
    2: 1704,
    3: 2152,
    4: 2601,
    5: 3049,
    6: 3498,
    7: 3946,
    8: 4395,
}
# Each additional person beyond 8 adds roughly this much per month.
_FPL_INCREMENT = 448

# Category keys -> display labels (drives the grouped results UI).
CATEGORY_LABELS = {
    "food": "🥦 Food Support",
    "healthcare": "🏥 Healthcare",
    "childcare": "👶 Childcare",
    "cash": "💵 Cash & Basic Support",
    "family": "🏠 Family Resources",
}


def load_programs() -> list[dict]:
    """Load the bundled local fallback program list from sample_data/programs.json."""
    path = Path(__file__).parent / "sample_data" / "programs.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["programs"]


def get_fpl_monthly(household_size: int) -> int:
    """Return the approximate monthly FPL threshold for a household size (>=1)."""
    size = max(int(household_size or 1), 1)
    if size <= 8:
        return FPL_MONTHLY[size]
    return FPL_MONTHLY[8] + (size - 8) * _FPL_INCREMENT


def income_pct_fpl(monthly_income: float, household_size: int) -> float:
    """Return household income as a percent of the monthly FPL (0 if base is 0)."""
    base = get_fpl_monthly(household_size)
    if not base:
        return 0.0
    return (float(monthly_income or 0) / base) * 100.0


def screen_programs(profile: dict, programs: Optional[list[dict]] = None) -> list[dict]:
    """Screen programs against a family profile and return likely-eligible ones.

    Each returned program is a shallow copy with an added ``match_reasons`` list.
    When ``programs`` is omitted the bundled local JSON is used; callers may pass a
    trusted dataset (e.g. adapted Unity Catalog rows) instead - the keys are the same.

    Profile keys used: household_size, monthly_income, has_children, children_ages,
    pregnant, is_documented, needs_childcare, has_dv_concern, is_working.
    """
    if programs is None:
        programs = load_programs()

    household_size = profile.get("household_size", 1)
    monthly_income = profile.get("monthly_income", 0)
    pct_fpl = income_pct_fpl(monthly_income, household_size)
    ages = profile.get("children_ages") or []

    eligible: list[dict] = []

    for prog in programs:
        reasons: list[str] = []
        income_limit = prog.get("income_limit_pct_fpl", 999)
        accepts_undocumented = prog.get("accepts_undocumented", False)

        # Income gate: skip if the household is clearly over the program's cap.
        if pct_fpl > income_limit:
            continue

        # Documentation gate: skip programs that require status if the family lacks it.
        if not profile.get("is_documented", True) and not accepts_undocumented:
            continue

        category = prog.get("category")
        pid = prog.get("id")

        if category == "food":
            if pid == "snap":
                reasons.append(f"Income (~{pct_fpl:.0f}% FPL) is within the typical SNAP range")
            elif pid == "wic":
                if profile.get("pregnant") or any(a < 5 for a in ages):
                    reasons.append("Pregnancy or a child under 5 qualifies for WIC")
                else:
                    continue

        elif category == "healthcare":
            if pid == "nj_familycare":
                reasons.append("NJ FamilyCare covers most low-income families")
            elif pid == "chip":
                if not any(a < 19 for a in ages):
                    continue
                reasons.append("A child under 19 may qualify for CHIP")

        elif category == "childcare":
            if pid == "ccdf":
                if not profile.get("needs_childcare") or not profile.get("is_working"):
                    continue
                if not any(a < 13 for a in ages):
                    continue
                reasons.append("A working parent with a child under 13 may qualify for a subsidy")
            elif pid == "preschool":
                if not any(a in (3, 4) for a in ages):
                    continue
                reasons.append("A child age 3-4 may qualify for free NJ preschool")

        elif category == "cash":
            if pid == "tanf":
                if not profile.get("has_children"):
                    continue
                reasons.append("A family with children may qualify for TANF cash assistance")
            elif pid == "ga":
                if profile.get("has_children"):
                    continue  # General Assistance is for adults without children
                reasons.append("A single adult may qualify for General Assistance")
            elif pid == "liheap":
                reasons.append("A low-income household may qualify for energy bill assistance")

        elif category == "family":
            if pid == "211nj":
                reasons.append("NJ 2-1-1 connects every family to local resources")
            elif pid == "ece_home_visit":
                if not profile.get("pregnant") and not any(a <= 2 for a in ages):
                    continue
                reasons.append("First-time parents with a newborn may receive free home visits")
            elif pid == "dv_services":
                if not profile.get("has_dv_concern"):
                    continue
                reasons.append("Domestic violence services are available regardless of income")

        prog_copy = dict(prog)
        prog_copy["match_reasons"] = reasons or ["May be eligible based on income"]
        eligible.append(prog_copy)

    return eligible


def group_by_category(programs: list[dict]) -> dict[str, list[dict]]:
    """Group screened programs into a {category: [programs]} dict."""
    grouped: dict[str, list[dict]] = {}
    for prog in programs:
        grouped.setdefault(prog.get("category", "family"), []).append(prog)
    return grouped
