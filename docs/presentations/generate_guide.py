#!/usr/bin/env python3
"""Generate LocaNext Localization Team Guide PDF."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Polygon
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
import os

# ── Colors ──────────────────────────────────────────────────────────────────
DARK_NAVY = HexColor("#1a1a2e")
MEDIUM_NAVY = HexColor("#16213e")
DEEP_BLUE = HexColor("#0f3460")
ACCENT_BLUE = HexColor("#4361ee")
LIGHT_BLUE = HexColor("#e3f2fd")
PASTEL_BLUE = HexColor("#bbdefb")
PASTEL_GREEN = HexColor("#c8e6c9")
PASTEL_YELLOW = HexColor("#fff9c4")
PASTEL_ORANGE = HexColor("#ffe0b2")
PASTEL_PURPLE = HexColor("#e1bee7")
PASTEL_RED = HexColor("#ffcdd2")
SOFT_GREEN = HexColor("#43a047")
WARM_ORANGE = HexColor("#ef6c00")
TEXT_DARK = HexColor("#333333")
TEXT_LIGHT = HexColor("#666666")
HEADER_BG = HexColor("#e8eaf6")
WHITE = white
BG_CREAM = HexColor("#fafafa")

WIDTH, HEIGHT = A4  # 595.27 x 841.89 points


# ── Custom Flowables ────────────────────────────────────────────────────────

class GradientBackground(Flowable):
    """Full-page gradient background for cover."""
    def __init__(self, width, height, color1, color2):
        super().__init__()
        self.bg_width = width
        self.bg_height = height
        self.color1 = color1
        self.color2 = color2

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        canvas = self.canv
        steps = 100
        for i in range(steps):
            t = i / steps
            r = self.color1.red + (self.color2.red - self.color1.red) * t
            g = self.color1.green + (self.color2.green - self.color1.green) * t
            b = self.color1.blue + (self.color2.blue - self.color1.blue) * t
            canvas.setFillColor(Color(r, g, b))
            y = self.bg_height - (i + 1) * (self.bg_height / steps)
            canvas.rect(-100, y - 450, self.bg_width + 200, self.bg_height / steps + 1, stroke=0, fill=1)


class ColoredBox(Flowable):
    """A colored rounded rectangle containing text."""
    def __init__(self, text, bg_color, text_color=TEXT_DARK, width=None, icon="", font_size=13, bold_title=""):
        super().__init__()
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.box_width = width or (WIDTH - 100)
        self.icon = icon
        self.font_size = font_size
        self.bold_title = bold_title
        self._height = 0

    def wrap(self, availWidth, availHeight):
        # Estimate height based on text length
        chars_per_line = int(self.box_width / (self.font_size * 0.5))
        lines = max(1, len(self.text) / max(chars_per_line, 1)) + 1
        if self.bold_title:
            lines += 1.2
        self._height = max(50, lines * (self.font_size + 6) + 24)
        return (self.box_width, self._height)

    def draw(self):
        canvas = self.canv
        # Rounded rectangle
        canvas.setFillColor(self.bg_color)
        canvas.roundRect(0, 0, self.box_width, self._height, 10, stroke=0, fill=1)
        # Border
        canvas.setStrokeColor(Color(0, 0, 0, 0.08))
        canvas.setLineWidth(0.5)
        canvas.roundRect(0, 0, self.box_width, self._height, 10, stroke=1, fill=0)

        # Icon
        x_offset = 15
        if self.icon:
            canvas.setFont("Helvetica", self.font_size + 4)
            canvas.setFillColor(self.text_color)
            canvas.drawString(x_offset, self._height - 24, self.icon)
            x_offset = 40

        # Bold title
        y_pos = self._height - 24
        if self.bold_title:
            canvas.setFont("Helvetica-Bold", self.font_size + 1)
            canvas.setFillColor(self.text_color)
            canvas.drawString(x_offset, y_pos, self.bold_title)
            y_pos -= self.font_size + 8

        # Text (with word wrap)
        canvas.setFont("Helvetica", self.font_size)
        canvas.setFillColor(self.text_color)
        words = self.text.split()
        line = ""
        max_w = self.box_width - x_offset - 15
        for word in words:
            test = line + " " + word if line else word
            if canvas.stringWidth(test, "Helvetica", self.font_size) < max_w:
                line = test
            else:
                canvas.drawString(x_offset, y_pos, line)
                y_pos -= self.font_size + 5
                line = word
        if line:
            canvas.drawString(x_offset, y_pos, line)


class StepBox(Flowable):
    """A numbered step with icon and description."""
    def __init__(self, number, title, description, color, width=None):
        super().__init__()
        self.number = number
        self.title = title
        self.description = description
        self.color = color
        self.box_width = width or (WIDTH - 100)

    def wrap(self, availWidth, availHeight):
        return (self.box_width, 65)

    def draw(self):
        canvas = self.canv
        # Background
        canvas.setFillColor(self.color)
        canvas.roundRect(0, 0, self.box_width, 60, 8, stroke=0, fill=1)

        # Number circle
        canvas.setFillColor(DARK_NAVY)
        canvas.circle(30, 30, 18, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawCentredString(30, 24, str(self.number))

        # Title
        canvas.setFillColor(DARK_NAVY)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(58, 38, self.title)

        # Description
        canvas.setFillColor(TEXT_DARK)
        canvas.setFont("Helvetica", 11)
        canvas.drawString(58, 18, self.description)


class LayoutDiagram(Flowable):
    """Simplified screen layout diagram."""
    def __init__(self):
        super().__init__()

    def wrap(self, availWidth, availHeight):
        return (WIDTH - 100, 280)

    def draw(self):
        c = self.canv
        w = WIDTH - 100
        h = 270

        # Outer frame (app window)
        c.setStrokeColor(DARK_NAVY)
        c.setLineWidth(2)
        c.setFillColor(HexColor("#f5f5f5"))
        c.roundRect(0, 0, w, h, 8, stroke=1, fill=1)

        # Title bar
        c.setFillColor(DARK_NAVY)
        c.rect(0, h - 30, w, 30, stroke=0, fill=1)
        # Round top corners manually
        c.roundRect(0, h - 35, w, 35, 8, stroke=0, fill=1)
        c.rect(0, h - 30, w, 5, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 22, "LocaNext - Your Translation Workspace")

        # Left panel - File Explorer
        panel_top = h - 40
        left_w = w * 0.22
        c.setFillColor(HexColor("#e8f5e9"))
        c.roundRect(8, 8, left_w, panel_top - 8, 6, stroke=0, fill=1)
        c.setStrokeColor(SOFT_GREEN)
        c.setLineWidth(2)
        c.roundRect(8, 8, left_w, panel_top - 8, 6, stroke=1, fill=0)
        c.setFillColor(SOFT_GREEN)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(8 + left_w / 2, panel_top - 22, "File Explorer")
        # File icons
        c.setFont("Helvetica", 9)
        c.setFillColor(TEXT_DARK)
        files = ["  > Project A", "     game_text.xml", "     ui_strings.xml", "  > Project B", "     dialogs.xml"]
        for i, f in enumerate(files):
            c.drawString(16, panel_top - 42 - i * 16, f)

        # Center panel - Translation Grid
        center_x = 8 + left_w + 8
        center_w = w * 0.52
        c.setFillColor(LIGHT_BLUE)
        c.roundRect(center_x, 8, center_w, panel_top - 8, 6, stroke=0, fill=1)
        c.setStrokeColor(ACCENT_BLUE)
        c.setLineWidth(2)
        c.roundRect(center_x, 8, center_w, panel_top - 8, 6, stroke=1, fill=0)
        c.setFillColor(ACCENT_BLUE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(center_x + center_w / 2, panel_top - 22, "Translation Grid (Main Work Area)")

        # Grid lines
        c.setStrokeColor(HexColor("#90caf9"))
        c.setLineWidth(0.5)
        grid_top = panel_top - 35
        # Header
        c.setFillColor(HexColor("#1565c0"))
        c.rect(center_x + 6, grid_top - 2, center_w - 12, 18, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        cols = ["ID", "Korean", "English", "Japanese", "Status"]
        col_w = (center_w - 12) / 5
        for i, col in enumerate(cols):
            c.drawCentredString(center_x + 12 + i * col_w + col_w / 2, grid_top + 3, col)
        # Rows
        c.setFont("Helvetica", 8)
        rows_data = [
            ["001", "안녕하세요", "Hello", "こんにちは", "Done"],
            ["002", "게임 시작", "Start Game", "ゲーム開始", "Done"],
            ["003", "설정", "Settings", "設定", "Review"],
            ["004", "저장하기", "Save", "セーブ", "New"],
            ["005", "불러오기", "Load", "ロード", "New"],
        ]
        status_colors = {"Done": PASTEL_GREEN, "Review": PASTEL_YELLOW, "New": PASTEL_BLUE}
        for ri, row in enumerate(rows_data):
            y = grid_top - 18 - ri * 17
            # Alternating row bg
            if ri % 2 == 0:
                c.setFillColor(HexColor("#e3f2fd"))
            else:
                c.setFillColor(WHITE)
            c.rect(center_x + 6, y - 2, center_w - 12, 17, stroke=0, fill=1)
            c.setFillColor(TEXT_DARK)
            for ci, cell in enumerate(row):
                if ci == 4:  # Status column
                    sc = status_colors.get(cell, PASTEL_BLUE)
                    c.setFillColor(sc)
                    c.roundRect(center_x + 12 + ci * col_w + 2, y, col_w - 8, 13, 3, stroke=0, fill=1)
                    c.setFillColor(TEXT_DARK)
                    c.drawCentredString(center_x + 12 + ci * col_w + col_w / 2, y + 2, cell)
                else:
                    c.drawCentredString(center_x + 12 + ci * col_w + col_w / 2, y + 2, cell)

        # Right panel - Details
        right_x = center_x + center_w + 8
        right_w = w - right_x - 8
        c.setFillColor(HexColor("#fff3e0"))
        c.roundRect(right_x, 8, right_w, panel_top - 8, 6, stroke=0, fill=1)
        c.setStrokeColor(WARM_ORANGE)
        c.setLineWidth(2)
        c.roundRect(right_x, 8, right_w, panel_top - 8, 6, stroke=1, fill=0)
        c.setFillColor(WARM_ORANGE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(right_x + right_w / 2, panel_top - 22, "Details")
        c.setFont("Helvetica", 8)
        c.setFillColor(TEXT_DARK)
        details = ["ID: 001", "File: game_text", "Category: UI", "Status: Done", "", "TM Match:", "  95% similar"]
        for i, d in enumerate(details):
            c.drawString(right_x + 8, panel_top - 40 - i * 14, d)


class NetworkDiagram(Flowable):
    """Simple network diagram showing multiple PCs connected to server."""
    def __init__(self):
        super().__init__()

    def wrap(self, availWidth, availHeight):
        return (WIDTH - 100, 220)

    def draw(self):
        c = self.canv
        w = WIDTH - 100
        h = 210

        # Server (center)
        srv_x = w / 2
        srv_y = h - 50

        # Server box
        c.setFillColor(DEEP_BLUE)
        c.roundRect(srv_x - 50, srv_y - 25, 100, 50, 8, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(srv_x, srv_y + 5, "LocaNext")
        c.drawCentredString(srv_x, srv_y - 12, "Server")

        # Decorative glow
        c.setFillColor(Color(0.263, 0.380, 0.933, 0.15))
        c.circle(srv_x, srv_y, 55, stroke=0, fill=1)
        c.setFillColor(DEEP_BLUE)
        c.roundRect(srv_x - 50, srv_y - 25, 100, 50, 8, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(srv_x, srv_y + 5, "LocaNext")
        c.drawCentredString(srv_x, srv_y - 12, "Server")

        # Client computers
        clients = [
            (w * 0.15, 50, "Translator A", "(Korean)"),
            (w * 0.38, 30, "Translator B", "(Japanese)"),
            (w * 0.62, 30, "Translator C", "(Chinese)"),
            (w * 0.85, 50, "Manager", "(Review)"),
        ]

        for cx, cy, name, role in clients:
            # Connection line
            c.setStrokeColor(ACCENT_BLUE)
            c.setLineWidth(2)
            c.setDash(4, 3)
            c.line(cx, cy + 22, srv_x, srv_y - 28)
            c.setDash()

            # Arrow head (small dot at server end)
            c.setFillColor(ACCENT_BLUE)
            c.circle(srv_x + (cx - srv_x) * 0.15, srv_y - 28 + (cy + 22 - srv_y + 28) * 0.15, 3, stroke=0, fill=1)

            # Computer box
            c.setFillColor(HexColor("#e8eaf6"))
            c.roundRect(cx - 40, cy - 15, 80, 38, 6, stroke=0, fill=1)
            c.setStrokeColor(ACCENT_BLUE)
            c.setLineWidth(1)
            c.roundRect(cx - 40, cy - 15, 80, 38, 6, stroke=1, fill=0)

            # Monitor icon (small)
            c.setFillColor(DARK_NAVY)
            c.rect(cx - 12, cy + 8, 24, 14, stroke=0, fill=1)
            c.setFillColor(HexColor("#64b5f6"))
            c.rect(cx - 10, cy + 10, 20, 10, stroke=0, fill=1)
            # Stand
            c.setFillColor(DARK_NAVY)
            c.rect(cx - 3, cy + 4, 6, 4, stroke=0, fill=1)

            # Name
            c.setFillColor(TEXT_DARK)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(cx, cy - 5, name)
            c.setFont("Helvetica", 7)
            c.setFillColor(TEXT_LIGHT)
            c.drawCentredString(cx, cy - 14, role)

        # "Real-time sync" label
        c.setFillColor(SOFT_GREEN)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(w / 2, srv_y - 48, "Real-time sync -- everyone sees changes instantly!")


class LanguageFlow(Flowable):
    """Visual: Computer -> LocaNext -> Multiple languages."""
    def __init__(self):
        super().__init__()

    def wrap(self, availWidth, availHeight):
        return (WIDTH - 100, 140)

    def draw(self):
        c = self.canv
        w = WIDTH - 100

        # Game file (left)
        c.setFillColor(PASTEL_ORANGE)
        c.roundRect(10, 40, 100, 60, 8, stroke=0, fill=1)
        c.setFillColor(DARK_NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(60, 80, "Game Text")
        c.setFont("Helvetica", 9)
        c.drawCentredString(60, 62, "(XML files)")

        # Arrow
        c.setStrokeColor(ACCENT_BLUE)
        c.setLineWidth(3)
        c.line(115, 70, 160, 70)
        # Arrowhead
        c.setFillColor(ACCENT_BLUE)
        p = c.beginPath()
        p.moveTo(160, 75); p.lineTo(170, 70); p.lineTo(160, 65); p.close()
        c.drawPath(p, stroke=0, fill=1)

        # LocaNext (center)
        c.setFillColor(DEEP_BLUE)
        c.roundRect(175, 30, 130, 80, 10, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(240, 78, "LocaNext")
        c.setFont("Helvetica", 9)
        c.drawCentredString(240, 58, "Translate &")
        c.drawCentredString(240, 45, "Manage")

        # Arrow right
        c.setStrokeColor(ACCENT_BLUE)
        c.setLineWidth(3)
        c.line(310, 70, 355, 70)
        c.setFillColor(ACCENT_BLUE)
        p = c.beginPath()
        p.moveTo(355, 75); p.lineTo(365, 70); p.lineTo(355, 65); p.close()
        c.drawPath(p, stroke=0, fill=1)

        # Language boxes (right)
        langs = [
            ("KR", "Korean", HexColor("#ffcdd2")),
            ("EN", "English", HexColor("#bbdefb")),
            ("JP", "Japanese", HexColor("#c8e6c9")),
            ("ZH", "Chinese", HexColor("#fff9c4")),
        ]
        for i, (code, name, color) in enumerate(langs):
            y = 100 - i * 28
            c.setFillColor(color)
            c.roundRect(370, y, 110, 24, 6, stroke=0, fill=1)
            c.setFillColor(DARK_NAVY)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(378, y + 7, f"{code}")
            c.setFont("Helvetica", 9)
            c.drawString(400, y + 7, f"  {name}")


class BulletPoint(Flowable):
    """A colored bullet point with text."""
    def __init__(self, text, bullet_color=ACCENT_BLUE, font_size=13, indent=30, sub_text=""):
        super().__init__()
        self.text = text
        self.bullet_color = bullet_color
        self.font_size = font_size
        self.indent = indent
        self.sub_text = sub_text

    def wrap(self, availWidth, availHeight):
        h = self.font_size + 12
        if self.sub_text:
            h += self.font_size + 2
        return (WIDTH - 100, h)

    def draw(self):
        c = self.canv
        y = self.font_size + 4
        if self.sub_text:
            y += self.font_size

        # Bullet circle
        c.setFillColor(self.bullet_color)
        c.circle(self.indent - 12, y - 3, 5, stroke=0, fill=1)

        # Text
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", self.font_size)
        c.drawString(self.indent, y - 6, self.text)

        if self.sub_text:
            c.setFont("Helvetica", self.font_size - 2)
            c.setFillColor(TEXT_LIGHT)
            c.drawString(self.indent + 10, y - 6 - self.font_size - 2, self.sub_text)


class FeatureCard(Flowable):
    """A feature card with icon, title, and description."""
    def __init__(self, icon, title, description, color, width=None):
        super().__init__()
        self.icon = icon
        self.title = title
        self.description = description
        self.color = color
        self.card_width = width or (WIDTH - 100)

    def wrap(self, availWidth, availHeight):
        return (self.card_width, 55)

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(self.color)
        c.roundRect(0, 0, self.card_width, 50, 8, stroke=0, fill=1)

        # Icon circle
        c.setFillColor(DARK_NAVY)
        c.circle(28, 25, 16, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(28, 19, self.icon)

        # Title
        c.setFillColor(DARK_NAVY)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(52, 32, self.title)

        # Description (word-wrapped)
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 10)
        # Simple wrap
        words = self.description.split()
        line = ""
        max_w = self.card_width - 60
        y = 16
        for word in words:
            test = line + " " + word if line else word
            if c.stringWidth(test, "Helvetica", 10) < max_w:
                line = test
            else:
                c.drawString(52, y, line)
                y -= 13
                line = word
        if line:
            c.drawString(52, y, line)


# ── Page Templates ──────────────────────────────────────────────────────────

def page_footer(canvas_obj, doc):
    """Standard footer with page number and LocaNext branding."""
    canvas_obj.saveState()
    # Footer line
    canvas_obj.setStrokeColor(HexColor("#e0e0e0"))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(50, 40, WIDTH - 50, 40)
    # Page number
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.setFillColor(TEXT_LIGHT)
    canvas_obj.drawCentredString(WIDTH / 2, 25, f"Page {doc.page}")
    # Branding
    canvas_obj.drawString(50, 25, "LocaNext Guide")
    canvas_obj.drawRightString(WIDTH - 50, 25, "v26.x (2026)")
    canvas_obj.restoreState()


def cover_page(canvas_obj, doc):
    """Cover page with gradient background."""
    canvas_obj.saveState()

    # Gradient background
    steps = 120
    for i in range(steps):
        t = i / steps
        r = DARK_NAVY.red + (MEDIUM_NAVY.red - DARK_NAVY.red) * t
        g = DARK_NAVY.green + (MEDIUM_NAVY.green - DARK_NAVY.green) * t
        b = DARK_NAVY.blue + (MEDIUM_NAVY.blue - DARK_NAVY.blue) * t
        canvas_obj.setFillColor(Color(r, g, b))
        y = HEIGHT - (i + 1) * (HEIGHT / steps)
        canvas_obj.rect(0, y, WIDTH, HEIGHT / steps + 1, stroke=0, fill=1)

    # Decorative circles (semi-transparent blue)
    canvas_obj.setFillColor(Color(0.263, 0.380, 0.933, 0.12))
    canvas_obj.circle(WIDTH * 0.8, HEIGHT * 0.7, 120, stroke=0, fill=1)
    canvas_obj.circle(WIDTH * 0.2, HEIGHT * 0.3, 80, stroke=0, fill=1)
    canvas_obj.circle(WIDTH * 0.9, HEIGHT * 0.2, 60, stroke=0, fill=1)

    # Decorative line
    canvas_obj.setStrokeColor(Color(0.263, 0.380, 0.933, 0.25))
    canvas_obj.setLineWidth(2)
    canvas_obj.line(WIDTH * 0.15, HEIGHT * 0.55, WIDTH * 0.85, HEIGHT * 0.55)

    # LocaNext logo text
    canvas_obj.setFillColor(ACCENT_BLUE)
    canvas_obj.setFont("Helvetica-Bold", 18)
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.72, "~ LOCANEXT ~")

    # Title
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 38)
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.62, "LocaNext")

    # Subtitle line 1
    canvas_obj.setFont("Helvetica", 20)
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.56, "Your Localization Companion")

    # Decorative line
    canvas_obj.setStrokeColor(ACCENT_BLUE)
    canvas_obj.setLineWidth(2)
    canvas_obj.line(WIDTH * 0.3, HEIGHT * 0.52, WIDTH * 0.7, HEIGHT * 0.52)

    # Second subtitle
    canvas_obj.setFont("Helvetica", 16)
    canvas_obj.setFillColor(HexColor("#aaaaee"))
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.47, "A Simple Guide for the Localization Team")

    # Version
    canvas_obj.setFont("Helvetica", 13)
    canvas_obj.setFillColor(HexColor("#8888bb"))
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.40, "Version 26.x  |  2026")

    # Language icons at bottom
    langs = [
        ("KR", HexColor("#ffcdd2")),
        ("EN", HexColor("#bbdefb")),
        ("JP", HexColor("#c8e6c9")),
        ("ZH", HexColor("#fff9c4")),
        ("DE", HexColor("#e1bee7")),
        ("FR", HexColor("#ffe0b2")),
    ]
    start_x = WIDTH / 2 - (len(langs) * 52) / 2
    for i, (code, color) in enumerate(langs):
        x = start_x + i * 52
        canvas_obj.setFillColor(color)
        canvas_obj.roundRect(x, HEIGHT * 0.28, 42, 28, 6, stroke=0, fill=1)
        canvas_obj.setFillColor(DARK_NAVY)
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawCentredString(x + 21, HEIGHT * 0.28 + 8, code)

    # Footer
    canvas_obj.setFillColor(HexColor("#666699"))
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawCentredString(WIDTH / 2, HEIGHT * 0.08, "Confidential - For Internal Use Only")

    canvas_obj.restoreState()


# ── Build Document ──────────────────────────────────────────────────────────

def build_pdf():
    output_path = os.path.join(os.path.dirname(__file__), "LocaNext_Localization_Team_Guide.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=60,
        bottomMargin=60,
        leftMargin=50,
        rightMargin=50,
    )

    content_width = WIDTH - 100
    story = []

    # ── PAGE 1: Cover (blank content, drawn by cover_page callback) ──
    story.append(Spacer(1, 1))
    story.append(PageBreak())

    # ── PAGE 2: What is LocaNext? ──
    story.append(Spacer(1, 10))

    # Page title
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>What is LocaNext?</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=0, leading=30)
    ))
    # Decorative line under title
    story.append(Spacer(1, 8))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=ACCENT_BLUE, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        '<font color="#666666" size="13">LocaNext is your all-in-one tool for game localization. '
        'Here is what it does for you:</font>',
        ParagraphStyle("intro", spaceAfter=20)
    ))

    # Three bullet points
    bullets = [
        ("LocaNext helps you translate game text into multiple languages.",
         ACCENT_BLUE, "Work with Korean, English, Japanese, Chinese, and more."),
        ("Multiple people can work on the same file at the same time.",
         SOFT_GREEN, "No more emailing files back and forth!"),
        ("It automatically finds similar translations you have done before.",
         WARM_ORANGE, "Translation Memory saves you time and keeps things consistent."),
    ]
    for text, color, sub in bullets:
        story.append(BulletPoint(text, bullet_color=color, sub_text=sub))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 25))

    # Visual: Language flow diagram
    story.append(Paragraph(
        '<font color="#1a1a2e" size="14"><b>How it works:</b></font>',
        ParagraphStyle("h2", spaceAfter=12)
    ))
    story.append(LanguageFlow())

    story.append(Spacer(1, 30))

    # Info box
    story.append(ColoredBox(
        "You do NOT need to be a computer expert to use LocaNext. "
        "It is designed to be simple and intuitive. If you can use a spreadsheet, "
        "you can use LocaNext!",
        PASTEL_BLUE,
        icon="i",
        bold_title="Good news!"
    ))

    story.append(PageBreak())

    # ── PAGE 3: Getting Started ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>Getting Started</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2, leading=30)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=SOFT_GREEN, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        '<font color="#666666" size="13">Follow these three simple steps to get started:</font>',
        ParagraphStyle("intro", spaceAfter=20)
    ))

    # Steps
    steps = [
        (1, "Open LocaNext", "Double-click LocaNext.exe on your desktop to start the application.", PASTEL_GREEN),
        (2, "Log In", "Enter your username and password. Ask your admin if you do not have one.", PASTEL_BLUE),
        (3, "Open a File", "Click File > Open, or simply drag and drop an XML file into the window.", PASTEL_GREEN),
    ]
    for num, title, desc, color in steps:
        story.append(StepBox(num, title, desc, color, content_width))
        story.append(Spacer(1, 12))

    story.append(Spacer(1, 20))

    # Tips box
    story.append(ColoredBox(
        "After logging in, you will see the main screen with your files on the left "
        "and the translation grid in the center. If this is your first time, ask your "
        "administrator to give you access to the right project files.",
        PASTEL_YELLOW,
        icon="!",
        bold_title="First-time tip"
    ))

    story.append(Spacer(1, 25))

    # Login reminder box
    story.append(ColoredBox(
        "Your login keeps your work safe. LocaNext tracks who made each change, "
        "so your team always knows who translated what. Never share your password.",
        PASTEL_PURPLE,
        icon="*",
        bold_title="Why do I need to log in?"
    ))

    story.append(PageBreak())

    # ── PAGE 4: The Main Screen ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>The Main Screen</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2, leading=30)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=WARM_ORANGE, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        '<font color="#666666" size="13">The main screen has three areas. '
        'Here is what each area does:</font>',
        ParagraphStyle("intro", spaceAfter=15)
    ))

    # Layout diagram
    story.append(LayoutDiagram())

    story.append(Spacer(1, 20))

    # Legend boxes
    legend_data = [
        ("File Explorer (Left)", "Browse your project folders and files. Click a file to open it.", PASTEL_GREEN, SOFT_GREEN),
        ("Translation Grid (Center)", "This is where you do your work! Each row is a text entry to translate.", PASTEL_BLUE, ACCENT_BLUE),
        ("Details Panel (Right)", "Shows extra information about the selected row, including Translation Memory matches.", PASTEL_ORANGE, WARM_ORANGE),
    ]
    for title, desc, bg, border in legend_data:
        story.append(ColoredBox(desc, bg, bold_title=title, font_size=11))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ── PAGE 5: How to Translate ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>How to Translate</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2, leading=30)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=ACCENT_BLUE, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        '<font color="#666666" size="13">Translating text is easy. Just follow these steps:</font>',
        ParagraphStyle("intro", spaceAfter=20)
    ))

    translate_steps = [
        (1, "Select a Row", "Click on any row in the translation grid to select it.", PASTEL_BLUE),
        (2, "Type Your Translation", "Click on the cell for your language and start typing.", PASTEL_GREEN),
        (3, "Save Your Work", "Press Enter to confirm, or Ctrl+Enter for multi-line text.", PASTEL_BLUE),
        (4, "Automatic Save", "Your changes are saved automatically. No need to press Save!", PASTEL_GREEN),
    ]
    for num, title, desc, color in translate_steps:
        story.append(StepBox(num, title, desc, color, content_width))
        story.append(Spacer(1, 12))

    story.append(Spacer(1, 15))

    # Team work notice
    story.append(ColoredBox(
        "If someone else is editing the same row, you will see their name highlighted. "
        "LocaNext prevents conflicts automatically, so you never lose your work.",
        PASTEL_YELLOW,
        icon="!",
        bold_title="Working with teammates"
    ))

    story.append(Spacer(1, 15))

    # Keyboard shortcuts box
    story.append(ColoredBox(
        "Enter = save and move to next row  |  Ctrl+Enter = new line in cell  |  "
        "Escape = cancel editing  |  Ctrl+F = search  |  Ctrl+H = find and replace",
        LIGHT_BLUE,
        icon="~",
        bold_title="Keyboard shortcuts"
    ))

    story.append(PageBreak())

    # ── PAGE 6: Useful Features ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>Useful Features</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2, leading=30)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=HexColor("#9c27b0"), strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 20))

    features = [
        ("?", "Search", "Type in the search bar or press Ctrl+F to find any text in your file. You can search by ID, original text, or translation.", PASTEL_BLUE),
        ("=", "Filter", "Filter rows by language, translation status (New, Done, Review), or category. This helps you focus on what needs work.", PASTEL_GREEN),
        ("*", "Translation Memory (TM)", "LocaNext remembers past translations. When you select a row, it shows similar translations from previous work. This saves time and keeps things consistent.", PASTEL_YELLOW),
        ("+", "Merge", "Combine translations from different files. Right-click a file to merge translations into it. Great for updating old files with new translations.", PASTEL_ORANGE),
        ("~", "Audio", "Some text entries have voice recordings linked to them. You can listen to the audio to understand the context better. Use the Audio Codex to browse all recordings.", PASTEL_PURPLE),
    ]
    for icon, title, desc, color in features:
        story.append(FeatureCard(icon, title, desc, color, content_width))
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 10))

    story.append(ColoredBox(
        "All these features are designed to make your translation work faster and easier. "
        "You do not need to learn everything at once. Start with the basics (open, translate, save) "
        "and explore more features as you get comfortable.",
        LIGHT_BLUE,
        icon="i",
        bold_title="Take it step by step"
    ))

    story.append(PageBreak())

    # ── PAGE 7: Working Together (LAN Mode) ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>Working Together</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2)
    ))
    story.append(Paragraph(
        '<font color="#666666" size="15">LAN Mode - Real-Time Collaboration</font>',
        ParagraphStyle("subtitle", spaceAfter=0)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=DEEP_BLUE, strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 15))

    # Network diagram
    story.append(NetworkDiagram())

    story.append(Spacer(1, 15))

    # LAN mode steps
    lan_points = [
        ("Your administrator sets up the LocaNext server.", ACCENT_BLUE,
         "You do not need to do anything technical."),
        ("You connect by entering the server address.", SOFT_GREEN,
         "Your admin will give you the address to type in."),
        ("Everyone sees changes in real-time.", WARM_ORANGE,
         "When a teammate saves a translation, it appears on your screen instantly."),
        ("No more emailing files back and forth!", HexColor("#9c27b0"),
         "Everything stays in one place, always up to date."),
    ]
    for text, color, sub in lan_points:
        story.append(BulletPoint(text, bullet_color=color, sub_text=sub))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 15))

    story.append(ColoredBox(
        "If you lose internet connection, LocaNext switches to offline mode automatically. "
        "Your work is saved locally, and it will sync back when you reconnect. "
        "You will never lose your translations!",
        PASTEL_GREEN,
        icon="!",
        bold_title="What if I lose connection?"
    ))

    story.append(PageBreak())

    # ── PAGE 8: Need Help? ──
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        '<font color="#1a1a2e" size="26"><b>Need Help?</b></font>',
        ParagraphStyle("title", alignment=TA_LEFT, spaceAfter=2, leading=30)
    ))
    d = Drawing(content_width, 4)
    d.add(Rect(0, 0, content_width, 3, fillColor=HexColor("#e91e63"), strokeColor=None))
    story.append(d)
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        '<font color="#666666" size="13">If you run into any problems, here is what to do:</font>',
        ParagraphStyle("intro", spaceAfter=20)
    ))

    # Help options
    help_items = [
        ("1", "Contact Your Administrator",
         "Your admin can help with login issues, server setup, and file access. They know the system best.",
         PASTEL_BLUE),
        ("2", "Check the Built-in Help",
         "Click the ? icon in the top-right corner of LocaNext for quick tips and documentation.",
         PASTEL_GREEN),
        ("3", "Common Solutions",
         "See the troubleshooting guide below for the most frequent issues.",
         PASTEL_YELLOW),
    ]
    for num, title, desc, color in help_items:
        story.append(StepBox(int(num), title, desc, color, content_width))
        story.append(Spacer(1, 12))

    story.append(Spacer(1, 20))

    # Troubleshooting table
    story.append(Paragraph(
        '<font color="#1a1a2e" size="16"><b>Troubleshooting</b></font>',
        ParagraphStyle("h2", spaceAfter=12)
    ))

    trouble_data = [
        ["Problem", "Solution"],
        ["Cannot connect to server", "Check that your computer is on the\nsame network as the server.\nAsk your admin for the correct address."],
        ["LocaNext feels slow", "Ask your admin to rebuild the search\nindex. This is a quick fix."],
        ["Cannot find my file", "Check the File Explorer on the left.\nAsk your admin to add the file to\nyour project."],
        ["My changes disappeared", "Do not worry! Check the \"Offline\"\nindicator. Your changes are saved\nlocally and will sync back."],
        ["Cannot log in", "Double-check your username and\npassword. Ask your admin to reset\nyour password if needed."],
    ]

    # Build table
    table = Table(trouble_data, colWidths=[content_width * 0.35, content_width * 0.65])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor("#fafafa")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, HexColor("#f5f5f5")]),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_DARK),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#e0e0e0")),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    story.append(table)

    story.append(Spacer(1, 25))

    # Final encouragement box
    story.append(ColoredBox(
        "Remember: there is no such thing as a silly question! "
        "Your admin and team are here to help. LocaNext is a tool that makes "
        "your translation work easier, and we want you to feel comfortable using it.",
        HexColor("#e8f5e9"),
        icon="<3",
        bold_title="You are doing great!"
    ))

    # ── Build with page templates ──
    doc.build(
        story,
        onFirstPage=cover_page,
        onLaterPages=page_footer,
    )

    print(f"PDF created: {output_path}")
    return output_path


if __name__ == "__main__":
    path = build_pdf()
    # Verify
    size = os.path.getsize(path)
    print(f"File size: {size:,} bytes ({size/1024:.1f} KB)")
