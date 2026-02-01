"""
Result Panel Module

Displays search results in a Treeview with mode-specific columns:
- MAP: KOR, Translation, Description, Position (X,Y,Z), StrKey
- CHARACTER: KOR, Translation, UseMacro (race/gender), Age, Job
- ITEM: KOR, Translation, StrKey, StringID
- AUDIO: EventName, KOR Script, ENG Script

Features:
- Mode-specific column layouts using displaycolumns
- Tooltips for truncated text
- Cell selection and Ctrl+C copy
- Detail panel showing full entry information
"""

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Ensure parent directory is in sys.path for PyInstaller compatibility
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_ui_text
from core.search import SearchResult


# =============================================================================
# TOOLTIP CLASS
# =============================================================================

class ToolTip:
    """Tooltip popup for displaying truncated text."""

    def __init__(self, widget: tk.Widget):
        self.widget = widget
        self.tip_window: Optional[tk.Toplevel] = None
        self.text = ""

    def show(self, text: str, x: int, y: int) -> None:
        """Show tooltip at specified position."""
        if not text or self.tip_window:
            return

        self.text = text
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        # Create tooltip frame with border
        frame = ttk.Frame(self.tip_window, relief="solid", borderwidth=1)
        frame.pack()

        # Tooltip label with word wrap
        label = tk.Label(
            frame,
            text=text,
            justify="left",
            background="#ffffe0",  # Light yellow
            foreground="black",
            font=('TkDefaultFont', 9),
            wraplength=400,
            padx=5,
            pady=3
        )
        label.pack()

    def hide(self) -> None:
        """Hide the tooltip."""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
            self.text = ""


# =============================================================================
# ALL COLUMN DEFINITIONS (SUPERSET)
# =============================================================================

# All possible columns: (id, header_key, min_width, default_width)
ALL_COLUMN_DEFS = [
    ("name_kr", "name_kr", 80, 150),
    ("name_tr", "name_tr", 80, 150),
    ("desc", "description", 100, 200),
    ("position", "position", 80, 140),
    ("strkey", "strkey", 80, 150),
    ("use_macro", "use_macro", 80, 140),
    ("age", "age", 60, 80),
    ("job", "job", 80, 120),
    ("string_id", "string_id", 80, 100),
]

# Column ID to index mapping
COLUMN_ID_TO_INDEX = {col[0]: i for i, col in enumerate(ALL_COLUMN_DEFS)}


# =============================================================================
# MODE-SPECIFIC COLUMN CONFIGURATIONS
# =============================================================================

# Which columns to display per mode (uses displaycolumns)
MODE_DISPLAY_COLUMNS = {
    'map': ('name_kr', 'name_tr', 'desc', 'position', 'strkey'),
    'character': ('name_kr', 'name_tr', 'use_macro', 'age', 'job'),
    'item': ('name_kr', 'name_tr', 'strkey', 'string_id'),
    'audio': ('name_kr', 'desc', 'name_tr'),  # EventName, KOR Script, ENG Script
}

# Header overrides for specific modes
MODE_HEADER_OVERRIDES = {
    'audio': {
        'name_kr': 'event_name',
        'desc': 'script_line_kor',
        'name_tr': 'script_line_eng',
    },
}


class ResultPanel(ttk.Frame):
    """Panel displaying search results in a Treeview with mode-specific columns."""

    # Truncation threshold for tooltip display
    TRUNCATE_THRESHOLD = 80

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
        self._current_mode = "map"

        # Cache full text for tooltips (strkey -> {column -> full_text})
        self._full_text_cache: Dict[str, Dict[str, str]] = {}

        # Tooltip
        self._tooltip: Optional[ToolTip] = None
        self._tooltip_scheduled: Optional[str] = None

        # Cell selection state
        self._selected_cell: Optional[Tuple[str, str]] = None  # (strkey, col_id)

        # Detail panel collapsed state
        self._detail_collapsed = tk.BooleanVar(value=False)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Header frame with result count and selection info
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=2)

        self._count_label = ttk.Label(
            header_frame,
            text=get_ui_text('results') + ": 0"
        )
        self._count_label.pack(side="left")

        # Selection info label (shows copied cell info)
        self._selection_info_label = ttk.Label(
            header_frame,
            text="",
            foreground="gray"
        )
        self._selection_info_label.pack(side="right", padx=10)

        # Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Define ALL columns (superset)
        all_columns = tuple(col[0] for col in ALL_COLUMN_DEFS)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=all_columns,
            show="headings",
            selectmode="browse"
        )

        # Configure ALL columns with headers and widths
        for col_id, header_key, min_width, default_width in ALL_COLUMN_DEFS:
            self._tree.heading(
                col_id,
                text=get_ui_text(header_key),
                command=lambda c=col_id: self._sort_column(c)
            )
            self._tree.column(
                col_id,
                width=default_width,
                minwidth=min_width,
                stretch=True
            )

        # Apply initial mode columns
        self._apply_mode_columns('map')

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

        # Cell selection and copy bindings
        self._tree.bind("<Button-1>", self._on_cell_click)
        self._tree.bind("<Control-c>", self._copy_selected_cell)
        self._tree.bind("<Control-C>", self._copy_selected_cell)  # Caps lock

        # Tooltip bindings
        self._tooltip = ToolTip(self._tree)
        self._tree.bind("<Motion>", self._on_tree_motion)
        self._tree.bind("<Leave>", self._on_tree_leave)

        # Detail panel (collapsible)
        self._create_detail_panel()

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

    def _create_detail_panel(self) -> None:
        """Create collapsible detail panel below treeview."""
        # Detail panel frame
        self._detail_frame = ttk.LabelFrame(self, text="Details")
        self._detail_frame.pack(fill="x", padx=5, pady=(0, 5))

        # Toggle button
        toggle_btn = ttk.Checkbutton(
            self._detail_frame,
            text="Collapse",
            variable=self._detail_collapsed,
            command=self._toggle_detail_panel
        )
        toggle_btn.pack(anchor="e", padx=5, pady=2)

        # Detail content frame
        self._detail_content = ttk.Frame(self._detail_frame)
        self._detail_content.pack(fill="x", padx=5, pady=5)

        # Name row
        name_frame = ttk.Frame(self._detail_content)
        name_frame.pack(fill="x", pady=2)
        ttk.Label(name_frame, text="Name:", font=('TkDefaultFont', 9, 'bold'), width=12).pack(side="left")
        self._detail_name = ttk.Label(name_frame, text="", wraplength=350)
        self._detail_name.pack(side="left", fill="x", expand=True)

        # Description row
        desc_frame = ttk.Frame(self._detail_content)
        desc_frame.pack(fill="x", pady=2)
        ttk.Label(desc_frame, text="Description:", font=('TkDefaultFont', 9, 'bold'), width=12).pack(side="left", anchor="n")

        # Scrollable text for description
        desc_text_frame = ttk.Frame(desc_frame)
        desc_text_frame.pack(side="left", fill="x", expand=True)

        # Get background color from ttk Style (ttk widgets don't support cget("background"))
        style = ttk.Style()
        bg_color = style.lookup("TLabelframe", "background") or "#f0f0f0"

        self._detail_desc = tk.Text(
            desc_text_frame,
            height=3,
            width=40,
            wrap="word",
            font=('TkDefaultFont', 9),
            state="disabled",
            relief="flat",
            background=bg_color
        )
        self._detail_desc.pack(fill="x")

        # Position/Group row
        pos_frame = ttk.Frame(self._detail_content)
        pos_frame.pack(fill="x", pady=2)
        self._detail_pos_label = ttk.Label(pos_frame, text="Position:", font=('TkDefaultFont', 9, 'bold'), width=12)
        self._detail_pos_label.pack(side="left")
        self._detail_pos = ttk.Label(pos_frame, text="")
        self._detail_pos.pack(side="left")

        # StrKey row
        strkey_frame = ttk.Frame(self._detail_content)
        strkey_frame.pack(fill="x", pady=2)
        ttk.Label(strkey_frame, text="StrKey:", font=('TkDefaultFont', 9, 'bold'), width=12).pack(side="left")
        self._detail_strkey = ttk.Label(strkey_frame, text="", foreground="gray")
        self._detail_strkey.pack(side="left")

    def _toggle_detail_panel(self) -> None:
        """Toggle detail panel visibility."""
        if self._detail_collapsed.get():
            self._detail_content.pack_forget()
        else:
            self._detail_content.pack(fill="x", padx=5, pady=5)

    def _update_detail_panel(self, result: Optional[SearchResult]) -> None:
        """Update detail panel with selected result."""
        if not result:
            self._detail_name.config(text="")
            self._detail_desc.config(state="normal")
            self._detail_desc.delete("1.0", "end")
            self._detail_desc.config(state="disabled")
            self._detail_pos.config(text="")
            self._detail_strkey.config(text="")
            return

        if self._current_mode == "audio":
            # AUDIO mode: show event name, KOR script, ENG script
            self._detail_name.config(text=result.name_kr)  # Event name

            # Description shows KOR script
            self._detail_desc.config(state="normal")
            self._detail_desc.delete("1.0", "end")
            self._detail_desc.insert("1.0", result.desc_kr if result.desc_kr else "(No KOR script)")
            self._detail_desc.config(state="disabled")

            # Position shows ENG script
            self._detail_pos_label.config(text="ENG Script:")
            self._detail_pos.config(text=result.desc_translated if result.desc_translated else "(No ENG script)")

            # StrKey (same as event name for audio)
            self._detail_strkey.config(text=result.strkey)
        elif self._current_mode == "character":
            # CHARACTER mode: show name, race/gender, age, job
            name_text = result.name_kr
            if result.name_translated and result.name_translated != result.name_kr:
                name_text = f"{result.name_kr} / {result.name_translated}"
            self._detail_name.config(text=name_text)

            # Description shows formatted CHARACTER info
            char_info = []
            if result.use_macro:
                char_info.append(f"Race/Gender: {self._format_use_macro(result.use_macro)}")
            if result.age:
                char_info.append(f"Age: {result.age}")
            if result.job:
                char_info.append(f"Job: {self._format_job(result.job)}")

            self._detail_desc.config(state="normal")
            self._detail_desc.delete("1.0", "end")
            self._detail_desc.insert("1.0", "\n".join(char_info) if char_info else "(No character info)")
            self._detail_desc.config(state="disabled")

            # Position shows Group
            self._detail_pos_label.config(text="Group:")
            self._detail_pos.config(text=result.group)

            # StrKey
            self._detail_strkey.config(text=result.strkey)
        else:
            # MAP/ITEM modes: standard display
            name_text = result.name_kr
            if result.name_translated and result.name_translated != result.name_kr:
                name_text = f"{result.name_kr} / {result.name_translated}"
            self._detail_name.config(text=name_text)

            # Description
            desc_text = result.desc_translated if result.desc_translated else result.desc_kr
            self._detail_desc.config(state="normal")
            self._detail_desc.delete("1.0", "end")
            self._detail_desc.insert("1.0", desc_text)
            self._detail_desc.config(state="disabled")

            # Position or Group
            if self._current_mode == "map":
                self._detail_pos_label.config(text="Position:")
                self._detail_pos.config(text=result.position_str)
            else:
                self._detail_pos_label.config(text="Group:")
                self._detail_pos.config(text=result.group)

            # StrKey
            self._detail_strkey.config(text=result.strkey)

    # =========================================================================
    # MODE-SPECIFIC COLUMNS
    # =========================================================================

    def _apply_mode_columns(self, mode: str) -> None:
        """
        Apply mode-specific column layout using displaycolumns.

        Args:
            mode: 'map', 'character', 'item', or 'audio'
        """
        display_cols = MODE_DISPLAY_COLUMNS.get(mode, MODE_DISPLAY_COLUMNS['map'])
        self._tree.configure(displaycolumns=display_cols)

        # Apply header overrides if any
        overrides = MODE_HEADER_OVERRIDES.get(mode, {})
        for col_id, header_key in overrides.items():
            self._tree.heading(col_id, text=get_ui_text(header_key))

        # Reset non-overridden headers to defaults
        default_headers = {col[0]: col[1] for col in ALL_COLUMN_DEFS}
        for col_id in display_cols:
            if col_id not in overrides:
                self._tree.heading(col_id, text=get_ui_text(default_headers[col_id]))

    # =========================================================================
    # CELL SELECTION AND COPY
    # =========================================================================

    def _on_cell_click(self, event) -> None:
        """Handle click to select a cell."""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            self._selected_cell = None
            self._selection_info_label.config(text="")
            return

        item = self._tree.identify_row(event.y)
        column = self._tree.identify_column(event.x)
        if not item or not column:
            return

        # Get column ID from display column index
        # column is like "#1", "#2", etc. - index into displaycolumns
        col_display_idx = int(column[1:]) - 1
        display_cols = MODE_DISPLAY_COLUMNS.get(self._current_mode, MODE_DISPLAY_COLUMNS['map'])

        if col_display_idx < 0 or col_display_idx >= len(display_cols):
            return

        col_id = display_cols[col_display_idx]
        self._selected_cell = (item, col_id)

        # Update selection info
        full_text = self._full_text_cache.get(item, {}).get(col_id, "")
        if full_text:
            preview = full_text[:30] + "..." if len(full_text) > 30 else full_text
            self._selection_info_label.config(text=f"[Ctrl+C to copy: {preview}]")
        else:
            self._selection_info_label.config(text="")

    def _copy_selected_cell(self, event=None) -> str:
        """Copy selected cell value to clipboard."""
        if not self._selected_cell:
            return "break"

        strkey, col_id = self._selected_cell
        full_text = self._full_text_cache.get(strkey, {}).get(col_id, "")

        if full_text:
            self.clipboard_clear()
            self.clipboard_append(full_text)
            preview = full_text[:40] + "..." if len(full_text) > 40 else full_text
            self._selection_info_label.config(text=f"Copied: {preview}")
        else:
            self._selection_info_label.config(text="(Cell is empty)")

        return "break"

    # =========================================================================
    # DATA FORMATTING HELPERS
    # =========================================================================

    def _format_use_macro(self, use_macro: str) -> str:
        """Format UseMacro to readable race/gender.

        'Macro_NPC_Human_Male' -> 'Human Male'
        """
        if not use_macro:
            return ""
        parts = use_macro.replace("Macro_", "").replace("_", " ").split()
        filtered = [p for p in parts if p.lower() not in ('npc', 'unique')]
        return " ".join(filtered[:2])

    def _format_job(self, job: str) -> str:
        """Format Job to readable string.

        'Job_Scholar' -> 'Scholar'
        """
        return job.replace("Job_", "").replace("_", " ") if job else ""

    # =========================================================================
    # TOOLTIP HANDLING
    # =========================================================================

    def _on_tree_motion(self, event) -> None:
        """Handle mouse motion over tree - show tooltip for truncated text."""
        # Cancel any scheduled tooltip
        if self._tooltip_scheduled:
            self.after_cancel(self._tooltip_scheduled)
            self._tooltip_scheduled = None

        # Hide current tooltip
        if self._tooltip:
            self._tooltip.hide()

        # Identify what's under the mouse
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        # Get the item and column
        item = self._tree.identify_row(event.y)
        column = self._tree.identify_column(event.x)
        if not item or not column:
            return

        # Get column ID from display column index
        col_display_idx = int(column[1:]) - 1
        display_cols = MODE_DISPLAY_COLUMNS.get(self._current_mode, MODE_DISPLAY_COLUMNS['map'])

        if col_display_idx < 0 or col_display_idx >= len(display_cols):
            return

        col_id = display_cols[col_display_idx]

        # Check if this cell has cached full text that was truncated
        strkey = item
        if strkey in self._full_text_cache:
            full_text = self._full_text_cache[strkey].get(col_id)
            if full_text and len(full_text) > self.TRUNCATE_THRESHOLD:
                # Schedule tooltip display after short delay
                self._tooltip_scheduled = self.after(
                    500,  # 500ms delay
                    lambda: self._show_tooltip(full_text, event.x_root + 10, event.y_root + 10)
                )

    def _show_tooltip(self, text: str, x: int, y: int) -> None:
        """Show tooltip at position."""
        if self._tooltip:
            self._tooltip.show(text, x, y)

    def _on_tree_leave(self, event) -> None:
        """Handle mouse leaving tree - hide tooltip."""
        if self._tooltip_scheduled:
            self.after_cancel(self._tooltip_scheduled)
            self._tooltip_scheduled = None
        if self._tooltip:
            self._tooltip.hide()

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
            self._insert_result(result)

        # Update count label
        self._update_count_label()

        # Update load more button
        self._load_more_btn.config(state="normal" if has_more else "disabled")

    def _insert_result(self, result: SearchResult) -> None:
        """Insert a single result into the tree with ALL column values."""
        # Build full text cache for ALL columns (with None safety)
        self._full_text_cache[result.strkey] = {
            'name_kr': result.name_kr or "",
            'name_tr': result.name_translated or "",
            'desc': result.desc_translated or result.desc_kr or "",
            'position': result.position_str if self._current_mode == "map" else (result.group or ""),
            'strkey': result.strkey or "",
            'use_macro': self._format_use_macro(result.use_macro),
            'age': result.age or "",
            'job': self._format_job(result.job),
            'string_id': result.string_id or "",
        }

        # AUDIO mode overrides
        if self._current_mode == "audio":
            self._full_text_cache[result.strkey]['desc'] = result.desc_kr  # KOR script
            self._full_text_cache[result.strkey]['name_tr'] = result.desc_translated  # ENG script

        # Helper to truncate text (handles None and empty)
        def truncate(text: str) -> str:
            if not text:
                return ""
            if len(text) > self.TRUNCATE_THRESHOLD:
                return text[:self.TRUNCATE_THRESHOLD - 3] + "..."
            return text

        # Build values tuple for ALL columns (in order of ALL_COLUMN_DEFS)
        cache = self._full_text_cache[result.strkey]
        values = (
            truncate(cache['name_kr']),
            truncate(cache['name_tr']),
            truncate(cache['desc']),
            truncate(cache['position']),
            cache['strkey'],
            truncate(cache['use_macro']),
            cache['age'],
            truncate(cache['job']),
            cache['string_id'],
        )

        self._tree.insert(
            "",
            "end",
            iid=result.strkey,
            values=values
        )

    def _update_count_label(self) -> None:
        """Update the result count label."""
        if self._total_count > len(self._results):
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(self._results)} / {self._total_count}"
            )
        else:
            self._count_label.config(
                text=f"{get_ui_text('results')}: {len(self._results)}"
            )

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
            self._insert_result(result)

        self._update_count_label()
        self._load_more_btn.config(state="normal" if has_more else "disabled")

    def clear(self) -> None:
        """Clear all results."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._results = []
        self._total_count = 0
        self._has_more = False
        self._full_text_cache.clear()
        self._selected_cell = None
        self._selection_info_label.config(text="")
        self._count_label.config(text=f"{get_ui_text('results')}: 0")
        self._load_more_btn.config(state="disabled")
        self._update_detail_panel(None)

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
                    # Update detail panel
                    self._update_detail_panel(result)
                    break
        else:
            self._update_detail_panel(None)

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
        # Get column index in ALL_COLUMN_DEFS
        idx = COLUMN_ID_TO_INDEX.get(col, 0)

        # Get current items
        items = [(self._tree.item(iid)["values"], iid) for iid in self._tree.get_children()]

        # Sort
        items.sort(key=lambda x: str(x[0][idx]).lower() if x[0][idx] else "")

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
            mode: 'map', 'character', 'item', or 'audio'
        """
        self._current_mode = mode
        self._apply_mode_columns(mode)

        # Update detail panel label
        if hasattr(self, '_detail_pos_label'):
            if mode == 'map':
                self._detail_pos_label.config(text="Position:")
            elif mode == 'audio':
                self._detail_pos_label.config(text="ENG Script:")
            else:
                self._detail_pos_label.config(text="Group:")

    def set_mode(self, mode: str) -> None:
        """
        Set display mode and apply mode-specific column layout.

        Args:
            mode: 'map', 'character', 'item', or 'audio'
        """
        self._current_mode = mode
        self.set_mode_headers(mode)
        self.clear()  # Clear tree, cache, and selection state

    def set_column_visible(self, column: str, visible: bool) -> None:
        """
        Programmatically set column visibility.

        Note: This method is kept for backward compatibility but
        column visibility is now controlled by MODE_DISPLAY_COLUMNS.
        """
        pass  # No-op - columns are controlled by mode

    def get_column_visible(self, column: str) -> bool:
        """Get column visibility state based on current mode."""
        display_cols = MODE_DISPLAY_COLUMNS.get(self._current_mode, MODE_DISPLAY_COLUMNS['map'])
        return column in display_cols
