from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "作品说明文档.md"
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT = OUTPUT_DIR / "景区AI数字人智能导览系统-作品说明文档.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
TOP = 19 * mm
BOTTOM = 18 * mm

INK = colors.HexColor("#24332E")
MUTED = colors.HexColor("#65736E")
GREEN = colors.HexColor("#2F6B57")
GREEN_DARK = colors.HexColor("#1F4D3E")
GREEN_LIGHT = colors.HexColor("#EAF2EE")
GOLD = colors.HexColor("#B28A4A")
GOLD_LIGHT = colors.HexColor("#F6F0E4")
LINE = colors.HexColor("#CDD8D3")
PAPER = colors.HexColor("#FCFDFB")


def register_fonts() -> tuple[str, str]:
    candidates = [
        (Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\msyhbd.ttc")),
        (Path(r"C:\Windows\Fonts\simsun.ttc"), Path(r"C:\Windows\Fonts\simhei.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("CN", str(regular)))
            pdfmetrics.registerFont(TTFont("CN-Bold", str(bold)))
            addMapping("CN", 0, 0, "CN")
            addMapping("CN", 1, 0, "CN-Bold")
            return "CN", "CN-Bold"
    raise FileNotFoundError("No supported Chinese font found in C:\\Windows\\Fonts")


FONT, FONT_BOLD = register_fonts()


def normalize_text(value: str) -> str:
    return value.replace("—", " - ").replace("–", "-").replace("‑", "-")


def inline_markup(value: str) -> str:
    text = escape(normalize_text(value.strip()))
    text = re.sub(r"`([^`]+)`", r'<font color="#2F6B57">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return text


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CNBody", fontName=FONT, fontSize=10.3, leading=17.2,
    textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4 * mm,
    wordWrap="CJK", allowWidows=0, allowOrphans=0,
))
styles.add(ParagraphStyle(
    name="CNH1", fontName=FONT_BOLD, fontSize=20, leading=28,
    textColor=GREEN_DARK, spaceBefore=4 * mm, spaceAfter=5 * mm,
    keepWithNext=True, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="TOCTitle", parent=styles["CNH1"],
))
styles.add(ParagraphStyle(
    name="CNH2", fontName=FONT_BOLD, fontSize=15, leading=22,
    textColor=GREEN, spaceBefore=5 * mm, spaceAfter=3 * mm,
    keepWithNext=True, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="CNH3", fontName=FONT_BOLD, fontSize=12.2, leading=18,
    textColor=colors.HexColor("#765D34"), spaceBefore=3.5 * mm,
    spaceAfter=2.2 * mm, keepWithNext=True, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="CNBullet", parent=styles["CNBody"], leftIndent=6 * mm,
    firstLineIndent=-4 * mm, bulletIndent=1.2 * mm, spaceAfter=1.8 * mm,
))
styles.add(ParagraphStyle(
    name="CNQuote", parent=styles["CNBody"], backColor=GREEN_LIGHT,
    borderColor=GREEN, borderWidth=0.8, borderPadding=8,
    leftIndent=3 * mm, rightIndent=3 * mm, textColor=GREEN_DARK,
    spaceBefore=2 * mm, spaceAfter=4 * mm,
))
styles.add(ParagraphStyle(
    name="CNCaption", fontName=FONT, fontSize=8.8, leading=13,
    textColor=MUTED, alignment=TA_CENTER, spaceBefore=1.5 * mm,
    spaceAfter=4 * mm, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="CNTable", fontName=FONT, fontSize=8.1, leading=11.8,
    textColor=INK, wordWrap="CJK", splitLongWords=0,
))
styles.add(ParagraphStyle(
    name="CNTableHead", fontName=FONT_BOLD, fontSize=8.3, leading=12,
    textColor=colors.white, alignment=TA_CENTER, wordWrap="CJK",
))


class WorkDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=TOP,
            bottomMargin=BOTTOM,
            title="景区 AI 数字人智能导览系统作品说明文档",
            author="项目团队",
            subject="软件杯作品说明文档",
        )
        cover_frame = Frame(0, 0, PAGE_W, PAGE_H, id="cover", showBoundary=0)
        body_frame = Frame(
            MARGIN_X, BOTTOM, PAGE_W - 2 * MARGIN_X, PAGE_H - TOP - BOTTOM,
            id="body", leftPadding=0, rightPadding=0, topPadding=3 * mm, bottomPadding=0,
        )
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[cover_frame], onPage=self.draw_cover),
            PageTemplate(id="Body", frames=[body_frame], onPage=self.draw_body),
        ])

    def draw_cover(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(GREEN_DARK)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#315E50"))
        canvas.circle(PAGE_W - 25 * mm, 25 * mm, 48 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#3B7663"))
        canvas.circle(PAGE_W - 8 * mm, 7 * mm, 32 * mm, fill=1, stroke=0)
        canvas.restoreState()

    def draw_body(self, canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_X, PAGE_H - 13 * mm, PAGE_W - MARGIN_X, PAGE_H - 13 * mm)
        canvas.setFont(FONT, 8.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, PAGE_H - 10 * mm, "景区 AI 数字人智能导览系统")
        canvas.drawRightString(PAGE_W - MARGIN_X, 10 * mm, f"{page_num - 1}")
        canvas.setFillColor(GOLD)
        canvas.rect(MARGIN_X, 8.8 * mm, 12 * mm, 1.2 * mm, fill=1, stroke=0)
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"CNH1", "CNH2", "CNH3"}:
                level = {"CNH1": 0, "CNH2": 1, "CNH3": 2}[style_name]
                text = flowable.getPlainText()
                key = f"h-{self.seq.nextf('heading')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                if level < 2:
                    self.notify("TOCEntry", (level, text, self.page - 1, key))


class Diagram(Flowable):
    def __init__(self, kind: str, width: float = 165 * mm, height: float = 75 * mm):
        super().__init__()
        self.kind = kind
        self.width = width
        self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def _box(self, canvas, x, y, w, h, title, subtitle="", fill=GREEN_LIGHT):
        canvas.setFillColor(fill)
        canvas.setStrokeColor(GREEN)
        canvas.roundRect(x, y, w, h, 4, fill=1, stroke=1)
        canvas.setFillColor(GREEN_DARK)
        canvas.setFont(FONT_BOLD, 8.5)
        canvas.drawCentredString(x + w / 2, y + h - 11, title)
        if subtitle:
            canvas.setFont(FONT, 6.8)
            canvas.setFillColor(MUTED)
            canvas.drawCentredString(x + w / 2, y + 7, subtitle)

    def _arrow(self, canvas, x1, y1, x2, y2):
        canvas.setStrokeColor(GOLD)
        canvas.setFillColor(GOLD)
        canvas.setLineWidth(1.2)
        canvas.line(x1, y1, x2, y2)
        angle = 5
        if abs(x2 - x1) >= abs(y2 - y1):
            direction = 1 if x2 > x1 else -1
            canvas.line(x2, y2, x2 - direction * angle, y2 + 2.5)
            canvas.line(x2, y2, x2 - direction * angle, y2 - 2.5)
        else:
            direction = 1 if y2 > y1 else -1
            canvas.line(x2, y2, x2 + 2.5, y2 - direction * angle)
            canvas.line(x2, y2, x2 - 2.5, y2 - direction * angle)

    def draw(self):
        c = self.canv
        c.saveState()
        if self.kind == "architecture":
            labels = [
                ("游客交互层", "文字 / 语音 / 图片 / 选择"),
                ("智能服务层", "ASR / 情绪 / 意图 / Pipeline"),
                ("知识问答层", "FAQ / 缓存 / RAG / DeepSeek"),
                ("流式表现层", "SSE / TTS / VRM 数字人"),
                ("运营闭环层", "反馈 / 洞察 / 盲区 / 知识维护"),
            ]
            w, h, gap = 136 * mm, 10.5 * mm, 3 * mm
            x = (self.width - w) / 2
            top = self.height - h - 3 * mm
            for index, (title, sub) in enumerate(labels):
                y = top - index * (h + gap)
                self._box(c, x, y, w, h, title, sub, GREEN_LIGHT if index % 2 == 0 else GOLD_LIGHT)
                if index < len(labels) - 1:
                    self._arrow(c, self.width / 2, y, self.width / 2, y - gap + 1)
        elif self.kind == "pipeline":
            labels = ["游客输入", "输入理解", "知识检索", "DeepSeek", "流式 TTS", "数字人呈现"]
            w, h, gap = 23 * mm, 18 * mm, 4 * mm
            total = len(labels) * w + (len(labels) - 1) * gap
            x = (self.width - total) / 2
            y = 35 * mm
            for index, label in enumerate(labels):
                self._box(c, x, y, w, h, label, "", GREEN_LIGHT if index % 2 == 0 else GOLD_LIGHT)
                if index < len(labels) - 1:
                    self._arrow(c, x + w, y + h / 2, x + w + gap, y + h / 2)
                x += w + gap
            c.setFont(FONT, 8)
            c.setFillColor(MUTED)
            c.drawCentredString(self.width / 2, 21 * mm, "FAQ / 缓存 / RAG 约束事实，文本与音频以 SSE 小片段持续返回")
        else:
            labels = ["游客交互", "智能回答", "数字人表达", "行为反馈", "运营分析", "知识改进"]
            w, h, gap = 22 * mm, 16 * mm, 4 * mm
            total = len(labels) * w + (len(labels) - 1) * gap
            x = (self.width - total) / 2
            y = 35 * mm
            starts = []
            for index, label in enumerate(labels):
                starts.append(x)
                self._box(c, x, y, w, h, label, "", GREEN_LIGHT if index % 2 == 0 else GOLD_LIGHT)
                if index < len(labels) - 1:
                    self._arrow(c, x + w, y + h / 2, x + w + gap, y + h / 2)
                x += w + gap
            self._arrow(c, starts[-1] + w / 2, y, starts[-1] + w / 2, 15 * mm)
            c.line(starts[-1] + w / 2, 15 * mm, starts[0] + w / 2, 15 * mm)
            self._arrow(c, starts[0] + w / 2, 15 * mm, starts[0] + w / 2, y)
            c.setFont(FONT, 7.5)
            c.setFillColor(MUTED)
            c.drawCentredString(self.width / 2, 7 * mm, "知识更新重新进入检索与回答，形成持续改进闭环")
        c.restoreState()


def cover_story():
    title = Paragraph(
        "景区 AI 数字人<br/>智能导览系统",
        ParagraphStyle(
            "CoverTitle", fontName=FONT_BOLD, fontSize=29, leading=41,
            textColor=colors.white, alignment=TA_LEFT,
        ),
    )
    subtitle = Paragraph(
        "作品说明文档",
        ParagraphStyle(
            "CoverSub", fontName=FONT, fontSize=18, leading=26,
            textColor=colors.HexColor("#E8D9BA"), alignment=TA_LEFT,
        ),
    )
    meta = Paragraph(
        "多模态交互 · 检索增强生成 · 流式语音 · 三维数字人 · 体验运营闭环",
        ParagraphStyle(
            "CoverMeta", fontName=FONT, fontSize=10.5, leading=18,
            textColor=colors.HexColor("#DCE8E3"), alignment=TA_LEFT,
        ),
    )
    return [
        Spacer(1, 58 * mm),
        Table([["AI SCENIC GUIDE"]], colWidths=[58 * mm], rowHeights=[9 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GOLD),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])),
        Spacer(1, 11 * mm), title, Spacer(1, 7 * mm), subtitle,
        Spacer(1, 18 * mm), meta,
        Spacer(1, 45 * mm),
        Paragraph(
            "比赛演示版 · 基于当前代码库与实际运行配置编制",
            ParagraphStyle("CoverFoot", fontName=FONT, fontSize=9.5, leading=15,
                           textColor=colors.HexColor("#DCE8E3")),
        ),
        NextPageTemplate("Body"), PageBreak(),
    ]


def make_toc():
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName=FONT_BOLD, fontSize=11, leading=17,
                       leftIndent=0, firstLineIndent=0, textColor=GREEN_DARK, spaceBefore=3),
        ParagraphStyle("TOC2", fontName=FONT, fontSize=9.2, leading=14,
                       leftIndent=6 * mm, firstLineIndent=0, textColor=INK),
        ParagraphStyle("TOC3", fontName=FONT, fontSize=8.4, leading=12,
                       leftIndent=12 * mm, firstLineIndent=0, textColor=MUTED),
    ]
    return [Paragraph("目录", styles["TOCTitle"]), toc, PageBreak()]


def table_from_markdown(lines: list[str]):
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return Spacer(1, 1)
    cols = max(len(row) for row in rows)
    normalized = [row + [""] * (cols - len(row)) for row in rows]
    data = []
    for row_index, row in enumerate(normalized):
        style = styles["CNTableHead"] if row_index == 0 else styles["CNTable"]
        data.append([Paragraph(inline_markup(cell) or " ", style) for cell in row])
    available = PAGE_W - 2 * MARGIN_X
    if cols == 5:
        widths = [23 * mm, 26 * mm, 39 * mm, 39 * mm, available - 127 * mm]
    elif cols == 4:
        widths = [38 * mm, 30 * mm, 48 * mm, available - 116 * mm]
    elif cols == 3:
        widths = [40 * mm, 45 * mm, available - 85 * mm]
    else:
        widths = [available / cols] * cols
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def parse_markdown(text: str):
    lines = text.splitlines()
    story = []
    index = 0
    diagram_index = 0
    paragraph_lines: list[str] = []

    def flush_paragraph():
        if paragraph_lines:
            joined = " ".join(item.strip() for item in paragraph_lines).strip()
            if joined:
                story.append(Paragraph(inline_markup(joined), styles["CNBody"]))
            paragraph_lines.clear()

    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith("# "):
            flush_paragraph()
            index += 1
            continue
        if line == "---":
            flush_paragraph()
            story.append(Spacer(1, 2 * mm))
            index += 1
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1)) - 1
            style = styles[{1: "CNH1", 2: "CNH2", 3: "CNH3"}.get(level, "CNH3")]
            story.append(Paragraph(inline_markup(heading.group(2)), style))
            index += 1
            continue
        if line.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(inline_markup(line[2:]), styles["CNQuote"]))
            index += 1
            continue
        if line.startswith("```"):
            flush_paragraph()
            language = line[3:].strip().lower()
            code = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            if language == "mermaid":
                kinds = ["architecture", "pipeline", "loop"]
                kind = kinds[min(diagram_index, len(kinds) - 1)]
                diagram_index += 1
                story.append(KeepTogether([
                    Diagram(kind),
                    Paragraph(
                        ["图 1 系统功能架构", "图 2 核心回答链路", "图 3 游客体验与运营闭环"][diagram_index - 1],
                        styles["CNCaption"],
                    ),
                ]))
            else:
                code_style = ParagraphStyle(
                    "Code", fontName="Courier", fontSize=7.8, leading=11,
                    textColor=colors.HexColor("#E8F0ED"), backColor=GREEN_DARK,
                    borderPadding=8, leftIndent=0, rightIndent=0, spaceAfter=4 * mm,
                )
                story.append(Preformatted(normalize_text("\n".join(code)), code_style))
            continue
        if line.startswith("|") and "|" in line[1:]:
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(table_from_markdown(table_lines))
            story.append(Spacer(1, 4 * mm))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        numbered = re.match(r"^(\d+)\.\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            if bullet:
                prefix, content = "•", bullet.group(1)
            else:
                prefix, content = f"{numbered.group(1)}.", numbered.group(2)
            story.append(Paragraph(f"{prefix}&nbsp;&nbsp;{inline_markup(content)}", styles["CNBullet"]))
            index += 1
            continue
        paragraph_lines.append(raw)
        index += 1
    flush_paragraph()
    return story


def build_pdf():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_text = SOURCE.read_text(encoding="utf-8")
    story = cover_story() + make_toc() + parse_markdown(source_text)
    doc = WorkDocTemplate(str(OUTPUT))
    doc.multiBuild(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
