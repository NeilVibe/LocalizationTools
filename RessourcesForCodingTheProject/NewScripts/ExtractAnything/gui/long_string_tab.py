"""Long String extraction tab."""

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import config
from core import long_string_engine
from core.excel_writer import write_extraction_excel
from core.validators import validate_xml_source_folder
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class LongStringTab(BaseTab):
    TAB_TITLE = "Long String"

    def _build_ui(self) -> None:
        # Source folder
        src = ttk.LabelFrame(self.frame, text="Source Folder (XML / Excel)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Source", log_fn=self.log)))

        # Settings
        opt = ttk.LabelFrame(self.frame, text="Settings")
        opt.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(opt, text="Min visible chars:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self._min_chars_var = tk.IntVar(value=200)
        ttk.Spinbox(opt, from_=10, to=9999, textvariable=self._min_chars_var,
                     width=8).grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Action
        ttk.Button(self.frame, text="Extract Long Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        if not src:
            self.log("Source folder is required.", "error")
            return

        min_chars = self._min_chars_var.get()

        def work():
            self._log_header(f"Long String Extraction (>= {min_chars} chars)")
            self.set_progress(5)

            # Need EXPORT index for category + subfolder
            idx = self.get_export_index(
                lambda cur, tot: self.set_progress(5 + cur * 20 // max(tot, 1))
            )
            if not idx.is_built:
                self.log("EXPORT index required for category filtering.", "warning")

            result = long_string_engine.extract_long_strings_folder(
                Path(src),
                min_chars=min_chars,
                category_map=idx.category_map if idx.is_built else None,
                subfolder_map=idx.subfolder_map if idx.is_built else None,
                log_fn=self.log,
                progress_fn=lambda v: self.set_progress(25 + v * 0.65),
            )

            if self.app.path_filter_active:
                self.log(f"Applying path filter ({self.app.path_filter_count} paths)...")
                for lang in list(result.keys()):
                    result[lang] = self.filter_entries_by_path(result[lang])
                    if not result[lang]:
                        del result[lang]

            if not result:
                self.log("No long strings found.", "info")
                return

            self.set_progress(92)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"long_strings_{min_chars}chars_{ts}"

            total = 0
            for lang, entries in sorted(result.items()):
                # Excel
                xlsx_path = out_dir / f"{lang}_script_long_strings.xlsx"
                write_extraction_excel(
                    xlsx_path, entries,
                    columns=[
                        ("string_id", "StringID", 35),
                        ("str_origin", "StrOrigin", 45),
                        ("str_value", "Str", 60),
                        ("char_count", "CharCount", 12),
                    ],
                    sheet_name="SCRIPT Long Strings",
                    header_bg="#2E4057",
                    # No sort_key — engine already sorts descending by char_count
                )

                # XML
                xml_path = out_dir / f"{lang}_script_long_strings.xml"
                write_locstr_xml(xml_path, entries)

                total += len(entries)
                self.log(f"  {lang}: {len(entries):,} entries")

            self.log(f"Total: {total:,} entries across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)
