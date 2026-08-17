"""Trigger-rate testing: run declarative cases against a simulated router.

Cases live in a YAML file (default: skilldoctor.cases.yml in the skill dir):

    cases:
      - input: "帮我把这篇笔记改成小红书风格"
        expect: trigger        # this skill should be chosen
      - input: "帮我写公众号推文"
        expect: no_trigger     # adjacent request, must NOT trigger

The router is any OpenAI-compatible chat model. This is an *approximation*
of real agent routing — good enough to iterate on descriptions, not a
guarantee of in-agent behavior.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .parser import parse_skill
from .router_prompt import SYSTEM_PROMPT, SkillSummary, build_router_prompt, parse_decision

DEFAULT_CASE_FILES = ("skilldoctor.cases.yml", "skilldoctor.cases.yaml", "cases.yml")


class TesterError(Exception):
    pass


@dataclass
class Case:
    input: str
    expect_trigger: bool


@dataclass
class CaseResult:
    case: Case
    chosen: str | None  # skill name chosen by the router, None = no skill
    target_name: str

    @property
    def triggered(self) -> bool:
        return self.chosen == self.target_name

    @property
    def passed(self) -> bool:
        return self.triggered == self.case.expect_trigger


@dataclass
class TestReport:
    skill_name: str
    results: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def trigger_rate(self) -> float | None:
        expected = [r for r in self.results if r.case.expect_trigger]
        if not expected:
            return None
        return sum(1 for r in expected if r.triggered) / len(expected)

    @property
    def false_positive_rate(self) -> float | None:
        adjacent = [r for r in self.results if not r.case.expect_trigger]
        if not adjacent:
            return None
        return sum(1 for r in adjacent if r.triggered) / len(adjacent)

    def as_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "passed": self.passed,
            "total": self.total,
            "trigger_rate": self.trigger_rate,
            "false_positive_rate": self.false_positive_rate,
            "cases": [
                {
                    "input": r.case.input,
                    "expect_trigger": r.case.expect_trigger,
                    "chosen": r.chosen,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }


def load_cases(path: Path) -> list[Case]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise TesterError(f"{path} must contain a top-level `cases:` list")
    cases = []
    for i, item in enumerate(data["cases"], start=1):
        try:
            expect = str(item["expect"])
            cases.append(Case(input=str(item["input"]), expect_trigger=expect == "trigger"))
        except KeyError as exc:
            raise TesterError(f"case #{i} in {path} is missing field {exc}") from exc
    return cases


def find_cases_file(skill_dir: Path) -> Path:
    for name in DEFAULT_CASE_FILES:
        candidate = Path(skill_dir) / name
        if candidate.is_file():
            return candidate
    raise TesterError(
        f"no cases file found in {skill_dir} (expected one of: {', '.join(DEFAULT_CASE_FILES)})"
    )


def collect_summaries(skill_dir: Path, extra_dirs: list[Path] | None = None) -> list[SkillSummary]:
    """Summaries for the target skill plus optional 'competitor' skills."""
    summaries = []
    for directory in [Path(skill_dir), *(Path(d) for d in extra_dirs or [])]:
        doc = parse_skill(directory)
        summaries.append(SkillSummary(name=doc.name or directory.name, description=doc.description or ""))
    return summaries


DEFAULT_MAX_TOKENS = 1024
RETRY_MAX_TOKENS = 4096


def _ask_router(client, model: str, skills: list[SkillSummary], user_input: str, max_tokens: int) -> tuple[str, str | None]:
    """One routing question. Returns (reply_text, finish_reason)."""
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_router_prompt(skills, user_input)},
        ],
    )
    choice = completion.choices[0]
    return choice.message.content or "", choice.finish_reason


def run_cases(
    skill_dir: Path,
    cases: list[Case],
    skills: list[SkillSummary],
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> TestReport:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise TesterError("the `openai` package is required for `skilldoctor test`") from exc

    api_key = api_key or os.environ.get("SKILLDOCTOR_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = base_url or os.environ.get("SKILLDOCTOR_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    if not api_key:
        raise TesterError(
            "no API key configured; set SKILLDOCTOR_API_KEY / OPENAI_API_KEY or pass --api-key "
            "(any OpenAI-compatible endpoint works, e.g. DeepSeek, Kimi, local models)"
        )

    target = parse_skill(skill_dir)
    target_name = target.name or Path(skill_dir).name
    client = OpenAI(api_key=api_key, base_url=base_url)

    report = TestReport(skill_name=target_name)
    for case in cases:
        reply, finish_reason = _ask_router(client, model, skills, case.input, max_tokens)
        # Reasoning models (deepseek-r1-style, kimi thinking, ...) spend tokens on
        # hidden reasoning before answering; a truncated budget returns an empty
        # reply (finish_reason="length"), which must not be scored as "no skill".
        if finish_reason == "length" and not reply.strip() and max_tokens < RETRY_MAX_TOKENS:
            reply, _ = _ask_router(client, model, skills, case.input, RETRY_MAX_TOKENS)
        report.results.append(CaseResult(case=case, chosen=parse_decision(reply, skills), target_name=target_name))
    return report
