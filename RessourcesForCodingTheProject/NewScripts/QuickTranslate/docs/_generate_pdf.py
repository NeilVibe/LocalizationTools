#!/usr/bin/env python3
"""Generate beautiful PDF user guides from markdown using weasyprint."""

import sys
import markdown
from pathlib import Path

# markdown extensions for tables + code blocks + toc
MD_EXTENSIONS = ["tables", "fenced_code", "codehilite", "toc"]

CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 22mm 18mm;

    @top-right {
        content: "QuickTranslate v7.0";
        font-family: 'NanumSquare', 'Segoe UI', sans-serif;
        font-size: 8pt;
        color: #8899aa;
    }
    @bottom-center {
        content: counter(page);
        font-family: 'NanumSquare', 'Segoe UI', sans-serif;
        font-size: 9pt;
        color: #667788;
    }
}

@page :first {
    @top-right { content: none; }
}

:root {
    --accent: #2563eb;
    --accent-light: #dbeafe;
    --accent-dark: #1e40af;
    --bg-code: #f1f5f9;
    --border: #cbd5e1;
    --text: #1e293b;
    --text-secondary: #475569;
    --header-bg: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
    --success: #059669;
    --warning: #d97706;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'NanumSquare', 'NanumGothic', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: var(--text);
}

/* ─── Title ─── */
h1 {
    font-size: 22pt;
    font-weight: 800;
    color: white;
    background: var(--header-bg);
    padding: 18px 24px;
    margin: 0 -18mm 12px -18mm;
    padding-left: 18mm;
    padding-right: 18mm;
    border-radius: 0;
    letter-spacing: -0.5px;
}

h1 + p {
    margin-top: -6px;
    margin-bottom: 14px;
    font-size: 10pt;
    color: var(--text-secondary);
}

/* ─── Section Headers ─── */
h2 {
    font-size: 14pt;
    font-weight: 700;
    color: var(--accent-dark);
    border-bottom: 2.5px solid var(--accent);
    padding-bottom: 4px;
    margin-top: 18px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    font-weight: 700;
    color: var(--accent);
    margin-top: 12px;
    margin-bottom: 6px;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    font-weight: 700;
    color: var(--text);
    margin-top: 8px;
    margin-bottom: 4px;
}

/* ─── Paragraphs ─── */
p {
    margin-bottom: 8px;
}

strong {
    color: var(--accent-dark);
}

/* ─── Tables ─── */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 9pt;
    page-break-inside: avoid;
}

thead th {
    background: var(--accent);
    color: white;
    font-weight: 700;
    text-align: left;
    padding: 6px 10px;
    border: 1px solid var(--accent-dark);
    font-size: 9pt;
}

/* Center-aligned header cells (from markdown :--:) */
th[style*="text-align: center"] {
    text-align: center !important;
}

tbody td {
    padding: 5px 10px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}

tbody tr:nth-child(even) {
    background: #f8fafc;
}

tbody tr:hover {
    background: var(--accent-light);
}

/* First column bold in reference tables */
tbody td:first-child {
    font-weight: 600;
    color: var(--text);
}

/* ─── Code blocks ─── */
pre {
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    padding: 10px 14px;
    font-family: 'NanumGothicCoding', 'Consolas', 'Monaco', monospace;
    font-size: 8.5pt;
    line-height: 1.5;
    margin: 6px 0 10px 0;
    overflow-x: auto;
    page-break-inside: avoid;
    white-space: pre-wrap;
    word-wrap: break-word;
}

code {
    font-family: 'NanumGothicCoding', 'Consolas', 'Monaco', monospace;
    font-size: 8.5pt;
    background: var(--bg-code);
    padding: 1px 4px;
    border-radius: 3px;
    color: #c7254e;
}

pre code {
    background: none;
    padding: 0;
    color: var(--text);
}

/* ─── Horizontal rules ─── */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 14px 0;
}

/* ─── Lists ─── */
ul, ol {
    margin: 4px 0 8px 20px;
}

li {
    margin-bottom: 3px;
}

/* ─── Blockquotes ─── */
blockquote {
    border-left: 3px solid var(--accent);
    background: var(--accent-light);
    padding: 8px 14px;
    margin: 8px 0;
    border-radius: 0 4px 4px 0;
    font-style: italic;
    color: var(--text-secondary);
}

/* ─── Page breaks ─── */
h2 {
    page-break-before: auto;
}
"""


def md_to_pdf(md_path: Path, pdf_path: Path):
    """Convert a markdown file to a styled PDF."""
    from weasyprint import HTML

    md_text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=MD_EXTENSIONS)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    HTML(string=full_html).write_pdf(str(pdf_path))
    size_kb = pdf_path.stat().st_size / 1024
    print(f"  ✓ {pdf_path.name} ({size_kb:.0f} KB)")


def main():
    docs_dir = Path(__file__).parent

    print("Generating QuickTranslate User Guide PDFs...\n")

    # Korean first (most important)
    kr_md = docs_dir / "USER_GUIDE_KR.md"
    kr_pdf = docs_dir / "QuickTranslate_UserGuide_KR.pdf"
    if kr_md.exists():
        print("  Korean...")
        md_to_pdf(kr_md, kr_pdf)
    else:
        print(f"  ✗ {kr_md} not found")

    # English
    en_md = docs_dir / "USER_GUIDE.md"
    en_pdf = docs_dir / "QuickTranslate_UserGuide.pdf"
    if en_md.exists():
        print("  English...")
        md_to_pdf(en_md, en_pdf)
    else:
        print(f"  ✗ {en_md} not found")

    print("\nDone!")


if __name__ == "__main__":
    main()
