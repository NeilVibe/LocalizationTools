"""
Export Service -- XML, Excel, and Text export.

Replaces broken inline _build_*_from_dicts functions with proper lxml + xlsxwriter
implementation. Patterns ported from ExtractAnything and LanguageDataExporter.

XML: lxml etree with correct attribute casing (StringId, StrOrigin, Str).
     lxml auto-escapes br-tags in attribute values -- no manual escaping needed.

Excel: xlsxwriter with 14-column EU structure, header formatting, freeze panes.

Text: Tab-delimited StringID + source + target, UTF-8 encoded.
"""

from __future__ import annotations

import io
from typing import Any

from loguru import logger
from lxml import etree

from server.tools.ldm.services.korean_detection import is_korean_text


# EU column order (14 columns)
EU_COLUMNS = [
    "StrOrigin", "ENG", "Str", "Correction", "Text State",
    "STATUS", "COMMENT", "MEMO1", "MEMO2", "Category",
    "FileName", "StringID", "DescOrigin", "Desc",
]


class ExportService:
    """Service for exporting LDM rows to XML, Excel, and text formats.

    All methods accept rows (list of dicts) and metadata (dict) and return bytes.
    """

    def export_xml(self, rows: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> bytes:
        """Export rows to XML using lxml.

        Attribute mapping:
            string_id -> StringId
            source    -> StrOrigin
            target    -> Str
            extra_data keys preserved as-is

        None values are skipped (no attribute written).
        Empty strings produce attr="".
        lxml auto-escapes <br/> in attribute values to &lt;br/&gt;.

        Returns:
            UTF-8 encoded XML bytes with xml declaration.
        """
        metadata = metadata or {}

        root_tag = metadata.get("root_element", "LangData")
        encoding = metadata.get("encoding", "utf-8")
        element_tag = metadata.get("element_tag", "LocStr")
        root_attributes = metadata.get("root_attributes") or {}

        # Build root element -- handle xmlns specially via nsmap
        nsmap = None
        if "xmlns" in root_attributes:
            nsmap = {None: root_attributes["xmlns"]}

        root = etree.Element(root_tag, nsmap=nsmap)
        for key, val in root_attributes.items():
            if key == "xmlns":
                continue  # Already handled via nsmap
            root.set(key, val)

        for row in rows:
            elem = etree.SubElement(root, element_tag)

            # Core attributes with correct casing
            attr_map = {
                "StringId": row.get("string_id"),
                "StrOrigin": row.get("source"),
                "Str": row.get("target"),
            }

            for attr_name, attr_val in attr_map.items():
                if attr_val is not None:
                    elem.set(attr_name, attr_val)

            # Extra data attributes
            extra_data = row.get("extra_data") or {}
            for attr_name, attr_val in extra_data.items():
                if attr_val is not None:
                    elem.set(attr_name, attr_val)

        result = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding=encoding,
        )

        logger.debug(f"ExportService.export_xml: {len(rows)} rows, {len(result)} bytes")
        return result

    def export_excel(self, rows: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> bytes:
        """Export rows to Excel using xlsxwriter with EU column structure.

        14 columns: StrOrigin | ENG | Str | Correction | Text State | STATUS |
                    COMMENT | MEMO1 | MEMO2 | Category | FileName | StringID |
                    DescOrigin | Desc

        Header format: bold, #DAEEF3 background, centered, border 1.
        StringID column: text format (num_format='@') to prevent scientific notation.
        Text State: KOREAN if target contains Korean, else TRANSLATED.
        Freeze panes at row 1. Autofilter on all columns.

        Returns:
            Excel file bytes (.xlsx).
        """
        import xlsxwriter

        metadata = metadata or {}
        output = io.BytesIO()

        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = wb.add_worksheet(metadata.get("sheet_name", "Translations"))

        # --- Formats ---
        header_fmt = wb.add_format({
            "bold": True,
            "bg_color": "#DAEEF3",
            "align": "center",
            "border": 1,
        })

        cell_fmt = wb.add_format({
            "text_wrap": True,
            "border": 1,
            "valign": "top",
        })

        text_fmt = wb.add_format({
            "text_wrap": True,
            "border": 1,
            "valign": "top",
            "num_format": "@",
        })

        # --- Headers ---
        for col_idx, header in enumerate(EU_COLUMNS):
            ws.write(0, col_idx, header, header_fmt)

        # --- Data rows ---
        for row_idx, row in enumerate(rows, start=1):
            extra = row.get("extra_data") or {}
            target = row.get("target") or ""
            source = row.get("source") or ""
            string_id = row.get("string_id") or ""

            # Text State: Korean detection
            text_state = "KOREAN" if is_korean_text(target) else "TRANSLATED"

            # Map to EU column positions
            # 0: StrOrigin, 1: ENG, 2: Str, 3: Correction, 4: Text State,
            # 5: STATUS, 6: COMMENT, 7: MEMO1, 8: MEMO2, 9: Category,
            # 10: FileName, 11: StringID, 12: DescOrigin, 13: Desc
            values = [
                source,                          # 0: StrOrigin
                extra.get("ENG", ""),             # 1: ENG
                target,                          # 2: Str
                extra.get("Correction", ""),      # 3: Correction
                text_state,                       # 4: Text State
                extra.get("STATUS", ""),          # 5: STATUS
                extra.get("COMMENT", ""),         # 6: COMMENT
                extra.get("MEMO1", extra.get("Memo", "")),  # 7: MEMO1
                extra.get("MEMO2", ""),           # 8: MEMO2
                extra.get("Category", ""),        # 9: Category
                extra.get("FileName", ""),        # 10: FileName
                string_id,                        # 11: StringID (text format)
                extra.get("DescOrigin", ""),       # 12: DescOrigin
                extra.get("Desc", ""),            # 13: Desc
            ]

            for col_idx, val in enumerate(values):
                if col_idx == 11:  # StringID column -- text format
                    ws.write_string(row_idx, col_idx, str(val), text_fmt)
                else:
                    ws.write(row_idx, col_idx, val, cell_fmt)

        # --- Freeze panes & autofilter ---
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(rows), len(EU_COLUMNS) - 1)

        wb.close()
        output.seek(0)
        result = output.read()

        logger.debug(f"ExportService.export_excel: {len(rows)} rows, {len(result)} bytes")
        return result

    def export_text(self, rows: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> bytes:
        """Export rows to tab-delimited text.

        Format: StringID\\tSource\\tTarget per line.
        None values become empty strings.
        UTF-8 encoded.

        Returns:
            UTF-8 encoded text bytes.
        """
        lines = []
        for row in rows:
            string_id = row.get("string_id") or ""
            source = row.get("source") or ""
            target = row.get("target") or ""
            lines.append(f"{string_id}\t{source}\t{target}")

        content = "\n".join(lines)
        result = content.encode("utf-8")

        logger.debug(f"ExportService.export_text: {len(rows)} rows, {len(result)} bytes")
        return result
