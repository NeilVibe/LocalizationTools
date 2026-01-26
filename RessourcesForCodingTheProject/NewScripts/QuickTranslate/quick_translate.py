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
    - Branch selection: mainline or cd_lambda
    - Direct StringID lookup
"""

import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, List, Optional
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
# BRANCH CONFIGURATION
# =============================================================================

BRANCHES = {
    "mainline": {
        "loc": Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"),
        "export": Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__"),
    },
    "cd_lambda": {
        "loc": Path(r"F:\perforce\cd\cd_lambda\resource\GameData\stringtable\loc"),
        "export": Path(r"F:\perforce\cd\cd_lambda\resource\GameData\stringtable\export__"),
    },
}

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
    """
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)
    raw = _fix_bad_entities(raw)
    raw = _preprocess_newlines(raw)
    raw = re.sub(r'="([^"]*<[^"]*)"',
                 lambda m: '="' + m.group(1).replace("<", "&lt;") + '"', raw)
    raw = re.sub(r'="([^"]*&[^ltgapoqu][^"]*)"',
                 lambda m: '="' + m.group(1).replace("&", "&amp;") + '"', raw)
    return raw


def parse_xml_file(xml_path: Path) -> ET.Element:
    """Parse XML file with sanitization and recovery mode."""
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

def build_sequencer_strorigin_index(sequencer_folder: Path, progress_callback=None) -> Dict[str, str]:
    """
    Scan Sequencer/*.loc.xml files and build StringID->StrOrigin mapping.
    """
    if not sequencer_folder.exists():
        return {}

    index = {}
    xml_files = list(sequencer_folder.rglob("*.loc.xml"))
    total = len(xml_files)

    for i, xml_file in enumerate(xml_files):
        if progress_callback:
            progress_callback(f"Indexing Sequencer... {i+1}/{total}")
        try:
            root = parse_xml_file(xml_file)
            for elem in root.iter('LocStr'):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID'))
                str_origin = (elem.get('StrOrigin') or elem.get('Strorigin') or
                             elem.get('strorigin') or elem.get('STRORIGIN') or '')
                if string_id and str_origin:
                    index[string_id] = str_origin
        except Exception:
            continue

    return index


# =============================================================================
# LANGUAGE FILE DISCOVERY AND PARSING
# =============================================================================

def discover_language_files(loc_folder: Path) -> Dict[str, Path]:
    """Find all languagedata_*.xml files."""
    if not loc_folder.exists():
        return {}

    lang_files = {}
    for xml_file in loc_folder.glob("languagedata_*.xml"):
        match = re.match(r'languagedata_(.+)\.xml', xml_file.name, re.IGNORECASE)
        if match:
            lang_code = match.group(1).lower()
            lang_files[lang_code] = xml_file

    return lang_files


def build_translation_lookup(lang_files: Dict[str, Path], progress_callback=None) -> Dict[str, Dict[str, str]]:
    """Parse all language files and build lookup."""
    lookup = {}
    total = len(lang_files)

    for i, (lang_code, xml_path) in enumerate(lang_files.items()):
        if progress_callback:
            progress_callback(f"Loading {lang_code.upper()}... {i+1}/{total}")
        lookup[lang_code] = {}

        try:
            root = parse_xml_file(xml_path)
            for elem in root.iter('LocStr'):
                string_id = (elem.get('StringId') or elem.get('StringID') or
                            elem.get('stringid') or elem.get('STRINGID'))
                str_value = (elem.get('Str') or elem.get('str') or elem.get('STR') or '')
                if string_id:
                    lookup[lang_code][string_id] = str_value
        except Exception:
            continue

    return lookup


# =============================================================================
# MATCHING LOGIC
# =============================================================================

def find_matches(korean_input: str, strorigin_index: Dict[str, str]) -> List[str]:
    """Find all StringIDs where korean_input is a substring of StrOrigin."""
    if not korean_input.strip():
        return []

    matches = []
    search_text = korean_input.strip()

    for string_id, str_origin in strorigin_index.items():
        if search_text in str_origin:
            matches.append(string_id)

    return matches


def format_multiple_matches(translations: List[str]) -> str:
    """Format multiple matches as numbered list."""
    translations = [t for t in translations if t and t.strip()]
    if not translations:
        return ""
    if len(translations) == 1:
        return translations[0]
    return "\n".join(f"{i+1}. {t}" for i, t in enumerate(translations))


# =============================================================================
# EXCEL I/O
# =============================================================================

def read_korean_input(excel_path: Path) -> List[str]:
    """Read Korean text from Column 1 of input Excel file."""
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
    """Get languages in preferred order."""
    ordered = []
    for lang in config.LANGUAGE_ORDER:
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
    available_langs: List[str]
):
    """Write output Excel file with translations."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Translations"

    ordered_langs = get_ordered_languages(available_langs)

    # Header row
    headers = ["KOR (Input)"] + [config.LANGUAGE_NAMES.get(lang, lang.upper()) for lang in ordered_langs]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # Data rows
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

    for col_idx, _ in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 40

    wb.save(output_path)


def write_stringid_lookup_excel(
    output_path: Path,
    string_id: str,
    translation_lookup: Dict[str, Dict[str, str]],
    available_langs: List[str]
):
    """
    Write output Excel for a single StringID lookup.

    Output format: StringID | ENG | FRE | GER | ...
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "StringID Lookup"

    ordered_langs = get_ordered_languages(available_langs)

    # Header row
    headers = ["StringID"] + [config.LANGUAGE_NAMES.get(lang, lang.upper()) for lang in ordered_langs]
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


# =============================================================================
# GUI APPLICATION
# =============================================================================

class QuickTranslateApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QuickTranslate")
        self.root.geometry("500x380")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.input_path = tk.StringVar()
        self.string_id_input = tk.StringVar()
        self.selected_branch = tk.StringVar(value="mainline")
        self.status_text = tk.StringVar(value="Ready")

        # Cached data
        self.strorigin_index: Optional[Dict[str, str]] = None
        self.translation_lookup: Optional[Dict[str, Dict[str, str]]] = None
        self.available_langs: Optional[List[str]] = None
        self.cached_branch: Optional[str] = None

        self._create_ui()

    def _create_ui(self):
        # Main container
        main = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = tk.Label(main, text="QuickTranslate", font=('Segoe UI', 16, 'bold'),
                        bg='#f0f0f0', fg='#333')
        title.pack(pady=(0, 12))

        # Branch selection section (moved to top)
        branch_frame = tk.LabelFrame(main, text="Branch", font=('Segoe UI', 9),
                                     bg='#f0f0f0', fg='#555', padx=10, pady=6)
        branch_frame.pack(fill=tk.X, pady=(0, 10))

        branch_inner = tk.Frame(branch_frame, bg='#f0f0f0')
        branch_inner.pack()

        for branch_name in BRANCHES.keys():
            btn = tk.Radiobutton(
                branch_inner,
                text=branch_name,
                variable=self.selected_branch,
                value=branch_name,
                font=('Segoe UI', 10),
                bg='#f0f0f0',
                activebackground='#f0f0f0',
                cursor='hand2',
                padx=15
            )
            btn.pack(side=tk.LEFT, padx=5)

        # ===== Korean Match Section =====
        korean_frame = tk.LabelFrame(main, text="Korean Text Match (from Excel)", font=('Segoe UI', 9),
                                     bg='#f0f0f0', fg='#555', padx=10, pady=8)
        korean_frame.pack(fill=tk.X, pady=(0, 10))

        input_inner = tk.Frame(korean_frame, bg='#f0f0f0')
        input_inner.pack(fill=tk.X)

        self.input_entry = tk.Entry(input_inner, textvariable=self.input_path,
                                    font=('Segoe UI', 9), relief='solid', bd=1)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        browse_btn = tk.Button(input_inner, text="Browse", command=self._browse_input,
                              font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                              padx=10, cursor='hand2')
        browse_btn.pack(side=tk.LEFT, padx=(6, 0))

        self.translate_btn = tk.Button(input_inner, text="Translate", command=self._translate,
                                       font=('Segoe UI', 9, 'bold'), bg='#4a90d9', fg='white',
                                       relief='flat', padx=10, cursor='hand2')
        self.translate_btn.pack(side=tk.LEFT, padx=(6, 0))

        # ===== StringID Lookup Section =====
        stringid_frame = tk.LabelFrame(main, text="StringID Lookup", font=('Segoe UI', 9),
                                       bg='#f0f0f0', fg='#555', padx=10, pady=8)
        stringid_frame.pack(fill=tk.X, pady=(0, 10))

        stringid_inner = tk.Frame(stringid_frame, bg='#f0f0f0')
        stringid_inner.pack(fill=tk.X)

        self.stringid_entry = tk.Entry(stringid_inner, textvariable=self.string_id_input,
                                       font=('Segoe UI', 9), relief='solid', bd=1)
        self.stringid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        self.lookup_btn = tk.Button(stringid_inner, text="Lookup", command=self._lookup_stringid,
                                    font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                                    relief='flat', padx=14, cursor='hand2')
        self.lookup_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Status bar
        status_frame = tk.Frame(main, bg='#e8e8e8', relief='solid', bd=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        status_label = tk.Label(status_frame, textvariable=self.status_text,
                               font=('Segoe UI', 9), bg='#e8e8e8', fg='#666',
                               anchor='w', padx=8, pady=4)
        status_label.pack(fill=tk.X)

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select Input Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self.input_path.set(path)

    def _update_status(self, text: str):
        self.status_text.set(text)
        self.root.update()

    def _load_data_if_needed(self, need_sequencer: bool = True) -> bool:
        """Load data if not cached or branch changed."""
        branch = self.selected_branch.get()

        if self.cached_branch == branch and self.translation_lookup is not None:
            if not need_sequencer or self.strorigin_index is not None:
                return True  # Already loaded

        paths = BRANCHES.get(branch)
        if not paths:
            messagebox.showerror("Error", f"Unknown branch: {branch}")
            return False

        loc_folder = paths["loc"]
        export_folder = paths["export"]
        sequencer_folder = export_folder / "Sequencer"

        # Validate paths
        if not loc_folder.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_folder}")
            return False

        if need_sequencer:
            if not sequencer_folder.exists():
                messagebox.showerror("Error", f"Sequencer folder not found:\n{sequencer_folder}")
                return False

            # Build Sequencer index
            self.strorigin_index = build_sequencer_strorigin_index(
                sequencer_folder, self._update_status
            )

            if not self.strorigin_index:
                messagebox.showerror("Error", "No Sequencer data found.")
                return False

        # Load language files
        lang_files = discover_language_files(loc_folder)
        if not lang_files:
            messagebox.showerror("Error", "No language files found.")
            return False

        self.translation_lookup = build_translation_lookup(lang_files, self._update_status)
        self.available_langs = list(lang_files.keys())
        self.cached_branch = branch

        return True

    def _translate(self):
        """Run Korean text translation and generate output."""
        # Validate input
        if not self.input_path.get():
            messagebox.showwarning("Warning", "Please select an input Excel file.")
            return

        input_file = Path(self.input_path.get())
        if not input_file.exists():
            messagebox.showerror("Error", f"Input file not found:\n{input_file}")
            return

        # Disable buttons during processing
        self.translate_btn.config(state='disabled')
        self.lookup_btn.config(state='disabled')

        try:
            # Load data if needed
            if not self._load_data_if_needed(need_sequencer=True):
                return

            # Read input
            self._update_status("Reading input file...")
            korean_inputs = read_korean_input(input_file)

            if not korean_inputs:
                messagebox.showwarning("Warning", "No text found in input file.")
                return

            # Find matches
            self._update_status("Finding matches...")
            matches_per_input = []
            total_matches = 0

            for korean_text in korean_inputs:
                matches = find_matches(korean_text, self.strorigin_index)
                matches_per_input.append(matches)
                total_matches += len(matches)

            # Write output
            self._update_status("Writing output...")
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

            self._update_status(f"Done! {len(korean_inputs)} inputs, {total_matches} matches")
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Translation failed:\n{e}")
            self._update_status(f"Error: {e}")

        finally:
            self.translate_btn.config(state='normal')
            self.lookup_btn.config(state='normal')

    def _lookup_stringid(self):
        """Look up a single StringID and generate output."""
        string_id = self.string_id_input.get().strip()

        if not string_id:
            messagebox.showwarning("Warning", "Please enter a StringID.")
            return

        # Disable buttons during processing
        self.translate_btn.config(state='disabled')
        self.lookup_btn.config(state='disabled')

        try:
            # Load data if needed (don't need Sequencer for direct StringID lookup)
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Check if StringID exists in any language
            found = False
            for lang_code, lookup in self.translation_lookup.items():
                if string_id in lookup:
                    found = True
                    break

            if not found:
                messagebox.showwarning("Warning", f"StringID not found: {string_id}")
                self._update_status(f"StringID not found: {string_id}")
                return

            # Write output
            self._update_status("Writing output...")
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"StringID_{string_id}_{timestamp}.xlsx"

            write_stringid_lookup_excel(
                output_path,
                string_id,
                self.translation_lookup,
                self.available_langs
            )

            self._update_status(f"Done! Lookup for {string_id}")
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Lookup failed:\n{e}")
            self._update_status(f"Error: {e}")

        finally:
            self.translate_btn.config(state='normal')
            self.lookup_btn.config(state='normal')


# =============================================================================
# MAIN
# =============================================================================

def main():
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
