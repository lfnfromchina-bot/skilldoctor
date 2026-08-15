"""Rich terminal rendering for validate / lint / test results."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table

from .issues import Issue, Level
from .tester import TestReport

console = Console()

# Academic three-line table: top rule, header separator, bottom rule, no verticals.
TABLE_BOX = box.SIMPLE_HEAD

_LEVEL_STYLE = {
    Level.ERROR: "bold red",
    Level.WARNING: "yellow",
    Level.INFO: "cyan",
}


def render_issues(results: dict[str, list[Issue]]) -> int:
    """Print an issue table. Returns process exit code (1 if any error)."""
    has_error = any(i.level == Level.ERROR for issues in results.values() for i in issues)
    total = sum(len(v) for v in results.values())

    if total == 0:
        console.print("[bold green]✓ all checks passed[/]")
        return 0

    table = Table(box=TABLE_BOX, show_lines=False, pad_edge=False)
    table.add_column("skill", style="bold")
    table.add_column("level")
    table.add_column("rule", style="dim")
    table.add_column("message")
    for skill, issues in results.items():
        for issue in issues:
            table.add_row(
                skill,
                f"[{_LEVEL_STYLE[issue.level]}]{issue.level.value}[/]",
                issue.rule,
                issue.message,
            )
    console.print(table)
    console.print(f"\n{total} issue(s) across {len(results)} skill(s)")
    return 1 if has_error else 0


def render_test_report(report: TestReport) -> int:
    table = Table(box=TABLE_BOX, title=f"{report.skill_name} — trigger test report", pad_edge=False)
    table.add_column("input")
    table.add_column("expected")
    table.add_column("router chose")
    table.add_column("result")
    for r in report.results:
        table.add_row(
            r.case.input,
            "trigger" if r.case.expect_trigger else "no_trigger",
            r.chosen or "NONE",
            "[green]✓[/]" if r.passed else "[bold red]✗[/]",
        )
    console.print(table)

    rate = report.trigger_rate
    fpr = report.false_positive_rate
    summary = f"\npassed {report.passed}/{report.total}"
    if rate is not None:
        summary += f"  ·  trigger rate {rate:.0%}"
    if fpr is not None:
        summary += f"  ·  false-positive rate {fpr:.0%}"
    console.print(summary)

    failed_triggers = [r for r in report.results if r.case.expect_trigger and not r.passed]
    if failed_triggers:
        missed = "、".join(f'"{r.case.input}"' for r in failed_triggers)
        console.print(f"\n[yellow]suggestion:[/] these phrasings failed to trigger: {missed}")
        console.print("add them (or their vocabulary) verbatim to the skill description, then re-run.")
    return 0 if report.passed == report.total else 1
