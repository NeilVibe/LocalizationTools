"""
QuickTranslate GUI Application.

Tkinter-based GUI with multi-mode support:
- Format Selection: Excel / XML
- Mode Selection: Folder (recursive) / File (single)
- Match Type Selection: Substring / StringID-only / Strict / Special Key
- Settings panel for path configuration
- Detailed logging and reporting
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import config
from core import (
    build_sequencer_strorigin_index,
    scan_folder_for_strings,
    discover_language_files,
    build_translation_lookup,
    build_reverse_lookup,
    find_matches,
    find_matches_with_stats,
    find_matches_stringid_only,
    find_matches_strict,
    find_matches_special_key,
    find_stringid_from_text,
    format_multiple_matches,
    read_korean_input,
    read_corrections_from_excel,
    get_ordered_languages,
    write_output_excel,
    write_stringid_lookup_excel,
    write_folder_translation_excel,
    write_reverse_lookup_excel,
    parse_corrections_from_xml,
    parse_folder_xml_files,
    # TRANSFER functions
    transfer_folder_to_folder,
    transfer_file_to_file,
    format_transfer_report,
    # Korean miss extractor
    extract_korean_misses,
)
from core.indexing import scan_folder_for_entries
from core.language_loader import build_stringid_to_category, build_stringid_to_subfolder
from utils import read_text_file_lines


class QuickTranslateApp:
    """Main GUI application for QuickTranslate."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QuickTranslate")
        self.root.geometry("900x1000")
        self.root.resizable(False, True)
        self.root.minsize(900, 900)
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.format_mode = tk.StringVar(value="excel")  # excel or xml
        self.input_mode = tk.StringVar(value="file")    # folder or file
        self.match_type = tk.StringVar(value="substring")  # substring, stringid_only, strict, special_key

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.string_id_input = tk.StringVar()
        self.reverse_file_path = tk.StringVar()

        # Settings variables
        self.settings_loc_path = tk.StringVar()
        self.settings_export_path = tk.StringVar()

        self.status_text = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar(value=0)

        # Cached data
        self.strorigin_index: Optional[Dict[str, str]] = None
        self.translation_lookup: Optional[Dict[str, Dict[str, str]]] = None
        self.stringid_to_category: Optional[Dict[str, str]] = None
        self.stringid_to_subfolder: Optional[Dict[str, str]] = None
        self.available_langs: Optional[List[str]] = None
        self.cached_paths: Optional[tuple] = None  # (loc_path, export_path)

        # Load current settings into variables
        self._load_settings_to_vars()

        self._create_ui()

    def _load_settings_to_vars(self):
        """Load current config settings into StringVars."""
        settings = config.get_settings()
        self.settings_loc_path.set(settings.get("loc_folder", ""))
        self.settings_export_path.set(settings.get("export_folder", ""))

    def _create_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = tk.Label(main, text="QuickTranslate", font=('Segoe UI', 18, 'bold'),
                        bg='#f0f0f0', fg='#333')
        title.pack(pady=(0, 10))

        # === Format Selection ===
        format_frame = tk.LabelFrame(main, text="Format", font=('Segoe UI', 10, 'bold'),
                                     bg='#f0f0f0', fg='#555', padx=15, pady=8)
        format_frame.pack(fill=tk.X, pady=(0, 8))

        format_inner = tk.Frame(format_frame, bg='#f0f0f0')
        format_inner.pack()

        tk.Radiobutton(format_inner, text="Excel (.xlsx)", variable=self.format_mode,
                      value="excel", font=('Segoe UI', 10), bg='#f0f0f0',
                      activebackground='#f0f0f0', cursor='hand2', padx=20).pack(side=tk.LEFT)
        tk.Radiobutton(format_inner, text="XML (.xml)", variable=self.format_mode,
                      value="xml", font=('Segoe UI', 10), bg='#f0f0f0',
                      activebackground='#f0f0f0', cursor='hand2', padx=20).pack(side=tk.LEFT)

        # === Mode Selection ===
        mode_frame = tk.LabelFrame(main, text="Mode", font=('Segoe UI', 10, 'bold'),
                                   bg='#f0f0f0', fg='#555', padx=15, pady=8)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        mode_inner = tk.Frame(mode_frame, bg='#f0f0f0')
        mode_inner.pack()

        tk.Radiobutton(mode_inner, text="File (single)", variable=self.input_mode,
                      value="file", font=('Segoe UI', 10), bg='#f0f0f0',
                      activebackground='#f0f0f0', cursor='hand2', padx=20).pack(side=tk.LEFT)
        tk.Radiobutton(mode_inner, text="Folder (recursive)", variable=self.input_mode,
                      value="folder", font=('Segoe UI', 10), bg='#f0f0f0',
                      activebackground='#f0f0f0', cursor='hand2', padx=20).pack(side=tk.LEFT)

        # === Match Type Selection ===
        match_frame = tk.LabelFrame(main, text="Match Type", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        match_frame.pack(fill=tk.X, pady=(0, 8))

        match_types = [
            ("substring", "Substring Match", "Find Korean text in StrOrigin"),
            ("stringid_only", "StringID-Only (SCRIPT)", "SCRIPT categories only - match by StringID"),
            ("strict", "StringID + StrOrigin (STRICT)", "Requires BOTH to match exactly"),
            ("special_key", "Special Key Match", "Match by StringID + Category"),
        ]

        for value, label, desc in match_types:
            row = tk.Frame(match_frame, bg='#f0f0f0')
            row.pack(fill=tk.X, pady=2)
            tk.Radiobutton(row, text=label, variable=self.match_type, value=value,
                          font=('Segoe UI', 10), bg='#f0f0f0', activebackground='#f0f0f0',
                          cursor='hand2', width=28, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=('Segoe UI', 9), bg='#f0f0f0', fg='#888').pack(side=tk.LEFT)

        # === Files Section ===
        files_frame = tk.LabelFrame(main, text="Files", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        files_frame.pack(fill=tk.X, pady=(0, 8))

        # Source file/folder
        source_row = tk.Frame(files_frame, bg='#f0f0f0')
        source_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(source_row, text="Source:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.source_entry = tk.Entry(source_row, textvariable=self.source_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(source_row, text="Browse", command=self._browse_source,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Target folder (for strict mode)
        target_row = tk.Frame(files_frame, bg='#f0f0f0')
        target_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(target_row, text="Target:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.target_entry = tk.Entry(target_row, textvariable=self.target_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(target_row, text="Browse", command=self._browse_target,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # === Quick Actions Section ===
        quick_frame = tk.LabelFrame(main, text="Quick Actions", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=8)
        quick_frame.pack(fill=tk.X, pady=(0, 8))

        # StringID Lookup
        stringid_row = tk.Frame(quick_frame, bg='#f0f0f0')
        stringid_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(stringid_row, text="StringID:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.stringid_entry = tk.Entry(stringid_row, textvariable=self.string_id_input,
                                       font=('Segoe UI', 9), relief='solid', bd=1)
        self.stringid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(stringid_row, text="Lookup", command=self._lookup_stringid,
                 font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                 relief='flat', padx=14, cursor='hand2').pack(side=tk.LEFT)

        # Reverse Lookup
        reverse_row = tk.Frame(quick_frame, bg='#f0f0f0')
        reverse_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(reverse_row, text="Reverse:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.reverse_entry = tk.Entry(reverse_row, textvariable=self.reverse_file_path,
                                      font=('Segoe UI', 9), relief='solid', bd=1)
        self.reverse_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(reverse_row, text="Browse", command=self._browse_reverse_file,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(reverse_row, text="Find All", command=self._reverse_lookup,
                 font=('Segoe UI', 9, 'bold'), bg='#d9534f', fg='white',
                 relief='flat', padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Korean Misses - Find Korean strings in Target that don't exist in Source
        korean_miss_row = tk.Frame(quick_frame, bg='#f0f0f0')
        korean_miss_row.pack(fill=tk.X)
        tk.Label(korean_miss_row, text="", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        tk.Label(korean_miss_row, text="Find Korean strings in Target not in Source (uses Source/Target paths above)",
                font=('Segoe UI', 8), bg='#f0f0f0', fg='#888').pack(side=tk.LEFT, padx=(0, 8))
        self.korean_miss_btn = tk.Button(korean_miss_row, text="Extract Korean Misses",
                 command=self._extract_korean_misses,
                 font=('Segoe UI', 9, 'bold'), bg='#f0ad4e', fg='white',
                 relief='flat', padx=10, cursor='hand2')
        self.korean_miss_btn.pack(side=tk.RIGHT)

        # === Settings Section ===
        settings_frame = tk.LabelFrame(main, text="Settings", font=('Segoe UI', 10, 'bold'),
                                       bg='#f0f0f0', fg='#555', padx=15, pady=8)
        settings_frame.pack(fill=tk.X, pady=(0, 8))

        # LOC Path
        loc_row = tk.Frame(settings_frame, bg='#f0f0f0')
        loc_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(loc_row, text="LOC Path:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.loc_entry = tk.Entry(loc_row, textvariable=self.settings_loc_path,
                                  font=('Segoe UI', 9), relief='solid', bd=1)
        self.loc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(loc_row, text="Browse", command=self._browse_loc_path,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Export Path
        export_row = tk.Frame(settings_frame, bg='#f0f0f0')
        export_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(export_row, text="Export Path:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=10, anchor='w').pack(side=tk.LEFT)
        self.export_entry = tk.Entry(export_row, textvariable=self.settings_export_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.export_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(export_row, text="Browse", command=self._browse_export_path,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Save Settings button
        save_row = tk.Frame(settings_frame, bg='#f0f0f0')
        save_row.pack(fill=tk.X)
        tk.Button(save_row, text="Save Settings", command=self._save_settings,
                 font=('Segoe UI', 9, 'bold'), bg='#5bc0de', fg='white',
                 relief='flat', padx=14, cursor='hand2').pack(side=tk.RIGHT)
        tk.Label(save_row, text="Paths are saved to settings.json", font=('Segoe UI', 8),
                bg='#f0f0f0', fg='#888').pack(side=tk.LEFT)

        # === Log Section ===
        log_frame = tk.LabelFrame(main, text="Log", font=('Segoe UI', 10, 'bold'),
                                  bg='#f0f0f0', fg='#555', padx=10, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=6, font=('Consolas', 9), relief='solid', bd=1,
            wrap=tk.WORD, state='disabled'
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Configure log tags for colors
        self.log_area.tag_config('info', foreground='#333')
        self.log_area.tag_config('success', foreground='#008000')
        self.log_area.tag_config('warning', foreground='#FF8C00')
        self.log_area.tag_config('error', foreground='#FF0000')
        self.log_area.tag_config('header', foreground='#4a90d9', font=('Consolas', 9, 'bold'))

        # === Progress Section ===
        progress_frame = tk.Frame(main, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_value,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        status_label = tk.Label(progress_frame, textvariable=self.status_text,
                               font=('Segoe UI', 9), bg='#f0f0f0', fg='#666', anchor='w')
        status_label.pack(fill=tk.X)

        # === Action Buttons ===
        button_frame = tk.Frame(main, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(5, 0))

        self.generate_btn = tk.Button(button_frame, text="Generate", command=self._generate,
                                      font=('Segoe UI', 11, 'bold'), bg='#4a90d9', fg='white',
                                      relief='flat', padx=30, pady=8, cursor='hand2')
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.transfer_btn = tk.Button(button_frame, text="TRANSFER", command=self._transfer,
                                      font=('Segoe UI', 11, 'bold'), bg='#d9534f', fg='white',
                                      relief='flat', padx=25, pady=8, cursor='hand2')
        self.transfer_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Clear Log", command=self._clear_log,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=15, pady=6, cursor='hand2').pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Clear All", command=self._clear_fields,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=15, pady=6, cursor='hand2').pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Exit", command=self.root.quit,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=20, pady=6, cursor='hand2').pack(side=tk.LEFT)

    def _log(self, message: str, tag: str = 'info'):
        """Add message to log area."""
        self.log_area.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update()

    def _clear_log(self):
        """Clear the log area."""
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

    def _analyze_folder(self, folder_path: str, role: str) -> None:
        """Analyze a folder and print detailed info to terminal and log.

        Args:
            folder_path: Path to the folder to analyze
            role: "SOURCE" or "TARGET" for display purposes
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"\n[{role}] ERROR: Path does not exist or is not a directory: {folder_path}")
            self._log(f"{role} folder invalid: {folder_path}", 'error')
            return

        try:
            all_files = list(folder.iterdir())
        except OSError as e:
            print(f"\n[{role}] ERROR: Cannot read folder: {e}")
            self._log(f"{role} folder unreadable: {e}", 'error')
            return

        xml_files = [f for f in all_files if f.suffix.lower() == ".xml" and f.is_file()]
        xlsx_files = [f for f in all_files if f.suffix.lower() in (".xlsx", ".xls") and f.is_file()]
        categorized = set(xml_files) | set(xlsx_files)
        other_files = [f for f in all_files if f.is_file() and f not in categorized]
        subdirs = [f for f in all_files if f.is_dir()]

        # Identify languagedata files and extract language codes
        lang_files = []
        non_lang_xml = []
        for f in xml_files:
            name = f.stem.lower()
            if name.startswith("languagedata_"):
                lang_code = f.stem[13:]  # Preserve original case
                try:
                    size_kb = f.stat().st_size / 1024
                except OSError:
                    size_kb = 0
                lang_files.append((f.name, lang_code, size_kb))
            else:
                non_lang_xml.append(f.name)

        # Terminal output
        separator = "=" * 60
        print(f"\n{separator}")
        print(f"  {role} FOLDER ANALYSIS")
        print(f"{separator}")
        print(f"  Path: {folder_path}")
        print(f"  Total items: {len(all_files)} ({len(xml_files)} XML, {len(xlsx_files)} Excel, {len(other_files)} other, {len(subdirs)} subdirs)")
        print(f"{'-' * 60}")

        if lang_files:
            print(f"\n  LANGUAGEDATA FILES ({len(lang_files)} found):")
            print(f"  {'#':<4} {'Filename':<35} {'Lang':<8} {'Size':<10}")
            print(f"  {'-'*4} {'-'*35} {'-'*8} {'-'*10}")
            total_size = 0
            for idx, (fname, lang, size) in enumerate(sorted(lang_files, key=lambda x: x[1]), 1):
                total_size += size
                if size >= 1024:
                    size_str = f"{size/1024:.1f} MB"
                else:
                    size_str = f"{size:.0f} KB"
                print(f"  {idx:<4} {fname:<35} {lang:<8} {size_str:<10}")
            if total_size >= 1024:
                total_str = f"{total_size/1024:.1f} MB"
            else:
                total_str = f"{total_size:.0f} KB"
            print(f"  {'-'*4} {'-'*35} {'-'*8} {'-'*10}")
            print(f"  {'':4} {'TOTAL':<35} {'':<8} {total_str:<10}")
        else:
            print(f"\n  WARNING: No languagedata_*.xml files found!")

        if non_lang_xml:
            print(f"\n  OTHER XML FILES ({len(non_lang_xml)}):")
            for f in non_lang_xml:
                print(f"    - {f}")

        if xlsx_files:
            print(f"\n  EXCEL FILES ({len(xlsx_files)}):")
            for f in xlsx_files:
                try:
                    size_kb = f.stat().st_size / 1024
                    print(f"    - {f.name} ({size_kb:.0f} KB)")
                except OSError:
                    print(f"    - {f.name} (size unknown)")

        if subdirs:
            print(f"\n  SUBDIRECTORIES ({len(subdirs)}):")
            for d in subdirs:
                print(f"    - {d.name}/")

        # Validation
        print(f"\n  VALIDATION:")
        is_eligible = len(lang_files) > 0
        lang_codes = sorted([lc for _, lc, _ in lang_files]) if lang_files else []
        if is_eligible:
            print(f"  [OK] Eligible for TRANSFER ({len(lang_files)} language files)")
            print(f"  [OK] Languages: {', '.join(lang_codes)}")
        else:
            print(f"  [!!] NOT eligible for TRANSFER - no languagedata_*.xml files")

        if non_lang_xml:
            print(f"  [!!] {len(non_lang_xml)} non-languagedata XML files will be IGNORED")
        if subdirs:
            print(f"  [!!] {len(subdirs)} subdirectories will be IGNORED (flat scan only)")

        print(f"{separator}\n")

        # Also log to GUI
        if is_eligible:
            self._log(f"{role}: {len(lang_files)} languagedata files found - ELIGIBLE", 'success')
            self._log(f"  Languages: {', '.join(lang_codes)}", 'info')
        else:
            self._log(f"{role}: No languagedata files found - NOT ELIGIBLE", 'error')

    def _browse_source(self):
        """Browse for source file or folder based on mode."""
        if self.input_mode.get() == "folder":
            path = filedialog.askdirectory(title="Select Source Folder")
        else:
            if self.format_mode.get() == "excel":
                filetypes = [("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            else:
                filetypes = [("XML files", "*.xml"), ("All files", "*.*")]
            path = filedialog.askopenfilename(title="Select Source File", filetypes=filetypes)
        if path:
            self.source_path.set(path)
            if self.input_mode.get() == "folder":
                self._analyze_folder(path, "SOURCE")

    def _browse_target(self):
        """Browse for target folder."""
        path = filedialog.askdirectory(title="Select Target Folder")
        if path:
            self.target_path.set(path)
            self._analyze_folder(path, "TARGET")

    def _browse_reverse_file(self):
        """Browse for reverse lookup text file."""
        path = filedialog.askopenfilename(
            title="Select Text File with List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.reverse_file_path.set(path)

    def _browse_loc_path(self):
        """Browse for LOC folder path."""
        path = filedialog.askdirectory(title="Select LOC Folder (languagedata_*.xml files)")
        if path:
            self.settings_loc_path.set(path)

    def _browse_export_path(self):
        """Browse for Export folder path."""
        path = filedialog.askdirectory(title="Select Export Folder (categorized .loc.xml files)")
        if path:
            self.settings_export_path.set(path)

    def _save_settings(self):
        """Save current settings to config file."""
        loc_path = self.settings_loc_path.get().strip()
        export_path = self.settings_export_path.get().strip()

        if not loc_path and not export_path:
            messagebox.showwarning("Warning", "Please enter at least one path to save.")
            return

        # Validate paths exist
        if loc_path and not Path(loc_path).exists():
            if not messagebox.askyesno("Warning", f"LOC path does not exist:\n{loc_path}\n\nSave anyway?"):
                return

        if export_path and not Path(export_path).exists():
            if not messagebox.askyesno("Warning", f"Export path does not exist:\n{export_path}\n\nSave anyway?"):
                return

        # Save settings
        config.update_settings(
            loc_folder=loc_path if loc_path else None,
            export_folder=export_path if export_path else None
        )

        # Clear cached data since paths changed
        self.cached_paths = None
        self.strorigin_index = None
        self.translation_lookup = None
        self.stringid_to_category = None
        self.stringid_to_subfolder = None

        self._log("Settings saved to settings.json", 'success')
        messagebox.showinfo("Success", "Settings saved successfully!")

    def _update_status(self, text: str, progress: float = None):
        """Update status text and optionally progress bar."""
        self.status_text.set(text)
        if progress is not None:
            self.progress_value.set(progress)
        self.root.update()

    def _load_data_if_needed(self, need_sequencer: bool = True) -> bool:
        """Load data if not cached or paths changed."""
        loc_folder = config.LOC_FOLDER
        export_folder = config.EXPORT_FOLDER
        current_paths = (str(loc_folder), str(export_folder))

        if self.cached_paths == current_paths and self.translation_lookup is not None:
            if not need_sequencer or self.strorigin_index is not None:
                return True

        sequencer_folder = export_folder / "Sequencer"

        if not loc_folder.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_folder}\n\nPlease configure in Settings.")
            return False

        if need_sequencer:
            if not sequencer_folder.exists():
                messagebox.showerror("Error", f"Sequencer folder not found:\n{sequencer_folder}\n\nPlease check Export path in Settings.")
                return False

            self._log(f"Loading Sequencer data...", 'info')
            self.strorigin_index = build_sequencer_strorigin_index(
                sequencer_folder, self._update_status
            )

            if not self.strorigin_index:
                messagebox.showerror("Error", "No Sequencer data found.")
                return False

            self._log(f"Loaded {len(self.strorigin_index)} Sequencer entries", 'success')

            # Also build category mapping for StringID-only mode
            self._update_status("Building category index...")
            self._log("Building category index...", 'info')
            self.stringid_to_category = build_stringid_to_category(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_category)} StringIDs to categories", 'success')

            # Build subfolder mapping for exclusion filtering
            self._update_status("Building subfolder index...")
            self._log("Building subfolder index...", 'info')
            self.stringid_to_subfolder = build_stringid_to_subfolder(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_subfolder)} StringIDs to subfolders", 'success')

        # Load language files
        self._log("Discovering language files...", 'info')
        lang_files = discover_language_files(loc_folder)
        if not lang_files:
            messagebox.showerror("Error", "No language files found.")
            return False

        self._log(f"Found {len(lang_files)} languages: {', '.join(lang_files.keys())}", 'success')

        self.translation_lookup = build_translation_lookup(lang_files, self._update_status)
        self.available_langs = list(lang_files.keys())
        self.cached_paths = current_paths

        return True

    def _clear_fields(self):
        """Clear all input fields."""
        self.source_path.set("")
        self.target_path.set("")
        self.string_id_input.set("")
        self.reverse_file_path.set("")
        self.progress_value.set(0)
        self.status_text.set("Ready")
        self._clear_log()

    def _disable_buttons(self):
        """Disable all action buttons during processing."""
        self.generate_btn.config(state='disabled')
        self.transfer_btn.config(state='disabled')
        self.korean_miss_btn.config(state='disabled')

    def _enable_buttons(self):
        """Re-enable all action buttons."""
        self.generate_btn.config(state='normal')
        self.transfer_btn.config(state='normal')
        self.korean_miss_btn.config(state='normal')

    def _generate(self):
        """Main generate action based on current mode."""
        if not self.source_path.get():
            messagebox.showwarning("Warning", "Please select a source file/folder.")
            return

        source = Path(self.source_path.get())
        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        match_type = self.match_type.get()
        self._log(f"=== QuickTranslate Generation ===", 'header')
        self._log(f"Match Type: {match_type.upper()}", 'info')
        self._log(f"Format: {self.format_mode.get().upper()}", 'info')
        self._log(f"Mode: {self.input_mode.get().upper()}", 'info')

        try:
            # Load data
            if not self._load_data_if_needed(need_sequencer=True):
                return

            self.progress_value.set(20)

            # Read input based on format and mode
            corrections = []
            korean_inputs = []

            # Read from source file/folder
            if self.input_mode.get() == "folder":
                # FOLDER MODE: Auto-detect and handle mixed Excel + XML
                xml_files = list(source.rglob("*.xml"))
                excel_files = list(source.rglob("*.xlsx")) + list(source.rglob("*.xls"))

                if xml_files:
                    xml_corrections = parse_folder_xml_files(source, self._update_status)
                    corrections.extend(xml_corrections)
                    self._log(f"Loaded {len(xml_corrections)} corrections from {len(xml_files)} XML files", 'info')

                if excel_files:
                    for excel_file in excel_files:
                        excel_corrections = read_corrections_from_excel(excel_file)
                        corrections.extend(excel_corrections)
                    self._log(f"Loaded {sum(1 for _ in excel_files)} Excel files", 'info')

                korean_inputs = [c.get("str_origin", "") for c in corrections if c.get("str_origin")]
                if not korean_inputs:
                    korean_inputs = [c.get("string_id", "") for c in corrections if c.get("string_id")]
            else:
                # FILE MODE: Auto-detect by extension
                suffix = source.suffix.lower()
                if suffix in (".xlsx", ".xls"):
                    korean_inputs = read_korean_input(source)
                    self._log(f"Read {len(korean_inputs)} inputs from Excel", 'info')

                    # For non-substring modes, build corrections from Excel
                    if match_type in ("stringid_only", "strict", "special_key"):
                        excel_corrections = read_corrections_from_excel(source)
                        corrections.extend(excel_corrections)
                        self._log(f"Loaded {len(excel_corrections)} corrections from Excel", 'info')
                        if corrections:
                            korean_inputs = [c.get("str_origin", "") or c.get("string_id", "") for c in corrections]
                else:
                    # XML format
                    xml_corrections = parse_corrections_from_xml(source)
                    corrections.extend(xml_corrections)
                    korean_inputs = [c.get("str_origin", "") for c in corrections if c.get("str_origin")]
                    self._log(f"Loaded {len(xml_corrections)} corrections from XML", 'info')

            if not korean_inputs and not corrections:
                messagebox.showwarning("Warning", "No input data found.")
                self._log("No input data found!", 'error')
                return

            self.progress_value.set(40)

            # Find matches based on match type
            self._update_status("Finding matches...")
            self._log(f"Finding matches using {match_type} mode...", 'info')

            matches_per_input = []
            stats = {"total": len(korean_inputs), "matched": 0, "no_match": 0, "multi_match": 0, "skipped": 0, "total_matches": 0}

            if match_type == "substring":
                # Use new stats-tracking function
                matches_per_input, stats = find_matches_with_stats(korean_inputs, self.strorigin_index)
                self._log(f"Substring search complete:", 'info')
                self._log(f"  - Total inputs: {stats['total']}", 'info')
                self._log(f"  - Matched (1): {stats['matched']}", 'success')
                self._log(f"  - Multi-match: {stats['multi_match']}", 'warning')
                self._log(f"  - Not found: {stats['no_match']}", 'error')

            elif match_type == "stringid_only":
                # StringID-only (SCRIPT): Filter to SCRIPT categories
                if not self.stringid_to_category:
                    messagebox.showwarning("Warning", "Category index not loaded.")
                    return

                if corrections:
                    script_corrections, skipped = find_matches_stringid_only(
                        corrections, self.stringid_to_category
                    )
                    korean_inputs = [c.get("str_origin", "") for c in script_corrections]
                    for c in script_corrections:
                        matches_per_input.append([c.get("string_id")])
                    stats["total"] = len(corrections)
                    stats["matched"] = len(script_corrections)
                    stats["skipped"] = skipped
                    stats["total_matches"] = len(script_corrections)
                    self._log(f"SCRIPT filter results:", 'info')
                    self._log(f"  - Total corrections: {stats['total']}", 'info')
                    self._log(f"  - SCRIPT strings kept: {stats['matched']}", 'success')
                    self._log(f"  - Non-SCRIPT skipped: {stats['skipped']}", 'warning')
                else:
                    # Excel mode with StringIDs in column A
                    for text in korean_inputs:
                        sid = text.strip()
                        category = self.stringid_to_category.get(sid, "")
                        if category in config.SCRIPT_CATEGORIES:
                            matches_per_input.append([sid])
                            stats["matched"] += 1
                        else:
                            matches_per_input.append([])
                            stats["skipped"] += 1
                    stats["total_matches"] = stats["matched"]

            elif match_type == "strict":
                # Strict mode: Match by StringID + StrOrigin tuple
                if not corrections:
                    messagebox.showwarning("Warning", "Strict mode requires XML input or corrections data.")
                    return

                target = self.target_path.get()
                if target:
                    self._log(f"Scanning target folder: {target}", 'info')
                    xml_entries = scan_folder_for_entries(Path(target), self._update_status)
                    self._log(f"Found {len(xml_entries)} entries in target", 'info')

                    matched, not_found = find_matches_strict(corrections, xml_entries)
                    korean_inputs = [c.get("str_origin", "") for c in matched]
                    for c in matched:
                        matches_per_input.append([c.get("string_id")])
                    stats["total"] = len(corrections)
                    stats["matched"] = len(matched)
                    stats["no_match"] = not_found
                    stats["total_matches"] = len(matched)
                    self._log(f"Strict match results:", 'info')
                    self._log(f"  - Total corrections: {stats['total']}", 'info')
                    self._log(f"  - Matched (ID+Origin): {stats['matched']}", 'success')
                    self._log(f"  - Not found: {stats['no_match']}", 'error')
                else:
                    messagebox.showwarning("Warning", "Strict mode requires a Target folder for matching.")
                    return

            elif match_type == "special_key":
                # Special key mode - use hardcoded field combination (string_id, category)
                if not corrections:
                    messagebox.showwarning("Warning", "Special Key mode requires corrections data (XML or structured Excel).")
                    return

                # Use hardcoded key fields from config
                key_fields = config.SPECIAL_KEY_FIELDS

                self._log(f"Using key fields: {key_fields}", 'info')

                # Build target entries with same key pattern
                target = self.target_path.get()
                if target:
                    raw_entries = scan_folder_for_entries(Path(target), self._update_status)
                    # Convert to special key format
                    xml_entries = {}
                    for (sid, origin), entry in raw_entries.items():
                        key_parts = []
                        for field in key_fields:
                            if field == "string_id":
                                key_parts.append(sid.lower())
                            elif field == "str_origin":
                                key_parts.append(origin.lower())
                            elif field == "category":
                                key_parts.append(self.stringid_to_category.get(sid, "").lower())
                            else:
                                key_parts.append(entry.get(field, "").lower() if entry.get(field) else "")
                        xml_entries[":".join(key_parts)] = entry

                    matched, not_found = find_matches_special_key(corrections, xml_entries, key_fields)
                    korean_inputs = [c.get("str_origin", "") for c in matched]
                    for c in matched:
                        matches_per_input.append([c.get("string_id")])
                    stats["total"] = len(corrections)
                    stats["matched"] = len(matched)
                    stats["no_match"] = not_found
                    stats["total_matches"] = len(matched)
                    self._log(f"Special Key match results:", 'info')
                    self._log(f"  - Total corrections: {stats['total']}", 'info')
                    self._log(f"  - Matched: {stats['matched']}", 'success')
                    self._log(f"  - Not found: {stats['no_match']}", 'error')
                else:
                    # No target - just use StringID matching against translation lookup
                    # Use any language lookup to check if StringID exists
                    any_lookup = next(iter(self.translation_lookup.values()), {})
                    for c in corrections:
                        sid = c.get("string_id", "")
                        if sid and sid in any_lookup:
                            matches_per_input.append([sid])
                            stats["matched"] += 1
                        else:
                            matches_per_input.append([])
                            stats["no_match"] += 1
                    korean_inputs = [c.get("str_origin", "") for c in corrections]
                    stats["total"] = len(corrections)
                    stats["total_matches"] = stats["matched"]
                    self._log(f"Special Key (no target): {stats['matched']} found, {stats['no_match']} not in translations", 'info')

            self.progress_value.set(70)

            # Write output
            self._update_status("Writing output...")
            self._log("Writing output Excel...", 'info')
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"QuickTranslate_{timestamp}.xlsx"

            write_output_excel(
                output_path,
                korean_inputs,
                matches_per_input,
                self.translation_lookup,
                self.available_langs,
                config.LANGUAGE_NAMES,
                stats=stats,
                match_type=match_type,
            )

            self.progress_value.set(100)
            self._update_status(f"Done! {stats['total']} inputs processed")
            self._log(f"=== Generation Complete ===", 'header')
            self._log(f"Output: {output_path}", 'success')
            self._log(f"Summary: {stats['matched']} matched, {stats.get('no_match', 0)} not found, {stats.get('skipped', 0)} skipped", 'info')

            messagebox.showinfo("Success", f"Output saved to:\n{output_path}\n\n"
                              f"Total: {stats['total']}\n"
                              f"Matched: {stats['matched']}\n"
                              f"Not Found: {stats.get('no_match', 0)}\n"
                              f"Skipped: {stats.get('skipped', 0)}")

        except Exception as e:
            messagebox.showerror("Error", f"Generation failed:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: {e}")

        finally:
            self._enable_buttons()

    def _lookup_stringid(self):
        """Look up a single StringID."""
        string_id = self.string_id_input.get().strip()

        if not string_id:
            messagebox.showwarning("Warning", "Please enter a StringID.")
            return

        self._disable_buttons()
        self._log(f"Looking up StringID: {string_id}", 'info')

        try:
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Check if StringID exists
            found = False
            for lang_code, lookup in self.translation_lookup.items():
                if string_id in lookup:
                    found = True
                    break

            if not found:
                messagebox.showwarning("Warning", f"StringID not found: {string_id}")
                self._log(f"StringID not found: {string_id}", 'error')
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
                self.available_langs,
                config.LANGUAGE_NAMES,
            )

            self._update_status(f"Done! Lookup for {string_id}")
            self._log(f"Output saved: {output_path}", 'success')
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Lookup failed:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: {e}")

        finally:
            self._enable_buttons()

    def _reverse_lookup(self):
        """Perform reverse lookup from any language to all languages."""
        if not self.reverse_file_path.get():
            messagebox.showwarning("Warning", "Please select a text file with list of strings.")
            return

        file_path = Path(self.reverse_file_path.get())
        if not file_path.exists():
            messagebox.showerror("Error", f"File not found:\n{file_path}")
            return

        self._disable_buttons()
        self._log(f"Reverse lookup from: {file_path}", 'info')

        try:
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Read input file
            self._update_status("Reading input file...")
            input_texts = read_text_file_lines(file_path)

            if not input_texts:
                messagebox.showwarning("Warning", "No text found in input file.")
                return

            self._log(f"Read {len(input_texts)} texts from file", 'info')

            # Build reverse lookup
            self._update_status("Building reverse lookup...")
            reverse_lookup = build_reverse_lookup(self.translation_lookup)

            # Find StringID for each input text
            self._update_status("Finding StringIDs...")
            stringid_map = {}
            not_found = []
            detected_langs = set()

            for text in input_texts:
                result = find_stringid_from_text(text, reverse_lookup)
                if result:
                    string_id, lang = result
                    stringid_map[text] = string_id
                    detected_langs.add(lang)
                else:
                    not_found.append(text)

            self._log(f"Found: {len(stringid_map)}, Not found: {len(not_found)}", 'info')
            if detected_langs:
                self._log(f"Detected languages: {', '.join(sorted(detected_langs))}", 'info')

            # Write output
            self._update_status("Writing output...")
            config.ensure_output_folder()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.OUTPUT_FOLDER / f"ReverseLookup_{timestamp}.xlsx"

            write_reverse_lookup_excel(
                output_path,
                input_texts,
                stringid_map,
                self.translation_lookup,
                self.available_langs,
                config.LANGUAGE_NAMES,
            )

            found_count = len(stringid_map)
            total_count = len(input_texts)
            detected_str = ", ".join(sorted(detected_langs)) if detected_langs else "N/A"

            self._update_status(f"Done! {found_count}/{total_count} found")
            self._log(f"Output saved: {output_path}", 'success')
            messagebox.showinfo("Success",
                f"Output saved to:\n{output_path}\n\n"
                f"Found: {found_count}/{total_count}\n"
                f"Detected languages: {detected_str}")

        except Exception as e:
            messagebox.showerror("Error", f"Reverse lookup failed:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: {e}")

        finally:
            self._enable_buttons()

    def _extract_korean_misses(self):
        """Extract Korean strings from Target that don't exist in Source."""
        # Validate source file (should be XML)
        source_path = self.source_path.get().strip()
        if not source_path:
            messagebox.showwarning("Warning", "Please select a Source XML file (the reference file).")
            return

        source = Path(source_path)
        if not source.exists():
            messagebox.showerror("Error", f"Source file not found:\n{source}")
            return

        if not source.suffix.lower() == ".xml":
            messagebox.showwarning("Warning", "Source file must be an XML file (e.g., languagedata_kor.xml)")
            return

        # Validate target file (should be XML)
        target_path = self.target_path.get().strip()
        if not target_path:
            messagebox.showwarning("Warning", "Please select a Target XML file (the file to check for Korean misses).")
            return

        target = Path(target_path)
        if not target.exists():
            messagebox.showerror("Error", f"Target file not found:\n{target}")
            return

        # If target is a directory, try to find single XML or ask user
        if target.is_dir():
            xml_files = list(target.glob("*.xml"))
            if len(xml_files) == 1:
                target = xml_files[0]
            elif len(xml_files) == 0:
                messagebox.showerror("Error", f"No XML files found in target folder:\n{target}")
                return
            else:
                messagebox.showwarning(
                    "Warning",
                    "Target must be a single XML file, not a folder with multiple XML files.\n"
                    "Please select a specific XML file."
                )
                return

        # Ask user for output file location
        output_path = filedialog.asksaveasfilename(
            title="Save Korean Misses Output",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            initialfile=f"korean_misses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        )

        if not output_path:
            return  # User cancelled

        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        self._log("=== Extract Korean Misses ===", 'header')
        self._log(f"Source (reference): {source}", 'info')
        self._log(f"Target (to check): {target}", 'info')
        self._log(f"Output: {output_path}", 'info')

        # Default excluded paths for system strings
        # File attr format is "System/Gimmick/file.xml" (no "export" prefix, PascalCase)
        excluded_paths = ["System/MultiChange", "System/Gimmick"]
        self._log(f"Excluded paths: {', '.join(excluded_paths)}", 'info')

        try:
            self._update_status("Extracting Korean misses...")
            self.progress_value.set(20)

            # Get export folder from config for StringID -> File path mapping
            export_folder = str(config.EXPORT_FOLDER)
            self._log(f"Export folder: {export_folder}", 'info')

            # Print info to terminal as well (GUI log is small)
            print(f"\n[GUI] Starting Korean Miss Extraction...")
            print(f"[GUI] Export folder: {export_folder}")

            # Call the extraction function - it will print detailed results to terminal
            stats = extract_korean_misses(
                source_file=str(source),
                target_file=str(target),
                output_file=output_path,
                export_folder=export_folder,
                excluded_paths=excluded_paths,
                progress_callback=self._update_status
            )

            self.progress_value.set(100)

            # Log results
            self._log("=== Results ===", 'header')
            self._log(f"Korean strings in Target: {stats['total_target_korean']}", 'info')
            self._log(f"Hits (found in Source): {stats['hits']}", 'success')
            self._log(f"Misses before filter: {stats['misses_before_filter']}", 'warning')
            self._log(f"Filtered out (excluded paths): {stats['filtered_out']}", 'info')
            self._log(f"Final misses written: {stats['final_misses']}", 'error' if stats['final_misses'] > 0 else 'success')
            self._log(f"Output saved: {output_path}", 'success')

            self._update_status(f"Done! {stats['final_misses']} Korean misses found")

            # No GUI popup - all debug info is in terminal
            # User requested terminal-only output for debugging

        except FileNotFoundError as e:
            messagebox.showerror("Error", f"File not found:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: File not found")

        except ValueError as e:
            messagebox.showerror("Error", f"XML parsing error:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: XML parsing failed")

        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self._enable_buttons()

    def _transfer(self):
        """Transfer corrections from source to target XML files (LOC folder)."""
        if not self.source_path.get():
            messagebox.showwarning("Warning", "Please select a Source file/folder with corrections.")
            return

        if not self.target_path.get():
            # Default to LOC folder from config
            self.target_path.set(str(config.LOC_FOLDER))

        source = Path(self.source_path.get())
        target = Path(self.target_path.get())

        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        if not target.exists():
            messagebox.showerror("Error", f"Target folder not found:\n{target}")
            return

        # Confirm with user
        match_type = self.match_type.get()
        mode_str = "Folder" if self.input_mode.get() == "folder" else "File"
        match_str = match_type.upper()

        confirm = messagebox.askyesno(
            "Confirm Transfer",
            f"This will WRITE corrections to XML files in:\n{target}\n\n"
            f"Source Mode: {mode_str}\n"
            f"Match Mode: {match_str}\n\n"
            f"Are you sure you want to proceed?"
        )

        if not confirm:
            return

        self._disable_buttons()
        self.progress_value.set(0)
        self._clear_log()

        self._log("=== QuickTranslate TRANSFER ===", 'header')
        self._log(f"Match Mode: {match_str}", 'info')
        self._log(f"Source: {source}", 'info')
        self._log(f"Target: {target}", 'info')

        try:
            # Pre-transfer cross-match analysis (folder mode)
            if self.input_mode.get() == "folder" and source.is_dir() and target.is_dir():
                src_xmls = {f.stem.lower()[13:]: f.name for f in source.glob("*.xml") if f.stem.lower().startswith("languagedata_")}
                tgt_xmls = {f.stem.lower()[13:]: f.name for f in target.glob("*.xml") if f.stem.lower().startswith("languagedata_")}
                matched_langs = sorted(set(src_xmls.keys()) & set(tgt_xmls.keys()))
                src_only = sorted(set(src_xmls.keys()) - set(tgt_xmls.keys()))
                tgt_only = sorted(set(tgt_xmls.keys()) - set(src_xmls.keys()))

                print(f"\n{'=' * 60}")
                print(f"  TRANSFER CROSS-MATCH ANALYSIS")
                print(f"{'=' * 60}")
                print(f"  Source: {len(src_xmls)} languagedata files")
                print(f"  Target: {len(tgt_xmls)} languagedata files")
                print(f"  Matched: {len(matched_langs)} pairs")
                print(f"{'-' * 60}")
                if matched_langs:
                    print(f"\n  MATCHED PAIRS ({len(matched_langs)}):")
                    for lang in matched_langs:
                        print(f"    {src_xmls[lang]:<35} --> {tgt_xmls[lang]}")
                if src_only:
                    print(f"\n  SOURCE ONLY (no target match - SKIPPED):")
                    for lang in src_only:
                        print(f"    {src_xmls[lang]:<35} --> [NO MATCH]")
                if tgt_only:
                    print(f"\n  TARGET ONLY (no source - UNCHANGED):")
                    for lang in tgt_only:
                        print(f"    {'[NO SOURCE]':<35} --> {tgt_xmls[lang]}")
                print(f"{'=' * 60}\n")

                self._log(f"Cross-match: {len(matched_langs)} pairs, {len(src_only)} source-only, {len(tgt_only)} target-only", 'info')

            # Load category data if needed for stringid_only mode
            stringid_to_category = None
            stringid_to_subfolder = None
            if match_type == "stringid_only":
                if not self._load_data_if_needed(need_sequencer=True):
                    return
                stringid_to_category = self.stringid_to_category
                stringid_to_subfolder = self.stringid_to_subfolder

            self.progress_value.set(20)
            self._update_status("Transferring corrections...")

            # Perform transfer
            if self.input_mode.get() == "folder":
                results = transfer_folder_to_folder(
                    source,
                    target,
                    stringid_to_category=stringid_to_category,
                    stringid_to_subfolder=stringid_to_subfolder,
                    match_mode="stringid_only" if match_type == "stringid_only" else "strict",
                    dry_run=False,
                    progress_callback=self._update_status,
                )
                report_mode = "folder"
            else:
                # Single file mode - find matching languagedata_*.xml in target folder
                target_file = target
                if target.is_dir():
                    source_name = source.stem.lower()
                    lang_code = None

                    # Extract language code from source filename
                    if source_name.startswith("languagedata_"):
                        lang_code = source_name[13:]
                    elif "_" in source_name:
                        lang_code = source_name.split("_")[-1]

                    if lang_code:
                        candidates = [
                            target / f"languagedata_{lang_code}.xml",
                            target / f"languagedata_{lang_code.upper()}.xml",
                            target / f"languagedata_{lang_code.lower()}.xml",
                        ]
                        for c in candidates:
                            if c.exists():
                                target_file = c
                                break

                    # If no match found, check for single XML
                    if target_file.is_dir():
                        xml_files = list(target.glob("*.xml"))
                        if len(xml_files) == 1:
                            target_file = xml_files[0]
                        elif len(xml_files) == 0:
                            messagebox.showerror("Error", f"No XML files found in target folder:\n{target}")
                            return
                        else:
                            messagebox.showwarning(
                                "Warning",
                                f"Multiple XML files in target folder. Please use Folder mode or specify a single file."
                            )
                            return

                self._log(f"Target file: {target_file}", 'info')

                results = transfer_file_to_file(
                    source,
                    target_file,
                    stringid_to_category=stringid_to_category,
                    stringid_to_subfolder=stringid_to_subfolder,
                    match_mode="stringid_only" if match_type == "stringid_only" else "strict",
                    dry_run=False,
                )
                report_mode = "file"

            self.progress_value.set(80)

            # Generate report
            report = format_transfer_report(results, mode=report_mode)

            # Log the report
            for line in report.split("\n"):
                if "SUCCESS" in line or "UPDATED" in line or "●" in line:
                    self._log(line, 'success')
                elif "ERROR" in line or "x" in line or "NOT_FOUND" in line or "○" in line:
                    self._log(line, 'error')
                elif "WARN" in line or "half" in line or "SKIPPED" in line:
                    self._log(line, 'warning')
                elif "=" in line or "|" in line or "REPORT" in line:
                    self._log(line, 'header')
                else:
                    self._log(line, 'info')

            self.progress_value.set(100)

            # Summary
            if report_mode == "folder":
                updated = results.get("total_updated", 0)
                matched = results.get("total_matched", 0)
                not_found = results.get("total_not_found", 0)
            else:
                updated = results.get("updated", 0)
                matched = results.get("matched", 0)
                not_found = results.get("not_found", 0)

            self._update_status(f"Transfer complete: {updated} updated")

            messagebox.showinfo(
                "Transfer Complete",
                f"Transfer completed!\n\n"
                f"Matched: {matched}\n"
                f"Updated: {updated}\n"
                f"Not Found: {not_found}\n\n"
                f"Target: {target}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Transfer failed:\n{e}")
            self._log(f"ERROR: {e}", 'error')
            self._update_status(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self._enable_buttons()


def run_app():
    """Create and run the application."""
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()
