"""Preview the test-report table style (offline demo, no API needed)."""

from skilldoctor.tester import Case, CaseResult, TestReport
from skilldoctor.report import render_test_report

report = TestReport(
    skill_name="xhs-writer",
    results=[
        CaseResult(Case("帮我把这篇笔记改成小红书风格", True), "xhs-writer", "xhs-writer"),
        CaseResult(Case("发个xhs", True), None, "xhs-writer"),
        CaseResult(Case("帮我写公众号推文", False), None, "xhs-writer"),
    ],
)
render_test_report(report)
