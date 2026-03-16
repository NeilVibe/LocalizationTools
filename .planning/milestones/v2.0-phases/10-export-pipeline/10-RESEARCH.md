# Phase 10: Export Pipeline - Research

**Researched:** 2026-03-15
**Domain:** XML/Excel/Text export with data integrity, br-tag preservation
**Confidence:** HIGH

## Summary

Phase 10 delivers three export formats (XML, Excel, plain text) from LocaNext's in-memory row data. The critical insight is that **all three export builders already exist** in `server/tools/ldm/routes/files.py` (`_build_xml_file_from_dicts`, `_build_excel_file_from_dicts`, `_build_txt_file_from_dicts`) and are wired to the `/api/ldm/files/{file_id}/download` endpoint. However, **all three have serious deficiencies** that must be fixed:

1. **XML export uses stdlib ET** -- loses attribute case (lowercases everything), does not preserve original casing of StringId/StrOrigin/Str. Uses `minidom.toprettyxml` which is fragile. Must be migrated to lxml with `etree.tostring(pretty_print=True)` to match the rest of the pipeline.

2. **Excel export uses openpyxl** -- violates the project rule "xlsxwriter for writing, openpyxl only for reading." Must be rewritten using xlsxwriter with the proper EU column structure from LanguageDataExporter: `StrOrigin | ENG | Str | Correction | Text State | STATUS | COMMENT | MEMO1 | MEMO2 | Category | FileName | StringID | DescOrigin | Desc`.

3. **Text export** -- functional but needs proper column structure (StringID + source + translation, tab-delimited).

The core challenge is **br-tag round-trip integrity**. In-memory values use `<br/>`. When lxml writes XML attributes, it auto-escapes to `&lt;br/&gt;` on disk -- this is correct and happens automatically. The existing stdlib ET export also does this, but since we are migrating to lxml for consistency, the lxml auto-escaping gives us this for free. The existing integration test `test_export_roundtrip.py` validates this behavior.

**Primary recommendation:** Refactor the three `_build_*_from_dicts` functions into a proper `ExportService` class under `server/tools/ldm/services/export_service.py`, fix the XML/Excel implementations, and add a new `/api/ldm/files/{file_id}/export` endpoint that supports format selection (xml, xlsx, txt) while keeping the existing download endpoint backward-compatible.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TMERGE-05 | Export produces correct XML with br-tag preservation | lxml `etree.tostring()` auto-escapes `<br/>` to `&lt;br/&gt;` in attributes. Migrate from stdlib ET to lxml. Use `raw_attribs` pattern from ExtractAnything for full attribute reconstruction. Existing integration test validates round-trip. |
| TMERGE-06 | Export produces Excel format with correct column structure | Use xlsxwriter (NOT openpyxl) with EU column order: StrOrigin, ENG, Str, Correction, Text State, STATUS, COMMENT, MEMO1, MEMO2, Category, FileName, StringID, DescOrigin, Desc. Port formatting from LanguageDataExporter `excel_writer.py`. |
| TMERGE-07 | Export produces plain tabulated text (StringID + source + translation) | Tab-delimited format: `StringID\tStrOrigin\tStr`. Simple text builder, no special libraries needed. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=4.9.0 | XML serialization with auto-escaping | Already used by XMLParsingEngine. Handles br-tag escaping automatically. |
| xlsxwriter | (installed) | Excel .xlsx writing | Project rule: xlsxwriter for writing. Already in requirements.txt. |
| loguru | (installed) | Logging | Project standard. Never print(). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| io.BytesIO | stdlib | In-memory file buffer | All export responses return bytes via StreamingResponse |
| fastapi.responses.StreamingResponse | (installed) | HTTP file download response | Already used by download endpoint |

### Do NOT Use
| Library | Reason |
|---------|--------|
| openpyxl | Only for reading, never writing. Current Excel export WRONGLY uses it. |
| xml.etree.ElementTree | Loses attribute case. Already migrated to lxml in Phase 07. |
| minidom | Fragile pretty-printing. lxml's `pretty_print=True` is superior. |

**Installation:** No new packages needed. All required libraries already installed.

## Architecture Patterns

### Recommended Project Structure
```
server/tools/ldm/
  services/
    export_service.py        # NEW: ExportService class (XML, Excel, Text)
  routes/
    files.py                 # MODIFY: Update _build_*_from_dicts to use ExportService
```

### Pattern 1: ExportService as Stateless Service
**What:** A service class with three methods: `export_xml()`, `export_excel()`, `export_text()`. Each takes rows (list of dicts) and metadata (dict), returns bytes.
**When to use:** Every export/download operation.
**Why:** Keeps route handlers thin. Service can be unit-tested without HTTP. Matches existing service pattern (TranslatorMergeService, XMLParsingEngine).

```python
# Source: Pattern from existing TranslatorMergeService
from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional

from loguru import logger
from lxml import etree


class ExportService:
    """Export rows to XML, Excel, or plain text format."""

    def export_xml(
        self,
        rows: List[Dict],
        metadata: Dict,
    ) -> bytes:
        """Build XML from row dicts with full attribute preservation."""
        ...

    def export_excel(
        self,
        rows: List[Dict],
        metadata: Dict,
        include_english: bool = True,
    ) -> bytes:
        """Build Excel with LanguageDataExporter column structure."""
        ...

    def export_text(
        self,
        rows: List[Dict],
        metadata: Dict,
    ) -> bytes:
        """Build tab-delimited text: StringID \\t source \\t translation."""
        ...
```

### Pattern 2: XML Export with lxml (br-tag safe)
**What:** Use lxml `etree.SubElement` with raw attribute dict, then `etree.tostring(pretty_print=True)`. lxml auto-escapes `<br/>` to `&lt;br/&gt;` in attribute values.
**Critical:** Do NOT manually escape or unescape br-tags. lxml handles it.

```python
# Source: ExtractAnything/core/xml_writer.py (proven pattern)
from lxml import etree

def export_xml(self, rows, metadata):
    root_tag = metadata.get("root_element", "LangData")
    root = etree.Element(root_tag)

    root_attribs = metadata.get("root_attributes")
    if root_attribs:
        for k, v in root_attribs.items():
            root.set(k, v)

    element_tag = metadata.get("element_tag", "LocStr")

    for row in rows:
        # Core attributes with ORIGINAL casing
        attrs = {}
        if row.get("string_id"):
            attrs["StringId"] = row["string_id"]
        if row.get("source"):
            attrs["StrOrigin"] = row["source"]
        if row.get("target") is not None:
            attrs["Str"] = row["target"]

        # Extra attributes from extra_data (Desc, DescOrigin, Memo, etc.)
        extra = row.get("extra_data") or {}
        for k, v in extra.items():
            if v is not None:
                attrs[k] = str(v)

        etree.SubElement(root, element_tag, **attrs)

    xml_decl = metadata.get("xml_declaration")
    encoding = metadata.get("encoding", "utf-8")

    return etree.tostring(
        root,
        encoding=encoding,
        xml_declaration=True,
        pretty_print=True,
    )
```

### Pattern 3: Excel Export with xlsxwriter (LanguageDataExporter column structure)
**What:** Use xlsxwriter workbook with the exact EU column order from LanguageDataExporter config.
**Key details from source:**
- Header format: bold, #DAEEF3 background, centered, bordered
- Column widths: StrOrigin=45, ENG=45, Str=45, Correction=45, etc.
- Text State: "KOREAN" or "TRANSLATED" based on Korean detection
- STATUS dropdown: ISSUE / NO ISSUE / FIXED
- StringID uses text format (`num_format='@'`) to prevent scientific notation
- Freeze panes on row 1, autofilter on all columns

```python
# Source: LanguageDataExporter/exporter/excel_writer.py
import xlsxwriter

COLUMN_HEADERS_EU = [
    "StrOrigin", "ENG", "Str", "Correction", "Text State",
    "STATUS", "COMMENT", "MEMO1", "MEMO2",
    "Category", "FileName", "StringID", "DescOrigin", "Desc",
]
```

### Pattern 4: Text Export (Simple Tabulated)
**What:** Tab-delimited text: `StringID\tStrOrigin\tStr` per line.
**Why simple:** Plain text export is for quick reference/scripting. No headers needed (or optional).

### Anti-Patterns to Avoid
- **Using stdlib ET for XML output:** Lowercases all attribute names. Use lxml.
- **Using openpyxl for writing:** Violates project rules. Use xlsxwriter.
- **Manual br-tag escaping:** Never do `text.replace('<br/>', '&lt;br/&gt;')` before passing to lxml. lxml does this automatically in attribute values.
- **Hardcoding column order in route handler:** Put it in ExportService so it can be tested independently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML attribute escaping | Manual `<` to `&lt;` replacement | lxml `etree.tostring()` | Auto-handles all XML escaping. Manual code is error-prone. |
| Excel file creation | openpyxl write | xlsxwriter | Project rule. xlsxwriter is faster, supports cell protection, data validation. |
| Pretty-print XML | minidom.toprettyxml | lxml `pretty_print=True` | minidom adds extra whitespace, is fragile with encoding. |
| Column structure | Invent new columns | Copy from LanguageDataExporter config.py | Proven column order, widths, formatting. |
| Korean detection | Custom regex | `server.tools.ldm.services.korean_detection.is_korean_text()` | Already exists, uses correct regex with Jamo + Compat Jamo. |

**Key insight:** The export service is a **porting** exercise from two proven sources: ExtractAnything's `xml_writer.py` (XML output) and LanguageDataExporter's `excel_writer.py` (Excel output). Zero new algorithms needed.

## Common Pitfalls

### Pitfall 1: br-tag Double Escaping
**What goes wrong:** Manually escaping `<br/>` to `&lt;br/&gt;` before lxml serializes, resulting in `&amp;lt;br/&amp;gt;` on disk (double-escaped).
**Why it happens:** Developer doesn't trust lxml's auto-escaping and adds manual conversion.
**How to avoid:** In-memory values contain `<br/>`. Pass directly to lxml. lxml auto-escapes to `&lt;br/&gt;` in attributes. Never touch it.
**Warning signs:** Exported XML contains `&amp;lt;` or `&amp;gt;`.

### Pitfall 2: Attribute Case Loss
**What goes wrong:** Using stdlib `xml.etree.ElementTree` which lowercases attribute names: `StringId` becomes `stringid`, `StrOrigin` becomes `strorigin`.
**Why it happens:** Current `_build_xml_file_from_dicts` uses stdlib ET.
**How to avoid:** Use lxml which preserves attribute name casing exactly.
**Warning signs:** Exported XML has lowercase attribute names when originals were CamelCase.

### Pitfall 3: openpyxl for Writing
**What goes wrong:** Using openpyxl to create Excel files violates project rules and produces less styled output.
**Why it happens:** Current `_build_excel_file_from_dicts` uses openpyxl.
**How to avoid:** Use xlsxwriter with proper formatting (header styles, column widths, data validation).
**Warning signs:** Import of openpyxl in write path.

### Pitfall 4: Missing extra_data Attributes in XML Export
**What goes wrong:** XML export only writes StringId/StrOrigin/Str but loses Desc, DescOrigin, Memo, Category, Priority etc.
**Why it happens:** Not iterating over `extra_data` dict to restore all original attributes.
**How to avoid:** Always merge `extra_data` dict into element attributes after core attributes.
**Warning signs:** Exported XML has fewer attributes than original upload.

### Pitfall 5: Empty String vs None in Attributes
**What goes wrong:** Writing `Str=""` when the value is None, or skipping an attribute when it should be empty string.
**Why it happens:** Python `None` vs `""` confusion.
**How to avoid:** Only skip attributes that are `None`. Empty string `""` is a valid attribute value and should be written.
**Warning signs:** Missing attributes or attributes with "None" text value.

## Code Examples

### XML Export (lxml, br-tag safe)
```python
# Source: ExtractAnything/core/xml_writer.py + LINEBREAK_SAFEGUARDS.md
from lxml import etree

root = etree.Element("LangData")

# Value in memory: "First line<br/>Second line"
attrs = {"StringId": "001", "StrOrigin": "첫 줄<br/>둘째 줄", "Str": "First line<br/>Second line"}
etree.SubElement(root, "LocStr", **attrs)

xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True)
# On disk: StrOrigin="첫 줄&lt;br/&gt;둘째 줄"  (auto-escaped by lxml)
```

### Excel Export (xlsxwriter, LanguageDataExporter structure)
```python
# Source: LanguageDataExporter/exporter/excel_writer.py
import xlsxwriter
from io import BytesIO

output = BytesIO()
workbook = xlsxwriter.Workbook(output)
worksheet = workbook.add_worksheet("Export")

headers = ["StrOrigin", "ENG", "Str", "Correction", "Text State",
           "STATUS", "COMMENT", "MEMO1", "MEMO2",
           "Category", "FileName", "StringID", "DescOrigin", "Desc"]

# Header format
header_fmt = workbook.add_format({
    'bold': True, 'bg_color': '#DAEEF3', 'align': 'center',
    'valign': 'vcenter', 'border': 1,
})

# Write headers
for col, h in enumerate(headers):
    worksheet.write(0, col, h, header_fmt)

# Data
cell_fmt = workbook.add_format({'text_wrap': True, 'border': 1, 'valign': 'top'})
string_fmt = workbook.add_format({'border': 1, 'num_format': '@'})  # StringID

for row_idx, row in enumerate(rows, 1):
    worksheet.write(row_idx, 0, row.get("source", ""), cell_fmt)        # StrOrigin
    worksheet.write(row_idx, 1, "", cell_fmt)                           # ENG (empty for now)
    worksheet.write(row_idx, 2, row.get("target", ""), cell_fmt)        # Str
    worksheet.write(row_idx, 3, "", cell_fmt)                           # Correction (empty)
    # ... Text State, STATUS, etc.
    worksheet.write(row_idx, 11, row.get("string_id", ""), string_fmt)  # StringID

worksheet.freeze_panes(1, 0)
workbook.close()
output.seek(0)
return output.read()
```

### Text Export (tab-delimited)
```python
# Simple tab-delimited format
lines = []
for row in rows:
    sid = row.get("string_id", "")
    source = row.get("source", "")
    target = row.get("target", "")
    lines.append(f"{sid}\t{source}\t{target}")

content = "\n".join(lines)
return content.encode("utf-8")
```

## State of the Art

| Old Approach (Current) | New Approach (Phase 10) | Impact |
|------------------------|------------------------|--------|
| stdlib ET for XML export | lxml with `pretty_print=True` | Preserves attribute casing, auto-escapes br-tags correctly |
| openpyxl for Excel writing | xlsxwriter with LanguageDataExporter formatting | Proper column structure, styles, data validation |
| Export builders in route file | ExportService in services/ | Testable, reusable, consistent with service pattern |
| Generic headers (Source, Target) | Full EU column structure (14 columns) | Matches LanguageDataExporter professional output |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pytest.ini |
| Quick run command | `python3 -m pytest tests/unit/ldm/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TMERGE-05 | XML export with br-tag preservation | unit | `python3 -m pytest tests/unit/ldm/test_export_service.py::TestXMLExport -x` | Wave 0 |
| TMERGE-05 | br-tag round-trip (upload-export) | integration | `python3 -m pytest tests/integration/test_export_roundtrip.py -x` | Exists (v1.0) |
| TMERGE-06 | Excel export with correct columns | unit | `python3 -m pytest tests/unit/ldm/test_export_service.py::TestExcelExport -x` | Wave 0 |
| TMERGE-07 | Plain text tabulated export | unit | `python3 -m pytest tests/unit/ldm/test_export_service.py::TestTextExport -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/unit/ldm/test_export_service.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/ldm/test_export_service.py` -- covers TMERGE-05, TMERGE-06, TMERGE-07
- [ ] Update `tests/integration/test_export_roundtrip.py` -- verify lxml migration doesn't break existing tests

## Sources

### Primary (HIGH confidence)
- `server/tools/ldm/routes/files.py` lines 1252-1380 -- existing `_build_*_from_dicts` functions (direct inspection)
- `RessourcesForCodingTheProject/NewScripts/ExtractAnything/core/xml_writer.py` -- raw_attribs XML output pattern with lxml
- `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/exporter/excel_writer.py` -- full Excel column structure, formatting, data validation
- `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/config.py` line 310 -- EU column header definition
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/docs/LINEBREAK_SAFEGUARDS.md` -- three-layer br-tag defense
- `server/tools/ldm/services/xml_parsing.py` -- XMLParsingEngine singleton (lxml-based)
- `server/tools/ldm/file_handlers/xml_handler.py` -- how rows are parsed on upload (extra_data structure)
- `tests/integration/test_export_roundtrip.py` -- existing round-trip validation tests

### Secondary (MEDIUM confidence)
- `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py` -- `_write_target_xml` function (lxml tree.write pattern)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in the project
- Architecture: HIGH -- existing patterns (service + route) well-established in Phases 07-09
- Pitfalls: HIGH -- all pitfalls identified from direct codebase inspection of current bugs in existing export code

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain, no external dependencies)
