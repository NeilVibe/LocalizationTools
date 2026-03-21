"""
TMX Tools Tab — Tab 3 in QuickTranslate.

Section 1: MemoQ-TMX Conversion (auto language detection)
Section 2: TMX Cleaner -> Excel export
"""
from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from core.tmx_tools import convert_to_memoq_tmx, clean_and_convert_to_excel

logger = logging.getLogger(__name__)


class TMXToolsTab(tk.Frame):
    """TMX Tools tab with conversion and cleaning sections."""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent, bg='#f0f0f0')
        self._mode = tk.StringVar(value="folder")
        self._path_var = tk.StringVar()
        self._status_var = tk.StringVar(value="No path selected")
        self._build_ui()

    def _build_ui(self):
        # ============================================================
        # Section 1: MemoQ-TMX Conversion
        # ============================================================
        conv_frame = tk.LabelFrame(
            self, text="MemoQ-TMX Conversion",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        conv_frame.pack(fill=tk.X, pady=(0, 12), padx=5)

        # Mode toggle (ExtractAnything pattern)
        mode_row = tk.Frame(conv_frame, bg='#f0f0f0')
        mode_row.pack(fill=tk.X, pady=(0, 6))
        tk.Radiobutton(mode_row, text="Folder", variable=self._mode,
                        value="folder", bg='#f0f0f0',
                        font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))
        tk.Radiobutton(mode_row, text="Single File", variable=self._mode,
                        value="file", bg='#f0f0f0',
                        font=('Segoe UI', 9)).pack(side=tk.LEFT)

        # Path row
        path_row = tk.Frame(conv_frame, bg='#f0f0f0')
        path_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(path_row, text="Path:", font=('Segoe UI', 9),
                 bg='#f0f0f0').pack(side=tk.LEFT)
        tk.Entry(path_row, textvariable=self._path_var,
                 font=('Segoe UI', 9),
                 width=50).pack(side=tk.LEFT, padx=(6, 6),
                                fill=tk.X, expand=True)
        tk.Button(path_row, text="Browse...", command=self._browse_path,
                  font=('Segoe UI', 9), cursor='hand2').pack(side=tk.LEFT)

        # Status label (detected languages)
        self._status_label = tk.Label(
            conv_frame, textvariable=self._status_var,
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            anchor='w', wraplength=500,
        )
        self._status_label.pack(fill=tk.X, pady=(0, 8))

        # Convert button
        tk.Button(conv_frame, text="Convert to MemoQ-TMX",
                  command=self._on_convert,
                  font=('Segoe UI', 9, 'bold'), bg='#4472C4', fg='white',
                  relief='flat', padx=14, pady=4,
                  cursor='hand2').pack(anchor='w')

        # ============================================================
        # Section 2: TMX Cleaner -> Excel
        # ============================================================
        clean_frame = tk.LabelFrame(
            self, text="TMX Cleaner -> Excel",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        clean_frame.pack(fill=tk.X, pady=(0, 8), padx=5)

        desc = tk.Label(
            clean_frame,
            text="Select a TMX file to clean all CAT tool markup and export "
                 "to Excel (3 columns: StrOrigin, Correction, StringID).",
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            wraplength=500, justify='left',
        )
        desc.pack(fill=tk.X, pady=(0, 8))

        tk.Button(clean_frame, text="Select TMX -> Clean & Export to Excel",
                  command=self._on_clean_to_excel,
                  font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                  relief='flat', padx=14, pady=4,
                  cursor='hand2').pack(anchor='w')

    # ------------------------------------------------------------------
    # Section 1: Browse + Convert
    # ------------------------------------------------------------------
    def _browse_path(self):
        if self._mode.get() == "folder":
            path = filedialog.askdirectory(
                title="Select folder with XML/Excel files")
        else:
            path = filedialog.askopenfilename(
                title="Select XML or Excel file",
                filetypes=[("XML files", "*.xml"),
                           ("Excel files", "*.xlsx;*.xls"),
                           ("All files", "*.*")])
        if path:
            self._path_var.set(path)
            self._scan_and_update_status(path)

    def _scan_and_update_status(self, path: str):
        """Scan path for languages and update status label."""
        try:
            from pathlib import Path as P
            from core.source_scanner import scan_source_for_languages
            scan = scan_source_for_languages(P(path))
            if scan.lang_files:
                parts = [
                    f"{k.upper()} ({len(v)} files)"
                    for k, v in sorted(scan.lang_files.items())
                ]
                self._status_var.set(f"Detected: {', '.join(parts)}")
                self._status_label.config(fg='#2d7d2d')
            else:
                msg = "No languages detected"
                if scan.unrecognized:
                    msg += f" ({len(scan.unrecognized)} unrecognized items)"
                self._status_var.set(msg)
                self._status_label.config(fg='#cc3333')
        except Exception as exc:
            self._status_var.set(f"Scan error: {exc}")
            self._status_label.config(fg='#cc3333')

    def _on_convert(self):
        path = self._path_var.get()
        if not path:
            messagebox.showwarning("No Path",
                                   "Please select a file or folder first.")
            return

        logger.info("[TMX] Starting MemoQ-TMX conversion: %s", path)

        def _run():
            try:
                results = convert_to_memoq_tmx(path)
                if not results:
                    msg = (
                        "No languages detected -- nothing to convert.\n"
                        "Make sure files/folders have language suffixes "
                        "(e.g. FRE/, corrections_GER.xml)"
                    )
                    self.after(0, lambda: messagebox.showwarning(
                        "No Languages", msg))
                    return
                summary = []
                for lang, out, ok in results:
                    status = "OK" if ok else "FAILED"
                    summary.append(f"{lang}: {status}")
                msg = ("MemoQ-TMX conversion complete:\n\n"
                       + "\n".join(summary))
                created = [out for _, out, ok in results if ok]
                if created:
                    msg += (f"\n\nFiles created in:\n"
                            f"{os.path.dirname(created[0])}")
                self.after(0, lambda: messagebox.showinfo(
                    "MemoQ-TMX Complete", msg))
            except Exception as exc:
                err_msg = str(exc)
                logger.error("[TMX] Conversion failed: %s", err_msg,
                             exc_info=True)
                self.after(0, lambda em=err_msg: messagebox.showerror(
                    "TMX Error", f"Failed: {em}"))

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Section 2: TMX Cleaner -> Excel
    # ------------------------------------------------------------------
    def _on_clean_to_excel(self):
        fpath = filedialog.askopenfilename(
            title="Select TMX file to clean and convert to Excel",
            filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")]
        )
        if not fpath:
            return

        logger.info("[TMX Cleaner] Processing: %s", fpath)

        def _run():
            try:
                out = clean_and_convert_to_excel(fpath)
                self.after(0, lambda: messagebox.showinfo(
                    "TMX Cleaner", f"Excel exported:\n{out}"))
            except Exception as exc:
                err_msg = str(exc)
                logger.error("TMX Cleaner failed: %s", err_msg,
                             exc_info=True)
                self.after(0, lambda em=err_msg: messagebox.showerror(
                    "TMX Cleaner Error", f"Failed: {em}"))

        threading.Thread(target=_run, daemon=True).start()
