"""
smoke_local_path.py

Deterministic smoke test for the fully-local path (no API key, no network, no DB
writes, no secrets). It loads the bundled trusted-data fallback (sample_data/
programs.json) and runs the deterministic rules engine against the main demo profile,
asserting the expected 8 program matches.

Run:  py -3.11 tests/smoke_local_path.py
Pass: prints the 8 matched ids, prints SMOKE_OK, exits 0.
Fail: prints the mismatch and exits 1.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from anywhere: put the repo root (parent of tests/) on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benefits_rules import load_programs, screen_programs  # noqa: E402

# Main demo scenario: single mom, 2 kids (3 & 7), ~$1,800/mo, working part-time,
# needs food/childcare/healthcare. Mirrors docs/TESTING.md.
DEMO_PROFILE = {
    "household_size": 3,
    "monthly_income": 1800,
    "has_children": True,
    "children_ages": [3, 7],
    "pregnant": False,
    "is_documented": True,
    "needs_childcare": True,
    "has_dv_concern": False,
    "is_working": True,
}

EXPECTED_IDS = [
    "snap",
    "wic",
    "nj_familycare",
    "chip",
    "ccdf",
    "preschool",
    "liheap",
    "211nj",
]


def main() -> int:
    programs = load_programs()
    matched = screen_programs(DEMO_PROFILE, programs)
    matched_ids = [p["id"] for p in matched]

    for pid in matched_ids:
        print(pid)

    if matched_ids != EXPECTED_IDS:
        print("SMOKE_FAIL")
        print(f"  expected: {EXPECTED_IDS}")
        print(f"  actual:   {matched_ids}")
        missing = [p for p in EXPECTED_IDS if p not in matched_ids]
        extra = [p for p in matched_ids if p not in EXPECTED_IDS]
        if missing:
            print(f"  missing:  {missing}")
        if extra:
            print(f"  extra:    {extra}")
        return 1

    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
