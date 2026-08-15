"""Best-practice linting for agent skills.

`validate` checks whether a skill is *correct*; `lint` checks whether it
is *good*. Rules here come from community best practices around trigger
rate, progressive disclosure and guardrails.
"""

from __future__ import annotations

import re
from pathlib import Path

from .issues import Issue, Level
from .parser import SkillDoc, SkillParseError, parse_skill

BODY_LINE_TARGET = 150
# CJK text is much denser than English; a 30-char Chinese description can
# already carry a full "what + when" sentence, so keep the floor low.
DESC_MIN_CHARS = 30

# Signals that the description tells the agent *when* to load the skill,
# not just what it is. Multi-language on purpose.
_TRIGGER_HINTS = [
    "use when",
    "use this when",
    "when the user",
    "trigger",
    "使用场景",
    "当用户",
    "适用于",
    "触发",
]

# Words that indicate guardrails against hallucination / overreach.
_GUARDRAIL_HINTS = [
    "do not invent",
    "never fabricate",
    "do not make up",
    "ask the user",
    "不要编造",
    "不得虚构",
    "不要臆造",
    "信息不足",
    "向用户确认",
]

_QUOTED_PHRASE_RE = re.compile(r"[\"'“”「]([^\"'“”」]{2,40})[\"'“”」]")


def _check_description_quality(doc: SkillDoc) -> list[Issue]:
    desc = (doc.description or "").strip()
    if not desc:
        return []
    issues: list[Issue] = []
    lowered = desc.lower()
    if len(desc) < DESC_MIN_CHARS:
        issues.append(
            Issue(
                Level.WARNING,
                "desc-too-short",
                f"description is only {len(desc)} chars; the description is the *only* signal "
                "the agent uses to decide whether to load this skill — state what it does AND when to use it",
            )
        )
    if not any(hint in lowered for hint in _TRIGGER_HINTS):
        issues.append(
            Issue(
                Level.WARNING,
                "desc-no-trigger",
                "description does not mention when to use this skill; "
                "add trigger scenarios (e.g. \"Use when the user asks to ...\") or example phrasings",
            )
        )
    if not _QUOTED_PHRASE_RE.search(desc):
        issues.append(
            Issue(
                Level.INFO,
                "desc-no-phrasings",
                "description contains no quoted example phrasings; embedding 2-3 verbatim user "
                "phrasings is the most reliable way to raise trigger rate",
            )
        )
    return issues


def _check_body(doc: SkillDoc) -> list[Issue]:
    issues: list[Issue] = []
    n_lines = len(doc.body_lines)
    if n_lines > BODY_LINE_TARGET:
        issues.append(
            Issue(
                Level.WARNING,
                "body-too-long",
                f"body is {n_lines} lines (target ≤ {BODY_LINE_TARGET}); move detail into "
                "references/*.md and link to it — the body is only loaded on trigger, keep it lean",
            )
        )
    lowered = doc.body.lower()
    if not any(hint in lowered for hint in _GUARDRAIL_HINTS):
        issues.append(
            Issue(
                Level.INFO,
                "no-guardrails",
                "body has no explicit guardrails; add at least one instruction preventing the "
                "model from inventing facts (e.g. \"If information is missing, ask the user instead of guessing\")",
            )
        )
    return issues


def lint_skill(skill_dir: Path) -> list[Issue]:
    skill_dir = Path(skill_dir)
    try:
        doc = parse_skill(skill_dir)
    except SkillParseError as exc:
        return [Issue(Level.ERROR, "parse", str(exc))]
    return _check_description_quality(doc) + _check_body(doc)


def lint_path(root: Path) -> dict[str, list[Issue]]:
    from .validator import iter_skill_dirs

    results: dict[str, list[Issue]] = {}
    for skill_dir in iter_skill_dirs(root):
        issues = lint_skill(skill_dir)
        for issue in issues:
            issue.skill = skill_dir.name
        results[skill_dir.name] = issues
    return results
