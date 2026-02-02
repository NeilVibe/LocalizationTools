#!/usr/bin/env python3
"""
Generate PDF from USER_GUIDE.md

Usage:
    python generate_pdf.py

Requirements:
    pip install markdown weasyprint pygments
"""

import sys
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    missing = []

    try:
        import markdown
    except ImportError:
        missing.append("markdown")

    try:
        import weasyprint
    except ImportError:
        missing.append("weasyprint")

    if missing:
        print("Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)

def generate_pdf():
    """Convert USER_GUIDE.md to PDF."""
    check_dependencies()

    import markdown
    from weasyprint import HTML, CSS

    # Paths
    docs_dir = Path(__file__).parent
    md_file = docs_dir / "USER_GUIDE.md"
    css_file = docs_dir / "style.css"
    output_file = docs_dir / "QuickTranslate_UserGuide.pdf"

    # Check files exist
    if not md_file.exists():
        print(f"Error: {md_file} not found")
        sys.exit(1)

    print(f"Reading {md_file.name}...")
    md_content = md_file.read_text(encoding="utf-8")

    # Convert Markdown to HTML
    print("Converting Markdown to HTML...")
    md = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "attr_list",
            "md_in_html",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": False,
            },
            "toc": {
                "permalink": False,
                "toc_depth": 3,
            },
        }
    )
    html_content = md.convert(md_content)

    # Wrap in HTML document
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickTranslate User Guide</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap" rel="stylesheet">
</head>
<body>
{html_content}
</body>
</html>
"""

    # Load CSS
    css_content = ""
    if css_file.exists():
        print(f"Loading {css_file.name}...")
        css_content = css_file.read_text(encoding="utf-8")

    # Generate PDF
    print(f"Generating {output_file.name}...")
    html = HTML(string=html_doc, base_url=str(docs_dir))
    css = CSS(string=css_content)
    html.write_pdf(output_file, stylesheets=[css])

    print(f"\n✓ PDF generated: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.1f} KB")

def main():
    """Main entry point."""
    print("=" * 50)
    print("QuickTranslate User Guide PDF Generator")
    print("=" * 50)
    print()

    try:
        generate_pdf()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
