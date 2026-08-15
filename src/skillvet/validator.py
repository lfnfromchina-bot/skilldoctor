"""Spec validation for agent skills.

Checks a skill directory against the SKILL.md open standard and the
Claude Code frontmatter contract. Every rule lives in this module so the
spec table stays easy to update as the standard evolves.
"""

from __future__ import annotations

import re
from pathlib import Path

from .issues import Issue, Level
from .parser import SkillDoc, SkillParseError, is_kebab_case, parse_skill

NAME_MAX = 64
DESCRIPTION_MAX = 1024
# description + when_to_use are truncated together in the skill listing
LISTING_MAX = 1536

KNOWN_FIELDS = {
    "name",
    "description",
    "when_to_use",
    "argument-hint",
    "arguments",
    "disable-model-invocation",
    "user-invocable",
    "allowed-tools",
    "disallowed-tools",
    "model",
    "effort",
    "context",
    "agent",
    "hooks",
    "paths",
    "shell",
    "version",
    "author",
    "license",
    "trigger_keywords",
}

_DANGER_PATTERNS = [
    (re.compile(r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r"), "recursive force-delete"),
    (re.compile(r"curl\b[^|]*\|\s*(sudo\s+)?(ba)?sh"), "curl-pipe-to-shell"),
    (re.compile(r"\bos\.system\("), "os.system call"),
    (re.compile(r"\bsubprocess\b.*shell\s*=\s*True"), "subprocess with shell=True"),
]


def _check_name(doc: SkillDoc) -> list[Issue]:
    issues: list[Issue] = []
    name = doc.name
    if name is None:
        issues.append(Issue(Level.ERROR, "name-required", "frontmatter is missing required field `name`"))
        return issues
    if len(name) > NAME_MAX:
        issues.append(Issue(Level.ERROR, "name-length", f"name is {len(name)} chars, max is {NAME_MAX}"))
    if not is_kebab_case(name):
        issues.append(Issue(Level.WARNING, "name-kebab", f"name `{name}` should be kebab-case (e.g. my-skill)"))
    if name != doc.dir_name:
        issues.append(
            Issue(
                Level.WARNING,
                "name-dir-mismatch",
                f"name `{name}` does not match directory `{doc.dir_name}`; "
                "slash-command invocation uses the directory name, keep them identical",
            )
        )
    return issues


def _check_description(doc: SkillDoc) -> list[Issue]:
    issues: list[Issue] = []
    desc = doc.description
    if desc is None or not desc.strip():
        return [Issue(Level.ERROR, "description-required", "frontmatter is missing required field `description`")]
    length = len(desc)
    if length > DESCRIPTION_MAX:
        issues.append(
            Issue(
                Level.ERROR,
                "description-length",
                f"description is {length} chars, max is {DESCRIPTION_MAX}; "
                "anything beyond the limit is silently truncated in the skill listing",
            )
        )
    when_to_use = doc.frontmatter.get("when_to_use")
    if when_to_use:
        total = length + len(str(when_to_use))
        if total > LISTING_MAX:
            issues.append(
                Issue(
                    Level.WARNING,
                    "listing-truncation",
                    f"description + when_to_use = {total} chars, listings truncate at {LISTING_MAX}",
                )
            )
    return issues


def _check_fields(doc: SkillDoc) -> list[Issue]:
    return [
        Issue(
            Level.WARNING,
            "unknown-field",
            f"unknown frontmatter field `{field}` (known: name, description, when_to_use, allowed-tools, ...)",
        )
        for field in doc.frontmatter
        if field not in KNOWN_FIELDS
    ]


def _check_references(doc: SkillDoc) -> list[Issue]:
    issues = []
    for ref in doc.referenced_files:
        if not (doc.skill_dir / ref).is_file():
            issues.append(
                Issue(
                    Level.ERROR,
                    "missing-reference",
                    f"body references `{ref}` but the file does not exist in the skill directory",
                )
            )
    return issues


def _check_script_safety(doc: SkillDoc) -> list[Issue]:
    issues = []
    scripts_dir = doc.skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return issues
    for script in sorted(scripts_dir.rglob("*")):
        if not script.is_file():
            continue
        try:
            text = script.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern, label in _DANGER_PATTERNS:
            if pattern.search(text):
                issues.append(
                    Issue(Level.WARNING, "risky-script", f"scripts/{script.name} contains {label}; reviewers and users will flag this")
                )
    return issues


def validate_skill(skill_dir: Path) -> list[Issue]:
    """Validate one skill directory. Returns a list of issues (empty = clean)."""
    skill_dir = Path(skill_dir)
    try:
        doc = parse_skill(skill_dir)
    except SkillParseError as exc:
        return [Issue(Level.ERROR, "parse", str(exc))]

    issues: list[Issue] = []
    issues += _check_name(doc)
    issues += _check_description(doc)
    issues += _check_fields(doc)
    issues += _check_references(doc)
    issues += _check_script_safety(doc)
    return issues


def iter_skill_dirs(root: Path) -> list[Path]:
    """If root itself is a skill, return [root]; otherwise scan immediate subdirs."""
    root = Path(root)
    if (root / "SKILL.md").is_file():
        return [root]
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))


def validate_path(root: Path) -> dict[str, list[Issue]]:
    """Validate one skill or every skill under a collection directory."""
    results: dict[str, list[Issue]] = {}
    for skill_dir in iter_skill_dirs(root):
        issues = validate_skill(skill_dir)
        for issue in issues:
            issue.skill = skill_dir.name
        results[skill_dir.name] = issues
    return results
