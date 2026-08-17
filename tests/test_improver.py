from pathlib import Path

import pytest

from skilldoctor.improver import improve_skill, write_description
from skilldoctor.parser import parse_skill
from skilldoctor.router_prompt import SkillSummary
from skilldoctor.tester import Case

FIXTURES = Path(__file__).parent / "fixtures"

SKILL_DIR = FIXTURES / "demo-skill"
SKILLS = [SkillSummary(name="demo-skill", description="旧描述"), SkillSummary(name="other-skill", description="别的")]
CASES = [Case(input="触发我", expect_trigger=True), Case(input="无关请求", expect_trigger=False)]


class _FakeCompletions:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content, finish_reason = self.script.pop(0)
        message = type("M", (), {"content": content})
        choice = type("C", (), {"message": message, "finish_reason": finish_reason})
        return type("R", (), {"choices": [choice]})


def _install_fake_openai(monkeypatch, script):
    client = type("Client", (), {"chat": type("Chat", (), {"completions": _FakeCompletions(script)})})()
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: client)
    monkeypatch.setenv("SKILLDOCTOR_API_KEY", "test-key")
    return client.chat.completions


def test_improve_converges_and_picks_best(monkeypatch):
    fake = _install_fake_openai(monkeypatch, [
        ("NONE", "stop"),                # baseline: trigger case misses
        ("NONE", "stop"),                # baseline: no_trigger case passes
        ('"v2 新描述，嵌入触发我这个说法"', "stop"),  # rewrite proposal
        ("demo-skill", "stop"),          # round 1: trigger case hits
        ("NONE", "stop"),                # round 1: no_trigger still clean
    ])
    result = improve_skill(SKILL_DIR, CASES, SKILLS, model="fake")

    assert len(result.rounds) == 2          # stopped early once solved
    assert result.baseline.report.passed == 1
    assert result.improved and result.solved
    assert result.best.description == "v2 新描述，嵌入触发我这个说法"
    # the rewrite prompt must contain the phrasing that failed
    rewrite_prompt = fake.calls[2]["messages"][0]["content"]
    assert "触发我" in rewrite_prompt


def test_improve_stops_when_model_repeats_itself(monkeypatch):
    current = parse_skill(SKILL_DIR).description  # proposal identical to current -> give up
    _install_fake_openai(monkeypatch, [
        ("NONE", "stop"),
        ("NONE", "stop"),
        (current, "stop"),
    ])
    result = improve_skill(SKILL_DIR, CASES, SKILLS, model="fake")

    assert len(result.rounds) == 1
    assert not result.improved and not result.solved


def test_write_description_preserves_body(tmp_path):
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: old words\n---\n\n# Body stays\n\nKeep me.\n",
        encoding="utf-8",
    )
    write_description(skill, "新的 description 中文也行")

    doc = parse_skill(skill)
    assert doc.description == "新的 description 中文也行"
    assert doc.name == "demo"
    assert "# Body stays" in doc.body and "Keep me." in doc.body
