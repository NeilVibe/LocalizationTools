"""
Language Data Exporter GUI - Simplified Application.

Tkinter GUI for the LanguageDataExporter tool with:
1. Branch selector (auto-resolves LOC/EXPORT/VRS paths from settings.json)
2. Language selection (ALL checkbox or individual)
3. Two functions: Generate Excel Language Data + Generate Word Count Report
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import logging
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from config import (
    OUTPUT_FOLDER,
    CLUSTER_CONFIG,
    DIALOG_SEQUENCER_EXCLUSION,
    LANGUAGES_WITH_DIALOG_EXCLUSION,
    KNOWN_BRANCHES,
)
from exporter import (
    parse_language_file,
    discover_language_files,
    build_stringid_category_index,
    load_cluster_config,
    write_language_excel,
)
from utils.language_utils import should_include_english_column, LANGUAGE_NAMES as LANG_DISPLAY
from reports import ReportGenerator, ExcelReportWriter

logger = logging.getLogger(__name__)

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Language Data Exporter v4.0"
WINDOW_WIDTH = 850
WINDOW_HEIGHT = 580

# Languages to EXCLUDE (Korean is source, not target)
EXCLUDED_LANGUAGES = {"kor"}

# Fixed display order for language checkboxes (13 target languages)
LANGUAGE_ORDER = [
    "eng", "fre", "ger", "ita", "jpn", "pol",
    "por-br", "rus", "spa-es", "spa-mx", "tur", "zho-cn", "zho-tw"
]


class LanguageDataExporterGUI:
    """Main GUI application for Language Data Exporter."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(750, 500)
        self.root.resizable(True, True)

        # Language checkbox vars: lang_code -> BooleanVar
        self.lang_vars: dict[str, tk.BooleanVar] = {}
        self.all_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._check_paths()

    def _build_ui(self):
        """Build the main UI layout."""
        self.root.columnconfigure(0, weight=1)

        # Row 0: Title
        tk.Label(
            self.root,
            text="Language Data Exporter",
            font=("Arial", 18, "bold")
        ).grid(row=0, column=0, pady=15)

        # Row 1: Branch Selector
        self._build_branch_selector()

        # Row 2: Path Info
        self._build_path_info_section()

        # Row 3: Language Selection
        self._build_language_section()

        # Row 4: Action Buttons
        self._build_actions_section()

        # Row 5: Status
        self._build_status_section()

    # =========================================================================
    # BRANCH SELECTOR
    # =========================================================================

    def _build_branch_selector(self):
        """Build branch selector (QACompiler style)."""
        frame = ttk.Frame(self.root)
        frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 5))

        ttk.Label(frame, text="Branch:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        self.branch_var = tk.StringVar(value=config.get_branch())
        combo = ttk.Combobox(frame, textvariable=self.branch_var,
                             values=KNOWN_BRANCHES, width=25)
        combo.pack(side="left", padx=5)
        combo.bind("<<ComboboxSelected>>", self._on_branch_change)
        combo.bind("<Return>", self._on_branch_change)

        self.branch_status = ttk.Label(frame, text="", font=("Arial", 9))
        self.branch_status.pack(side="left", padx=10)

    def _on_branch_change(self, event=None):
        """Handle branch selection change."""
        new_branch = self.branch_var.get().strip()
        if not new_branch:
            return
        config.update_branch(new_branch)
        self.branch_status.config(text=f"Branch set to: {new_branch}", foreground="green")
        self._update_path_labels()

    def _update_path_labels(self):
        """Refresh path labels after branch change."""
        self.loc_path_label.config(text=str(config.LOC_FOLDER))
        self.export_path_label.config(text=str(config.EXPORT_FOLDER))
        self.vrs_path_label.config(text=str(config.VOICE_RECORDING_FOLDER))
        self._check_paths()

    # =========================================================================
    # PATH INFO SECTION
    # =========================================================================

    def _build_path_info_section(self):
        """Build path information section (read-only display)."""
        section = ttk.LabelFrame(self.root, text="Configured Paths", padding=10)
        section.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(1, weight=1)

        # LOC Folder
        ttk.Label(section, text="LOC Folder:").grid(row=0, column=0, sticky="w", padx=5)
        self.loc_path_label = ttk.Label(section, text=str(config.LOC_FOLDER), foreground="blue")
        self.loc_path_label.grid(row=0, column=1, sticky="w", padx=5)
        self.loc_status = ttk.Label(section, text="")
        self.loc_status.grid(row=0, column=2, sticky="w", padx=5)

        # EXPORT Folder
        ttk.Label(section, text="EXPORT Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.export_path_label = ttk.Label(section, text=str(config.EXPORT_FOLDER), foreground="blue")
        self.export_path_label.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.export_status = ttk.Label(section, text="")
        self.export_status.grid(row=1, column=2, sticky="w", padx=5, pady=5)

        # VRS Folder
        ttk.Label(section, text="VRS Folder:").grid(row=2, column=0, sticky="w", padx=5)
        self.vrs_path_label = ttk.Label(section, text=str(config.VOICE_RECORDING_FOLDER), foreground="blue")
        self.vrs_path_label.grid(row=2, column=1, sticky="w", padx=5)
        self.vrs_status = ttk.Label(section, text="")
        self.vrs_status.grid(row=2, column=2, sticky="w", padx=5)

        # Output Folder
        ttk.Label(section, text="Output Folder:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(section, text=str(OUTPUT_FOLDER), foreground="blue").grid(
            row=3, column=1, sticky="w", padx=5, pady=5
        )

    def _check_paths(self):
        """Check if configured paths exist and update status labels."""
        self.loc_status.config(
            text="OK" if config.LOC_FOLDER.exists() else "NOT FOUND",
            foreground="green" if config.LOC_FOLDER.exists() else "red"
        )
        self.export_status.config(
            text="OK" if config.EXPORT_FOLDER.exists() else "NOT FOUND",
            foreground="green" if config.EXPORT_FOLDER.exists() else "red"
        )
        self.vrs_status.config(
            text="OK" if config.VOICE_RECORDING_FOLDER.exists() else "NOT FOUND",
            foreground="green" if config.VOICE_RECORDING_FOLDER.exists() else "red"
        )

    # =========================================================================
    # LANGUAGE SELECTION SECTION
    # =========================================================================

    def _build_language_section(self):
        """Build language selection section with ALL + individual checkboxes."""
        section = ttk.LabelFrame(self.root, text="Languages", padding=10)
        section.grid(row=3, column=0, sticky="ew", padx=15, pady=5)

        # ALL checkbox (spans both language rows so it's vertically centered)
        ttk.Checkbutton(
            section,
            text="ALL",
            variable=self.all_var,
            command=self._on_all_toggle
        ).grid(row=0, column=0, rowspan=2, sticky="w", padx=(5, 10))

        ttk.Separator(section, orient="vertical").grid(
            row=0, column=1, rowspan=2, sticky="ns", padx=(5, 8)
        )

        # Row 0: ENG FRE GER ITA JPN POL POR-BR
        row1_langs = LANGUAGE_ORDER[:7]
        for col_idx, lang in enumerate(row1_langs):
            var = tk.BooleanVar(value=True)
            self.lang_vars[lang] = var
            display = LANG_DISPLAY.get(lang, lang.upper())
            ttk.Checkbutton(
                section,
                text=display,
                variable=var,
                command=self._on_lang_toggle
            ).grid(row=0, column=col_idx + 2, sticky="w", padx=3)

        # Row 1: RUS SPA-ES SPA-MX TUR ZHO-CN ZHO-TW (offset by 1 column to align under row 1 start)
        row2_langs = LANGUAGE_ORDER[7:]
        for col_idx, lang in enumerate(row2_langs):
            var = tk.BooleanVar(value=True)
            self.lang_vars[lang] = var
            display = LANG_DISPLAY.get(lang, lang.upper())
            ttk.Checkbutton(
                section,
                text=display,
                variable=var,
                command=self._on_lang_toggle
            ).grid(row=1, column=col_idx + 2, sticky="w", padx=3, pady=(5, 0))

    def _on_all_toggle(self):
        """ALL checkbox toggled — set all individual checkboxes to match."""
        state = self.all_var.get()
        for var in self.lang_vars.values():
            var.set(state)

    def _on_lang_toggle(self):
        """Individual language checkbox toggled — sync ALL checkbox state."""
        all_checked = all(var.get() for var in self.lang_vars.values())
        self.all_var.set(all_checked)

    def _get_selected_languages(self) -> list[str]:
        """Return list of currently checked language codes (in LANGUAGE_ORDER order)."""
        return [lang for lang in LANGUAGE_ORDER if lang in self.lang_vars and self.lang_vars[lang].get()]

    # =========================================================================
    # ACTIONS SECTION
    # =========================================================================

    def _build_actions_section(self):
        """Build 2-button action section."""
        section = ttk.LabelFrame(self.root, text="Actions", padding=10)
        section.grid(row=4, column=0, sticky="ew", padx=15, pady=5)

        self.btn_excel = ttk.Button(
            section,
            text="Generate Excel Language Data",
            command=self._generate_language_excels,
            width=32
        )
        self.btn_excel.pack(side="left", padx=10, ipady=8)

        self.btn_report = ttk.Button(
            section,
            text="Generate Word Count Report",
            command=self._generate_report,
            width=32
        )
        self.btn_report.pack(side="left", padx=10, ipady=8)

    def _set_buttons_enabled(self, enabled: bool):
        """Enable or disable both action buttons."""
        state = "normal" if enabled else "disabled"
        self.btn_excel.config(state=state)
        self.btn_report.config(state=state)

    # =========================================================================
    # STATUS SECTION
    # =========================================================================

    def _build_status_section(self):
        """Build status display section."""
        section = ttk.LabelFrame(self.root, text="Status", padding=10)
        section.grid(row=5, column=0, sticky="ew", padx=15, pady=10)
        section.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(section, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", pady=5)

        self.status_label = ttk.Label(section, text="Ready")
        self.status_label.grid(row=1, column=0, sticky="w", pady=5)

    # =========================================================================
    # GENERATE EXCEL LANGUAGE DATA
    # =========================================================================

    def _generate_language_excels(self):
        """Generate individual Excel files for each selected language."""
        loc_folder = config.LOC_FOLDER
        export_folder = config.EXPORT_FOLDER

        if not loc_folder.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_folder}")
            return
        if not export_folder.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{export_folder}")
            return

        selected_langs = self._get_selected_languages()
        if not selected_langs:
            messagebox.showerror("Error", "No languages selected")
            return

        self._set_status(f"Generating {len(selected_langs)} language Excel files...")
        self.progress["value"] = 0
        self._set_buttons_enabled(False)

        def generate():
            try:
                OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

                cluster_cfg = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    export_folder,
                    cluster_cfg,
                    cluster_cfg.get("default_category", "Uncategorized")
                )

                all_lang_files = discover_language_files(loc_folder)

                # Parse English for cross-reference
                eng_lookup = {}
                if "eng" in all_lang_files:
                    eng_data = parse_language_file(all_lang_files["eng"])
                    eng_lookup = {row["string_id"]: row["str"] for row in eng_data}

                # Filter to selected languages that actually exist in LOC folder
                lang_files = {
                    lang: all_lang_files[lang]
                    for lang in selected_langs
                    if lang in all_lang_files
                }

                total = len(lang_files)
                if total == 0:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "No matching language files found in LOC folder"
                    ))
                    self.root.after(0, lambda: self._set_status("Ready"))
                    self.root.after(0, lambda: self._set_buttons_enabled(True))
                    return

                skipped = [l for l in selected_langs if l not in all_lang_files]

                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)
                    display_name = LANG_DISPLAY.get(lang_code.lower(), lang_code.upper())
                    output_file = OUTPUT_FOLDER / f"LanguageData_{display_name}.xlsx"

                    include_english = should_include_english_column(lang_code)
                    excluded_categories = None
                    if lang_code.lower() in LANGUAGES_WITH_DIALOG_EXCLUSION:
                        excluded_categories = DIALOG_SEQUENCER_EXCLUSION

                    write_language_excel(
                        lang_code=lang_code,
                        lang_data=lang_data,
                        eng_lookup=eng_lookup,
                        category_index=category_index,
                        output_path=output_file,
                        include_english=include_english,
                        default_category=cluster_cfg.get("default_category", "Uncategorized"),
                        excluded_categories=excluded_categories,
                    )

                    progress = int((i + 1) / total * 100)
                    self.root.after(0, lambda p=progress: self._update_progress(p))

                skip_note = f"\n\nSkipped (not on disk): {', '.join(s.upper() for s in skipped)}" if skipped else ""
                self.root.after(0, lambda: self._set_status(
                    f"Generated {total} Excel files in {OUTPUT_FOLDER}"
                ))
                self.root.after(0, lambda: self._set_buttons_enabled(True))
                self.root.after(0, lambda n=skip_note: messagebox.showinfo(
                    "Success", f"Generated {total} files in:\n{OUTPUT_FOLDER}{n}"
                ))

            except Exception as ex:
                logger.exception("Language Excel generation failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Generation failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Generation failed"))
                self.root.after(0, lambda: self._set_buttons_enabled(True))

        threading.Thread(target=generate, daemon=True).start()

    # =========================================================================
    # GENERATE WORD COUNT REPORT
    # =========================================================================

    def _generate_report(self):
        """Generate comprehensive word count report for selected languages."""
        loc_folder = config.LOC_FOLDER
        export_folder = config.EXPORT_FOLDER

        if not loc_folder.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{loc_folder}")
            return
        if not export_folder.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{export_folder}")
            return

        selected_langs = self._get_selected_languages()
        if not selected_langs:
            messagebox.showerror("Error", "No languages selected")
            return

        self._set_status(f"Generating report for {len(selected_langs)} languages...")
        self.progress["value"] = 0
        self._set_buttons_enabled(False)

        def generate():
            try:
                OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

                cluster_cfg = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    export_folder,
                    cluster_cfg,
                    cluster_cfg.get("default_category", "Uncategorized")
                )

                all_lang_files = discover_language_files(loc_folder)

                # Filter to selected languages that actually exist in LOC folder
                lang_files = {
                    lang: all_lang_files[lang]
                    for lang in selected_langs
                    if lang in all_lang_files
                }

                total = len(lang_files)
                if total == 0:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", "No matching language files found in LOC folder"
                    ))
                    self.root.after(0, lambda: self._set_status("Ready"))
                    self.root.after(0, lambda: self._set_buttons_enabled(True))
                    return

                skipped = [l for l in selected_langs if l not in all_lang_files]

                language_data = {}
                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)
                    language_data[lang_code] = lang_data

                    progress = int((i + 1) / total * 70)
                    self.root.after(0, lambda p=progress: self._update_progress(p))

                generator = ReportGenerator(
                    category_index,
                    cluster_cfg.get("default_category", "Uncategorized")
                )
                report = generator.generate_full_report(language_data, LANG_DISPLAY)

                report_path = OUTPUT_FOLDER / "WordCountReport.xlsx"
                writer = ExcelReportWriter(report_path)
                writer.write_report(report)

                skip_note = f"\n\nSkipped (not on disk): {', '.join(s.upper() for s in skipped)}" if skipped else ""
                self.root.after(0, lambda: self._update_progress(100))
                self.root.after(0, lambda: self._set_status(f"Report generated: {report_path}"))
                self.root.after(0, lambda: self._set_buttons_enabled(True))
                self.root.after(0, lambda n=skip_note: messagebox.showinfo(
                    "Success", f"Report generated:\n{report_path}{n}"
                ))

            except Exception as ex:
                logger.exception("Report generation failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Generation failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Generation failed"))
                self.root.after(0, lambda: self._set_buttons_enabled(True))

        threading.Thread(target=generate, daemon=True).start()

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _update_progress(self, value: int):
        """Update progress bar value."""
        self.progress["value"] = value

    def _set_status(self, text: str):
        """Update status label."""
        self.status_label["text"] = text


def launch_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = LanguageDataExporterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
