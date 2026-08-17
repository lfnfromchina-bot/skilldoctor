"""Debug: show raw router replies for models that scored 0% trigger rate.

Usage:
  SKILLDOCTOR_API_KEY=... SKILLDOCTOR_BASE_URL=... \
    .venv/bin/python scripts/debug_router_raw.py deepseek-v4-flash kimi-k2.5
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openai import OpenAI
from skilldoctor.router_prompt import SYSTEM_PROMPT, SkillSummary, build_router_prompt, parse_decision

skills = [
    SkillSummary("xhs-writer", "小红书文案撰写。当用户要求写小红书笔记、小红书文案、爆款标题、种草文案、red书、Xiaohongshu 时使用。"),
    SkillSummary("wechat-editor", "微信公众号文章排版与编辑。"),
    SkillSummary("weekly-report-cn", "中文工作周报生成。"),
    SkillSummary("video-script-polisher", "视频脚本润色。"),
    SkillSummary("product-copy-generator", "产品营销文案生成。"),
]

CASE = "帮我把这篇笔记改成小红书风格"

client = OpenAI(
    api_key=os.environ["SKILLDOCTOR_API_KEY"],
    base_url=os.environ.get("SKILLDOCTOR_BASE_URL"),
)

for model in sys.argv[1:]:
    for max_tokens in (20, 200):
        try:
            r = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_router_prompt(skills, CASE)},
                ],
            )
            msg = r.choices[0].message
            content = msg.content or ""
            reasoning = getattr(msg, "reasoning_content", None) or ""
            print(f"=== {model} max_tokens={max_tokens} ===")
            print(f"finish_reason : {r.choices[0].finish_reason}")
            print(f"usage         : {r.usage}")
            print(f"content       : {content!r}")
            if reasoning:
                print(f"reasoning     : {reasoning[:300]!r}...")
            print(f"parse_decision: {parse_decision(content, skills)}")
        except Exception as e:
            print(f"=== {model} max_tokens={max_tokens} === ERROR: {e}")
        print()
