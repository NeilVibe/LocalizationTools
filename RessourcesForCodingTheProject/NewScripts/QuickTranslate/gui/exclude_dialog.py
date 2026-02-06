"""
Exclude Dialog for Missing Translations.

Two-panel Toplevel dialog that lets users browse the EXPORT tree
and select folders/files to exclude from Missing Translation results.
Exclusions are persisted via config.save_exclude_rules().
"""

import logging
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class ExcludeDialog(tk.Toplevel):
    """
    EXPORT tree browser for selecting folders/files to exclude.

    Left panel:  Lazy-loaded EXPORT tree (ttk.Treeview)
    Right panel: Currently excluded paths (ttk.Treeview)

    Result: self.result is a List[str] of relative paths, or None if cancelled.
    """

    def __init__(self, parent: tk.Tk, export_folder: Path, current_exclusions: List[str]):
        super().__init__(parent)
        self.title("Exclude from Missing Translations")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._export_folder = export_folder
        self._exclusions: List[str] = list(current_exclusions)
        self.result: Optional[List[str]] = None

        self._build_ui()

        # Populate trees
        self._populate_export_root()
        self._rebuild_excluded_tree()
        self._update_status()

        # Center on parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = max(self.winfo_width(), 800)
        h = max(self.winfo_height(), 550)
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(700, 450)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_save())
        self.wait_window(self)

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(
            main,
            text="Select folders/files to exclude from Missing Translation results",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        # Middle: 3-column layout (left tree, buttons, right tree)
        mid = ttk.Frame(main)
        mid.pack(fill=tk.BOTH, expand=True)
        mid.columnconfigure(0, weight=55)
        mid.columnconfigure(1, weight=0)
        mid.columnconfigure(2, weight=45)
        mid.rowconfigure(0, weight=1)

        # === Left Panel: EXPORT Tree ===
        left_frame = ttk.LabelFrame(mid, text="EXPORT Tree", padding=4)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self._export_tree = ttk.Treeview(left_frame, show="tree", selectmode="extended")
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self._export_tree.yview)
        self._export_tree.configure(yscrollcommand=left_scroll.set)
        self._export_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._export_tree.bind("<<TreeviewOpen>>", self._on_export_expand)

        # === Center Buttons ===
        btn_frame = ttk.Frame(mid)
        btn_frame.grid(row=0, column=1, sticky="ns", padx=6)

        spacer_top = ttk.Frame(btn_frame)
        spacer_top.pack(expand=True)

        self._add_btn = ttk.Button(btn_frame, text="Add >>", width=10, command=self._add_selected)
        self._add_btn.pack(pady=4)

        self._remove_btn = ttk.Button(btn_frame, text="<< Remove", width=10, command=self._remove_selected)
        self._remove_btn.pack(pady=4)

        spacer_bot = ttk.Frame(btn_frame)
        spacer_bot.pack(expand=True)

        # === Right Panel: Excluded Paths ===
        right_frame = ttk.LabelFrame(mid, text="Excluded Paths", padding=4)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        self._excluded_tree = ttk.Treeview(right_frame, show="tree", selectmode="extended")
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self._excluded_tree.yview)
        self._excluded_tree.configure(yscrollcommand=right_scroll.set)
        self._excluded_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # === Bottom: Status + Buttons ===
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(8, 0))

        self._status_label = ttk.Label(bottom, text="", font=("Segoe UI", 9))
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(bottom, text="Clear All", command=self._clear_all, width=10).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(bottom, text="Save", command=self._on_save, width=10).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(bottom, text="Cancel", command=self._on_cancel, width=10).pack(side=tk.LEFT)

    # =========================================================================
    # EXPORT Tree (Lazy Loading)
    # =========================================================================

    def _populate_export_root(self):
        """Populate the root level of the EXPORT tree."""
        if not self._export_folder.exists():
            self._export_tree.insert("", tk.END, text="(EXPORT folder not found)")
            return

        self._insert_children("", self._export_folder)

    def _insert_children(self, parent_iid: str, folder: Path):
        """Insert sorted children (dirs first, then .xml files) under parent_iid."""
        try:
            children = list(folder.iterdir())
        except OSError:
            return

        dirs = sorted([c for c in children if c.is_dir()], key=lambda p: p.name.lower())
        files = sorted([c for c in children if c.is_file() and c.suffix.lower() == ".xml"],
                       key=lambda p: p.name.lower())

        for d in dirs:
            rel = self._rel_path(d)
            iid = self._export_tree.insert(parent_iid, tk.END, text=f"\U0001F4C1 {d.name}",
                                           values=(rel,), open=False)
            # Insert dummy child for expand arrow
            self._export_tree.insert(iid, tk.END, text="__dummy__")

        for f in files:
            rel = self._rel_path(f)
            self._export_tree.insert(parent_iid, tk.END, text=f"\U0001F4C4 {f.name}",
                                     values=(rel,))

    def _on_export_expand(self, event):
        """Lazy-load children when a folder is expanded."""
        iid = self._export_tree.focus()
        children = self._export_tree.get_children(iid)

        # Check if this is the dummy placeholder
        if len(children) == 1 and self._export_tree.item(children[0], "text") == "__dummy__":
            self._export_tree.delete(children[0])
            rel = self._export_tree.item(iid, "values")
            if rel:
                folder = self._export_folder / rel[0]
                self._insert_children(iid, folder)

    def _rel_path(self, path: Path) -> str:
        """Get path relative to EXPORT folder, with / separators."""
        try:
            return str(path.relative_to(self._export_folder)).replace("\\", "/")
        except ValueError:
            return path.name

    # =========================================================================
    # Add / Remove Logic
    # =========================================================================

    def _add_selected(self):
        """Add selected EXPORT tree items to exclusion list."""
        selected = self._export_tree.selection()
        if not selected:
            return

        changed = False
        for iid in selected:
            vals = self._export_tree.item(iid, "values")
            if not vals:
                continue
            rel = vals[0]
            if self._add_exclusion(rel):
                changed = True

        if changed:
            self._rebuild_excluded_tree()
            self._update_status()

    def _add_exclusion(self, rel_path: str) -> bool:
        """
        Add a path to exclusions with consolidation logic.

        - Adding a folder: removes all children already in exclusions (folder subsumes them)
        - Adding a file: skipped if any ancestor folder is already excluded
        """
        norm = rel_path.replace("\\", "/")
        is_folder = not norm.lower().endswith(".xml")

        if norm in self._exclusions:
            return False

        # Check if any ancestor folder is already excluded (applies to both files and folders)
        for existing in self._exclusions:
            if not existing.lower().endswith(".xml"):
                # existing is a folder - check if it's an ancestor
                prefix = existing.replace("\\", "/")
                if norm.lower().startswith(prefix.lower() + "/"):
                    return False  # Already covered by parent folder

        if not is_folder:
            self._exclusions.append(norm)
            return True

        # Adding a folder: remove all children (files and subfolders under it)
        prefix_lower = norm.lower() + "/"
        self._exclusions = [
            p for p in self._exclusions
            if not p.replace("\\", "/").lower().startswith(prefix_lower)
        ]
        # Also remove exact match subfolders
        self._exclusions = [
            p for p in self._exclusions
            if p.replace("\\", "/").lower() != norm.lower()
        ]
        self._exclusions.append(norm)
        return True

    def _remove_selected(self):
        """Remove selected items from the excluded tree."""
        selected = self._excluded_tree.selection()
        if not selected:
            return

        to_remove = set()
        for iid in selected:
            vals = self._excluded_tree.item(iid, "values")
            if vals and vals[0]:
                to_remove.add(vals[0])

        if to_remove:
            self._exclusions = [p for p in self._exclusions if p not in to_remove]
            self._rebuild_excluded_tree()
            self._update_status()

    def _clear_all(self):
        """Clear all exclusions."""
        if self._exclusions:
            self._exclusions.clear()
            self._rebuild_excluded_tree()
            self._update_status()

    # =========================================================================
    # Excluded Tree Display
    # =========================================================================

    def _rebuild_excluded_tree(self):
        """Rebuild the excluded paths tree from current exclusions."""
        self._excluded_tree.delete(*self._excluded_tree.get_children())

        if not self._exclusions:
            return

        # Organize as a mini-tree: group by top-level folder
        tree_data = {}  # top_folder -> list of (full_path, display_name, is_folder)
        for path in sorted(self._exclusions, key=lambda p: p.lower()):
            parts = path.replace("\\", "/").split("/")
            is_folder = not path.lower().endswith(".xml")
            top = parts[0] if parts else path

            if top not in tree_data:
                tree_data[top] = []

            if len(parts) == 1:
                # Top-level item
                tree_data[top].append((path, parts[0], is_folder))
            else:
                # Nested item
                tree_data[top].append((path, "/".join(parts[1:]), is_folder))

        for top_key in sorted(tree_data.keys(), key=str.lower):
            items = tree_data[top_key]

            if len(items) == 1 and items[0][1] == top_key:
                # Single top-level entry - show directly
                path, name, is_folder = items[0]
                icon = "\U0001F4C1" if is_folder else "\U0001F4C4"
                label = "Folder" if is_folder else "File"
                self._excluded_tree.insert("", tk.END, text=f"{icon} {name}  [{label}]",
                                           values=(path,))
            else:
                # Group under top-level folder
                group_iid = self._excluded_tree.insert("", tk.END, text=f"\U0001F4C1 {top_key}",
                                                        values=("",), open=True)
                for path, name, is_folder in items:
                    if name == top_key:
                        # The top folder itself is excluded
                        self._excluded_tree.item(group_iid, values=(path,))
                        icon = "\U0001F4C1" if is_folder else "\U0001F4C4"
                        label = "Folder" if is_folder else "File"
                        self._excluded_tree.item(group_iid,
                                                 text=f"{icon} {top_key}  [{label}]")
                    else:
                        icon = "\U0001F4C1" if is_folder else "\U0001F4C4"
                        label = "Folder" if is_folder else "File"
                        self._excluded_tree.insert(group_iid, tk.END,
                                                   text=f"{icon} {name}  [{label}]",
                                                   values=(path,))

    # =========================================================================
    # Status
    # =========================================================================

    def _update_status(self):
        """Update the status label with current exclusion count."""
        if not self._exclusions:
            self._status_label.configure(text="No exclusions configured")
            return

        folders = sum(1 for p in self._exclusions if not p.lower().endswith(".xml"))
        files = sum(1 for p in self._exclusions if p.lower().endswith(".xml"))

        parts = []
        if folders:
            parts.append(f"{folders} folder{'s' if folders != 1 else ''}")
        if files:
            parts.append(f"{files} file{'s' if files != 1 else ''}")

        self._status_label.configure(
            text=f"{len(self._exclusions)} paths excluded ({', '.join(parts)})"
        )

    # =========================================================================
    # Save / Cancel
    # =========================================================================

    def _on_save(self):
        self.result = list(self._exclusions)
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
