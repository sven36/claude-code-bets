from __future__ import annotations

import html
import os
import re
import struct
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Claude_Code_Best_源码分享_30min.pptx"
IMG = ROOT / "docs" / "images"

EMU_PER_INCH = 914400
SLIDE_W = int(13.333333 * EMU_PER_INCH)
SLIDE_H = int(7.5 * EMU_PER_INCH)

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


COLORS = {
    "bg": "0F172A",
    "panel": "172033",
    "panel2": "1F2A44",
    "line": "334155",
    "title": "F8FAFC",
    "text": "CBD5E1",
    "muted": "94A3B8",
    "accent": "22D3EE",
    "accent2": "A3E635",
    "warn": "FBBF24",
    "white": "FFFFFF",
}


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def emu(inches: float) -> int:
    return int(inches * EMU_PER_INCH)


def color_xml(color: str) -> str:
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'


def rect_xml(x, y, w, h, fill, line=None, radius=False, alpha=None):
    fill_xml = f'<a:solidFill><a:srgbClr val="{fill}">'
    if alpha is not None:
        fill_xml += f'<a:alpha val="{alpha}"/>'
    fill_xml += "</a:srgbClr></a:solidFill>"
    if line:
        line_xml = f'<a:ln w="9525">{color_xml(line)}</a:ln>'
    else:
        line_xml = '<a:ln><a:noFill/></a:ln>'
    geom = "roundRect" if radius else "rect"
    return f"""
      <p:sp>
        <p:nvSpPr><p:cNvPr id="{next_id()}" name="shape"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
          <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
          {fill_xml}
          {line_xml}
        </p:spPr>
      </p:sp>
    """


_shape_id = 10


def next_id():
    global _shape_id
    _shape_id += 1
    return _shape_id


def run_xml(text, size=24, color=None, bold=False, font="Microsoft YaHei"):
    c = color or COLORS["text"]
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="zh-CN" sz="{int(size * 100)}"{b}>'
        f'{color_xml(c)}'
        f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/>'
        f"</a:rPr><a:t>{esc(text)}</a:t></a:r>"
    )


def paragraph_xml(text="", size=24, color=None, bold=False, bullet=False, level=0, align="l", space_after=550):
    ppr = f'<a:pPr algn="{align}" marL="{level * 260000}" indent="0">'
    if bullet:
        ppr += '<a:buChar char="•"/>'
    else:
        ppr += "<a:buNone/>"
    ppr += f'<a:spcAft><a:spcPts val="{space_after}"/></a:spcAft></a:pPr>'
    return f"<a:p>{ppr}{run_xml(text, size, color, bold)}</a:p>"


def text_box_xml(x, y, w, h, paragraphs, fill=None, line=None, margin=0.08, radius=False, valign="t"):
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    body = "".join(paragraphs)
    fill_xml = color_xml(fill) if fill else "<a:noFill/>"
    line_xml = f'<a:ln w="9525">{color_xml(line)}</a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return f"""
      <p:sp>
        <p:nvSpPr><p:cNvPr id="{next_id()}" name="text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
          <a:prstGeom prst="{'roundRect' if radius else 'rect'}"><a:avLst/></a:prstGeom>
          {fill_xml}
          {line_xml}
        </p:spPr>
        <p:txBody>
          <a:bodyPr wrap="square" anchor="{valign}" lIns="{emu(margin)}" tIns="{emu(margin)}" rIns="{emu(margin)}" bIns="{emu(margin)}">
            <a:normAutofit fontScale="90000" lnSpcReduction="20000"/>
          </a:bodyPr>
          <a:lstStyle/>
          {body}
        </p:txBody>
      </p:sp>
    """


def title_xml(title, subtitle=None, kicker=None):
    parts = []
    if kicker:
        parts.append(text_box_xml(emu(0.7), emu(0.35), emu(4.5), emu(0.35), [
            paragraph_xml(kicker, 13, COLORS["accent"], True, space_after=0)
        ]))
    parts.append(text_box_xml(emu(0.7), emu(0.75), emu(12.0), emu(0.8), [
        paragraph_xml(title, 30, COLORS["title"], True, space_after=0)
    ]))
    if subtitle:
        parts.append(text_box_xml(emu(0.72), emu(1.45), emu(11.7), emu(0.35), [
            paragraph_xml(subtitle, 13.5, COLORS["muted"], False, space_after=0)
        ]))
    parts.append(rect_xml(emu(0.7), emu(1.85), emu(1.05), emu(0.035), COLORS["accent"]))
    return "".join(parts)


def code_box_xml(x, y, w, h, lines, title=None):
    paras = []
    if title:
        paras.append(paragraph_xml(title, 12, COLORS["accent2"], True, space_after=400))
    for line in lines:
        paras.append(paragraph_xml(line, 14, COLORS["white"], False, space_after=180))
    return text_box_xml(x, y, w, h, paras, fill="111827", line=COLORS["line"], margin=0.16, radius=True)


def image_size(path: Path):
    with path.open("rb") as f:
        sig = f.read(24)
    if sig.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", sig[16:24])
    raise ValueError(f"Unsupported image format: {path}")


def image_xml(rel_id, x, y, w, h, name="image"):
    return f"""
      <p:pic>
        <p:nvPicPr><p:cNvPr id="{next_id()}" name="{esc(name)}"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="{rel_id}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr>
          <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:ln><a:noFill/></a:ln>
        </p:spPr>
      </p:pic>
    """


def fit_image(path: Path, x, y, w, h):
    iw, ih = image_size(path)
    scale = min(w / iw, h / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    return x + (w - nw) // 2, y + (h - nh) // 2, nw, nh


def bg_xml():
    return f'<p:bg><p:bgPr>{color_xml(COLORS["bg"])}</p:bgPr></p:bg>'


def slide_xml(shapes):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    {bg_xml()}
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def rels_xml(rels):
    body = "".join(
        f'<Relationship Id="{rid}" Type="{typ}" Target="{target}"/>'
        for rid, typ, target in rels
    )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'


def content_types_xml(slide_count):
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    overrides.extend(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  {''.join(overrides)}
</Types>"""


def presentation_xml(slide_count):
    sld_ids = "".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>'
        for i in range(1, slide_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId{slide_count + 1}"/></p:sldMasterIdLst>
  <p:sldIdLst>{sld_ids}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
  <p:defaultTextStyle>
    <a:defPPr><a:defRPr lang="zh-CN"/></a:defPPr>
  </p:defaultTextStyle>
</p:presentation>"""


def slide_master_xml():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>{bg_xml()}<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>"""


def slide_layout_xml():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""


def theme_xml():
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{NS_A}" name="Claude Code Best">
  <a:themeElements>
    <a:clrScheme name="Dark"><a:dk1><a:srgbClr val="0F172A"/></a:dk1><a:lt1><a:srgbClr val="F8FAFC"/></a:lt1><a:dk2><a:srgbClr val="172033"/></a:dk2><a:lt2><a:srgbClr val="CBD5E1"/></a:lt2><a:accent1><a:srgbClr val="22D3EE"/></a:accent1><a:accent2><a:srgbClr val="A3E635"/></a:accent2><a:accent3><a:srgbClr val="FBBF24"/></a:accent3><a:accent4><a:srgbClr val="38BDF8"/></a:accent4><a:accent5><a:srgbClr val="F472B6"/></a:accent5><a:accent6><a:srgbClr val="818CF8"/></a:accent6><a:hlink><a:srgbClr val="22D3EE"/></a:hlink><a:folHlink><a:srgbClr val="94A3B8"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="Microsoft YaHei"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Default"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle/></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>"""


def core_props_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Claude Code Best 源码项目分享</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:keywords>Claude Code, Agentic Loop, Tool, Permission, Context</cp:keywords>
  <dc:description>基于 PROJECT_SHARE_SPEECH_30MIN.md 生成的 30 分钟技术分享 PPT。</dc:description>
</cp:coreProperties>"""


def app_props_xml(slide_count):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Codex OOXML Generator</Application><PresentationFormat>宽屏</PresentationFormat><Slides>{slide_count}</Slides>
</Properties>"""


def slide_layout_rel_type():
    return "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"


def image_rel_type():
    return "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def build_slides():
    slides = []

    def add(shapes, images=None):
        slides.append({"shapes": shapes, "images": images or []})

    add([
        rect_xml(0, 0, SLIDE_W, SLIDE_H, COLORS["bg"]),
        rect_xml(emu(0.7), emu(0.65), emu(0.08), emu(5.9), COLORS["accent"]),
        text_box_xml(emu(0.95), emu(0.85), emu(11.2), emu(1.3), [
            paragraph_xml("Claude Code Best", 44, COLORS["title"], True, space_after=100),
            paragraph_xml("源码项目分享：从 CLI 到 Agent 运行时", 22, COLORS["text"], False, space_after=0),
        ]),
        text_box_xml(emu(0.98), emu(3.0), emu(8.9), emu(1.7), [
            paragraph_xml("30 分钟建立共同认知", 20, COLORS["accent2"], True, space_after=550),
            paragraph_xml("React/Ink 终端前端 + QueryEngine 会话编排 + query.ts Agentic Loop + Tool/Permission/API 基础设施", 22, COLORS["white"], True, space_after=0),
        ]),
        text_box_xml(emu(0.98), emu(6.65), emu(10.5), emu(0.35), [
            paragraph_xml("基于 PROJECT_SHARE_SPEECH_30MIN.md", 12, COLORS["muted"], False, space_after=0)
        ]),
    ])

    add([
        title_xml("今天讲什么", "按 30 分钟源码导读节奏组织", "00 议程"),
        text_box_xml(emu(0.9), emu(2.25), emu(5.4), emu(4.5), [
            paragraph_xml("0-5 min  项目定位、技术栈、仓库地图", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("5-10 min  分层架构与主链路", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("10-17 min Agentic Loop 深入", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("17-25 min 工具、权限、上下文", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("25-30 min 扩展入口、总结、Q&A", 22, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        code_box_xml(emu(7.0), emu(2.35), emu(5.35), emu(3.85), [
            "CLI 启动",
            "  -> 终端 UI / headless 输入",
            "  -> QueryEngine 会话编排",
            "  -> query.ts Agentic Loop",
            "  -> Tool 系统执行动作",
            "  -> API Provider 与模型通信",
        ], "主线")
    ])

    add([
        title_xml("项目定位", "它不是聊天 CLI，而是终端 Agent 平台", "01 项目定位"),
        text_box_xml(emu(0.9), emu(2.1), emu(5.8), emu(4.65), [
            paragraph_xml("模型可以真实做事：读文件、改文件、执行命令、调用 MCP、创建子 Agent", 21, COLORS["white"], True, bullet=True),
            paragraph_xml("系统要管理多轮会话、上下文、记忆、transcript、成本和中断", 21, COLORS["white"], True, bullet=True),
            paragraph_xml("所有动作必须被权限、Hook、Plan Mode 和 UI 状态管住", 21, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        text_box_xml(emu(7.2), emu(2.35), emu(4.9), emu(2.9), [
            paragraph_xml("一句话", 16, COLORS["accent"], True, space_after=400),
            paragraph_xml("Claude Code Best 是一套终端 Agent 运行时，而不是模型聊天壳子。", 26, COLORS["title"], True, space_after=0),
        ], fill=COLORS["panel2"], line=COLORS["accent"], margin=0.25, radius=True),
    ])

    add([
        title_xml("技术栈与仓库地图", "先建立问题归类坐标系", "02 工程地图"),
        text_box_xml(emu(0.75), emu(2.1), emu(3.95), emu(4.75), [
            paragraph_xml("Bun + TypeScript/TSX", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("React 19 + Ink 终端 UI", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("Commander.js CLI 路由", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("Zod / JSON Schema 工具入参校验", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("Anthropic + OpenAI/Gemini/Grok Provider 适配", 20, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.2, radius=True),
        code_box_xml(emu(5.25), emu(2.15), emu(3.25), emu(4.35), [
            "src/       主应用源码",
            "packages/  workspace 子包",
            "docs/      架构和功能文档",
            "tests/     集成测试/mocks",
            "scripts/   构建与健康检查",
            "vendor/    原生资源",
        ], "顶层结构"),
        code_box_xml(emu(8.95), emu(2.15), emu(3.65), emu(4.35), [
            "bun install",
            "bun run dev",
            "bun run build",
            "bun test",
            "bun run lint",
            "",
            "bin: ccb / claude-code-best",
        ], "常用命令")
    ])

    arch = IMG / "architecture-layers.png"
    ix, iy, iw, ih = fit_image(arch, emu(5.6), emu(2.0), emu(6.65), emu(4.95))
    add([
        title_xml("七层架构总览", "入口、前端、会话、循环、工具、Provider、基础设施", "03 架构分层"),
        text_box_xml(emu(0.75), emu(2.1), emu(4.35), emu(4.65), [
            paragraph_xml("CLI Bootstrap：快速路径与特殊模式", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("main.tsx：配置、命令、运行模式分发", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("REPL/headless：不同前端，共用核心", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("QueryEngine：会话级编排器", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("query.ts：Agentic Loop 状态机", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("Tool/API/MCP/Permission：真实执行与边界", 18.5, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.18, radius=True),
        image_xml("rIdImg1", ix, iy, iw, ih, "architecture-layers"),
    ], [arch])

    add([
        title_xml("启动与路由", "短命令不为完整应用付启动成本", "04 Bootstrap"),
        code_box_xml(emu(0.85), emu(2.2), emu(5.2), emu(3.65), [
            "src/entrypoints/cli.tsx",
            "  --version 快速输出",
            "  Chrome / Computer Use MCP",
            "  daemon worker / bridge",
            "  dynamic import('../main.jsx')",
        ], "冷启动优化"),
        text_box_xml(emu(6.75), emu(2.2), emu(5.55), emu(3.65), [
            paragraph_xml("src/main.tsx 是初始化中心", 22, COLORS["title"], True, space_after=550),
            paragraph_xml("配置、认证、feature flags、policy limits、遥测、MCP、插件、skills、tools、commands 都在这里被组织。", 21, COLORS["white"], True, bullet=True),
            paragraph_xml("最终进入 REPL、headless、resume、remote/bridge 等路径。", 21, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
    ])

    add([
        title_xml("UI 与会话编排", "REPL 只是一个前端，QueryEngine 才是会话组织者", "05 QueryEngine"),
        text_box_xml(emu(0.75), emu(2.1), emu(5.7), emu(4.55), [
            paragraph_xml("REPL.tsx：消息列表、输入框、权限弹窗、状态栏、任务面板", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("src/cli：print、structured IO、headless 输出", 20, COLORS["white"], True, bullet=True),
            paragraph_xml("二者共用 QueryEngine 和 query.ts", 20, COLORS["accent2"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        text_box_xml(emu(7.0), emu(2.1), emu(5.35), emu(4.55), [
            paragraph_xml("QueryEngine 维护", 22, COLORS["title"], True, space_after=520),
            paragraph_xml("mutableMessages / readFileState / permissionDenials / totalUsage / transcript / abortController / skill discovery", 21, COLORS["white"], True, bullet=True),
            paragraph_xml("它把 UI/SDK 输入变成 query() 可消费的参数，并把输出再转回 UI/SDK。", 21, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel2"], line=COLORS["line"], margin=0.22, radius=True),
    ])

    loop = IMG / "agentic-loop.png"
    ix, iy, iw, ih = fit_image(loop, emu(6.7), emu(2.0), emu(5.6), emu(4.95))
    add([
        title_xml("Agentic Loop 是核心", "从一次问答变成“思考、行动、观察、再思考”", "06 Agentic Loop"),
        code_box_xml(emu(0.75), emu(2.05), emu(5.25), emu(4.85), [
            "用户输入",
            "  -> 请求模型",
            "  -> 模型发出 tool_use",
            "  -> 系统执行工具",
            "  -> tool_result 写回消息",
            "  -> 模型继续判断",
            "  -> 没有工具调用后结束",
        ], "普通聊天 CLI 做不到的部分"),
        image_xml("rIdImg1", ix, iy, iw, ih, "agentic-loop"),
    ], [loop])

    stream = IMG / "streaming-timeline.png"
    ix, iy, iw, ih = fit_image(stream, emu(6.6), emu(2.15), emu(5.7), emu(4.65))
    add([
        title_xml("query.ts 的五步循环", "AsyncGenerator 让 UI 可以边执行边展示", "07 核心流程"),
        text_box_xml(emu(0.75), emu(2.05), emu(5.15), emu(4.85), [
            paragraph_xml("1. 上下文预处理：预算、snip、compact、collapse", 18.8, COLORS["white"], True, bullet=True),
            paragraph_xml("2. 流式调用模型：接收 text / tool_use", 18.8, COLORS["white"], True, bullet=True),
            paragraph_xml("3. 执行工具：并发安全则并行，有副作用则串行", 18.8, COLORS["white"], True, bullet=True),
            paragraph_xml("4. tool_result 写回消息流", 18.8, COLORS["white"], True, bullet=True),
            paragraph_xml("5. 继续、恢复、重试或终止", 18.8, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.18, radius=True),
        image_xml("rIdImg1", ix, iy, iw, ih, "streaming-timeline"),
    ], [stream])

    add([
        title_xml("工具系统：Tool as Capability", "工具不是函数，而是结构化能力对象", "08 Tools"),
        text_box_xml(emu(0.75), emu(2.15), emu(5.5), emu(4.55), [
            paragraph_xml("src/Tool.ts：工具类型、权限上下文、结果结构", 19.2, COLORS["white"], True, bullet=True),
            paragraph_xml("src/tools.ts：按 feature/env/权限/MCP/插件组装工具", 19.2, COLORS["white"], True, bullet=True),
            paragraph_xml("src/tools/*：Bash、FileRead、FileEdit、Grep、Agent、MCP、WebSearch、Skill", 19.2, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.2, radius=True),
        text_box_xml(emu(6.95), emu(2.15), emu(5.25), emu(4.55), [
            paragraph_xml("每个工具包含", 21, COLORS["title"], True, space_after=450),
            paragraph_xml("name / input schema / description / call()", 19.5, COLORS["white"], True, bullet=True),
            paragraph_xml("是否启用、只读、并发安全、破坏性操作", 19.5, COLORS["white"], True, bullet=True),
            paragraph_xml("权限上下文、结果大小限制、进度类型", 19.5, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel2"], line=COLORS["line"], margin=0.22, radius=True),
    ])

    perm = IMG / "permission-layers.png"
    ix, iy, iw, ih = fit_image(perm, emu(6.55), emu(2.0), emu(5.75), emu(4.95))
    add([
        title_xml("权限边界", "模型只提出意图，权限系统决定边界，工具系统负责执行", "09 Permission"),
        code_box_xml(emu(0.75), emu(2.0), emu(5.1), emu(4.95), [
            "模型请求 tool_use",
            "  -> schema 校验",
            "  -> 工具自身权限检查",
            "  -> allow / ask / deny 规则",
            "  -> hook 介入",
            "  -> UI 弹窗 / headless callback",
            "  -> 允许后才真正 call()",
        ], "执行前裁决"),
        image_xml("rIdImg1", ix, iy, iw, ih, "permission-layers"),
    ], [perm])

    comp = IMG / "compaction.png"
    ix, iy, iw, ih = fit_image(comp, emu(6.55), emu(2.05), emu(5.75), emu(4.75))
    add([
        title_xml("上下文、记忆与压缩", "把上下文窗口当成一等资源管理", "10 Context"),
        text_box_xml(emu(0.75), emu(2.05), emu(5.2), emu(4.75), [
            paragraph_xml("System Prompt / userContext / toolUseContext 组装", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("CLAUDE.md、项目记忆、session memory、nested memory", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("token 估算、预算、输出控制", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("autoCompact、reactiveCompact、contextCollapse、microcompact", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("过长工具结果落盘，只把预览和路径给模型", 18.5, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.18, radius=True),
        image_xml("rIdImg1", ix, iy, iw, ih, "compaction"),
    ], [comp])

    data = IMG / "data-flow.png"
    ix, iy, iw, ih = fit_image(data, emu(6.55), emu(2.0), emu(5.75), emu(4.95))
    add([
        title_xml("API Provider 与模型通信", "query.ts 不直接绑定某个 Provider", "11 Provider"),
        text_box_xml(emu(0.75), emu(2.05), emu(5.25), emu(4.8), [
            paragraph_xml("src/services/api/claude.ts 是 Claude 主实现", 19, COLORS["white"], True, bullet=True),
            paragraph_xml("openai / gemini / grok 目录负责协议适配", 19, COLORS["white"], True, bullet=True),
            paragraph_xml("适配点：消息转换、工具转换、stream adapter、model mapping", 19, COLORS["white"], True, bullet=True),
            paragraph_xml("统一 streaming 事件让核心循环不被 Provider 细节污染", 19, COLORS["accent2"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.2, radius=True),
        image_xml("rIdImg1", ix, iy, iw, ih, "data-flow"),
    ], [data])

    mcp = IMG / "mcp-architecture.png"
    ix, iy, iw, ih = fit_image(mcp, emu(7.05), emu(2.15), emu(5.05), emu(4.45))
    add([
        title_xml("扩展体系与二次开发入口", "先判断你要扩展的是命令、工具、Provider、MCP、插件还是 UI", "12 Extension"),
        text_box_xml(emu(0.75), emu(2.05), emu(5.85), emu(4.8), [
            paragraph_xml("Slash Commands：src/commands/、src/commands.ts", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("Tools：src/Tool.ts、src/tools.ts、src/tools/*", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("Provider：src/services/api/，参考 openai/gemini/grok", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("MCP/Plugins/Skills：services/mcp、utils/plugins、src/skills", 18.5, COLORS["white"], True, bullet=True),
            paragraph_xml("UI/权限/压缩：screens、hooks、utils/permissions、services/compact", 18.5, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.18, radius=True),
        image_xml("rIdImg1", ix, iy, iw, ih, "mcp-architecture"),
    ], [mcp])

    add([
        title_xml("源码阅读路线", "不要直接从 main.tsx 或 REPL.tsx 硬啃", "13 Reading Path"),
        code_box_xml(emu(0.75), emu(2.0), emu(5.7), emu(4.9), [
            "1. package.json + build.ts",
            "2. src/entrypoints/cli.tsx",
            "3. src/main.tsx",
            "4. REPL.tsx / src/cli",
            "5. src/QueryEngine.ts",
            "6. src/query.ts",
        ], "第一轮：跑通主链路"),
        code_box_xml(emu(7.0), emu(2.0), emu(5.3), emu(4.9), [
            "7. src/Tool.ts + src/tools.ts",
            "8. FileEditTool 或 BashTool",
            "9. services/api/claude.ts",
            "10. services/api/openai/",
            "11. utils/permissions/",
            "12. services/compact/",
        ], "第二轮：深入关键模块")
    ])

    add([
        title_xml("现场演示映射", "把运行时现象和源码位置对应起来", "14 Demo"),
        text_box_xml(emu(0.9), emu(2.05), emu(11.35), emu(4.9), [
            paragraph_xml("启动命令 -> src/entrypoints/cli.tsx 与 src/main.tsx", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("输入框和消息列表 -> src/screens/REPL.tsx", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("一次模型请求 -> src/QueryEngine.ts 与 src/query.ts", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("文件读取、搜索、命令执行 -> src/tools/", 22, COLORS["white"], True, bullet=True),
            paragraph_xml("权限弹窗 -> canUseTool 与 ToolPermissionContext", 22, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.24, radius=True),
    ])

    add([
        title_xml("总结", "复杂度来自 CLI、Agent、平台三件事叠加", "15 Wrap-up"),
        text_box_xml(emu(0.9), emu(2.05), emu(3.55), emu(3.6), [
            paragraph_xml("复杂 CLI", 25, COLORS["accent"], True, space_after=450),
            paragraph_xml("启动性能、跨平台、终端渲染、快捷键、headless 输出", 19.5, COLORS["white"], True, space_after=0),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        text_box_xml(emu(4.9), emu(2.05), emu(3.55), emu(3.6), [
            paragraph_xml("复杂 Agent", 25, COLORS["accent2"], True, space_after=450),
            paragraph_xml("多轮循环、工具调用、上下文压缩、错误恢复、成本追踪", 19.5, COLORS["white"], True, space_after=0),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        text_box_xml(emu(8.9), emu(2.05), emu(3.55), emu(3.6), [
            paragraph_xml("平台化能力", 25, COLORS["warn"], True, space_after=450),
            paragraph_xml("MCP、插件、Skills、子 Agent、远程控制、多 Provider、feature flags", 19.5, COLORS["white"], True, space_after=0),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.22, radius=True),
        text_box_xml(emu(1.15), emu(6.0), emu(11.0), emu(0.75), [
            paragraph_xml("核心主线：React/Ink 前端 + QueryEngine + query.ts Agentic Loop + Tool/Permission/API", 20, COLORS["title"], True, space_after=0, align="c"),
        ], fill=COLORS["panel2"], line=COLORS["accent"], margin=0.1, radius=True),
    ])

    add([
        title_xml("Q&A 引导", "用问题把分享落到后续改造工作", "16 Q&A"),
        text_box_xml(emu(0.9), emu(2.05), emu(11.25), emu(4.85), [
            paragraph_xml("如果要新增内部工具，应该走 Tool 还是 MCP？", 23, COLORS["white"], True, bullet=True),
            paragraph_xml("如果要接入新的模型服务，Provider 适配最小改动点在哪里？", 23, COLORS["white"], True, bullet=True),
            paragraph_xml("当前权限模型是否满足我们的使用场景？", 23, COLORS["white"], True, bullet=True),
            paragraph_xml("对长任务来说，压缩策略和 transcript 是否还需要增强？", 23, COLORS["white"], True, bullet=True),
        ], fill=COLORS["panel"], line=COLORS["line"], margin=0.28, radius=True),
    ])

    return slides


def write_pptx():
    slides = build_slides()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml(len(slides)))
        z.writestr("_rels/.rels", rels_xml([
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
        ]))
        z.writestr("docProps/core.xml", core_props_xml())
        z.writestr("docProps/app.xml", app_props_xml(len(slides)))
        z.writestr("ppt/presentation.xml", presentation_xml(len(slides)))

        pres_rels = [
            (f"rId{i}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide", f"slides/slide{i}.xml")
            for i in range(1, len(slides) + 1)
        ]
        pres_rels.append((f"rId{len(slides) + 1}", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster", "slideMasters/slideMaster1.xml"))
        z.writestr("ppt/_rels/presentation.xml.rels", rels_xml(pres_rels))
        z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", rels_xml([
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme", "../theme/theme1.xml"),
        ]))
        z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", rels_xml([
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster", "../slideMasters/slideMaster1.xml")
        ]))
        z.writestr("ppt/theme/theme1.xml", theme_xml())

        media_written = {}
        media_idx = 0
        for idx, slide in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{idx}.xml", slide_xml(slide["shapes"]))
            rels = [("rId1", slide_layout_rel_type(), "../slideLayouts/slideLayout1.xml")]
            for img_num, img_path in enumerate(slide["images"], 1):
                img_path = Path(img_path)
                if img_path not in media_written:
                    media_idx += 1
                    media_name = f"image{media_idx}.png"
                    media_written[img_path] = media_name
                    z.write(img_path, f"ppt/media/{media_name}")
                rels.append((f"rIdImg{img_num}", image_rel_type(), f"../media/{media_written[img_path]}"))
            z.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", rels_xml(rels))


if __name__ == "__main__":
    write_pptx()
    print(OUT)
