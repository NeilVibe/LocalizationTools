# ExcelRegex

**Purpose**: Utility scripts for regex operations on Excel files

**Created**: 2025-12-05
**Status**: Active

---

## Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `cell_parser.py` | Parse `<<header::value>>` cells into columns | Done |

---

## cell_parser.py

**Input**: Excel with cells like:
```
<<Korean::안녕>><<English::Hello>><<Type::Greeting>>
```

**Output**: Nicely formatted Excel with:
- Headers as columns (green, bold, thick border)
- Values expanded into rows
- Alternating row colors (orange)
- Auto column widths

**Usage**:
```bash
python cell_parser.py
# Select file → Output saved as [name]_parsed.xlsx
```

---

## Dependencies

```bash
pip install openpyxl
```
