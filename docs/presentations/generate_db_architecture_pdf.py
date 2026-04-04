#!/usr/bin/env python3
"""Generate LocaNext Database Architecture PDF for the Database Team."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle
from reportlab.graphics import renderPDF

# ── Colors ──────────────────────────────────────────────────────────────────
PG_BLUE = HexColor("#336791")
PG_DARK = HexColor("#1A3A5C")
PG_LIGHT = HexColor("#E8F0F8")
PG_MID = HexColor("#4A8DB7")
ACCENT_GREEN = HexColor("#2E8B57")
ACCENT_ORANGE = HexColor("#D4760A")
ACCENT_RED = HexColor("#C0392B")
TEXT_DARK = HexColor("#1A1A2E")
TEXT_MID = HexColor("#4A4A6A")
LIGHT_GRAY = HexColor("#F5F5F5")
MID_GRAY = HexColor("#CCCCCC")
WHITE = white
BLACK = black

WIDTH, HEIGHT = A4  # 595.27 x 841.89 points


# ── Custom Flowables ────────────────────────────────────────────────────────
class BoxedDiagram(Flowable):
    """A custom flowable for drawing architecture diagrams."""

    def __init__(self, width, height, draw_func):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.draw_func = draw_func

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.draw_func(self.canv, self.width, self.height)


def draw_rounded_rect(c, x, y, w, h, r, fill_color, stroke_color=None, stroke_width=1):
    """Draw a rounded rectangle on the canvas."""
    c.saveState()
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    else:
        c.setStrokeColor(fill_color)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1 if stroke_color else 0)
    c.restoreState()


def draw_arrow(c, x1, y1, x2, y2, color=PG_BLUE, width=1.5, head_size=6):
    """Draw an arrow from (x1,y1) to (x2,y2)."""
    import math
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    c.translate(x2, y2)
    c.rotate(math.degrees(angle))
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(-head_size, head_size / 2)
    p.lineTo(-head_size, -head_size / 2)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.restoreState()


def centered_text(c, x, y, text, font="Helvetica", size=9, color=BLACK):
    """Draw centered text."""
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(color)
    tw = c.stringWidth(text, font, size)
    c.drawString(x - tw / 2, y, text)
    c.restoreState()


def left_text(c, x, y, text, font="Helvetica", size=9, color=BLACK):
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y, text)
    c.restoreState()


# ── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "CoverTitle", parent=styles["Title"],
    fontSize=36, leading=44, textColor=WHITE,
    fontName="Helvetica-Bold", alignment=TA_CENTER,
    spaceAfter=12
)
style_subtitle = ParagraphStyle(
    "CoverSubtitle", parent=styles["Title"],
    fontSize=16, leading=22, textColor=HexColor("#B0D0E8"),
    fontName="Helvetica", alignment=TA_CENTER
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=20, leading=26, textColor=PG_BLUE,
    fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=10,
    borderWidth=0, borderPadding=0
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=13, leading=17, textColor=PG_DARK,
    fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=5
)
style_body = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=9, leading=12.5, textColor=TEXT_DARK,
    fontName="Helvetica", spaceAfter=4, alignment=TA_JUSTIFY
)
style_code = ParagraphStyle(
    "Code", parent=styles["Normal"],
    fontSize=8, leading=11, textColor=TEXT_DARK,
    fontName="Courier", spaceAfter=3, leftIndent=10,
    backColor=LIGHT_GRAY
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_body,
    leftIndent=18, bulletIndent=6, spaceBefore=1, spaceAfter=1,
    bulletFontName="Helvetica", bulletFontSize=9
)
style_small = ParagraphStyle(
    "Small", parent=style_body,
    fontSize=7.5, leading=10, textColor=TEXT_MID
)
style_footer = ParagraphStyle(
    "Footer", parent=styles["Normal"],
    fontSize=7, leading=9, textColor=MID_GRAY,
    fontName="Helvetica", alignment=TA_CENTER
)
style_page_num = ParagraphStyle(
    "PageNum", parent=styles["Normal"],
    fontSize=8, textColor=PG_BLUE, fontName="Helvetica-Bold",
    alignment=TA_RIGHT
)


# ── Table helpers ───────────────────────────────────────────────────────────
def make_table(data, col_widths=None, header_color=PG_BLUE, alt_row=True):
    """Create a styled table."""
    if col_widths:
        t = Table(data, colWidths=col_widths, repeatRows=1)
    else:
        t = Table(data, repeatRows=1)

    base_style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, header_color),
    ]
    if alt_row:
        for i in range(1, len(data)):
            if i % 2 == 0:
                base_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))

    t.setStyle(TableStyle(base_style))
    return t


def section_bar(text):
    """Colored section bar."""
    return Paragraph(
        f'<font color="white"><b>&nbsp;&nbsp;{text}</b></font>',
        ParagraphStyle(
            "SectionBar", parent=style_body,
            fontSize=10, leading=15, backColor=PG_BLUE,
            textColor=WHITE, spaceBefore=8, spaceAfter=6,
            leftIndent=0, rightIndent=0
        )
    )


# ── Page Template ───────────────────────────────────────────────────────────
def on_page(canvas, doc):
    """Header/footer on every page after cover."""
    page_num = doc.page
    if page_num == 1:
        return

    canvas.saveState()
    # Header line
    canvas.setStrokeColor(PG_BLUE)
    canvas.setLineWidth(1.5)
    canvas.line(30, HEIGHT - 30, WIDTH - 30, HEIGHT - 30)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(PG_BLUE)
    canvas.drawString(30, HEIGHT - 25, "LocaNext Database Architecture")
    canvas.drawRightString(WIDTH - 30, HEIGHT - 25, f"Page {page_num}")

    # Footer
    canvas.setStrokeColor(MID_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(30, 30, WIDTH - 30, 30)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MID_GRAY)
    canvas.drawCentredString(WIDTH / 2, 20, "CONFIDENTIAL - Database Team Internal  |  PostgreSQL 15  |  SQLAlchemy ORM  |  Dual-Mode Architecture")
    canvas.restoreState()


# ── Build Document ──────────────────────────────────────────────────────────
def build_pdf():
    output_path = os.path.join(os.path.dirname(__file__), "LocaNext_Database_Architecture.pdf")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=30, rightMargin=30,
        topMargin=45, bottomMargin=45
    )

    story = []
    usable_width = WIDTH - 60  # 535 pts

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER
    # ════════════════════════════════════════════════════════════════════════
    def draw_cover(canv, w, h):
        # Full background
        canv.saveState()
        # Gradient effect via overlapping rects
        for i in range(20):
            frac = i / 20
            r = 0.20 * (1 - frac) + 0.10 * frac
            g = 0.40 * (1 - frac) + 0.23 * frac
            b = 0.57 * (1 - frac) + 0.36 * frac
            canv.setFillColor(Color(r, g, b))
            canv.rect(0, h - (i + 1) * (h / 20), w, h / 20, fill=1, stroke=0)

        # Decorative elements — database cylinder shape
        cx, cy = w / 2, h * 0.72
        ew, eh = 100, 20
        canv.setStrokeColor(HexColor("#5A9FCA"))
        canv.setLineWidth(1.5)
        canv.setFillColor(Color(0.2, 0.35, 0.5, 0.3))
        # Cylinder body
        canv.rect(cx - ew / 2, cy - 60, ew, 60, fill=1, stroke=1)
        canv.ellipse(cx - ew / 2, cy - eh / 2, cx + ew / 2, cy + eh / 2, fill=1, stroke=1)
        canv.setFillColor(Color(0.25, 0.45, 0.65, 0.4))
        canv.ellipse(cx - ew / 2, cy - 60 - eh / 2, cx + ew / 2, cy - 60 + eh / 2, fill=1, stroke=1)
        # Data lines inside cylinder
        canv.setStrokeColor(HexColor("#7FBDE8"))
        canv.setLineWidth(0.5)
        for dy in [-15, -30, -45]:
            canv.line(cx - 35, cy + dy, cx + 35, cy + dy)

        # PostgreSQL elephant silhouette hint (simplified)
        canv.setFillColor(HexColor("#5A9FCA"))
        canv.setFont("Helvetica-Bold", 40)
        canv.drawCentredString(cx, cy - 100, "PG")
        canv.setFont("Helvetica", 10)
        canv.drawCentredString(cx, cy - 118, "PostgreSQL 15")

        # Title
        canv.setFont("Helvetica-Bold", 36)
        canv.setFillColor(WHITE)
        canv.drawCentredString(w / 2, h * 0.42, "LocaNext")
        canv.drawCentredString(w / 2, h * 0.42 - 44, "Database Architecture")

        # Subtitle
        canv.setFont("Helvetica", 16)
        canv.setFillColor(HexColor("#B0D0E8"))
        canv.drawCentredString(w / 2, h * 0.42 - 80, "PostgreSQL Configuration & Performance Guide")

        # Metadata bar
        canv.setFillColor(Color(0, 0, 0, 0.3))
        canv.rect(0, h * 0.18, w, 50, fill=1, stroke=0)
        canv.setFont("Helvetica", 9)
        canv.setFillColor(HexColor("#B0D0E8"))
        canv.drawCentredString(w / 2, h * 0.18 + 30, "Audience: Database Team  |  Classification: Internal  |  Version: 1.0")
        canv.drawCentredString(w / 2, h * 0.18 + 14, "Dual-Mode: PostgreSQL 15 (LAN Multi-User) + SQLite (Offline Single-User)")

        # Bottom
        canv.setFont("Helvetica", 8)
        canv.setFillColor(HexColor("#7A9FBF"))
        canv.drawCentredString(w / 2, 30, "LocaNext Localization Platform  |  2026")

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 700, draw_cover))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 2: ARCHITECTURE OVERVIEW
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Architecture Overview", style_h1))
    story.append(Paragraph(
        "LocaNext employs a <b>dual-mode database architecture</b> that automatically selects "
        "between PostgreSQL 15 (multi-user LAN) and SQLite (single-user offline). The mode is "
        "controlled by <font face='Courier' color='#336791'>DATABASE_MODE=auto</font> which "
        "attempts PostgreSQL connection first, falling back to SQLite on failure.",
        style_body
    ))

    story.append(Spacer(1, 6))

    # Architecture diagram
    def draw_arch_diagram(canv, w, h):
        canv.saveState()
        # Border
        draw_rounded_rect(canv, 0, 0, w, h, 4, WHITE, PG_BLUE, 1)

        # ── LocaNext.exe box ──
        bx, by, bw, bh = 20, h - 55, 130, 35
        draw_rounded_rect(canv, bx, by, bw, bh, 5, PG_BLUE)
        centered_text(canv, bx + bw / 2, by + 13, "LocaNext.exe", "Helvetica-Bold", 10, WHITE)

        # ── Embedded Python Backend ──
        px, py, pw, ph = 190, h - 55, 150, 35
        draw_rounded_rect(canv, px, py, pw, ph, 5, PG_MID)
        centered_text(canv, px + pw / 2, py + 18, "Embedded Python", "Helvetica-Bold", 9, WHITE)
        centered_text(canv, px + pw / 2, py + 6, "FastAPI Backend", "Helvetica", 8, WHITE)

        # Arrow LocaNext -> Backend
        draw_arrow(canv, bx + bw, by + bh / 2, px, py + bh / 2, PG_BLUE, 2)

        # ── SQLAlchemy ORM ──
        sx, sy, sw, sh = 380, h - 55, 130, 35
        draw_rounded_rect(canv, sx, sy, sw, sh, 5, ACCENT_GREEN)
        centered_text(canv, sx + sw / 2, sy + 13, "SQLAlchemy ORM", "Helvetica-Bold", 9, WHITE)

        # Arrow Backend -> ORM
        draw_arrow(canv, px + pw, py + bh / 2, sx, sy + sh / 2, PG_MID, 2)

        # ── Mode Decision Diamond ──
        dx, dy = sx + sw / 2, sy - 50
        canv.setFillColor(ACCENT_ORANGE)
        canv.setStrokeColor(ACCENT_ORANGE)
        p = canv.beginPath()
        p.moveTo(dx, dy + 20)
        p.lineTo(dx + 35, dy)
        p.lineTo(dx, dy - 20)
        p.lineTo(dx - 35, dy)
        p.close()
        canv.drawPath(p, fill=1, stroke=0)
        centered_text(canv, dx, dy - 4, "MODE?", "Helvetica-Bold", 8, WHITE)

        # Arrow ORM -> Decision
        draw_arrow(canv, sx + sw / 2, sy, dx, dy + 20, ACCENT_GREEN, 1.5)

        # ── PostgreSQL box ──
        pgx, pgy, pgw, pgh = 100, 30, 180, 60
        draw_rounded_rect(canv, pgx, pgy, pgw, pgh, 6, PG_BLUE)
        centered_text(canv, pgx + pgw / 2, pgy + 40, "PostgreSQL 15", "Helvetica-Bold", 11, WHITE)
        centered_text(canv, pgx + pgw / 2, pgy + 25, "Multi-User LAN Mode", "Helvetica", 8, HexColor("#B0D0E8"))
        centered_text(canv, pgx + pgw / 2, pgy + 10, "Bundled + Auto-Configured", "Helvetica", 7, HexColor("#8AB8DC"))

        # ── SQLite box ──
        sqx, sqy, sqw, sqh = 340, 30, 160, 60
        draw_rounded_rect(canv, sqx, sqy, sqw, sqh, 6, ACCENT_GREEN)
        centered_text(canv, sqx + sqw / 2, sqy + 40, "SQLite", "Helvetica-Bold", 11, WHITE)
        centered_text(canv, sqx + sqw / 2, sqy + 25, "Single-User Offline", "Helvetica", 8, HexColor("#C8E6D4"))
        centered_text(canv, sqx + sqw / 2, sqy + 10, "WAL Mode + Auto-Fallback", "Helvetica", 7, HexColor("#A8D4B8"))

        # Arrows from decision to databases
        draw_arrow(canv, dx - 35, dy, pgx + pgw / 2, pgy + pgh, PG_BLUE, 1.5)
        draw_arrow(canv, dx + 35, dy, sqx + sqw / 2, sqy + sqh, ACCENT_GREEN, 1.5)

        # Labels on arrows
        left_text(canv, dx - 80, dy - 15, "PG available", "Helvetica-Bold", 7, PG_BLUE)
        left_text(canv, dx + 25, dy - 15, "Fallback", "Helvetica-Bold", 7, ACCENT_GREEN)

        # Features lists
        canv.setFont("Helvetica", 6.5)
        canv.setFillColor(TEXT_MID)
        feats_pg = ["WebSocket sync", "SCRAM-SHA-256", "FTS GIN indexes", "Connection pool"]
        for i, f in enumerate(feats_pg):
            left_text(canv, 15, pgy - 10 - i * 9, f"  {f}", "Helvetica", 6.5, TEXT_MID)

        feats_sq = ["File-based", "Zero config", "WAL mode", "FTS5 full-text"]
        for i, f in enumerate(feats_sq):
            left_text(canv, 335, pgy - 10 - i * 9, f"  {f}", "Helvetica", 6.5, TEXT_MID)

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 200, draw_arch_diagram))
    story.append(Spacer(1, 8))

    story.append(section_bar("Key Design Decisions"))

    decisions = [
        ["Decision", "Choice", "Rationale"],
        ["ORM Layer", "SQLAlchemy 2.0", "Dialect abstraction enables dual-mode with shared models"],
        ["PG Version", "PostgreSQL 15", "Bundled with app, initdb on first launch, no external install"],
        ["Mode Selection", "DATABASE_MODE=auto", "PG preferred, SQLite fallback. Transparent to application code"],
        ["Auth Protocol", "SCRAM-SHA-256", "PG default since v14. No md5 or trust for network connections"],
        ["Offline Storage", "SQLite + WAL", "Concurrent reads, single-writer. Sufficient for single-user"],
        ["Full-Text Search", "GIN (PG) / FTS5 (SQLite)", "Dialect-specific indexes, same query API via ORM"],
    ]
    story.append(make_table(decisions, [85, 110, usable_width - 195]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 3: POSTGRESQL SETUP (8-Step Wizard)
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("PostgreSQL Setup: 8-Step Wizard", style_h1))
    story.append(Paragraph(
        "When LocaNext detects no existing PostgreSQL data directory, the <b>Setup Wizard</b> "
        "executes an 8-step automated provisioning sequence. Each step is <b>idempotent</b> "
        "and records state in <font face='Courier'>setup_state.json</font>, enabling crash recovery.",
        style_body
    ))
    story.append(Spacer(1, 4))

    wizard_data = [
        ["#", "Step", "Action", "Duration", "Crash-Safe"],
        ["1", "preflight_checks", "Validate port 5432 free, disk > 500MB, locate PG binaries", "~0.3s", "Yes"],
        ["2", "init_database", "initdb --encoding=UTF8 --locale=C --auth=scram-sha-256", "2-5s", "Yes (re-init)"],
        ["3", "configure_access", "Write pg_hba.conf + postgresql.conf (listen, SSL, WAL)", "~0.1s", "Yes"],
        ["4", "generate_certificates", "RSA 2048-bit self-signed cert (server.crt + server.key)", "~0.5s", "Yes"],
        ["5", "start_database", "pg_ctl start -w -t 30 (wait for ready)", "3-5s", "Yes (pg_ctl)"],
        ["6", "tune_performance", "Auto-detect HW via psutil, generate tuning SQL", "~1.0s", "Yes"],
        ["7", "create_account", "CREATE USER locanext WITH PASSWORD ... (SCRAM)", "~0.3s", "Yes (IF NOT EXISTS)"],
        ["8", "create_database", "CREATE DATABASE locanext_db + GRANT ALL", "~0.3s", "Yes (IF NOT EXISTS)"],
    ]
    story.append(make_table(wizard_data, [18, 105, 245, 50, 55]))
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "<b>Total Setup Time:</b> 7-13 seconds on typical hardware. All steps run once on first launch, "
        "then state is persisted. Subsequent launches skip directly to <font face='Courier'>start_database</font>.",
        style_body
    ))
    story.append(Spacer(1, 8))

    story.append(section_bar("Crash Recovery State Machine"))

    # State machine diagram
    def draw_state_machine(canv, w, h):
        canv.saveState()
        draw_rounded_rect(canv, 0, 0, w, h, 4, WHITE, MID_GRAY, 0.5)

        states = [
            (30, h - 30, "NOT_STARTED"),
            (150, h - 30, "PREFLIGHT"),
            (270, h - 30, "INIT_DB"),
            (390, h - 30, "CONFIGURE"),
            (30, 25, "CERTS"),
            (150, 25, "STARTING"),
            (270, 25, "TUNING"),
            (390, 25, "COMPLETE"),
        ]

        for i, (x, y, label) in enumerate(states):
            color = ACCENT_GREEN if label == "COMPLETE" else PG_BLUE
            draw_rounded_rect(canv, x, y, 95, 22, 4, color)
            centered_text(canv, x + 47, y + 7, label, "Helvetica-Bold", 7, WHITE)

        # Top row arrows (right)
        for i in range(3):
            x1 = states[i][0] + 95
            y1 = states[i][1] + 11
            x2 = states[i + 1][0]
            y2 = states[i + 1][1] + 11
            draw_arrow(canv, x1, y1, x2, y2, PG_MID, 1, 4)

        # Top-right to bottom-left (wrap)
        draw_arrow(canv, states[3][0] + 47, states[3][1], states[3][0] + 47, 47 + 22, PG_MID, 1, 4)
        # Move left along bottom: the diagram wraps. Draw arrow from CONFIGURE down to CERTS area
        # Actually let's just connect the bottom row
        canv.setStrokeColor(PG_MID)
        canv.setLineWidth(1)
        canv.setDash(3, 2)
        canv.line(states[3][0] + 47, states[3][1], states[3][0] + 47, h - 10)
        canv.line(states[3][0] + 47, h - 10, 10, h - 10)
        canv.line(10, h - 10, 10, 36)
        canv.line(10, 36, states[4][0], 36)
        canv.setDash()

        # Bottom row arrows (right)
        for i in range(4, 7):
            x1 = states[i][0] + 95
            y1 = states[i][1] + 11
            x2 = states[i + 1][0]
            y2 = states[i + 1][1] + 11
            draw_arrow(canv, x1, y1, x2, y2, PG_MID, 1, 4)

        # Crash recovery note
        left_text(canv, w / 2 - 100, h / 2 + 2, "On crash: read setup_state.json", "Helvetica-Bold", 7, ACCENT_ORANGE)
        left_text(canv, w / 2 - 100, h / 2 - 10, "Resume from last completed step", "Helvetica", 7, TEXT_MID)

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 85, draw_state_machine))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>State File Format</b> (<font face='Courier'>setup_state.json</font>):", style_body))
    code_lines = [
        '{',
        '  "current_step": 5,',
        '  "completed_steps": [1, 2, 3, 4],',
        '  "pg_port": 5432,',
        '  "data_dir": "resources/bin/postgresql/data",',
        '  "started_at": "2026-04-02T10:30:00Z"',
        '}',
    ]
    for line in code_lines:
        story.append(Paragraph(line, style_code))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 4: PERFORMANCE TUNING
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Performance Tuning (Auto-Generated)", style_h1))
    story.append(Paragraph(
        "At setup step 6, LocaNext probes hardware via <font face='Courier'>psutil</font> "
        "(RAM, CPU cores, SSD detection) and generates PostgreSQL tuning parameters. "
        "All values are <b>calculated, not hardcoded</b>.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Memory & Parallelism Parameters"))

    perf_data = [
        ["Parameter", "Formula", "8 GB", "16 GB", "32 GB", "64 GB"],
        ["shared_buffers", "RAM / 4", "2 GB", "4 GB", "8 GB", "16 GB"],
        ["effective_cache_size", "RAM * 3/4", "6 GB", "12 GB", "24 GB", "48 GB"],
        ["work_mem", "RAM*1024 / (250*4)", "8 MB", "16 MB", "32 MB", "64 MB"],
        ["maintenance_work_mem", "RAM / 16 (cap 4GB)", "512 MB", "1 GB", "2 GB", "4 GB"],
        ["max_connections", "Fixed", "250", "250", "250", "250"],
        ["max_parallel_workers", "min(8, cores)", "4", "4", "8", "8"],
        ["max_parallel_workers_per_gather", "min(4, cores/2)", "2", "2", "4", "4"],
        ["max_worker_processes", "min(8, cores)", "4", "4", "8", "8"],
    ]
    story.append(make_table(perf_data, [135, 110, 60, 60, 60, 60]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Storage & WAL Configuration"))

    wal_data = [
        ["Parameter", "Value", "Condition", "Rationale"],
        ["random_page_cost", "1.1", "SSD detected", "Default 4.0 for HDD. SSD seeks are near-sequential cost"],
        ["effective_io_concurrency", "200", "SSD detected", "Default 1. NVMe can handle 200+ concurrent reads"],
        ["wal_buffers", "64 MB", "Always", "WAL write buffer. -1 auto = 3% of shared_buffers"],
        ["max_wal_size", "4 GB", "Always", "Checkpoint distance. Larger = fewer checkpoints, more recovery time"],
        ["min_wal_size", "1 GB", "Always", "Prevents WAL segment recycling thrash"],
        ["checkpoint_completion_target", "0.9", "Always", "Spread checkpoint I/O over 90% of interval (reduces spikes)"],
        ["huge_pages", "try", "Always", "Use if OS supports. Falls back to standard pages"],
        ["wal_level", "replica", "Always", "Enables pg_basebackup. Minimal overhead vs 'minimal'"],
    ]
    story.append(make_table(wal_data, [130, 55, 80, usable_width - 265]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Detection Logic"))
    story.append(Paragraph(
        "<b>SSD Detection:</b> <font face='Courier'>psutil.disk_usage()</font> + "
        "<font face='Courier'>/sys/block/*/queue/rotational</font> (Linux) or "
        "<font face='Courier'>wmic diskdrive</font> (Windows). If rotational=0 or "
        "undetectable, assumes SSD (safe default for modern hardware).",
        style_body
    ))
    story.append(Paragraph(
        "<b>RAM Detection:</b> <font face='Courier'>psutil.virtual_memory().total</font>. "
        "Tuning caps at 64 GB to prevent oversized buffers on high-memory servers. "
        "CPU cores via <font face='Courier'>os.cpu_count()</font> with logical core count.",
        style_body
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 5: CONNECTION POOLING
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Connection Pooling", style_h1))
    story.append(Paragraph(
        "LocaNext uses SQLAlchemy's built-in <b>QueuePool</b> for connection management. "
        "Pool parameters are mode-dependent with conservative defaults that scale for LAN deployments.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Pool Configuration by Mode"))

    pool_data = [
        ["Parameter", "Default Mode", "LAN Server Mode", "Effect"],
        ["pool_size", "5", "10", "Persistent connections maintained in pool"],
        ["max_overflow", "10", "20", "Additional connections created under load"],
        ["Total Max Connections", "15", "30", "pool_size + max_overflow"],
        ["pool_pre_ping", "True", "True", "SELECT 1 before checkout (stale detection)"],
        ["pool_recycle", "1800s (30 min)", "1800s (30 min)", "Max connection lifetime before forced close"],
        ["pool_timeout", "20s", "20s", "Wait time for connection before raising error"],
        ["pool_reset_on_return", "rollback", "rollback", "ROLLBACK uncommitted transactions on return"],
    ]
    story.append(make_table(pool_data, [100, 95, 95, usable_width - 290]))
    story.append(Spacer(1, 8))

    # Pool diagram
    def draw_pool_diagram(canv, w, h):
        canv.saveState()
        draw_rounded_rect(canv, 0, 0, w, h, 4, WHITE, MID_GRAY, 0.5)

        # Client requests
        for i in range(4):
            y = h - 25 - i * 30
            draw_rounded_rect(canv, 15, y, 80, 20, 3, PG_LIGHT, PG_BLUE, 0.5)
            centered_text(canv, 55, y + 6, f"Request {i + 1}", "Helvetica", 7, PG_DARK)
            draw_arrow(canv, 95, y + 10, 140, h / 2, PG_MID, 1, 4)

        # Pool box
        draw_rounded_rect(canv, 140, 15, 170, h - 30, 5, PG_LIGHT, PG_BLUE, 1.5)
        centered_text(canv, 225, h - 25, "SQLAlchemy QueuePool", "Helvetica-Bold", 9, PG_BLUE)

        # Pool slots
        labels = ["conn-1 (active)", "conn-2 (active)", "conn-3 (idle)", "conn-4 (idle)", "conn-5 (idle)"]
        colors = [ACCENT_GREEN, ACCENT_GREEN, PG_MID, PG_MID, PG_MID]
        for i, (label, color) in enumerate(zip(labels, colors)):
            y = h - 50 - i * 20
            draw_rounded_rect(canv, 155, y, 140, 16, 3, color)
            centered_text(canv, 225, y + 4, label, "Helvetica", 7, WHITE)

        # Overflow zone
        canv.setDash(3, 2)
        canv.setStrokeColor(ACCENT_ORANGE)
        canv.rect(155, 15, 140, 30, fill=0, stroke=1)
        canv.setDash()
        centered_text(canv, 225, 25, "overflow (0-10)", "Helvetica", 7, ACCENT_ORANGE)

        # PG connections
        draw_rounded_rect(canv, 370, 30, 140, h - 60, 5, PG_BLUE)
        centered_text(canv, 440, h - 40, "PostgreSQL", "Helvetica-Bold", 10, WHITE)
        centered_text(canv, 440, h - 55, "max_connections=250", "Helvetica", 7, HexColor("#B0D0E8"))
        for i in range(5):
            y = h - 75 - i * 18
            draw_rounded_rect(canv, 385, y, 110, 14, 2, PG_DARK)
            centered_text(canv, 440, y + 3, f"backend pid {5000 + i}", "Courier", 6, HexColor("#B0D0E8"))

        # Arrows pool -> PG
        for i in range(3):
            y = h - 50 - i * 20 + 8
            draw_arrow(canv, 310, y, 370, y, PG_MID, 1, 4)

        # pre_ping label
        left_text(canv, 315, h / 2 + 25, "pre_ping", "Helvetica-Bold", 6, ACCENT_GREEN)
        left_text(canv, 315, h / 2 + 15, "SELECT 1", "Courier", 6, ACCENT_GREEN)

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 160, draw_pool_diagram))
    story.append(Spacer(1, 8))

    story.append(section_bar("Connection Lifecycle"))
    story.append(Paragraph(
        "<b>1. Checkout:</b> Request arrives, pool checks for idle connection. "
        "If <font face='Courier'>pool_pre_ping=True</font>, sends SELECT 1 to verify liveness. "
        "Dead connections are discarded and replaced.<br/>"
        "<b>2. Usage:</b> Connection bound to request via async context manager. "
        "SQLAlchemy tracks transaction state.<br/>"
        "<b>3. Return:</b> On request completion, ROLLBACK any uncommitted work, "
        "connection returns to idle pool.<br/>"
        "<b>4. Recycle:</b> After 1800s, connection is closed and a fresh one is created. "
        "Prevents stale server-side state accumulation.",
        style_body
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 6: ACCESS CONTROL
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Access Control (pg_hba.conf)", style_h1))
    story.append(Paragraph(
        "PostgreSQL Host-Based Authentication is auto-generated at setup step 3. "
        "The configuration follows a <b>deny-by-default</b> model with explicit grants.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Authentication Matrix"))

    hba_data = [
        ["Type", "Source", "User", "Database", "Method", "SSL", "Purpose"],
        ["local", "Unix socket", "postgres", "all", "trust", "N/A", "pg_ctl admin (local only)"],
        ["host", "127.0.0.1/32", "postgres", "all", "scram-sha-256", "No", "Local superuser admin"],
        ["host", "127.0.0.1/32", "locanext", "locanext_db", "scram-sha-256", "No", "App service account"],
        ["hostssl", "LAN/24", "locanext", "locanext_db", "scram-sha-256", "Required", "LAN multi-user"],
        ["host", "0.0.0.0/0", "all", "all", "reject", "N/A", "Block everything else"],
    ]
    story.append(make_table(hba_data, [45, 75, 55, 65, 80, 45, usable_width - 365]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Subnet Auto-Detection"))
    story.append(Paragraph(
        "LAN access requires knowing the local subnet. LocaNext uses "
        "<font face='Courier'>detect_lan_ip()</font> which iterates network interfaces via "
        "<font face='Courier'>socket.getaddrinfo()</font>, identifies the primary LAN IP, "
        "and derives a <font face='Courier'>/24</font> subnet mask. Example: if the host IP is "
        "<font face='Courier'>192.168.1.50</font>, the pg_hba.conf entry becomes "
        "<font face='Courier'>hostssl locanext_db locanext 192.168.1.0/24 scram-sha-256</font>.",
        style_body
    ))
    story.append(Spacer(1, 6))

    story.append(section_bar("SSL/TLS Configuration"))
    ssl_data = [
        ["Setting", "Value", "Notes"],
        ["ssl", "on", "Enabled in postgresql.conf at step 3"],
        ["ssl_cert_file", "server.crt", "RSA 2048, self-signed, 10-year validity"],
        ["ssl_key_file", "server.key", "Permissions: 0600 (owner-only read)"],
        ["ssl_ciphers", "HIGH:!aNULL", "Disables null ciphers, requires strong encryption"],
        ["ssl_min_protocol_version", "TLSv1.2", "Disables TLS 1.0/1.1 (deprecated)"],
    ]
    story.append(make_table(ssl_data, [120, 120, usable_width - 240]))
    story.append(Spacer(1, 8))

    # Visual access diagram
    def draw_access_diagram(canv, w, h):
        canv.saveState()
        draw_rounded_rect(canv, 0, 0, w, h, 4, WHITE, MID_GRAY, 0.5)

        # PostgreSQL server in center
        cx = w / 2
        draw_rounded_rect(canv, cx - 60, h / 2 - 25, 120, 50, 6, PG_BLUE)
        centered_text(canv, cx, h / 2 + 8, "PostgreSQL 15", "Helvetica-Bold", 10, WHITE)
        centered_text(canv, cx, h / 2 - 6, "Port 5432", "Helvetica", 8, HexColor("#B0D0E8"))

        # Local access (left)
        draw_rounded_rect(canv, 20, h - 35, 100, 22, 3, ACCENT_GREEN)
        centered_text(canv, 70, h - 28, "Local (trust)", "Helvetica-Bold", 7, WHITE)
        draw_arrow(canv, 120, h - 24, cx - 60, h / 2 + 20, ACCENT_GREEN, 1, 4)

        # 127.0.0.1 (left-bottom)
        draw_rounded_rect(canv, 20, 10, 100, 22, 3, PG_MID)
        centered_text(canv, 70, 17, "127.0.0.1 (SCRAM)", "Helvetica-Bold", 6.5, WHITE)
        draw_arrow(canv, 120, 21, cx - 60, h / 2 - 10, PG_MID, 1, 4)

        # LAN (right-top)
        draw_rounded_rect(canv, w - 130, h - 35, 115, 22, 3, ACCENT_ORANGE)
        centered_text(canv, w - 72, h - 28, "LAN/24 (SSL+SCRAM)", "Helvetica-Bold", 6.5, WHITE)
        draw_arrow(canv, w - 130, h - 24, cx + 60, h / 2 + 20, ACCENT_ORANGE, 1, 4)

        # Internet (right-bottom) — REJECTED
        draw_rounded_rect(canv, w - 120, 10, 105, 22, 3, ACCENT_RED)
        centered_text(canv, w - 67, 17, "0.0.0.0/0 REJECT", "Helvetica-Bold", 7, WHITE)
        canv.setStrokeColor(ACCENT_RED)
        canv.setLineWidth(2)
        canv.setDash(4, 3)
        canv.line(w - 120, 21, cx + 60, h / 2 - 10)
        canv.setDash()
        # X mark
        xm = (w - 120 + cx + 60) / 2
        ym = (21 + h / 2 - 10) / 2
        canv.setLineWidth(2.5)
        canv.line(xm - 6, ym - 6, xm + 6, ym + 6)
        canv.line(xm + 6, ym - 6, xm - 6, ym + 6)

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 100, draw_access_diagram))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 7: SCHEMA & DATA MODEL
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Schema & Data Model", style_h1))
    story.append(Paragraph(
        "LocaNext uses SQLAlchemy ORM with declarative models. Schema changes are applied via "
        "<b>auto-migration</b> on startup (inspects metadata, creates missing tables/columns). "
        "Both PostgreSQL and SQLite share identical model definitions.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Core Tables"))

    schema_data = [
        ["Table", "Rows (Typical)", "Key Columns", "Indexes"],
        ["users", "5-50", "id, username, password_hash, role, is_active", "UNIQUE(username)"],
        ["files", "50-500", "id, name, path, project_id, language, extra_data (JSONB)", "idx_files_project, idx_files_path"],
        ["file_rows", "10K-500K", "id, file_id, string_id, original, translated, status", "idx_rows_file_id, idx_rows_string_id"],
        ["translation_memory", "10K-1M", "id, source, target, src_lang, tgt_lang, score", "FTS GIN(source, target), idx_tm_langs"],
        ["sessions", "10-100", "id, user_id, token, created_at, expires_at", "idx_sessions_token, idx_sessions_user"],
        ["projects", "1-20", "id, name, base_language, target_languages", "UNIQUE(name)"],
        ["merge_history", "100-5K", "id, source_file, target_file, match_type, timestamp", "idx_merge_source"],
        ["audit_log", "1K-100K", "id, user_id, action, entity_type, entity_id, timestamp", "idx_audit_user, idx_audit_time"],
    ]
    story.append(make_table(schema_data, [90, 65, 215, usable_width - 370]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Indexing Strategy"))

    idx_data = [
        ["Index Type", "Engine", "Usage", "Example"],
        ["B-tree", "Both", "Primary keys, foreign keys, unique constraints", "CREATE INDEX idx_rows_file_id ON file_rows(file_id)"],
        ["GIN (tsvector)", "PostgreSQL", "Full-text search on translation columns", "CREATE INDEX idx_fts ON file_rows USING GIN(to_tsvector(...))"],
        ["FTS5", "SQLite", "Full-text search (virtual table)", "CREATE VIRTUAL TABLE fts_rows USING fts5(original, translated)"],
        ["JSONB GIN", "PostgreSQL", "Querying extra_data metadata fields", "CREATE INDEX idx_extra ON files USING GIN(extra_data)"],
        ["Partial", "PostgreSQL", "Status-filtered queries (hot rows)", "WHERE status = 'translated' (avoid scanning confirmed rows)"],
    ]
    story.append(make_table(idx_data, [70, 65, 170, usable_width - 305]))
    story.append(Spacer(1, 8))

    story.append(section_bar("SQLite-Specific Configuration"))
    sqlite_data = [
        ["PRAGMA", "Value", "Effect"],
        ["journal_mode", "WAL", "Write-Ahead Logging: concurrent reads during writes"],
        ["synchronous", "NORMAL", "Balanced durability/performance (not FULL)"],
        ["cache_size", "-64000", "64 MB page cache (negative = KB)"],
        ["foreign_keys", "ON", "Enforce FK constraints (off by default in SQLite)"],
        ["busy_timeout", "5000", "Wait 5s for lock before SQLITE_BUSY"],
        ["temp_store", "MEMORY", "Temp tables in RAM (faster sorts, JOINs)"],
    ]
    story.append(make_table(sqlite_data, [100, 80, usable_width - 180]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 8: MONITORING & HEALTH
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Monitoring & Health", style_h1))
    story.append(Paragraph(
        "LocaNext includes a built-in <b>Admin Dashboard</b> (port 5174) with real-time "
        "database monitoring. Two API endpoints provide comprehensive PostgreSQL health data "
        "with auto-generated recommendations.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("API Endpoints"))

    api_data = [
        ["Endpoint", "Method", "Response", "Refresh"],
        ["  /api/v2/admin/db/stats", "GET", "Connection pool state, query perf, table sizes, active queries", "5s auto"],
        ["  /api/v2/admin/db/health", "GET", "Cache hit ratio, dead tuples, bloat, index usage, recommendations", "5s auto"],
        ["  /api/v2/admin/db/vacuum", "POST", "Triggers VACUUM ANALYZE on specified table", "Manual"],
        ["  /api/v2/admin/db/reindex", "POST", "Reindex specified table or all tables", "Manual"],
    ]
    story.append(make_table(api_data, [130, 45, 250, 50]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Health Check Metrics"))

    health_data = [
        ["Metric", "Query / Source", "Target", "Alert If"],
        ["Cache Hit Ratio", "pg_stat_user_tables: heap_blks_hit / (hit+read)", "> 99%", "< 95%"],
        ["Connection Usage", "pg_stat_activity count / max_connections", "< 20%", "> 80%"],
        ["Dead Tuples", "pg_stat_user_tables: n_dead_tup", "< 1000", "> 10,000"],
        ["Index Hit Ratio", "pg_stat_user_indexes: idx_blks_hit / (hit+read)", "> 99%", "< 95%"],
        ["Long-Running Queries", "pg_stat_activity: state = 'active' AND duration > 30s", "0", "> 0"],
        ["Table Bloat", "pg_stat_user_tables: n_dead_tup / n_live_tup", "< 5%", "> 20%"],
        ["WAL Size", "pg_ls_waldir() total size", "< max_wal_size", "> 3 GB"],
        ["Replication Lag", "pg_stat_replication: sent_lsn - write_lsn", "0", "> 1 MB"],
    ]
    story.append(make_table(health_data, [100, 200, 65, usable_width - 365]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Auto-Generated Recommendations"))
    story.append(Paragraph(
        "The health endpoint returns actionable recommendations based on metric thresholds:",
        style_body
    ))
    recs = [
        "<bullet>&bull;</bullet> <b>Cache hit ratio &lt; 99%:</b> Increase <font face='Courier'>shared_buffers</font>. Current workload exceeds buffer pool.",
        "<bullet>&bull;</bullet> <b>Dead tuples &gt; 10K:</b> Run <font face='Courier'>VACUUM ANALYZE table_name</font>. Autovacuum may be falling behind.",
        "<bullet>&bull;</bullet> <b>Connection usage &gt; 80%:</b> Increase <font face='Courier'>max_connections</font> or review connection leaks.",
        "<bullet>&bull;</bullet> <b>Index hit ratio &lt; 95%:</b> Review query plans with <font face='Courier'>EXPLAIN ANALYZE</font>. Missing indexes.",
        "<bullet>&bull;</bullet> <b>Long-running queries:</b> Identify via <font face='Courier'>pg_stat_activity</font>. Consider <font face='Courier'>statement_timeout</font>.",
    ]
    for r in recs:
        story.append(Paragraph(r, style_bullet))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 9: BACKUP & RECOVERY
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Backup & Recovery", style_h1))
    story.append(Paragraph(
        "LocaNext operates as a <b>desktop application</b> with embedded PostgreSQL. "
        "Backup and recovery strategies differ from traditional server deployments.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Shutdown Procedure"))
    story.append(Paragraph(
        "On application exit, LocaNext executes <font face='Courier'>pg_ctl stop -m fast</font> which:",
        style_body
    ))
    shutdown_items = [
        "<bullet>&bull;</bullet> Disconnects all active clients",
        "<bullet>&bull;</bullet> Rolls back in-progress transactions",
        "<bullet>&bull;</bullet> Flushes WAL to disk",
        "<bullet>&bull;</bullet> Writes checkpoint",
        "<bullet>&bull;</bullet> Removes PID file",
    ]
    for item in shutdown_items:
        story.append(Paragraph(item, style_bullet))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Crash Recovery:</b> If the application crashes without clean shutdown, PostgreSQL's "
        "WAL replay handles recovery automatically on next startup. The WAL ensures no committed "
        "transactions are lost.",
        style_body
    ))
    story.append(Spacer(1, 6))

    story.append(section_bar("Data Directory Layout"))

    dir_data = [
        ["Path (relative to install)", "Contents", "Size"],
        ["resources/bin/postgresql/data/", "PostgreSQL data directory (PGDATA)", "50-500 MB"],
        ["resources/bin/postgresql/data/base/", "Database files (heap, indexes, TOAST)", "Bulk of data"],
        ["resources/bin/postgresql/data/pg_wal/", "Write-Ahead Log segments (16 MB each)", "16 MB - 4 GB"],
        ["resources/bin/postgresql/data/pg_hba.conf", "Host-based authentication rules", "< 1 KB"],
        ["resources/bin/postgresql/data/postgresql.conf", "Server configuration (tuned)", "~25 KB"],
        ["resources/bin/postgresql/data/server.crt", "SSL certificate (self-signed, RSA 2048)", "~1 KB"],
        ["resources/bin/postgresql/data/server.key", "SSL private key (0600 permissions)", "~2 KB"],
        ["resources/bin/postgresql/setup_state.json", "Setup wizard state (crash recovery)", "< 1 KB"],
    ]
    story.append(make_table(dir_data, [200, 220, usable_width - 420]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Setup Wizard Crash Recovery"))
    story.append(Paragraph(
        "The 8-step setup wizard is designed for <b>idempotent re-execution</b>. "
        "Each step checks preconditions before acting:",
        style_body
    ))

    recovery_data = [
        ["Step", "Idempotency Check", "Recovery Action"],
        ["init_database", "PGDATA exists + PG_VERSION file", "Skip if valid, re-init if corrupt"],
        ["configure_access", "Config file timestamps", "Overwrite (safe, declarative)"],
        ["generate_certificates", "Cert files exist + valid", "Regenerate if missing"],
        ["start_database", "pg_ctl status", "Start only if not running"],
        ["tune_performance", "Tuning marker in config", "Re-apply (idempotent ALTER SYSTEM)"],
        ["create_account", "pg_roles lookup", "Skip if user exists (IF NOT EXISTS)"],
        ["create_database", "pg_database lookup", "Skip if DB exists (IF NOT EXISTS)"],
    ]
    story.append(make_table(recovery_data, [100, 180, usable_width - 280]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 10: CAPACITY PLANNING
    # ════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Capacity Planning", style_h1))
    story.append(Paragraph(
        "LocaNext targets <b>small-to-medium localization teams</b> (2-20 users) with a single "
        "server PC acting as the database host. The following analysis is based on the "
        "PEARL reference hardware and typical localization workloads.",
        style_body
    ))
    story.append(Spacer(1, 4))

    story.append(section_bar("Reference Hardware (PEARL)"))

    hw_data = [
        ["Component", "Specification", "PG Impact"],
        ["CPU", "Intel i7-12700 (12C/20T)", "8 parallel workers, 250 connections easily served"],
        ["RAM", "64 GB DDR4", "16 GB shared_buffers, 48 GB effective_cache_size"],
        ["Storage", "NVMe SSD (1 TB)", "random_page_cost=1.1, 200 IO concurrency"],
        ["Network", "1 Gbps Ethernet", "LAN transfer bottleneck for large files"],
        ["OS", "Windows 10/11 Pro", "Bundled PG binaries (Windows x64)"],
    ]
    story.append(make_table(hw_data, [80, 180, usable_width - 260]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Capacity Metrics"))

    cap_data = [
        ["Metric", "Value", "Calculation", "Status"],
        ["Max Concurrent Connections", "250", "max_connections setting", "Fixed"],
        ["Connections at 10 Users", "~12", "pool_size(5) + ~1 overflow per user", "4.8% utilization"],
        ["Connections at 20 Users", "~24", "pool_size per user with sharing", "9.6% utilization"],
        ["Cache Hit Ratio (10 users)", "> 99.7%", "64 GB RAM, ~500 MB dataset", "Excellent"],
        ["Shared Buffers Hit", "> 99%", "16 GB buffers >> working set", "Excellent"],
        ["TM Search (500K entries)", "< 50ms", "GIN index + tsvector", "Within SLA"],
        ["File Load (10K rows)", "< 200ms", "Bulk COPY + client pagination", "Within SLA"],
        ["Concurrent File Edits", "20+", "Row-level locking, no table locks", "No contention"],
    ]
    story.append(make_table(cap_data, [130, 75, 190, usable_width - 395]))
    story.append(Spacer(1, 8))

    story.append(section_bar("Bottleneck Analysis"))

    # Bottleneck diagram
    def draw_bottleneck(canv, w, h):
        canv.saveState()
        draw_rounded_rect(canv, 0, 0, w, h, 4, WHITE, MID_GRAY, 0.5)

        bars = [
            ("CPU (i7-12700)", 8, ACCENT_GREEN, "8% at 10 users"),
            ("RAM (64 GB)", 12, ACCENT_GREEN, "12% buffer utilization"),
            ("Disk I/O (NVMe)", 5, ACCENT_GREEN, "5% sustained throughput"),
            ("Network (1 Gbps)", 35, ACCENT_ORANGE, "35% during bulk transfers"),
            ("Connections (250)", 5, ACCENT_GREEN, "4.8% at 10 users"),
        ]

        bar_h = 16
        y_start = h - 25
        bar_max_w = w - 230

        for i, (label, pct, color, detail) in enumerate(bars):
            y = y_start - i * (bar_h + 8)
            # Label
            left_text(canv, 10, y + 4, label, "Helvetica-Bold", 7.5, TEXT_DARK)
            # Bar background
            bx = 130
            draw_rounded_rect(canv, bx, y, bar_max_w, bar_h, 3, LIGHT_GRAY)
            # Bar fill
            fill_w = max(bar_max_w * pct / 100, 10)
            draw_rounded_rect(canv, bx, y, fill_w, bar_h, 3, color)
            # Percentage
            centered_text(canv, bx + fill_w + 18, y + 4, f"{pct}%", "Helvetica-Bold", 7, color)
            # Detail
            left_text(canv, bx + bar_max_w + 35, y + 4, detail, "Helvetica", 6.5, TEXT_MID)

        canv.restoreState()

    story.append(BoxedDiagram(usable_width, 135, draw_bottleneck))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Conclusion:</b> The primary bottleneck is <b>network I/O</b> during large file "
        "transfers (XML files can exceed 50 MB). Database operations are well within capacity. "
        "For teams larger than 20 users, consider increasing <font face='Courier'>pool_size</font> "
        "to 10 and <font face='Courier'>max_overflow</font> to 20 (LAN Server Mode defaults).",
        style_body
    ))
    story.append(Spacer(1, 6))

    story.append(section_bar("Scaling Recommendations"))
    scaling_items = [
        "<bullet>&bull;</bullet> <b>10-20 users:</b> Default configuration sufficient. Monitor cache hit ratio weekly.",
        "<bullet>&bull;</bullet> <b>20-50 users:</b> Enable LAN Server Mode (pool_size=10). Consider dedicated server PC.",
        "<bullet>&bull;</bullet> <b>50+ users:</b> External PostgreSQL server recommended. PgBouncer for connection pooling.",
        "<bullet>&bull;</bullet> <b>Multi-site:</b> Logical replication between offices. Each site runs own LocaNext instance.",
    ]
    for item in scaling_items:
        story.append(Paragraph(item, style_bullet))

    # ── Build PDF ──
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return output_path


if __name__ == "__main__":
    path = build_pdf()
    print(f"PDF generated: {path}")
    print(f"Size: {os.path.getsize(path):,} bytes")
