from pathlib import Path

from skilldoctor.issues import Level
from skilldoctor.validator import validate_path, validate_skill

FIXTURES = Path(__file__).parent / "fixtures"


def rules(issues):
    return {i.rule for i in issues}


def test_valid_skill_is_clean():
    issues = validate_skill(FIXTURES / "demo-skill")
    assert rules(issues) <= {"desc-no-phrasings"}  # no errors at all
    assert not any(i.level == Level.ERROR for i in issues)


def test_broken_skill_flags():
    issues = validate_skill(FIXTURES / "broken-skill")
    assert {"missing-reference", "unknown-field"} <= rules(issues)


def test_missing_description(tmp_path):
    (tmp_path / "SKILL.md").write_text("---\nname: foo\n---\nbody\n", encoding="utf-8")
    assert "description-required" in rules(validate_skill(tmp_path))


def test_description_too_long(tmp_path):
    (tmp_path / "SKILL.md").write_text(
        f"---\nname: {tmp_path.name}\ndescription: {'x' * 1100}\n---\n", encoding="utf-8"
    )
    assert "description-length" in rules(validate_skill(tmp_path))


def test_name_dir_mismatch(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: other-name\ndescription: d\n---\n", encoding="utf-8")
    assert "name-dir-mismatch" in rules(validate_skill(skill_dir))


def test_validate_path_scans_collection():
    results = validate_path(FIXTURES)
    assert set(results) == {"demo-skill", "broken-skill"}


def test_risky_script_warning(tmp_path):
    skill_dir = tmp_path / "risky-skill"
    (skill_dir / "scripts").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: risky-skill\ndescription: does things with scripts\n---\nrun it\n", encoding="utf-8"
    )
    (skill_dir / "scripts" / "run.sh").write_text("rm -rf /\n", encoding="utf-8")
    assert "risky-script" in rules(validate_skill(skill_dir))
