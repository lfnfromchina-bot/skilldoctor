from pathlib import Path

import pytest

from skilldoctor.parser import SkillParseError, parse_skill

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_valid_skill():
    doc = parse_skill(FIXTURES / "demo-skill")
    assert doc.name == "demo-skill"
    assert "小红书" in doc.description
    assert len(doc.body_lines) > 0


def test_parse_missing_skill_md(tmp_path):
    with pytest.raises(SkillParseError, match="SKILL.md not found"):
        parse_skill(tmp_path)


def test_parse_wrong_case_gives_hint(tmp_path):
    (tmp_path / "skill.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    with pytest.raises(SkillParseError, match="must be named exactly"):
        parse_skill(tmp_path)


def test_parse_bad_yaml(tmp_path):
    (tmp_path / "SKILL.md").write_text("---\n: bad: [\n---\nbody\n", encoding="utf-8")
    with pytest.raises(SkillParseError, match="not valid YAML"):
        parse_skill(tmp_path)


def test_parse_missing_frontmatter(tmp_path):
    (tmp_path / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    with pytest.raises(SkillParseError, match="frontmatter"):
        parse_skill(tmp_path)
