from __future__ import annotations

import copy
import shutil
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PPTX = Path(r"C:\Users\dd\Documents\PowerShell\Claude_Code_Best_源码分享_模板版_30min.pptx")

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("a", NS_A)
ET.register_namespace("r", NS_R)
ET.register_namespace("p", NS_P)

W_PX, H_PX = 1600, 900
SLIDE_W, SLIDE_H = 12192000, 6858000

COLORS = {
    "bg": "F8F2E8",
    "text": "243536",
    "muted": "69787A",
    "orange": "FF7A2F",
    "orange_soft": "FFE3D2",
    "green": "2F8F71",
    "green_soft": "E1F3EC",
    "blue": "2D6CDF",
    "blue_soft": "E7EEFF",
    "purple": "8B5CF6",
    "purple_soft": "F3EAFE",
    "panel": "FFF8EE",
    "panel2": "FFF2E3",
    "white": "FFFDF8",
    "shadow": "E8D9C8",
    "source": "9A8D7E",
}


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def px(v: float, axis: str = "x") -> int:
    return int(round(v / (W_PX if axis == "x" else H_PX) * (SLIDE_W if axis == "x" else SLIDE_H)))


def box(x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
    return px(x1), px(y1, "y"), px(x2 - x1), px(y2 - y1, "y")


class SlideBuilder:
    def __init__(self, start_id: int = 100):
        self.next_shape_id = start_id
        self.items: list[str] = []

    def nid(self) -> int:
        self.next_shape_id += 1
        return self.next_shape_id

    def add(self, xml: str) -> None:
        self.items.append(xml)


def solid(color: str, alpha: int | None = None) -> str:
    alpha_xml = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    return f'<a:solidFill><a:srgbClr val="{color}">{alpha_xml}</a:srgbClr></a:solidFill>'


def run(text: str, size: int, color: str, bold: bool = False) -> str:
    b = ' b="1"' if bold else ""
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<a:r><a:rPr lang="zh-CN" sz="{size * 100}"{b}>'
        f'{solid(color)}'
        '<a:latin typeface="Microsoft YaHei"/>'
        '<a:ea typeface="Microsoft YaHei"/>'
        '<a:cs typeface="Microsoft YaHei"/>'
        f'</a:rPr><a:t>{safe}</a:t></a:r>'
    )


def paras(lines: list[str], size: int, color: str, bold: bool = False, align: str = "l", gap: int = 400) -> str:
    out = []
    for line in lines:
        out.append(
            f'<a:p><a:pPr algn="{align}"><a:spcAft><a:spcPts val="{gap}"/></a:spcAft></a:pPr>'
            f'{run(line, size, color, bold)}</a:p>'
        )
    return "".join(out)


def shape(
    b: SlideBuilder,
    x: int,
    y: int,
    w: int,
    h: int,
    text_lines: list[str] | None = None,
    *,
    fill: str | None = None,
    line: str | None = None,
    line_w: int = 19050,
    radius: bool = False,
    font_size: int = 18,
    font_color: str = COLORS["text"],
    bold: bool = False,
    align: str = "l",
    margin: int = 95000,
    name: str = "editable",
    alpha: int | None = None,
) -> str:
    sid = b.nid()
    geom = "roundRect" if radius else "rect"
    fill_xml = solid(fill, alpha) if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="{line_w}">{solid(line)}</a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    tx = ""
    if text_lines is not None:
        tx = (
            f'<p:txBody><a:bodyPr wrap="square" lIns="{margin}" tIns="{margin}" rIns="{margin}" bIns="{margin}">'
            '<a:normAutofit fontScale="90000" lnSpcReduction="20000"/></a:bodyPr>'
            f'<a:lstStyle/>{paras(text_lines, font_size, font_color, bold, align)}</p:txBody>'
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
        <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
        {fill_xml}
        {line_xml}
      </p:spPr>
      {tx}
    </p:sp>"""


def connector(b: SlideBuilder, x1: float, y1: float, x2: float, y2: float, color: str = COLORS["orange"]) -> str:
    sid = b.nid()
    off_x, off_y = px(min(x1, x2)), px(min(y1, y2), "y")
    ext_x, ext_y = max(1, px(abs(x2 - x1))), max(1, px(abs(y2 - y1), "y"))
    flip_h = ' flipH="1"' if x2 < x1 else ""
    flip_v = ' flipV="1"' if y2 < y1 else ""
    return f"""
    <p:cxnSp>
      <p:nvCxnSpPr><p:cNvPr id="{sid}" name="editable arrow"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
      <p:spPr>
        <a:xfrm{flip_h}{flip_v}><a:off x="{off_x}" y="{off_y}"/><a:ext cx="{ext_x}" cy="{ext_y}"/></a:xfrm>
        <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
        <a:ln w="25400">{solid(color)}<a:headEnd type="triangle"/></a:ln>
      </p:spPr>
    </p:cxnSp>"""


def add_text(b: SlideBuilder, x1: float, y1: float, x2: float, y2: float, lines: list[str], size: int, color: str, bold: bool = False, align: str = "l") -> None:
    b.add(
        shape(
            b,
            *box(x1, y1, x2, y2),
            lines,
            font_size=size,
            font_color=color,
            bold=bold,
            align=align,
            margin=20000,
            name="editable text",
        )
    )


def add_card(b: SlideBuilder, x1: float, y1: float, x2: float, y2: float, title: str, body: list[str], fill: str, outline: str) -> None:
    # Small editable shadow.
    b.add(shape(b, *box(x1 + 5, y1 + 6, x2 + 5, y2 + 6), fill=COLORS["shadow"], radius=True, name="editable shadow"))
    b.add(shape(b, *box(x1, y1, x2, y2), fill=fill, line=outline, line_w=22860, radius=True, name="editable card"))
    add_text(b, x1 + 22, y1 + 18, x2 - 12, y1 + 45, [title], 17, COLORS["text"], True)
    add_text(b, x1 + 22, y1 + 60, x2 - 12, y2 - 8, body, 16, COLORS["muted"], False)


def add_node(b: SlideBuilder, x1: float, y1: float, x2: float, y2: float, label: list[str], size: int = 18) -> None:
    b.add(shape(b, *box(x1, y1, x2, y2), label, fill=COLORS["white"], line=COLORS["orange"], line_w=22860, radius=True, font_size=size, font_color=COLORS["text"], bold=True, align="ctr", margin=25000, name="editable node"))


def add_pill(b: SlideBuilder, x1: float, y1: float, x2: float, text: str) -> None:
    b.add(shape(b, *box(x1, y1, x2, y1 + 34), [text], fill=COLORS["white"], line=COLORS["orange"], line_w=15240, radius=True, font_size=12, font_color=COLORS["text"], align="ctr", margin=18000, name="editable pill"))


def build_content(with_canvas_bg: bool) -> list[str]:
    b = SlideBuilder()
    if with_canvas_bg:
        b.add(shape(b, 0, 0, SLIDE_W, SLIDE_H, fill=COLORS["bg"], name="editable page background"))

    add_text(b, 82, 52, 110, 82, ["02"], 14, COLORS["orange"], True)
    add_text(b, 124, 52, 300, 82, ["CLAUDE 是什么"], 14, COLORS["muted"], True)
    add_text(b, 82, 94, 920, 153, ["Claude Code = 终端里的工程代理系统"], 36, COLORS["text"], True)
    add_text(b, 84, 159, 1125, 190, ["不是聊天壳，而是把模型、工具、上下文、权限和本地执行串起来的 Agentic Coding Runtime。"], 17, COLORS["muted"])
    b.add(shape(b, *box(84, 199, 396, 204), fill=COLORS["orange"], name="editable accent line"))

    add_card(b, 88, 235, 392, 350, "Terminal-native", ["运行在本地终端", "直接面对项目目录"], COLORS["blue_soft"], COLORS["blue"])
    add_card(b, 420, 235, 724, 350, "Agentic Loop", ["模型会决策工具链", "不是一问一答"], COLORS["green_soft"], COLORS["green"])
    add_card(b, 88, 374, 392, 489, "Tool as Capability", ["读写文件 / Shell / 搜索", "MCP / LSP / 子 Agent"], COLORS["orange_soft"], COLORS["orange"])
    add_card(b, 420, 374, 724, 489, "Permission Boundary", ["能执行真实动作", "所以必须可控"], COLORS["purple_soft"], COLORS["purple"])

    b.add(shape(b, *box(92, 540, 728, 770), fill=COLORS["shadow"], radius=True, name="editable shadow"))
    b.add(shape(b, *box(88, 535, 724, 765), fill=COLORS["panel2"], line=COLORS["orange"], line_w=22860, radius=True, name="editable summary"))
    add_text(b, 122, 562, 360, 595, ["一句话给听众"], 21, COLORS["text"], True)
    add_text(b, 122, 613, 704, 747, ["Claude Code 的核心不是“会聊天”，", "而是“会在你的工程目录里行动”：", "", "读代码 -> 调工具 -> 执行动作 -> 看结果 -> 再决策。"], 21, COLORS["text"], True)

    b.add(shape(b, *box(786, 232, 1514, 770), fill=COLORS["shadow"], radius=True, name="editable shadow"))
    b.add(shape(b, *box(782, 226, 1510, 765), fill=COLORS["panel"], line=COLORS["orange"], line_w=22860, radius=True, alpha=94000, name="editable diagram panel"))
    add_text(b, 812, 257, 1130, 288, ["源码视角：一次会话背后的骨架"], 17, COLORS["text"], True)
    add_text(b, 812, 291, 1390, 318, ["用户输入最终进入 QueryEngine，再被拆成上下文、工具、状态与安全边界。"], 12, COLORS["muted"])

    add_node(b, 1105, 328, 1210, 380, ["用户"], 20)
    add_node(b, 1040, 425, 1275, 487, ["Claude Code 会话"], 20)
    add_node(b, 1062, 535, 1250, 596, ["QueryEngine"], 20)
    add_node(b, 1062, 666, 1250, 728, ["query.ts", "Agentic Loop"], 16)
    add_node(b, 1320, 500, 1482, 558, ["系统提示词", "消息历史"], 16)
    add_node(b, 822, 628, 1010, 686, ["Tool", "工具系统"], 16)
    add_node(b, 822, 708, 1010, 766, ["Context", "上下文系统"], 16)
    add_node(b, 1302, 628, 1482, 686, ["AppState", "状态系统"], 16)
    add_node(b, 1302, 708, 1482, 766, ["Plan Mode", "权限边界"], 16)

    b.add(connector(b, 1157, 380, 1157, 425))
    b.add(connector(b, 1157, 487, 1157, 535))
    b.add(connector(b, 1157, 596, 1157, 666))
    b.add(connector(b, 1250, 566, 1320, 529))
    b.add(connector(b, 1062, 566, 1010, 628))
    b.add(connector(b, 1088, 596, 1010, 708))
    b.add(connector(b, 1250, 566, 1302, 628))
    b.add(connector(b, 1230, 596, 1302, 708))

    add_pill(b, 814, 802, 985, "文件 / Shell / 搜索")
    add_pill(b, 1034, 802, 1152, "MCP / LSP")
    add_pill(b, 1210, 802, 1342, "Agent / Task")
    add_text(b, 1130, 842, 1520, 870, ["Source view: CLI / QueryEngine / query.ts / Tool.ts"], 12, COLORS["source"])

    return b.items


def replace_slide_shapes(root: ET.Element, shapes_xml: list[str]) -> None:
    sp_tree = root.find(f".//{{{NS_P}}}spTree")
    if sp_tree is None:
        raise RuntimeError("spTree not found")

    preserved = []
    for child in list(sp_tree):
        local = child.tag.split("}")[-1]
        if local in {"nvGrpSpPr", "grpSpPr"}:
            preserved.append(copy.deepcopy(child))

    sp_tree.clear()
    for child in preserved:
        sp_tree.append(child)
    for xml in shapes_xml:
        wrapped = (
            f'<root xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
            f"{xml}</root>"
        )
        sp_tree.append(ET.fromstring(wrapped)[0])


def strip_image_rels(rels_bytes: bytes | None) -> bytes | None:
    if not rels_bytes:
        return rels_bytes
    root = ET.fromstring(rels_bytes)
    for rel in list(root):
        if rel.attrib.get("Type", "").endswith("/image"):
            root.remove(rel)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if not PPTX.exists():
        raise FileNotFoundError(PPTX)

    backup = PPTX.with_name(PPTX.stem + f".bak_editable_{time.strftime('%Y%m%d_%H%M%S')}" + PPTX.suffix)
    shutil.copy2(PPTX, backup)

    tmp = PPTX.with_name(PPTX.stem + ".editable.tmp.pptx")
    with zipfile.ZipFile(PPTX, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        names = zin.namelist()
        slide2 = ET.fromstring(zin.read("ppt/slides/slide2.xml"))
        slide3 = ET.fromstring(zin.read("ppt/slides/slide3.xml"))
        replace_slide_shapes(slide2, build_content(with_canvas_bg=True))
        replace_slide_shapes(slide3, build_content(with_canvas_bg=False))

        modified = {
            "ppt/slides/slide2.xml": ET.tostring(slide2, encoding="utf-8", xml_declaration=True),
            "ppt/slides/slide3.xml": ET.tostring(slide3, encoding="utf-8", xml_declaration=True),
        }
        rel2_path = "ppt/slides/_rels/slide2.xml.rels"
        if rel2_path in names:
            modified[rel2_path] = strip_image_rels(zin.read(rel2_path))

        for item in zin.infolist():
            data = modified.get(item.filename)
            if data is None:
                data = zin.read(item.filename)
            zout.writestr(item, data)

    tmp.replace(PPTX)
    print(f"updated={PPTX}")
    print(f"backup={backup}")


if __name__ == "__main__":
    main()
