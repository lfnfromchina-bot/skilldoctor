"""Scaffold new skill directories from templates.

Placeholders in templates use the form {{NAME}}, {{DESCRIPTION}},
{{TRIGGERS}} (a bullet list of quoted phrasings), {{TRIGGER_LIST}}
(comma-separated quoted phrasings for the description line).
"""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

from .parser import is_kebab_case

TEMPLATES = ("basic", "with-scripts", "with-references")


class ScaffoldError(Exception):
    pass


def _render(text: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def build_context(name: str, description: str, phrasings: list[str]) -> dict[str, str]:
    quoted = [f'"{p.strip()}"' for p in phrasings if p.strip()]
    return {
        "NAME": name,
        "DESCRIPTION": description.strip(),
        "TRIGGER_LIST": "、".join(quoted),
        "TRIGGERS": "\n".join(f"- {q}" for q in quoted),
    }


def new_skill(
    name: str,
    description: str,
    phrasings: list[str],
    out_dir: Path,
    template: str = "basic",
) -> Path:
    """Create a new skill directory. Returns the created path."""
    if not is_kebab_case(name):
        raise ScaffoldError(f"skill name must be kebab-case, got `{name}`")
    if template not in TEMPLATES:
        raise ScaffoldError(f"unknown template `{template}`, choose from: {', '.join(TEMPLATES)}")

    target = Path(out_dir) / name
    if target.exists():
        raise ScaffoldError(f"{target} already exists")

    context = build_context(name, description, phrasings)
    template_root = resources.files("skilldoctor") / "templates" / template

    with resources.as_file(template_root) as template_path:
        for src in sorted(Path(template_path).rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(template_path)
            dest_name = rel.name[: -len(".tmpl")] if rel.name.endswith(".tmpl") else rel.name
            dest = target / rel.parent / dest_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.suffix == ".tmpl":
                dest.write_text(_render(src.read_text(encoding="utf-8"), context), encoding="utf-8")
            else:
                shutil.copyfile(src, dest)
    return target
