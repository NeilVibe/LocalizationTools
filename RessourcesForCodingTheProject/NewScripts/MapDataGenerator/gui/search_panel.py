"""
Search Panel Module

Provides the search interface with:
- Query input
- Match type selector (Contains, Exact, Fuzzy)
- Language dropdown
- Search button
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

try:
    from config import LANGUAGES, LANGUAGE_NAMES, get_ui_text, get_settings
except ImportError:
    from ..config import LANGUAGES, LANGUAGE_NAMES, get_ui_text, get_settings


class SearchPanel(ttk.Frame):
    """Search panel with query input and options."""

    def __init__(
        self,
        parent: tk.Widget,
        on_search: Callable[[str, str, str], None],
        on_language_change: Callable[[str], None],
        **kwargs
    ):
        """
        Initialize search panel.

        Args:
            parent: Parent widget
            on_search: Callback for search (query, match_type, language)
            on_language_change: Callback for language change
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._on_search = on_search
        self._on_language_change = on_language_change

        # Variables
        self._search_var = tk.StringVar()
        self._match_type_var = tk.StringVar(value="contains")
        self._language_var = tk.StringVar(value=get_settings().selected_language)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Row 1: Search entry + button
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=5, pady=5)

        # Search label
        ttk.Label(
            search_frame,
            text=get_ui_text('search') + ":"
        ).pack(side="left", padx=(0, 5))

        # Search entry
        self._search_entry = ttk.Entry(
            search_frame,
            textvariable=self._search_var,
            width=40,
            font=('Malgun Gothic', 11)
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self._search_entry.bind("<Return>", lambda e: self._do_search())

        # Search button
        self._search_btn = ttk.Button(
            search_frame,
            text=get_ui_text('search'),
            command=self._do_search,
            width=10
        )
        self._search_btn.pack(side="left", padx=5)

        # Clear button
        self._clear_btn = ttk.Button(
            search_frame,
            text="Clear",
            command=self._clear_search,
            width=8
        )
        self._clear_btn.pack(side="left")

        # Row 2: Options (match type + language)
        options_frame = ttk.Frame(self)
        options_frame.pack(fill="x", padx=5, pady=(0, 5))

        # Match type
        match_label = ttk.Label(options_frame, text="Match:")
        match_label.pack(side="left", padx=(0, 5))

        self._contains_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('contains'),
            variable=self._match_type_var,
            value="contains"
        )
        self._contains_radio.pack(side="left", padx=2)

        self._exact_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('exact'),
            variable=self._match_type_var,
            value="exact"
        )
        self._exact_radio.pack(side="left", padx=2)

        self._fuzzy_radio = ttk.Radiobutton(
            options_frame,
            text=get_ui_text('fuzzy'),
            variable=self._match_type_var,
            value="fuzzy"
        )
        self._fuzzy_radio.pack(side="left", padx=2)

        # Separator
        ttk.Separator(options_frame, orient="vertical").pack(
            side="left", fill="y", padx=15
        )

        # Language dropdown
        lang_label = ttk.Label(options_frame, text=get_ui_text('language') + ":")
        lang_label.pack(side="left", padx=(0, 5))

        # Build language display values
        lang_display = [f"{LANGUAGE_NAMES.get(code, code)} ({code})"
                        for code, _ in LANGUAGES if code != 'kor']
        self._lang_codes = [code for code, _ in LANGUAGES if code != 'kor']

        self._language_combo = ttk.Combobox(
            options_frame,
            values=lang_display,
            state="readonly",
            width=25
        )
        self._language_combo.pack(side="left", padx=5)

        # Set initial selection
        try:
            idx = self._lang_codes.index(self._language_var.get())
            self._language_combo.current(idx)
        except ValueError:
            self._language_combo.current(0)  # Default to first

        self._language_combo.bind("<<ComboboxSelected>>", self._on_language_selected)

    def _do_search(self) -> None:
        """Execute search."""
        query = self._search_var.get().strip()
        match_type = self._match_type_var.get()
        language = self._get_selected_language()

        self._on_search(query, match_type, language)

    def _clear_search(self) -> None:
        """Clear search field."""
        self._search_var.set("")
        self._search_entry.focus_set()

    def _get_selected_language(self) -> str:
        """Get currently selected language code."""
        idx = self._language_combo.current()
        if 0 <= idx < len(self._lang_codes):
            return self._lang_codes[idx]
        return "eng"

    def _on_language_selected(self, event=None) -> None:
        """Handle language selection change."""
        lang_code = self._get_selected_language()
        self._language_var.set(lang_code)
        self._on_language_change(lang_code)

    # Public API

    def set_search_text(self, text: str) -> None:
        """Set the search text."""
        self._search_var.set(text)

    def get_search_text(self) -> str:
        """Get the current search text."""
        return self._search_var.get()

    def get_match_type(self) -> str:
        """Get the current match type."""
        return self._match_type_var.get()

    def get_language(self) -> str:
        """Get the current language code."""
        return self._get_selected_language()

    def set_language(self, code: str) -> None:
        """Set the language selection."""
        try:
            idx = self._lang_codes.index(code)
            self._language_combo.current(idx)
            self._language_var.set(code)
        except ValueError:
            pass

    def focus_search(self) -> None:
        """Set focus to search entry."""
        self._search_entry.focus_set()

    def enable(self, enabled: bool = True) -> None:
        """Enable or disable the panel."""
        state = "normal" if enabled else "disabled"
        self._search_entry.config(state=state)
        self._search_btn.config(state=state)
        self._clear_btn.config(state=state)
        self._contains_radio.config(state=state)
        self._exact_radio.config(state=state)
        self._fuzzy_radio.config(state=state)
        self._language_combo.config(state="readonly" if enabled else "disabled")
