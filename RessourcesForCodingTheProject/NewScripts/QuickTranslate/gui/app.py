"""
QuickTranslate GUI Application.

Tkinter-based GUI with multi-mode support:
- Format Selection: Excel / XML
- Mode Selection: Folder (recursive) / File (single)
- Match Type Selection: StringID-only / Strict / Special Key
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
    find_matches_stringid_only,
    find_matches_strict,
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
)
from core.indexing import scan_folder_for_entries
from core.language_loader import build_stringid_to_category
from utils import read_text_file_lines


class QuickTranslateApp:
    """Main GUI application for QuickTranslate."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("QuickTranslate")
        self.root.geometry("850x750")
        self.root.resizable(False, False)
        self.root.configure(bg='#f0f0f0')

        # Variables
        self.format_mode = tk.StringVar(value="excel")  # excel or xml
        self.input_mode = tk.StringVar(value="file")    # folder or file
        self.match_type = tk.StringVar(value="substring")  # substring, stringid_only, strict, special_key

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.string_id_input = tk.StringVar()
        self.reverse_file_path = tk.StringVar()
        self.tosubmit_enabled = tk.BooleanVar(value=False)

        self.selected_source_branch = tk.StringVar(value="mainline")
        self.selected_target_branch = tk.StringVar(value="mainline")
        self.status_text = tk.StringVar(value="Ready")
        self.progress_value = tk.DoubleVar(value=0)

        # Cached data
        self.strorigin_index: Optional[Dict[str, str]] = None
        self.translation_lookup: Optional[Dict[str, Dict[str, str]]] = None
        self.stringid_to_category: Optional[Dict[str, str]] = None
        self.available_langs: Optional[List[str]] = None
        self.cached_branch: Optional[str] = None

        self._create_ui()

    def _create_ui(self):
        """Create the main UI layout."""
        # Main container with padding
        main = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = tk.Label(main, text="QuickTranslate", font=('Segoe UI', 18, 'bold'),
                        bg='#f0f0f0', fg='#333')
        title.pack(pady=(0, 15))

        # === Format Selection ===
        format_frame = tk.LabelFrame(main, text="Format", font=('Segoe UI', 10, 'bold'),
                                     bg='#f0f0f0', fg='#555', padx=15, pady=10)
        format_frame.pack(fill=tk.X, pady=(0, 10))

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
                                   bg='#f0f0f0', fg='#555', padx=15, pady=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

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
                                    bg='#f0f0f0', fg='#555', padx=15, pady=10)
        match_frame.pack(fill=tk.X, pady=(0, 10))

        match_types = [
            ("substring", "Substring Match", "Original - finds text in StrOrigin"),
            ("stringid_only", "StringID-Only (SCRIPT)", "For Sequencer/Dialog - match by StringID only"),
            ("strict", "StringID + StrOrigin (STRICT)", "Most precise - requires both to match"),
            ("special_key", "Special Key Match", "Custom composite key matching"),
        ]

        for value, label, desc in match_types:
            row = tk.Frame(match_frame, bg='#f0f0f0')
            row.pack(fill=tk.X, pady=2)
            tk.Radiobutton(row, text=label, variable=self.match_type, value=value,
                          font=('Segoe UI', 10), bg='#f0f0f0', activebackground='#f0f0f0',
                          cursor='hand2', width=30, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=('Segoe UI', 9), bg='#f0f0f0', fg='#888').pack(side=tk.LEFT)

        # === Files Section ===
        files_frame = tk.LabelFrame(main, text="Files", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=10)
        files_frame.pack(fill=tk.X, pady=(0, 10))

        # Source file/folder
        source_row = tk.Frame(files_frame, bg='#f0f0f0')
        source_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(source_row, text="Source:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.source_entry = tk.Entry(source_row, textvariable=self.source_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(source_row, text="Browse", command=self._browse_source,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # Target folder (optional)
        target_row = tk.Frame(files_frame, bg='#f0f0f0')
        target_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(target_row, text="Target:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)
        self.target_entry = tk.Entry(target_row, textvariable=self.target_path,
                                     font=('Segoe UI', 9), relief='solid', bd=1)
        self.target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
        tk.Button(target_row, text="Browse", command=self._browse_target,
                 font=('Segoe UI', 9), bg='#e0e0e0', relief='solid', bd=1,
                 padx=10, cursor='hand2').pack(side=tk.LEFT)

        # ToSubmit checkbox
        tosubmit_row = tk.Frame(files_frame, bg='#f0f0f0')
        tosubmit_row.pack(fill=tk.X, pady=(0, 8))
        tk.Checkbutton(tosubmit_row, text="ToSubmit Folder Integration",
                      variable=self.tosubmit_enabled, font=('Segoe UI', 10),
                      bg='#f0f0f0', activebackground='#f0f0f0', cursor='hand2').pack(side=tk.LEFT)

        # Branch selection
        branch_row = tk.Frame(files_frame, bg='#f0f0f0')
        branch_row.pack(fill=tk.X)
        tk.Label(branch_row, text="Branch:", font=('Segoe UI', 10), bg='#f0f0f0',
                width=8, anchor='w').pack(side=tk.LEFT)

        branch_names = list(config.BRANCHES.keys()) if hasattr(config, 'BRANCHES') else ["mainline", "cd_lambda"]

        source_combo = ttk.Combobox(branch_row, textvariable=self.selected_source_branch,
                                   values=branch_names, state='readonly', width=15)
        source_combo.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(branch_row, text="→", font=('Segoe UI', 12), bg='#f0f0f0').pack(side=tk.LEFT, padx=5)

        target_combo = ttk.Combobox(branch_row, textvariable=self.selected_target_branch,
                                   values=branch_names, state='readonly', width=15)
        target_combo.pack(side=tk.LEFT)

        # === Quick Actions Section ===
        quick_frame = tk.LabelFrame(main, text="Quick Actions", font=('Segoe UI', 10, 'bold'),
                                    bg='#f0f0f0', fg='#555', padx=15, pady=10)
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        # StringID Lookup
        stringid_row = tk.Frame(quick_frame, bg='#f0f0f0')
        stringid_row.pack(fill=tk.X, pady=(0, 8))
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
        reverse_row.pack(fill=tk.X)
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

        # === Progress Section ===
        progress_frame = tk.Frame(main, bg='#f0f0f0')
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_value,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        status_label = tk.Label(progress_frame, textvariable=self.status_text,
                               font=('Segoe UI', 9), bg='#f0f0f0', fg='#666', anchor='w')
        status_label.pack(fill=tk.X)

        # === Action Buttons ===
        button_frame = tk.Frame(main, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.generate_btn = tk.Button(button_frame, text="Generate", command=self._generate,
                                      font=('Segoe UI', 11, 'bold'), bg='#4a90d9', fg='white',
                                      relief='flat', padx=30, pady=8, cursor='hand2')
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Clear", command=self._clear_fields,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=20, pady=6, cursor='hand2').pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(button_frame, text="Exit", command=self.root.quit,
                 font=('Segoe UI', 10), bg='#e0e0e0', relief='solid', bd=1,
                 padx=20, pady=6, cursor='hand2').pack(side=tk.LEFT)

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

    def _browse_target(self):
        """Browse for target folder."""
        path = filedialog.askdirectory(title="Select Target Folder")
        if path:
            self.target_path.set(path)

    def _browse_reverse_file(self):
        """Browse for reverse lookup text file."""
        path = filedialog.askopenfilename(
            title="Select Text File with List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.reverse_file_path.set(path)

    def _update_status(self, text: str, progress: float = None):
        """Update status text and optionally progress bar."""
        self.status_text.set(text)
        if progress is not None:
            self.progress_value.set(progress)
        self.root.update()

    def _load_data_if_needed(self, need_sequencer: bool = True) -> bool:
        """Load data if not cached or branch changed."""
        branch = self.selected_source_branch.get()

        if self.cached_branch == branch and self.translation_lookup is not None:
            if not need_sequencer or self.strorigin_index is not None:
                return True

        if not hasattr(config, 'BRANCHES'):
            messagebox.showerror("Error", "BRANCHES not configured in config.py")
            return False

        paths = config.BRANCHES.get(branch)
        if not paths:
            messagebox.showerror("Error", f"Unknown branch: {branch}")
            return False

        loc_folder = paths["loc"]
        export_folder = paths["export"]
        sequencer_folder = export_folder / "Sequencer"

        if not loc_folder.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_folder}")
            return False

        if need_sequencer:
            if not sequencer_folder.exists():
                messagebox.showerror("Error", f"Sequencer folder not found:\n{sequencer_folder}")
                return False

            self.strorigin_index = build_sequencer_strorigin_index(
                sequencer_folder, self._update_status
            )

            if not self.strorigin_index:
                messagebox.showerror("Error", "No Sequencer data found.")
                return False

            # Also build category mapping for StringID-only mode
            self._update_status("Building category index...")
            self.stringid_to_category = build_stringid_to_category(export_folder, self._update_status)

        # Load language files
        lang_files = discover_language_files(loc_folder)
        if not lang_files:
            messagebox.showerror("Error", "No language files found.")
            return False

        self.translation_lookup = build_translation_lookup(lang_files, self._update_status)
        self.available_langs = list(lang_files.keys())
        self.cached_branch = branch

        return True

    def _clear_fields(self):
        """Clear all input fields."""
        self.source_path.set("")
        self.target_path.set("")
        self.string_id_input.set("")
        self.reverse_file_path.set("")
        self.progress_value.set(0)
        self.status_text.set("Ready")

    def _disable_buttons(self):
        """Disable all action buttons during processing."""
        self.generate_btn.config(state='disabled')

    def _enable_buttons(self):
        """Re-enable all action buttons."""
        self.generate_btn.config(state='normal')

    def _generate(self):
        """Main generate action based on current mode."""
        if not self.source_path.get():
            messagebox.showwarning("Warning", "Please select a source file or folder.")
            return

        source = Path(self.source_path.get())
        if not source.exists():
            messagebox.showerror("Error", f"Source not found:\n{source}")
            return

        self._disable_buttons()
        self.progress_value.set(0)

        try:
            # Load data
            if not self._load_data_if_needed(need_sequencer=True):
                return

            self.progress_value.set(20)

            # Read input based on format and mode
            corrections = []  # Initialize for all modes
            korean_inputs = []

            if self.format_mode.get() == "excel":
                korean_inputs = read_korean_input(source)
                # For non-substring modes, build corrections from Excel
                match_type = self.match_type.get()
                if match_type in ("stringid_only", "strict", "special_key"):
                    # Read structured data: assume col1=StringID, col2=StrOrigin, col3=Correction
                    corrections = read_corrections_from_excel(source)
                    if corrections:
                        korean_inputs = [c.get("str_origin", "") or c.get("string_id", "") for c in corrections]
            else:
                # XML format
                if self.input_mode.get() == "folder":
                    corrections = parse_folder_xml_files(source, self._update_status)
                else:
                    corrections = parse_corrections_from_xml(source)
                korean_inputs = [c.get("str_origin", "") for c in corrections if c.get("str_origin")]

            if not korean_inputs and not corrections:
                messagebox.showwarning("Warning", "No input data found.")
                return

            self.progress_value.set(40)

            # Find matches based on match type
            self._update_status("Finding matches...")
            match_type = self.match_type.get()
            matches_per_input = []
            total_matches = 0

            if match_type == "substring":
                # Original mode: substring search in StrOrigin
                for korean_text in korean_inputs:
                    matches = find_matches(korean_text, self.strorigin_index)
                    matches_per_input.append(matches)
                    total_matches += len(matches)

            elif match_type == "stringid_only":
                # StringID-only (SCRIPT): Filter to SCRIPT categories
                if not self.stringid_to_category:
                    messagebox.showwarning("Warning", "Category index not loaded. Re-select branch.")
                    return
                # For Excel: assume column 1 contains StringIDs
                # For XML: corrections already have string_id
                if self.format_mode.get() == "xml":
                    script_corrections, skipped = find_matches_stringid_only(
                        corrections, self.stringid_to_category
                    )
                    korean_inputs = [c.get("str_origin", "") for c in script_corrections]
                    for c in script_corrections:
                        matches_per_input.append([c.get("string_id")])
                        total_matches += 1
                    self._update_status(f"SCRIPT filter: {len(script_corrections)} kept, {skipped} skipped")
                else:
                    # Excel mode with StringID-only: treat input as StringIDs
                    for text in korean_inputs:
                        sid = text.strip()
                        category = self.stringid_to_category.get(sid, "")
                        if category in config.SCRIPT_CATEGORIES:
                            matches_per_input.append([sid])
                            total_matches += 1
                        else:
                            matches_per_input.append([])

            elif match_type == "strict":
                # Strict mode: Match by StringID + StrOrigin tuple
                if self.format_mode.get() != "xml":
                    messagebox.showwarning("Warning", "Strict mode requires XML input with StringID and StrOrigin.")
                    return
                # Build entries dict from target folder if specified
                target = self.target_path.get()
                if target:
                    from core.indexing import scan_folder_for_entries
                    xml_entries = scan_folder_for_entries(Path(target), self._update_status)
                    matched, not_found = find_matches_strict(corrections, xml_entries)
                    korean_inputs = [c.get("str_origin", "") for c in matched]
                    for c in matched:
                        matches_per_input.append([c.get("string_id")])
                        total_matches += 1
                    self._update_status(f"Strict match: {len(matched)} found, {not_found} not found")
                else:
                    messagebox.showwarning("Warning", "Strict mode requires a Target folder for matching.")
                    return

            elif match_type == "special_key":
                # Special key mode - not yet fully implemented
                messagebox.showinfo("Info", "Special Key mode: Using StringID as key for now.")
                for korean_text in korean_inputs:
                    matches = find_matches(korean_text, self.strorigin_index)
                    matches_per_input.append(matches)
                    total_matches += len(matches)

            else:
                # Fallback to substring
                for korean_text in korean_inputs:
                    matches = find_matches(korean_text, self.strorigin_index)
                    matches_per_input.append(matches)
                    total_matches += len(matches)

            self.progress_value.set(70)

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
                self.available_langs,
                config.LANGUAGE_NAMES,
            )

            self.progress_value.set(100)
            self._update_status(f"Done! {len(korean_inputs)} inputs, {total_matches} matches")
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Generation failed:\n{e}")
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
            messagebox.showinfo("Success", f"Output saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Lookup failed:\n{e}")
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

        try:
            if not self._load_data_if_needed(need_sequencer=False):
                return

            # Read input file
            self._update_status("Reading input file...")
            input_texts = read_text_file_lines(file_path)

            if not input_texts:
                messagebox.showwarning("Warning", "No text found in input file.")
                return

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
            messagebox.showinfo("Success",
                f"Output saved to:\n{output_path}\n\n"
                f"Found: {found_count}/{total_count}\n"
                f"Detected languages: {detected_str}")

        except Exception as e:
            messagebox.showerror("Error", f"Reverse lookup failed:\n{e}")
            self._update_status(f"Error: {e}")

        finally:
            self._enable_buttons()


def run_app():
    """Create and run the application."""
    root = tk.Tk()
    app = QuickTranslateApp(root)
    root.mainloop()
