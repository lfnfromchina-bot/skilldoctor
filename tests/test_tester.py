from pathlib import Path

import pytest

from skillvet.tester import Case, CaseResult, TestReport, TesterError, load_cases

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_cases():
    cases = load_cases(FIXTURES / "demo-skill" / "skillvet.cases.yml")
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
