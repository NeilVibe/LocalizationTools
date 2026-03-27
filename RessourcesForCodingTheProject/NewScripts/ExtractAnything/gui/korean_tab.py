"""Korean/Translation tab – filter entries by Korean presence in Str."""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

import config
from core.excel_writer import write_extraction_excel
from core.input_parser import parse_input_folder
from core.korean_filter_engine import filter_by_korean
from core.validators import validate_xml_source_folder
from core.xml_writer import write_locstr_xml
from .base_tab import BaseTab

logger = logging.getLogger(__name__)

_MODES = [
    ("Translated (Korean in Str)", "translated"),
    ("Untranslated (no Korean in Str)", "untranslated"),
]


class KoreanTab(BaseTab):
    TAB_TITLE = "Korean/Translation"

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

        # Mode selection
        mode_frame = ttk.LabelFrame(self.frame, text="Filter Mode")
        mode_frame.pack(fill=tk.X, padx=5, pady=2)
        self._mode_var = tk.StringVar(value="translated")
        for label, value in _MODES:
            ttk.Radiobutton(mode_frame, text=label, variable=self._mode_var,
                            value=value).pack(anchor="w", padx=10, pady=2)

        # Category filter
        cat_frame = ttk.LabelFrame(self.frame, text="Category Filter")
        cat_frame.pack(fill=tk.X, padx=5, pady=2)
        self._cat_var = tk.StringVar(value=config.CATEGORY_FILTERS[0])
        ttk.Label(cat_frame, text="Category:").pack(side=tk.LEFT, padx=(5, 2), pady=5)
        ttk.Combobox(cat_frame, textvariable=self._cat_var,
                      values=config.CATEGORY_FILTERS, state="readonly",
                      width=20).pack(side=tk.LEFT, padx=2, pady=5)

        # Info
        info = ttk.LabelFrame(self.frame, text="Info")
        info.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(info, text="Filter LocStr entries by Korean character presence in the Str attribute.\n"
                             "  Translated = Str contains Korean characters (work is done)\n"
                             "  Untranslated = Str has NO Korean characters (work needed)\n"
                             "Outputs Excel + XML per language.",
                  wraplength=500, justify=tk.LEFT).pack(padx=5, pady=5)

        ttk.Button(self.frame, text="Extract", command=self._run).pack(pady=10)

    def _run(self) -> None:
        src = self._src_var.get().strip()
        if not src:
            self.log("Source folder is required.", "error")
            return

        mode = self._mode_var.get()
        cat_filter = self._cat_var.get()

        def work():
            mode_label = "Translated (KR in Str)" if mode == "translated" else "Untranslated (no KR in Str)"
            self._log_header(f"Korean/Translation Filter — {mode_label}")
            self.set_progress(5)

            # EXPORT index (for category column + filtering)
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
                progress_fn=lambda v: self.set_progress(20 + v * 0.40),
            )

            if not result:
                self.log("No entries found in source folder.", "warning")
                return

            self.set_progress(62)

            # Apply Korean filter
            total_before = sum(len(v) for v in result.values())
            for lang in list(result.keys()):
                result[lang] = filter_by_korean(result[lang], mode=mode)
                if not result[lang]:
                    del result[lang]

            total_after = sum(len(v) for v in result.values())
            self.log(f"Korean filter ({mode_label}): {total_before:,} -> {total_after:,} entries")
            self.set_progress(70)

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
            tag = "translated" if mode == "translated" else "untranslated"
            out_dir = config.OUTPUT_DIR / f"korean_{tag}_{ts}"

            header_bg = "#1B5E20" if mode == "translated" else "#BF360C"

            total = 0
            for lang, entries in sorted(result.items()):
                if category_map:
                    for e in entries:
                        e.setdefault("category", category_map.get(e["string_id"].lower(), ""))

                label = f"KR_{tag.upper()}_{lang}"
                xlsx_path = out_dir / f"{label}.xlsx"
                write_extraction_excel(
                    xlsx_path, entries,
                    columns=[
                        ("string_id", "StringID", 35),
                        ("str_origin", "StrOrigin", 45),
                        ("str_value", "Str", 60),
                        ("category", "Category", 14),
                    ],
                    sheet_name=f"Korean {tag.title()}",
                    header_bg=header_bg,
                    sort_key=lambda e: e["string_id"].lower(),
                )

                xml_path = out_dir / f"{label}.xml"
                write_locstr_xml(xml_path, entries, sort_key=lambda e: e["string_id"].lower())

                total += len(entries)
                self.log(f"  {lang}: {len(entries):,} entries")

            self.set_progress(98)
            self.log(f"Total: {total:,} {tag} entries across {len(result)} languages -> {out_dir}", "success")

        self.run_in_thread(work)
