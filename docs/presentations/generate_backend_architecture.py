#!/usr/bin/env python3
"""
Generate LocaNext Backend Architecture PDF document.
Professional technical document for backend/code experts.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
import os

# ============================================================================
# Color Scheme
# ============================================================================

FASTAPI_GREEN = HexColor("#009688")
FASTAPI_DARK = HexColor("#00796B")
FASTAPI_LIGHT = HexColor("#E0F2F1")
DARK_BG = HexColor("#1a1a2e")
ACCENT_BLUE = HexColor("#2196F3")
ACCENT_ORANGE = HexColor("#FF9800")
ACCENT_PURPLE = HexColor("#7C4DFF")
CODE_BG = HexColor("#F5F5F5")
TEXT_DARK = HexColor("#212121")
TEXT_MEDIUM = HexColor("#424242")
TEXT_LIGHT = HexColor("#757575")
TABLE_HEADER_BG = HexColor("#00796B")
TABLE_ALT_ROW = HexColor("#E8F5E9")
BORDER_COLOR = HexColor("#B2DFDB")


# ============================================================================
# Styles
# ============================================================================

def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'CoverTitle', parent=styles['Title'],
        fontSize=36, leading=44, textColor=white,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'],
        fontSize=16, leading=22, textColor=HexColor("#B2DFDB"),
        alignment=TA_CENTER, fontName='Helvetica',
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        'PageTitle', parent=styles['Heading1'],
        fontSize=22, leading=28, textColor=FASTAPI_DARK,
        fontName='Helvetica-Bold', spaceBefore=0, spaceAfter=12,
        borderColor=FASTAPI_GREEN, borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontSize=13, leading=17, textColor=FASTAPI_GREEN,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'BodyText2', parent=styles['Normal'],
        fontSize=9.5, leading=13.5, textColor=TEXT_DARK,
        fontName='Helvetica', alignment=TA_JUSTIFY,
        spaceBefore=2, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'CodeBlock', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=HexColor("#333333"),
        fontName='Courier', backColor=CODE_BG,
        spaceBefore=4, spaceAfter=4,
        leftIndent=12, rightIndent=12,
        borderColor=BORDER_COLOR, borderWidth=0.5, borderPadding=6,
    ))
    styles.add(ParagraphStyle(
        'BulletItem', parent=styles['Normal'],
        fontSize=9.5, leading=13, textColor=TEXT_DARK,
        fontName='Helvetica', leftIndent=20, bulletIndent=8,
        spaceBefore=1, spaceAfter=1,
    ))
    styles.add(ParagraphStyle(
        'SmallNote', parent=styles['Normal'],
        fontSize=8, leading=11, textColor=TEXT_LIGHT,
        fontName='Helvetica-Oblique', alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontSize=8.5, leading=11.5, textColor=TEXT_DARK,
        fontName='Helvetica',
    ))
    styles.add(ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontSize=9, leading=12, textColor=white,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'DiagramLabel', parent=styles['Normal'],
        fontSize=8, leading=10, textColor=TEXT_DARK,
        fontName='Helvetica', alignment=TA_CENTER,
    ))
    return styles


# ============================================================================
# Diagram helpers
# ============================================================================

def draw_box(d, x, y, w, h, text, fill_color=FASTAPI_GREEN, text_color=white, font_size=9, corner_r=4):
    """Draw a rounded-corner box with centered text."""
    r = Rect(x, y, w, h, rx=corner_r, ry=corner_r)
    r.fillColor = fill_color
    r.strokeColor = HexColor("#00695C") if fill_color == FASTAPI_GREEN else HexColor("#BDBDBD")
    r.strokeWidth = 0.7
    d.add(r)
    s = String(x + w/2, y + h/2 - font_size/3, text, textAnchor='middle',
               fontSize=font_size, fontName='Helvetica-Bold', fillColor=text_color)
    d.add(s)


def draw_arrow_right(d, x1, y, x2, color=HexColor("#616161")):
    """Draw horizontal arrow from x1 to x2 at y."""
    line = Line(x1, y, x2 - 4, y)
    line.strokeColor = color
    line.strokeWidth = 1.2
    d.add(line)
    # arrowhead
    head = Polygon(points=[x2, y, x2-6, y+3, x2-6, y-3])
    head.fillColor = color
    head.strokeColor = color
    d.add(head)


def draw_arrow_down(d, x, y1, y2, color=HexColor("#616161")):
    """Draw vertical arrow from y1 down to y2 at x."""
    line = Line(x, y1, x, y2 + 4)
    line.strokeColor = color
    line.strokeWidth = 1.2
    d.add(line)
    head = Polygon(points=[x, y2, x-3, y2+6, x+3, y2+6])
    head.fillColor = color
    head.strokeColor = color
    d.add(head)


# ============================================================================
# Page drawing helpers
# ============================================================================

def add_page_header(story, styles, title, page_num):
    """Add consistent page header with green accent bar."""
    story.append(Spacer(1, 2*mm))
    # Title with page number
    story.append(Paragraph(f"{title}", styles['PageTitle']))
    # Green accent line
    story.append(HRFlowable(width="100%", thickness=2, color=FASTAPI_GREEN, spaceAfter=8))


def make_table(headers, rows, col_widths=None):
    """Create a styled table with green header."""
    header_style = ParagraphStyle('TH', fontSize=8.5, leading=11, textColor=white,
                                   fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('TC', fontSize=8.5, leading=11.5, textColor=TEXT_DARK,
                                 fontName='Helvetica')

    data = [[Paragraph(h, header_style) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), cell_style) for c in row])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), TABLE_ALT_ROW))

    t.setStyle(TableStyle(style_cmds))
    return t


def bullet(text, styles):
    return Paragraph(f"\u2022  {text}", styles['BulletItem'])


def code_block(text, styles):
    # Escape HTML entities
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(f"<font face='Courier' size=8>{text}</font>", styles['CodeBlock'])


# ============================================================================
# Page Content Builders
# ============================================================================

def build_cover(story, styles):
    """Page 1: Cover page with dark background."""
    story.append(Spacer(1, 60*mm))
    story.append(Paragraph("LocaNext", styles['CoverTitle']))
    story.append(Paragraph("Backend Architecture", styles['CoverTitle']))
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph("File Parsing, Indexing, and Media Processing Pipeline", styles['CoverSubtitle']))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Technical Reference for Backend Engineers", styles['CoverSubtitle']))
    story.append(Spacer(1, 30*mm))

    # Tech stack badges
    badge_style = ParagraphStyle('Badge', fontSize=10, leading=14,
                                  textColor=HexColor("#80CBC4"), alignment=TA_CENTER,
                                  fontName='Helvetica')
    story.append(Paragraph("Python 3.11  |  FastAPI  |  SQLAlchemy  |  Socket.IO  |  FAISS  |  lxml", badge_style))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("PostgreSQL / SQLite  |  Model2Vec  |  vgmstream  |  Pillow", badge_style))

    story.append(Spacer(1, 20*mm))
    date_style = ParagraphStyle('Date', fontSize=9, textColor=HexColor("#4DB6AC"),
                                 alignment=TA_CENTER, fontName='Helvetica-Oblique')
    story.append(Paragraph("April 2026  |  Internal Engineering Document", date_style))
    story.append(PageBreak())


def build_system_overview(story, styles):
    """Page 2: System Overview with architecture diagram."""
    add_page_header(story, styles, "System Overview", 2)

    story.append(Paragraph(
        "LocaNext is a game localization management platform built on an Electron + Python architecture. "
        "The backend is a FastAPI application embedded within the Electron desktop app, providing REST APIs, "
        "WebSocket collaboration, and in-memory game data indexing. It supports dual database modes: "
        "PostgreSQL for multi-user online collaboration and SQLite for offline single-user work.",
        styles['BodyText2']))

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Architecture Diagram", styles['SectionHead']))

    # Build architecture diagram
    dw, dh = 480, 200
    d = Drawing(dw, dh)

    # Row 1: Frontend
    draw_box(d, 160, 165, 160, 28, "Electron Frontend (Svelte 5)", DARK_BG, white, 9)

    # Arrow down
    draw_arrow_down(d, 240, 165, 145, FASTAPI_GREEN)

    # Row 2: API Layer
    draw_box(d, 140, 118, 200, 25, "FastAPI REST + Socket.IO (uvicorn)", FASTAPI_GREEN, white, 9)

    # Arrow down
    draw_arrow_down(d, 240, 118, 100, FASTAPI_GREEN)

    # Row 3: Service layer boxes
    svc_y = 68
    svc_h = 28
    svc_color = HexColor("#26A69A")
    draw_box(d, 5, svc_y, 75, svc_h, "LDM", svc_color, white, 8)
    draw_box(d, 85, svc_y, 80, svc_h, "XLSTransfer", svc_color, white, 8)
    draw_box(d, 170, svc_y, 75, svc_h, "MegaIndex", svc_color, white, 8)
    draw_box(d, 250, svc_y, 78, svc_h, "QuickSearch", svc_color, white, 8)
    draw_box(d, 333, svc_y, 70, svc_h, "KRSimilar", svc_color, white, 8)
    draw_box(d, 408, svc_y, 68, svc_h, "MediaConv", svc_color, white, 8)

    # Label
    s = String(240, svc_y + svc_h + 7, "Service Layer", textAnchor='middle',
               fontSize=8, fontName='Helvetica-Oblique', fillColor=TEXT_LIGHT)
    d.add(s)

    # Arrow down from center service
    draw_arrow_down(d, 240, svc_y, svc_y - 18, FASTAPI_GREEN)

    # Row 4: Data layer
    dl_y = 10
    dl_h = 28
    dl_color = HexColor("#455A64")
    draw_box(d, 20, dl_y, 110, dl_h, "PostgreSQL / SQLite", dl_color, white, 8)
    draw_box(d, 140, dl_y, 100, dl_h, "FAISS Vectors", dl_color, white, 8)
    draw_box(d, 250, dl_y, 100, dl_h, "File System", dl_color, white, 8)
    draw_box(d, 360, dl_y, 110, dl_h, "In-Memory Index", dl_color, white, 8)

    s2 = String(240, dl_y + dl_h + 7, "Data Layer", textAnchor='middle',
                fontSize=8, fontName='Helvetica-Oblique', fillColor=TEXT_LIGHT)
    d.add(s2)

    story.append(d)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Tech Stack", styles['SectionHead']))

    tech_rows = [
        ["Python 3.11", "Core runtime, async/await, type hints throughout"],
        ["FastAPI + uvicorn", "Async REST API with auto-generated OpenAPI docs"],
        ["SQLAlchemy 2.0", "Async ORM for PostgreSQL and SQLite (dual-mode)"],
        ["python-socketio", "Real-time WebSocket events (Socket.IO protocol)"],
        ["lxml", "High-performance XML parsing with XPath, br-tag preservation"],
        ["FAISS (faiss-cpu)", "Vector similarity search for Translation Memory"],
        ["Model2Vec", "Sentence embeddings for semantic TM search (~2.3GB model)"],
        ["Pillow (PIL)", "DDS texture to PNG conversion with LRU cache"],
        ["vgmstream-cli", "WEM audio to WAV conversion (bundled binary)"],
        ["pyahocorasick", "Aho-Corasick automaton for fast multi-pattern text search"],
        ["openpyxl", "Excel .xlsx reading/writing for XLSTransfer"],
        ["Loguru", "Structured logging with rotation and filtering"],
    ]
    story.append(make_table(["Component", "Role"], tech_rows, [100, 380]))

    story.append(PageBreak())


def build_file_parsing(story, styles):
    """Page 3: File Parsing Pipeline."""
    add_page_header(story, styles, "File Parsing Pipeline", 3)

    story.append(Paragraph(
        "LocaNext parses three primary file formats used in game localization workflows. "
        "All parsing preserves the critical <font face='Courier'>&lt;br/&gt;</font> tag convention "
        "where newlines in XML language data are encoded as <font face='Courier'>&lt;br/&gt;</font> tags, "
        "not literal newline characters.",
        styles['BodyText2']))

    story.append(Paragraph("Supported Formats", styles['SectionHead']))
    fmt_rows = [
        [".loc.xml", "Game localization XML", "lxml with XPath", "Primary format. StringID + language attributes (KR, EN, JP, ZH, etc.)"],
        [".xlsx", "Excel spreadsheet", "openpyxl", "Import/export via XLSTransfer. Column-per-language layout"],
        [".tmx", "Translation Memory", "lxml", "TMX 1.4 standard. TU/TUV structure with language pairs"],
    ]
    story.append(make_table(["Format", "Description", "Parser", "Notes"], fmt_rows, [55, 100, 75, 250]))

    story.append(Paragraph("XML Parsing Architecture", styles['SectionHead']))
    story.append(Paragraph(
        "The XML handler (<font face='Courier'>file_handlers/xml_handler.py</font>) uses lxml's iterparse "
        "for memory-efficient streaming of large game XML files. Key design decisions:",
        styles['BodyText2']))
    story.append(bullet("Newlines stored as <font face='Courier'>&lt;br/&gt;</font> tags in XML attributes (never &#38;#10;)", styles))
    story.append(bullet("Case-insensitive attribute matching via <font face='Courier'>attrs = {k.lower(): v for k, v in elem.attrib.items()}</font>", styles))
    story.append(bullet("StringID extraction normalized to lowercase for consistent lookups", styles))
    story.append(bullet("StrOrigin normalization: collapse whitespace, strip br-tags, normalize placeholders", styles))

    story.append(Paragraph("Bulk Load Architecture", styles['SectionHead']))
    story.append(Paragraph(
        "When a user opens a file, LocaNext bulk-loads ALL rows in a single operation. "
        "The client receives the complete dataset and handles search, filtering, and scrolling "
        "entirely client-side. This eliminates server round-trips during editing sessions.",
        styles['BodyText2']))

    # Bulk load pipeline diagram
    dw, dh = 460, 70
    d = Drawing(dw, dh)
    bx_w, bx_h = 95, 30
    y = 20
    colors = [HexColor("#1565C0"), HexColor("#2E7D32"), HexColor("#E65100"), HexColor("#6A1B9A")]
    labels = ["File Upload\n(XML/XLSX)", "Parse &\nNormalize", "Bulk Insert\n(PG COPY)", "Send ALL\nto Client"]

    for i, (label, col) in enumerate(zip(labels, colors)):
        x = 10 + i * 115
        draw_box(d, x, y, bx_w, bx_h, label.split('\n')[0], col, white, 8)
        if len(label.split('\n')) > 1:
            s = String(x + bx_w/2, y - 2, label.split('\n')[1], textAnchor='middle',
                       fontSize=7, fontName='Helvetica', fillColor=TEXT_LIGHT)
            d.add(s)
        if i < 3:
            draw_arrow_right(d, x + bx_w, y + bx_h/2, x + 115, FASTAPI_GREEN)

    story.append(d)

    story.append(Paragraph("Row Data Structure", styles['SectionHead']))
    row_fields = [
        ["StringID", "Unique row identifier", "str", "Lowercased, used as primary key"],
        ["StrOrigin", "Source language text", "str", "Original game text with br-tags"],
        ["KR, EN, JP, ZH...", "Language columns", "str", "One column per target language"],
        ["DevMemo", "Developer notes", "str", "Internal comments from game XML"],
        ["Status", "Row editing state", "enum", "original / translated / reviewed"],
        ["ExportPath", "Source XML file path", "str", "Relative path within game data"],
    ]
    story.append(make_table(["Field", "Description", "Type", "Notes"], row_fields, [70, 110, 35, 265]))

    story.append(PageBreak())


def build_megaindex(story, styles):
    """Page 4: MegaIndex - Game Data Indexing."""
    add_page_header(story, styles, "MegaIndex \u2014 Game Data Indexing", 4)

    story.append(Paragraph(
        "MegaIndex is the unified in-memory game data index. It parses ALL game data XML files "
        "(items, quests, skills, NPCs, audio events, textures) into <b>35 dictionaries</b> with "
        "O(1) lookups in every direction. Built via a 7-phase pipeline at application startup.",
        styles['BodyText2']))

    story.append(Paragraph("7-Phase Build Pipeline", styles['SectionHead']))
    phase_rows = [
        ["Phase 1", "Foundation", "Scan DDS textures, WEM audio files (3 language folders), parse KnowledgeInfo XMLs, build knowledge groups"],
        ["Phase 2", "Entity Parse", "Parse Characters, Items (with InspectKnowledge), Regions, Factions, Skills, Gimmicks, Quests from StaticInfo XMLs"],
        ["Phase 3", "Localization", "Parse export .loc.xml files: event-to-StringID mapping (D11), StringID-to-StrOrigin (D12), translations (D13), export file index (D17/D18)"],
        ["Phase 4", "VRS Reorder", "Voice Recording Script reorder: sort events by (export_path, xml_order, event_name) for audio codex navigation"],
        ["Phase 5", "Broad Scan", "Parse DevMemo fields from all XML files (D19)"],
        ["Phase 6", "Reverse Dicts", "Build 7 reverse lookup dicts: R1 (Korean name/desc), R2 (knowledge_key), R3 (StringID-to-event), R4-R7 (texture, source, origin, group)"],
        ["Phase 7", "Composed Dicts", "Build bridge dicts: C1 (entity-to-image via 4-phase DDS), C2-C5 (audio/script), C6/C7 (entity-StringID bridge for grid images)"],
    ]
    story.append(make_table(["Phase", "Name", "Operations"], phase_rows, [45, 65, 370]))

    story.append(Paragraph("Entity Types Indexed", styles['SectionHead']))
    entity_rows = [
        ["Knowledge", "D1: knowledge_by_strkey", "KnowledgeEntry", "strkey, name, desc, ui_texture_name, group_key, source_file"],
        ["Character", "D2: character_by_strkey", "CharacterEntry", "strkey, name, desc, knowledge_key, use_macro, age, job"],
        ["Item", "D3: item_by_strkey", "ItemEntry", "strkey, name, desc, knowledge_key, group_key, inspect_entries"],
        ["Region", "D4: region_by_strkey", "RegionEntry", "strkey, name, desc, world_position (x,y,z), node_type"],
        ["Faction", "D5: faction_by_strkey", "FactionEntry", "strkey, name, desc, group, knowledge_key"],
        ["Skill", "D7: skill_by_strkey", "SkillEntry", "strkey, name, desc, knowledge_key, source_file"],
        ["Gimmick", "D8: gimmick_by_strkey", "GimmickEntry", "strkey, name, desc, knowledge_key"],
        ["Quest", "D7b: quest_by_strkey", "QuestEntry", "strkey, name, desc, knowledge_key, source_file"],
    ]
    story.append(make_table(["Type", "Dict ID", "Schema", "Fields"], entity_rows, [55, 105, 75, 245]))

    story.append(Paragraph("4-Phase DDS Greedy Algorithm (Image Resolution)", styles['SectionHead']))
    story.append(Paragraph(
        "Resolves entity-to-image mappings through a cascading 4-phase algorithm. "
        "Each phase tries progressively broader strategies until an image is found:",
        styles['BodyText2']))
    dds_rows = [
        ["Phase A", "Knowledge UITextureName", "Direct lookup: entry.ui_texture_name in dds_by_stem (D9)"],
        ["Phase B", "Greedy XML Attr Scan", "During entity parsing, collect ALL texture-like attribute values; match against DDS stems"],
        ["Phase C", "knowledge_key Chain", "Follow knowledge_key to KnowledgeEntry, use its ui_texture_name for DDS lookup"],
        ["Phase D", "Korean Name R1 Fallback", "Match entity's Korean name/desc in R1 index; follow chain to find an entity that HAS an image"],
    ]
    story.append(make_table(["Phase", "Strategy", "Description"], dds_rows, [50, 115, 315]))

    story.append(Paragraph(
        "All schemas are frozen dataclasses with <font face='Courier'>__slots__</font> for memory efficiency. "
        "The MegaIndex class uses cooperative multiple inheritance (MRO) with 4 mixins: "
        "DataParsersMixin, EntityParsersMixin, BuildersMixin, and ApiMixin.",
        styles['SmallNote']))

    story.append(PageBreak())


def build_translation_memory(story, styles):
    """Page 5: Translation Memory."""
    add_page_header(story, styles, "Translation Memory (TM) System", 5)

    story.append(Paragraph(
        "The Translation Memory system provides multi-tier search combining exact hash matching "
        "with semantic vector similarity. TM entries are stored in the database and indexed using "
        "FAISS HNSW vectors for fast approximate nearest-neighbor search.",
        styles['BodyText2']))

    story.append(Paragraph("TM Index Architecture", styles['SectionHead']))

    # TM architecture diagram
    dw, dh = 460, 120
    d = Drawing(dw, dh)

    # Input
    draw_box(d, 10, 75, 80, 30, "TM Entries", HexColor("#1565C0"), white, 8)
    draw_arrow_right(d, 90, 90, 120, FASTAPI_GREEN)

    # TMIndexer
    draw_box(d, 120, 65, 100, 50, "TMIndexer", FASTAPI_GREEN, white, 10)
    draw_arrow_right(d, 220, 90, 250, FASTAPI_GREEN)

    # Output indexes
    draw_box(d, 250, 95, 90, 22, "Hash Index", HexColor("#E65100"), white, 8)
    draw_box(d, 250, 68, 90, 22, "FAISS HNSW", HexColor("#6A1B9A"), white, 8)
    draw_box(d, 250, 41, 90, 22, "Embeddings", HexColor("#2E7D32"), white, 8)

    # Search tiers
    draw_arrow_right(d, 340, 106, 370, HexColor("#E65100"))
    draw_arrow_right(d, 340, 79, 370, HexColor("#6A1B9A"))

    draw_box(d, 370, 95, 80, 22, "Tier 1: Exact", HexColor("#E65100"), white, 7)
    draw_box(d, 370, 68, 80, 22, "Tier 2: Fuzzy", HexColor("#6A1B9A"), white, 7)

    # Storage label
    s = String(160, 15, "Storage: server/data/ldm_tm/{tm_id}/", textAnchor='middle',
               fontSize=7, fontName='Courier', fillColor=TEXT_LIGHT)
    d.add(s)

    story.append(d)

    story.append(Paragraph("Search Tiers", styles['SectionHead']))
    tier_rows = [
        ["Tier 1", "Whole Hash", "Exact match on normalized full text", "O(1) dict lookup", "100%"],
        ["Tier 2", "Whole FAISS", "Semantic similarity on full segment", "HNSW ANN search", "Configurable"],
        ["Tier 3", "Line Hash", "Exact match on individual lines (br-tag split)", "O(1) dict lookup", "100%"],
        ["Tier 4", "Line FAISS", "Semantic similarity on individual lines", "HNSW ANN search", "Configurable"],
    ]
    story.append(make_table(["Tier", "Name", "Strategy", "Algorithm", "Precision"],
                            tier_rows, [35, 65, 150, 95, 55]))

    story.append(Paragraph("Embedding Pipeline", styles['SectionHead']))
    story.append(bullet("<b>Model:</b> Model2Vec (loaded at startup). Produces dense sentence embeddings for semantic search", styles))
    story.append(bullet("<b>Index:</b> FAISS HNSW (Hierarchical Navigable Small World) for fast ANN queries", styles))
    story.append(bullet("<b>Normalization:</b> Text normalized before embedding (whitespace collapse, br-tag removal, placeholder stripping)", styles))
    story.append(bullet("<b>Storage:</b> Embeddings as .npy, FAISS indexes as .index, hash lookups as .pkl", styles))
    story.append(bullet("<b>Aho-Corasick:</b> pyahocorasick automaton for multi-pattern exact text search across TM entries", styles))

    story.append(Paragraph("Merge System (6 Match Modes)", styles['SectionHead']))
    merge_rows = [
        ["strict", "StringID + StrOrigin must both match exactly"],
        ["stringid_only", "Match by StringID alone (ignore text differences)"],
        ["strorigin_only", "Match by source text alone (ignore StringID)"],
        ["strorigin_descorigin", "Match by source text OR description origin"],
        ["strorigin_filename", "Match by source text, scoped to same filename"],
        ["fuzzy", "Fuzzy text matching using Model2Vec cosine similarity"],
    ]
    story.append(make_table(["Mode", "Description"], merge_rows, [110, 370]))

    story.append(Paragraph(
        "Merge paths: to-file (single target), to-folder (with suffix recognition), "
        "and DB+SSE (streaming progress via Server-Sent Events). All paths filter by "
        "<font face='Courier'>status == 'reviewed'</font> (only confirmed rows are merged).",
        styles['BodyText2']))

    story.append(PageBreak())


def build_audio_pipeline(story, styles):
    """Page 6: Audio Processing Pipeline."""
    add_page_header(story, styles, "Audio Processing Pipeline", 6)

    story.append(Paragraph(
        "LocaNext processes game audio files in Wwise's WEM format, converting them to WAV "
        "for playback via the Windows audio API. The architecture is ported from MapDataGenerator's "
        "AudioHandler for exact behavioral parity.",
        styles['BodyText2']))

    story.append(Paragraph("Conversion Pipeline", styles['SectionHead']))

    # Audio pipeline diagram
    dw, dh = 460, 70
    d = Drawing(dw, dh)
    y = 25
    steps = [
        ("WEM File\n(Wwise)", HexColor("#B71C1C")),
        ("vgmstream-cli\n(decode)", HexColor("#E65100")),
        ("WAV Cache\n(temp dir)", HexColor("#F9A825")),
        ("winsound\n(playback)", HexColor("#2E7D32")),
    ]
    for i, (label, col) in enumerate(steps):
        x = 10 + i * 118
        lines = label.split('\n')
        draw_box(d, x, y, 100, 30, lines[0], col, white, 8)
        if len(lines) > 1:
            s = String(x + 50, y - 2, lines[1], textAnchor='middle',
                       fontSize=7, fontName='Helvetica', fillColor=TEXT_LIGHT)
            d.add(s)
        if i < 3:
            draw_arrow_right(d, x + 100, y + 15, x + 118, FASTAPI_GREEN)

    story.append(d)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("Audio Playback Service", styles['SectionHead']))
    story.append(Paragraph(
        "The <font face='Courier'>AudioPlaybackService</font> is a thread-safe singleton ported from "
        "MapDataGenerator's <font face='Courier'>audio_handler.py</font>. Key design:",
        styles['BodyText2']))
    story.append(bullet("<b>winsound.PlaySound()</b> for synchronous playback in a background thread", styles))
    story.append(bullet("<b>Generation counter</b> prevents stale thread callbacks when tracks change rapidly", styles))
    story.append(bullet("<b>Thread-safe stop</b> via SND_PURGE + thread join", styles))
    story.append(bullet("<b>WAV cache</b> in temp directory; hashed filenames prevent re-conversion", styles))
    story.append(bullet("<b>Linux (DEV mode):</b> winsound unavailable; play() returns False gracefully", styles))

    story.append(Paragraph("Audio Folder Mapping", styles['SectionHead']))
    story.append(Paragraph(
        "Three audio folders are scanned during MegaIndex Phase 1, mapping languages to audio sources "
        "based on the game's voice recording structure:",
        styles['BodyText2']))

    audio_rows = [
        ["English(US)", "D10a: wem_by_event_en", "eng, fre, ger, spa-es, spa-mx, por-br, ita, rus, tur, pol", "Latin-script languages share English audio"],
        ["Korean", "D10b: wem_by_event_kr", "kor, jpn, zho-tw", "East Asian languages (except PRC Chinese)"],
        ["Chinese(PRC)", "D10c: wem_by_event_zh", "zho-cn", "Mainland Chinese audio"],
    ]
    story.append(make_table(["Audio Folder", "MegaIndex Dict", "Languages Routed", "Notes"],
                            audio_rows, [70, 100, 160, 150]))

    story.append(Paragraph("Audio Codex", styles['SectionHead']))
    story.append(Paragraph(
        "The Audio Codex provides a searchable catalog of all game audio events. It uses MegaIndex's "
        "D11 (event-to-StringID), C4/C5 (event-to-script Korean/English), and the VRS reorder from Phase 4 "
        "to present audio events sorted by (export_path, xml_order, event_name). "
        "The frontend displays a recursive explorer tree (unlimited depth) with auto-expand, "
        "and a player panel with Prev/Play/Stop/Next controls.",
        styles['BodyText2']))

    story.append(Paragraph("API Endpoints", styles['SectionHead']))
    api_rows = [
        ["POST /api/v2/audio/play", "Play audio by event name; converts WEM to WAV, plays via winsound"],
        ["POST /api/v2/audio/stop", "Stop current playback (SND_PURGE)"],
        ["GET /api/v2/audio/status", "Get playback status: is_playing, current_event, elapsed, duration"],
    ]
    story.append(make_table(["Endpoint", "Description"], api_rows, [160, 320]))

    story.append(PageBreak())


def build_image_processing(story, styles):
    """Page 7: Image Processing."""
    add_page_header(story, styles, "Image Processing Pipeline", 7)

    story.append(Paragraph(
        "LocaNext resolves game entity images from DDS (DirectDraw Surface) textures stored in the "
        "game's data files. The MediaConverter service handles DDS-to-PNG conversion with an LRU "
        "cache for performance. Image resolution leverages MegaIndex's 4-phase DDS Greedy algorithm.",
        styles['BodyText2']))

    story.append(Paragraph("DDS-to-PNG Conversion", styles['SectionHead']))
    story.append(bullet("<b>Input:</b> .dds texture files from game data (scanned in MegaIndex Phase 1, dict D9)", styles))
    story.append(bullet("<b>Conversion:</b> Pillow (PIL) opens DDS, converts to RGBA, thumbnails to max 256px", styles))
    story.append(bullet("<b>Cache:</b> OrderedDict-based LRU cache (500 entries default), keyed by path:size", styles))
    story.append(bullet("<b>Output:</b> PNG bytes served via streaming endpoint to frontend grid", styles))

    story.append(Paragraph("Image Resolution Chain", styles['SectionHead']))

    # Image resolution diagram
    dw, dh = 460, 120
    d = Drawing(dw, dh)

    draw_box(d, 10, 80, 80, 25, "Grid Row", HexColor("#1565C0"), white, 8)
    draw_arrow_right(d, 90, 92, 120, FASTAPI_GREEN)

    draw_box(d, 120, 80, 80, 25, "StringID", FASTAPI_GREEN, white, 8)
    draw_arrow_right(d, 200, 92, 230, FASTAPI_GREEN)

    draw_box(d, 230, 80, 70, 25, "C7 Bridge", HexColor("#E65100"), white, 8)
    draw_arrow_right(d, 300, 92, 330, FASTAPI_GREEN)

    draw_box(d, 330, 80, 70, 25, "Entity", HexColor("#6A1B9A"), white, 8)
    draw_arrow_right(d, 400, 92, 430, FASTAPI_GREEN)

    draw_box(d, 430, 80, 20, 25, "", HexColor("#2E7D32"), white, 8)

    # C6 label
    s = String(265, 112, "C7: stringid_to_entity", textAnchor='middle',
               fontSize=7, fontName='Courier', fillColor=TEXT_LIGHT)
    d.add(s)

    # Image result
    draw_box(d, 330, 30, 120, 25, "C1: DDS Image Path", HexColor("#2E7D32"), white, 8)
    draw_arrow_down(d, 365, 80, 57, HexColor("#2E7D32"))

    # PNG conversion
    draw_box(d, 150, 30, 120, 25, "MediaConverter", HexColor("#455A64"), white, 8)
    draw_arrow_right(d, 270, 42, 330, HexColor("#2E7D32"))

    # PNG output
    draw_box(d, 30, 30, 100, 25, "PNG (cached)", HexColor("#E65100"), white, 8)
    draw_arrow_right(d, 130, 42, 150, HexColor("#455A64"))

    story.append(d)

    story.append(Paragraph("MapDataService", styles['SectionHead']))
    story.append(Paragraph(
        "The <font face='Courier'>MapDataService</font> provides the high-level API for image and audio "
        "context lookups. It indexes entries under multiple keys (StrKey, StringID, KnowledgeKey) for "
        "robust lookup. Initialized AFTER MegaIndex build completes (in 3 init points: mega_index route, "
        "PROD lifespan, DEV lifespan).",
        styles['BodyText2']))

    story.append(Paragraph("Batch Preload", styles['SectionHead']))
    story.append(Paragraph(
        "When the grid loads, images are batch-preloaded for visible rows. The frontend sends "
        "a batch of StringIDs, and the backend resolves images in parallel, returning PNG thumbnails. "
        "Image URLs use the pattern <font face='Courier'>/api/ldm/media/image/{strkey}</font> which "
        "triggers on-demand DDS-to-PNG conversion with cache lookup.",
        styles['BodyText2']))

    story.append(Paragraph("Image Context Response", styles['SectionHead']))
    img_fields = [
        ["texture_name", "str", "UITextureName from entity data"],
        ["dds_path", "str", "Absolute path to DDS file on disk"],
        ["thumbnail_url", "str", "API endpoint for PNG thumbnail"],
        ["has_image", "bool", "Whether an image was resolved"],
        ["fallback_reason", "str", "Why lookup failed (empty = found)"],
    ]
    story.append(make_table(["Field", "Type", "Description"], img_fields, [90, 40, 350]))

    story.append(PageBreak())


def build_realtime(story, styles):
    """Page 8: Real-Time Collaboration."""
    add_page_header(story, styles, "Real-Time Collaboration", 8)

    story.append(Paragraph(
        "LocaNext supports multi-user real-time collaboration via Socket.IO (python-socketio). "
        "When multiple translators work on the same file, they see each other's presence, "
        "cell edits broadcast in real-time, and row-level locking prevents conflicts.",
        styles['BodyText2']))

    story.append(Paragraph("WebSocket Event Architecture", styles['SectionHead']))

    ws_rows = [
        ["ldm_join_file", "Client -> Server", "Join a file room for real-time updates. Broadcasts presence to all viewers"],
        ["ldm_leave_file", "Client -> Server", "Leave the file room. Releases any held row locks"],
        ["ldm_lock_row", "Client -> Server", "Acquire exclusive lock on a row for editing. Rejects if already locked"],
        ["ldm_unlock_row", "Client -> Server", "Release row lock after editing is complete"],
        ["ldm_cell_update", "Server -> Room", "Broadcast cell value change to all viewers of the file"],
        ["ldm_file_joined", "Server -> Client", "Confirm file room join with current viewer list"],
        ["ldm_presence_update", "Server -> Room", "Updated list of users viewing the file"],
        ["ldm_row_locked", "Server -> Room", "Notify all viewers that a row is now locked by a user"],
        ["ldm_row_unlocked", "Server -> Room", "Notify all viewers that a row lock was released"],
    ]
    story.append(make_table(["Event", "Direction", "Description"], ws_rows, [100, 80, 300]))

    story.append(Paragraph("Optimistic UI Pattern", styles['SectionHead']))
    story.append(Paragraph(
        "LocaNext mandates Optimistic UI for all user interactions. The pattern:",
        styles['BodyText2']))
    story.append(bullet("<b>1. User edits a cell</b> -- UI updates INSTANTLY (no loading spinner)", styles))
    story.append(bullet("<b>2. API call fires</b> in background (PATCH /api/ldm/rows/{id})", styles))
    story.append(bullet("<b>3. Success:</b> WebSocket broadcasts change to other viewers", styles))
    story.append(bullet("<b>4. Failure:</b> UI REVERTS to previous value, shows error toast", styles))

    story.append(Paragraph("Conflict Resolution", styles['SectionHead']))
    story.append(bullet("<b>Row-level locking:</b> Only one user can edit a row at a time. Lock held during edit, released on blur/save", styles))
    story.append(bullet("<b>Last-write-wins:</b> For cell values within a locked row, the last write is authoritative", styles))
    story.append(bullet("<b>Presence tracking:</b> Server maintains viewer sets per file room; disconnects auto-release locks", styles))

    story.append(Paragraph("State Management", styles['SectionHead']))
    story.append(code_block(
        "# Server-side state (in-memory)\n"
        "ldm_file_viewers: Dict[int, Set[tuple]]  # file_id -> {(sid, user_id, username)}\n"
        "ldm_row_locks: Dict[tuple, Dict]          # (file_id, row_id) -> {sid, user_id, ...}",
        styles))

    story.append(PageBreak())


def build_api_architecture(story, styles):
    """Page 9: API Architecture."""
    add_page_header(story, styles, "API Architecture", 9)

    story.append(Paragraph(
        "The backend exposes a comprehensive REST API via FastAPI with automatic OpenAPI documentation. "
        "The API is organized into modular routers, with authentication, CORS, and IP filtering middleware.",
        styles['BodyText2']))

    story.append(Paragraph("Router Organization", styles['SectionHead']))
    router_rows = [
        ["/api/ldm/", "LDM (main tool)", "40+ routes across 20+ sub-routers: files, rows, TM, merge, codex, search, settings"],
        ["/api/v2/xlstransfer/", "XLSTransfer", "XML-to-Excel and Excel-to-XML conversion endpoints"],
        ["/api/v2/quicksearch/", "QuickSearch", "Fast text search across loaded files"],
        ["/api/v2/krsimilar/", "KRSimilar", "Korean text similarity search"],
        ["/api/v2/admin/", "Admin", "User management, stats, telemetry, logs, server config"],
        ["/api/v2/audio/", "Audio", "Play, stop, status for audio playback"],
        ["/health", "Health", "Server health check with uptime, version, mode"],
    ]
    story.append(make_table(["Prefix", "Module", "Description"], router_rows, [100, 75, 305]))

    story.append(Paragraph("LDM Sub-Routers (Detail)", styles['SectionHead']))
    ldm_rows = [
        ["health.py", "Health check"],
        ["files.py", "File upload, download, list, delete"],
        ["rows.py", "Row CRUD + project tree"],
        ["tm_crud.py", "TM upload, list, delete, export (TMX)"],
        ["tm_search.py", "TM suggest / semantic search"],
        ["tm_indexes.py", "TM index build / sync"],
        ["merge.py", "Game dev merge (6 match modes)"],
        ["merge_to_disk.py", "QT-style merge to disk files"],
        ["codex.py", "Game data codex (browse entities)"],
        ["codex_audio.py", "Audio codex (browse audio events)"],
        ["codex_items/skills/quests/...", "Entity-specific codex pages"],
        ["mapdata.py", "Image/audio context for grid rows"],
        ["semantic_search.py", "FAISS-powered semantic search"],
        ["worldmap.py", "World map data (region positions)"],
    ]
    story.append(make_table(["Router", "Purpose"], ldm_rows, [130, 350]))

    story.append(Paragraph("Middleware Stack", styles['SectionHead']))
    story.append(bullet("<b>CORS:</b> Configured for Electron origin (localhost) + development ports", styles))
    story.append(bullet("<b>Authentication:</b> JWT token validation via <font face='Courier'>get_current_active_user_async</font>", styles))
    story.append(bullet("<b>IP Filtering:</b> Optional whitelist for server mode deployments", styles))
    story.append(bullet("<b>SSE Streaming:</b> Server-Sent Events for long-running operations (merge, export, index build)", styles))
    story.append(bullet("<b>BaseToolAPI:</b> Shared pattern for tool APIs (reduces boilerplate by ~73%)", styles))

    story.append(Paragraph("API Design Patterns", styles['SectionHead']))
    story.append(code_block(
        "# BaseToolAPI pattern (shared by XLSTransfer, QuickSearch, KRSimilar)\n"
        "class XLSTransferAPI(BaseToolAPI):\n"
        "    def __init__(self):\n"
        "        super().__init__(tool_name='XLSTransfer',\n"
        "                         router_prefix='/api/v2/xlstransfer')\n"
        "# Reduces 1105 lines -> ~300 lines per tool API",
        styles))

    story.append(PageBreak())


def build_performance(story, styles):
    """Page 10: Performance Characteristics."""
    add_page_header(story, styles, "Performance Characteristics", 10)

    story.append(Paragraph(
        "LocaNext is optimized for handling large game localization datasets (100K+ rows per file, "
        "thousands of game entities). Performance is achieved through bulk operations, in-memory "
        "indexing, client-side processing, and efficient data structures.",
        styles['BodyText2']))

    story.append(Paragraph("Database Performance", styles['SectionHead']))
    db_rows = [
        ["Bulk Insert (PG)", "COPY protocol", "Streams rows directly into PostgreSQL; bypasses ORM overhead entirely"],
        ["Bulk Insert (SQLite)", "executemany (4x batch)", "Batched inserts with WAL mode for concurrent reads during write"],
        ["Full-Text Search (PG)", "FTS GIN index", "Built at PG startup; supports Korean text tokenization"],
        ["Full-Text Search (SQLite)", "FTS5 virtual table", "Shadow tables with unicode61 tokenizer for CJK support"],
        ["Bulk Update", "No-SELECT pattern", "UPDATE without prior SELECT; avoids N+1 query overhead"],
    ]
    story.append(make_table(["Operation", "Technique", "Details"], db_rows, [95, 95, 290]))

    story.append(Paragraph("In-Memory Performance", styles['SectionHead']))
    mem_rows = [
        ["MegaIndex", "35 dicts, O(1) lookup", "Frozen dataclasses with __slots__; cooperative MRO with 4 mixins"],
        ["DDS Cache", "OrderedDict LRU (500)", "PNG bytes cached; eviction on overflow; keyed by path:size"],
        ["WAV Cache", "Disk-based (temp dir)", "Hashed filenames prevent re-conversion; persistent across sessions"],
        ["Hash Index", "Pickle dicts", "Whole-segment and line-level hash tables for O(1) TM exact match"],
        ["FAISS HNSW", "Vector index", "Approximate nearest neighbor; sub-millisecond query on 100K+ entries"],
    ]
    story.append(make_table(["Component", "Strategy", "Details"], mem_rows, [75, 115, 290]))

    story.append(Paragraph("Client-Side Optimization", styles['SectionHead']))
    story.append(bullet("<b>Bulk Load:</b> ALL rows sent to client on file open. Zero server round-trips for search/filter/scroll", styles))
    story.append(bullet("<b>Virtual Scroll:</b> Renders only visible rows (100K+ supported). Content-aware row heights computed once", styles))
    story.append(bullet("<b>Client Search:</b> Filtering, text search, and column sorting happen entirely in the browser", styles))
    story.append(bullet("<b>Optimistic Save:</b> Cell edits update UI instantly; API call fires in background", styles))

    story.append(Paragraph("Async Architecture", styles['SectionHead']))
    story.append(bullet("<b>MegaIndex build:</b> Runs via <font face='Courier'>asyncio.to_thread()</font> -- non-blocking, doesn't freeze the API", styles))
    story.append(bullet("<b>SSE streaming:</b> Long operations (merge, export) stream progress via Server-Sent Events", styles))
    story.append(bullet("<b>WebSocket:</b> python-socketio async handlers for real-time collaboration", styles))
    story.append(bullet("<b>File parsing:</b> Async endpoints with background task support for large files", styles))

    story.append(Paragraph("Key Metrics", styles['SectionHead']))
    metric_rows = [
        ["File open (10K rows)", "Bulk load + client transfer", "< 2 seconds"],
        ["MegaIndex build", "7-phase pipeline (all game data)", "5-15 seconds (depends on game size)"],
        ["TM search (100K entries)", "FAISS HNSW query", "< 50ms per query"],
        ["Image resolution", "DDS-to-PNG (cached)", "< 10ms (cache hit), ~100ms (cache miss)"],
        ["Cell edit round-trip", "Optimistic UI + API", "0ms perceived (async save)"],
        ["Virtual scroll render", "Content-aware heights", "60fps at 100K+ rows"],
    ]
    story.append(make_table(["Operation", "Method", "Typical Time"], metric_rows, [110, 160, 110]))


# ============================================================================
# Cover Page Background
# ============================================================================

def cover_page_bg(canvas, doc):
    """Dark background for cover page."""
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    # Green accent bar at top
    canvas.setFillColor(FASTAPI_GREEN)
    canvas.rect(0, A4[1] - 8*mm, A4[0], 8*mm, fill=1, stroke=0)

    # Green accent bar at bottom
    canvas.rect(0, 0, A4[0], 4*mm, fill=1, stroke=0)

    # Decorative circuit-like lines
    canvas.setStrokeColor(HexColor("#2a2a4e"))
    canvas.setLineWidth(0.3)
    for y_offset in range(50, int(A4[1]), 40):
        canvas.line(20*mm, y_offset, A4[0] - 20*mm, y_offset)

    canvas.restoreState()


def regular_page_bg(canvas, doc):
    """Regular page background with header/footer."""
    canvas.saveState()

    # Green top bar
    canvas.setFillColor(FASTAPI_GREEN)
    canvas.rect(0, A4[1] - 4*mm, A4[0], 4*mm, fill=1, stroke=0)

    # Footer
    canvas.setFillColor(HexColor("#F5F5F5"))
    canvas.rect(0, 0, A4[0], 12*mm, fill=1, stroke=0)
    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(20*mm, 5*mm, "LocaNext Backend Architecture")
    canvas.drawRightString(A4[0] - 20*mm, 5*mm, f"Page {doc.page}")

    # Thin green line above footer
    canvas.setStrokeColor(FASTAPI_GREEN)
    canvas.setLineWidth(0.5)
    canvas.line(15*mm, 12*mm, A4[0] - 15*mm, 12*mm)

    canvas.restoreState()


# ============================================================================
# Main
# ============================================================================

def main():
    output_path = Path(__file__).parent / "LocaNext_Backend_Architecture.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = create_styles()
    story = []

    # Page 1: Cover
    build_cover(story, styles)

    # Pages 2-10: Content
    build_system_overview(story, styles)
    build_file_parsing(story, styles)
    build_megaindex(story, styles)
    build_translation_memory(story, styles)
    build_audio_pipeline(story, styles)
    build_image_processing(story, styles)
    build_realtime(story, styles)
    build_api_architecture(story, styles)
    build_performance(story, styles)

    # Build PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=18*mm,
        bottomMargin=18*mm,
        leftMargin=15*mm,
        rightMargin=15*mm,
        title="LocaNext Backend Architecture",
        author="LocaNext Engineering",
        subject="File Parsing, Indexing, and Media Processing Pipeline",
    )

    doc.build(
        story,
        onFirstPage=cover_page_bg,
        onLaterPages=regular_page_bg,
    )

    print(f"PDF generated: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
