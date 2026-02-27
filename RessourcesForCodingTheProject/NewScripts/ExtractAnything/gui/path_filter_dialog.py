"""
Reusable Path Filter Dialog.

Two-panel Toplevel dialog that lets users browse the EXPORT tree
and select folders/files.  Supports both INCLUDE and EXCLUDE modes.

Adapted from QuickTranslate's ExcludeDialog.
"""

import logging
import tkinter as tk
from pathlib import Path
from tkinter import ttk

logger = logging.getLogger(__name__)

_MAX_SEARCH_RESULTS = 500


class PathFilterDialog(tk.Toplevel):
    """
    EXPORT tree browser for selecting folders/files.

    Left panel:  Lazy-loaded EXPORT tree (ttk.Treeview) with substring search
    Right panel: Currently selected paths (ttk.Treeview)

    Result: self.result is a list[str] of relative paths, or None if cancelled.
    """

    def __init__(
        self,
        parent: tk.Tk,
        export_folder: Path,
        current_selections: list[str],
        *,
        mode: str = "include",
        title: str | None = None,
    ):
        super().__init__(parent)

        self._mode = mode
        if title:
            self.title(title)
        elif mode == "include":
            self.title("Path Filter — Include Paths")
        else:
            self.title("Path Filter — Exclude Paths")

        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._export_folder = export_folder
        self._selections: list[str] = list(current_selections)
        self.result: list[str] | None = None

        # Search state
        self._search_var = tk.StringVar()
        self._search_after_id = None
        self._search_active = False
        self._all_entries: list[tuple[str, str, bool]] | None = None

        self._build_ui()

        # Populate trees
        self._populate_export_root()
        self._rebuild_selection_tree()
        self._update_status()

        # Wire search
        self._search_var.trace_add("write", self._on_search_changed)

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
        self.bind("<Escape>", self._on_escape)
        self.bind("<Return>", lambda e: self._on_save())
        self.wait_window(self)

    def _build_ui(self):
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        if self._mode == "include":
            header_text = "Select folders/files to INCLUDE in extraction results"
            right_label = "Included Paths"
        else:
            header_text = "Select folders/files to EXCLUDE from results"
            right_label = "Excluded Paths"

        ttk.Label(
            main, text=header_text,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        # Middle: 3-column layout
        mid = ttk.Frame(main)
        mid.pack(fill=tk.BOTH, expand=True)
        mid.columnconfigure(0, weight=55)
        mid.columnconfigure(1, weight=0)
        mid.columnconfigure(2, weight=45)
        mid.rowconfigure(0, weight=1)

        # === Left Panel: EXPORT Tree ===
        left_frame = ttk.LabelFrame(mid, text="EXPORT Tree", padding=4)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Search bar
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(search_frame, text="\U0001f50d", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self._search_entry = ttk.Entry(search_frame, textvariable=self._search_var, font=("Segoe UI", 9))
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._clear_btn = ttk.Button(search_frame, text="\u2715", width=3, command=self._clear_search)

        self._search_info = ttk.Label(search_frame, text="", font=("Segoe UI", 8))

        # Tree + scrollbar
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self._export_tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        left_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._export_tree.yview)
        self._export_tree.configure(yscrollcommand=left_scroll.set)
        self._export_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._export_tree.bind("<<TreeviewOpen>>", self._on_export_expand)

        # === Center Buttons ===
        btn_frame = ttk.Frame(mid)
        btn_frame.grid(row=0, column=1, sticky="ns", padx=6)

        ttk.Frame(btn_frame).pack(expand=True)
        ttk.Button(btn_frame, text="Add >>", width=10, command=self._add_selected).pack(pady=4)
        ttk.Button(btn_frame, text="<< Remove", width=10, command=self._remove_selected).pack(pady=4)
        ttk.Frame(btn_frame).pack(expand=True)

        # === Right Panel: Selected Paths ===
        right_frame = ttk.LabelFrame(mid, text=right_label, padding=4)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

        self._selection_tree = ttk.Treeview(right_frame, show="tree", selectmode="extended")
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self._selection_tree.yview)
        self._selection_tree.configure(yscrollcommand=right_scroll.set)
        self._selection_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
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
    # Search
    # =========================================================================

    def _on_search_changed(self, *_args):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)

        if self._search_var.get():
            self._clear_btn.pack(side=tk.LEFT, padx=(2, 0))
        else:
            self._clear_btn.pack_forget()
            self._search_info.pack_forget()

        self._search_after_id = self.after(250, self._execute_search)

    def _execute_search(self):
        self._search_after_id = None
        query = self._search_var.get().strip().lower()

        if not query:
            self._restore_tree_view()
            return

        if self._all_entries is None:
            self._all_entries = self._walk_export_tree()

        matches = [(rel, name, is_dir) for rel, name, is_dir in self._all_entries
                   if query in rel.lower()]

        self._export_tree.delete(*self._export_tree.get_children())
        self._search_active = True

        shown = 0
        for rel, name, is_dir in matches:
            if shown >= _MAX_SEARCH_RESULTS:
                break
            icon = "\U0001f4c1" if is_dir else "\U0001f4c4"
            self._export_tree.insert("", tk.END, text=f"{icon} {rel}", values=(rel,))
            shown += 1

        total = len(matches)
        if total > _MAX_SEARCH_RESULTS:
            info = f"{_MAX_SEARCH_RESULTS}/{total}"
        else:
            info = str(total)
        self._search_info.configure(text=info)
        self._search_info.pack(side=tk.LEFT, padx=(4, 0))

    def _walk_export_tree(self) -> list[tuple[str, str, bool]]:
        results = []
        try:
            for item in sorted(self._export_folder.rglob("*"), key=lambda p: str(p).lower()):
                try:
                    is_dir = item.is_dir()
                    if is_dir:
                        rel = self._rel_path(item)
                        results.append((rel, item.name, True))
                    elif item.is_file() and item.suffix.lower() == ".xml":
                        rel = self._rel_path(item)
                        results.append((rel, item.name, False))
                except OSError:
                    continue
        except OSError:
            logger.warning("Failed to walk EXPORT tree for search")
        return results

    def _restore_tree_view(self):
        if not self._search_active:
            return
        self._search_active = False
        self._search_info.pack_forget()
        self._export_tree.delete(*self._export_tree.get_children())
        self._populate_export_root()

    def _clear_search(self):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._search_var.set("")
        self._clear_btn.pack_forget()
        self._search_info.pack_forget()
        self._restore_tree_view()
        self._search_entry.focus_set()

    def _on_escape(self, _event):
        if self._search_var.get():
            self._clear_search()
        else:
            self._on_cancel()

    # =========================================================================
    # EXPORT Tree (Lazy Loading)
    # =========================================================================

    def _populate_export_root(self):
        if not self._export_folder.exists():
            self._export_tree.insert("", tk.END, text="(EXPORT folder not found)")
            return
        self._insert_children("", self._export_folder)

    def _insert_children(self, parent_iid: str, folder: Path):
        try:
            children = list(folder.iterdir())
        except OSError:
            return

        dirs = sorted([c for c in children if c.is_dir()], key=lambda p: p.name.lower())
        files = sorted([c for c in children if c.is_file() and c.suffix.lower() == ".xml"],
                       key=lambda p: p.name.lower())

        for d in dirs:
            rel = self._rel_path(d)
            iid = self._export_tree.insert(parent_iid, tk.END, text=f"\U0001f4c1 {d.name}",
                                           values=(rel,), open=False)
            self._export_tree.insert(iid, tk.END, text="__dummy__")

        for f in files:
            rel = self._rel_path(f)
            self._export_tree.insert(parent_iid, tk.END, text=f"\U0001f4c4 {f.name}",
                                     values=(rel,))

    def _on_export_expand(self, event):
        if self._search_active:
            return
        iid = self._export_tree.focus()
        children = self._export_tree.get_children(iid)

        if len(children) == 1 and self._export_tree.item(children[0], "text") == "__dummy__":
            self._export_tree.delete(children[0])
            rel = self._export_tree.item(iid, "values")
            if rel:
                folder = self._export_folder / rel[0]
                self._insert_children(iid, folder)

    def _rel_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._export_folder)).replace("\\", "/")
        except ValueError:
            return path.name

    # =========================================================================
    # Add / Remove Logic
    # =========================================================================

    def _add_selected(self):
        selected = self._export_tree.selection()
        if not selected:
            return

        changed = False
        for iid in selected:
            vals = self._export_tree.item(iid, "values")
            if not vals:
                continue
            if self._add_selection(vals[0]):
                changed = True

        if changed:
            self._rebuild_selection_tree()
            self._update_status()

    def _add_selection(self, rel_path: str) -> bool:
        """Add a path with smart consolidation.

        - Adding a folder removes all children already selected (folder subsumes them).
        - Adding a file is skipped if an ancestor folder is already selected.
        """
        norm = rel_path.replace("\\", "/")
        is_folder = not norm.lower().endswith(".xml")

        if norm in self._selections:
            return False

        # Check if any ancestor folder already selected
        for existing in self._selections:
            if not existing.lower().endswith(".xml"):
                prefix = existing.replace("\\", "/")
                if norm.lower().startswith(prefix.lower() + "/"):
                    return False

        if not is_folder:
            self._selections.append(norm)
            return True

        # Adding a folder: remove all children under it
        prefix_lower = norm.lower() + "/"
        self._selections = [
            p for p in self._selections
            if not p.replace("\\", "/").lower().startswith(prefix_lower)
        ]
        self._selections = [
            p for p in self._selections
            if p.replace("\\", "/").lower() != norm.lower()
        ]
        self._selections.append(norm)
        return True

    def _remove_selected(self):
        selected = self._selection_tree.selection()
        if not selected:
            return

        to_remove = set()
        for iid in selected:
            vals = self._selection_tree.item(iid, "values")
            if vals and vals[0]:
                to_remove.add(vals[0])

        if to_remove:
            self._selections = [p for p in self._selections if p not in to_remove]
            self._rebuild_selection_tree()
            self._update_status()

    def _clear_all(self):
        if self._selections:
            self._selections.clear()
            self._rebuild_selection_tree()
            self._update_status()

    # =========================================================================
    # Selection Tree Display
    # =========================================================================

    def _rebuild_selection_tree(self):
        self._selection_tree.delete(*self._selection_tree.get_children())

        if not self._selections:
            return

        tree_data: dict[str, list[tuple[str, str, bool]]] = {}
        for path in sorted(self._selections, key=lambda p: p.lower()):
            parts = path.replace("\\", "/").split("/")
            is_folder = not path.lower().endswith(".xml")
            top = parts[0] if parts else path

            if top not in tree_data:
                tree_data[top] = []

            if len(parts) == 1:
                tree_data[top].append((path, parts[0], is_folder))
            else:
                tree_data[top].append((path, "/".join(parts[1:]), is_folder))

        for top_key in sorted(tree_data.keys(), key=str.lower):
            items = tree_data[top_key]

            if len(items) == 1 and items[0][1] == top_key:
                path, name, is_folder = items[0]
                icon = "\U0001f4c1" if is_folder else "\U0001f4c4"
                label = "Folder" if is_folder else "File"
                self._selection_tree.insert("", tk.END, text=f"{icon} {name}  [{label}]",
                                            values=(path,))
            else:
                group_iid = self._selection_tree.insert("", tk.END, text=f"\U0001f4c1 {top_key}",
                                                        values=("",), open=True)
                for path, name, is_folder in items:
                    if name == top_key:
                        self._selection_tree.item(group_iid, values=(path,))
                        icon = "\U0001f4c1" if is_folder else "\U0001f4c4"
                        label = "Folder" if is_folder else "File"
                        self._selection_tree.item(group_iid,
                                                  text=f"{icon} {top_key}  [{label}]")
                    else:
                        icon = "\U0001f4c1" if is_folder else "\U0001f4c4"
                        label = "Folder" if is_folder else "File"
                        self._selection_tree.insert(group_iid, tk.END,
                                                    text=f"{icon} {name}  [{label}]",
                                                    values=(path,))

    # =========================================================================
    # Status
    # =========================================================================

    def _update_status(self):
        action = "included" if self._mode == "include" else "excluded"

        if not self._selections:
            self._status_label.configure(text=f"No paths {action}")
            return

        folders = sum(1 for p in self._selections if not p.lower().endswith(".xml"))
        files = sum(1 for p in self._selections if p.lower().endswith(".xml"))

        parts = []
        if folders:
            parts.append(f"{folders} folder{'s' if folders != 1 else ''}")
        if files:
            parts.append(f"{files} file{'s' if files != 1 else ''}")

        self._status_label.configure(
            text=f"{len(self._selections)} paths {action} ({', '.join(parts)})"
        )

    # =========================================================================
    # Save / Cancel
    # =========================================================================

    def _on_save(self):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self.result = list(self._selections)
        self.destroy()

    def _on_cancel(self):
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self.result = None
        self.destroy()
