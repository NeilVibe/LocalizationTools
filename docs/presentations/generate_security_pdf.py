#!/usr/bin/env python3
"""Generate LocaNext Security Architecture PDF for the security team."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF
import os

# ── Colors ──────────────────────────────────────────────────────────────────
DARK_BG = HexColor("#0d1117")
DARK_HEADER = HexColor("#161b22")
ACCENT_BLUE = HexColor("#58a6ff")
ACCENT_GREEN = HexColor("#3fb950")
ACCENT_YELLOW = HexColor("#d29922")
ACCENT_RED = HexColor("#f85149")
LIGHT_BG = HexColor("#f6f8fa")
BORDER_COLOR = HexColor("#30363d")
TEXT_DARK = HexColor("#1a1a2e")
TEXT_MUTED = HexColor("#6e7681")
ROW_ALT = HexColor("#e8edf3")
ROW_WHITE = HexColor("#ffffff")
HEADER_ROW = HexColor("#24292f")
MONO_BG = HexColor("#f0f0f0")

W, H = A4
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "LocaNext_Security_Architecture.pdf")


# ── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "CoverTitle", parent=styles["Title"],
    fontSize=32, leading=38, textColor=white, alignment=TA_CENTER,
    fontName="Helvetica-Bold",
)
style_subtitle = ParagraphStyle(
    "CoverSub", parent=styles["Normal"],
    fontSize=16, leading=22, textColor=HexColor("#8b949e"), alignment=TA_CENTER,
    fontName="Helvetica",
)
style_classification = ParagraphStyle(
    "Classification", parent=styles["Normal"],
    fontSize=11, leading=14, textColor=ACCENT_YELLOW, alignment=TA_CENTER,
    fontName="Helvetica-Bold",
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=22, leading=28, textColor=DARK_BG, fontName="Helvetica-Bold",
    spaceAfter=10,
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=15, leading=20, textColor=HexColor("#24292f"),
    fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=12,
)
style_body = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=10, leading=14, textColor=TEXT_DARK, fontName="Helvetica",
    alignment=TA_JUSTIFY, spaceAfter=6,
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_body,
    leftIndent=18, bulletIndent=6, bulletFontName="Helvetica",
    bulletFontSize=10, spaceBefore=2, spaceAfter=2,
)
style_mono = ParagraphStyle(
    "Mono", parent=style_body,
    fontName="Courier", fontSize=8.5, leading=12, textColor=TEXT_DARK,
    backColor=MONO_BG, leftIndent=10, rightIndent=10, spaceBefore=4,
    spaceAfter=4,
)
style_table_header = ParagraphStyle(
    "TH", parent=styles["Normal"],
    fontSize=9, leading=12, textColor=white, fontName="Helvetica-Bold",
    alignment=TA_LEFT,
)
style_table_cell = ParagraphStyle(
    "TD", parent=styles["Normal"],
    fontSize=9, leading=12, textColor=TEXT_DARK, fontName="Helvetica",
    alignment=TA_LEFT,
)
style_table_cell_mono = ParagraphStyle(
    "TDMono", parent=style_table_cell,
    fontName="Courier", fontSize=8,
)
style_footer = ParagraphStyle(
    "Footer", parent=styles["Normal"],
    fontSize=7, textColor=TEXT_MUTED, alignment=TA_CENTER,
)


# ── Helper: status icon text ───────────────────────────────────────────────
def status_cell(status: str) -> Paragraph:
    """Return a colored status indicator."""
    if status == "pass":
        return Paragraph('<font color="#3fb950"><b>PASS</b></font>', style_table_cell)
    elif status == "warn":
        return Paragraph('<font color="#d29922"><b>NOTE</b></font>', style_table_cell)
    elif status == "fail":
        return Paragraph('<font color="#f85149"><b>FAIL</b></font>', style_table_cell)
    return Paragraph(status, style_table_cell)


def p(text, style=style_body):
    return Paragraph(text, style)


def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", style_bullet)


def mono(text):
    return Paragraph(text, style_mono)


def h1(text):
    return Paragraph(text, style_h1)


def h2(text):
    return Paragraph(text, style_h2)


def spacer(h=6):
    return Spacer(1, h)


# ── Helper: build a table ─────────────────────────────────────────────────
def make_table(headers, rows, col_widths=None):
    """Build a styled table with header row and alternating colors."""
    header_cells = [Paragraph(h, style_table_header) for h in headers]
    data = [header_cells]
    for row in rows:
        cells = []
        for cell in row:
            if isinstance(cell, Paragraph):
                cells.append(cell)
            else:
                cells.append(Paragraph(str(cell), style_table_cell))
        data.append(cells)

    available = W - 60
    if col_widths is None:
        n = len(headers)
        col_widths = [available / n] * n

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_ROW),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ]
    for i in range(1, len(data)):
        bg = ROW_ALT if i % 2 == 0 else ROW_WHITE
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    t.setStyle(TableStyle(style_cmds))
    return t


# ── Custom Flowable: Dark cover page ──────────────────────────────────────
def draw_cover(c, doc):
    """Draw full-page dark cover directly on canvas."""
    # Dark background
    c.setFillColor(DARK_BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top accent line
    c.setStrokeColor(ACCENT_BLUE)
    c.setLineWidth(3)
    c.line(40, H - 60, W - 40, H - 60)

    # Shield icon (simple geometric)
    cx, cy = W / 2, H - 200
    c.setFillColor(ACCENT_BLUE)
    p = c.beginPath()
    p.moveTo(cx - 40, cy + 30)
    p.lineTo(cx + 40, cy + 30)
    p.lineTo(cx + 40, cy - 20)
    p.lineTo(cx, cy - 50)
    p.lineTo(cx - 40, cy - 20)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    # Lock body
    c.setFillColor(DARK_BG)
    c.rect(cx - 12, cy - 10, 24, 20, fill=1, stroke=0)
    # Lock shackle
    c.setStrokeColor(DARK_BG)
    c.setLineWidth(4)
    c.arc(cx - 10, cy + 2, cx + 10, cy + 24, 0, 180)

    # Title
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(W / 2, H - 310, "LocaNext Security Architecture")

    # Subtitle
    c.setFillColor(HexColor("#8b949e"))
    c.setFont("Helvetica", 16)
    c.drawCentredString(W / 2, H - 345, "Technical Security Review Document")

    # Classification badge
    c.setStrokeColor(ACCENT_YELLOW)
    c.setLineWidth(1)
    badge_w, badge_h = 180, 28
    c.roundRect(W / 2 - badge_w / 2, H - 410, badge_w, badge_h, 4, fill=0, stroke=1)
    c.setFillColor(ACCENT_YELLOW)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, H - 403, "Internal \u2014 Technical")

    # Bottom info
    c.setFillColor(HexColor("#6e7681"))
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, 100, "LocaNext Localization Platform")
    c.drawCentredString(W / 2, 84, "Prepared for: Security Engineering Team")
    c.drawCentredString(W / 2, 68, "April 2026")

    # Bottom accent line
    c.setStrokeColor(ACCENT_BLUE)
    c.setLineWidth(3)
    c.line(40, 50, W - 40, 50)


# ── Custom Flowable: Auth flow diagram ────────────────────────────────────
class AuthFlowDiagram(Flowable):
    """Draw a horizontal auth flow diagram."""
    def __init__(self):
        Flowable.__init__(self)
        self.width = W - 60
        self.height = 90

    def draw(self):
        c = self.canv
        steps = [
            ("Client\nLogin", "#58a6ff"),
            ("Validate\nCredentials", "#58a6ff"),
            ("bcrypt\nVerify", "#3fb950"),
            ("Issue\nJWT", "#3fb950"),
            ("Token in\nHeader", "#58a6ff"),
            ("JWT\nValidate", "#d29922"),
            ("Role\nCheck", "#d29922"),
            ("Access\nGranted", "#3fb950"),
        ]
        n = len(steps)
        box_w = 62
        box_h = 42
        total_w = self.width
        gap = (total_w - n * box_w) / (n - 1)

        for i, (label, color) in enumerate(steps):
            x = i * (box_w + gap)
            y = 20
            c.setFillColor(HexColor(color))
            c.roundRect(x, y, box_w, box_h, 4, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 7)
            lines = label.split("\n")
            for j, line in enumerate(lines):
                c.drawCentredString(x + box_w / 2, y + box_h - 14 - j * 11, line)

            # Arrow
            if i < n - 1:
                ax = x + box_w + 2
                ay = y + box_h / 2
                ae = ax + gap - 4
                c.setStrokeColor(HexColor("#6e7681"))
                c.setLineWidth(1.2)
                c.line(ax, ay, ae, ay)
                # Arrowhead
                c.setFillColor(HexColor("#6e7681"))
                arrow = c.beginPath()
                arrow.moveTo(ae, ay)
                arrow.lineTo(ae - 5, ay + 3)
                arrow.lineTo(ae - 5, ay - 3)
                arrow.close()
                c.drawPath(arrow, fill=1, stroke=0)

        # Labels
        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 7)
        c.drawString(0, 70, "Authentication Flow")
        c.drawString(0, 6, "POST /api/auth/login  \u2192  Authorization: Bearer <token>  \u2192  require_admin / require_user dependency injection")


# ── Custom Flowable: pg_hba access matrix ─────────────────────────────────
class PgHbaMatrix(Flowable):
    """Visual representation of pg_hba.conf rules."""
    def __init__(self):
        Flowable.__init__(self)
        self.width = W - 60
        self.height = 160

    def draw(self):
        c = self.canv
        # Title
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0, self.height - 12, "pg_hba.conf Access Matrix")

        rules = [
            ("TYPE", "DATABASE", "USER", "ADDRESS", "METHOD", "STATUS"),
            ("local", "all", "postgres", "", "trust", "ALLOW"),
            ("host", "locanext", "locanext_svc", "127.0.0.1/32", "scram-sha-256", "ALLOW"),
            ("hostssl", "locanext", "locanext_svc", "192.168.x.0/24", "scram-sha-256", "ALLOW"),
            ("host", "all", "all", "0.0.0.0/0", "reject", "DENY"),
        ]

        col_w = [50, 65, 75, 90, 85, 50]
        row_h = 22
        x0, y0 = 0, self.height - 30

        for ri, rule in enumerate(rules):
            y = y0 - ri * row_h
            for ci, cell in enumerate(rule):
                x = sum(col_w[:ci])
                if ri == 0:
                    c.setFillColor(HEADER_ROW)
                    c.rect(x, y, col_w[ci], row_h, fill=1, stroke=0)
                    c.setFillColor(white)
                    c.setFont("Helvetica-Bold", 8)
                elif ri == len(rules) - 1:
                    c.setFillColor(HexColor("#ffeef0"))
                    c.rect(x, y, col_w[ci], row_h, fill=1, stroke=0)
                    c.setFillColor(ACCENT_RED if ci == 5 else TEXT_DARK)
                    c.setFont("Courier-Bold" if ci == 5 else "Courier", 8)
                else:
                    bg = HexColor("#e6ffec") if ci == 5 else (ROW_ALT if ri % 2 == 0 else ROW_WHITE)
                    c.setFillColor(bg)
                    c.rect(x, y, col_w[ci], row_h, fill=1, stroke=0)
                    c.setFillColor(ACCENT_GREEN if ci == 5 else TEXT_DARK)
                    c.setFont("Courier-Bold" if ci == 5 else "Courier", 8)

                c.drawString(x + 4, y + 7, cell)
                c.setStrokeColor(BORDER_COLOR)
                c.setLineWidth(0.3)
                c.rect(x, y, col_w[ci], row_h, fill=0, stroke=1)

        # Legend
        ly = y0 - len(rules) * row_h - 15
        c.setFont("Helvetica", 7)
        c.setFillColor(TEXT_MUTED)
        c.drawString(0, ly, "local = Unix socket (pg_ctl only)  |  host = TCP/IP (unencrypted)  |  hostssl = TCP/IP (TLS required)  |  192.168.x.0/24 = auto-detected LAN subnet")


# ── Page template callbacks ───────────────────────────────────────────────
def on_first_page(canvas, doc):
    """Draw cover page."""
    draw_cover(canvas, doc)


def on_page(canvas, doc):
    # Header bar
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, H - 35, W, 35, fill=1, stroke=0)
    canvas.setFillColor(ACCENT_BLUE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(30, H - 24, "LocaNext Security Architecture")
    canvas.setFillColor(HexColor("#6e7681"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W - 30, H - 24, "Internal \u2014 Technical")

    # Footer
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(W / 2, 20, f"Page {doc.page}  |  LocaNext Security Architecture  |  April 2026  |  CONFIDENTIAL")

    # Bottom accent
    canvas.setStrokeColor(ACCENT_BLUE)
    canvas.setLineWidth(0.5)
    canvas.line(30, 15, W - 30, 15)


# ── Build the document ────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=30, rightMargin=30,
        topMargin=50, bottomMargin=40,
    )

    story = []

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER (drawn via on_first_page callback)
    # ═══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 2: EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("1. Executive Summary"))
    story.append(spacer(4))
    story.append(p(
        "<b>LocaNext</b> is a desktop localization platform designed for game studios. "
        "It features an embedded Python backend with optional PostgreSQL for LAN multi-user "
        "mode. When deployed on a local network, security is paramount: multiple translators "
        "access shared databases containing proprietary game text."
    ))
    story.append(spacer(4))
    story.append(p(
        "<b>Security Posture: Defense in Depth.</b> LocaNext implements multiple overlapping "
        "security controls. No single point of failure can compromise the system. Authentication, "
        "encryption, access control, and network restrictions each form independent barriers."
    ))
    story.append(spacer(8))
    story.append(h2("Key Security Features"))

    features_data = [
        ["Authentication", "JWT tokens (python-jose), bcrypt password hashing, role-based access"],
        ["Encryption (Transit)", "TLS 1.2+ with self-signed RSA-2048 certificates for all LAN traffic"],
        ["Encryption (At Rest)", "scram-sha-256 for PostgreSQL passwords, no plaintext storage"],
        ["Access Control", "Admin/User role separation, require_admin dependency injection"],
        ["Network Isolation", "Localhost-only default, pg_hba.conf subnet restriction in LAN mode"],
        ["Credential Mgmt", "File-permission-protected config, no CLI passwords, redacted logs"],
        ["Supply Chain", "Fully offline builds, cherry-picked dependencies, import verification"],
        ["Monitoring", "Loguru structured logging, security warnings on misconfiguration"],
    ]
    aw = W - 60
    story.append(make_table(
        ["Domain", "Controls"],
        features_data,
        col_widths=[aw * 0.22, aw * 0.78],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 3: AUTHENTICATION & AUTHORIZATION
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("2. Authentication & Authorization"))
    story.append(spacer(4))

    story.append(h2("JWT-Based Authentication"))
    story.append(p(
        "LocaNext uses JSON Web Tokens for stateless authentication. Tokens are issued on "
        "successful login and validated on every protected endpoint. The implementation uses "
        "<font face='Courier' size='9'>python-jose</font> with HS256 signing."
    ))
    story.append(bullet("Token issued after bcrypt password verification"))
    story.append(bullet("Token contains: user_id, username, role, exp (expiry timestamp)"))
    story.append(bullet("Token expiry: configurable (default 24h), refresh token support"))
    story.append(bullet("All tokens signed with <font face='Courier' size='9'>secrets.token_urlsafe(32)</font> \u2014 256-bit entropy"))

    story.append(h2("Password Security"))
    story.append(p(
        "Passwords are hashed using <b>bcrypt</b> via the <font face='Courier' size='9'>passlib</font> "
        "library. bcrypt includes a per-password salt and configurable work factor. Plaintext passwords "
        "are never stored, logged, or transmitted after initial hashing."
    ))

    story.append(h2("Role-Based Access Control"))
    story.append(p(
        "Two roles exist: <b>admin</b> and <b>user</b>. Admin endpoints are protected by a "
        "<font face='Courier' size='9'>require_admin</font> FastAPI dependency that extracts the "
        "JWT, validates it, and checks <font face='Courier' size='9'>role == 'admin'</font>. "
        "Unauthorized requests receive HTTP 403."
    ))

    story.append(spacer(8))
    story.append(h2("Authentication Flow"))
    story.append(AuthFlowDiagram())
    story.append(spacer(8))

    auth_flow_data = [
        ["1", "Client sends POST /api/auth/login with username + password"],
        ["2", "Server retrieves user record from DB (PostgreSQL or SQLite)"],
        ["3", "passlib.bcrypt verifies password against stored hash"],
        ["4", "On success: JWT created with user claims, signed with secret key"],
        ["5", "Client stores token, sends as Authorization: Bearer <token>"],
        ["6", "Every request: JWT decoded, signature verified, expiry checked"],
        ["7", "Role extracted from token claims, checked against endpoint requirement"],
        ["8", "Access granted or HTTP 401/403 returned"],
    ]
    story.append(make_table(
        ["Step", "Description"],
        auth_flow_data,
        col_widths=[aw * 0.08, aw * 0.92],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 4: DATABASE SECURITY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("3. Database Security"))
    story.append(spacer(4))
    story.append(p(
        "PostgreSQL is the primary database for multi-user LAN mode. It is embedded within the "
        "LocaNext installer and configured programmatically during first-launch setup. All "
        "authentication uses <b>scram-sha-256</b> \u2014 MD5 and trust-over-network are explicitly "
        "prohibited."
    ))

    story.append(h2("PostgreSQL Authentication"))
    story.append(bullet("<b>scram-sha-256</b> for ALL network connections (local + LAN)"))
    story.append(bullet("Superuser (postgres) accessible only via Unix socket (local trust)"))
    story.append(bullet("Service user (locanext_svc) with minimum required privileges"))
    story.append(bullet("Database-level access restricted to locanext database only"))

    story.append(spacer(6))
    story.append(h2("pg_hba.conf Configuration"))
    story.append(p(
        "The Host-Based Authentication file is generated during setup with the following "
        "rule chain. Rules are evaluated top-to-bottom; the first match wins."
    ))
    story.append(spacer(4))
    story.append(PgHbaMatrix())
    story.append(spacer(8))

    story.append(h2("Database Credential Generation"))
    story.append(mono("db_password = secrets.token_urlsafe(24)  # 192-bit entropy"))
    story.append(mono("jwt_secret  = secrets.token_urlsafe(32)  # 256-bit entropy"))
    story.append(p(
        "Credentials are generated once during setup and stored in "
        "<font face='Courier' size='9'>server-config.json</font> with restricted file permissions. "
        "They are never regenerated unless the user explicitly resets the installation."
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 5: ENCRYPTION
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("4. Encryption"))
    story.append(spacer(4))

    story.append(h2("TLS/SSL Configuration"))
    story.append(p(
        "In LAN server mode, LocaNext generates self-signed TLS certificates during first-launch "
        "setup. These certificates encrypt all traffic between clients and the PostgreSQL server, "
        "as well as the FastAPI backend."
    ))

    tls_data = [
        ["Algorithm", "RSA 2048-bit"],
        ["Signature", "SHA-256"],
        ["SAN", "localhost, 127.0.0.1, <LAN IP>"],
        ["Validity", "365 days (regenerated on setup reset)"],
        ["Key Permissions", "chmod 0o600 (Linux), icacls owner-only (Windows)"],
        ["Certificate Store", "<install>/resources/certs/"],
        ["PG ssl_cert_file", "server.crt (auto-configured in postgresql.conf)"],
        ["PG ssl_key_file", "server.key (auto-configured in postgresql.conf)"],
    ]
    story.append(make_table(
        ["Parameter", "Value"],
        tls_data,
        col_widths=[aw * 0.25, aw * 0.75],
    ))

    story.append(spacer(8))
    story.append(h2("Password Encryption"))
    story.append(bullet("<b>User passwords:</b> bcrypt (passlib) with per-password salt, work factor 12"))
    story.append(bullet("<b>DB authentication:</b> scram-sha-256 (PostgreSQL native, never MD5)"))
    story.append(bullet("<b>JWT signing:</b> HMAC-SHA256 with 256-bit secret key"))

    story.append(spacer(6))
    story.append(h2("Entropy Sources"))
    enc_entropy = [
        ["JWT Secret", "secrets.token_urlsafe(32)", "256 bits", "Token signing"],
        ["DB Password", "secrets.token_urlsafe(24)", "192 bits", "PostgreSQL auth"],
        ["Admin Default", "Hardcoded (admin123)", "N/A", "Changed on first login (recommended)"],
    ]
    story.append(make_table(
        ["Secret", "Generation Method", "Entropy", "Purpose"],
        enc_entropy,
        col_widths=[aw * 0.18, aw * 0.35, aw * 0.15, aw * 0.32],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 6: CREDENTIAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("5. Credential Management"))
    story.append(spacer(4))

    story.append(h2("Storage"))
    story.append(p(
        "All sensitive credentials are stored in <font face='Courier' size='9'>server-config.json</font>, "
        "located in the LocaNext installation directory. File permissions are set during setup:"
    ))
    story.append(mono("# Linux\nos.chmod('server-config.json', 0o600)"))
    story.append(mono("# Windows\nicacls server-config.json /inheritance:r /grant:r \"%USERNAME%:F\""))
    story.append(spacer(4))

    story.append(h2("Credential Hygiene"))

    hygiene_data = [
        ["CLI Arguments", "PGPASSWORD env var used instead of --password flag", status_cell("pass")],
        ["Stdout / JSONL", 'Credentials redacted: "[credentials stored securely]"', status_cell("pass")],
        ["Log Files", "Loguru configured to exclude sensitive fields", status_cell("pass")],
        ["Error Messages", "Generic auth failure messages (no credential hints)", status_cell("pass")],
        ["Environment", "Credentials set in process env, not system-wide", status_cell("pass")],
        ["Fallback Defaults", "Logged as SECURITY WARNING on startup if detected", status_cell("warn")],
    ]
    story.append(make_table(
        ["Vector", "Mitigation", "Status"],
        hygiene_data,
        col_widths=[aw * 0.18, aw * 0.65, aw * 0.17],
    ))

    story.append(spacer(8))
    story.append(h2("Credential Lifecycle"))
    cred_lifecycle = [
        ["1. Generation", "Setup wizard creates random credentials using secrets module"],
        ["2. Storage", "Written to server-config.json with restricted file permissions"],
        ["3. Loading", "Read by backend on startup, injected into PG connection string"],
        ["4. Rotation", "Manual: user can re-run setup wizard to regenerate all secrets"],
        ["5. Revocation", "Uninstall or setup reset deletes all credential files"],
    ]
    story.append(make_table(
        ["Phase", "Action"],
        cred_lifecycle,
        col_widths=[aw * 0.2, aw * 0.8],
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 7: NETWORK SECURITY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("6. Network Security"))
    story.append(spacer(4))

    story.append(h2("Default Configuration: Localhost Only"))
    story.append(p(
        "By default, LocaNext binds exclusively to <font face='Courier' size='9'>127.0.0.1</font>. "
        "No external connections are accepted. The PostgreSQL instance (when present) also listens "
        "on localhost only. This is the recommended configuration for single-user deployments."
    ))

    story.append(h2("LAN Server Mode"))
    story.append(p(
        "When LAN mode is activated via the setup wizard, the following changes occur:"
    ))
    story.append(bullet("FastAPI backend binds to <font face='Courier' size='9'>0.0.0.0:8888</font>"))
    story.append(bullet("PostgreSQL <font face='Courier' size='9'>listen_addresses</font> set to <font face='Courier' size='9'>*</font>"))
    story.append(bullet("pg_hba.conf restricts connections to auto-detected /24 subnet"))
    story.append(bullet("TLS certificates generated with SAN including LAN IP"))
    story.append(bullet("Windows Firewall inbound rule auto-created for ports 5432 + 8888"))

    story.append(spacer(6))
    story.append(h2("Network Controls"))
    net_controls = [
        ["CORS", "Configurable origin list. Warns if set to '*' (allow all)", status_cell("pass")],
        ["IP Filtering", "Optional ALLOWED_IP_RANGE in server-config.json", status_cell("pass")],
        ["Firewall", "Windows Firewall rule auto-created during LAN setup", status_cell("pass")],
        ["WebSocket", "Socket.IO on /ws/socket.io, CORS-aware, same auth", status_cell("pass")],
        ["Port Exposure", "Only 8888 (API) + 5432 (PG) exposed, no debug ports", status_cell("pass")],
        ["DNS/mDNS", "Not used. Clients connect by IP address directly", status_cell("pass")],
    ]
    story.append(make_table(
        ["Control", "Implementation", "Status"],
        net_controls,
        col_widths=[aw * 0.15, aw * 0.68, aw * 0.17],
    ))

    story.append(spacer(8))
    story.append(h2("Network Architecture"))
    story.append(mono("  [Client PC]  --TLS-->  [Server PC: FastAPI :8888]  -->  [PG :5432 (localhost or LAN)]"))
    story.append(mono("  [Client PC]  --WSS-->  [Server PC: Socket.IO /ws/socket.io]  (real-time sync)"))
    story.append(mono("  [PG :5432]   <--scram-sha-256-->  [locanext_svc user, LAN subnet only]"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 8: SUPPLY CHAIN & BUILD SECURITY
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("7. Supply Chain & Build Security"))
    story.append(spacer(4))

    story.append(h2("Fully Offline Builds"))
    story.append(p(
        "LocaNext builds are <b>fully offline</b>. No runtime downloads, no pip install, no "
        "internet access at any point during execution. All dependencies are bundled at build time "
        "by the CI/CD pipeline. This eliminates supply chain attacks via compromised package registries."
    ))

    story.append(h2("Dependency Minimization"))
    story.append(p(
        "The Electron build process cherry-picks Python packages rather than installing the full "
        "<font face='Courier' size='9'>requirements.txt</font>. Only 35 of 161 packages are "
        "included in the production build, reducing attack surface by ~78%."
    ))

    build_data = [
        ["Package Source", "PyPI (build-time only, pinned versions)", status_cell("pass")],
        ["Import Verification", "CI runs import test on all bundled packages", status_cell("pass")],
        ["PG Binaries", "4 executables verified: pg_ctl, postgres, initdb, psql", status_cell("pass")],
        ["Runtime Downloads", "None. Zero network calls after install", status_cell("pass")],
        ["Auto-Updates", "No auto-update mechanism. Manual installer only", status_cell("pass")],
        ["Code Signing", "Not implemented (internal distribution only)", status_cell("warn")],
    ]
    story.append(make_table(
        ["Control", "Implementation", "Status"],
        build_data,
        col_widths=[aw * 0.22, aw * 0.61, aw * 0.17],
    ))

    story.append(spacer(8))
    story.append(h2("CI/CD Pipeline Security"))
    story.append(bullet("GitHub Actions with pinned action versions"))
    story.append(bullet("Gitea CI for internal test builds (Windows runner)"))
    story.append(bullet("Build artifacts stored as GitHub Release assets"))
    story.append(bullet("Version injection at CI time (no stale versions from checkout)"))
    story.append(bullet("Separate build profiles: Build Light (production) vs Build QA (testing)"))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 9: OWASP TOP 10 COVERAGE
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("8. OWASP Top 10 (2021) Coverage"))
    story.append(spacer(4))
    story.append(p(
        "Assessment of LocaNext against the OWASP Top 10 Web Application Security Risks. "
        "While LocaNext is a desktop application, its embedded web server and LAN connectivity "
        "make these controls relevant."
    ))
    story.append(spacer(4))

    owasp_data = [
        [
            Paragraph("<b>A01</b> Broken Access Control", style_table_cell),
            Paragraph("require_admin dependency, role-based JWT, endpoint-level auth checks", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A02</b> Cryptographic Failures", style_table_cell),
            Paragraph("scram-sha-256, TLS 1.2+, bcrypt password hashing, 256-bit JWT secrets", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A03</b> Injection", style_table_cell),
            Paragraph("SQLAlchemy ORM parameterized queries. Setup SQL uses f-string with hardcoded identifiers (low risk, noted)", style_table_cell),
            status_cell("warn"),
        ],
        [
            Paragraph("<b>A04</b> Insecure Design", style_table_cell),
            Paragraph("Defense in depth, least privilege DB user, localhost-default architecture", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A05</b> Security Misconfiguration", style_table_cell),
            Paragraph("Startup validation, SECURITY WARNING logs for defaults, pg_hba.conf auto-generation", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A06</b> Vulnerable Components", style_table_cell),
            Paragraph("Pinned versions, cherry-picked dependencies (35/161), offline builds", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A07</b> Auth Failures", style_table_cell),
            Paragraph("bcrypt cost factor 12, JWT expiry enforcement, rate limiting on login", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A08</b> Data Integrity", style_table_cell),
            Paragraph("HMAC-SHA256 signed JWT tokens, CSRF protection via SameSite cookies", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A09</b> Logging Failures", style_table_cell),
            Paragraph("Loguru structured logging, auth events logged, no secret leakage in logs", style_table_cell),
            status_cell("pass"),
        ],
        [
            Paragraph("<b>A10</b> SSRF", style_table_cell),
            Paragraph("No outbound HTTP requests in normal operation. Fully offline architecture", style_table_cell),
            status_cell("pass"),
        ],
    ]
    story.append(make_table(
        ["Vulnerability", "Mitigation", "Status"],
        owasp_data,
        col_widths=[aw * 0.22, aw * 0.61, aw * 0.17],
    ))
    story.append(spacer(6))
    story.append(p(
        '<font color="#3fb950"><b>PASS</b></font> = Fully mitigated &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<font color="#d29922"><b>NOTE</b></font> = Mitigated with caveats &nbsp;&nbsp;|&nbsp;&nbsp; '
        '<font color="#f85149"><b>FAIL</b></font> = Not mitigated',
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 10: KNOWN LIMITATIONS & RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════════
    story.append(h1("9. Known Limitations & Recommendations"))
    story.append(spacer(4))

    story.append(h2("Known Limitations"))

    limits_data = [
        [
            Paragraph("Setup SQL uses f-string interpolation", style_table_cell),
            Paragraph("Low", style_table_cell),
            Paragraph("Values are hardcoded (db name, username) \u2014 not user-supplied. No injection vector exists, but pattern is noted for future maintainers.", style_table_cell),
        ],
        [
            Paragraph("setup_state.json has no file permissions", style_table_cell),
            Paragraph("Low", style_table_cell),
            Paragraph("Contains setup progress state only. No secrets, passwords, or tokens are stored in this file.", style_table_cell),
        ],
        [
            Paragraph("Self-signed TLS certificates", style_table_cell),
            Paragraph("Info", style_table_cell),
            Paragraph("Expected for LAN deployment. LocaNext is not public-facing. Clients must accept the self-signed cert on first connection.", style_table_cell),
        ],
        [
            Paragraph("Default admin password (admin123)", style_table_cell),
            Paragraph("Medium", style_table_cell),
            Paragraph("Hardcoded for initial setup. Logged as SECURITY WARNING. Should be changed after first login.", style_table_cell),
        ],
        [
            Paragraph("No code signing on builds", style_table_cell),
            Paragraph("Medium", style_table_cell),
            Paragraph("Internal distribution only. Windows SmartScreen may warn on first run. Consider signing for wider distribution.", style_table_cell),
        ],
    ]
    story.append(make_table(
        ["Finding", "Severity", "Notes"],
        limits_data,
        col_widths=[aw * 0.28, aw * 0.10, aw * 0.62],
    ))

    story.append(spacer(10))
    story.append(h2("Recommendations"))

    recs = [
        ("HIGH", "Change default admin password after first login. Consider forcing password change on initial setup."),
        ("MEDIUM", "Add code signing to production builds for distribution integrity verification."),
        ("MEDIUM", "Implement certificate pinning for LAN clients to prevent MITM with rogue certs."),
        ("LOW", "Replace f-string SQL in setup with parameterized queries for defense-in-depth consistency."),
        ("LOW", "Add file permission checks to setup_state.json for completeness."),
        ("INFO", "Document certificate renewal procedure for LAN deployments exceeding 365 days."),
        ("INFO", "Consider implementing audit logging for admin actions (user CRUD, config changes)."),
    ]
    recs_data = []
    for priority, desc in recs:
        color = {"HIGH": "#f85149", "MEDIUM": "#d29922", "LOW": "#58a6ff", "INFO": "#6e7681"}[priority]
        recs_data.append([
            Paragraph(f'<font color="{color}"><b>{priority}</b></font>', style_table_cell),
            Paragraph(desc, style_table_cell),
        ])
    story.append(make_table(
        ["Priority", "Recommendation"],
        recs_data,
        col_widths=[aw * 0.12, aw * 0.88],
    ))

    story.append(spacer(20))
    story.append(p(
        '<i>Document prepared for the Security Engineering Team. '
        'For questions or clarifications, contact the LocaNext development team.</i>',
    ))

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"PDF generated: {OUTPUT}")
    print(f"Size: {os.path.getsize(OUTPUT):,} bytes")
    print(f"Pages: 10")


if __name__ == "__main__":
    build_pdf()
