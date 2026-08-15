from pathlib import Path

from skilldoctor.linter import lint_skill

FIXTURES = Path(__file__).parent / "fixtures"


def rules(issues):
    return {i.rule for i in issues}


def test_good_description_passes_trigger_checks(tmp_path):
    skill = tmp_path / "good-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: good-skill\n"
        "description: >-\n"
        "  把笔记改写成小红书风格文案。使用场景：当用户说 \"改成小红书风格\" 时加载。\n"
        "---\n"
        "## 步骤\n1. 生成\n\n## 防护栏\n- 不要编造用户未提供的事实。\n",
        encoding="utf-8",
    )
    issues = rules(lint_skill(skill))
    assert "desc-no-trigger" not in issues
    assert "desc-too-short" not in issues
    assert "no-guardrails" not in issues


def test_thin_description_is_flagged(tmp_path):
    skill = tmp_path / "thin-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: thin-skill\ndescription: 处理文本\n---\n正文。\n", encoding="utf-8")
    issues = rules(lint_skill(skill))
    assert "desc-too-short" in issues
    assert "desc-no-trigger" in issues
    assert "no-guardrails" in issues


def test_long_body_suggests_splitting(tmp_path):
    skill = tmp_path / "fat-skill"
    skill.mkdir()
    body = "\n".join(f"line {i} 不要编造" for i in range(200))
    (skill / "SKILL.md").write_text(
        f"---\nname: fat-skill\ndescription: 使用场景：当用户说 \"x\" 时加载，这是一个足够长的描述用来测试正文长度规则。\n---\n{body}\n",
        encoding="utf-8",
    )
    assert "body-too-long" in rules(lint_skill(skill))


def test_fixture_demo_skill_lint():
    issues = lint_skill(FIXTURES / "demo-skill")
    assert "desc-no-trigger" not in rules(issues)
