"""
agent.py

Anthropic Claude reasoning layer (direct API). Claude is used ONLY to:
  * extract a structured family profile from free text,
  * propose 2-3 clarifying questions,
  * merge clarifying answers back into the profile,
  * narrate a warm, grounded action plan from the rules-engine matches.

Claude never decides eligibility - that is the deterministic rules engine's job.
The API key is read from the environment and is never logged.
"""

from __future__ import annotations

import json
import os
from typing import Optional

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

_client = None  # lazily constructed so importing this module never needs a key


def _get_client():
    """Return a cached Anthropic client, constructing it on first use."""
    global _client
    if _client is None:
        import anthropic  # lazy import keeps module import cheap

        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def _strip_fences(text: str) -> str:
    """Remove accidental markdown code fences from a model response."""
    return text.replace("```json", "").replace("```", "").strip()


def _ask(system: str, user: str, max_tokens: int) -> str:
    """Send a single-turn message to Claude and return the text response."""
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def extract_profile_from_text(user_text: str) -> dict:
    """Parse free-text family situation into a structured profile dict."""
    system = """You are a compassionate benefits navigator for New Jersey families.
Extract a structured profile from the family's description. Respond with ONLY valid
JSON - no markdown, no commentary.

Schema:
{
  "household_size": <int total people in household>,
  "monthly_income": <float estimated gross monthly household income USD, 0 if unknown>,
  "has_children": <bool>,
  "children_ages": <list of ints>,
  "pregnant": <bool>,
  "is_documented": <bool true if US citizen or has legal status>,
  "needs_childcare": <bool>,
  "has_dv_concern": <bool domestic violence concern>,
  "is_working": <bool>,
  "free_text_summary": <one-sentence summary>
}

Defaults when unstated: is_documented true, has_dv_concern false, monthly_income 0.
Never invent specific facts that were not implied."""
    raw = _ask(system, user_text, max_tokens=600)
    return json.loads(_strip_fences(raw))


def generate_clarifying_questions(user_text: str, profile: dict) -> list[str]:
    """Return 2-3 short, plain-English follow-up questions as a list of strings."""
    system = """You are a benefits navigator for NJ families. Given the family's
description and the extracted profile, identify the 2-3 most useful missing details
for benefit screening. Return ONLY a JSON array of short conversational question
strings. No markdown, no commentary."""
    user = (
        f"Family description: {user_text}\n\n"
        f"Profile so far: {json.dumps(profile, indent=2)}\n\n"
        "What are the 2-3 most useful follow-up questions?"
    )
    raw = _ask(system, user, max_tokens=300)
    try:
        questions = json.loads(_strip_fences(raw))
        return [str(q) for q in questions][:3]
    except Exception:
        return []


def merge_profile_with_answers(
    profile: dict, questions: list[str], answers: list[str]
) -> dict:
    """Merge clarifying Q&A into the profile, preserving known values."""
    system = """You are updating a family benefits profile with new answers to
clarifying questions. Merge the new information into the existing profile, keeping
prior known values unless an answer clearly overrides them. Return ONLY the updated
JSON profile - no markdown, no commentary."""
    qa_pairs = "\n".join(f"Q: {q}\nA: {a}" for q, a in zip(questions, answers))
    user = (
        f"Existing profile: {json.dumps(profile, indent=2)}\n\n"
        f"New Q&A:\n{qa_pairs}\n\n"
        "Return the updated profile JSON."
    )
    raw = _ask(system, user, max_tokens=600)
    try:
        return json.loads(_strip_fences(raw))
    except Exception:
        return profile  # keep the original profile if the merge can't be parsed


def generate_action_plan(profile: dict, eligible_programs: list[dict]) -> str:
    """Generate a warm, grounded action plan narrated only from matched programs."""
    system = """You are a compassionate, knowledgeable NJ benefits navigator. Write a
warm, practical action plan for this family.

Guidelines:
- Open with a brief empathetic acknowledgment (1-2 sentences).
- Group recommendations by benefit category with clear headers.
- For each program, explain WHY it fits THIS family specifically.
- End with 1-2 concrete steps they can take today.
- Plain, friendly, jargon-free language. 300-450 words.
- Only reference the programs provided. Never guarantee eligibility - say
  "may qualify" or "worth checking". Do not output markdown code blocks or JSON."""
    summary = [
        {
            "name": p.get("name"),
            "category": p.get("category"),
            "description": p.get("description"),
            "how_to_apply": p.get("how_to_apply"),
            "match_reasons": p.get("match_reasons", []),
        }
        for p in eligible_programs
    ]
    user = (
        f"Family profile: {json.dumps(profile, indent=2)}\n\n"
        f"Matched programs: {json.dumps(summary, indent=2)}\n\n"
        "Write a personalized action plan for this family."
    )
    return _ask(system, user, max_tokens=800)
