"""skilldoctor command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .linter import lint_path
from .scaffolder import TEMPLATES, ScaffoldError, new_skill
from .tester import collect_summaries, find_cases_file, load_cases, run_cases
from .validator import validate_path


def _force_utf8_stdio() -> None:
    """Reports contain CJK text; a C/POSIX locale turns redirected stdout into
    ASCII and crashes rich mid-table. UTF-8 output is always what we want."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # pragma: no cover - exotic stream types
                pass


_force_utf8_stdio()

app = typer.Typer(
    name="skilldoctor",
    help="Scaffold, validate, lint and test agent skills (SKILL.md).",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"skilldoctor {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", callback=_version_callback, is_eager=True),
) -> None:
    """Scaffold, validate, lint and test agent skills."""


@app.command()
def new(
    name: str = typer.Argument(..., help="skill name, kebab-case"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="one-sentence purpose"),
    phrasings: Optional[list[str]] = typer.Option(
        None, "--say", "-s", help="a user phrasing that should trigger the skill (repeatable)"
    ),
    template: str = typer.Option("basic", "--template", "-t", help=f"one of: {', '.join(TEMPLATES)}"),
    out: Path = typer.Option(Path("."), "--out", "-o", help="parent directory"),
) -> None:
    """Scaffold a new skill directory interactively or from flags."""
    import questionary

    from .report import console

    if description is None:
        description = questionary.text("这个 skill 是干什么的？（一句话）").ask() or ""
    if not phrasings:
        raw = questionary.text("用户会怎么表达这个需求？输入 3 种说法，用 | 分隔").ask() or ""
        phrasings = [p.strip() for p in raw.split("|") if p.strip()]
    if not description.strip() or len(phrasings) < 1:
        console.print("[bold red]description and at least one phrasing are required[/]")
        raise typer.Exit(2)

    try:
        target = new_skill(name, description, phrasings, out, template)
    except ScaffoldError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(2) from exc
    console.print(f"[bold green]✓ created {target}[/]")
    console.print("next: edit SKILL.md, then run [bold]skilldoctor validate[/] and [bold]skilldoctor test[/]")


@app.command()
def validate(
    path: Path = typer.Argument(Path("."), help="a skill directory or a collection of skills"),
    json_out: bool = typer.Option(False, "--json", help="machine-readable output for CI"),
) -> None:
    """Check skills against the SKILL.md spec (offline, no LLM needed)."""
    results = validate_path(path)
    if json_out:
        typer.echo(json.dumps({k: [i.as_dict() for i in v] for k, v in results.items()}, ensure_ascii=False, indent=2))
        raise typer.Exit(1 if any(i.level.value == "error" for v in results.values() for i in v) else 0)
    from .report import render_issues

    raise typer.Exit(render_issues(results))


@app.command()
def lint(
    path: Path = typer.Argument(Path("."), help="a skill directory or a collection of skills"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Best-practice checks: trigger wording, progressive disclosure, guardrails."""
    results = lint_path(path)
    if json_out:
        typer.echo(json.dumps({k: [i.as_dict() for i in v] for k, v in results.items()}, ensure_ascii=False, indent=2))
        return
    from .report import render_issues

    render_issues(results)


@app.command()
def test(
    path: Path = typer.Argument(..., help="the skill directory under test"),
    cases: Optional[Path] = typer.Option(None, "--cases", "-c", help="cases YAML (default: skilldoctor.cases.yml in the skill dir)"),
    with_skills: Optional[list[Path]] = typer.Option(
        None, "--with", "-w", help="other skill dirs to compete against in the simulated listing (repeatable)"
    ),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="any OpenAI-compatible chat model"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="or set SKILLDOCTOR_API_KEY / OPENAI_API_KEY"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="or set SKILLDOCTOR_BASE_URL / OPENAI_BASE_URL"),
    max_tokens: int = typer.Option(
        1024, "--max-tokens", help="router reply budget; reasoning models need headroom (auto-retries at 4096 on truncation)"
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Measure trigger rate: simulate the agent's skill-routing decision with an LLM."""
    from .report import console, render_test_report

    try:
        cases_file = cases or find_cases_file(path)
        case_list = load_cases(cases_file)
        skills = collect_summaries(path, with_skills)
        report = run_cases(path, case_list, skills, model=model, api_key=api_key, base_url=base_url, max_tokens=max_tokens)
    except Exception as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(2) from exc

    if json_out:
        typer.echo(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        raise typer.Exit(0 if report.passed == report.total else 1)
    raise typer.Exit(render_test_report(report))
