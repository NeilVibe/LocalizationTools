"""
Export Tree Panel - Category browser for AUDIO mode.

Displays the export folder hierarchy as a collapsible tree.
Each node shows a count badge. Selecting a node filters the result grid
to show entries from that category in their original XML element order.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

log = logging.getLogger(__name__)

# Auto-expand depth: first N levels open by default
_AUTO_EXPAND_DEPTH = 2


class ExportTreePanel(ttk.LabelFrame):
    """Treeview-based category browser for audio export paths."""

    def __init__(
        self,
        parent: tk.Widget,
        on_category_select: Optional[Callable[[str], None]] = None,
        label_text: str = "Export Categories",
        all_audio_text: str = "All Audio",
        **kwargs,
    ):
        super().__init__(parent, text=label_text, **kwargs)
        self._on_category_select = on_category_select
        self._all_audio_text = all_audio_text
        self._node_to_path: Dict[str, str] = {}  # tree item id -> path prefix

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Build treeview with vertical + horizontal scrollbars."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Grid layout for dual scrollbars
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            frame, show="tree", height=14, selectmode="browse"
        )
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # Selection callback
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Right-click context menu
        self._context_menu = tk.Menu(self._tree, tearoff=0)
        self._context_menu.add_command(label="Expand All", command=self._expand_all)
        self._context_menu.add_command(label="Collapse All", command=self._collapse_all)
        self._tree.bind("<Button-3>", self._on_right_click)

    def _on_right_click(self, event) -> None:
        """Show context menu on right-click."""
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _expand_all(self) -> None:
        """Expand all tree nodes."""
        for item in self._get_all_items():
            self._tree.item(item, open=True)

    def _collapse_all(self) -> None:
        """Collapse all tree nodes except root."""
        children = self._tree.get_children()
        if not children:
            return
        root_id = children[0]
        for item in self._get_all_items():
            if item != root_id:
                self._tree.item(item, open=False)
        # Keep root open
        self._tree.item(root_id, open=True)

    def _get_all_items(self):
        """Yield all tree item IDs recursively."""
        def recurse(parent):
            for child in self._tree.get_children(parent):
                yield child
                yield from recurse(child)
        yield from recurse("")

    def _on_select(self, _event=None) -> None:
        """Handle tree node selection."""
        sel = self._tree.selection()
        if not sel:
            return
        item_id = sel[0]
        path = self._node_to_path.get(item_id, "")

        if self._on_category_select:
            self._on_category_select(path)

    def set_tree_data(self, tree_dict: Dict, total: int) -> None:
        """Populate treeview from category tree dict.

        Args:
            tree_dict: Nested dict from AudioIndex.build_category_tree()
                       {"_count": N, "children": {"name": {...}, ...}}
            total: Total audio entry count (for root label)
        """
        # Safe clear
        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)
        self._node_to_path.clear()

        # Root node
        root_id = self._tree.insert(
            "", "end",
            text=f"{self._all_audio_text} ({total:,})",
            open=True,
        )
        self._node_to_path[root_id] = ""  # empty = all

        # Insert children recursively with auto-expand
        tree_children = tree_dict.get("children", {})
        self._insert_children(root_id, tree_children, "", depth=1)

        # Auto-select root
        self._tree.selection_set(root_id)
        self._tree.see(root_id)

    def _insert_children(
        self, parent_id: str, children: Dict, parent_path: str, depth: int
    ) -> None:
        """Recursively insert child nodes sorted alphabetically."""
        for name in sorted(children.keys()):
            node = children[name]
            count = node.get("_count", 0)
            child_path = f"{parent_path}/{name}" if parent_path else name

            # Auto-expand first N levels for a useful initial view
            auto_open = depth < _AUTO_EXPAND_DEPTH

            item_id = self._tree.insert(
                parent_id, "end",
                text=f"{name} ({count:,})",
                open=auto_open,
            )
            self._node_to_path[item_id] = child_path

            # Recurse into sub-children
            sub_children = node.get("children", {})
            if sub_children:
                self._insert_children(item_id, sub_children, child_path, depth + 1)

    def clear(self) -> None:
        """Clear tree contents."""
        children = self._tree.get_children()
        if children:
            self._tree.delete(*children)
        self._node_to_path.clear()

    def set_label(self, text: str) -> None:
        """Update the LabelFrame title text."""
        self.configure(text=text)

    def set_all_audio_text(self, text: str) -> None:
        """Update the 'All Audio' root label text (for i18n)."""
        self._all_audio_text = text
