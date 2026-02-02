"""
Excel I/O Operations.

Read input Excel files and write output Excel files.
"""

from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment

from .korean_detection import is_korean_text


def read_korean_input(excel_path: Path) -> List[str]:
    """
    Read Korean text from Column 1 of input Excel file.

    Args:
        excel_path: Path to input Excel file

    Returns:
        List of Korean text strings (trimmed, non-empty)
    """
    wb = load_workbook(excel_path, read_only=True)
    ws = wb.active

    korean_texts = []
    for row in ws.iter_rows(min_row=1, max_col=1):
        cell_value = row[0].value
        if cell_value:
            korean_texts.append(str(cell_value).strip())

    wb.close()
    return korean_texts


def read_corrections_from_excel(
    excel_path: Path,
    stringid_col: int = 1,
    strorigin_col: int = 2,
    correction_col: int = 3,
    has_header: bool = True,
) -> List[Dict]:
    """
    Read corrections from Excel file for transfer mode.

    Args:
        excel_path: Path to input Excel file
        stringid_col: Column number for StringID (1-based)
        strorigin_col: Column number for StrOrigin (1-based)
        correction_col: Column number for corrected text (1-based)
        has_header: Skip first row if True

    Returns:
        List of correction dicts with keys: string_id, str_origin, corrected
    """
    wb = load_workbook(excel_path, read_only=True)
    ws = wb.active

    corrections = []
    start_row = 2 if has_header else 1

    for row in ws.iter_rows(min_row=start_row):
        try:
            string_id = row[stringid_col - 1].value
            str_origin = row[strorigin_col - 1].value if strorigin_col <= len(row) else None
            corrected = row[correction_col - 1].value if correction_col <= len(row) else None

            if string_id and corrected:
                corrections.append({
                    "string_id": str(string_id).strip(),
                    "str_origin": str(str_origin).strip() if str_origin else "",
                    "corrected": str(corrected).strip(),
                })
        except (IndexError, AttributeError):
            continue

    wb.close()
    return corrections


def get_ordered_languages(available_langs: List[str], language_order: List[str] = None) -> List[str]:
    """
    Get languages in preferred order.

    Args:
        available_langs: List of available language codes
        language_order: Preferred order (optional, uses default if None)

    Returns:
        Ordered list of language codes (excludes KOR)
    """
    if language_order is None:
        language_order = [
            "kor", "eng", "fre", "ger", "spa", "por", "ita", "rus",
            "tur", "pol", "zho-cn", "zho-tw", "jpn", "tha", "vie", "ind", "msa"
        ]

    ordered = []
    for lang in language_order:
        if lang in available_langs and lang != "kor":
            ordered.append(lang)

    for lang in available_langs:
        if lang not in ordered and lang != "kor":
            ordered.append(lang)

    return ordered


def write_output_excel(
    output_path: Path,
    korean_inputs: List[str],
    matches_per_input: List[List[str]],
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str],
    language_names: Dict[str, str] = None,
):
    """
    Write output Excel file with translations.

    Args:
        output_path: Path to output Excel file
        korean_inputs: List of Korean input texts
        matches_per_input: List of StringID lists for each input
        translation_lookup: Dict mapping lang_code to {StringID: translation}
        available_langs: List of available language codes
        language_names: Optional mapping of lang_code to display name
    """
    if language_names is None:
        language_names = {}

    wb = Workbook()
    ws = wb.active
    ws.title = "Translations"

    ordered_langs = get_ordered_languages(available_langs)

    # Header row
    headers = ["KOR (Input)"] + [language_names.get(lang, lang.upper()) for lang in ordered_langs]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Data rows
    from .matching import format_multiple_matches

    for row_idx, (korean_text, string_ids) in enumerate(zip(korean_inputs, matches_per_input), start=2):
        ws.cell(row=row_idx, column=1, value=korean_text)

        for col_idx, lang_code in enumerate(ordered_langs, start=2):
            if not string_ids:
                ws.cell(row=row_idx, column=col_idx, value="")
                continue

            translations = []
            for sid in string_ids:
                trans = translation_lookup.get(lang_code, {}).get(sid, "")
                if trans:
                    translations.append(trans)

            cell_value = format_multiple_matches(translations)
            cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)
            if "\n" in cell_value:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Column widths
    for col_idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 40

    wb.save(output_path)


def write_stringid_lookup_excel(
    output_path: Path,
    string_id: str,
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str],
    language_names: Dict[str, str] = None,
):
    """
    Write output Excel for a single StringID lookup.

    Output format: StringID | ENG | FRE | GER | ...
    """
    if language_names is None:
        language_names = {}

    wb = Workbook()
    ws = wb.active
    ws.title = "StringID Lookup"

    ordered_langs = get_ordered_languages(available_langs)

    # Header row
    headers = ["StringID"] + [language_names.get(lang, lang.upper()) for lang in ordered_langs]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Data row
    ws.cell(row=2, column=1, value=string_id)

    for col_idx, lang_code in enumerate(ordered_langs, start=2):
        trans = translation_lookup.get(lang_code, {}).get(string_id, "")
        cell = ws.cell(row=2, column=col_idx, value=trans)
        cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Column widths
    ws.column_dimensions['A'].width = 20
    for col_idx in range(2, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 40

    wb.save(output_path)


def write_folder_translation_excel(
    output_path: Path,
    string_map: Dict[str, str],
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str],
    language_names: Dict[str, str] = None,
):
    """
    Write Excel with one sheet per language.

    Columns: StrOrigin | English | Translation | StringID

    "NO TRANSLATION" if translation is empty or contains Korean characters.
    """
    if language_names is None:
        language_names = {}

    wb = Workbook()
    # Remove default sheet
    default_sheet = wb.active
    wb.remove(default_sheet)

    ordered_langs = get_ordered_languages(available_langs)

    # Get English lookup for reference
    eng_lookup = translation_lookup.get("eng", {})

    for lang_code in ordered_langs:
        lang_name = language_names.get(lang_code, lang_code.upper())
        ws = wb.create_sheet(title=lang_name)
        lang_lookup = translation_lookup.get(lang_code, {})

        # Header row
        headers = ["StrOrigin", "English", lang_name, "StringID"]
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')

        # Data rows
        row_idx = 2
        for string_id, str_origin in string_map.items():
            # StrOrigin
            ws.cell(row=row_idx, column=1, value=str_origin)

            # English
            eng_trans = eng_lookup.get(string_id, "")
            if not eng_trans or is_korean_text(eng_trans):
                eng_trans = "NO TRANSLATION"
            ws.cell(row=row_idx, column=2, value=eng_trans)

            # Target language translation
            lang_trans = lang_lookup.get(string_id, "")
            if not lang_trans or is_korean_text(lang_trans):
                lang_trans = "NO TRANSLATION"
            cell = ws.cell(row=row_idx, column=3, value=lang_trans)
            if "\n" in lang_trans:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

            # StringID
            ws.cell(row=row_idx, column=4, value=string_id)

            row_idx += 1

        # Column widths
        ws.column_dimensions['A'].width = 50  # StrOrigin
        ws.column_dimensions['B'].width = 40  # English
        ws.column_dimensions['C'].width = 40  # Translation
        ws.column_dimensions['D'].width = 25  # StringID

    wb.save(output_path)


def write_reverse_lookup_excel(
    output_path: Path,
    input_texts: List[str],
    stringid_map: Dict[str, str],  # input_text -> StringID
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str],
    language_names: Dict[str, str] = None,
):
    """
    Write Excel with all languages in columns.

    Columns: Input | KOR | ENG | FRE | GER | ...
    """
    if language_names is None:
        language_names = {}

    wb = Workbook()
    ws = wb.active
    ws.title = "Reverse Lookup"

    # Order: KOR first, then others
    ordered_langs = ["kor"] + get_ordered_languages(available_langs)

    # Header row
    headers = ["Input"] + [language_names.get(lang, lang.upper()) for lang in ordered_langs]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Data rows
    for row_idx, input_text in enumerate(input_texts, start=2):
        # Write input text
        ws.cell(row=row_idx, column=1, value=input_text)

        string_id = stringid_map.get(input_text)
        if not string_id:
            # NOT FOUND - write "NOT FOUND" in KOR column, leave rest empty
            ws.cell(row=row_idx, column=2, value="NOT FOUND")
            continue

        # For each language, get translation
        for col_idx, lang_code in enumerate(ordered_langs, start=2):
            trans = translation_lookup.get(lang_code, {}).get(string_id, "")
            if not trans or is_korean_text(trans):
                trans = "NO TRANSLATION"
            cell = ws.cell(row=row_idx, column=col_idx, value=trans)
            if "\n" in trans:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Column widths
    ws.column_dimensions['A'].width = 50  # Input
    for col_idx in range(2, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 40

    wb.save(output_path)
