"""
seed_demo_journeys.py

SYNTHETIC DEMO DATA FOR HACKATHON DASHBOARD ONLY.

Seeds synthetic Benefits Navigator journeys into the Lakebase app-state tables so
the Program Leader Dashboard shows meaningful trends for judges. It writes via the
existing lakebase_client writer functions (intake -> matches -> action plan ->
feedback) and uses the real benefits_rules engine to produce realistic matches.

Privacy / safety:
  * Uses ONLY synthetic, hand-written demo profiles. No real user data.
  * No names, emails, phone numbers, addresses, or any PII.
  * Does NOT call Claude (no API key needed); action plans are fixed synthetic text.
  * Does NOT read or write any secret values, and never creates a .env.

Requires Lakebase to be reachable (PG*/LAKEBASE_* env vars, e.g. locally, or run
inside the deployed app environment). If Lakebase is not configured, it prints a
clear message and exits without writing.

IDEMPOTENCY: NOT idempotent. Each run INSERTS new journeys with fresh UUIDs, so
re-running ADDS more demo journeys. Use --count to control how many to add.

Usage:
  python scripts/seed_demo_journeys.py            # adds the default set
  python scripts/seed_demo_journeys.py --count 6  # add the first 6 synthetic profiles
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from the repo root or the scripts/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import benefits_rules  # noqa: E402
import lakebase_client  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_journeys")

_SYNTHETIC_MODEL = "synthetic-seed"
_SYNTHETIC_PLAN = (
    "Synthetic demo action plan. This record is seeded test data for the Program "
    "Leader Dashboard and does not represent a real family."
)

# Synthetic, PII-free demo profiles spanning a range of situations so the
# dashboard shows varied demand, profiles, and gaps.
_DEMO_PROFILES = [
    {"household_size": 3, "monthly_income": 1800, "has_children": True, "children_ages": [3, 7],
     "pregnant": False, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 2, "monthly_income": 1200, "has_children": True, "children_ages": [1],
     "pregnant": False, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 5, "monthly_income": 2600, "has_children": True, "children_ages": [2, 4, 9],
     "pregnant": True, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": False},
    {"household_size": 4, "monthly_income": 2200, "has_children": True, "children_ages": [5, 11],
     "pregnant": False, "is_documented": True, "needs_childcare": False, "has_dv_concern": False, "is_working": True},
    {"household_size": 1, "monthly_income": 900, "has_children": False, "children_ages": [],
     "pregnant": False, "is_documented": True, "needs_childcare": False, "has_dv_concern": False, "is_working": False},
    {"household_size": 6, "monthly_income": 3100, "has_children": True, "children_ages": [2, 5, 8, 13],
     "pregnant": False, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 3, "monthly_income": 1500, "has_children": True, "children_ages": [4],
     "pregnant": False, "is_documented": False, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 2, "monthly_income": 800, "has_children": True, "children_ages": [0],
     "pregnant": True, "is_documented": True, "needs_childcare": False, "has_dv_concern": True, "is_working": False},
    {"household_size": 4, "monthly_income": 2000, "has_children": True, "children_ages": [3, 6],
     "pregnant": False, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 3, "monthly_income": 2800, "has_children": True, "children_ages": [10, 14],
     "pregnant": False, "is_documented": True, "needs_childcare": False, "has_dv_concern": False, "is_working": True},
    {"household_size": 5, "monthly_income": 1700, "has_children": True, "children_ages": [1, 3, 7],
     "pregnant": False, "is_documented": True, "needs_childcare": True, "has_dv_concern": False, "is_working": True},
    {"household_size": 2, "monthly_income": 1100, "has_children": False, "children_ages": [],
     "pregnant": True, "is_documented": True, "needs_childcare": False, "has_dv_concern": False, "is_working": True},
]

# Simple synthetic ratings cycled across journeys (kept high-ish for a demo).
_RATINGS = [5, 4, 5, 4, 3, 5, 4, 5, 4, 5, 3, 4]

_SYNTHETIC_INTAKE_TEXT = "Synthetic demo journey (seeded). No real personal data."


def seed(count: int) -> int:
    if not lakebase_client.is_configured():
        logger.error(
            "Lakebase is not configured (PG*/LAKEBASE_* env vars missing). "
            "Run where Lakebase is reachable (locally with PG env, or in the app). "
            "No data was written."
        )
        return 0

    programs = benefits_rules.load_programs()
    written = 0
    profiles = _DEMO_PROFILES[: max(0, count)]
    for i, profile in enumerate(profiles):
        matches = benefits_rules.screen_programs(profile, programs)
        intake_id = lakebase_client.write_family_intake_event(profile, _SYNTHETIC_INTAKE_TEXT)
        if not intake_id:
            logger.warning("Skipped a journey: intake write failed (Lakebase unavailable?).")
            continue
        lakebase_client.write_program_matches(intake_id, matches)
        lakebase_client.write_action_plan(intake_id, _SYNTHETIC_PLAN, _SYNTHETIC_MODEL)
        lakebase_client.write_user_feedback(intake_id, _RATINGS[i % len(_RATINGS)], "")
        written += 1
        logger.info("Seeded synthetic journey %d/%d (%d matches).", written, len(profiles), len(matches))

    logger.info("Done. Seeded %d synthetic journey(s) into Lakebase.", written)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed synthetic demo journeys into Lakebase.")
    parser.add_argument(
        "--count", type=int, default=len(_DEMO_PROFILES),
        help=f"How many synthetic journeys to add (max {len(_DEMO_PROFILES)}).",
    )
    args = parser.parse_args()
    written = seed(min(args.count, len(_DEMO_PROFILES)))
    return 0 if written > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
