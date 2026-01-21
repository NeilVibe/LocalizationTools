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
)
from exporter import (
    parse_language_file,
    discover_language_files,
    build_stringid_category_index,
    load_cluster_config,
    analyze_categories,
    write_language_excel,
)
from exporter.excel_writer import write_summary_excel
from utils.language_utils import should_include_english_column, LANGUAGE_NAMES as LANG_DISPLAY
from reports import ReportGenerator, ExcelReportWriter

logger = logging.getLogger(__name__)

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Language Data Exporter v3.0"
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 500

# Languages to EXCLUDE (Korean is source, not target)
EXCLUDED_LANGUAGES = {"kor"}


class LanguageDataExporterGUI:
    """Main GUI application for Language Data Exporter."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Category data
        self.category_data = {}

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

        # === Section 2: Category Analysis ===
        self._build_cluster_section()

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

    def _build_cluster_section(self):
        """Build cluster analysis section."""
        section = ttk.LabelFrame(self.root, text="Category Analysis", padding=10)
        section.grid(row=2, column=0, sticky="nsew", padx=15, pady=5)
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        # Button frame
        btn_frame = ttk.Frame(section)
        btn_frame.grid(row=0, column=0, sticky="w", pady=5)

        ttk.Button(
            btn_frame,
            text="Analyze Categories",
            command=self._analyze_categories
        ).pack(side="left", padx=5)

        # TreeView for category display
        tree_frame = ttk.Frame(section)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        columns = ("category", "files", "tier")
        self.category_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)

        self.category_tree.heading("category", text="Category")
        self.category_tree.heading("files", text="Files")
        self.category_tree.heading("tier", text="Tier")

        self.category_tree.column("category", width=200)
        self.category_tree.column("files", width=80, anchor="center")
        self.category_tree.column("tier", width=100, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=scrollbar.set)

        self.category_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def _build_export_section(self):
        """Build export actions section."""
        section = ttk.LabelFrame(self.root, text="Generate Report", padding=10)
        section.grid(row=3, column=0, sticky="ew", padx=15, pady=5)

        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame,
            text="Generate Word Count Report",
            command=self._generate_report,
            width=35
        ).pack(side="left", padx=10, ipady=8)

        ttk.Button(
            btn_frame,
            text="Generate Language Excels",
            command=self._generate_language_excels,
            width=35
        ).pack(side="left", padx=10, ipady=8)

    def _build_status_section(self):
        """Build status display section."""
        section = ttk.LabelFrame(self.root, text="Status", padding=10)
        section.grid(row=4, column=0, sticky="ew", padx=15, pady=10)
        section.columnconfigure(0, weight=1)

        # Progress bar
        self.progress = ttk.Progressbar(section, mode="determinate", length=400)
        self.progress.grid(row=0, column=0, sticky="ew", pady=5)

        # Status label
        self.status_label = ttk.Label(section, text="Ready - Click 'Generate Word Count Report' to start")
        self.status_label.grid(row=1, column=0, sticky="w", pady=5)

    # =========================================================================
    # CATEGORY ANALYSIS
    # =========================================================================

    def _analyze_categories(self):
        """Analyze EXPORT folder and show category distribution."""
        if not EXPORT_FOLDER.exists():
            messagebox.showerror("Error", f"EXPORT folder not found:\n{EXPORT_FOLDER}")
            return

        self._set_status("Analyzing categories...")
        self.progress["value"] = 0

        def analyze():
            try:
                # Load config
                config = load_cluster_config(CLUSTER_CONFIG)

                # Analyze categories
                category_counts = analyze_categories(EXPORT_FOLDER, config)

                # Update UI on main thread
                self.root.after(0, lambda: self._display_categories(category_counts))

            except Exception as ex:
                self.root.after(0, lambda err=str(ex): messagebox.showerror("Error", f"Analysis failed: {err}"))
                self.root.after(0, lambda: self._set_status("Analysis failed"))

        threading.Thread(target=analyze, daemon=True).start()

    def _display_categories(self, category_counts):
        """Display category counts in TreeView."""
        # Clear existing items
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)

        # Determine tier for each category
        def get_tier(category):
            if category.startswith("Dialog_"):
                return "STORY"
            elif category.startswith("Seq_"):
                return "STORY"
            else:
                return "GAME_DATA"

        # Add items sorted by count
        total_files = 0
        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            tier = get_tier(category)
            self.category_tree.insert("", "end", values=(category, count, tier))
            total_files += count

        self.category_data = category_counts
        self._set_status(f"Found {len(category_counts)} categories, {total_files} files")
        self.progress["value"] = 100

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

                    write_language_excel(
                        lang_code=lang_code,
                        lang_data=lang_data,
                        eng_lookup=eng_lookup,
                        category_index=category_index,
                        output_path=output_file,
                        include_english=include_english,
                        default_category=config.get("default_category", "Uncategorized")
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


def launch_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = LanguageDataExporterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
