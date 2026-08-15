import pytest

from skillvet.scaffolder import ScaffoldError, new_skill
from skillvet.validator import validate_skill


def test_scaffold_basic(tmp_path):
    target = new_skill(
        name="xhs-writer",
        description="把笔记改写成小红书风格文案",
        phrasings=["改成小红书风格", "写个xhs文案", "帮我写种草笔记"],
        out_dir=tmp_path,
    )
    skill_md = target / "SKILL.md"
    assert skill_md.is_file()
    text = skill_md.read_text(encoding="utf-8")
    assert "name: xhs-writer" in text
    assert '"改成小红书风格"' in text
    # scaffolded skills must pass validation out of the box
    assert not [i for i in validate_skill(target) if i.level.value == "error"]


def test_scaffold_with_scripts(tmp_path):
    target = new_skill("scripted-skill", "demo", ["说法一"], tmp_path, template="with-scripts")
    assert (target / "scripts" / "run.py").is_file()


def test_scaffold_with_references(tmp_path):
    target = new_skill("ref-skill", "demo", ["说法一"], tmp_path, template="with-references")
    assert (target / "references" / "REFERENCE.md").is_file()


def test_rejects_bad_name(tmp_path):
    with pytest.raises(ScaffoldError):
        new_skill("Bad Name", "d", ["x"], tmp_path)


def test_rejects_existing_dir(tmp_path):
    new_skill("dup-skill", "d", ["x"], tmp_path)
    with pytest.raises(ScaffoldError):
        new_skill("dup-skill", "d", ["x"], tmp_path)
