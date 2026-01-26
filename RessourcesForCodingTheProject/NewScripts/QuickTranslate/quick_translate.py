"""
QuickTranslate - Find translations for Korean text by matching StrOrigin.

Matches Korean input text against StrOrigin attribute in Sequencer XML files
and outputs an Excel file with translations in all available languages.

Usage:
    python quick_translate.py

Features:
    - Substring matching: finds all entries where input is contained in StrOrigin
    - Multiple matches: formats as "1. XXX\n2. YYY" in same cell
    - Auto-discovers all language files
"""

import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Try lxml first (more robust), fallback to standard library
try:
    from lxml import etree as ET
    USING_LXML = True
except ImportError:
    from xml.etree import ElementTree as ET
    USING_LXML = False

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    raise

import config

# =============================================================================
# XML SANITIZATION (from LanguageDataExporter - battle-tested)
# =============================================================================

_bad_entity_re = re.compile(r'&(?!lt;|gt;|amp;|apos;|quot;)')


def _fix_bad_entities(txt: str) -> str:
    """Fix unescaped ampersands."""
    return _bad_entity_re.sub("&amp;", txt)


def _preprocess_newlines(raw: str) -> str:
    """Handle newlines in seg elements."""
    def repl(m: re.Match) -> str:
        inner = m.group(1).replace("\n", "&lt;br/&gt;").replace("\r\n", "&lt;br/&gt;")
        return f"<seg>{inner}</seg>"
    return re.sub(r"<seg>(.*?)</seg>", repl, raw, flags=re.DOTALL)


def sanitize_xml_content(raw: str) -> str:
    """
    Sanitize XML content to handle common issues.
    - Fix unescaped ampersands
    - Handle newlines in segments
    - Fix < and & in attribute values
    - Remove invalid control characters
    """
    # Remove invalid XML characters
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    # Fix entities
    raw = _fix_bad_entities(raw)
    raw = _preprocess_newlines(raw)

    # Fix < and & in attribute values
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)

    return raw


def parse_xml_file(xml_path: Path) -> ET.Element:
    """
    Parse XML file with sanitization and recovery mode.
    Returns the root element.
    """
    content = xml_path.read_text(encoding='utf-8')
    content = sanitize_xml_content(content)

    if USING_LXML:
        wrapped = f"<ROOT>\n{content}\n</ROOT>"
        try:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(huge_tree=True)
            )
        except ET.XMLSyntaxError:
            return ET.fromstring(
                wrapped.encode("utf-8"),
                parser=ET.XMLParser(recover=True, huge_tree=True)
            )
    else:
        return ET.fromstring(content)


# =============================================================================
# SEQUENCER STRORIGIN INDEX
# =============================================================================

def build_sequencer_strorigin_index(sequencer_folder: Path) -> Dict[str, str]:
    """
    Scan Sequencer/*.loc.xml files and build StringID->StrOrigin mapping.

    Args:
        sequencer_folder: Path to Export/Sequencer folder

    Returns:
        Dictionary {StringID: StrOrigin}
    """
    if not sequencer_folder.exists():
        print(f"WARNING: Sequencer folder not found: {sequencer_folder}")
        return {}

    index = {}
    file_count = 0

    for xml_file in sequencer_folder.rglob("*.loc.xml"):
        file_count += 1
        try:
            root = parse_xml_file(xml_file)

            # Find all LocStr elements
            for elem in root.iter('LocStr'):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID'))
                str_origin = (elem.get('StrOrigin') or elem.get('Strorigin') or
                             elem.get('strorigin') or elem.get('STRORIGIN') or '')

                if string_id and str_origin:
                    index[string_id] = str_origin

        except Exception as e:
            print(f"Error parsing {xml_file.name}: {e}")
            continue

    print(f"Indexed {len(index)} StringIDs from {file_count} Sequencer files")
    return index


# =============================================================================
# LANGUAGE FILE DISCOVERY AND PARSING
# =============================================================================

def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    """
    Find all languagedata_*.xml files.

    Returns:
        Dictionary {lang_code: Path} e.g. {"eng": Path(...), "fre": Path(...)}
    """
    if not loc_folder.exists():
        print(f"WARNING: LOC folder not found: {loc_folder}")
        return {}

    lang_files = {}

    for xml_file in loc_folder.glob("languagedata_*.xml"):
        # Extract language code: languagedata_eng.xml -> eng
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file

    print(f"Discovered {len(lang_files)} language files: {list(lang_files.keys())}")
    return lang_files


def build_translation_lookup(lang_files: Dict[str, Path]) -> Dict[str, Dict[str, str]]:
    """
    Parse all language files and build lookup.

    Returns:
        {lang_code: {StringID: translation}}
    """
    lookup = {}

    for lang_code, xml_path in lang_files.items():
        print(f"Parsing {lang_code}...")
        lookup[lang_code] = {}

        try:
            root = parse_xml_file(xml_path)

            for elem in root.iter('LocStr'):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID'))
                str_value = (elem.get('Str') or elem.get('str') or
                            elem.get('STR') or '')

                if string_id:
                    lookup[lang_code][string_id] = str_value

        except Exception as e:
            print(f"Error parsing {xml_path.name}: {e}")
            continue

        print(f"  {lang_code}: {len(lookup[lang_code])} entries")

    return lookup


# =============================================================================
# MATCHING LOGIC
# =============================================================================

def find_matches(korean_input: str, strorigin_index: Dict[str, str]) -> List[str]:
    """
    Find all StringIDs where korean_input is a substring of StrOrigin.

    Args:
        korean_input: Korean text to search for
        strorigin_index: {StringID: StrOrigin} mapping

    Returns:
        List of matching StringIDs
    """
    if not korean_input.strip():
        return []

    matches = []
    search_text = korean_input.strip()

    for string_id, str_origin in strorigin_index.items():
        if search_text in str_origin:
            matches.append(string_id)

    return matches


def format_multiple_matches(translations: List[str]) -> str:
    """
    Format multiple matches as numbered list.

    Returns:
        "1. XXX\n2. YYY\n3. ZZZ" or single value if only one match
    """
    # Filter out empty translations
    translations = [t for t in translations if t and t.strip()]

    if not translations:
        return ""
    if len(translations) == 1:
        return translations[0]
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(translations))


# =============================================================================
# EXCEL OUTPUT
# =============================================================================

def read_korean_input(excel_path: Path) -> List[str]:
    """
    Read Korean text from Column 1 of input Excel file.

    Returns:
        List of Korean text strings
    """
    from openpyxl import load_workbook

    wb = load_workbook(excel_path, read_only=True)
    ws = wb.active

    korean_texts = []
    for row in ws.iter_rows(min_row=1, max_col=1):
        cell_value = row[0].value
        if cell_value:
            korean_texts.append(str(cell_value).strip())

    wb.close()
    return korean_texts


def get_ordered_languages(available_langs: List[str]) -> List[str]:
    """
    Get languages in preferred order, filtering to only available ones.
    KOR is always first (input), then follow LANGUAGE_ORDER.
    """
    ordered = []

    for lang in config.LANGUAGE_ORDER:
        if lang in available_langs and lang != "kor":
            ordered.append(lang)

    # Add any remaining languages not in LANGUAGE_ORDER
    for lang in available_langs:
        if lang not in ordered and lang != "kor":
            ordered.append(lang)

    return ordered


def write_output_excel(
    output_path: Path,
    korean_inputs: List[str],
    matches_per_input: List[List[str]],
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str]
):
    """
    Write output Excel file with translations.

    Columns: KOR (input) | ENG | FRE | GER | ...
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Translations"

    # Get ordered languages (excluding KOR since it's the input)
    ordered_langs = get_ordered_languages(available_langs)

    # Write header row
    headers = ["KOR (Input)"] + [config.LANGUAGE_NAMES.get(lang, lang.upper()) for lang in ordered_langs]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Write data rows
    for row_idx, (korean_text, string_ids) in enumerate(zip(korean_inputs, matches_per_input), start=2):
        # Column 1: Korean input
        ws.cell(row=row_idx, column=1, value=korean_text)

        # For each language, get translations for all matching StringIDs
        for col_idx, lang_code in enumerate(ordered_langs, start=2):
            if not string_ids:
                ws.cell(row=row_idx, column=col_idx, value="")
                continue

            translations = []
            for sid in string_ids:
                trans = translation_lookup.get(lang_code, {}).get(sid, "")
                if trans:
                    translations.append(trans)

            # Format and write
            cell_value = format_multiple_matches(translations)
            cell = ws.cell(row=row_idx, column=col_idx, value=cell_value)

            # Enable text wrapping for multiline content
            if "\n" in cell_value:
                cell.alignment = Alignment(wrap_text=True, vertical='top')

    # Auto-adjust column widths (approximate)
    for col_idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 40

    wb.save(output_path)
    print(f"Saved output to: {output_path}")


# =============================================================================
# GUI APPLICATION
# =============================================================================

class QuickTranslateApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QuickTranslate")
        self.root.geometry("600x300")
        self.root.resizable(True, False)

        # Variables
        self.input_path = tk.StringVar()
        self.loc_folder = tk.StringVar(value=str(config.LOC_FOLDER))
        self.export_folder = tk.StringVar(value=str(config.EXPORT_FOLDER))
        self.status_text = tk.StringVar(value="Ready")

        # Pre-loaded data (None until loaded)
        self.strorigin_index = None
        self.translation_lookup = None
        self.available_langs = None

        self._create_ui()

    def _create_ui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input file row
        row = 0
        ttk.Label(main_frame, text="Input Excel:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.input_path, width=50).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self._browse_input).grid(row=row, column=2, pady=5)

        # LOC folder row
        row += 1
        ttk.Label(main_frame, text="LOC Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.loc_folder, width=50).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self._browse_loc).grid(row=row, column=2, pady=5)

        # EXPORT folder row
        row += 1
        ttk.Label(main_frame, text="EXPORT Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.export_folder, width=50).grid(row=row, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Browse...", command=self._browse_export).grid(row=row, column=2, pady=5)

        # Separator
        row += 1
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10)

        # Buttons row
        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="Load Data", command=self._load_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Translate", command=self._translate).pack(side=tk.LEFT, padx=5)

        # Status row
        row += 1
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=5)
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_text).pack(side=tk.LEFT, padx=5)

        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select Input Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.input_path.set(path)

    def _browse_loc(self):
        path = filedialog.askdirectory(title="Select LOC Folder")
        if path:
            self.loc_folder.set(path)
            config.update_settings(loc_folder=path)

    def _browse_export(self):
        path = filedialog.askdirectory(title="Select EXPORT Folder")
        if path:
            self.export_folder.set(path)
            config.update_settings(export_folder=path)

    def _load_data(self):
        """Load Sequencer index and translation data."""
        self.status_text.set("Loading data...")
        self.root.update()

        try:
            # Update paths from UI
            loc_path = Path(self.loc_folder.get())
            export_path = Path(self.export_folder.get())
            sequencer_path = export_path / "Sequencer"

            # Build Sequencer StrOrigin index
            self.status_text.set("Building Sequencer index...")
            self.root.update()
            self.strorigin_index = build_sequencer_strorigin_index(sequencer_path)

            if not self.strorigin_index:
                messagebox.showwarning("Warning", f"No Sequencer data found in:\n{sequencer_path}")
                self.status_text.set("No Sequencer data found")
                return

            # Discover and parse language files
            self.status_text.set("Loading language files...")
            self.root.update()
            lang_files = discover_language_files(loc_path)

            if not lang_files:
                messagebox.showwarning("Warning", f"No language files found in:\n{loc_path}")
                self.status_text.set("No language files found")
                return

            self.translation_lookup = build_translation_lookup(lang_files)
            self.available_langs = list(lang_files.keys())

            self.status_text.set(f"Loaded: {len(self.strorigin_index)} strings, {len(self.available_langs)} languages")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data:\n{e}")
            self.status_text.set(f"Error: {e}")

    def _translate(self):
        """Run translation lookup and generate output."""
        # Validate input
        if not self.input_path.get():
            messagebox.showwarning("Warning", "Please select an input Excel file.")
            return

        input_file = Path(self.input_path.get())
        if not input_file.exists():
            messagebox.showerror("Error", f"Input file not found:\n{input_file}")
            return

        # Load data if not already loaded
        if self.strorigin_index is None or self.translation_lookup is None:
            self._load_data()
            if self.strorigin_index is None:
                return

        self.status_text.set("Reading input file...")
        self.root.update()

        try:
            # Read Korean input
            korean_inputs = read_korean_input(input_file)
            print(f"Read {len(korean_inputs)} Korean inputs")

            if not korean_inputs:
                messagebox.showwarning("Warning", "No text found in input file.")
                self.status_text.set("No input text found")
                return

            # Find matches for each input
            self.status_text.set("Finding matches...")
            self.root.update()

            matches_per_input = []
            total_matches = 0

            for korean_text in korean_inputs:
                matches = find_matches(korean_text, self.strorigin_index)
                matches_per_input.append(matches)
                total_matches += len(matches)

            print(f"Found {total_matches} total matches")

            # Generate output
            self.status_text.set("Writing output file...")
            self.root.update()

            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"QuickTranslate_{timestamp}.xlsx"

            write_output_excel(
                output_path,
                korean_inputs,
                matches_per_input,
                self.translation_lookup,
                self.available_langs
            )

            self.status_text.set(f"Done! {len(korean_inputs)} inputs, {total_matches} matches")
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Translation failed:\n{e}")
            self.status_text.set(f"Error: {e}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
