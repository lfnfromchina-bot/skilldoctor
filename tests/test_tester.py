from pathlib import Path

import pytest

from skilldoctor.router_prompt import SkillSummary
from skilldoctor.tester import Case, CaseResult, TestReport, TesterError, load_cases, run_cases

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_cases():
    cases = load_cases(FIXTURES / "demo-skill" / "skilldoctor.cases.yml")
    assert len(cases) == 2
    assert cases[0].expect_trigger is True
    assert cases[1].expect_trigger is False


def test_load_cases_bad_file(tmp_path):
    bad = tmp_path / "cases.yml"
    bad.write_text("nope: []\n", encoding="utf-8")
    with pytest.raises(TesterError):
        load_cases(bad)


def _result(inp: str, expect: bool, chosen: str | None) -> CaseResult:
    return CaseResult(case=Case(input=inp, expect_trigger=expect), chosen=chosen, target_name="demo-skill")


def test_report_metrics():
    report = TestReport(
        skill_name="demo-skill",
        results=[
            _result("a", True, "demo-skill"),
            _result("b", True, None),          # missed trigger
            _result("c", False, None),          # correctly ignored
            _result("d", False, "demo-skill"),  # false positive
        ],
    )
    assert report.passed == 2
    assert report.total == 4
    assert report.trigger_rate == 0.5
    assert report.false_positive_rate == 0.5


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content, finish_reason):
        self.message = _FakeMessage(content)
        self.finish_reason = finish_reason


class _FakeCompletions:
    """Plays back a script of (content, finish_reason) responses."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content, finish_reason = self.script.pop(0)
        return type("Completion", (), {"choices": [_FakeChoice(content, finish_reason)]})


class _FakeClient:
    def __init__(self, script):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(script)})


def _install_fake_openai(monkeypatch, script):
    client = _FakeClient(script)
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: client)
    monkeypatch.setenv("SKILLDOCTOR_API_KEY", "test-key")
    return client


def test_run_cases_retries_reasoning_model_truncation(monkeypatch):
    """A reasoning model that spends its whole budget thinking returns an empty
    reply with finish_reason='length'; we must retry with a larger budget
    instead of scoring it as NONE."""
    client = _install_fake_openai(monkeypatch, [("", "length"), ("demo-skill", "stop")])
    skills = [SkillSummary(name="demo-skill", description="demo")]
    report = run_cases(
        FIXTURES / "demo-skill",
        [Case(input="触发一下", expect_trigger=True)],
        skills,
        model="fake-reasoner",
    )
    assert len(client.chat.completions.calls) == 2
    assert client.chat.completions.calls[1]["max_tokens"] == 4096
    assert report.results[0].chosen == "demo-skill"
    assert report.trigger_rate == 1.0


def test_run_cases_no_retry_on_normal_answer(monkeypatch):
    client = _install_fake_openai(monkeypatch, [("NONE", "stop")])
    skills = [SkillSummary(name="demo-skill", description="demo")]
    report = run_cases(
        FIXTURES / "demo-skill",
        [Case(input="无关请求", expect_trigger=False)],
        skills,
        model="fake-chat",
    )
    assert len(client.chat.completions.calls) == 1
    assert client.chat.completions.calls[0]["max_tokens"] == 1024
    assert report.results[0].chosen is None
