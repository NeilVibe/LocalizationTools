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
from config import CATEGORIES, ensure_folders_exist


# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "QA Compiler Suite v2.0"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
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
                self.root.after(0, lambda: self._on_generate_error(str(e)))

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
        """Transfer QA files from OLD/NEW to QAfolder."""
        self._set_status("Transferring QA files...")
        self._start_progress()

        def run():
            try:
                # Import transfer function
                from core.transfer import transfer_qa_files
                success = transfer_qa_files()

                self.root.after(0, lambda: self._on_transfer_complete(success))
            except ImportError:
                # Fallback to original compile_qa
                try:
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "QAExcelCompiler"))
                    from compile_qa import transfer_qa_files
                    success = transfer_qa_files()
                    self.root.after(0, lambda: self._on_transfer_complete(success))
                except Exception as e:
                    self.root.after(0, lambda: self._on_transfer_error(str(e)))
            except Exception as e:
                self.root.after(0, lambda: self._on_transfer_error(str(e)))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

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
                    self.root.after(0, lambda: self._on_build_error(str(e)))
            except Exception as e:
                self.root.after(0, lambda: self._on_build_error(str(e)))

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
                )

                self.root.after(0, lambda: self._on_coverage_complete(report))
            except ImportError as e:
                self.root.after(0, lambda: self._on_coverage_error(f"Coverage module not available: {e}"))
            except Exception as e:
                self.root.after(0, lambda: self._on_coverage_error(str(e)))

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
