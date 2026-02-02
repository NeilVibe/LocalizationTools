# QuickTranslate Documentation

This folder contains the user guide and documentation for QuickTranslate.

## Files

| File | Description |
|------|-------------|
| `USER_GUIDE.md` | Complete user guide in Markdown format |
| `style.css` | CSS stylesheet for PDF generation |
| `README.md` | This file |

## Generating PDF

### Option 1: Pandoc + WeasyPrint (Recommended)

**Install dependencies:**
```bash
# Windows (with Chocolatey)
choco install pandoc
pip install weasyprint

# Linux
sudo apt install pandoc
pip install weasyprint
```

**Generate PDF:**
```bash
pandoc USER_GUIDE.md -o QuickTranslate_UserGuide.pdf \
    --pdf-engine=weasyprint \
    --css=style.css \
    --metadata title="QuickTranslate User Guide" \
    --toc \
    --toc-depth=3
```

### Option 2: Pandoc + wkhtmltopdf

**Install dependencies:**
```bash
choco install pandoc wkhtmltopdf
```

**Generate PDF:**
```bash
pandoc USER_GUIDE.md -o QuickTranslate_UserGuide.pdf \
    --pdf-engine=wkhtmltopdf \
    --css=style.css \
    --toc
```

### Option 3: VS Code Extension

1. Install "Markdown PDF" extension in VS Code
2. Open `USER_GUIDE.md`
3. Press `Ctrl+Shift+P` → "Markdown PDF: Export (pdf)"

### Option 4: Typora

1. Open `USER_GUIDE.md` in Typora
2. File → Export → PDF
3. Configure theme in Preferences → Export → PDF

### Option 5: Online Converter

1. Copy content from `USER_GUIDE.md`
2. Paste into [MarkdownToPDF.com](https://www.markdowntopdf.com/)
3. Download PDF

## Styling the PDF

The `style.css` file provides professional styling:

### Colors
- **Primary Blue** `#2563EB` - Headers, links
- **Success Green** `#059669` - Pro tips
- **Warning Amber** `#D97706` - Warnings
- **Info Purple** `#7C3AED` - Notes

### Callout Boxes

Use blockquotes with emoji markers:

```markdown
> 💡 **PRO TIP**
>
> Your helpful tip here.

> ⚠️ **WARNING**
>
> Important warning here.

> ℹ️ **NOTE**
>
> Informational note here.

> 🎉 **SUCCESS!**
>
> Success message here.
```

### Fonts

The stylesheet uses:
- **Inter** for headings and body text
- **JetBrains Mono** for code

Install these fonts for best results:
- [Inter](https://fonts.google.com/specimen/Inter)
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/)

## Updating the Guide

1. Edit `USER_GUIDE.md`
2. Preview in VS Code or Typora
3. Regenerate PDF
4. Commit both `.md` and `.pdf` files

## Screenshots

To add screenshots:

1. Take screenshot (PNG format, high resolution)
2. Save to `docs/images/` folder
3. Reference in Markdown:
   ```markdown
   ![Main Window](images/main-window.png)
   ```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | Feb 2026 | Initial comprehensive guide |
