"""Regenerate docs/demo.png — a pixel-aligned terminal-style screenshot of the
`skilldoctor test` report. CJK glyphs are exactly 2 cells wide, so columns stay
aligned no matter what font the README viewer uses.

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
from skilldoctor.tester import Case, CaseResult, TestReport

# ---------------------------------------------------------------- sample data
buf = io.StringIO()
rep.console = Console(file=buf, force_terminal=False, width=80)
report = TestReport(skill_name="xhs-writer")
report.results = [
    CaseResult(Case("帮我把这篇笔记改成小红书风格", True), "xhs-writer", "xhs-writer"),
    CaseResult(Case("发个xhs", True), None, "xhs-writer"),
    CaseResult(Case("帮我写公众号推文", False), None, "xhs-writer"),
]
rep.render_test_report(report)
lines = [ln.rstrip() for ln in buf.getvalue().splitlines()]
while lines and not lines[0]:
    lines.pop(0)
while lines and not lines[-1]:
    lines.pop()

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

def is_wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")

def line_cells(line: str) -> int:
    return sum(2 if is_wide(c) else 1 for c in line)

# ------------------------------------------------------------------ colors
BG = (13, 17, 23)        # GitHub dark #0d1117
FG = (230, 237, 243)
DIM = (125, 133, 144)
GREEN = (63, 185, 80)
RED = (248, 81, 73)
YELLOW = (210, 153, 34)

def line_style(line: str):
    if "trigger test report" in line:
        return "title"
    if line.lstrip().startswith(("input", "─")):
        return "dim"
    if line.startswith("suggestion:"):
        return "warn"
    return "normal"

# ------------------------------------------------------------------- render
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
            adv = font.getlength(ch)
            xoff = x + (slot - adv) / 2
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

out = ROOT / "docs" / "demo.png"
out.parent.mkdir(exist_ok=True)
img.save(out)
print(f"wrote {out}  {img.size[0]}x{img.size[1]}")
