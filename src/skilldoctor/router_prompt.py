"""Prompt construction and response parsing for the simulated skill router.

An agent decides which skill to load by scanning the listing of
(name + description) pairs. We reproduce that decision context as a
plain prompt so any OpenAI-compatible chat model can stand in for the
router. Everything in this module is pure and offline-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SYSTEM_PROMPT = (
    "You are the skill router of an AI coding agent. At startup you receive a list of "
    "available skills, each described only by its name and description. When the user "
    "sends a request, you decide whether to load exactly one of these skills or none "
    "at all. Answer with ONLY the skill name, or the word NONE. No explanation."
)


@dataclass
class SkillSummary:
    name: str
    description: str


def build_listing(skills: list[SkillSummary]) -> str:
    """Render the skill listing exactly as an agent would see it."""
    lines = []
    for skill in skills:
        desc = " ".join(skill.description.split())  # collapse whitespace like a real listing
        lines.append(f"- {skill.name}: {desc}")
    return "\n".join(lines)


def build_router_prompt(skills: list[SkillSummary], user_input: str) -> str:
    return (
        "Available skills:\n"
        f"{build_listing(skills)}\n\n"
        f"User request: {user_input}\n\n"
        "Which skill should be loaded? Reply with the skill name or NONE."
    )


def parse_decision(response: str, skills: list[SkillSummary]) -> str | None:
    """Extract the chosen skill name from the router's reply.

    Returns the skill name, or None when the router chose none / the reply
    cannot be mapped back to a known skill.
    """
    text = response.strip().strip('"`').strip()
    if not text or text.upper() == "NONE":
        return None
    names = {s.name for s in skills}
    if text in names:
        return text
    # Tolerate chatty models: look for a skill name mentioned in the reply.
    match = re.search(r"[a-z0-9]+(?:-[a-z0-9]+)+", text.lower())
    if match and match.group(0) in names:
        return match.group(0)
    for name in names:
        if name in text:
            return name
    return None
