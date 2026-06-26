# -*- coding: utf-8 -*-
"""将 docker-fastapi-basics.md 转换为 PDF"""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, Preformatted, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── 注册中文字体 ──
import os, sys
_font_dirs = [
    r"C:\Windows\Fonts",
    r"C:\Users\why\AppData\Local\Microsoft\Windows\Fonts",
]
def _reg(name, files):
    for d in _font_dirs:
        for f in files:
            p = os.path.join(d, f)
            if os.path.isfile(p):
                pdfmetrics.registerFont(TTFont(name, p))
                return True
    return False

_reg("CN", ["msyh.ttc", "MSYH.TTC", "msyh.ttf"])
_reg("CNB", ["msyhbd.ttc", "MSYHBD.TTC", "msyhbd.ttf"])
_reg("CNC", ["msyhl.ttc", "MSYHL.TTC", "msyhl.ttf"])

# ── 颜色 ──
C_BG   = HexColor("#1E1E2E")
C_CODE = HexColor("#CDD6F4")
C_HEAD = HexColor("#1A5276")
C_H2   = HexColor("#2E86C1")
C_H3   = HexColor("#2874A6")
C_LINK = HexColor("#2980B9")
C_TBL_HEAD = HexColor("#2C3E50")
C_TBL_BG1  = HexColor("#EBF5FB")
C_TBL_BG2  = HexColor("#FFFFFF")

# ── 样式 ──
sTitle = ParagraphStyle("sTitle", fontName="CNB", fontSize=22, leading=30, alignment=TA_CENTER, textColor=C_HEAD, spaceAfter=6*mm)
sSub   = ParagraphStyle("sSub", fontName="CNC", fontSize=11, leading=16, alignment=TA_CENTER, textColor=HexColor("#555555"), spaceAfter=8*mm)
sH2    = ParagraphStyle("sH2", fontName="CNB", fontSize=16, leading=22, textColor=C_H2, spaceBefore=8*mm, spaceAfter=4*mm)
sH3    = ParagraphStyle("sH3", fontName="CNB", fontSize=13, leading=18, textColor=C_H3, spaceBefore=5*mm, spaceAfter=3*mm)
sH4    = ParagraphStyle("sH4", fontName="CNB", fontSize=11, leading=16, textColor=HexColor("#34495E"), spaceBefore=3*mm, spaceAfter=2*mm)
sBody  = ParagraphStyle("sBody", fontName="CN", fontSize=10, leading=15, textColor=HexColor("#2C3E50"), spaceAfter=2*mm)
sBold  = ParagraphStyle("sBold", fontName="CNB", fontSize=10, leading=15, textColor=HexColor("#2C3E50"), spaceAfter=2*mm)
sQuote = ParagraphStyle("sQuote", fontName="CNC", fontSize=9.5, leading=14, textColor=HexColor("#7F8C8D"), leftIndent=10*mm, spaceAfter=2*mm)
sCode  = ParagraphStyle("sCode", fontName="CN", fontSize=8.5, leading=12, textColor=C_CODE, backColor=C_BG, leftIndent=3*mm, rightIndent=3*mm, spaceBefore=2*mm, spaceAfter=2*mm, borderPadding=(4,4,4,4))
sCodeB = ParagraphStyle("sCodeB", fontName="CNB", fontSize=9, leading=13, textColor=HexColor("#F1C40F"), backColor=C_BG, leftIndent=3*mm, rightIndent=3*mm, spaceBefore=1*mm, spaceAfter=0, borderPadding=(2,2,2,2))

# ── 读取 MD ──
with open(r"E:\360MoveData\Users\why\Desktop\Agent项目\Multi-Agent\learning\docker-fastapi-basics.md", encoding="utf-8") as f:
    md = f.read()

# ── 工具函数 ──
def esc(text):
    """转义 reportlab XML 特殊字符"""
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def inline_md(text):
    """处理行内加粗和代码"""
    text = esc(text)
    # 加粗
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # 行内代码
    text = re.sub(r'`([^`]+)`', r'<font color="#E74C3C"><b>\1</b></font>', text)
    return text

def parse_table(lines):
    """解析 markdown 表格"""
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("|---") or re.match(r'^\|[\s\-:|]+\|$', ln):
            continue
        cells = [c.strip() for c in ln.split("|")[1:-1]]
        rows.append(cells)
    return rows

def make_table(rows):
    """生成 reportlab Table"""
    if not rows:
        return None
    # 转义 + 行内格式
    data = []
    for row in rows:
        data.append([Paragraph(inline_md(c), sBody) for c in row])
    
    ncol = max(len(r) for r in data)
    for r in data:
        while len(r) < ncol:
            r.append(Paragraph("", sBody))
    
    t = Table(data, colWidths=[None]*ncol)
    style_cmds = [
        ("FONTNAME", (0,0), (-1,-1), "CN"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, HexColor("#BDC3C7")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,0), (-1,0), C_TBL_HEAD),
        ("TEXTCOLOR", (0,0), (-1,0), HexColor("#FFFFFF")),
        ("FONTNAME", (0,0), (-1,0), "CNB"),
    ]
    # 斑马纹
    for i in range(1, len(data)):
        bg = C_TBL_BG1 if i % 2 == 1 else C_TBL_BG2
        style_cmds.append(("BACKGROUND", (0,i), (-1,i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t

# ── 解析 MD 为 story ──
story = []

# 标题
story.append(Paragraph("Docker + FastAPI 零基础学习指南", sTitle))
story.append(Paragraph("面向 Multi-Agent 项目的基础技术栈学习", sSub))

lines = md.split("\n")
i = 0
in_code = False
code_buf = []
code_lang = ""
in_table = False
table_buf = []

while i < len(lines):
    ln = lines[i]
    stripped = ln.strip()
    
    # ── 代码块 ──
    if stripped.startswith("```"):
        if in_code:
            # 结束代码块
            code_text = "\n".join(code_buf)
            # 如果有语言标注，先显示
            if code_lang:
                story.append(Paragraph(f"[ {code_lang} ]", sCodeB))
            story.append(Preformatted(esc(code_text), sCode))
            in_code = False
            code_buf = []
            code_lang = ""
        else:
            # 开始代码块
            # 先处理之前可能积累的表格
            if in_table and table_buf:
                tbl = make_table(parse_table(table_buf))
                if tbl:
                    story.append(tbl)
                in_table = False
                table_buf = []
            in_code = True
            code_lang = stripped[3:].strip()
            code_buf = []
        i += 1
        continue
    
    if in_code:
        code_buf.append(ln)
        i += 1
        continue
    
    # ── 空行 ──
    if not stripped:
        i += 1
        continue
    
    # ── 分隔线 ──
    if stripped == "---":
        story.append(Spacer(1, 3*mm))
        i += 1
        continue
    
    # ── 标题 ──
    if stripped.startswith("#### "):
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False; table_buf = []
        text = stripped[5:]
        story.append(Paragraph(inline_md(text), sH4))
        i += 1
        continue
    
    if stripped.startswith("### "):
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False; table_buf = []
        text = stripped[4:]
        story.append(Paragraph(inline_md(text), sH3))
        i += 1
        continue
    
    if stripped.startswith("## "):
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False; table_buf = []
        text = stripped[3:]
        story.append(Paragraph(inline_md(text), sH2))
        i += 1
        continue
    
    # ── 引用 ──
    if stripped.startswith("> "):
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False; table_buf = []
        text = stripped[2:]
        story.append(Paragraph(inline_md(text), sQuote))
        i += 1
        continue
    
    # ── 列表项 ──
    if stripped.startswith("- ") or re.match(r'^\d+\.\s', stripped):
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False; table_buf = []
        text = re.sub(r'^[-\d]+\.\s*', '', stripped)
        story.append(Paragraph("  • " + inline_md(text), sBody))
        i += 1
        continue
    
    # ── 表格行 ──
    if stripped.startswith("|"):
        in_table = True
        table_buf.append(stripped)
        i += 1
        continue
    else:
        if in_table and table_buf:
            tbl = make_table(parse_table(table_buf))
            if tbl: story.append(tbl)
            in_table = False
            table_buf = []
    
    # ── 普通段落 ──
    story.append(Paragraph(inline_md(stripped), sBody))
    i += 1

# 收尾表格
if in_table and table_buf:
    tbl = make_table(parse_table(table_buf))
    if tbl: story.append(tbl)

# ── 生成 PDF ──
out = r"E:\360MoveData\Users\why\Desktop\Agent项目\Multi-Agent\learning\docker-fastapi-basics.pdf"
doc = SimpleDocTemplate(
    out, pagesize=A4,
    leftMargin=18*mm, rightMargin=18*mm,
    topMargin=20*mm, bottomMargin=20*mm,
    title="Docker + FastAPI 零基础学习指南",
    author="虾米 AI"
)
doc.build(story)
print(f"OK → {out}")
sz = os.path.getsize(out)
print(f"大小: {sz/1024:.1f} KB")
