"""
Language Data Exporter GUI - Simplified Application.

Tkinter GUI for the LanguageDataExporter tool with:
1. Fixed paths from settings.json (drive selected at install)
2. One-click generation (ALL languages except KOR)
3. Progress tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import logging
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    LOC_FOLDER,
    EXPORT_FOLDER,
    OUTPUT_FOLDER,
    CLUSTER_CONFIG,
    TOSUBMIT_FOLDER,
    TRACKER_PATH,
    TRACKER_CATEGORIES,
    LOCDEV_FOLDER,
    DIALOG_SEQUENCER_EXCLUSION,
    LANGUAGES_WITH_DIALOG_EXCLUSION,
    ensure_tosubmit_folder,
)
from exporter import (
    parse_language_file,
    discover_language_files,
    build_stringid_category_index,
    load_cluster_config,
    write_language_excel,
    discover_submit_files,
    prepare_all_for_submit,
    merge_all_corrections,
    print_merge_report,
    analyze_patterns,
    generate_pattern_report,
)
from exporter.excel_writer import write_summary_excel
from utils.language_utils import should_include_english_column, LANGUAGE_NAMES as LANG_DISPLAY
from reports import ReportGenerator, ExcelReportWriter
from tracker import CorrectionTracker

logger = logging.getLogger(__name__)

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Language Data Exporter v3.0"
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 400

# Languages to EXCLUDE (Korean is source, not target)
EXCLUDED_LANGUAGES = {"kor"}


class LanguageDataExporterGUI:
    """Main GUI application for Language Data Exporter."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Build UI
        self._build_ui()

        # Show path status
        self._check_paths()

    def _build_ui(self):
        """Build the main UI layout."""
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # Title
        title_label = tk.Label(
            self.root,
            text="Language Data Exporter",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=15)

        # === Section 1: Path Info (Read-Only) ===
        self._build_path_info_section()

        # === Section 2: Export Actions ===
        self._build_export_section()

        # === Section 4: Status ===
        self._build_status_section()

    def _build_path_info_section(self):
        """Build path information section (read-only display)."""
        section = ttk.LabelFrame(self.root, text="Configured Paths (from settings.json)", padding=10)
        section.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(1, weight=1)

        # LOC Folder
        ttk.Label(section, text="LOC Folder:").grid(row=0, column=0, sticky="w", padx=5)
        loc_label = ttk.Label(section, text=str(LOC_FOLDER), foreground="blue")
        loc_label.grid(row=0, column=1, sticky="w", padx=5)
        self.loc_status = ttk.Label(section, text="")
        self.loc_status.grid(row=0, column=2, sticky="w", padx=5)

        # EXPORT Folder
        ttk.Label(section, text="EXPORT Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        export_label = ttk.Label(section, text=str(EXPORT_FOLDER), foreground="blue")
        export_label.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.export_status = ttk.Label(section, text="")
        self.export_status.grid(row=1, column=2, sticky="w", padx=5, pady=5)

        # Output Folder
        ttk.Label(section, text="Output Folder:").grid(row=2, column=0, sticky="w", padx=5)
        output_label = ttk.Label(section, text=str(OUTPUT_FOLDER), foreground="blue")
        output_label.grid(row=2, column=1, sticky="w", padx=5)

        # Note about languages
        note_frame = ttk.Frame(section)
        note_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Label(
            note_frame,
            text="All languages will be processed (excluding KOR which is the source language)",
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).pack(side="left")

    def _check_paths(self):
        """Check if configured paths exist."""
        if LOC_FOLDER.exists():
            self.loc_status.config(text="OK", foreground="green")
        else:
            self.loc_status.config(text="NOT FOUND", foreground="red")

        if EXPORT_FOLDER.exists():
            self.export_status.config(text="OK", foreground="green")
        else:
            self.export_status.config(text="NOT FOUND", foreground="red")

    def _build_export_section(self):
        """Build export actions section."""
        section = ttk.LabelFrame(self.root, text="Generate & Submit", padding=10)
        section.grid(row=2, column=0, sticky="ew", padx=15, pady=5)

        # Row 1: Generate buttons
        btn_frame1 = ttk.Frame(section)
        btn_frame1.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame1,
            text="Generate Word Count Report",
            command=self._generate_report,
            width=28
        ).pack(side="left", padx=5, ipady=8)

        ttk.Button(
            btn_frame1,
            text="Generate Language Excels",
            command=self._generate_language_excels,
            width=28
        ).pack(side="left", padx=5, ipady=8)

        # Row 2: Submit preparation button
        btn_frame2 = ttk.Frame(section)
        btn_frame2.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame2,
            text="Prepare For Submit",
            command=self._prepare_for_submit,
            width=28
        ).pack(side="left", padx=5, ipady=8)

        ttk.Button(
            btn_frame2,
            text="Open ToSubmit Folder",
            command=self._open_tosubmit_folder,
            width=28
        ).pack(side="left", padx=5, ipady=8)

        # Row 3: LOCDEV merge and Pattern Analysis buttons
        btn_frame3 = ttk.Frame(section)
        btn_frame3.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame3,
            text="Merge to LOCDEV",
            command=self._merge_to_locdev,
            width=28
        ).pack(side="left", padx=5, ipady=8)

        ttk.Button(
            btn_frame3,
            text="Analyze Code Patterns",
            command=self._analyze_code_patterns,
            width=28
        ).pack(side="left", padx=5, ipady=8)

    def _build_status_section(self):
        """Build status display section."""
        section = ttk.LabelFrame(self.root, text="Status", padding=10)
        section.grid(row=3, column=0, sticky="ew", padx=15, pady=10)
        section.columnconfigure(0, weight=1)

        # Progress bar
        self.progress = ttk.Progressbar(section, mode="determinate", length=400)
        self.progress.grid(row=0, column=0, sticky="ew", pady=5)

        # Status label
        self.status_label = ttk.Label(section, text="Ready")
        self.status_label.grid(row=1, column=0, sticky="w", pady=5)

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================

    def _get_target_languages(self):
        """Get all languages except excluded ones (KOR)."""
        if not LOC_FOLDER.exists():
            return []

        all_langs = discover_language_files(LOC_FOLDER)
        return [lang for lang in all_langs.keys() if lang.lower() not in EXCLUDED_LANGUAGES]

    def _generate_report(self):
        """Generate comprehensive word count report."""
        if not LOC_FOLDER.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{LOC_FOLDER}")
            return
        if not EXPORT_FOLDER.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{EXPORT_FOLDER}")
            return

        languages = self._get_target_languages()
        if not languages:
            messagebox.showerror("Error", "No language files found")
            return

        self._set_status(f"Generating report for {len(languages)} languages...")
        self.progress["value"] = 0

        def generate():
            try:
                # Ensure output folder exists
                OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

                # Load config and build category index
                config = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    EXPORT_FOLDER,
                    config,
                    config.get("default_category", "Uncategorized")
                )

                # Discover language files
                all_lang_files = discover_language_files(LOC_FOLDER)
                lang_files = {k: v for k, v in all_lang_files.items() if k.lower() not in EXCLUDED_LANGUAGES}

                # Parse all languages
                language_data = {}
                total = len(lang_files)

                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)
                    language_data[lang_code] = lang_data

                    progress = int((i + 1) / total * 70)
                    self.root.after(0, lambda p=progress: self._update_progress(p))

                # Generate word count report
                generator = ReportGenerator(
                    category_index,
                    config.get("default_category", "Uncategorized")
                )

                report = generator.generate_full_report(language_data, LANG_DISPLAY)

                report_path = OUTPUT_FOLDER / "WordCountReport.xlsx"
                writer = ExcelReportWriter(report_path)
                writer.write_report(report)

                self.root.after(0, lambda: self._update_progress(100))
                self.root.after(0, lambda: self._set_status(f"Report generated: {report_path}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Report generated:\n{report_path}"))

            except Exception as ex:
                logger.exception("Report generation failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror("Error", f"Generation failed: {err}"))
                self.root.after(0, lambda: self._set_status("Generation failed"))

        threading.Thread(target=generate, daemon=True).start()

    def _generate_language_excels(self):
        """Generate individual Excel files for each language."""
        if not LOC_FOLDER.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{LOC_FOLDER}")
            return
        if not EXPORT_FOLDER.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{EXPORT_FOLDER}")
            return

        languages = self._get_target_languages()
        if not languages:
            messagebox.showerror("Error", "No language files found")
            return

        self._set_status(f"Generating {len(languages)} language Excel files...")
        self.progress["value"] = 0

        def generate():
            try:
                # Ensure output folder exists
                OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

                # Load config and build category index
                config = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    EXPORT_FOLDER,
                    config,
                    config.get("default_category", "Uncategorized")
                )

                # Discover language files
                all_lang_files = discover_language_files(LOC_FOLDER)
                lang_files = {k: v for k, v in all_lang_files.items() if k.lower() not in EXCLUDED_LANGUAGES}

                # Parse English for cross-reference
                eng_lookup = {}
                if "eng" in all_lang_files:
                    eng_data = parse_language_file(all_lang_files["eng"])
                    eng_lookup = {row["string_id"]: row["str"] for row in eng_data}

                # Parse and generate for each language
                total = len(lang_files)

                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)

                    display_name = LANG_DISPLAY.get(lang_code.lower(), lang_code.upper())
                    output_file = OUTPUT_FOLDER / f"LanguageData_{display_name}.xlsx"

                    include_english = should_include_english_column(lang_code)

                    # Determine category exclusion for this language
                    # ENG and ZHO-CN exclude Dialog/Sequencer categories (voiced content)
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
                        default_category=config.get("default_category", "Uncategorized"),
                        excluded_categories=excluded_categories,
                    )

                    progress = int((i + 1) / total * 100)
                    self.root.after(0, lambda p=progress: self._update_progress(p))

                self.root.after(0, lambda: self._set_status(f"Generated {total} Excel files in {OUTPUT_FOLDER}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Generated {total} files in:\n{OUTPUT_FOLDER}"))

            except Exception as ex:
                logger.exception("Language Excel generation failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror("Error", f"Generation failed: {err}"))
                self.root.after(0, lambda: self._set_status("Generation failed"))

        threading.Thread(target=generate, daemon=True).start()

    def _update_progress(self, value):
        """Update progress bar value."""
        self.progress["value"] = value

    def _set_status(self, text):
        """Update status label."""
        self.status_label["text"] = text

    # =========================================================================
    # SUBMIT PREPARATION
    # =========================================================================

    def _open_tosubmit_folder(self):
        """Open the ToSubmit folder in file explorer."""
        import subprocess
        import platform

        ensure_tosubmit_folder()

        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(TOSUBMIT_FOLDER)], check=False)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(TOSUBMIT_FOLDER)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(TOSUBMIT_FOLDER)], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def _prepare_for_submit(self):
        """Prepare files in ToSubmit folder - extract rows with corrections."""
        # Check if ToSubmit folder exists
        if not TOSUBMIT_FOLDER.exists():
            ensure_tosubmit_folder()
            messagebox.showinfo(
                "ToSubmit Folder Created",
                f"The ToSubmit folder has been created at:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your Excel files there first, then run this again."
            )
            return

        # Discover files
        files = discover_submit_files(TOSUBMIT_FOLDER)
        if not files:
            messagebox.showwarning(
                "No Files Found",
                f"No languagedata_*.xlsx files found in:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your Excel files there first."
            )
            return

        # Get file list for confirmation
        file_list = "\n".join(f"  - {f[1]}" for f in files)

        # Confirm with user (destructive operation)
        confirm = messagebox.askyesno(
            "Confirm Submission Preparation",
            f"This will OVERWRITE the following {len(files)} files:\n\n"
            f"{file_list}\n\n"
            "Operations:\n"
            "1. Create backup of all files\n"
            "2. Extract rows with Correction values\n"
            "3. Output only: StrOrigin, Correction, StringID\n\n"
            "Note: Progress tracker is updated during 'Merge to LOCDEV'.\n\n"
            "Continue?"
        )

        if not confirm:
            return

        self._set_status("Preparing files for submit...")
        self.progress["value"] = 0

        def prepare():
            try:
                # Prepare files
                def progress_cb(pct, msg):
                    self.root.after(0, lambda p=pct: self._update_progress(p))
                    self.root.after(0, lambda m=msg: self._set_status(m))

                results = prepare_all_for_submit(TOSUBMIT_FOLDER, progress_cb)

                self.root.after(0, lambda: self._update_progress(100))

                # Build result message
                if results["errors"]:
                    error_msg = "\n".join(results["errors"])
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Completed with Errors",
                        f"Processed {results['files_processed']} files\n"
                        f"Extracted {results['total_corrections']} corrections\n\n"
                        f"Errors:\n{error_msg}\n\n"
                        f"Backup: {results['backup_folder']}"
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success",
                        f"Prepared {results['files_processed']} files for submission!\n\n"
                        f"Corrections extracted: {results['total_corrections']}\n"
                        f"Backup folder: {results['backup_folder']}\n\n"
                        f"Next step: Run 'Merge to LOCDEV' to apply and track."
                    ))

                self.root.after(0, lambda: self._set_status(
                    f"Ready - {results['files_processed']} files prepared"
                ))

            except Exception as ex:
                logger.exception("Submit preparation failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Preparation failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Preparation failed"))

        threading.Thread(target=prepare, daemon=True).start()

    def _merge_to_locdev(self):
        """Merge corrections from ToSubmit Excel files to LOCDEV XML files and update tracker."""
        # Check if ToSubmit folder exists
        if not TOSUBMIT_FOLDER.exists():
            ensure_tosubmit_folder()
            messagebox.showinfo(
                "ToSubmit Folder Created",
                f"The ToSubmit folder has been created at:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your corrected Excel files there first, then run this again."
            )
            return

        # Check if LOCDEV folder exists
        if not LOCDEV_FOLDER.exists():
            messagebox.showerror(
                "LOCDEV Folder Not Found",
                f"LOCDEV folder not found:\n{LOCDEV_FOLDER}\n\n"
                "Please check your settings.json configuration."
            )
            return

        # Discover files
        files = discover_submit_files(TOSUBMIT_FOLDER)
        if not files:
            messagebox.showwarning(
                "No Files Found",
                f"No languagedata_*.xlsx files found in:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your corrected Excel files there first."
            )
            return

        # Get file list for confirmation
        file_list = "\n".join(f"  - {f[1]}" for f in files)

        # Confirm with user
        confirm = messagebox.askyesno(
            "Confirm LOCDEV Merge",
            f"This will merge corrections from {len(files)} Excel files:\n\n"
            f"{file_list}\n\n"
            f"Into LOCDEV XML files at:\n{LOCDEV_FOLDER}\n\n"
            "Matching is STRICT: StringID + StrOrigin must BOTH match.\n\n"
            "Progress tracker will be updated with merge results.\n\n"
            "Continue?"
        )

        if not confirm:
            return

        self._set_status("Merging corrections to LOCDEV...")
        self.progress["value"] = 0

        def merge():
            try:
                self.root.after(0, lambda: self._update_progress(10))
                self.root.after(0, lambda: self._set_status("Merging corrections..."))

                results = merge_all_corrections(TOSUBMIT_FOLDER, LOCDEV_FOLDER)

                # Print terminal report
                print_merge_report(results)

                self.root.after(0, lambda: self._update_progress(70))
                self.root.after(0, lambda: self._set_status("Updating progress tracker..."))

                # Update progress tracker with merge results
                tracker = CorrectionTracker(TRACKER_PATH, TRACKER_CATEGORIES)
                tracker.update_and_rebuild_from_merge(results)

                self.root.after(0, lambda: self._update_progress(100))

                # Build result message
                if results["errors"]:
                    error_msg = "\n".join(results["errors"][:5])  # Show first 5 errors
                    if len(results["errors"]) > 5:
                        error_msg += f"\n... and {len(results['errors']) - 5} more"
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Completed with Errors",
                        f"Processed {results['files_processed']} files\n"
                        f"Corrections: {results['total_corrections']}\n"
                        f"Success: {results['total_success']}\n"
                        f"Fail: {results['total_fail']}\n\n"
                        f"Tracker updated: {TRACKER_PATH.name}\n\n"
                        f"Errors:\n{error_msg}"
                    ))
                else:
                    success_rate = (results['total_success'] / results['total_corrections'] * 100) if results['total_corrections'] > 0 else 0
                    self.root.after(0, lambda: messagebox.showinfo(
                        "LOCDEV Merge Complete",
                        f"Processed {results['files_processed']} files\n\n"
                        f"Corrections: {results['total_corrections']}\n"
                        f"Success: {results['total_success']} ({success_rate:.1f}%)\n"
                        f"Fail: {results['total_fail']}\n\n"
                        f"Tracker updated: {TRACKER_PATH.name}"
                    ))

                self.root.after(0, lambda: self._set_status(
                    f"Ready - {results['total_success']} corrections merged to LOCDEV"
                ))

            except Exception as ex:
                logger.exception("LOCDEV merge failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Merge failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Merge failed"))

        threading.Thread(target=merge, daemon=True).start()

    def _analyze_code_patterns(self):
        """Analyze code patterns in languagedata XML and generate report."""
        if not LOC_FOLDER.exists():
            messagebox.showerror("Error", f"LOC folder not found:\n{LOC_FOLDER}")
            return
        if not EXPORT_FOLDER.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{EXPORT_FOLDER}")
            return

        self._set_status("Analyzing code patterns...")
        self.progress["value"] = 0

        def analyze():
            try:
                # Ensure output folder exists
                OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

                self.root.after(0, lambda: self._update_progress(10))
                self.root.after(0, lambda: self._set_status("Loading category index..."))

                # Load category index
                config = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    EXPORT_FOLDER,
                    config,
                    config.get("default_category", "Uncategorized")
                )

                self.root.after(0, lambda: self._update_progress(30))
                self.root.after(0, lambda: self._set_status("Scanning patterns..."))

                # Analyze patterns
                result = analyze_patterns(
                    LOC_FOLDER,
                    category_index,
                    threshold=0.8,
                    default_category=config.get("default_category", "Uncategorized")
                )

                self.root.after(0, lambda: self._update_progress(80))
                self.root.after(0, lambda: self._set_status("Generating report..."))

                # Generate report
                output_path = OUTPUT_FOLDER / "CodePatternReport.xlsx"
                generate_pattern_report(result, output_path)

                self.root.after(0, lambda: self._update_progress(100))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Analysis Complete",
                    f"Found {result['total_patterns']} unique patterns\n"
                    f"Grouped into {result['total_clusters']} clusters\n\n"
                    f"Report: {output_path.name}"
                ))
                self.root.after(0, lambda: self._set_status("Ready"))

            except Exception as ex:
                logger.exception("Pattern analysis failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Pattern analysis failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Analysis failed"))

        threading.Thread(target=analyze, daemon=True).start()


def launch_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = LanguageDataExporterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
