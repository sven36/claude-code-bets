# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp_template_output_preview" / "slide2_claude_what_is_fit.png"
W, H = 1600, 900

BG = "#F8F2E8"
TEXT = "#243536"
MUTED = "#69787A"
ORANGE = "#FF7A2F"
ORANGE_SOFT = "#FFE3D2"
GREEN = "#2F8F71"
GREEN_SOFT = "#E1F3EC"
BLUE = "#2D6CDF"
BLUE_SOFT = "#E7EEFF"
PANEL = "#FFF8EE"
PANEL2 = "#FFF2E3"
LINE = "#FF7A2F"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_TITLE = font(46, True)
F_SUB = font(22)
F_KICKER = font(19, True)
F_BOX = font(24, True)
F_BOX_SMALL = font(20, True)
F_BODY = font(20)
F_TINY = font(16)


def text_size(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), s, font=f)
    return box[2] - box[0], box[3] - box[1]


def centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    f: ImageFont.ImageFont,
    fill: str = TEXT,
    line_gap: int = 5,
) -> None:
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    sizes = [text_size(draw, line, f) for line in lines]
    total_h = sum(h for _, h in sizes) + line_gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, (tw, th) in zip(lines, sizes):
        draw.text((x1 + (x2 - x1 - tw) / 2, y), line, font=f, fill=fill)
        y += th + line_gap


def round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str = LINE,
    width: int = 3,
    radius: int = 8,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = LINE,
    width: int = 4,
    head: int = 14,
) -> None:
    draw.line([start, end], fill=color, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    pts = [
        end,
        (
            int(end[0] - head * math.cos(ang - math.pi / 6)),
            int(end[1] - head * math.sin(ang - math.pi / 6)),
        ),
        (
            int(end[0] - head * math.cos(ang + math.pi / 6)),
            int(end[1] - head * math.sin(ang + math.pi / 6)),
        ),
    ]
    draw.polygon(pts, fill=color)


def poly_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    color: str = LINE,
    width: int = 4,
) -> None:
    draw.line(points, fill=color, width=width, joint="curve")
    arrow(draw, points[-2], points[-1], color=color, width=0, head=14)


def shadow(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int = 10) -> None:
    x1, y1, x2, y2 = box
    draw.rounded_rectangle((x1 + 4, y1 + 5, x2 + 4, y2 + 5), radius=radius, fill="#E8D9C8")


def draw_pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, stroke: str) -> None:
    pad_x, pad_y = 18, 8
    tw, th = text_size(draw, text, F_TINY)
    box = (x, y, x + tw + pad_x * 2, y + th + pad_y * 2)
    draw.rounded_rectangle(box, radius=18, fill=fill, outline=stroke, width=2)
    draw.text((x + pad_x, y + pad_y - 1), text, font=F_TINY, fill=TEXT)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((82, 52), "02", font=F_KICKER, fill=ORANGE)
    draw.text((124, 52), "CLAUDE 是什么", font=F_KICKER, fill=MUTED)
    draw.text((82, 92), "Claude Code = 终端里的工程代理系统", font=F_TITLE, fill=TEXT)
    draw.text(
        (84, 154),
        "不是聊天壳，而是把模型、工具、上下文、权限和本地执行串起来的 Agentic Coding Runtime。",
        font=F_SUB,
        fill=MUTED,
    )
    draw.line((84, 200, 395, 200), fill=ORANGE, width=5)

    # Definition cards
    cards = [
        (88, 235, 392, 350, "Terminal-native", "运行在本地终端\n直接面对项目目录", BLUE_SOFT, BLUE),
        (420, 235, 724, 350, "Agentic Loop", "模型会决策工具链\n不是一问一答", GREEN_SOFT, GREEN),
        (88, 374, 392, 489, "Tool as Capability", "读写文件 / Shell / 搜索\nMCP / LSP / 子 Agent", ORANGE_SOFT, ORANGE),
        (420, 374, 724, 489, "Permission Boundary", "能执行真实动作\n所以必须可控", "#F3EAFE", "#8B5CF6"),
    ]
    for x1, y1, x2, y2, title, body, fill, stroke in cards:
        shadow(draw, (x1, y1, x2, y2))
        round_rect(draw, (x1, y1, x2, y2), fill, stroke, 3, 12)
        draw.text((x1 + 22, y1 + 16), title, font=F_BOX_SMALL, fill=TEXT)
        draw.multiline_text((x1 + 22, y1 + 52), body, font=F_BODY, fill=MUTED, spacing=6)

    # Main diagram panel
    panel = (782, 226, 1510, 765)
    shadow(draw, panel, 14)
    round_rect(draw, panel, PANEL, ORANGE, 3, 14)
    draw.text((812, 252), "源码视角：一次会话背后的骨架", font=F_BOX_SMALL, fill=TEXT)
    draw.text((812, 284), "用户输入最终进入 QueryEngine，再被拆成上下文、工具、状态与安全边界。", font=F_TINY, fill=MUTED)

    # Diagram nodes
    user = (1105, 328, 1210, 380)
    session = (1040, 425, 1275, 487)
    qe = (1062, 535, 1250, 596)
    agent_loop = (1062, 666, 1250, 728)
    modules = [
        (822, 628, 1010, 686, "Tool\n工具系统"),
        (822, 708, 1010, 766, "Context\n上下文系统"),
        (1302, 628, 1482, 686, "AppState\n状态系统"),
        (1302, 708, 1482, 766, "Plan Mode\n权限边界"),
    ]
    history = (1320, 500, 1482, 558)

    for box, label, fill in [
        (user, "用户", "#FFFDF8"),
        (session, "Claude Code 会话", "#FFFDF8"),
        (qe, "QueryEngine", "#FFFDF8"),
        (agent_loop, "query.ts\nAgentic Loop", "#FFFDF8"),
        (history, "系统提示词\n消息历史", "#FFFDF8"),
    ]:
        round_rect(draw, box, fill, ORANGE, 3, 7)
        centered_text(draw, box, label, F_BOX_SMALL if "\n" in label else F_BOX)

    arrow(draw, ((user[0] + user[2]) // 2, user[3]), ((session[0] + session[2]) // 2, session[1]))
    arrow(draw, ((session[0] + session[2]) // 2, session[3]), ((qe[0] + qe[2]) // 2, qe[1]))
    arrow(draw, ((qe[0] + qe[2]) // 2, qe[3]), ((agent_loop[0] + agent_loop[2]) // 2, agent_loop[1]))
    poly_arrow(draw, [(1250, 564), (1320, 530)])

    for x1, y1, x2, y2, label in modules:
        box = (x1, y1, x2, y2)
        round_rect(draw, box, "#FFFDF8", ORANGE, 3, 7)
        centered_text(draw, box, label, F_BOX_SMALL)

    # Connections from query engine to modules
    poly_arrow(draw, [(1062, 566), (1008, 628)])
    poly_arrow(draw, [(1088, 596), (1010, 712)])
    poly_arrow(draw, [(1250, 566), (1302, 628)])
    poly_arrow(draw, [(1230, 596), (1302, 712)])

    # Tool detail row
    tool_details = [
        (814, 802, "文件 / Shell / 搜索"),
        (1034, 802, "MCP / LSP"),
        (1210, 802, "Agent / Task"),
    ]
    for x, y, label in tool_details:
        draw_pill(draw, x, y, label, "#FFFDF8", ORANGE)

    # Bottom summary
    summary = (88, 535, 724, 765)
    shadow(draw, summary, 14)
    round_rect(draw, summary, PANEL2, ORANGE, 3, 14)
    draw.text((122, 552), "一句话给听众", font=F_BOX, fill=TEXT)
    draw.multiline_text(
        (122, 604),
        "Claude Code 的核心不是“会聊天”，\n而是“会在你的工程目录里行动”：\n\n读代码 -> 调工具 -> 执行动作 -> 看结果 -> 再决策。",
        font=font(25, True),
        fill=TEXT,
        spacing=11,
    )

    draw.text((1130, 836), "Source view: CLI / QueryEngine / query.ts / Tool.ts", font=F_TINY, fill="#9A8D7E")

    img.save(OUT, quality=96)
    print(OUT)
    print(f"{W}x{H}")


if __name__ == "__main__":
    main()
