"""
QA Compiler Suite - Unified GUI
================================
Tkinter GUI with three main functions:
1. Generate Datasheets (from XML sources)
2. Transfer QA Files (OLD + NEW → QAfolder)
3. Build Master Files (QAfolder → Masterfolder)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CATEGORIES, ensure_folders_exist,
    TRACKER_UPDATE_FOLDER, TRACKER_UPDATE_QA,
    TRACKER_UPDATE_MASTER_EN, TRACKER_UPDATE_MASTER_CN
)


# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "QA Compiler Suite v2.0"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 1000
BUTTON_WIDTH = 50


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class QACompilerSuiteGUI:
    """Unified GUI for QA Compiler Suite."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)

        # Category checkboxes state
        self.category_vars = {}

        # Store last generation results for coverage analysis
        self.last_korean_strings = {}

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the main UI layout."""
        # Title
        title_label = tk.Label(
            self.root,
            text="QA Compiler Suite",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=15)

        # === Section 1: Generate Datasheets ===
        section1_frame = ttk.LabelFrame(self.root, text="1. Generate Datasheets", padding=10)
        section1_frame.pack(fill="x", padx=15, pady=5)

        # Category checkboxes grid (3 columns)
        checkbox_frame = ttk.Frame(section1_frame)
        checkbox_frame.pack(fill="x", pady=5)

        for i, category in enumerate(CATEGORIES):
            var = tk.BooleanVar(value=True)
            self.category_vars[category] = var
            cb = ttk.Checkbutton(checkbox_frame, text=category, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=10, pady=2)

        # Select/Deselect All buttons
        btn_frame = ttk.Frame(section1_frame)
        btn_frame.pack(fill="x", pady=5)

        select_all_btn = ttk.Button(btn_frame, text="Select All", command=self._select_all)
        select_all_btn.pack(side="left", padx=5)

        deselect_all_btn = ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all)
        deselect_all_btn.pack(side="left", padx=5)

        generate_btn = ttk.Button(
            btn_frame,
            text="Generate Selected",
            command=self._do_generate
        )
        generate_btn.pack(side="right", padx=5)

        # === Section 2: Transfer QA Files ===
        section2_frame = ttk.LabelFrame(self.root, text="2. Transfer QA Files", padding=10)
        section2_frame.pack(fill="x", padx=15, pady=5)

        transfer_desc = ttk.Label(
            section2_frame,
            text="Transfer tester work from OLD and NEW folders to QAfolder\n(QAfolderOLD + QAfolderNEW → QAfolder)"
        )
        transfer_desc.pack(pady=5)

        transfer_btn = ttk.Button(
            section2_frame,
            text="Transfer QA Files",
            command=self._do_transfer,
            width=BUTTON_WIDTH
        )
        transfer_btn.pack(pady=5, ipady=8)

        # === Section 3: Build Master Files ===
        section3_frame = ttk.LabelFrame(self.root, text="3. Build Master Files", padding=10)
        section3_frame.pack(fill="x", padx=15, pady=5)

        build_desc = ttk.Label(
            section3_frame,
            text="Compile QA files into master files with progress tracking\n(QAfolder → Masterfolder_EN / Masterfolder_CN)"
        )
        build_desc.pack(pady=5)

        build_btn = ttk.Button(
            section3_frame,
            text="Build Master Files",
            command=self._do_build,
            width=BUTTON_WIDTH
        )
        build_btn.pack(pady=5, ipady=8)

        # === Section 4: Coverage Analysis ===
        section4_frame = ttk.LabelFrame(self.root, text="4. Coverage Analysis", padding=10)
        section4_frame.pack(fill="x", padx=15, pady=5)

        coverage_desc = ttk.Label(
            section4_frame,
            text="Calculate coverage of language data by generated datasheets.\nRun after 'Generate Datasheets' to see coverage statistics."
        )
        coverage_desc.pack(pady=5)

        coverage_btn = ttk.Button(
            section4_frame,
            text="Run Coverage Analysis",
            command=self._do_coverage,
            width=BUTTON_WIDTH
        )
        coverage_btn.pack(pady=5, ipady=8)

        # === Section 5: System Localizer ===
        section5_frame = ttk.LabelFrame(self.root, text="5. System Sheet Localizer", padding=10)
        section5_frame.pack(fill="x", padx=15, pady=5)

        localizer_desc = ttk.Label(
            section5_frame,
            text="Create localized versions of System datasheet for all languages.\nSelect System Excel file → Creates System_LQA_All/ with all language versions."
        )
        localizer_desc.pack(pady=5)

        localizer_btn = ttk.Button(
            section5_frame,
            text="Localize System Sheet",
            command=self._do_system_localizer,
            width=BUTTON_WIDTH
        )
        localizer_btn.pack(pady=5, ipady=8)

        # === Section 6: Update Tracker Only ===
        section6_frame = ttk.LabelFrame(self.root, text="6. Update Tracker Only", padding=10)
        section6_frame.pack(fill="x", padx=15, pady=5)

        tracker_desc = ttk.Label(
            section6_frame,
            text="Retroactively add missing days to tracker from TrackerUpdateFolder.\n"
                 "Place QA files in QAfolder/, Master files in Masterfolder_EN/ or Masterfolder_CN/"
        )
        tracker_desc.pack(pady=5)

        # Date picker row
        date_frame = ttk.Frame(section6_frame)
        date_frame.pack(fill="x", pady=5)

        ttk.Label(date_frame, text="Set Date (YYYY-MM-DD):").pack(side="left", padx=5)
        self.tracker_date_var = tk.StringVar(value="")
        date_entry = ttk.Entry(date_frame, textvariable=self.tracker_date_var, width=15)
        date_entry.pack(side="left", padx=5)

        set_date_btn = ttk.Button(
            date_frame,
            text="Set File Dates...",
            command=self._do_set_file_dates,
            width=15
        )
        set_date_btn.pack(side="left", padx=5)

        ttk.Label(date_frame, text="(Select folder to update)").pack(side="left", padx=5)

        tracker_btn = ttk.Button(
            section6_frame,
            text="Update Tracker",
            command=self._do_update_tracker,
            width=BUTTON_WIDTH
        )
        tracker_btn.pack(pady=5, ipady=8)

        # === Status Bar ===
        self.status_var = tk.StringVar(value="Ready")
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom", padx=15, pady=10)

        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Arial", 10)
        )
        status_label.pack()

        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=400)
        self.progress.pack(pady=5)

    def _select_all(self):
        """Select all category checkboxes."""
        for var in self.category_vars.values():
            var.set(True)

    def _deselect_all(self):
        """Deselect all category checkboxes."""
        for var in self.category_vars.values():
            var.set(False)

    def _get_selected_categories(self):
        """Get list of selected categories."""
        return [cat for cat, var in self.category_vars.items() if var.get()]

    def _set_status(self, text: str):
        """Update status text."""
        self.status_var.set(text)
        self.root.update()

    def _start_progress(self):
        """Start indeterminate progress bar."""
        self.progress.start(10)

    def _stop_progress(self):
        """Stop progress bar."""
        self.progress.stop()

    # =========================================================================
    # Action Handlers
    # =========================================================================

    def _do_generate(self):
        """Generate datasheets for selected categories."""
        selected = self._get_selected_categories()

        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one category.")
            return

        self._set_status(f"Generating datasheets for: {', '.join(selected)}...")
        self._start_progress()

        def run():
            try:
                # Import generators here to avoid circular imports
                from generators import generate_datasheets
                results = generate_datasheets(selected)

                self.root.after(0, lambda: self._on_generate_complete(results))
            except ImportError:
                self.root.after(0, lambda: self._on_generate_error(
                    "Generator modules not yet implemented.\nPlease run from original scripts."
                ))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_generate_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_generate_complete(self, results):
        """Handle generate completion."""
        self._stop_progress()
        self._set_status("Generation complete!")
        # Store korean_strings for coverage analysis
        self.last_korean_strings = results.get("korean_strings", {})
        messagebox.showinfo(
            "Success",
            f"Datasheets generated!\n\nCategories: {', '.join(results.get('categories_processed', []))}\nCheck console for details."
        )

    def _on_generate_error(self, error_msg):
        """Handle generate error."""
        self._stop_progress()
        self._set_status("Generation failed - check console")
        messagebox.showerror("Error", f"Generation failed:\n{error_msg}")

    def _do_transfer(self):
        """
        Transfer QA files from OLD/NEW to QAfolder.

        SEAMLESS FLOW (one button does everything):
        1. Auto-populate QAfolderNEW with fresh datasheets
        2. Transfer data from QAfolderOLD → merge with QAfolderNEW → output to QAfolder

        STRICT MODE: If any datasheet is missing or stale, stops immediately.
        """
        self._set_status("Checking datasheets & populating QAfolderNEW...")
        self._start_progress()

        def run():
            try:
                # STEP 1: Auto-populate QAfolderNEW (STRICT MODE)
                from core.populate_new import populate_qa_folder_new

                populate_success, populate_msg = populate_qa_folder_new()

                if not populate_success:
                    # Datasheets missing or stale - stop immediately
                    self.root.after(0, lambda msg=populate_msg: self._on_populate_failed(msg))
                    return

                # STEP 2: Transfer (merge OLD data with NEW sheets)
                self._set_status_safe("Transferring QA data...")

                from core.transfer import transfer_qa_files
                success = transfer_qa_files()

                self.root.after(0, lambda: self._on_transfer_complete(success))

            except ImportError as e:
                # Fallback to original compile_qa
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "QAExcelCompiler"))
                    from compile_qa import transfer_qa_files
                    success = transfer_qa_files()
                    self.root.after(0, lambda: self._on_transfer_complete(success))
                except Exception as e2:
                    err_msg = str(e2)
                    self.root.after(0, lambda msg=err_msg: self._on_transfer_error(msg))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_transfer_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _set_status_safe(self, text):
        """Thread-safe status update."""
        self.root.after(0, lambda: self._set_status(text))

    def _on_populate_failed(self, message):
        """Handle populate failure - datasheets missing or stale."""
        self._stop_progress()
        self._set_status("Transfer stopped - datasheets need refresh")
        messagebox.showwarning(
            "Datasheets Not Ready",
            f"{message}\n\n"
            "Please run 'Generate Datasheets' first (select ALL categories),\n"
            "then try Transfer again."
        )

    def _on_transfer_complete(self, success):
        """Handle transfer completion."""
        self._stop_progress()
        if success:
            self._set_status("Transfer complete!")
            messagebox.showinfo("Success", "Transfer completed!\nCheck console for details.")
        else:
            self._set_status("Transfer failed - check console")
            messagebox.showerror("Error", "Transfer failed.\nCheck console for details.")

    def _on_transfer_error(self, error_msg):
        """Handle transfer error."""
        self._stop_progress()
        self._set_status("Transfer failed - check console")
        messagebox.showerror("Error", f"Transfer failed:\n{error_msg}")

    def _do_build(self):
        """Build master files from QAfolder."""
        self._set_status("Building master files...")
        self._start_progress()

        def run():
            try:
                # Import main build function
                from core.compiler import run_compiler
                run_compiler()

                self.root.after(0, self._on_build_complete)
            except ImportError:
                # Fallback to original compile_qa
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "QAExcelCompiler"))
                    from compile_qa import main as compile_main
                    compile_main()
                    self.root.after(0, self._on_build_complete)
                except Exception as e:
                    err_msg = str(e)
                    self.root.after(0, lambda msg=err_msg: self._on_build_error(msg))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_build_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_build_complete(self):
        """Handle build completion."""
        self._stop_progress()
        self._set_status("Build complete!")
        messagebox.showinfo("Success", "Build completed!\nCheck console for details.")

    def _on_build_error(self, error_msg):
        """Handle build error."""
        self._stop_progress()
        self._set_status("Build failed - check console")
        messagebox.showerror("Error", f"Build failed:\n{error_msg}")

    def _do_coverage(self):
        """Run coverage analysis on generated datasheets."""
        self._set_status("Running coverage analysis...")
        self._start_progress()

        def run():
            try:
                from config import LANGUAGE_FOLDER, VOICE_RECORDING_SHEET_FOLDER, DATASHEET_OUTPUT
                from tracker.coverage import run_coverage_analysis, load_korean_strings_from_datasheets

                # ALWAYS load from existing Excel files in GeneratedDatasheets folder
                category_strings = load_korean_strings_from_datasheets(DATASHEET_OUTPUT)

                if not category_strings:
                    self.root.after(0, lambda: self._on_coverage_error(
                        f"No datasheets found in:\n{DATASHEET_OUTPUT}\n\nPlace generated Excel files there first."
                    ))
                    return

                report = run_coverage_analysis(
                    LANGUAGE_FOLDER,
                    VOICE_RECORDING_SHEET_FOLDER,
                    category_strings,
                    DATASHEET_OUTPUT,  # Output folder for word count
                )

                self.root.after(0, lambda: self._on_coverage_complete(report))
            except ImportError as e:
                err_msg = f"Coverage module not available: {e}"
                self.root.after(0, lambda msg=err_msg: self._on_coverage_error(msg))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_coverage_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_coverage_complete(self, report):
        """Handle coverage analysis completion."""
        self._stop_progress()
        self._set_status("Coverage analysis complete!")

        # Format summary for dialog
        if report.total_master_strings > 0:
            pct = report.total_covered_strings / report.total_master_strings * 100
            summary = (
                f"Coverage: {report.total_covered_strings:,} / {report.total_master_strings:,} strings ({pct:.1f}%)\n\n"
                f"Categories analyzed: {len(report.categories)}\n\n"
                "See console for detailed report."
            )
        else:
            summary = "No master language data found.\nCheck LANGUAGE_FOLDER in config.py."

        messagebox.showinfo("Coverage Analysis", summary)

    def _on_coverage_error(self, error_msg):
        """Handle coverage analysis error."""
        self._stop_progress()
        self._set_status("Coverage analysis failed - check console")
        messagebox.showerror("Error", f"Coverage analysis failed:\n{error_msg}")

    def _do_system_localizer(self):
        """Run System Sheet Localizer - create localized versions for all languages."""
        from tkinter import filedialog

        # Ask user to select System Excel file
        input_file = filedialog.askopenfilename(
            title="Select System Excel File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )

        if not input_file:
            return  # User cancelled

        self._set_status("Localizing System sheet...")
        self._start_progress()

        def run():
            try:
                from config import LANGUAGE_FOLDER, DATASHEET_OUTPUT
                from system_localizer import process_system_sheet

                input_path = Path(input_file)
                output_folder = DATASHEET_OUTPUT / "System_LQA_All"

                result = process_system_sheet(
                    input_path=input_path,
                    lang_folder=LANGUAGE_FOLDER,
                    output_folder=output_folder
                )

                self.root.after(0, lambda: self._on_localizer_complete(result, output_folder))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_localizer_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_localizer_complete(self, result, output_folder):
        """Handle localizer completion."""
        self._stop_progress()

        if result.get("success", False):
            files_created = result.get("files_created", 0)
            languages = result.get("languages", [])
            self._set_status(f"Localization complete! {files_created} files created.")
            messagebox.showinfo(
                "Success",
                f"System Localization Complete!\n\n"
                f"Files created: {files_created}\n"
                f"Languages: {', '.join(languages[:10])}{'...' if len(languages) > 10 else ''}\n\n"
                f"Output: {output_folder}"
            )
        else:
            errors = result.get("errors", ["Unknown error"])
            self._set_status("Localization completed with errors")
            messagebox.showwarning(
                "Completed with Errors",
                f"Localization completed but with errors:\n\n" + "\n".join(errors[:5])
            )

    def _on_localizer_error(self, error_msg):
        """Handle localizer error."""
        self._stop_progress()
        self._set_status("Localization failed - check console")
        messagebox.showerror("Error", f"System localization failed:\n{error_msg}")

    def _do_set_file_dates(self):
        """Set LastWriteTime on all xlsx files in a selected folder."""
        from tkinter import filedialog
        import os

        date_str = self.tracker_date_var.get().strip()

        if not date_str:
            messagebox.showwarning("No Date", "Please enter a date (YYYY-MM-DD)")
            return

        # Validate date format
        try:
            from datetime import datetime
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            target_timestamp = target_date.timestamp()
        except ValueError:
            messagebox.showerror("Invalid Date", f"Invalid date format: {date_str}\nUse YYYY-MM-DD (e.g., 2025-01-18)")
            return

        # Ensure TrackerUpdateFolder exists
        TRACKER_UPDATE_FOLDER.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_QA.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_MASTER_EN.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_MASTER_CN.mkdir(parents=True, exist_ok=True)

        # Ask user to select folder
        selected_folder = filedialog.askdirectory(
            title="Select Folder to Set File Dates",
            initialdir=str(TRACKER_UPDATE_FOLDER),
            mustexist=True
        )

        if not selected_folder:
            return  # User cancelled

        selected_path = Path(selected_folder)

        # Find all xlsx files (recursively)
        xlsx_files = list(selected_path.rglob("*.xlsx"))
        xlsx_files = [f for f in xlsx_files if not f.name.startswith("~")]

        if not xlsx_files:
            messagebox.showwarning("No Files", f"No xlsx files found in:\n{selected_path}")
            return

        # Set mtime on all files
        count = 0
        for xlsx_path in xlsx_files:
            try:
                os.utime(xlsx_path, (target_timestamp, target_timestamp))
                count += 1
            except Exception as e:
                print(f"  WARN: Could not set date on {xlsx_path.name}: {e}")

        self._set_status(f"Set date to {date_str} on {count} files")
        messagebox.showinfo("Done", f"Set LastWriteTime to {date_str} on {count} file(s)\n\nFolder: {selected_path.name}")

    def _do_update_tracker(self):
        """Update tracker from QAFolderForTracker without rebuilding masters."""
        self._set_status("Updating tracker...")
        self._start_progress()

        def run():
            try:
                from core.tracker_update import update_tracker_only
                success, message, entries = update_tracker_only()

                self.root.after(0, lambda: self._on_update_tracker_complete(success, message, entries))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_update_tracker_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_update_tracker_complete(self, success, message, entries):
        """Handle tracker update completion."""
        self._stop_progress()

        if success:
            self._set_status("Tracker update complete!")
            # Build summary
            if entries:
                dates = sorted(set(e["date"] for e in entries))
                users = sorted(set(e["user"] for e in entries))
                total_done = sum(e["done"] for e in entries)
                summary = (
                    f"Tracker Updated!\n\n"
                    f"Entries: {len(entries)}\n"
                    f"Dates: {', '.join(dates)}\n"
                    f"Users: {', '.join(users[:5])}{'...' if len(users) > 5 else ''}\n"
                    f"Total Done: {total_done}\n\n"
                    "Check console for details."
                )
            else:
                summary = message
            messagebox.showinfo("Success", summary)
        else:
            self._set_status("Tracker update failed - check console")
            messagebox.showerror("Error", f"Tracker update failed:\n{message}")

    def _on_update_tracker_error(self, error_msg):
        """Handle tracker update error."""
        self._stop_progress()
        self._set_status("Tracker update failed - check console")
        messagebox.showerror("Error", f"Tracker update failed:\n{error_msg}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def run_gui():
    """Launch the GUI application."""
    ensure_folders_exist()

    root = tk.Tk()
    app = QACompilerSuiteGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
