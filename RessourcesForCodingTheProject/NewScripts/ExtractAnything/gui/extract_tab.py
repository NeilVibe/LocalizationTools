"""Simple extraction tab – extract all LocStr entries from a folder."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import config
from core.excel_writer import write_extraction_excel
from core.input_parser import parse_input_folder
from core.validators import validate_xml_source_folder
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class ExtractTab(BaseTab):
    TAB_TITLE = "Extract"

    def _build_ui(self) -> None:
        src = ttk.LabelFrame(self.frame, text="Source Folder (XML / Excel)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Source", log_fn=self.log)))

        # Category filter
        cat_frame = ttk.LabelFrame(self.frame, text="Category Filter")
        cat_frame.pack(fill=tk.X, padx=5, pady=2)
        self._cat_var = tk.StringVar(value=config.CATEGORY_FILTERS[0])
        ttk.Label(cat_frame, text="Category:").pack(side=tk.LEFT, padx=(5, 2), pady=5)
        ttk.Combobox(cat_frame, textvariable=self._cat_var,
                      values=config.CATEGORY_FILTERS, state="readonly",
                      width=20).pack(side=tk.LEFT, padx=2, pady=5)

        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="Extracts all LocStr entries from the source folder.\n"
                             "Use Path Filter (bottom bar) and Category Filter to narrow results.\n"
                             "Outputs Excel + XML per language.",
                  wraplength=500, justify=tk.LEFT).pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Extract Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        if not src:
            self.log("Source folder is required.", "error")
            return

        cat_filter = self._cat_var.get()

        def work():
            self._log_header("Simple Extraction")
            self.set_progress(5)

            # Always try EXPORT index (for category column); required when filtering
            need_filter = cat_filter != config.CATEGORY_FILTERS[0]
            category_map: dict[str, str] = {}

            idx = self.get_export_index(
                lambda cur, tot: self.set_progress(5 + cur * 15 // max(tot, 1))
            )
            if idx.is_built:
                category_map = idx.category_map
                self.log(f"EXPORT index: {len(category_map):,} categories")
            elif need_filter:
                self.log("EXPORT index required for category filtering.", "error")
                return
            else:
                self.log("EXPORT index not available — Category column will be empty.", "warning")

            self.set_progress(20)

            # Parse source folder
            result = parse_input_folder(
                Path(src),
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(20 + v * 0.50),
            )

            if not result:
                self.log("No entries found in source folder.", "warning")
                return

            self.set_progress(72)

            # Apply category filter
            if need_filter:
                if not category_map:
                    self.log("EXPORT index has no category data. Filter has no effect.", "warning")
                else:
                    is_script = cat_filter == "SCRIPT only"
                    for lang in list(result.keys()):
                        filtered = []
                        for e in result[lang]:
                            cat = category_map.get(e["string_id"].lower(), "")
                            in_script = cat in config.SCRIPT_CATEGORIES
                            if (is_script and in_script) or (not is_script and not in_script):
                                e["category"] = cat
                                filtered.append(e)
                        if filtered:
                            result[lang] = filtered
                        else:
                            del result[lang]
                    self.log(f"Category filter: {cat_filter}")

            self.set_progress(78)

            # Apply path filter
            if self.app.path_filter_active:
                self.log(f"Applying path filter ({self.app.path_filter_count} paths)...")
                for lang in list(result.keys()):
                    result[lang] = self.filter_entries_by_path(result[lang])
                    if not result[lang]:
                        del result[lang]

            if not result:
                self.log("No entries remain after filtering.", "info")
                return

            self.set_progress(85)

            # Write output
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"extract_{ts}"

            total = 0
            for lang, entries in sorted(result.items()):
                # Populate category from EXPORT index (best-effort)
                if category_map:
                    for e in entries:
                        e.setdefault("category", category_map.get(e["string_id"].lower(), ""))

                xlsx_path = out_dir / f"EXTRACT_{lang}.xlsx"
                write_extraction_excel(
                    xlsx_path, entries,
                    columns=[
                        ("string_id", "StringID", 35),
                        ("str_origin", "StrOrigin", 45),
                        ("str_value", "Str", 60),
                        ("category", "Category", 14),
                    ],
                    sheet_name="Extracted Strings",
                    header_bg="#1B5E20",
                    sort_key=lambda e: e["string_id"].lower(),
                )

                xml_path = out_dir / f"EXTRACT_{lang}.xml"
                write_locstr_xml(xml_path, entries, sort_key=lambda e: e["string_id"].lower())

                total += len(entries)
                self.log(f"  {lang}: {len(entries):,} entries")

            self.set_progress(98)
            self.log(f"Total: {total:,} entries across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)
