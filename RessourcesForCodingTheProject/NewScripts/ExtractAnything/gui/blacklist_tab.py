"""Blacklist extraction tab."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import config
from core import blacklist_engine
from core.excel_reader import read_blacklist_from_excel
from core.excel_writer import write_blacklist_excel
from core.language_utils import discover_valid_codes
from core.validators import (
    validate_blacklist_excel,
    validate_blacklist_folder,
    validate_xml_source_folder,
)
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class BlacklistTab(BaseTab):
    TAB_TITLE = "Blacklist"

    def _build_ui(self) -> None:
        # Blacklist source
        bl = ttk.LabelFrame(self.frame, text="Blacklist Source (Excel)")
        bl.pack(fill=tk.X, padx=5, pady=(5, 2))

        self._bl_file_var = tk.StringVar()
        self._make_path_row(bl, "File:", self._bl_file_var,
                            lambda: self.browse_file(
                                self._bl_file_var, "Select blacklist Excel",
                                [("Excel", "*.xlsx"), ("All", "*.*")],
                                on_selected=lambda p: validate_blacklist_excel(
                                    p, self.app.loc_folder, log_fn=self.log)))

        self._bl_folder_var = tk.StringVar()
        self._make_path_row(bl, "Or folder:", self._bl_folder_var,
                            lambda: self.browse_folder(
                                self._bl_folder_var, "Select blacklist folder",
                                on_selected=lambda p: validate_blacklist_folder(
                                    p, self.app.loc_folder, log_fn=self.log)),
                            row=1)

        # Target folder
        tgt = ttk.LabelFrame(self.frame, text="Target Folder (XML / Excel)")
        tgt.pack(fill=tk.X, padx=5, pady=2)
        self._tgt_var = tk.StringVar()
        self._make_path_row(tgt, "Folder:", self._tgt_var,
                            lambda: self.browse_folder(
                                self._tgt_var, "Select target folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Target", log_fn=self.log)))

        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="Blacklist Excel: columns = language codes (ENG, FRE, etc.),\n"
                             "rows = blacklisted terms. LOC folder needed for language validation.",
                  wraplength=500, justify=tk.LEFT).pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Search Blacklist", command=self._run).pack(pady=10)

    def _run(self) -> None:
        bl_file = self._bl_file_var.get().strip()
        bl_folder = self._bl_folder_var.get().strip()
        tgt = self._tgt_var.get().strip()

        if not tgt:
            self.log("Target folder is required.", "error")
            return
        if not bl_file and not bl_folder:
            self.log("Blacklist file or folder is required.", "error")
            return

        def work():
            self._log_header("Blacklist Search")
            self.set_progress(5)

            # Discover valid language codes from LOC
            loc = self.app.loc_folder
            if not loc or not loc.is_dir():
                self.log("LOC folder not set — language validation skipped.", "warning")
                valid_codes: set[str] = set()
            else:
                valid_codes = set(discover_valid_codes(loc).keys())
                self.log(f"Valid language codes: {', '.join(sorted(valid_codes))}")

            self.set_progress(10)

            # Load blacklist
            blacklist: dict[str, list[str]] = {}
            all_warnings: list[str] = []

            if bl_file:
                self.log(f"Loading blacklist: {Path(bl_file).name}")
                bl, warns = read_blacklist_from_excel(Path(bl_file), valid_codes)
                blacklist.update(bl)
                all_warnings.extend(warns)
            elif bl_folder:
                self.log(f"Loading blacklist folder: {Path(bl_folder).name}")
                xlsx_files = sorted(Path(bl_folder).rglob("*.xlsx"))
                for i, xlsx in enumerate(xlsx_files):
                    if xlsx.name.startswith("~$"):
                        continue
                    self.log(f"  {xlsx.name}")
                    bl, warns = read_blacklist_from_excel(xlsx, valid_codes)
                    for lang, terms in bl.items():
                        blacklist.setdefault(lang, []).extend(terms)
                    all_warnings.extend(warns)

            self.set_progress(20)

            for w in all_warnings:
                self.log(f"  Warning: {w}", "warning")

            total_terms = sum(len(v) for v in blacklist.values())
            self.log(f"Loaded {total_terms:,} terms across {len(blacklist)} languages.")

            if not blacklist:
                self.log("No blacklist terms loaded.", "warning")
                return

            # Per-language term counts
            for lang in sorted(blacklist):
                self.log(f"  {lang}: {len(blacklist[lang]):,} terms")

            # Search
            result = blacklist_engine.search_blacklist_folder(
                Path(tgt), blacklist,
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(20 + v * 0.7),
            )

            if self.app.path_filter_active:
                self.log(f"Applying path filter ({self.app.path_filter_count} paths)...")
                for lang in list(result.keys()):
                    result[lang] = self.filter_entries_by_path(result[lang])
                    if not result[lang]:
                        del result[lang]

            if not result:
                self.log("No blacklist matches found.", "info")
                return

            self.set_progress(92)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"blacklist_{ts}"

            total = 0
            for lang, matches in sorted(result.items()):
                # Excel
                xlsx_path = out_dir / f"BLACKLIST_{lang}.xlsx"
                write_blacklist_excel(xlsx_path, matches)

                # XML (deduplicated by SID)
                xml_path = out_dir / f"BLACKLIST_{lang}.xml"
                write_locstr_xml(xml_path, matches, dedup_by_sid=True,
                                 sort_key=lambda e: e["string_id"].lower())

                total += len(matches)
                self.log(f"  {lang}: {len(matches):,} matches")

            self.log(f"Total: {total:,} matches across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)
