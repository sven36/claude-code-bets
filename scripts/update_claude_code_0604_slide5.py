from __future__ import annotations

import copy
import shutil
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("a", NS_A)
ET.register_namespace("r", NS_R)
ET.register_namespace("p", NS_P)

SLIDE_W, SLIDE_H = 12192000, 6858000
W_PX, H_PX = 1600, 900

COLORS = {
    "text": "0E2B35",
    "muted": "607680",
    "orange": "FF7A2F",
    "panel": "FFF8EE",
    "node": "FFFDF8",
    "node_soft": "FFF4E8",
    "green_soft": "F1FAF5",
    "blue_soft": "EEF4FF",
    "shadow": "E8D9C8",
    "source": "9A8D7E",
}


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def px(v: float, axis: str = "x") -> int:
    return int(round(v / (W_PX if axis == "x" else H_PX) * (SLIDE_W if axis == "x" else SLIDE_H)))


def box(x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
    return px(x1), px(y1, "y"), px(x2 - x1), px(y2 - y1, "y")


def solid(color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class Builder:
    def __init__(self, start_id: int = 100):
        self.next_id = start_id
        self.items: list[str] = []

    def nid(self) -> int:
        self.next_id += 1
        return self.next_id

    def add(self, xml: str) -> None:
        self.items.append(xml)


def run(text: str, size: int, color: str, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="zh-CN" sz="{size * 100}"{b}>{solid(color)}'
        '<a:latin typeface="Microsoft YaHei"/>'
        '<a:ea typeface="Microsoft YaHei"/>'
        '<a:cs typeface="Microsoft YaHei"/>'
        f'</a:rPr><a:t>{esc(text)}</a:t></a:r>'
    )


def paras(lines: list[str], size: int, color: str, bold: bool, align: str = "l", gap: int = 250) -> str:
    out = []
    for line in lines:
        out.append(
            f'<a:p><a:pPr algn="{align}"><a:spcAft><a:spcPts val="{gap}"/></a:spcAft></a:pPr>'
            f"{run(line, size, color, bold)}</a:p>"
        )
    return "".join(out)


def sp(
    b: Builder,
    x: int,
    y: int,
    w: int,
    h: int,
    lines: list[str] | None = None,
    *,
    fill: str | None = None,
    line: str | None = None,
    line_w: int = 19050,
    radius: bool = False,
    diamond: bool = False,
    font_size: int = 15,
    color: str = COLORS["text"],
    bold: bool = False,
    align: str = "l",
    margin: int = 65000,
    name: str = "editable slide5",
) -> str:
    sid = b.nid()
    geom = "diamond" if diamond else ("roundRect" if radius else "rect")
    fill_xml = solid(fill) if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="{line_w}">{solid(line)}</a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    tx = ""
    if lines is not None:
        tx = (
            f'<p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="{margin}" tIns="{margin}" rIns="{margin}" bIns="{margin}">'
            '<a:normAutofit fontScale="90000" lnSpcReduction="20000"/></a:bodyPr>'
            f'<a:lstStyle/>{paras(lines, font_size, color, bold, align)}</p:txBody>'
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
        <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
        {fill_xml}{line_xml}
      </p:spPr>
      {tx}
    </p:sp>"""


def text(b: Builder, x1: float, y1: float, x2: float, y2: float, lines: list[str], size: int, color: str, bold: bool = False, align: str = "l") -> None:
    b.add(sp(b, *box(x1, y1, x2, y2), lines, font_size=size, color=color, bold=bold, align=align, margin=20000, name="editable slide5 text"))


def node(b: Builder, x1: float, y1: float, x2: float, y2: float, lines: list[str], size: int = 14, fill: str = "FFFDF8", bold: bool = True) -> None:
    b.add(sp(b, *box(x1, y1, x2, y2), lines, fill=fill, line=COLORS["orange"], line_w=19050, radius=True, font_size=size, color=COLORS["text"], bold=bold, align="ctr", margin=45000, name="editable slide5 node"))


def decision(b: Builder, cx: float, cy: float, w: float, h: float, lines: list[str]) -> None:
    b.add(sp(b, *box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), lines, fill="FFFDF8", line=COLORS["orange"], line_w=19050, diamond=True, font_size=12, color=COLORS["text"], bold=True, align="ctr", margin=45000, name="editable slide5 decision"))


def arrow(b: Builder, x1: float, y1: float, x2: float, y2: float, *, color: str = COLORS["orange"], head: bool = True) -> None:
    sid = b.nid()
    ox, oy = px(min(x1, x2)), px(min(y1, y2), "y")
    ex, ey = max(1, px(abs(x2 - x1))), max(1, px(abs(y2 - y1), "y"))
    flip_h = ' flipH="1"' if x2 < x1 else ""
    flip_v = ' flipV="1"' if y2 < y1 else ""
    head_xml = '<a:headEnd type="triangle"/>' if head else ""
    b.add(
        f"""
        <p:cxnSp>
          <p:nvCxnSpPr><p:cNvPr id="{sid}" name="editable slide5 arrow"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
          <p:spPr>
            <a:xfrm{flip_h}{flip_v}><a:off x="{ox}" y="{oy}"/><a:ext cx="{ex}" cy="{ey}"/></a:xfrm>
            <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
            <a:ln w="19050">{solid(color)}{head_xml}</a:ln>
          </p:spPr>
        </p:cxnSp>"""
    )


def build_slide5() -> list[str]:
    b = Builder()
    text(b, 84, 52, 980, 94, ["QueryEngine：Claude Code 的任务主循环"], 26, COLORS["text"], True)
    text(b, 84, 119, 1300, 165, ["如果只能选一个文件代表 Claude Code 的灵魂，大概率就是 QueryEngine.ts。"], 15, COLORS["muted"])
    b.add(sp(b, *box(84, 185, 420, 190), fill=COLORS["orange"], name="editable slide5 accent"))

    b.add(sp(b, *box(52, 216, 1550, 790), fill=COLORS["shadow"], radius=True, name="editable slide5 shadow"))
    b.add(sp(b, *box(48, 210, 1546, 782), fill=COLORS["panel"], line=COLORS["orange"], line_w=22860, radius=True, name="editable slide5 panel"))

    # Left explanation.
    b.add(sp(b, *box(96, 258, 545, 735), fill="FFFDF8", line=COLORS["orange"], line_w=15240, radius=True, name="editable slide5 explainer"))
    text(b, 126, 286, 515, 338, ["QueryEngine.ts", "不是局部能力，而是任务生命周期中枢"], 19, COLORS["text"], True)
    text(b, 126, 365, 510, 398, ["它负责把一次用户请求推进成完整任务："], 13, COLORS["muted"])
    # Use separate text boxes for bullet-like rows to keep editing easy.
    rows = [
        "接收用户输入",
        "组装上下文",
        "驱动模型调用",
        "处理中间工具执行",
        "维护会话状态",
        "把任务一直推进到结束",
    ]
    y = 425
    for row in rows:
        b.add(sp(b, *box(130, y, 500, y + 43), [row], fill=COLORS["blue_soft"], line=None, radius=True, font_size=13, color=COLORS["text"], bold=True, align="ctr", margin=30000, name="editable slide5 bullet"))
        y += 52
    text(b, 126, 703, 510, 734, ["这就是典型的 Agent 主循环。"], 14, COLORS["orange"], True)

    # Right flowchart.
    x0 = 900
    node(b, x0 - 135, 254, x0 + 135, 306, ["submitMessage()", "接收用户输入"], 13)
    arrow(b, x0, 306, x0, 348)
    node(b, x0 - 112, 348, x0 + 112, 400, ["准备配置与上下文"], 13, fill=COLORS["node_soft"])
    arrow(b, x0, 400, x0, 442)
    node(b, x0 - 135, 442, x0 + 135, 494, ["构造系统提示与消息历史"], 13)
    arrow(b, x0, 494, x0, 536)
    node(b, x0 - 112, 536, x0 + 112, 588, ["调用模型 query"], 13, fill=COLORS["node_soft"])
    arrow(b, x0, 588, x0, 642)
    decision(b, x0, 678, 185, 150, ["模型是否", "要调用工具？"])

    # Branches and lower actions.
    arrow(b, x0 - 72, 735, x0 - 230, 786)
    arrow(b, x0 + 72, 735, x0 + 230, 786)
    text(b, x0 - 254, 742, x0 - 222, 765, ["是"], 11, COLORS["text"], True)
    text(b, x0 + 220, 742, x0 + 254, 765, ["否"], 11, COLORS["text"], True)
    node(b, x0 - 360, 786, x0 - 120, 835, ["执行工具并收集结果"], 12, fill=COLORS["green_soft"])
    node(b, x0 + 120, 786, x0 + 360, 835, ["输出最终结果"], 12)

    # Tool result write-back, and loop line.
    arrow(b, x0 - 240, 835, x0 - 240, 858)
    node(b, x0 - 135, 858, x0 + 135, 892, ["把工具结果写回消息历史"], 11, fill=COLORS["node_soft"])
    arrow(b, x0 - 120, 858, x0 - 260, 835, head=False)
    arrow(b, x0 + 135, 875, x0 + 420, 590)
    arrow(b, x0 + 420, 590, x0 + 112, 562)

    text(b, 1055, 802, 1488, 822, ["Source view: QueryEngine.ts / query.ts / Tool.ts"], 9, COLORS["source"])
    return b.items


def replace_slide(root: ET.Element, items: list[str]) -> bytes:
    sp_tree = root.find(f".//{qn(NS_P, 'spTree')}")
    if sp_tree is None:
        raise RuntimeError("spTree not found")
    preserved = []
    for child in list(sp_tree):
        if child.tag.split("}")[-1] in {"nvGrpSpPr", "grpSpPr"}:
            preserved.append(copy.deepcopy(child))
    sp_tree.clear()
    for child in preserved:
        sp_tree.append(child)
    for item in items:
        wrapped = f'<root xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">{item}</root>'
        sp_tree.append(ET.fromstring(wrapped)[0])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def strip_image_rels(rels: bytes | None) -> bytes | None:
    if not rels:
        return rels
    root = ET.fromstring(rels)
    for rel in list(root):
        if rel.attrib.get("Type", "").endswith("/image"):
            root.remove(rel)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    pptx = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\dd\Documents\PowerShell\Claude_Code_0604.pptx")
    backup = pptx.with_name(pptx.stem + f".bak_slide5_queryengine_{time.strftime('%Y%m%d_%H%M%S')}" + pptx.suffix)
    shutil.copy2(pptx, backup)
    tmp = pptx.with_name(pptx.stem + ".slide5_queryengine.tmp.pptx")
    with zipfile.ZipFile(pptx, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        names = zin.namelist()
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == "ppt/slides/slide5.xml":
                data = replace_slide(ET.fromstring(data), build_slide5())
            elif info.filename == "ppt/slides/_rels/slide5.xml.rels":
                data = strip_image_rels(data)
            zout.writestr(info, data)
        if "ppt/slides/_rels/slide5.xml.rels" not in names:
            pass
    tmp.replace(pptx)
    print(f"updated={pptx}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
