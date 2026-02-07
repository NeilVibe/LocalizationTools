"""
Language Data Exporter GUI - Simplified Application.

Tkinter GUI for the LanguageDataExporter tool with:
1. Fixed paths from settings.json (drive selected at install)
2. One-click generation (ALL languages except KOR)
3. Progress tracking
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import logging
import sys
from typing import Dict, Tuple

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
    export_merge_report_to_excel,
    # StringID-only matching
    merge_all_corrections_stringid_only_script,
    print_stringid_only_report,
)
from utils.language_utils import should_include_english_column, LANGUAGE_NAMES as LANG_DISPLAY
from reports import ReportGenerator, ExcelReportWriter
from tracker import CorrectionTracker

logger = logging.getLogger(__name__)

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Language Data Exporter v3.0"
WINDOW_WIDTH = 850
WINDOW_HEIGHT = 800

# Languages to EXCLUDE (Korean is source, not target)
EXCLUDED_LANGUAGES = {"kor"}


def validate_locdev_folder(folder_path: Path) -> Tuple[bool, str, Dict]:
    """
    Validate a LOCDEV folder.

    Checks:
    - Folder exists
    - Contains languagedata_*.xml files
    - Files are valid XML
    - Reports found languages (NO hardcoded expected list)

    Args:
        folder_path: Path to check

    Returns:
        Tuple of (is_valid, message, details_dict)
    """
    details = {
        "exists": False,
        "found_languages": [],
        "invalid_files": [],
        "total_files": 0,
    }

    if not folder_path.exists():
        return False, "Folder does not exist", details

    if not folder_path.is_dir():
        return False, "Path is not a folder", details

    details["exists"] = True

    # Find all languagedata_*.xml files (dynamic discovery)
    xml_files = list(folder_path.glob("languagedata_*.xml"))
    xml_files.extend(folder_path.glob("LanguageData_*.xml"))

    # Remove duplicates (case-insensitive)
    seen = set()
    unique_files = []
    for f in xml_files:
        if f.name.lower() not in seen:
            seen.add(f.name.lower())
            unique_files.append(f)

    details["total_files"] = len(unique_files)

    if not unique_files:
        return False, "No languagedata_*.xml files found", details

    # Extract language codes and validate XML
    found_langs = set()
    for xml_file in unique_files:
        name = xml_file.stem.lower()
        if name.startswith("languagedata_"):
            lang_code = name[13:]
            found_langs.add(lang_code)

            # Quick XML validation (check if file contains XML content)
            try:
                with open(xml_file, 'rb') as f:
                    raw = f.read(1024)
                if not raw:
                    details["invalid_files"].append(xml_file.name)
                    continue
                # Strip BOM variants (UTF-8, UTF-16 LE/BE)
                for bom in (b'\xef\xbb\xbf', b'\xff\xfe', b'\xfe\xff'):
                    if raw.startswith(bom):
                        raw = raw[len(bom):]
                        break
                # Check for XML-like content (skip whitespace)
                text = raw.lstrip()
                if not (text.startswith(b'<?xml') or text.startswith(b'<')):
                    details["invalid_files"].append(xml_file.name)
            except Exception:
                details["invalid_files"].append(xml_file.name)

    details["found_languages"] = sorted(found_langs)

    # Build status message
    if details["invalid_files"]:
        return False, f"Invalid XML files: {', '.join(details['invalid_files'])}", details

    if len(found_langs) == 0:
        return False, "No valid language files found", details

    msg = f"✓ {len(found_langs)} languages found"

    return True, msg, details


class LanguageDataExporterGUI:
    """Main GUI application for Language Data Exporter."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(750, 700)
        self.root.resizable(True, True)

        # Custom LOCDEV path (defaults to config value)
        self.custom_locdev_path = tk.StringVar(value=str(LOCDEV_FOLDER))
        self.locdev_valid = False

        # Build UI
        self._build_ui()

        # Show path status
        self._check_paths()

        # Validate default LOCDEV
        self._validate_locdev()

    def _build_ui(self):
        """Build the main UI layout."""
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        # Title
        title_label = tk.Label(
            self.root,
            text="Language Data Exporter",
            font=("Arial", 18, "bold")
        )
        title_label.grid(row=0, column=0, pady=15)

        # === Section 1: Path Info (Read-Only) ===
        self._build_path_info_section()

        # === Section 2: LOCDEV Selection ===
        self._build_locdev_section()

        # === Section 3: Export Actions ===
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

    def _build_locdev_section(self):
        """Build LOCDEV folder selection section."""
        section = ttk.LabelFrame(self.root, text="LOCDEV Folder (for Merge Operations)", padding=10)
        section.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(1, weight=1)

        # Path entry
        ttk.Label(section, text="Path:").grid(row=0, column=0, sticky="w", padx=5)

        self.locdev_entry = ttk.Entry(section, textvariable=self.custom_locdev_path, width=50)
        self.locdev_entry.grid(row=0, column=1, sticky="ew", padx=5)

        # Browse button
        ttk.Button(
            section,
            text="Browse...",
            command=self._browse_locdev,
            width=10
        ).grid(row=0, column=2, padx=5)

        # Validate button
        ttk.Button(
            section,
            text="Validate",
            command=self._validate_locdev,
            width=10
        ).grid(row=0, column=3, padx=5)

        # Status row
        status_frame = ttk.Frame(section)
        status_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

        self.locdev_status_icon = ttk.Label(status_frame, text="", font=("Arial", 12))
        self.locdev_status_icon.pack(side="left", padx=(5, 2))

        self.locdev_status_text = ttk.Label(status_frame, text="Not validated")
        self.locdev_status_text.pack(side="left", padx=2)

        # Details label (for missing languages info)
        self.locdev_details = ttk.Label(section, text="", font=("Arial", 8), foreground="gray")
        self.locdev_details.grid(row=2, column=0, columnspan=4, sticky="w", padx=5)

    def _browse_locdev(self):
        """Browse for LOCDEV folder."""
        current_path = self.custom_locdev_path.get()
        initial_dir = current_path if Path(current_path).exists() else str(Path.home())

        folder = filedialog.askdirectory(
            title="Select LOCDEV Folder",
            initialdir=initial_dir
        )

        if folder:
            self.custom_locdev_path.set(folder)
            self._validate_locdev()

    def _validate_locdev(self):
        """Validate the selected LOCDEV folder."""
        folder_path = Path(self.custom_locdev_path.get())

        is_valid, message, details = validate_locdev_folder(folder_path)

        self.locdev_valid = is_valid

        if is_valid:
            self.locdev_status_icon.config(text="✓", foreground="green")
            self.locdev_status_text.config(text=message, foreground="green")

            # Show found languages (truncate if too many)
            found = details["found_languages"]
            if found:
                lang_str = ", ".join(lang.upper() for lang in found[:8])
                if len(found) > 8:
                    lang_str += f"... (+{len(found) - 8} more)"
                self.locdev_details.config(text=f"Languages: {lang_str}")
            else:
                self.locdev_details.config(text="")
        else:
            self.locdev_status_icon.config(text="✗", foreground="red")
            self.locdev_status_text.config(text=message, foreground="red")
            self.locdev_details.config(text="")

    def _get_locdev_folder(self) -> Path:
        """Get the current LOCDEV folder path."""
        return Path(self.custom_locdev_path.get())

    def _build_export_section(self):
        """Build export actions section."""
        section = ttk.LabelFrame(self.root, text="Generate & Submit", padding=10)
        section.grid(row=3, column=0, sticky="ew", padx=15, pady=5)

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

        # Row 3: LOCDEV merge buttons
        btn_frame3 = ttk.Frame(section)
        btn_frame3.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame3,
            text="Merge to LOCDEV (ALL - StringID, KR HIT)",
            command=self._merge_to_locdev,
            width=40
        ).pack(side="left", padx=5, ipady=8)

        ttk.Button(
            btn_frame3,
            text="Merge to LOCDEV (SCRIPT - StringID HIT)",
            command=self._stringid_only_script_transfer,
            width=40
        ).pack(side="left", padx=5, ipady=8)

        # Row 4: USER GUIDE
        btn_frame4 = ttk.Frame(section)
        btn_frame4.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame4,
            text="USER GUIDE",
            command=self._show_user_guide,
            width=28
        ).pack(side="left", padx=5, ipady=8)

    def _build_status_section(self):
        """Build status display section."""
        section = ttk.LabelFrame(self.root, text="Status", padding=10)
        section.grid(row=4, column=0, sticky="ew", padx=15, pady=10)
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

        # Show LOC folder info before starting
        messagebox.showinfo(
            "LOC Source",
            f"Generating Excel files from:\n\n"
            f"LOC: {LOC_FOLDER}\n"
            f"EXPORT: {EXPORT_FOLDER}\n\n"
            f"Languages: {len(languages)}\n"
            f"Output: {OUTPUT_FOLDER}"
        )

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

        # Use custom LOCDEV path
        locdev_folder = self._get_locdev_folder()

        # Validate LOCDEV folder
        if not self.locdev_valid:
            self._validate_locdev()
            if not self.locdev_valid:
                messagebox.showerror(
                    "LOCDEV Folder Invalid",
                    f"LOCDEV folder is not valid:\n{locdev_folder}\n\n"
                    "Please select a valid LOCDEV folder with languagedata_*.xml files."
                )
                return

        # Discover files (pass locdev_folder for accurate language matching)
        files = discover_submit_files(TOSUBMIT_FOLDER, locdev_folder)
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
            f"Into LOCDEV XML files at:\n{locdev_folder}\n\n"
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

                results = merge_all_corrections(TOSUBMIT_FOLDER, locdev_folder)

                # Print terminal report
                print_merge_report(results)

                # Export merge report to Excel (with Not Found Details tab)
                report_path = OUTPUT_FOLDER / "MergeReport.xlsx"
                export_merge_report_to_excel(results, report_path)
                logger.info(f"Merge report exported: {report_path}")

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

    def _stringid_only_script_transfer(self):
        """Transfer corrections using StringID-only matching for SCRIPT strings."""
        # Check if ToSubmit folder exists
        if not TOSUBMIT_FOLDER.exists():
            ensure_tosubmit_folder()
            messagebox.showinfo(
                "ToSubmit Folder Created",
                f"The ToSubmit folder has been created at:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your corrected Excel files there first, then run this again."
            )
            return

        # Use custom LOCDEV path
        locdev_folder = self._get_locdev_folder()

        # Validate LOCDEV folder
        if not self.locdev_valid:
            self._validate_locdev()
            if not self.locdev_valid:
                messagebox.showerror(
                    "LOCDEV Folder Invalid",
                    f"LOCDEV folder is not valid:\n{locdev_folder}\n\n"
                    "Please select a valid LOCDEV folder with languagedata_*.xml files."
                )
                return

        # Check if EXPORT folder exists (needed for category detection)
        if not EXPORT_FOLDER.exists():
            messagebox.showerror(
                "EXPORT Folder Not Found",
                f"EXPORT folder not found:\n{EXPORT_FOLDER}\n\n"
                "This folder is needed to detect SCRIPT-type strings.\n"
                "Please check your settings.json configuration."
            )
            return

        # Discover files (pass locdev_folder for accurate language matching)
        files = discover_submit_files(TOSUBMIT_FOLDER, locdev_folder)
        if not files:
            messagebox.showwarning(
                "No Files Found",
                f"No languagedata_*.xlsx files found in:\n{TOSUBMIT_FOLDER}\n\n"
                "Please copy your corrected Excel files there first."
            )
            return

        # Get file list for confirmation
        file_list = "\n".join(f"  - {f[1]}" for f in files)

        # Warning dialog explaining the behavior
        confirm = messagebox.askyesno(
            "StringID-Only HIT Transfer",
            "This transfers corrections using StringID-only matching.\n\n"
            "APPLIES TO: Dialog/Sequencer strings ONLY\n"
            "  • Sequencer (story cutscenes)\n"
            "  • AIDialog (NPC dialog)\n"
            "  • QuestDialog (quest text)\n\n"
            "EXCLUDES: NarrationDialog\n"
            "IGNORES: StrOrigin (source text)\n"
            "SKIPS: All non-SCRIPT strings (System, UI, etc.)\n\n"
            f"Target LOCDEV:\n{locdev_folder}\n\n"
            f"Files to process:\n{file_list}\n\n"
            "Use this when source text changed but StringID is still valid.\n\n"
            "Continue?",
            icon="warning"
        )

        if not confirm:
            return

        self._set_status("Running StringID-only HIT transfer...")
        self.progress["value"] = 0

        def transfer():
            try:
                self.root.after(0, lambda: self._update_progress(10))
                self.root.after(0, lambda: self._set_status("Building category index..."))

                results = merge_all_corrections_stringid_only_script(
                    TOSUBMIT_FOLDER, locdev_folder, EXPORT_FOLDER
                )

                # Print terminal report
                print_stringid_only_report(results)

                # Export merge report to Excel (with Not Found Details tab)
                report_path = OUTPUT_FOLDER / "StringIDOnlyMergeReport.xlsx"
                export_merge_report_to_excel(results, report_path)
                logger.info(f"StringID-only merge report exported: {report_path}")

                self.root.after(0, lambda: self._update_progress(100))

                # Build result message
                if results["errors"]:
                    error_msg = "\n".join(results["errors"][:5])
                    if len(results["errors"]) > 5:
                        error_msg += f"\n... and {len(results['errors']) - 5} more"
                    self.root.after(0, lambda: messagebox.showwarning(
                        "Completed with Errors",
                        f"Processed {results['files_processed']} files\n"
                        f"Total corrections: {results['total_corrections']}\n"
                        f"SCRIPT corrections: {results['total_script_corrections']}\n"
                        f"Skipped (non-SCRIPT): {results['total_skipped_non_script']}\n"
                        f"Success: {results['total_success']}\n"
                        f"Fail: {results['total_fail']}\n\n"
                        f"Errors:\n{error_msg}"
                    ))
                else:
                    script_total = results['total_script_corrections']
                    success_rate = (results['total_success'] / script_total * 100) if script_total > 0 else 0
                    self.root.after(0, lambda: messagebox.showinfo(
                        "StringID-Only Transfer Complete",
                        f"Processed {results['files_processed']} files\n\n"
                        f"Total corrections: {results['total_corrections']}\n"
                        f"SCRIPT corrections: {results['total_script_corrections']}\n"
                        f"Skipped (non-SCRIPT): {results['total_skipped_non_script']}\n\n"
                        f"Success: {results['total_success']} ({success_rate:.1f}%)\n"
                        f"Fail: {results['total_fail']}"
                    ))

                self.root.after(0, lambda: self._set_status(
                    f"Ready - {results['total_success']} SCRIPT corrections transferred"
                ))

            except Exception as ex:
                logger.exception("StringID-only transfer failed")
                self.root.after(0, lambda err=str(ex): messagebox.showerror(
                    "Error", f"Transfer failed: {err}"
                ))
                self.root.after(0, lambda: self._set_status("Transfer failed"))

        threading.Thread(target=transfer, daemon=True).start()

    def _show_user_guide(self):
        """Show USER GUIDE in a scrollable dialog window."""
        guide_window = tk.Toplevel(self.root)
        guide_window.title("USER GUIDE - LanguageDataExporter")
        guide_window.geometry("700x600")
        guide_window.minsize(600, 400)

        # Scrollable text widget
        text_frame = ttk.Frame(guide_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        text_widget = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
        )
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)

        guide_text = (
            "═══════════════════════════════════════════════════════\n"
            "  LANGUAGEDATAEXPORTER - USER GUIDE\n"
            "═══════════════════════════════════════════════════════\n\n"
            "── SOURCE FOLDERS ──\n\n"
            "LOC folder: Contains languagedata_*.xml files (all\n"
            "  game text, one file per language).\n"
            "EXPORT folder: Contains .loc.xml files organized by\n"
            "  category (Dialog/, Sequencer/, System/, World/).\n"
            "  Used to determine which category each StringID\n"
            "  belongs to.\n"
            "LOCDEV folder: Development XML files where corrections\n"
            "  are merged back into.\n"
            "All paths are configured in settings.json.\n\n"
            "── GENERATE WORD COUNT REPORT ──\n\n"
            "Creates a WordCountReport.xlsx with two sheets:\n"
            "  - General Summary: one row per language with totals\n"
            "  - Detailed Summary: per-category breakdown\n"
            "Counts words (EU) or characters (CJK) for LQA\n"
            "scheduling. Also shows untranslated string counts.\n\n"
            "── GENERATE LANGUAGE EXCELS ──\n\n"
            "Creates one Excel file per language from the LOC\n"
            "folder. Each file contains all strings organized by\n"
            "category with columns for QA review.\n\n"
            "Source: LOC folder (configured in settings.json)\n"
            "Output: GeneratedExcel/LanguageData_{LANG}.xlsx\n\n"
            "EU columns (11):\n"
            "  StrOrigin | ENG | Str | Correction | Text State\n"
            "  | STATUS | COMMENT | MEMO1 | MEMO2 | Category\n"
            "  | StringID\n\n"
            "Asian columns (10):\n"
            "  StrOrigin | Str | Correction | Text State\n"
            "  | STATUS | COMMENT | MEMO1 | MEMO2 | Category\n"
            "  | StringID\n\n"
            "Column details:\n"
            "  - Correction: empty, fill with corrected text\n"
            "  - Text State: auto-filled KOREAN (has Korean\n"
            "    characters = untranslated) or TRANSLATED\n"
            "  - STATUS: dropdown (ISSUE / NO ISSUE)\n"
            "  - COMMENT: free-text QA notes\n"
            "  - MEMO1, MEMO2: general-purpose memo fields\n\n"
            "Note: ENG and ZHO-CN exclude Dialog/Sequencer\n"
            "categories (voiced content handled separately).\n"
            "KOR is excluded (source language, not a target).\n\n"
            "── PREPARE FOR SUBMIT ──\n\n"
            "Extracts only rows that have Correction values from\n"
            "Excel files in ToSubmit/ folder. Creates clean\n"
            "3-column archive files (StrOrigin | Correction |\n"
            "StringID). A backup is created automatically.\n\n"
            "── OPEN TOSUBMIT FOLDER ──\n\n"
            "Opens the ToSubmit/ folder in your file explorer.\n"
            "Copy your corrected Excel files here before running\n"
            "Merge or Prepare For Submit.\n\n"
            "── MERGE TO LOCDEV (ALL - StringID, KR HIT) ──\n\n"
            "Pushes corrections back to LOCDEV XML files.\n\n"
            "Step-by-step:\n"
            "  1. Copy corrected Excel files to ToSubmit/ folder\n"
            "  2. Set LOCDEV folder path in the GUI\n"
            "  3. Click the merge button\n"
            "  4. Tool reads Correction column from each Excel\n"
            "  5. STRICT match: StringID + StrOrigin must BOTH\n"
            "     match in the LOCDEV XML\n"
            "  6. Updates Str attribute in LOCDEV XML\n"
            "  7. Progress tracker is updated with results\n\n"
            "Required Excel columns for merge:\n"
            "  - StrOrigin (Korean source text)\n"
            "  - Correction (the corrected translation)\n"
            "  - StringID (unique identifier)\n"
            "  - Category (optional, used for tracking)\n\n"
            "── MERGE TO LOCDEV (SCRIPT - StringID HIT) ──\n\n"
            "Same as above but uses StringID-ONLY matching.\n"
            "Applies ONLY to Dialog/Sequencer (SCRIPT) strings.\n"
            "Ignores StrOrigin - useful when source text changed\n"
            "but StringID is still valid.\n\n"
            "Step-by-step:\n"
            "  1. Same setup as normal merge\n"
            "  2. Click the SCRIPT merge button\n"
            "  3. Tool filters for SCRIPT categories only:\n"
            "     Sequencer, AIDialog, QuestDialog\n"
            "     (NarrationDialog excluded)\n"
            "  4. Matches by StringID only (ignores StrOrigin)\n"
            "  5. Non-SCRIPT strings are skipped\n\n"
            "── COMPLETE WORKFLOW ──\n\n"
            "  1. Generate Language Excels (creates files)\n"
            "  2. Copy files to ToSubmit/ folder\n"
            "  3. QA reviews Str, fills Correction column,\n"
            "     sets STATUS, adds COMMENT if needed\n"
            "  4. Merge to LOCDEV (push corrections to XML)\n"
            "  5. (Optional) Prepare For Submit (3-col archive)\n\n"
            "═══════════════════════════════════════════════════════\n"
        )

        text_widget.insert("1.0", guide_text)
        text_widget.config(state="disabled")

        # Close button
        ttk.Button(
            guide_window,
            text="Close",
            command=guide_window.destroy,
            width=15
        ).pack(pady=(0, 10))


def launch_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = LanguageDataExporterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
