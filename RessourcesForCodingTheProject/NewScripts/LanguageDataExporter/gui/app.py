"""
Language Data Exporter GUI - Main Application.

Tkinter GUI for the LanguageDataExporter tool with:
1. Folder selection (LOC, EXPORT, Output)
2. Cluster analysis visualization
3. Language selection with checkboxes
4. Excel generation (language files + word count reports)
5. Progress tracking
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
    LANGUAGE_NAMES,
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

WINDOW_TITLE = "Language Data Exporter v2.0"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 800


class LanguageDataExporterGUI:
    """Main GUI application for Language Data Exporter."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Path variables
        self.loc_folder = tk.StringVar(value=str(LOC_FOLDER))
        self.export_folder = tk.StringVar(value=str(EXPORT_FOLDER))
        self.output_folder = tk.StringVar(value=str(OUTPUT_FOLDER))

        # Language checkboxes state
        self.language_vars = {}

        # Category data
        self.category_data = {}

        # Build UI
        self._build_ui()

        # Initial discovery
        self._discover_languages()

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
        title_label.grid(row=0, column=0, pady=10)

        # === Section 1: Folder Selection ===
        self._build_folder_section()

        # === Section 2: Cluster Analysis ===
        self._build_cluster_section()

        # === Section 3: Language Selection ===
        self._build_language_section()

        # === Section 4: Export Actions ===
        self._build_export_section()

        # === Section 5: Status ===
        self._build_status_section()

    def _build_folder_section(self):
        """Build folder selection section."""
        section = ttk.LabelFrame(self.root, text="1. Folder Paths", padding=10)
        section.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(1, weight=1)

        # LOC Folder
        ttk.Label(section, text="LOC Folder:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Entry(section, textvariable=self.loc_folder, width=60).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(section, text="Browse", command=lambda: self._browse_folder(self.loc_folder)).grid(row=0, column=2, padx=5)

        # EXPORT Folder
        ttk.Label(section, text="EXPORT Folder:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(section, textvariable=self.export_folder, width=60).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(section, text="Browse", command=lambda: self._browse_folder(self.export_folder)).grid(row=1, column=2, padx=5, pady=5)

        # Output Folder
        ttk.Label(section, text="Output Folder:").grid(row=2, column=0, sticky="w", padx=5)
        ttk.Entry(section, textvariable=self.output_folder, width=60).grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Button(section, text="Browse", command=lambda: self._browse_folder(self.output_folder)).grid(row=2, column=2, padx=5)

    def _build_cluster_section(self):
        """Build cluster analysis section."""
        section = ttk.LabelFrame(self.root, text="2. Category Cluster Analysis", padding=10)
        section.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(0, weight=1)

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
        self.category_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

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

    def _build_language_section(self):
        """Build language selection section."""
        section = ttk.LabelFrame(self.root, text="3. Language Selection", padding=10)
        section.grid(row=3, column=0, sticky="nsew", padx=15, pady=5)
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        # Button frame
        btn_frame = ttk.Frame(section)
        btn_frame.grid(row=0, column=0, sticky="w", pady=5)

        ttk.Button(btn_frame, text="Select All", command=self._select_all_languages).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all_languages).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self._discover_languages).pack(side="left", padx=5)

        # Checkbox frame with scrollbar
        canvas_frame = ttk.Frame(section)
        canvas_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(canvas_frame, height=150)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.lang_checkbox_frame = ttk.Frame(canvas)

        canvas.create_window((0, 0), window=self.lang_checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.lang_checkbox_frame.bind("<Configure>", on_frame_configure)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.lang_canvas = canvas

    def _build_export_section(self):
        """Build export actions section."""
        section = ttk.LabelFrame(self.root, text="4. Export Actions", padding=10)
        section.grid(row=4, column=0, sticky="ew", padx=15, pady=5)

        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            btn_frame,
            text="Generate Language Excels",
            command=self._generate_language_excels,
            width=30
        ).pack(side="left", padx=10, ipady=5)

        ttk.Button(
            btn_frame,
            text="Generate Word Count Report",
            command=self._generate_word_count_report,
            width=30
        ).pack(side="left", padx=10, ipady=5)

        ttk.Button(
            btn_frame,
            text="Generate All",
            command=self._generate_all,
            width=20
        ).pack(side="left", padx=10, ipady=5)

    def _build_status_section(self):
        """Build status display section."""
        section = ttk.LabelFrame(self.root, text="5. Status", padding=10)
        section.grid(row=5, column=0, sticky="ew", padx=15, pady=5)
        section.columnconfigure(0, weight=1)

        # Progress bar
        self.progress = ttk.Progressbar(section, mode="determinate", length=400)
        self.progress.grid(row=0, column=0, sticky="ew", pady=5)

        # Status label
        self.status_label = ttk.Label(section, text="Ready")
        self.status_label.grid(row=1, column=0, sticky="w", pady=5)

    # =========================================================================
    # FOLDER OPERATIONS
    # =========================================================================

    def _browse_folder(self, var):
        """Open folder browser dialog."""
        current = var.get()
        initial = current if Path(current).exists() else str(Path.home())

        folder = filedialog.askdirectory(initialdir=initial, title="Select Folder")
        if folder:
            var.set(folder)

    # =========================================================================
    # LANGUAGE DISCOVERY
    # =========================================================================

    def _discover_languages(self):
        """Discover available language files."""
        loc_path = Path(self.loc_folder.get())

        # Clear existing checkboxes
        for widget in self.lang_checkbox_frame.winfo_children():
            widget.destroy()
        self.language_vars.clear()

        if not loc_path.exists():
            self._set_status("LOC folder not found")
            return

        # Discover language files
        lang_files = discover_language_files(loc_path)

        if not lang_files:
            self._set_status("No language files found")
            return

        # Create checkboxes in grid (4 columns)
        for i, lang_code in enumerate(sorted(lang_files.keys())):
            var = tk.BooleanVar(value=True)
            self.language_vars[lang_code] = var

            display_name = LANG_DISPLAY.get(lang_code.lower(), lang_code.upper())
            cb = ttk.Checkbutton(
                self.lang_checkbox_frame,
                text=display_name,
                variable=var
            )
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=10, pady=2)

        self._set_status(f"Found {len(lang_files)} language files")

    def _select_all_languages(self):
        """Select all language checkboxes."""
        for var in self.language_vars.values():
            var.set(True)

    def _deselect_all_languages(self):
        """Deselect all language checkboxes."""
        for var in self.language_vars.values():
            var.set(False)

    def _get_selected_languages(self):
        """Get list of selected language codes."""
        return [lang for lang, var in self.language_vars.items() if var.get()]

    # =========================================================================
    # CATEGORY ANALYSIS
    # =========================================================================

    def _analyze_categories(self):
        """Analyze EXPORT folder and show category distribution."""
        export_path = Path(self.export_folder.get())

        if not export_path.exists():
            messagebox.showerror("Error", "EXPORT folder not found")
            return

        self._set_status("Analyzing categories...")
        self.progress["value"] = 0

        def analyze():
            try:
                # Load config
                config = load_cluster_config(CLUSTER_CONFIG)

                # Analyze categories
                category_counts = analyze_categories(export_path, config)

                # Update UI on main thread
                self.root.after(0, lambda: self._display_categories(category_counts))

            except Exception as ex:
                # Capture exception by value in lambda (closure fix)
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
    # EXCEL GENERATION
    # =========================================================================

    def _generate_language_excels(self):
        """Generate Excel files for selected languages."""
        selected = self._get_selected_languages()

        if not selected:
            messagebox.showwarning("Warning", "No languages selected")
            return

        self._run_generation("language", selected)

    def _generate_word_count_report(self):
        """Generate word count report for selected languages."""
        selected = self._get_selected_languages()

        if not selected:
            messagebox.showwarning("Warning", "No languages selected")
            return

        self._run_generation("wordcount", selected)

    def _generate_all(self):
        """Generate both language Excels and word count report."""
        selected = self._get_selected_languages()

        if not selected:
            messagebox.showwarning("Warning", "No languages selected")
            return

        self._run_generation("all", selected)

    def _run_generation(self, mode, languages):
        """Run generation in background thread."""
        loc_path = Path(self.loc_folder.get())
        export_path = Path(self.export_folder.get())
        output_path = Path(self.output_folder.get())

        # Validate paths
        if not loc_path.exists():
            messagebox.showerror("Error", "LOC folder not found")
            return
        if not export_path.exists():
            messagebox.showerror("Error", "EXPORT folder not found")
            return

        self._set_status(f"Generating {mode}...")
        self.progress["value"] = 0

        def generate():
            try:
                # Ensure output folder exists
                output_path.mkdir(parents=True, exist_ok=True)

                # Load config and build category index
                config = load_cluster_config(CLUSTER_CONFIG)
                category_index = build_stringid_category_index(
                    export_path,
                    config,
                    config.get("default_category", "Uncategorized")
                )

                # Discover language files
                all_lang_files = discover_language_files(loc_path)
                lang_files = {k: v for k, v in all_lang_files.items() if k in languages}

                # Parse English for cross-reference
                eng_lookup = {}
                if "eng" in all_lang_files:
                    eng_data = parse_language_file(all_lang_files["eng"])
                    eng_lookup = {row["string_id"]: row["str"] for row in eng_data}

                # Parse all selected languages
                language_data = {}
                total = len(lang_files)

                for i, (lang_code, lang_path) in enumerate(sorted(lang_files.items())):
                    lang_data = parse_language_file(lang_path)
                    language_data[lang_code] = lang_data

                    progress = int((i + 1) / total * 50)
                    self.root.after(0, lambda p=progress: self._update_progress(p))

                # Generate language Excels
                if mode in ("language", "all"):
                    for i, (lang_code, lang_data) in enumerate(language_data.items()):
                        display_name = LANG_DISPLAY.get(lang_code.lower(), lang_code.upper())
                        output_file = output_path / f"LanguageData_{display_name}.xlsx"

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

                        progress = 50 + int((i + 1) / len(language_data) * 25)
                        self.root.after(0, lambda p=progress: self._update_progress(p))

                # Generate word count report
                if mode in ("wordcount", "all"):
                    generator = ReportGenerator(
                        category_index,
                        config.get("default_category", "Uncategorized")
                    )

                    report = generator.generate_full_report(language_data, LANG_DISPLAY)

                    report_path = output_path / "WordCountReport.xlsx"
                    writer = ExcelReportWriter(report_path)
                    writer.write_report(report)

                # Generate summary
                if mode in ("language", "all"):
                    from collections import Counter
                    language_stats = {
                        lc: {"rows": len(data), "file": f"LanguageData_{LANG_DISPLAY.get(lc.lower(), lc.upper())}.xlsx"}
                        for lc, data in language_data.items()
                    }
                    category_stats = Counter(category_index.values())
                    summary_path = output_path / "_Summary.xlsx"
                    write_summary_excel(language_stats, dict(category_stats), summary_path)

                self.root.after(0, lambda: self._update_progress(100))
                self.root.after(0, lambda: self._set_status(f"Generated {len(language_data)} files in {output_path}"))
                self.root.after(0, lambda: messagebox.showinfo("Success", f"Generated files in:\n{output_path}"))

            except Exception as ex:
                logger.exception("Generation failed")
                # Capture exception by value in lambda (closure fix)
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
