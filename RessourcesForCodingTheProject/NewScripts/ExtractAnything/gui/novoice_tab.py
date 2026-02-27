"""No-Voice extraction tab."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import config
from core import novoice_engine
from core.excel_writer import write_extraction_excel
from core.validators import validate_xml_source_folder
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)


class NoVoiceTab(BaseTab):
    TAB_TITLE = "No-Voice"

    def _build_ui(self) -> None:
        src = ttk.LabelFrame(self.frame, text="Source Folder (XML / Excel)")
        src.pack(fill=tk.X, padx=5, pady=(5, 2))
        self._src_var = tk.StringVar()
        self._make_path_row(src, "Folder:", self._src_var,
                            lambda: self.browse_folder(
                                self._src_var, "Select source folder",
                                on_selected=lambda p: validate_xml_source_folder(
                                    p, self.app.loc_folder, label="Source", log_fn=self.log)))

        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="Extracts SCRIPT-type LocStr entries without SoundEventName.\n"
                             "Requires EXPORT folder to be set (for category + voiced data).",
                  wraplength=500, justify=tk.LEFT).pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Extract No-Voice Strings", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        if not src:
            self.log("Source folder is required.", "error")
            return

        def work():
            self._log_header("No-Voice Extraction")
            self.set_progress(5)

            idx = self.get_export_index(
                lambda cur, tot: self.set_progress(5 + cur * 20 // max(tot, 1))
            )
            if not idx.is_built:
                self.log("EXPORT index required for No-Voice extraction.", "error")
                return

            self.log(f"EXPORT index: {len(idx.category_map):,} categories, "
                     f"{len(idx.voiced_sids):,} voiced SIDs")

            result = novoice_engine.extract_novoice_folder(
                Path(src),
                category_map=idx.category_map,
                voiced_sids=idx.voiced_sids,
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
                self.log("No unvoiced SCRIPT entries found.", "info")
                return

            self.set_progress(92)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = config.OUTPUT_DIR / f"novoice_script_{ts}"

            total = 0
            for lang, entries in sorted(result.items()):
                # Add empty correction field
                for e in entries:
                    e.setdefault("correction", "")
                    e.setdefault("category", idx.category_map.get(e["string_id"].lower(), ""))

                # Excel with Correction column
                xlsx_path = out_dir / f"NOVOICE_{lang}.xlsx"
                write_extraction_excel(
                    xlsx_path, entries,
                    columns=[
                        ("string_id", "StringID", 35),
                        ("str_origin", "StrOrigin", 45),
                        ("str_value", "Str", 60),
                        ("correction", "Correction", 40),
                        ("category", "Category", 14),
                    ],
                    sheet_name="No-Voice Script Strings",
                    header_bg="#4A6741",
                    sort_key=lambda e: e["string_id"].lower(),
                    extra_formats={"correction": {"bg_color": "#FFF9C4"}},
                )

                # XML
                xml_path = out_dir / f"NOVOICE_{lang}.xml"
                write_locstr_xml(xml_path, entries, sort_key=lambda e: e["string_id"].lower())

                total += len(entries)
                self.log(f"  {lang}: {len(entries):,} entries")

            self.log(f"Total: {total:,} entries across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)
