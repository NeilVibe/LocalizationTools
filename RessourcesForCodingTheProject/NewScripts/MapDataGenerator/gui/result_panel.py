"""
Result Panel Module

Displays search results in a Treeview with columns:
- Name (KR)
- Name (Translated)
- Description
- Position
- StrKey
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

try:
    from config import get_ui_text
    from core.search import SearchResult
except ImportError:
    from ..config import get_ui_text
    from ..core.search import SearchResult


class ResultPanel(ttk.Frame):
    """Panel displaying search results in a Treeview."""

    def __init__(
        self,
        parent: tk.Widget,
        on_select: Callable[[SearchResult], None],
        on_double_click: Callable[[SearchResult], None],
        **kwargs
    ):
        """
        Initialize result panel.

        Args:
            parent: Parent widget
            on_select: Callback when a result is selected
            on_double_click: Callback when a result is double-clicked
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._on_select = on_select
        self._on_double_click = on_double_click
        self._results: List[SearchResult] = []
        self._total_count = 0
        self._has_more = False

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Header frame with result count
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=2)

        self._count_label = ttk.Label(
            header_frame,
            text=get_ui_text('results') + ": 0"
        )
        self._count_label.pack(side="left")

        # Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Define columns (position/group share a column depending on mode)
        columns = ("name_kr", "name_tr", "desc", "pos_group", "strkey")

        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Configure columns
        self._tree.heading("name_kr", text=get_ui_text('name_kr'),
                          command=lambda: self._sort_column("name_kr"))
        self._tree.heading("name_tr", text=get_ui_text('name_tr'),
                          command=lambda: self._sort_column("name_tr"))
        self._tree.heading("desc", text=get_ui_text('description'),
                          command=lambda: self._sort_column("desc"))
        self._tree.heading("pos_group", text=get_ui_text('position'),
                          command=lambda: self._sort_column("pos_group"))
        self._tree.heading("strkey", text=get_ui_text('strkey'),
                          command=lambda: self._sort_column("strkey"))

        # Column widths
        self._tree.column("name_kr", width=150, minwidth=80)
        self._tree.column("name_tr", width=150, minwidth=80)
        self._tree.column("desc", width=200, minwidth=100)
        self._tree.column("pos_group", width=120, minwidth=60)
        self._tree.column("strkey", width=120, minwidth=80)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Grid layout for tree and scrollbars
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        # Bind events
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Double-1>", self._on_tree_double_click)

        # Load more button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=5, pady=2)

        self._load_more_btn = ttk.Button(
            btn_frame,
            text=get_ui_text('load_more'),
            command=self._request_more,
            state="disabled"
        )
        self._load_more_btn.pack(side="left")

        self._load_more_callback: Optional[Callable] = None

    def set_results(
        self,
        results: List[SearchResult],
        total_count: int = 0,
        has_more: bool = False
    ) -> None:
        """
        Set the displayed results.

        Args:
            results: List of SearchResult objects
            total_count: Total number of results (for display)
            has_more: Whether there are more results to load
        """
        self._results = results
        self._total_count = total_count if total_count else len(results)
        self._has_more = has_more

        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Add new items
        for result in results:
            desc_short = result.desc_translated if result.desc_translated else result.desc_kr
            if len(desc_short) > 50:
                desc_short = desc_short[:47] + "..."

            # Use position if available, otherwise group
            pos_or_group = result.position_str if result.position else result.group

            self._tree.insert(
                "",
                "end",
                iid=result.strkey,
                values=(
                    result.name_kr,
                    result.name_translated,
                    desc_short,
                    pos_or_group,
                    result.strkey
                )
            )

        # Update count label
        if self._total_count > len(results):
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(results)} / {self._total_count}"
            )
        else:
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(results)}"
            )

        # Update load more button
        self._load_more_btn.config(state="normal" if has_more else "disabled")

    def append_results(self, results: List[SearchResult], has_more: bool = False) -> None:
        """
        Append additional results.

        Args:
            results: Additional results to append
            has_more: Whether there are more results to load
        """
        self._results.extend(results)
        self._has_more = has_more

        for result in results:
            desc_short = result.desc_translated if result.desc_translated else result.desc_kr
            if len(desc_short) > 50:
                desc_short = desc_short[:47] + "..."

            # Use position if available, otherwise group
            pos_or_group = result.position_str if result.position else result.group

            self._tree.insert(
                "",
                "end",
                iid=result.strkey,
                values=(
                    result.name_kr,
                    result.name_translated,
                    desc_short,
                    pos_or_group,
                    result.strkey
                )
            )

        # Update count label
        if self._total_count > len(self._results):
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(self._results)} / {self._total_count}"
            )
        else:
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(self._results)}"
            )

        self._load_more_btn.config(state="normal" if has_more else "disabled")

    def clear(self) -> None:
        """Clear all results."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._results = []
        self._total_count = 0
        self._has_more = False
        self._count_label.config(text=f"{get_ui_text('results')}: 0")
        self._load_more_btn.config(state="disabled")

    def set_load_more_callback(self, callback: Callable) -> None:
        """Set callback for load more button."""
        self._load_more_callback = callback

    def _request_more(self) -> None:
        """Request more results."""
        if self._load_more_callback:
            self._load_more_callback()

    def _on_tree_select(self, event) -> None:
        """Handle tree selection."""
        selection = self._tree.selection()
        if selection:
            strkey = selection[0]
            for result in self._results:
                if result.strkey == strkey:
                    self._on_select(result)
                    break

    def _on_tree_double_click(self, event) -> None:
        """Handle tree double-click."""
        selection = self._tree.selection()
        if selection:
            strkey = selection[0]
            for result in self._results:
                if result.strkey == strkey:
                    self._on_double_click(result)
                    break

    def _sort_column(self, col: str) -> None:
        """Sort by column."""
        # Get column index
        col_map = {
            "name_kr": 0,
            "name_tr": 1,
            "desc": 2,
            "pos_group": 3,
            "strkey": 4
        }
        idx = col_map.get(col, 0)

        # Get current items
        items = [(self._tree.item(iid)["values"], iid) for iid in self._tree.get_children()]

        # Sort
        items.sort(key=lambda x: str(x[0][idx]).lower())

        # Reorder
        for i, (_, iid) in enumerate(items):
            self._tree.move(iid, "", i)

    def select_by_strkey(self, strkey: str) -> None:
        """Select a result by StrKey."""
        if self._tree.exists(strkey):
            self._tree.selection_set(strkey)
            self._tree.see(strkey)

    def get_selected(self) -> Optional[SearchResult]:
        """Get currently selected result."""
        selection = self._tree.selection()
        if selection:
            strkey = selection[0]
            for result in self._results:
                if result.strkey == strkey:
                    return result
        return None

    @property
    def result_count(self) -> int:
        """Get number of displayed results."""
        return len(self._results)

    def set_column_header(self, column: str, text: str) -> None:
        """
        Update a column header text.

        Args:
            column: Column identifier
            text: New header text
        """
        try:
            self._tree.heading(column, text=text)
        except tk.TclError:
            pass

    def set_mode_headers(self, mode: str) -> None:
        """
        Update column headers based on current mode.

        Args:
            mode: 'map', 'character', or 'item'
        """
        if mode == 'map':
            self._tree.heading("pos_group", text=get_ui_text('position'))
        else:
            self._tree.heading("pos_group", text=get_ui_text('group'))
