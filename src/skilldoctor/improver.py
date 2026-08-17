"""Closed-loop description optimization: test -> rewrite -> re-test.

`skilldoctor test` tells you the trigger rate; `improve` fixes it. Each round
the failing trigger phrasings are handed to the LLM, which rewrites the
description to catch them; the candidate is then re-scored against the full
case set (including the no_trigger guardrails) so a "better" description that
starts false-firing never wins.

Nothing is written to disk unless the CLI passes --write.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .parser import find_skill_md, parse_skill, split_frontmatter
from .router_prompt import SkillSummary
from .tester import (
    DEFAULT_MAX_TOKENS,
    Case,
    CaseResult,
    TestReport,
    TesterError,
    evaluate,
    make_client,
)

MAX_DESCRIPTION_CHARS = 1024  # spec limit; listings truncate beyond this

_REWRITE_PROMPT = """\
You are optimizing the `description` field of an agent skill named "{name}".
An agent router sees only skill names and descriptions, and decides which
skill to load for each user request.

Current description:
\"\"\"
{current}
\"\"\"

These user requests SHOULD have loaded this skill, but the router chose \
{losers}:
{failed}

Rewrite the description so these phrasings trigger the skill, while keeping
the existing ones working. Rules:
- Embed the missed phrasings (or their exact vocabulary) verbatim.
- Stay under 400 characters. Keep the original language(s) and intent.
- No keyword stuffing; it must still read like a sentence a human wrote.
Reply with ONLY the new description text. No quotes, no explanation."""


@dataclass
class Round:
    description: str
    report: TestReport

    @property
    def score(self) -> tuple[int, int]:
        # passed count first; on ties prefer the shorter (less gamed) description
        return (self.report.passed, -len(self.description))


@dataclass
class ImproveResult:
    skill_name: str
    rounds: list[Round] = field(default_factory=list)

    @property
    def baseline(self) -> Round:
        return self.rounds[0]

    @property
    def best(self) -> Round:
        return max(self.rounds, key=lambda r: r.score)

    @property
    def improved(self) -> bool:
        return self.best is not self.baseline

    @property
    def solved(self) -> bool:
        return self.best.report.passed == self.best.report.total

    def as_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "solved": self.solved,
            "improved": self.improved,
            "rounds": [
                {"description": r.description, **r.report.as_dict()} for r in self.rounds
            ],
        }


def _failed_trigger_cases(report: TestReport) -> list[CaseResult]:
    return [r for r in report.results if r.case.expect_trigger and not r.passed]


def propose_description(
    client,
    model: str,
    name: str,
    current: str,
    failed: list[CaseResult],
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Ask the LLM for a better description given what failed."""
    failed_lines = "\n".join(f'- "{r.case.input}"' for r in failed)
    stolen = {r.chosen for r in failed if r.chosen}
    losers = "nothing (NONE)" if not stolen else "/".join(sorted(stolen))
    completion = client.chat.completions.create(
        model=model,
        temperature=0.7,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": _REWRITE_PROMPT.format(
            name=name, current=current, failed=failed_lines, losers=losers)}],
    )
    proposal = (completion.choices[0].message.content or "").strip().strip('"').strip()
    return proposal


def improve_skill(
    skill_dir: Path,
    cases: list[Case],
    skills: list[SkillSummary],
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    rounds: int = 3,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> ImproveResult:
    """Iterate: evaluate -> rewrite the description -> re-evaluate.

    `skills[0]` must be the target skill's summary (see collect_summaries).
    """
    client = make_client(api_key, base_url)
    target = parse_skill(skill_dir)
    target_name = target.name or Path(skill_dir).name
    if not skills or skills[0].name != target_name:
        raise TesterError("internal error: skills[0] must be the skill under test")

    result = ImproveResult(skill_name=target_name)
    description = target.description or ""
    current_skills = list(skills)

    for round_no in range(rounds + 1):
        report = evaluate(client, model, target_name, current_skills, cases, max_tokens)
        result.rounds.append(Round(description=description, report=report))
        if report.passed == report.total or round_no == rounds:
            break
        proposal = propose_description(
            client, model, target_name, description, _failed_trigger_cases(report), max_tokens
        )
        if not proposal or proposal == description or len(proposal) > MAX_DESCRIPTION_CHARS:
            break  # model gave up / repeated itself / blew the spec limit
        description = proposal
        current_skills = [SkillSummary(name=target_name, description=description), *current_skills[1:]]
    return result


def write_description(skill_dir: Path, new_description: str) -> Path:
    """Replace `description` in SKILL.md frontmatter, preserving the body."""
    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        raise TesterError(f"SKILL.md not found in {skill_dir}")
    raw = skill_md.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(raw)
    frontmatter = yaml.safe_load(fm_text)
    frontmatter["description"] = new_description
    new_fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).rstrip("\n")
    skill_md.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
    return skill_md
