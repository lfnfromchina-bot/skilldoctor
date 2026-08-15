"""Parse a skill directory into a structured SkillDoc.

A skill directory looks like::

    my-skill/
    ├── SKILL.md            # required, exact case
    ├── references/...      # optional, progressive-disclosure docs
    └── scripts/...         # optional, executable helpers
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SKILL_MD = "SKILL.md"

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
# Backtick-quoted references to bundled files, e.g. `references/style.md`
_REFERENCE_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")
_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class SkillParseError(Exception):
    """Raised when SKILL.md is missing or its frontmatter cannot be parsed."""


def is_kebab_case(value: str) -> bool:
    return bool(_KEBAB_RE.match(value))


def find_skill_md(skill_dir: Path) -> Path | None:
    """Return the exact-case SKILL.md path, or None if absent.

    Uses directory listing instead of `Path.is_file()` because macOS and
    Windows filesystems are case-insensitive: `SKILL.md` would happily
    resolve to an on-disk `skill.md`, hiding the casing bug from validation.
    """
    if not skill_dir.is_dir():
        return None
    for child in skill_dir.iterdir():
        if child.is_file() and child.name == SKILL_MD:
            return child
    return None


def find_case_variant(skill_dir: Path) -> Path | None:
    """Return a wrongly-cased variant (e.g. skill.md) if one exists."""
    for child in skill_dir.iterdir():
        if child.is_file() and child.name.lower() == SKILL_MD.lower() and child.name != SKILL_MD:
            return child
    return None


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split raw SKILL.md text into (frontmatter_yaml, body).

    Raises SkillParseError if no frontmatter block is found.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillParseError("SKILL.md must start with a YAML frontmatter block (--- ... ---)")
    return match.group(1), text[match.end():]


@dataclass
class SkillDoc:
    skill_dir: Path
    skill_md: Path
    frontmatter: dict
    body: str

    @property
    def dir_name(self) -> str:
        return self.skill_dir.name

    @property
    def name(self) -> str | None:
        value = self.frontmatter.get("name")
        return str(value) if value is not None else None

    @property
    def description(self) -> str | None:
        value = self.frontmatter.get("description")
        return str(value) if value is not None else None

    @property
    def body_lines(self) -> list[str]:
        return self.body.splitlines()

    @property
    def referenced_files(self) -> list[str]:
        """Files mentioned in backticks under references/, scripts/ or assets/."""
        return _REFERENCE_RE.findall(self.body)


def parse_skill(skill_dir: Path) -> SkillDoc:
    """Parse a skill directory. Raises SkillParseError on structural problems."""
    skill_dir = Path(skill_dir)
    skill_md = find_skill_md(skill_dir)
    if skill_md is None:
        variant = find_case_variant(skill_dir)
        if variant is not None:
            raise SkillParseError(
                f"found {variant.name} but the file must be named exactly {SKILL_MD} "
                f"(uppercase SKILL, lowercase .md)"
            )
        raise SkillParseError(f"{SKILL_MD} not found in {skill_dir}")

    raw = skill_md.read_text(encoding="utf-8")
    fm_text, body = split_frontmatter(raw)
    try:
        frontmatter = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise SkillParseError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(frontmatter, dict):
        raise SkillParseError("frontmatter must be a YAML mapping (key: value pairs)")
    return SkillDoc(skill_dir=skill_dir, skill_md=skill_md, frontmatter=frontmatter, body=body)
