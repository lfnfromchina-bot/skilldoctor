from skillvet.router_prompt import SkillSummary, build_router_prompt, parse_decision

SKILLS = [
    SkillSummary(name="demo-skill", description="把笔记改写成小红书风格文案"),
    SkillSummary(name="weekly-report", description="生成中文工作周报"),
]


def test_prompt_contains_listing_and_input():
    prompt = build_router_prompt(SKILLS, "帮我写种草笔记")
    assert "demo-skill: 把笔记改写成小红书风格文案" in prompt
    assert "weekly-report" in prompt
    assert "帮我写种草笔记" in prompt


def test_parse_exact_name():
    assert parse_decision("demo-skill", SKILLS) == "demo-skill"


def test_parse_none():
    assert parse_decision("NONE", SKILLS) is None
    assert parse_decision("none", SKILLS) is None


def test_parse_chatty_reply():
    assert parse_decision("I would load `demo-skill` here.", SKILLS) == "demo-skill"


def test_parse_unknown_reply():
    assert parse_decision("something-else", SKILLS) is None
