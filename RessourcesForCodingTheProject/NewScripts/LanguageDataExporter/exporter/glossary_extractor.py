"""
Glossary Extractor — GameData-driven glossary extraction.

Uses the GameData reverse index to deterministically identify glossary terms:
- Parse LanguageData for all (StrOrigin, Str, StringID) entries
- Reverse-lookup each StrOrigin against the GameData index
- If the Korean text appears as a Name attribute → glossary term
- If Desc attribute → skip (not a glossary term)

Output: Clean Excel with Korean, English, Category, FileName, StringID, Count.
No heuristic filtering needed — GameData structure is the source of truth.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import xlsxwriter

from .gamedata_index import GameDataReverseIndex, normalize_text
from .xml_parser import parse_language_file, discover_language_files

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class GlossaryEntry:
    """A single glossary entry with all metadata."""
    korean: str             # Korean Name text (StrOrigin from LanguageData)
    english: str            # English translation
    translation: str        # Target language translation
    category: str           # GameData category (Knowledge, Item, Quest, etc.)
    gamedata_file: str      # Source GameData filename
    string_id: str          # StringID from LanguageData
    attr_name: str          # Exact attribute name (Name, CharacterName, etc.)
    count: int = 1          # Occurrence count in LanguageData


# =============================================================================
# GLOSSARY EXTRACTION
# =============================================================================

def extract_glossary(
    reverse_index: GameDataReverseIndex,
    lang_data: List[dict],
    eng_lookup: Dict[str, str],
    lang_code: str = "",
    progress_callback: Optional[callable] = None,
) -> List[GlossaryEntry]:
    """Extract glossary terms by matching LanguageData against GameData reverse index.

    Algorithm:
      1. For each LanguageData entry, normalize StrOrigin
      2. Look up in reverse index — if it's a Name-type attribute, it's a glossary term
      3. Deduplicate by Korean text (keep first translation, count occurrences)
      4. Sort by category then Korean text

    Args:
        reverse_index: Pre-built GameData reverse index
        lang_data: Parsed LanguageData entries [{str_origin, str, string_id, ...}]
        eng_lookup: {string_id → english_translation}
        lang_code: Target language code (for the translation column)
        progress_callback: Optional callback(message_str)

    Returns:
        List of GlossaryEntry sorted by category then Korean text
    """
    if progress_callback:
        progress_callback("Matching LanguageData against GameData index...")

    # Track: normalized_korean → {first entry data, count}
    seen: Dict[str, GlossaryEntry] = {}
    counts: Counter = Counter()
    total = len(lang_data)

    for idx, entry in enumerate(lang_data):
        if progress_callback and idx % 5000 == 0:
            progress_callback(f"Matching entries: {idx}/{total}...")

        str_origin = entry.get("str_origin", "")
        if not str_origin:
            continue

        normalized = normalize_text(str_origin)
        if not normalized:
            continue

        # Check if this Korean text is a Name in GameData
        if not reverse_index.is_name(normalized):
            continue

        counts[normalized] += 1

        # Only store first occurrence (dedup)
        if normalized in seen:
            continue

        gd_entry = reverse_index.get_best_entry(normalized)
        if not gd_entry:
            continue

        string_id = entry.get("string_id", "")
        translation = entry.get("str", "")
        english = eng_lookup.get(string_id, "")

        seen[normalized] = GlossaryEntry(
            korean=str_origin,
            english=english,
            translation=translation,
            category=gd_entry.category,
            gamedata_file=gd_entry.filename,
            string_id=string_id,
            attr_name=gd_entry.attr_name,
            count=1,  # will be updated below
        )

    # Apply counts
    for normalized, glossary_entry in seen.items():
        glossary_entry.count = counts[normalized]

    # Sort by category then Korean text
    result = sorted(seen.values(), key=lambda e: (e.category, e.korean))

    if progress_callback:
        progress_callback(f"Glossary extracted: {len(result)} terms")

    logger.info(
        "Glossary extraction: %d Name-type terms from %d LanguageData entries",
        len(result), total,
    )

    return result


# =============================================================================
# EXCEL WRITER
# =============================================================================

def write_glossary_excel(
    glossary: List[GlossaryEntry],
    output_path: Path,
    lang_code: str = "",
    include_translation: bool = True,
) -> bool:
    """Write glossary to a clean Excel file.

    Columns:
      - Korean (Name)
      - English
      - Translation (if include_translation and lang_code is not eng)
      - Category
      - Attribute
      - GameData File
      - StringID
      - Count

    Args:
        glossary: List of GlossaryEntry
        output_path: Output Excel file path
        lang_code: Target language code
        include_translation: Whether to include target translation column

    Returns:
        True if successful
    """
    try:
        wb = xlsxwriter.Workbook(str(output_path))
        ws = wb.add_worksheet("Glossary")

        # Styles
        header_fmt = wb.add_format({
            "bold": True,
            "bg_color": "#4472C4",
            "font_color": "#FFFFFF",
            "border": 1,
            "text_wrap": True,
            "valign": "vcenter",
        })
        text_fmt = wb.add_format({
            "border": 1,
            "text_wrap": True,
            "valign": "top",
        })
        stringid_fmt = wb.add_format({
            "border": 1,
            "num_format": "@",
            "valign": "top",
        })
        count_fmt = wb.add_format({
            "border": 1,
            "align": "center",
            "valign": "top",
        })
        # Category colors (same as LanguageDataExporter config)
        category_colors = {
            "Item": "#D9D2E9",
            "Quest": "#D9D2E9",
            "Character": "#F8CBAD",
            "Gimmick": "#D9D2E9",
            "Skill": "#D9D2E9",
            "Knowledge": "#D9D2E9",
            "Faction": "#D9D2E9",
            "UI": "#A9D08E",
            "Region": "#F8CBAD",
            "System_Misc": "#D9D9D9",
        }
        cat_formats = {}
        for cat, color in category_colors.items():
            cat_formats[cat] = wb.add_format({
                "border": 1,
                "bg_color": color,
                "valign": "top",
            })

        # Build headers
        headers = ["Korean (Name)", "English"]
        is_eng = lang_code.lower() == "eng"
        if include_translation and not is_eng and lang_code:
            headers.append(f"Translation ({lang_code.upper()})")
        headers.extend(["Category", "Attribute", "GameData File", "StringID", "Count"])

        # Write headers
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_fmt)

        # Write data
        for row_idx, entry in enumerate(glossary, start=1):
            col = 0

            # Korean
            ws.write(row_idx, col, entry.korean, text_fmt)
            col += 1

            # English
            ws.write(row_idx, col, entry.english, text_fmt)
            col += 1

            # Translation (optional)
            if include_translation and not is_eng and lang_code:
                ws.write(row_idx, col, entry.translation, text_fmt)
                col += 1

            # Category (with color)
            cat_fmt = cat_formats.get(entry.category, text_fmt)
            ws.write(row_idx, col, entry.category, cat_fmt)
            col += 1

            # Attribute name
            ws.write(row_idx, col, entry.attr_name, text_fmt)
            col += 1

            # GameData file
            ws.write(row_idx, col, entry.gamedata_file, text_fmt)
            col += 1

            # StringID (text format to prevent scientific notation)
            ws.write(row_idx, col, str(entry.string_id), stringid_fmt)
            col += 1

            # Count
            ws.write(row_idx, col, entry.count, count_fmt)

        # Column widths
        col_widths = [40, 40]
        if include_translation and not is_eng and lang_code:
            col_widths.append(40)
        col_widths.extend([15, 15, 30, 22, 8])

        for col_idx, width in enumerate(col_widths):
            ws.set_column(col_idx, col_idx, width)

        # Freeze header row
        ws.freeze_panes(1, 0)

        # Auto-filter
        last_col = len(headers) - 1
        last_row = len(glossary)
        ws.autofilter(0, 0, last_row, last_col)

        wb.close()
        logger.info("Glossary written: %s (%d terms)", output_path.name, len(glossary))
        return True

    except Exception:
        logger.exception("Failed to write glossary Excel: %s", output_path)
        return False


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def extract_and_write_glossary(
    reverse_index: GameDataReverseIndex,
    loc_folder: Path,
    output_folder: Path,
    selected_langs: List[str],
    progress_callback: Optional[callable] = None,
) -> Dict[str, int]:
    """Extract and write glossary for selected languages.

    Args:
        reverse_index: Pre-built GameData reverse index
        loc_folder: Path to LOC folder with languagedata_*.xml
        output_folder: Output directory for glossary Excel files
        selected_langs: List of language codes to process
        progress_callback: Optional callback(message_str)

    Returns:
        {lang_code: term_count}
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    results: Dict[str, int] = {}

    # Discover language files
    all_lang_files = discover_language_files(loc_folder)

    # Parse English for cross-reference
    eng_lookup: Dict[str, str] = {}
    if "eng" in all_lang_files:
        if progress_callback:
            progress_callback("Loading English translations...")
        eng_data = parse_language_file(all_lang_files["eng"])
        eng_lookup = {row["string_id"]: row["str"] for row in eng_data}
        logger.info("English lookup: %d entries", len(eng_lookup))

    total_langs = len(selected_langs)

    for idx, lang_code in enumerate(selected_langs):
        if lang_code not in all_lang_files:
            logger.warning("Language file not found for: %s", lang_code)
            continue

        if progress_callback:
            progress_callback(
                f"Extracting glossary for {lang_code.upper()} ({idx + 1}/{total_langs})..."
            )

        lang_data = parse_language_file(all_lang_files[lang_code])

        glossary = extract_glossary(
            reverse_index=reverse_index,
            lang_data=lang_data,
            eng_lookup=eng_lookup,
            lang_code=lang_code,
            progress_callback=progress_callback,
        )

        output_path = output_folder / f"Glossary_{lang_code.upper()}.xlsx"
        ok = write_glossary_excel(
            glossary=glossary,
            output_path=output_path,
            lang_code=lang_code,
        )

        results[lang_code] = len(glossary) if ok else 0

        if progress_callback:
            progress_callback(
                f"Glossary {lang_code.upper()}: {len(glossary)} terms → {output_path.name}"
            )

    return results
