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
    GAMEDATA_EXCLUSION,
    KNOWN_BRANCHES,
    VOICE_RECORDING_FOLDER,
    get_audio_folder,
)
from exporter import (
    parse_language_file,
    discover_language_files,
    build_stringid_category_index,
    build_stringid_filename_index,
    load_cluster_config,
    write_language_excel,
)
from exporter.xml_parser import build_stringid_soundevent_map
from utils.language_utils import should_include_english_column, LANGUAGE_NAMES as LANG_DISPLAY
from utils.vrs_ordering import VRSOrderer
from utils.audio_utils import build_wem_index
from reports import ReportGenerator, ExcelReportWriter

logger = logging.getLogger(__name__)

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Language Data Exporter v4.2"
WINDOW_WIDTH = 850
WINDOW_HEIGHT = 580

KNOWN_DRIVES = ["D", "E", "F"]

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
        self.root.minsize(750, 560)
        self.root.resizable(True, True)

        # Language checkbox vars: lang_code -> BooleanVar
        self.lang_vars: dict[str, tk.BooleanVar] = {}
        self.all_var = tk.BooleanVar(value=True)

        # Export mode: "No Script" | "Full Export" | "Script Only"
        self.export_mode_var = tk.StringVar(value="No Script")

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
        """Build branch + drive selector row."""
        frame = ttk.Frame(self.root)
        frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 5))

        # Branch
        ttk.Label(frame, text="Branch:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        self.branch_var = tk.StringVar(value=config.get_branch())
        branch_combo = ttk.Combobox(frame, textvariable=self.branch_var,
                                    values=KNOWN_BRANCHES, width=20)
        branch_combo.pack(side="left", padx=5)
        branch_combo.bind("<<ComboboxSelected>>", self._on_branch_change)
        branch_combo.bind("<Return>", self._on_branch_change)

        ttk.Separator(frame, orient="vertical").pack(side="left", fill="y", padx=10)

        # Drive
        ttk.Label(frame, text="Drive:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        self.drive_var = tk.StringVar(value=config.get_drive())
        drive_combo = ttk.Combobox(frame, textvariable=self.drive_var,
                                   values=KNOWN_DRIVES, width=5)
        drive_combo.pack(side="left", padx=5)
        drive_combo.bind("<<ComboboxSelected>>", self._on_drive_change)
        drive_combo.bind("<Return>", self._on_drive_change)

        self.selector_status = ttk.Label(
            frame,
            text=f"Branch: {config.get_branch()}  Drive: {config.get_drive()}",
            font=("Arial", 9),
            foreground="green"
        )
        self.selector_status.pack(side="left", padx=10)

    def _on_branch_change(self, event=None):
        """Handle branch selection change."""
        new_branch = self.branch_var.get().strip()
        if not new_branch:
            return
        config.update_branch(new_branch)
        self.selector_status.config(
            text=f"Branch: {new_branch}  Drive: {config.get_drive()}",
            foreground="green"
        )
        self._update_path_labels()

    def _on_drive_change(self, event=None):
        """Handle drive letter selection change."""
        new_drive = self.drive_var.get().strip()
        if not new_drive:
            return
        config.update_drive(new_drive)  # sanitizes internally
        self.selector_status.config(
            text=f"Branch: {config.get_branch()}  Drive: {config.get_drive()}",
            foreground="green"
        )
        self._update_path_labels()

    def _update_path_labels(self):
        """Refresh path labels after branch/drive change."""
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
        """Build action section: export mode selector + 2 buttons."""
        section = ttk.LabelFrame(self.root, text="Actions", padding=10)
        section.grid(row=4, column=0, sticky="ew", padx=15, pady=5)

        # Export mode selector (replaces old Include Script checkbox)
        mode_frame = ttk.Frame(section)
        mode_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(mode_frame, text="Export Mode:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

        self.export_mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.export_mode_var,
            values=["No Script", "Full Export", "Script Only"],
            state="readonly",
            width=14,
        )
        self.export_mode_combo.pack(side="left", padx=5)

        self.export_mode_hint = ttk.Label(
            mode_frame,
            text="Excludes Script/Dialog for all languages",
            font=("Arial", 8),
            foreground="gray",
        )
        self.export_mode_hint.pack(side="left", padx=(10, 0))
        self.export_mode_combo.bind("<<ComboboxSelected>>", self._on_export_mode_change)

        # Buttons
        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x")

        self.btn_excel = ttk.Button(
            btn_frame,
            text="Generate Excel Language Data",
            command=self._generate_language_excels,
            width=32
        )
        self.btn_excel.pack(side="left", padx=10, ipady=8)

        self.btn_report = ttk.Button(
            btn_frame,
            text="Generate Word Count Report",
            command=self._generate_report,
            width=32
        )
        self.btn_report.pack(side="left", padx=10, ipady=8)

    def _on_export_mode_change(self, event=None):
        """Update hint label when export mode changes."""
        mode = self.export_mode_var.get()
        hints = {
            "No Script": "Excludes Script/Dialog for all languages",
            "Full Export": "All categories included for all languages",
            "Script Only": "Only Sequencer/Dialog lines (all languages)",
        }
        self.export_mode_hint.config(text=hints.get(mode, ""))

    def _set_buttons_enabled(self, enabled: bool):
        """Enable or disable action buttons and export mode during generation."""
        state = "normal" if enabled else "disabled"
        combo_state = "readonly" if enabled else "disabled"
        self.btn_excel.config(state=state)
        self.btn_report.config(state=state)
        self.export_mode_combo.config(state=combo_state)

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
        export_mode = self.export_mode_var.get()

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
                filename_index = build_stringid_filename_index(export_folder)

                # Load VRS ordering (always active, all modes)
                vrs_orderer = VRSOrderer(config.VOICE_RECORDING_FOLDER)
                if vrs_orderer.load():
                    logger.info("Loaded %d EventNames for VRS ordering", vrs_orderer.total_events)
                else:
                    logger.warning("VRS not loaded - STORY strings won't be ordered")

                # Build StringID -> SoundEventName mapping
                stringid_to_soundevent = build_stringid_soundevent_map(export_folder)

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

                is_script = export_mode == "Script Only"

                # Build WEM index per-language for Script Only mode
                # Cache to avoid re-scanning same folder for multiple languages
                wem_cache: dict[str, set] = {}

                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)
                    display_name = LANG_DISPLAY.get(lang_code.lower(), lang_code.upper())
                    prefix = "ScriptData" if is_script else "LanguageData"
                    output_file = OUTPUT_FOLDER / f"{prefix}_{display_name}.xlsx"

                    include_english = should_include_english_column(lang_code)
                    excluded_categories = None
                    if is_script:
                        excluded_categories = GAMEDATA_EXCLUSION
                    elif export_mode == "No Script":
                        excluded_categories = DIALOG_SEQUENCER_EXCLUSION

                    # Build WEM index for this language (cached)
                    wem_index = None
                    if is_script:
                        audio_folder = get_audio_folder(lang_code)
                        audio_key = str(audio_folder)
                        if audio_key not in wem_cache:
                            wem_cache[audio_key] = build_wem_index(audio_folder)
                        wem_index = wem_cache[audio_key]

                    write_language_excel(
                        lang_code=lang_code,
                        lang_data=lang_data,
                        eng_lookup=eng_lookup,
                        category_index=category_index,
                        output_path=output_file,
                        include_english=include_english,
                        default_category=cluster_cfg.get("default_category", "Uncategorized"),
                        vrs_orderer=vrs_orderer,
                        stringid_to_soundevent=stringid_to_soundevent,
                        excluded_categories=excluded_categories,
                        filename_index=filename_index,
                        is_script_mode=is_script,
                        wem_index=wem_index,
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
