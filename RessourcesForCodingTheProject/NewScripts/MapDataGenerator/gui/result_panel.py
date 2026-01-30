"""
Result Panel Module

Displays search results in a Treeview with toggleable columns:
- Name (KR) - ON by default
- Name (Translated) - ON by default
- Description - OFF by default
- Position (X, Y, Z) - ON by default
- StrKey - ON by default

Features:
- Tooltips for truncated text
- Detail panel showing full entry information
- Mode-specific column defaults
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

try:
    from config import get_ui_text
    from core.search import SearchResult
except ImportError:
    from ..config import get_ui_text
    from ..core.search import SearchResult


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
# MODE COLUMN DEFAULTS
# =============================================================================

MODE_COLUMN_DEFAULTS: Dict[str, Dict[str, bool]] = {
    'map': {
        'name_kr': True,
        'name_tr': True,
        'desc': False,
        'position': True,
        'strkey': True,
    },
    'character': {
        'name_kr': True,
        'name_tr': True,
        'desc': False,
        'position': True,  # Shows Group in CHARACTER mode
        'strkey': True,
    },
    'item': {
        'name_kr': True,
        'name_tr': True,
        'desc': False,
        'position': True,  # Shows Group in ITEM mode
        'strkey': True,
    },
    'audio': {
        'name_kr': True,   # Event Name
        'name_tr': False,  # Hide - event name doesn't need translation
        'desc': True,      # KOR Script
        'position': True,  # ENG Script (repurposed column)
        'strkey': False,   # Hide - same as event name
    },
}

# Column header overrides for AUDIO mode
AUDIO_COLUMN_HEADERS = {
    'name_kr': 'event_name',      # "Event Name"
    'desc': 'script_line',        # "Script Line" (KOR)
    'position': 'name_tr',        # "Name (Translated)" - repurposed for ENG script
}


class ResultPanel(ttk.Frame):
    """Panel displaying search results in a Treeview with toggleable columns."""

    # Column definitions: (id, header_key, default_visible, min_width, default_width)
    COLUMN_DEFS = [
        ("name_kr", "name_kr", True, 80, 150),
        ("name_tr", "name_tr", True, 80, 150),
        ("desc", "description", False, 100, 200),  # OFF by default
        ("position", "position", True, 80, 140),
        ("strkey", "strkey", True, 80, 150),
    ]

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

        # Column visibility state
        self._column_visible = {}
        for col_id, _, default_visible, _, _ in self.COLUMN_DEFS:
            self._column_visible[col_id] = tk.BooleanVar(value=default_visible)

        # Cache full text for tooltips (strkey -> {column -> full_text})
        self._full_text_cache: Dict[str, Dict[str, str]] = {}

        # Tooltip
        self._tooltip: Optional[ToolTip] = None
        self._tooltip_scheduled: Optional[str] = None

        # Detail panel collapsed state
        self._detail_collapsed = tk.BooleanVar(value=False)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create panel widgets."""
        # Header frame with result count and column toggles
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=2)

        self._count_label = ttk.Label(
            header_frame,
            text=get_ui_text('results') + ": 0"
        )
        self._count_label.pack(side="left")

        # Column toggle frame
        toggle_frame = ttk.Frame(header_frame)
        toggle_frame.pack(side="right")

        ttk.Label(toggle_frame, text="Show:").pack(side="left", padx=(0, 5))

        self._column_checkboxes = {}
        for col_id, header_key, _, _, _ in self.COLUMN_DEFS:
            cb = ttk.Checkbutton(
                toggle_frame,
                text=get_ui_text(header_key),
                variable=self._column_visible[col_id],
                command=self._update_column_visibility
            )
            cb.pack(side="left", padx=2)
            self._column_checkboxes[col_id] = cb

        # Treeview with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Define all columns
        all_columns = tuple(col[0] for col in self.COLUMN_DEFS)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=all_columns,
            show="headings",
            selectmode="browse"
        )

        # Configure columns
        for col_id, header_key, default_visible, min_width, default_width in self.COLUMN_DEFS:
            self._tree.heading(
                col_id,
                text=get_ui_text(header_key),
                command=lambda c=col_id: self._sort_column(c)
            )
            self._tree.column(
                col_id,
                width=default_width if default_visible else 0,
                minwidth=min_width if default_visible else 0,
                stretch=True
            )

        # Apply initial visibility
        self._update_column_visibility()

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

        self._detail_desc = tk.Text(
            desc_text_frame,
            height=3,
            width=40,
            wrap="word",
            font=('TkDefaultFont', 9),
            state="disabled",
            relief="flat",
            background=self._detail_frame.cget("background") if hasattr(self._detail_frame, "cget") else "#f0f0f0"
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
        else:
            # Other modes: standard display
            # Name (KR + translated)
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

        # Get column index (column is like "#1", "#2", etc.)
        col_idx = int(column[1:]) - 1
        if col_idx < 0 or col_idx >= len(self.COLUMN_DEFS):
            return

        col_id = self.COLUMN_DEFS[col_idx][0]

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

    def _update_column_visibility(self) -> None:
        """Update column visibility based on checkboxes."""
        for col_id, _, _, min_width, default_width in self.COLUMN_DEFS:
            if self._column_visible[col_id].get():
                self._tree.column(col_id, width=default_width, minwidth=min_width, stretch=True)
            else:
                self._tree.column(col_id, width=0, minwidth=0, stretch=False)

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
        """Insert a single result into the tree."""
        # Cache full text for tooltips before truncation
        desc_full = result.desc_translated if result.desc_translated else result.desc_kr

        # Store full text cache
        self._full_text_cache[result.strkey] = {
            'name_kr': result.name_kr,
            'name_tr': result.name_translated,
            'desc': desc_full,
            'position': result.position_str if self._current_mode == "map" else result.group,
            'strkey': result.strkey
        }

        # Description: truncate if too long
        desc_display = desc_full
        if len(desc_display) > self.TRUNCATE_THRESHOLD:
            desc_display = desc_display[:self.TRUNCATE_THRESHOLD - 3] + "..."

        # Truncate name if too long
        name_kr_display = result.name_kr
        if len(name_kr_display) > self.TRUNCATE_THRESHOLD:
            name_kr_display = name_kr_display[:self.TRUNCATE_THRESHOLD - 3] + "..."

        name_tr_display = result.name_translated
        if len(name_tr_display) > self.TRUNCATE_THRESHOLD:
            name_tr_display = name_tr_display[:self.TRUNCATE_THRESHOLD - 3] + "..."

        # Position column: varies by mode
        # - MAP: Position (X, Y, Z)
        # - CHARACTER/ITEM: Group
        # - AUDIO: ENG Script (desc_translated)
        if self._current_mode == "map":
            pos_or_group = result.position_str  # Full X, Y, Z
        elif self._current_mode == "audio":
            # AUDIO mode: show ENG script in position column
            eng_script = result.desc_translated if result.desc_translated else ""
            if len(eng_script) > self.TRUNCATE_THRESHOLD:
                pos_or_group = eng_script[:self.TRUNCATE_THRESHOLD - 3] + "..."
            else:
                pos_or_group = eng_script
            # Also cache full ENG script for tooltip
            self._full_text_cache[result.strkey]['position'] = eng_script
        else:
            pos_or_group = result.group

        self._tree.insert(
            "",
            "end",
            iid=result.strkey,
            values=(
                name_kr_display,
                name_tr_display,
                desc_display,
                pos_or_group,
                result.strkey
            )
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
        # Get column index
        col_map = {col[0]: i for i, col in enumerate(self.COLUMN_DEFS)}
        idx = col_map.get(col, 0)

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

        if mode == 'audio':
            # AUDIO mode: special column headers
            self._tree.heading("name_kr", text=get_ui_text('event_name'))
            self._tree.heading("desc", text=get_ui_text('script_line') + " (KOR)")
            self._tree.heading("position", text=get_ui_text('script_line') + " (ENG)")
        elif mode == 'map':
            # MAP mode: default headers
            self._tree.heading("name_kr", text=get_ui_text('name_kr'))
            self._tree.heading("desc", text=get_ui_text('description'))
            self._tree.heading("position", text=get_ui_text('position'))
        else:
            # CHARACTER/ITEM mode
            self._tree.heading("name_kr", text=get_ui_text('name_kr'))
            self._tree.heading("desc", text=get_ui_text('description'))
            self._tree.heading("position", text=get_ui_text('group'))

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
        Set display mode and apply mode-specific column defaults.

        Args:
            mode: 'map', 'character', 'item', or 'audio'
        """
        self._current_mode = mode
        self.set_mode_headers(mode)

        # Apply mode-specific column defaults
        defaults = MODE_COLUMN_DEFAULTS.get(mode, MODE_COLUMN_DEFAULTS['map'])
        for col_id, visible in defaults.items():
            if col_id in self._column_visible:
                self._column_visible[col_id].set(visible)

        self._update_column_visibility()

    def set_column_visible(self, column: str, visible: bool) -> None:
        """
        Programmatically set column visibility.

        Args:
            column: Column identifier
            visible: Whether column should be visible
        """
        if column in self._column_visible:
            self._column_visible[column].set(visible)
            self._update_column_visibility()

    def get_column_visible(self, column: str) -> bool:
        """Get column visibility state."""
        if column in self._column_visible:
            return self._column_visible[column].get()
        return False
