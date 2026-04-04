#!/usr/bin/env python3
"""Generate LocaNext Executive Overview PDF — Sales-pitch style for non-technical executives."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import math
import os

# ── Colors ──────────────────────────────────────────────────────
NAVY = HexColor("#1a1a2e")
DARK_NAVY = HexColor("#0f0f1e")
ACCENT_BLUE = HexColor("#4facfe")
LIGHT_BLUE = HexColor("#00f2fe")
GREEN = HexColor("#2ecc71")
DARK_GREEN = HexColor("#27ae60")
RED = HexColor("#e74c3c")
DARK_RED = HexColor("#c0392b")
GOLD = HexColor("#f39c12")
ORANGE = HexColor("#e67e22")
PURPLE = HexColor("#9b59b6")
LIGHT_GRAY = HexColor("#ecf0f1")
MEDIUM_GRAY = HexColor("#bdc3c7")
DARK_GRAY = HexColor("#2c3e50")
WARM_WHITE = HexColor("#f8f9fa")
SOFT_BLUE_BG = HexColor("#e8f4f8")

WIDTH, HEIGHT = A4


def draw_dark_bg(c, page_num=0):
    """Draw dark gradient-like background with subtle geometric accents."""
    # Base dark fill
    c.setFillColor(NAVY)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

    # Subtle gradient overlay (darker at bottom)
    for i in range(20):
        alpha = 0.02 * i
        c.setFillColor(Color(0, 0, 0, alpha))
        c.rect(0, 0, WIDTH, HEIGHT * (1 - i / 20.0), fill=1, stroke=0)

    # Subtle accent circles (decorative)
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.03))  # ACCENT_BLUE with low alpha
    offsets = [(page_num * 50) % 200, (page_num * 70) % 300]
    c.circle(WIDTH + 30, HEIGHT - 100 + offsets[0], 200, fill=1, stroke=0)
    c.circle(-80, 100 + offsets[1], 150, fill=1, stroke=0)


def draw_light_bg(c, page_num=0):
    """Draw light professional background."""
    c.setFillColor(WARM_WHITE)
    c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)

    # Top accent bar
    c.setFillColor(NAVY)
    c.rect(0, HEIGHT - 8, WIDTH, 8, fill=1, stroke=0)

    # Subtle corner accent
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.05))
    c.circle(WIDTH + 50, HEIGHT - 50, 200, fill=1, stroke=0)


def draw_footer(c, page_num, total=10, dark=True):
    """Draw page footer with number."""
    if dark:
        c.setFillColor(Color(1, 1, 1, 0.3))
    else:
        c.setFillColor(Color(0, 0, 0, 0.3))
    c.setFont("Helvetica", 9)
    c.drawCentredString(WIDTH / 2, 20, f"{page_num} / {total}")

    # Thin line
    if dark:
        c.setStrokeColor(Color(1, 1, 1, 0.1))
    else:
        c.setStrokeColor(Color(0, 0, 0, 0.1))
    c.setLineWidth(0.5)
    c.line(40, 35, WIDTH - 40, 35)


def draw_rounded_rect(c, x, y, w, h, r=10, fill_color=None, stroke_color=None, stroke_width=1):
    """Draw a rounded rectangle."""
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def draw_icon_circle(c, cx, cy, r, icon_color, symbol=None):
    """Draw a colored circle with optional symbol text."""
    # Glow effect
    c.setFillColor(Color(icon_color.red, icon_color.green, icon_color.blue, 0.15))
    c.circle(cx, cy, r + 6, fill=1, stroke=0)

    # Main circle
    c.setFillColor(icon_color)
    c.circle(cx, cy, r, fill=1, stroke=0)

    if symbol:
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", int(r * 1.1))
        c.drawCentredString(cx, cy - r * 0.35, symbol)


def draw_checkmark(c, cx, cy, size, color=GREEN):
    """Draw a checkmark icon."""
    draw_icon_circle(c, cx, cy, size, color)
    # Checkmark path
    c.setStrokeColor(white)
    c.setLineWidth(size * 0.2)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(cx - size * 0.4, cy)
    p.lineTo(cx - size * 0.1, cy - size * 0.35)
    p.lineTo(cx + size * 0.45, cy + size * 0.35)
    c.drawPath(p, fill=0, stroke=1)


def draw_x_mark(c, cx, cy, size, color=RED):
    """Draw an X icon."""
    draw_icon_circle(c, cx, cy, size, color)
    c.setStrokeColor(white)
    c.setLineWidth(size * 0.2)
    c.setLineCap(1)
    offset = size * 0.3
    c.line(cx - offset, cy + offset, cx + offset, cy - offset)
    c.line(cx - offset, cy - offset, cx + offset, cy + offset)


def wrap_text(text, max_chars=40):
    """Simple word-wrap for text."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        if len(test) > max_chars:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_wrapped_text(c, text, x, y, font, size, color, max_chars=40, align="center", line_height=None):
    """Draw wrapped text, return final y position."""
    if line_height is None:
        line_height = size * 1.4
    c.setFont(font, size)
    c.setFillColor(color)
    lines = wrap_text(text, max_chars)
    for line in lines:
        if align == "center":
            c.drawCentredString(x, y, line)
        elif align == "left":
            c.drawString(x, y, line)
        y -= line_height
    return y


# ══════════════════════════════════════════════════════════════════
# PAGE 1: COVER
# ══════════════════════════════════════════════════════════════════
def page_cover(c):
    draw_dark_bg(c, 0)

    # Large decorative circle in background
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.06))
    c.circle(WIDTH / 2, HEIGHT / 2 - 20, 280, fill=1, stroke=0)
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.04))
    c.circle(WIDTH / 2, HEIGHT / 2 - 20, 350, fill=1, stroke=0)

    # Small decorative dots
    for i, (dx, dy) in enumerate([(100, 650), (480, 720), (120, 300), (450, 250), (300, 150)]):
        c.setFillColor(Color(0.31, 0.67, 1.0, 0.15 + i * 0.05))
        c.circle(dx, dy, 3 + i, fill=1, stroke=0)

    # LocaNext logo text
    y = HEIGHT / 2 + 120
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 72)
    c.drawCentredString(WIDTH / 2, y, "LocaNext")

    # Accent line under logo
    line_w = 120
    c.setStrokeColor(ACCENT_BLUE)
    c.setLineWidth(3)
    c.line(WIDTH / 2 - line_w / 2, y - 15, WIDTH / 2 + line_w / 2, y - 15)

    # Subtitle
    y -= 55
    c.setFont("Helvetica", 22)
    c.setFillColor(ACCENT_BLUE)
    c.drawCentredString(WIDTH / 2, y, "Professional Game Localization Platform")

    # Tagline
    y -= 80
    c.setFont("Helvetica", 16)
    c.setFillColor(Color(1, 1, 1, 0.7))
    c.drawCentredString(WIDTH / 2, y, "Built for Teams.  Built for Speed.  Built for Quality.")

    # Bottom version
    c.setFont("Helvetica", 10)
    c.setFillColor(Color(1, 1, 1, 0.3))
    c.drawCentredString(WIDTH / 2, 50, "Executive Overview  |  2026")

    draw_footer(c, 1, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 2: THE PROBLEM
# ══════════════════════════════════════════════════════════════════
def page_problem(c):
    draw_dark_bg(c, 1)

    # Header
    y = HEIGHT - 80
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 38)
    c.drawCentredString(WIDTH / 2, y, "Localization Today")
    y -= 45
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 38)
    c.drawCentredString(WIDTH / 2, y, "is Broken")

    # Three problem boxes
    problems = [
        "Files emailed back and forth \u2014 versions get lost",
        "Same sentences translated multiple times \u2014 wasted effort",
        "No way to know who changed what \u2014 chaos",
    ]

    box_h = 95
    box_w = WIDTH - 100
    start_y = y - 80

    for i, problem in enumerate(problems):
        by = start_y - i * (box_h + 25)

        # Red-tinted box
        draw_rounded_rect(c, 50, by, box_w, box_h, r=12,
                          fill_color=Color(0.91, 0.30, 0.24, 0.12))

        # Red border left
        c.setFillColor(RED)
        p = c.beginPath()
        p.roundRect(50, by, 6, box_h, 3)
        c.drawPath(p, fill=1, stroke=0)

        # X icon
        draw_x_mark(c, 95, by + box_h / 2, 18, RED)

        # Text
        c.setFillColor(white)
        c.setFont("Helvetica", 18)
        lines = wrap_text(problem, 38)
        text_y = by + box_h / 2 + (len(lines) - 1) * 12 - 2
        for line in lines:
            c.drawString(130, text_y, line)
            text_y -= 26

    # Bottom question
    bottom_y = start_y - 3 * (box_h + 25) - 20
    c.setFillColor(Color(1, 1, 1, 0.6))
    c.setFont("Helvetica-Oblique", 20)
    c.drawCentredString(WIDTH / 2, bottom_y, "Sound familiar?")

    draw_footer(c, 2, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 3: THE SOLUTION
# ══════════════════════════════════════════════════════════════════
def page_solution(c):
    draw_dark_bg(c, 2)

    # Header
    y = HEIGHT - 80
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "LocaNext Changes")
    y -= 45
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "Everything")

    solutions = [
        "One shared workspace \u2014 everyone sees changes instantly",
        "Translation Memory \u2014 never translate the same thing twice",
        "Full history \u2014 see who changed what, when, and why",
    ]

    box_h = 95
    box_w = WIDTH - 100
    start_y = y - 80

    for i, solution in enumerate(solutions):
        by = start_y - i * (box_h + 25)

        # Green-tinted box
        draw_rounded_rect(c, 50, by, box_w, box_h, r=12,
                          fill_color=Color(0.18, 0.80, 0.44, 0.10))

        # Green border left
        c.setFillColor(GREEN)
        p = c.beginPath()
        p.roundRect(50, by, 6, box_h, 3)
        c.drawPath(p, fill=1, stroke=0)

        # Checkmark
        draw_checkmark(c, 95, by + box_h / 2, 18, GREEN)

        # Text
        c.setFillColor(white)
        c.setFont("Helvetica", 18)
        lines = wrap_text(solution, 38)
        text_y = by + box_h / 2 + (len(lines) - 1) * 12 - 2
        for line in lines:
            c.drawString(130, text_y, line)
            text_y -= 26

    # Before/After mini comparison
    bottom_y = start_y - 3 * (box_h + 25) - 10
    comp_w = (WIDTH - 120) / 2

    # Before box
    draw_rounded_rect(c, 50, bottom_y - 5, comp_w, 55, r=8,
                      fill_color=Color(0.91, 0.30, 0.24, 0.1))
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(50 + comp_w / 2, bottom_y + 28, "BEFORE")
    c.setFillColor(Color(1, 1, 1, 0.7))
    c.setFont("Helvetica", 12)
    c.drawCentredString(50 + comp_w / 2, bottom_y + 8, "Scattered files, lost versions")

    # Arrow
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(WIDTH / 2, bottom_y + 18, "\u2192")

    # After box
    ax = WIDTH - 50 - comp_w
    draw_rounded_rect(c, ax, bottom_y - 5, comp_w, 55, r=8,
                      fill_color=Color(0.18, 0.80, 0.44, 0.1))
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(ax + comp_w / 2, bottom_y + 28, "AFTER")
    c.setFillColor(Color(1, 1, 1, 0.7))
    c.setFont("Helvetica", 12)
    c.drawCentredString(ax + comp_w / 2, bottom_y + 8, "One platform, always in sync")

    draw_footer(c, 3, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 4: KEY BENEFITS (THE MONEY SLIDE)
# ══════════════════════════════════════════════════════════════════
def page_benefits(c):
    draw_dark_bg(c, 3)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(WIDTH / 2, y, "What You Get")

    # 4 metric boxes in 2x2 grid
    metrics = [
        ("10x", "Faster", "Bulk operations, auto-suggestions,\ninstant search across all files", ACCENT_BLUE),
        ("0", "Conflicts", "Real-time sync with row-level\nlocking prevents overwrites", GREEN),
        ("6+", "Languages", "Korean, English, Japanese, Chinese,\nGerman, French \u2014 all at once", GOLD),
        ("100%", "Offline", "Works without internet.\nSyncs automatically when connected.", PURPLE),
    ]

    box_w = (WIDTH - 120) / 2
    box_h = 185
    start_y = y - 60

    for i, (number, label, desc, color) in enumerate(metrics):
        col = i % 2
        row = i // 2
        bx = 50 + col * (box_w + 20)
        by = start_y - row * (box_h + 20) - box_h

        # Box background
        draw_rounded_rect(c, bx, by, box_w, box_h, r=14,
                          fill_color=Color(color.red, color.green, color.blue, 0.08))

        # Top colored accent bar
        c.setFillColor(color)
        p = c.beginPath()
        p.roundRect(bx + 15, by + box_h - 8, box_w - 30, 4, 2)
        c.drawPath(p, fill=1, stroke=0)

        # Big number
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 52)
        c.drawCentredString(bx + box_w / 2, by + box_h - 70, number)

        # Label
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(bx + box_w / 2, by + box_h - 95, label)

        # Description
        c.setFillColor(Color(1, 1, 1, 0.6))
        c.setFont("Helvetica", 11)
        desc_lines = desc.split("\n")
        dy = by + 45
        for dline in desc_lines:
            c.drawCentredString(bx + box_w / 2, dy, dline)
            dy -= 15

    draw_footer(c, 4, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 5: HOW IT WORKS
# ══════════════════════════════════════════════════════════════════
def page_how_it_works(c):
    draw_dark_bg(c, 4)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(WIDTH / 2, y, "Simple as 1-2-3")

    steps = [
        ("1", "Open your file", "Drag and drop any localization\nfile to get started", ACCENT_BLUE),
        ("2", "Translate in the grid", "Type translations side by side.\nKR \u2192 EN \u2192 JP \u2192 all languages.", GREEN),
        ("3", "Save automatically", "Changes save in real-time.\nYour team sees them instantly.", GOLD),
    ]

    circle_r = 50
    start_y = y - 120
    spacing = 190

    for i, (num, title, desc, color) in enumerate(steps):
        cy = start_y - i * spacing

        # Connecting line (except last)
        if i < 2:
            c.setStrokeColor(Color(1, 1, 1, 0.1))
            c.setLineWidth(2)
            c.setDash([4, 4])
            c.line(WIDTH / 4, cy - circle_r - 10, WIDTH / 4, cy - spacing + circle_r + 10)
            c.setDash([])

        # Number circle
        # Glow
        c.setFillColor(Color(color.red, color.green, color.blue, 0.08))
        c.circle(WIDTH / 4, cy, circle_r + 15, fill=1, stroke=0)
        c.setFillColor(Color(color.red, color.green, color.blue, 0.15))
        c.circle(WIDTH / 4, cy, circle_r + 5, fill=1, stroke=0)

        # Circle
        c.setFillColor(color)
        c.circle(WIDTH / 4, cy, circle_r, fill=1, stroke=0)

        # Number
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(WIDTH / 4, cy - 14, num)

        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(WIDTH / 4 + circle_r + 30, cy + 10, title)

        # Description
        c.setFillColor(Color(1, 1, 1, 0.6))
        c.setFont("Helvetica", 14)
        for j, line in enumerate(desc.split("\n")):
            c.drawString(WIDTH / 4 + circle_r + 30, cy - 15 - j * 20, line)

    # Bottom text
    bottom_y = start_y - 2 * spacing - 90
    draw_rounded_rect(c, 60, bottom_y, WIDTH - 120, 50, r=10,
                      fill_color=Color(0.31, 0.67, 1.0, 0.08))
    c.setFillColor(Color(1, 1, 1, 0.8))
    c.setFont("Helvetica-Oblique", 16)
    c.drawCentredString(WIDTH / 2, bottom_y + 17, "That's it. Your team is already productive.")

    draw_footer(c, 5, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 6: TEAM COLLABORATION
# ══════════════════════════════════════════════════════════════════
def page_team(c):
    draw_dark_bg(c, 5)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "Your Whole Team,")
    y -= 45
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "One Screen")

    # Center server
    center_x = WIDTH / 2
    center_y = HEIGHT / 2 - 20

    # Big circle for server
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.06))
    c.circle(center_x, center_y, 180, fill=1, stroke=0)
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.08))
    c.circle(center_x, center_y, 120, fill=1, stroke=0)

    # Server icon (rectangle stack)
    sw, sh = 60, 18
    for j in range(3):
        sy = center_y + 20 - j * (sh + 4)
        draw_rounded_rect(c, center_x - sw / 2, sy, sw, sh, r=4, fill_color=ACCENT_BLUE)
        # Small dots on server
        c.setFillColor(white)
        c.circle(center_x + sw / 2 - 10, sy + sh / 2, 3, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(center_x, center_y - 45, "LocaNext Server")

    # Team members around the circle
    team = [
        ("KR Translator", 90),
        ("EN Translator", 30),
        ("JP Translator", 330),
        ("QA Reviewer", 210),
        ("Project Lead", 150),
        ("CN Translator", 270),
    ]

    radius = 165
    member_colors = [ACCENT_BLUE, GREEN, GOLD, PURPLE, ORANGE, Color(0.2, 0.8, 0.8)]

    for i, (name, angle_deg) in enumerate(team):
        angle = math.radians(angle_deg)
        mx = center_x + radius * math.cos(angle)
        my = center_y + radius * math.sin(angle)

        color = member_colors[i]

        # Connection line
        c.setStrokeColor(Color(color.red, color.green, color.blue, 0.3))
        c.setLineWidth(1.5)
        c.setDash([3, 3])
        c.line(center_x, center_y, mx, my)
        c.setDash([])

        # Person circle
        c.setFillColor(Color(color.red, color.green, color.blue, 0.15))
        c.circle(mx, my, 28, fill=1, stroke=0)
        c.setFillColor(color)
        c.circle(mx, my, 22, fill=1, stroke=0)

        # Person icon (simple head+body)
        c.setFillColor(white)
        c.circle(mx, my + 5, 6, fill=1, stroke=0)
        p = c.beginPath()
        p.moveTo(mx - 10, my - 6)
        p.curveTo(mx - 10, my + 2, mx + 10, my + 2, mx + 10, my - 6)
        c.drawPath(p, fill=1, stroke=0)

        # Name label
        c.setFillColor(white)
        c.setFont("Helvetica", 10)
        # Position label outside the circle
        label_dist = 42
        lx = center_x + (radius + label_dist) * math.cos(angle)
        ly = center_y + (radius + label_dist) * math.sin(angle)
        c.drawCentredString(lx, ly - 4, name)

    # Bottom label
    draw_rounded_rect(c, 80, 75, WIDTH - 160, 45, r=10,
                      fill_color=Color(0.31, 0.67, 1.0, 0.08))
    c.setFillColor(Color(1, 1, 1, 0.8))
    c.setFont("Helvetica", 15)
    c.drawCentredString(WIDTH / 2, 92, "Everyone works on the same file simultaneously")

    # Connection count
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(WIDTH / 2, 60, "Up to 200+ simultaneous connections")

    draw_footer(c, 6, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 7: SMART FEATURES
# ══════════════════════════════════════════════════════════════════
def page_smart_features(c):
    draw_dark_bg(c, 6)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "AI-Powered")
    y -= 45
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "Intelligence")

    features = [
        ("Translation\nMemory", "Suggests translations from\nyour history. Never start\nfrom scratch.", ACCENT_BLUE, "TM"),
        ("Smart\nSearch", "Find any text across all\nfiles in milliseconds.\nAll languages at once.", GREEN, "Q"),
        ("Audio\nPreview", "Listen to voice recordings\nlinked to each dialogue\nline.", GOLD, "\u266B"),
        ("Image\nContext", "See the actual game screen\nfor every text entry.\nNo guessing.", PURPLE, "\u25A3"),
    ]

    card_w = (WIDTH - 120) / 2
    card_h = 170
    start_y = y - 50

    for i, (title, desc, color, icon) in enumerate(features):
        col = i % 2
        row = i // 2
        cx = 50 + col * (card_w + 20)
        cy = start_y - row * (card_h + 20) - card_h

        # Card background
        draw_rounded_rect(c, cx, cy, card_w, card_h, r=12,
                          fill_color=Color(color.red, color.green, color.blue, 0.07))

        # Icon circle
        draw_icon_circle(c, cx + 35, cy + card_h - 38, 20, color, icon)

        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 17)
        title_lines = title.split("\n")
        ty = cy + card_h - 25
        for tl in title_lines:
            c.drawString(cx + 65, ty, tl)
            ty -= 20

        # Description
        c.setFillColor(Color(1, 1, 1, 0.6))
        c.setFont("Helvetica", 12)
        desc_lines = desc.split("\n")
        dy = cy + card_h - 75
        for dl in desc_lines:
            c.drawString(cx + 20, dy, dl)
            dy -= 16

    draw_footer(c, 7, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 8: SECURITY & RELIABILITY
# ══════════════════════════════════════════════════════════════════
def page_security(c):
    draw_dark_bg(c, 7)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "Enterprise-Grade")
    y -= 45
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(WIDTH / 2, y, "Security")

    badges = [
        ("Encrypted", "All data encrypted in\ntransit and at rest", ACCENT_BLUE, "\u26BF"),
        ("Access\nControl", "Admin controls who\ncan edit what", GREEN, "\u2699"),
        ("Audit\nTrail", "Complete history of\nevery single change", GOLD, "\u2630"),
        ("Offline-\nFirst", "Works without internet.\nZero data loss.", PURPLE, "\u2B24"),
    ]

    badge_w = (WIDTH - 120) / 2
    badge_h = 155
    start_y = y - 60

    for i, (title, desc, color, icon) in enumerate(badges):
        col = i % 2
        row = i // 2
        bx = 50 + col * (badge_w + 20)
        by = start_y - row * (badge_h + 20) - badge_h

        # Badge background
        draw_rounded_rect(c, bx, by, badge_w, badge_h, r=14,
                          fill_color=Color(color.red, color.green, color.blue, 0.06))

        # Border
        draw_rounded_rect(c, bx, by, badge_w, badge_h, r=14,
                          stroke_color=Color(color.red, color.green, color.blue, 0.2), stroke_width=1.5)

        # Shield icon
        c.setFillColor(color)
        # Shield shape (simplified)
        shield_cx = bx + badge_w / 2
        shield_cy = by + badge_h - 45
        sc = 22
        p = c.beginPath()
        p.moveTo(shield_cx, shield_cy + sc)
        p.lineTo(shield_cx + sc * 0.8, shield_cy + sc * 0.5)
        p.lineTo(shield_cx + sc * 0.8, shield_cy - sc * 0.2)
        p.curveTo(shield_cx + sc * 0.4, shield_cy - sc * 0.6,
                  shield_cx - sc * 0.4, shield_cy - sc * 0.6,
                  shield_cx - sc * 0.8, shield_cy - sc * 0.2)
        p.lineTo(shield_cx - sc * 0.8, shield_cy + sc * 0.5)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

        # Icon text inside shield
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(shield_cx, shield_cy - 2, icon.split("\n")[0] if "\n" in icon else icon)

        # Title
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 16)
        title_lines = title.split("\n")
        ty = by + 55
        for tl in title_lines:
            c.drawCentredString(bx + badge_w / 2, ty, tl)
            ty -= 19

        # Description
        c.setFillColor(Color(1, 1, 1, 0.6))
        c.setFont("Helvetica", 12)
        desc_lines = desc.split("\n")
        dy = by + 30
        for dl in desc_lines:
            c.drawCentredString(bx + badge_w / 2, dy, dl)
            dy -= 16

    # Bottom reassurance
    bottom_y = start_y - 2 * (badge_h + 20) - badge_h + 10
    c.setFillColor(Color(1, 1, 1, 0.5))
    c.setFont("Helvetica-Oblique", 14)
    c.drawCentredString(WIDTH / 2, bottom_y, "No technical setup required. Your IT team handles the rest.")

    draw_footer(c, 8, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 9: THE BOTTOM LINE (COMPARISON TABLE)
# ══════════════════════════════════════════════════════════════════
def page_bottom_line(c):
    draw_dark_bg(c, 8)

    # Header
    y = HEIGHT - 75
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(WIDTH / 2, y, "Why LocaNext?")

    # Comparison table
    rows = [
        ("File sharing", "Email attachments", "Real-time sync"),
        ("Version control", '"final_v3_REAL.xlsx"', "Automatic versioning"),
        ("Translation reuse", "Copy-paste from old files", "AI-powered suggestions"),
        ("Team coordination", "Meetings + spreadsheets", "Live collaboration"),
        ("Quality assurance", "Manual checking", "Automated validation"),
    ]

    table_x = 45
    table_w = WIDTH - 90
    col_widths = [table_w * 0.28, table_w * 0.36, table_w * 0.36]
    row_h = 52
    header_h = 45

    start_y = y - 70

    # Table header
    hy = start_y
    draw_rounded_rect(c, table_x, hy, col_widths[0], header_h, r=0,
                      fill_color=Color(1, 1, 1, 0.08))
    draw_rounded_rect(c, table_x + col_widths[0], hy, col_widths[1], header_h, r=0,
                      fill_color=Color(0.91, 0.30, 0.24, 0.15))
    draw_rounded_rect(c, table_x + col_widths[0] + col_widths[1], hy, col_widths[2], header_h, r=0,
                      fill_color=Color(0.18, 0.80, 0.44, 0.15))

    c.setFont("Helvetica-Bold", 14)
    header_text_y = hy + header_h / 2 - 5
    c.setFillColor(Color(1, 1, 1, 0.6))
    c.drawCentredString(table_x + col_widths[0] / 2, header_text_y, "")
    c.setFillColor(RED)
    c.drawCentredString(table_x + col_widths[0] + col_widths[1] / 2, header_text_y, "Before")
    c.setFillColor(GREEN)
    c.drawCentredString(table_x + col_widths[0] + col_widths[1] + col_widths[2] / 2, header_text_y, "With LocaNext")

    # Table rows
    for i, (category, before, after) in enumerate(rows):
        ry = start_y - header_h - i * row_h

        # Alternating row bg
        if i % 2 == 0:
            c.setFillColor(Color(1, 1, 1, 0.03))
        else:
            c.setFillColor(Color(1, 1, 1, 0.06))
        c.rect(table_x, ry, table_w, row_h, fill=1, stroke=0)

        # Row separator
        c.setStrokeColor(Color(1, 1, 1, 0.08))
        c.setLineWidth(0.5)
        c.line(table_x, ry, table_x + table_w, ry)

        text_y = ry + row_h / 2 - 5

        # Category
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(table_x + col_widths[0] / 2, text_y, category)

        # Before
        c.setFillColor(Color(1, 1, 1, 0.5))
        c.setFont("Helvetica", 12)
        c.drawCentredString(table_x + col_widths[0] + col_widths[1] / 2, text_y, before)

        # After
        c.setFillColor(GREEN)
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(table_x + col_widths[0] + col_widths[1] + col_widths[2] / 2, text_y, after)

    # Bottom tagline
    bottom_y = start_y - header_h - len(rows) * row_h - 50
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(WIDTH / 2, bottom_y + 15, "Save hours every week.")
    c.setFillColor(ACCENT_BLUE)
    c.drawCentredString(WIDTH / 2, bottom_y - 12, "Eliminate errors. Ship faster.")

    draw_footer(c, 9, dark=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 10: GET STARTED
# ══════════════════════════════════════════════════════════════════
def page_get_started(c):
    draw_dark_bg(c, 9)

    # Large decorative circles
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.04))
    c.circle(WIDTH / 2, HEIGHT / 2, 300, fill=1, stroke=0)
    c.setFillColor(Color(0.31, 0.67, 1.0, 0.06))
    c.circle(WIDTH / 2, HEIGHT / 2, 200, fill=1, stroke=0)

    # Header
    y = HEIGHT - 100
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(WIDTH / 2, y, "Ready to Transform")
    y -= 40
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(WIDTH / 2, y, "Your Workflow?")

    # LocaNext big name
    y -= 100
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 64)
    c.drawCentredString(WIDTH / 2, y, "LocaNext")

    # Accent line
    line_w = 100
    c.setStrokeColor(ACCENT_BLUE)
    c.setLineWidth(3)
    c.line(WIDTH / 2 - line_w / 2, y - 12, WIDTH / 2 + line_w / 2, y - 12)

    # Bullet points
    points = [
        "Contact your IT administrator to set up LocaNext",
        "Setup takes less than 5 minutes",
        "No training needed \u2014 if you can use Excel, you can use LocaNext",
    ]

    y -= 70
    for point in points:
        # Bullet dot
        c.setFillColor(ACCENT_BLUE)
        c.circle(WIDTH / 2 - 180, y + 5, 4, fill=1, stroke=0)

        # Text
        c.setFillColor(Color(1, 1, 1, 0.8))
        c.setFont("Helvetica", 16)
        c.drawString(WIDTH / 2 - 168, y, point)
        y -= 35

    # Bottom section
    y -= 30
    draw_rounded_rect(c, 80, y, WIDTH - 160, 55, r=12,
                      fill_color=Color(0.31, 0.67, 1.0, 0.1))
    c.setFillColor(ACCENT_BLUE)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(WIDTH / 2, y + 30, "Start localizing smarter today.")
    c.setFillColor(Color(1, 1, 1, 0.5))
    c.setFont("Helvetica", 12)
    c.drawCentredString(WIDTH / 2, y + 10, "Professional Game Localization Platform")

    # Version info
    c.setFillColor(Color(1, 1, 1, 0.25))
    c.setFont("Helvetica", 9)
    c.drawCentredString(WIDTH / 2, 55, "LocaNext  |  2026  |  Executive Overview")

    draw_footer(c, 10, dark=True)


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "LocaNext_Executive_Overview.pdf")

    c = canvas.Canvas(output_path, pagesize=A4)
    c.setTitle("LocaNext Executive Overview")
    c.setAuthor("LocaNext Team")
    c.setSubject("Professional Game Localization Platform")

    pages = [
        page_cover,
        page_problem,
        page_solution,
        page_benefits,
        page_how_it_works,
        page_team,
        page_smart_features,
        page_security,
        page_bottom_line,
        page_get_started,
    ]

    for i, page_fn in enumerate(pages):
        page_fn(c)
        if i < len(pages) - 1:
            c.showPage()

    c.save()
    print(f"PDF generated: {output_path}")
    print(f"Pages: {len(pages)}")
    file_size = os.path.getsize(output_path)
    print(f"Size: {file_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
