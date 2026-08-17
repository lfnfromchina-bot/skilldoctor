"""Regenerate docs/demo.png and docs/improve.png — pixel-aligned terminal-style
screenshots of skilldoctor reports. CJK glyphs are exactly 2 cells wide, so
columns stay aligned no matter what font the README viewer uses.

Usage:  .venv/bin/python scripts/make_demo_image.py
"""
import io
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont
from rich.console import Console

from skilldoctor import report as rep
from skilldoctor.improver import ImproveResult, Round
from skilldoctor.tester import Case, CaseResult, TestReport

TARGET = "xhs-writer"
CASES = [  # the 10 real cases from examples/xhs-writer/skilldoctor.cases.yml
    ("帮我把这篇笔记改成小红书风格", True),
    ("给我写个小红书爆款标题", True),
    ("发个xhs，主题是周末露营", True),
    ("red书文案怎么写", True),
    ("rewrite this post for Xiaohongshu", True),
    ("帮我把这个产品介绍改成种草文案", True),
    ("帮我写一篇微信公众号推文", False),
    ("帮我把这篇文章排版成公众号格式", False),
    ("帮我写一份工作周报", False),
    ("这个视频脚本帮我润色一下", False),
]

DESC_NAIVE = "小红书文案改写工具。"
DESC_IMPROVED = (
    "小红书文案改写工具，专为需要撰写和改写文案的用户设计。无论是"
    "“red书文案怎么写”，还是“帮我把这个产品介绍改成种草文案”，"
    "都能轻松满足您的需求，帮助您创作出吸引人的内容。"
)


def _results(chosen_map: dict[str, str | None]) -> list[CaseResult]:
    return [
        CaseResult(Case(inp, expect), chosen_map.get(inp), TARGET) for inp, expect in CASES
    ]


def capture_test_report() -> str:
    buf = io.StringIO()
    rep.console = Console(file=buf, force_terminal=False, width=80)
    report = TestReport(skill_name=TARGET)
    report.results = [
        CaseResult(Case("帮我把这篇笔记改成小红书风格", True), TARGET, TARGET),
        CaseResult(Case("发个xhs", True), None, TARGET),
        CaseResult(Case("帮我写公众号推文", False), None, TARGET),
    ]
    rep.render_test_report(report)
    return buf.getvalue()


def capture_improve_report() -> str:
    """The real v0.2.0 demo run: gpt-4o-mini, xhs-writer-naive, 67% -> 100%."""
    buf = io.StringIO()
    rep.console = Console(file=buf, force_terminal=False, width=100)
    baseline = TestReport(skill_name=TARGET)
    baseline.results = _results({
        "red书文案怎么写": None,
        "帮我把这个产品介绍改成种草文案": "product-copy-generator",
        "帮我写一篇微信公众号推文": "wechat-editor",
        "帮我把这篇文章排版成公众号格式": "wechat-editor",
        "帮我写一份工作周报": "weekly-report-cn",
        "这个视频脚本帮我润色一下": "video-script-polisher",
        **{inp: TARGET for inp, expect in CASES if expect and inp not in (
            "red书文案怎么写", "帮我把这个产品介绍改成种草文案")},
    })
    solved = TestReport(skill_name=TARGET)
    solved.results = _results({
        **{inp: TARGET for inp, expect in CASES if expect},
        "帮我写一篇微信公众号推文": "wechat-editor",
        "帮我把这篇文章排版成公众号格式": "wechat-editor",
        "帮我写一份工作周报": "weekly-report-cn",
        "这个视频脚本帮我润色一下": "video-script-polisher",
    })
    result = ImproveResult(skill_name=TARGET, rounds=[
        Round(DESC_NAIVE, baseline),
        Round(DESC_IMPROVED, solved),
    ])
    code = rep.render_improve_report(result)
    assert code == 0
    return buf.getvalue()


# ------------------------------------------------------------------- fonts
import matplotlib  # bundled DejaVu Sans Mono

ASCII_TTF = Path(matplotlib.__file__).parent / "mpl-data" / "fonts" / "ttf" / "DejaVuSansMono.ttf"
CJK_TTF_CANDIDATES = [
    Path(sys.executable).parent.parent / "fonts" / "NotoSansSC-Regular.ttf",
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/STHeiti Medium.ttc"),
]
CJK_TTF = next(p for p in CJK_TTF_CANDIDATES if p.is_file())

SCALE = 2
SIZE = 15 * SCALE
ascii_font = ImageFont.truetype(str(ASCII_TTF), SIZE)
ascii_bold = ImageFont.truetype(str(ASCII_TTF).replace(".ttf", "-Bold.ttf"), SIZE)
cjk_font = ImageFont.truetype(str(CJK_TTF), SIZE)
cjk_bold = ImageFont.truetype(str(CJK_TTF).replace("Regular", "Bold"), SIZE) if "Regular" in str(CJK_TTF) else cjk_font

CELL_W = ascii_font.getlength("M")          # one ASCII cell
LINE_H = int(SIZE * 1.5)
PAD = 14 * SCALE

BG = (13, 17, 23)        # GitHub dark #0d1117
FG = (230, 237, 243)
DIM = (125, 133, 144)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)


def is_wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def line_cells(line: str) -> int:
    return sum(2 if is_wide(c) else 1 for c in line)


def line_style(line: str):
    if "report" in line and "—" in line:
        return "title"
    stripped = line.lstrip()
    if stripped.startswith(("input", "round", "─")):
        return "dim"
    if stripped.startswith("suggestion:"):
        return "warn"
    return "normal"


def render(text: str, out: Path) -> None:
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    width = int(max(line_cells(ln) for ln in lines) * CELL_W) + 2 * PAD
    height = len(lines) * LINE_H + 2 * PAD
    img = Image.new("RGB", (width + SCALE * 4, height + SCALE * 4), (1, 4, 9))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([SCALE * 2, SCALE * 2, width + SCALE * 2, height + SCALE * 2],
                           radius=10 * SCALE, fill=BG)

    y = SCALE * 2 + PAD
    for ln in lines:
        style = line_style(ln)
        x = SCALE * 2 + PAD
        for ch in ln:
            if is_wide(ch):
                font = cjk_bold if style == "title" else cjk_font
                slot = 2 * CELL_W
                xoff = x + (slot - font.getlength(ch)) / 2
                step = slot
            else:
                font = ascii_bold if style == "title" else ascii_font
                xoff, step = x, CELL_W
            color = FG
            if style == "dim":
                color = DIM
            elif style == "warn":
                color = YELLOW
            if ch == "✓":
                color = GREEN
            elif ch == "✗":
                color = RED
            if ch != " ":
                draw.text((xoff, y), ch, font=font, fill=color)
            x += step
        y += LINE_H

    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(f"wrote {out}  {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    render(capture_test_report(), ROOT / "docs" / "demo.png")
    render(capture_improve_report(), ROOT / "docs" / "improve.png")
