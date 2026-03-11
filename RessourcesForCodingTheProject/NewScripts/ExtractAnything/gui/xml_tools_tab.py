"""XML Tools tab – miscellaneous LocStr XML operations.

Grafted from QSS misceallenousextractforXML.py.  Provides 8 operations:
restore, swap, extract (single + dual), erase, modify, stack, replace-by-SID.
"""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core import xml_tools_engine
from .base_tab import BaseTab

logger = logging.getLogger(__name__)

_XML_FILETYPES = [("XML files", "*.xml"), ("All files", "*.*")]


class XmlToolsTab(BaseTab):
    TAB_TITLE = "XML Tools"

    def _build_ui(self) -> None:
        # Scrollable canvas for all the controls
        canvas = tk.Canvas(self.frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=canvas.yview)
        self._inner = ttk.Frame(canvas)

        self._inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling — scoped to this canvas via Enter/Leave
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_linux_scroll_up(event):
            canvas.yview_scroll(-1, "units")

        def _on_linux_scroll_down(event):
            canvas.yview_scroll(1, "units")

        def _bind_scroll(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_linux_scroll_up)
            canvas.bind_all("<Button-5>", _on_linux_scroll_down)

        def _unbind_scroll(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_scroll)
        canvas.bind("<Leave>", _unbind_scroll)

        inner = self._inner

        # ── Mode (Folder / File) ──
        mode_frm = ttk.LabelFrame(inner, text="Mode & Path")
        mode_frm.pack(fill=tk.X, padx=5, pady=(5, 2))

        self._mode = tk.StringVar(value="folder")
        row = ttk.Frame(mode_frm)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Radiobutton(row, text="Folder", variable=self._mode,
                        value="folder").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(row, text="Single File", variable=self._mode,
                        value="file").pack(side=tk.LEFT)

        self._path_var = tk.StringVar()
        path_row = ttk.Frame(mode_frm)
        path_row.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(path_row, text="Path:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(path_row, textvariable=self._path_var, width=55).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(path_row, text="Browse", command=self._browse_path).pack(side=tk.LEFT)

        # ── Section 1: Quick Str/StrOrigin Ops ──
        sec1 = ttk.LabelFrame(inner, text="1. Quick Str / StrOrigin Operations")
        sec1.pack(fill=tk.X, padx=5, pady=2)

        btn_row = ttk.Frame(sec1)
        btn_row.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_row, text="Restore Str from StrOrigin",
                   command=self._do_restore).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Swap Str ↔ StrOrigin",
                   command=self._do_swap).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Stack KR/Translation",
                   command=self._do_stack).pack(side=tk.LEFT)

        ttk.Label(sec1, text="Restore = copy StrOrigin→Str  |  "
                             "Swap = exchange values  |  "
                             "Stack = append Str after StrOrigin with <br/>",
                  foreground="#666666", font=("Segoe UI", 8)).pack(padx=5, pady=(0, 5))

        # ── Section 2: Extract Single Condition ──
        sec2 = ttk.LabelFrame(inner, text="2. Extract Rows (Single Condition)")
        sec2.pack(fill=tk.X, padx=5, pady=2)

        r0 = ttk.Frame(sec2)
        r0.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(r0, text="Regex:").pack(side=tk.LEFT, padx=(0, 2))
        self._extract_regex = tk.StringVar()
        ttk.Entry(r0, textvariable=self._extract_regex, width=30).pack(
            side=tk.LEFT, padx=(0, 10))
        self._extract_contained = tk.BooleanVar(value=True)
        ttk.Radiobutton(r0, text="is contained",
                        variable=self._extract_contained, value=True).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(r0, text="is NOT contained",
                        variable=self._extract_contained, value=False).pack(side=tk.LEFT)

        r1 = ttk.Frame(sec2)
        r1.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(r1, text="Field:").pack(side=tk.LEFT, padx=(0, 2))
        self._extract_field = tk.StringVar(value="Str")
        ttk.Radiobutton(r1, text="Str", variable=self._extract_field,
                        value="Str").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(r1, text="StrOrigin", variable=self._extract_field,
                        value="StrOrigin").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(r1, text="Str OR StrOrigin", variable=self._extract_field,
                        value="StrOrStrOrigin").pack(side=tk.LEFT)

        ttk.Button(sec2, text="Extract", command=self._do_extract).pack(pady=(2, 5))

        # ── Section 3: Extract Dual AND ──
        sec3 = ttk.LabelFrame(inner, text="3. Extract Rows (Str AND StrOrigin)")
        sec3.pack(fill=tk.X, padx=5, pady=2)

        r_str = ttk.Frame(sec3)
        r_str.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(r_str, text="Str Regex:").pack(side=tk.LEFT, padx=(0, 2))
        self._dual_str_regex = tk.StringVar()
        ttk.Entry(r_str, textvariable=self._dual_str_regex, width=25).pack(
            side=tk.LEFT, padx=(0, 10))
        self._dual_str_contained = tk.BooleanVar(value=True)
        ttk.Radiobutton(r_str, text="contained",
                        variable=self._dual_str_contained, value=True).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(r_str, text="NOT contained",
                        variable=self._dual_str_contained, value=False).pack(side=tk.LEFT)

        r_so = ttk.Frame(sec3)
        r_so.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(r_so, text="StrOrigin Regex:").pack(side=tk.LEFT, padx=(0, 2))
        self._dual_so_regex = tk.StringVar()
        ttk.Entry(r_so, textvariable=self._dual_so_regex, width=25).pack(
            side=tk.LEFT, padx=(0, 10))
        self._dual_so_contained = tk.BooleanVar(value=True)
        ttk.Radiobutton(r_so, text="contained",
                        variable=self._dual_so_contained, value=True).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(r_so, text="NOT contained",
                        variable=self._dual_so_contained, value=False).pack(side=tk.LEFT)

        ttk.Button(sec3, text="Extract (AND)", command=self._do_extract_dual).pack(pady=(2, 5))

        # ── Section 4: Erase / Modify ──
        sec4 = ttk.LabelFrame(inner, text="4. Erase / Modify Str")
        sec4.pack(fill=tk.X, padx=5, pady=2)

        # Erase row
        er = ttk.Frame(sec4)
        er.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(er, text="Erase Regex:").pack(side=tk.LEFT, padx=(0, 2))
        self._erase_regex = tk.StringVar()
        ttk.Entry(er, textvariable=self._erase_regex, width=25).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Button(er, text="Erase Matching", command=self._do_erase).pack(side=tk.LEFT)

        # Modify rows
        mr = ttk.Frame(sec4)
        mr.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(mr, text="Search Regex:").pack(side=tk.LEFT, padx=(0, 2))
        self._modify_search = tk.StringVar()
        ttk.Entry(mr, textvariable=self._modify_search, width=20).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Label(mr, text="Replace:").pack(side=tk.LEFT, padx=(0, 2))
        self._modify_replace = tk.StringVar()
        ttk.Entry(mr, textvariable=self._modify_replace, width=20).pack(
            side=tk.LEFT, padx=(0, 5))
        ttk.Button(mr, text="Modify", command=self._do_modify).pack(side=tk.LEFT)

        ttk.Label(sec4, text="Erase = remove matched text from Str  |  "
                             "Modify = regex replace in Str (raw text, case-sensitive)",
                  foreground="#666666", font=("Segoe UI", 8)).pack(padx=5, pady=(0, 5))

        # ── Section 5: Replace StrOrigin by StringId (2 folders) ──
        sec5 = ttk.LabelFrame(inner, text="5. Replace StrOrigin (Source → Target by StringId)")
        sec5.pack(fill=tk.X, padx=5, pady=2)

        self._src_folder_var = tk.StringVar()
        sf = ttk.Frame(sec5)
        sf.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(sf, text="Source:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(sf, textvariable=self._src_folder_var, width=45).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(sf, text="Browse",
                   command=lambda: self.browse_folder(self._src_folder_var, "Select SOURCE folder")).pack(side=tk.LEFT)

        self._tgt_folder_var = tk.StringVar()
        tf = ttk.Frame(sec5)
        tf.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(tf, text="Target:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Entry(tf, textvariable=self._tgt_folder_var, width=45).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(tf, text="Browse",
                   command=lambda: self.browse_folder(self._tgt_folder_var, "Select TARGET folder")).pack(side=tk.LEFT)

        ttk.Button(sec5, text="Replace StrOrigin by StringId",
                   command=self._do_replace_strorigin).pack(pady=(2, 5))

        ttk.Label(sec5, text="Matches StringId in SOURCE → overwrites StrOrigin in TARGET.",
                  foreground="#C62828", font=("Segoe UI", 8)).pack(padx=5, pady=(0, 5))

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------
    def _browse_path(self) -> None:
        if self._mode.get() == "folder":
            path = filedialog.askdirectory(title="Select folder")
        else:
            path = filedialog.askopenfilename(
                title="Select XML file", filetypes=_XML_FILETYPES)
        if path:
            self._path_var.set(path)

    def _get_path(self) -> str | None:
        p = self._path_var.get().strip()
        if not p:
            self.log("Select a path first (Mode & Path section).", "error")
            return None
        pp = Path(p)
        if not pp.exists():
            self.log(f"Path does not exist: {p}", "error")
            return None
        return p

    # ------------------------------------------------------------------
    # 1. Quick ops
    # ------------------------------------------------------------------
    def _do_restore(self) -> None:
        path = self._get_path()
        if not path:
            return
        if not messagebox.askyesno(
            "Confirm Restore",
            "This will OVERWRITE Str with StrOrigin in all LocStr elements.\n\n"
            f"Path: {path}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Restore Str from StrOrigin")
            self.set_progress(5)
            changed = xml_tools_engine.restore_str_from_strorigin(
                path, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(f"Done: {changed} file(s) modified.", "success")

        self.run_in_thread(work)

    def _do_swap(self) -> None:
        path = self._get_path()
        if not path:
            return
        if not messagebox.askyesno(
            "Confirm Swap",
            "This will SWAP Str and StrOrigin values in all LocStr elements.\n"
            "Elements with only one attribute will get the other set to empty.\n\n"
            f"Path: {path}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Swap Str ↔ StrOrigin")
            self.set_progress(5)
            changed = xml_tools_engine.swap_str_with_strorigin(
                path, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(f"Done: {changed} file(s) modified.", "success")

        self.run_in_thread(work)

    def _do_stack(self) -> None:
        path = self._get_path()
        if not path:
            return
        if not messagebox.askyesno(
            "Confirm Stack",
            "This will APPEND Str after StrOrigin (with <br/> separator)\n"
            "for every LocStr element.\n\n"
            f"Path: {path}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Stack KR/Translation")
            self.set_progress(5)
            changed = xml_tools_engine.stack_kr_translation(
                path, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(f"Done: {changed} file(s) modified.", "success")

        self.run_in_thread(work)

    # ------------------------------------------------------------------
    # 2. Extract single
    # ------------------------------------------------------------------
    def _do_extract(self) -> None:
        path = self._get_path()
        if not path:
            return
        regex = self._extract_regex.get().strip()
        if not regex:
            self.log("Enter a regex pattern for extraction.", "error")
            return

        # Prompt save path on main thread BEFORE worker
        save_path = filedialog.asksaveasfilename(
            title="Save Extracted XML",
            defaultextension=".xml",
            filetypes=_XML_FILETYPES,
        )
        if not save_path:
            return

        field = self._extract_field.get()
        contained = self._extract_contained.get()

        def work():
            self._log_header("Extract Rows (Single Condition)")
            self.log(f"Field: {field} | Regex: {regex} | "
                     f"{'Contained' if contained else 'NOT Contained'}")
            self.set_progress(10)

            xml_str = xml_tools_engine.extract_rows(
                path, field, regex, contained, log_fn=self.log)

            self.set_progress(90)
            if xml_str:
                Path(save_path).write_text(xml_str, encoding="utf-8")
                self.log(f"Saved: {save_path}", "success")
            else:
                self.log("No matching rows found.", "warning")

        self.run_in_thread(work)

    # ------------------------------------------------------------------
    # 3. Extract dual AND
    # ------------------------------------------------------------------
    def _do_extract_dual(self) -> None:
        path = self._get_path()
        if not path:
            return

        regex_str = self._dual_str_regex.get().strip()
        regex_so = self._dual_so_regex.get().strip()
        if not regex_str and not regex_so:
            self.log("Enter at least one regex (Str or StrOrigin).", "error")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Extracted XML",
            defaultextension=".xml",
            filetypes=_XML_FILETYPES,
        )
        if not save_path:
            return

        contained_str = self._dual_str_contained.get()
        contained_so = self._dual_so_contained.get()

        def work():
            self._log_header("Extract Rows (Dual AND)")
            parts = []
            if regex_str:
                parts.append(f"Str: '{regex_str}' ({'in' if contained_str else 'NOT in'})")
            if regex_so:
                parts.append(f"StrOrigin: '{regex_so}' ({'in' if contained_so else 'NOT in'})")
            self.log(" AND ".join(parts))
            self.set_progress(10)

            xml_str = xml_tools_engine.extract_rows_dual(
                path, regex_str, contained_str, regex_so, contained_so,
                log_fn=self.log)

            self.set_progress(90)
            if xml_str:
                Path(save_path).write_text(xml_str, encoding="utf-8")
                self.log(f"Saved: {save_path}", "success")
            else:
                self.log("No matching rows found.", "warning")

        self.run_in_thread(work)

    # ------------------------------------------------------------------
    # 4. Erase / Modify
    # ------------------------------------------------------------------
    def _do_erase(self) -> None:
        path = self._get_path()
        if not path:
            return
        regex = self._erase_regex.get().strip()
        if not regex:
            self.log("Enter a regex pattern for erase.", "error")
            return

        if not messagebox.askyesno(
            "Confirm Erase",
            f"This will REMOVE text matching '{regex}' from Str values.\n\n"
            f"Path: {path}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Erase Str by Regex")
            self.set_progress(5)
            changed = xml_tools_engine.erase_str_matching(
                path, regex, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(f"Done: {changed} file(s) modified.", "success")

        self.run_in_thread(work)

    def _do_modify(self) -> None:
        path = self._get_path()
        if not path:
            return
        search = self._modify_search.get().strip()
        if not search:
            self.log("Enter a search regex for modify.", "error")
            return
        replace = self._modify_replace.get()

        if not messagebox.askyesno(
            "Confirm Modify",
            f"This will REPLACE '{search}' with '{replace}' in Str values.\n"
            "(Raw text, case-sensitive)\n\n"
            f"Path: {path}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Modify Str by Regex")
            self.set_progress(5)
            changed = xml_tools_engine.modify_str_matching(
                path, search, replace, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(f"Done: {changed} file(s) modified.", "success")

        self.run_in_thread(work)

    # ------------------------------------------------------------------
    # 5. Replace StrOrigin by StringId
    # ------------------------------------------------------------------
    def _do_replace_strorigin(self) -> None:
        src = self._src_folder_var.get().strip()
        tgt = self._tgt_folder_var.get().strip()
        if not src or not tgt:
            self.log("Source and target folders are required.", "error")
            return

        if not messagebox.askyesno(
            "Confirm Replace StrOrigin",
            "This will OVERWRITE StrOrigin in TARGET XMLs\n"
            "using StringId matches from SOURCE.\n\n"
            f"Source: {src}\nTarget: {tgt}\n\nProceed?",
        ):
            return

        def work():
            self._log_header("Replace StrOrigin by StringId")
            self.set_progress(5)
            files, locstrs, errs = xml_tools_engine.replace_strorigin_by_stringid(
                src, tgt, log_fn=self.log,
                progress_fn=lambda v: self.set_progress(5 + v * 0.9))
            self.log(
                f"Done: {files} file(s) updated, "
                f"{locstrs:,} LocStr(s) edited, {errs} error(s).",
                "success" if errs == 0 else "warning",
            )

        self.run_in_thread(work)
