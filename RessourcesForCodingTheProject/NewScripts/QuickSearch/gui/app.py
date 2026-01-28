"""
Main GUI Application

QuickSearch main window with tabs for Search and Glossary Checker.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional

from ..config import (
    APP_NAME, VERSION, GAMES, LANGUAGES,
    get_settings, save_settings, load_settings,
    get_ui_text, UI_LANGUAGES
)
from ..core.dictionary import DictionaryManager, create_dictionary, save_dictionary
from ..core.search import search_one_line, search_multi_line, SearchResult
from ..core.glossary import extract_glossary_with_validation, save_glossary
from .dialogs import LineCheckDialog, TermCheckDialog, center_dialog


class QuickSearchApp:
    """Main QuickSearch application."""

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("900x700")

        # Initialize
        self.settings = load_settings()
        self.dict_manager = DictionaryManager()
        self.dict_manager.scan_dictionaries()

        # UI State
        self.reference_active = False
        self.search_results = []
        self.current_index = 0

        # Variables
        self.progress_var = tk.StringVar(value="Ready")
        self.search_var = tk.StringVar()
        self.match_type_var = tk.StringVar(value="contains")
        self.search_mode_var = tk.StringVar(value="one_line")

        self._create_widgets()
        self._apply_settings()

    def _create_widgets(self) -> None:
        """Create main window widgets."""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Quick Search
        self.search_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.search_tab, text="Quick Search")
        self._create_search_tab()

        # Tab 2: Glossary Checker
        self.glossary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.glossary_tab, text="Glossary Checker")
        self._create_glossary_tab()

        # Status bar
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(status_frame, textvariable=self.progress_var, anchor="w")
        self.status_label.pack(fill="x", padx=5, pady=2)

    def _create_search_tab(self) -> None:
        """Create Quick Search tab."""
        # Button frame
        btn_frame = tk.Frame(self.search_tab)
        btn_frame.pack(fill="x", padx=5, pady=5)

        self.create_btn = tk.Button(
            btn_frame,
            text=get_ui_text('create_dict'),
            command=self._create_dictionary
        )
        self.create_btn.pack(side="left", padx=2)

        self.load_btn = tk.Button(
            btn_frame,
            text=get_ui_text('load_dict'),
            command=self._load_dictionary
        )
        self.load_btn.pack(side="left", padx=2)

        self.reference_btn = tk.Button(
            btn_frame,
            text=get_ui_text('reference_off'),
            command=self._toggle_reference
        )
        self.reference_btn.pack(side="left", padx=2)

        self.settings_btn = tk.Button(
            btn_frame,
            text=get_ui_text('settings'),
            command=self._open_settings
        )
        self.settings_btn.pack(side="right", padx=2)

        # Search frame
        search_frame = tk.Frame(self.search_tab)
        search_frame.pack(fill="x", padx=5, pady=5)

        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 12))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=2)
        self.search_entry.bind("<Return>", lambda e: self._search())

        self.search_btn = tk.Button(
            search_frame,
            text=get_ui_text('search'),
            command=self._search
        )
        self.search_btn.pack(side="left", padx=2)

        # Options frame
        options_frame = tk.Frame(self.search_tab)
        options_frame.pack(fill="x", padx=5)

        self.contains_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('contains'),
            variable=self.match_type_var,
            value="contains"
        )
        self.contains_radio.pack(side="left", padx=5)

        self.exact_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('exact_match'),
            variable=self.match_type_var,
            value="exact"
        )
        self.exact_radio.pack(side="left", padx=5)

        ttk.Separator(options_frame, orient="vertical").pack(side="left", fill="y", padx=10)

        self.one_line_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('one_line'),
            variable=self.search_mode_var,
            value="one_line"
        )
        self.one_line_radio.pack(side="left", padx=5)

        self.multi_line_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('multi_line'),
            variable=self.search_mode_var,
            value="multi_line"
        )
        self.multi_line_radio.pack(side="left", padx=5)

        # Results frame
        results_frame = tk.Frame(self.search_tab)
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.result_text = tk.Text(
            results_frame,
            wrap="word",
            font=(self.settings.font_family, self.settings.font_size)
        )
        self.result_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(results_frame, command=self.result_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.result_text.config(yscrollcommand=scrollbar.set)

        # Load more button
        self.load_more_btn = tk.Button(
            self.search_tab,
            text=get_ui_text('load_more'),
            command=self._load_more_results,
            state=tk.DISABLED
        )
        self.load_more_btn.pack(pady=5)

    def _create_glossary_tab(self) -> None:
        """Create Glossary Checker tab."""
        # Progress display
        progress_frame = tk.Frame(self.glossary_tab)
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.glossary_progress_label = tk.Label(
            progress_frame,
            textvariable=self.progress_var,
            anchor="w"
        )
        self.glossary_progress_label.pack(fill="x")

        # Buttons frame
        btn_frame = tk.Frame(self.glossary_tab)
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.extract_glossary_btn = tk.Button(
            btn_frame,
            text="Extract Glossary",
            command=self._extract_glossary,
            width=20,
            height=2
        )
        self.extract_glossary_btn.pack(side="left", padx=10)

        self.line_check_btn = tk.Button(
            btn_frame,
            text="LINE CHECK",
            command=self._line_check,
            width=20,
            height=2
        )
        self.line_check_btn.pack(side="left", padx=10)

        self.term_check_btn = tk.Button(
            btn_frame,
            text="TERM CHECK",
            command=self._term_check,
            width=20,
            height=2
        )
        self.term_check_btn.pack(side="left", padx=10)

        # Options frame
        options_frame = ttk.LabelFrame(self.glossary_tab, text="Filter Options")
        options_frame.pack(fill="x", padx=10, pady=10)

        self.filter_sentences_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Filter sentences (entries ending with . ? !)",
            variable=self.filter_sentences_var
        ).pack(anchor="w", padx=5, pady=2)

        length_row = tk.Frame(options_frame)
        length_row.pack(anchor="w", padx=5, pady=2)
        tk.Label(length_row, text="Max source length:").pack(side=tk.LEFT)
        self.length_threshold_var = tk.IntVar(value=15)
        tk.Spinbox(
            length_row,
            from_=5, to=50,
            textvariable=self.length_threshold_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)

        occurrence_row = tk.Frame(options_frame)
        occurrence_row.pack(anchor="w", padx=5, pady=2)
        tk.Label(occurrence_row, text="Min occurrences:").pack(side=tk.LEFT)
        self.min_occurrence_var = tk.IntVar(value=2)
        tk.Spinbox(
            occurrence_row,
            from_=1, to=10,
            textvariable=self.min_occurrence_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)

        # Sort method
        sort_row = tk.Frame(options_frame)
        sort_row.pack(anchor="w", padx=5, pady=2)
        tk.Label(sort_row, text="Sort by:").pack(side=tk.LEFT)
        self.sort_method_var = tk.StringVar(value="alphabetical")
        sort_combo = ttk.Combobox(
            sort_row,
            textvariable=self.sort_method_var,
            values=["alphabetical", "length", "frequency"],
            state="readonly",
            width=15
        )
        sort_combo.pack(side=tk.LEFT, padx=5)

        # Info text
        info_frame = tk.Frame(self.glossary_tab)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        info_text = tk.Text(info_frame, height=10, wrap="word")
        info_text.pack(fill="both", expand=True)
        info_text.insert("1.0", """QuickSearch Glossary Checker

Features:
- Extract Glossary: Creates a glossary from XML/TXT files
- LINE CHECK: Finds inconsistent translations (same source, different translations)
- TERM CHECK: Finds missing term translations using Aho-Corasick

New in this version:
- ENG BASE / KR BASE selection for LINE and TERM CHECK
  - KR BASE: Uses Korean StrOrigin as source (default)
  - ENG BASE: Uses English text matched via StringID
- Clean output (no filenames in reports)
- Modular architecture for better maintainability

Select source files and configure options before running checks.
""")
        info_text.config(state=tk.DISABLED)

    def _apply_settings(self) -> None:
        """Apply current settings to UI."""
        font = (self.settings.font_family, self.settings.font_size)
        self.result_text.config(font=font)

    def _create_dictionary(self) -> None:
        """Create a new dictionary."""
        files = filedialog.askopenfilenames(
            title="Select Source Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("All Files", "*.*")
            ]
        )
        if not files:
            return

        # Ask for game and language
        dialog = tk.Toplevel(self.root)
        dialog.title("Dictionary Info")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        game_var = tk.StringVar()
        lang_var = tk.StringVar()

        tk.Label(dialog, text="Game:").pack(pady=5)
        game_combo = ttk.Combobox(dialog, textvariable=game_var, values=GAMES, state="readonly")
        game_combo.pack(pady=5)

        tk.Label(dialog, text="Language:").pack(pady=5)
        lang_combo = ttk.Combobox(dialog, textvariable=lang_var, values=LANGUAGES, state="readonly")
        lang_combo.pack(pady=5)

        def on_create():
            game = game_var.get()
            lang = lang_var.get()
            if not game or not lang:
                messagebox.showwarning("Warning", "Please select game and language")
                return

            dialog.destroy()

            def task():
                def progress_callback(msg: str):
                    self.progress_var.set(msg)
                    self.root.update_idletasks()

                dictionary = create_dictionary(
                    list(files), game, lang, progress_callback
                )

                if dictionary:
                    if save_dictionary(dictionary):
                        self.dict_manager.scan_dictionaries()
                        self.progress_var.set(f"Dictionary created: {game}-{lang}")
                        messagebox.showinfo("Success", f"Dictionary {game}-{lang} created successfully!")
                    else:
                        self.progress_var.set("Error saving dictionary")
                else:
                    self.progress_var.set("Error creating dictionary")

            threading.Thread(target=task, daemon=True).start()

        tk.Button(dialog, text="Create", command=on_create).pack(pady=10)

    def _load_dictionary(self) -> None:
        """Load an existing dictionary."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Dictionary")
        dialog.geometry("300x400")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        game_var = tk.StringVar()
        lang_var = tk.StringVar()

        game_frame = ttk.LabelFrame(dialog, text="Select Game")
        game_frame.pack(padx=10, pady=5, fill="x")

        lang_frame = ttk.LabelFrame(dialog, text="Select Language")
        lang_frame.pack(padx=10, pady=5, fill="x")

        def update_languages(*args):
            for widget in lang_frame.winfo_children():
                widget.destroy()
            game = game_var.get()
            for lang in self.dict_manager.get_available(game):
                ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")

        for game in self.dict_manager.dictionaries:
            if self.dict_manager.dictionaries[game]:
                ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")

        game_var.trace('w', update_languages)

        def on_load():
            game = game_var.get()
            lang = lang_var.get()
            if not game or not lang:
                messagebox.showwarning("Warning", "Please select game and language")
                return

            if self.dict_manager.set_active(game, lang):
                self.load_btn.config(text=f"LOADED: {game}-{lang}")
                self.progress_var.set(f"Dictionary loaded: {game}-{lang}")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to load dictionary")

        tk.Button(dialog, text="Load", command=on_load).pack(pady=10)

    def _toggle_reference(self) -> None:
        """Toggle reference dictionary."""
        if self.reference_active:
            self.reference_active = False
            self.dict_manager.clear_reference()
            self.reference_btn.config(text=get_ui_text('reference_off'))
        else:
            # Show reference selection dialog (similar to load)
            dialog = tk.Toplevel(self.root)
            dialog.title("Select Reference Dictionary")
            dialog.geometry("300x400")
            dialog.transient(self.root)
            dialog.grab_set()
            center_dialog(dialog, self.root)

            game_var = tk.StringVar()
            lang_var = tk.StringVar()

            game_frame = ttk.LabelFrame(dialog, text="Select Game")
            game_frame.pack(padx=10, pady=5, fill="x")

            lang_frame = ttk.LabelFrame(dialog, text="Select Language")
            lang_frame.pack(padx=10, pady=5, fill="x")

            def update_languages(*args):
                for widget in lang_frame.winfo_children():
                    widget.destroy()
                game = game_var.get()
                for lang in self.dict_manager.get_available(game):
                    ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")

            for game in self.dict_manager.dictionaries:
                if self.dict_manager.dictionaries[game]:
                    ttk.Radiobutton(game_frame, text=game, variable=game_var, value=game).pack(anchor="w")

            game_var.trace('w', update_languages)

            def on_select():
                game = game_var.get()
                lang = lang_var.get()
                if not game or not lang:
                    messagebox.showwarning("Warning", "Please select game and language")
                    return

                if self.dict_manager.set_reference(game, lang):
                    self.reference_active = True
                    self.reference_btn.config(text=f"REF: {game}-{lang}")
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Failed to load reference dictionary")

            tk.Button(dialog, text="Select", command=on_select).pack(pady=10)

    def _search(self) -> None:
        """Perform search."""
        dictionary = self.dict_manager.get_active()
        if not dictionary:
            messagebox.showwarning("Warning", "Please load a dictionary first")
            return

        query = self.search_var.get()
        if not query:
            return

        reference_dict = self.dict_manager.get_reference() if self.reference_active else None

        if self.search_mode_var.get() == "one_line":
            results = search_one_line(
                query,
                dictionary,
                self.match_type_var.get(),
                reference_dict
            )
        else:
            results = search_multi_line(
                query,
                dictionary,
                self.match_type_var.get(),
                reference_dict
            )

        self.search_results = results
        self.current_index = len(results)
        self._display_results(results)

        if len(results) >= 50:
            self.load_more_btn.config(state=tk.NORMAL)
        else:
            self.load_more_btn.config(state=tk.DISABLED)

    def _load_more_results(self) -> None:
        """Load more search results."""
        dictionary = self.dict_manager.get_active()
        if not dictionary:
            return

        query = self.search_var.get()
        reference_dict = self.dict_manager.get_reference() if self.reference_active else None

        more_results = search_one_line(
            query,
            dictionary,
            self.match_type_var.get(),
            reference_dict,
            start_index=self.current_index
        )

        if more_results:
            self.search_results.extend(more_results)
            self.current_index += len(more_results)
            self._display_results(self.search_results)

        if len(more_results) < 50:
            self.load_more_btn.config(state=tk.DISABLED)

    def _display_results(self, results: list) -> None:
        """Display search results."""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)

        for i, result in enumerate(results):
            # Korean
            self.result_text.insert(tk.END, result.korean + "\n", f"korean_{i}")
            # Translation
            self.result_text.insert(tk.END, result.translation + "\n", f"translation_{i}")
            # Reference (if active)
            if self.reference_active and result.reference:
                self.result_text.insert(tk.END, result.reference + "\n", f"reference_{i}")
            self.result_text.insert(tk.END, "\n")

        # Apply colors
        for i in range(len(results)):
            self.result_text.tag_config(
                f"korean_{i}",
                foreground=self.settings.colors.get('korean', '#000000')
            )
            self.result_text.tag_config(
                f"translation_{i}",
                foreground=self.settings.colors.get('translation', '#000000')
            )
            self.result_text.tag_config(
                f"reference_{i}",
                foreground=self.settings.colors.get('reference', '#000000')
            )

        self.progress_var.set(f"Found {len(results)} results")

    def _extract_glossary(self) -> None:
        """Extract glossary from files."""
        files = filedialog.askopenfilenames(
            title="Select Source Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("All Files", "*.*")
            ]
        )
        if not files:
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Glossary As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not output_path:
            return

        def task():
            def progress_callback(msg: str):
                self.progress_var.set(msg)
                self.root.update_idletasks()

            glossary = extract_glossary_with_validation(
                list(files),
                length_threshold=self.length_threshold_var.get(),
                filter_sentences=self.filter_sentences_var.get(),
                min_occurrence=self.min_occurrence_var.get(),
                sort_method=self.sort_method_var.get(),
                progress_callback=progress_callback
            )

            if save_glossary(glossary, output_path):
                self.progress_var.set(f"Glossary saved: {len(glossary)} terms")
                messagebox.showinfo("Done", f"Glossary saved to:\n{output_path}")
            else:
                self.progress_var.set("Error saving glossary")

        threading.Thread(target=task, daemon=True).start()

    def _line_check(self) -> None:
        """Open LINE CHECK dialog."""
        LineCheckDialog(self.root, self.progress_var)

    def _term_check(self) -> None:
        """Open TERM CHECK dialog."""
        TermCheckDialog(self.root, self.progress_var)

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title(get_ui_text('settings_title'))
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        # Language selection
        lang_frame = ttk.LabelFrame(dialog, text=get_ui_text('language_select'))
        lang_frame.pack(padx=10, pady=5, fill="x")

        lang_var = tk.StringVar(value=self.settings.ui_language)
        for lang in UI_LANGUAGES:
            ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w")

        # Font settings
        font_frame = ttk.LabelFrame(dialog, text="Font Settings")
        font_frame.pack(padx=10, pady=5, fill="x")

        font_row = tk.Frame(font_frame)
        font_row.pack(pady=5)
        tk.Label(font_row, text="Font:").pack(side=tk.LEFT)
        font_var = tk.StringVar(value=self.settings.font_family)
        font_entry = tk.Entry(font_row, textvariable=font_var, width=20)
        font_entry.pack(side=tk.LEFT, padx=5)

        size_row = tk.Frame(font_frame)
        size_row.pack(pady=5)
        tk.Label(size_row, text="Size:").pack(side=tk.LEFT)
        size_var = tk.IntVar(value=self.settings.font_size)
        tk.Spinbox(size_row, from_=8, to=24, textvariable=size_var, width=5).pack(side=tk.LEFT, padx=5)

        def on_save():
            self.settings.ui_language = lang_var.get()
            self.settings.font_family = font_var.get()
            self.settings.font_size = size_var.get()
            save_settings(self.settings)
            self._apply_settings()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=on_save).pack(pady=10)

    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()
