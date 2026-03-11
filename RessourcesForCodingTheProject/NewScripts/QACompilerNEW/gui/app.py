"""
QA Compiler Suite - Unified GUI
================================
Tkinter GUI with six main functions:
1. Generate Datasheets (from XML sources)
2. Transfer QA Files (OLD + NEW → QAfolder)
3. Build Master Files (QAfolder → Masterfolder)
4. Coverage Analysis
5. System Sheet Localizer
6. Update Tracker Only
"""

import queue
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
import threading
import sys
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CATEGORIES, ensure_folders_exist,
    TRACKER_UPDATE_FOLDER, TRACKER_UPDATE_QA,
    TRACKER_UPDATE_MASTER_EN, TRACKER_UPDATE_MASTER_CN,
    KNOWN_BRANCHES, KNOWN_DRIVES,
    update_branch, update_drive, validate_paths,
)
import config


# =============================================================================
# GUI CONFIGURATION
# =============================================================================

from config import VERSION
WINDOW_TITLE = f"QA Compiler Suite v{VERSION}"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 1350
BUTTON_WIDTH = 50
_MAX_LOG_LINES = 5000


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class QACompilerSuiteGUI:
    """Unified GUI for QA Compiler Suite."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, True)

        # Center window on screen
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - WINDOW_WIDTH) // 2
        y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

        # Category checkboxes state
        self.category_vars = {}

        # Store last generation results for coverage analysis
        self.last_korean_strings = {}

        # Thread-safe queue for log/progress/status updates
        self._task_queue = queue.Queue()
        self._worker_thread = None

        # Build UI
        self._build_ui()

        # Initial path validation
        self._update_path_status()

    def _build_ui(self):
        """Build the main UI layout."""
        # Title
        title_label = tk.Label(
            self.root,
            text="QA Compiler Suite",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=10)

        # === Branch + Drive Selection ===
        branch_frame = ttk.Frame(self.root)
        branch_frame.pack(fill="x", padx=15, pady=(0, 5))

        ttk.Label(branch_frame, text="Branch:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        self.branch_var = tk.StringVar(value=config.get_branch())
        branch_combo = ttk.Combobox(
            branch_frame, textvariable=self.branch_var,
            values=KNOWN_BRANCHES, width=20
        )
        branch_combo.pack(side="left", padx=5)

        ttk.Label(branch_frame, text="Drive:", font=("Arial", 10, "bold")).pack(side="left", padx=(15, 5))

        self.drive_var = tk.StringVar(value=config.get_drive())
        drive_combo = ttk.Combobox(
            branch_frame, textvariable=self.drive_var,
            values=KNOWN_DRIVES, width=5
        )
        drive_combo.pack(side="left", padx=5)

        self.path_status_label = ttk.Label(branch_frame, text="", font=("Arial", 10, "bold"))
        self.path_status_label.pack(side="left", padx=15)

        def _on_branch_change(_event=None):
            new_branch = self.branch_var.get().strip()
            if new_branch:
                config.update_branch(new_branch)
                self._update_path_status()
                self._set_status(f"Branch changed to: {new_branch}")

        def _on_drive_change(_event=None):
            new_drive = self.drive_var.get().strip()
            if new_drive:
                config.update_drive(new_drive)
                self._update_path_status()
                self._set_status(f"Drive changed to: {new_drive}:")

        branch_combo.bind("<<ComboboxSelected>>", _on_branch_change)
        branch_combo.bind("<Return>", _on_branch_change)
        drive_combo.bind("<<ComboboxSelected>>", _on_drive_change)
        drive_combo.bind("<Return>", _on_drive_change)

        # === Section 1: Generate Datasheets ===
        section1_frame = ttk.LabelFrame(self.root, text="1. Generate Datasheets", padding=8)
        section1_frame.pack(fill="x", padx=15, pady=3)

        checkbox_frame = ttk.Frame(section1_frame)
        checkbox_frame.pack(fill="x", pady=3)

        for i, category in enumerate(CATEGORIES):
            var = tk.BooleanVar(value=True)
            self.category_vars[category] = var
            cb = ttk.Checkbutton(checkbox_frame, text=category, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=10, pady=1)

        btn_frame = ttk.Frame(section1_frame)
        btn_frame.pack(fill="x", pady=3)

        ttk.Button(btn_frame, text="Select All", command=self._select_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Generate Selected", command=self._do_generate).pack(side="right", padx=5)

        # === Section 2: Transfer QA Files ===
        section2_frame = ttk.LabelFrame(self.root, text="2. Transfer QA Files", padding=8)
        section2_frame.pack(fill="x", padx=15, pady=3)

        ttk.Label(section2_frame, text="Transfer tester work from OLD and NEW folders to QAfolder").pack(pady=2)
        ttk.Button(section2_frame, text="Transfer QA Files", command=self._do_transfer, width=BUTTON_WIDTH).pack(pady=3, ipady=5)

        # === Section 3: Build Master Files ===
        section3_frame = ttk.LabelFrame(self.root, text="3. Build Master Files", padding=8)
        section3_frame.pack(fill="x", padx=15, pady=3)

        ttk.Label(section3_frame, text="Compile QA files into master files (QAfolder → Masterfolder_EN / Masterfolder_CN)").pack(pady=2)
        ttk.Button(section3_frame, text="Build Master Files", command=self._do_build, width=BUTTON_WIDTH).pack(pady=3, ipady=5)

        # === Section 4: Coverage Analysis ===
        section4_frame = ttk.LabelFrame(self.root, text="4. Coverage Analysis", padding=8)
        section4_frame.pack(fill="x", padx=15, pady=3)

        ttk.Label(section4_frame, text="Calculate coverage of language data by generated datasheets").pack(pady=2)
        ttk.Button(section4_frame, text="Run Coverage Analysis", command=self._do_coverage, width=BUTTON_WIDTH).pack(pady=3, ipady=5)

        # === Section 5: System Localizer ===
        section5_frame = ttk.LabelFrame(self.root, text="5. System Sheet Localizer", padding=8)
        section5_frame.pack(fill="x", padx=15, pady=3)

        ttk.Label(section5_frame, text="Create localized versions of System datasheet for all languages").pack(pady=2)
        ttk.Button(section5_frame, text="Localize System Sheet", command=self._do_system_localizer, width=BUTTON_WIDTH).pack(pady=3, ipady=5)

        # === Section 6: Update Tracker Only ===
        section6_frame = ttk.LabelFrame(self.root, text="6. Update Tracker Only", padding=8)
        section6_frame.pack(fill="x", padx=15, pady=3)

        ttk.Label(section6_frame, text="Retroactively add missing days to tracker from TrackerUpdateFolder").pack(pady=2)

        date_frame = ttk.Frame(section6_frame)
        date_frame.pack(fill="x", pady=3)

        ttk.Label(date_frame, text="Date:").pack(side="left", padx=5)
        self.tracker_date_var = tk.StringVar(value="")
        ttk.Entry(date_frame, textvariable=self.tracker_date_var, width=12).pack(side="left", padx=2)

        ttk.Label(date_frame, text="Time:").pack(side="left", padx=5)
        self.tracker_time_var = tk.StringVar(value="12:00")
        ttk.Entry(date_frame, textvariable=self.tracker_time_var, width=6).pack(side="left", padx=2)

        ttk.Button(date_frame, text="Most Recent", command=self._set_most_recent_datetime, width=12).pack(side="left", padx=5)
        ttk.Button(date_frame, text="Set File Dates...", command=self._do_set_file_dates, width=15).pack(side="left", padx=5)

        ttk.Button(section6_frame, text="Update Tracker", command=self._do_update_tracker, width=BUTTON_WIDTH).pack(pady=3, ipady=5)

        # === Log Panel ===
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.log_area = scrolledtext.ScrolledText(
            log_frame, font=('Consolas', 9), relief='solid', bd=1,
            wrap=tk.WORD, state='disabled', height=10
        )
        self.log_area.pack(fill="both", expand=True)

        # Tag colors (QuickTranslate pattern)
        self.log_area.tag_config('info', foreground='#333')
        self.log_area.tag_config('success', foreground='#008000')
        self.log_area.tag_config('warning', foreground='#FF8C00')
        self.log_area.tag_config('error', foreground='#FF0000')
        self.log_area.tag_config('header', foreground='#4a90d9', font=('Consolas', 9, 'bold'))

        # === Status Bar + Progress ===
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom", padx=15, pady=(0, 8))

        self.progress_value = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            status_frame, variable=self.progress_value,
            maximum=100, mode='determinate', length=400
        )
        self.progress.pack(fill="x", pady=(0, 3))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10)).pack()

    # =========================================================================
    # Log System (QuickTranslate pattern)
    # =========================================================================

    def _log(self, message: str, tag: str = 'info'):
        """Add message to log area (thread-safe)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if threading.current_thread() is threading.main_thread() and (
            self._worker_thread is None or not self._worker_thread.is_alive()
        ):
            self._log_on_main(timestamp, message, tag)
        else:
            self._task_queue.put(('log', timestamp, message, tag))

    def _log_on_main(self, timestamp: str, message: str, tag: str):
        """Insert log message into widget (must run on main thread)."""
        try:
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, f"[{timestamp}] {message}\n", tag)
            line_count = int(self.log_area.index('end-1c').split('.')[0])
            if line_count > _MAX_LOG_LINES:
                excess = line_count - _MAX_LOG_LINES
                self.log_area.delete('1.0', f'{excess}.0')
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        except tk.TclError:
            pass

    def _clear_log(self):
        """Clear the log area."""
        self.log_area.config(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state='disabled')

    def _poll_queue(self):
        """Process queued messages from worker threads."""
        try:
            while True:
                msg = self._task_queue.get_nowait()
                kind = msg[0]
                if kind == 'log':
                    _, ts, text, tag = msg
                    self._log_on_main(ts, text, tag)
                elif kind == 'progress':
                    _, value = msg
                    self.progress_value.set(value)
                elif kind == 'status':
                    _, text = msg
                    self.status_var.set(text)
                elif kind == 'done':
                    self._drain_queue()
                    self._on_operation_done()
                    return
        except queue.Empty:
            pass

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self.root.after(50, self._poll_queue)
        elif self._worker_thread is not None:
            self._drain_queue()
            self._on_operation_done()

    def _drain_queue(self):
        """Drain remaining messages from queue."""
        try:
            while True:
                msg = self._task_queue.get_nowait()
                kind = msg[0]
                if kind == 'log':
                    _, ts, text, tag = msg
                    self._log_on_main(ts, text, tag)
                elif kind == 'progress':
                    _, value = msg
                    self.progress_value.set(value)
                elif kind == 'status':
                    _, text = msg
                    self.status_var.set(text)
        except queue.Empty:
            pass

    def _on_operation_done(self):
        """Clean up after operation completes."""
        self._worker_thread = None
        self.status_var.set("Ready")

    # =========================================================================
    # Helpers
    # =========================================================================

    def _select_all(self):
        for var in self.category_vars.values():
            var.set(True)

    def _deselect_all(self):
        for var in self.category_vars.values():
            var.set(False)

    def _get_selected_categories(self):
        return [cat for cat, var in self.category_vars.items() if var.get()]

    def _update_path_status(self):
        ok, missing = validate_paths()
        if ok:
            self.path_status_label.config(text="PATHS OK", foreground="green")
        else:
            self.path_status_label.config(text="PATHS NOT FOUND", foreground="red")

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.root.update()

    def _make_callbacks(self):
        """Create log_callback and progress_callback for worker threads."""
        def log_cb(message, tag='info'):
            self._task_queue.put(('log', datetime.now().strftime("%H:%M:%S"), message, tag))

        def progress_cb(pct):
            self._task_queue.put(('progress', pct))

        def status_cb(text):
            self._task_queue.put(('status', text))

        return log_cb, progress_cb, status_cb

    def _start_operation(self, status_text="Working..."):
        """Common setup for starting a background operation."""
        self._clear_log()
        self.progress_value.set(0)
        self.status_var.set(status_text)

    # =========================================================================
    # Action Handlers
    # =========================================================================

    def _do_generate(self):
        """Generate datasheets for selected categories."""
        selected = self._get_selected_categories()

        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one category.")
            return

        ok, missing = validate_paths()
        if not ok:
            messagebox.showerror(
                "Path Error",
                "Cannot generate — paths not found:\n\n"
                + "\n".join(f"  {name}" for name in missing)
                + "\n\nCheck your Branch and Drive settings."
            )
            return

        self._start_operation(f"Generating datasheets for: {', '.join(selected)}...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                from generators import generate_datasheets
                log_cb(f"=== Generate Datasheets ===", 'header')
                log_cb(f"Categories: {', '.join(selected)}")
                results = generate_datasheets(selected)
                self.last_korean_strings = results.get("korean_strings", {})
                log_cb(f"Generation complete: {', '.join(results.get('categories_processed', []))}", 'success')
                progress_cb(100)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"Generation failed: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _do_transfer(self):
        """Transfer QA files from OLD/NEW to QAfolder."""
        self._start_operation("Transferring QA files...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                log_cb("=== Transfer QA Files ===", 'header')

                # STEP 1: Auto-populate QAfolderNEW
                log_cb("Populating QAfolderNEW with fresh datasheets...")
                from core.populate_new import populate_qa_folder_new
                populate_success, populate_msg = populate_qa_folder_new()

                if not populate_success:
                    log_cb(f"Populate failed: {populate_msg}", 'error')
                    log_cb("Run 'Generate Datasheets' first, then try again.", 'warning')
                    self._task_queue.put(('done',))
                    return

                log_cb("QAfolderNEW populated", 'success')
                progress_cb(30)

                # STEP 2: Transfer
                log_cb("Transferring QA data (OLD + NEW → QAfolder)...")
                from core.transfer import transfer_qa_files
                success = transfer_qa_files()

                if success:
                    log_cb("Transfer complete", 'success')
                else:
                    log_cb("Transfer failed", 'error')
                progress_cb(100)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"Transfer failed: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _do_build(self):
        """Build master files from QAfolder."""
        self._start_operation("Building master files...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                from core.compiler import run_compiler
                run_compiler(log_callback=log_cb, progress_callback=progress_cb)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"BUILD FAILED: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _do_coverage(self):
        """Run coverage analysis on generated datasheets."""
        self._start_operation("Running coverage analysis...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                from config import LANGUAGE_FOLDER, VOICE_RECORDING_SHEET_FOLDER, DATASHEET_OUTPUT
                from tracker.coverage import run_coverage_analysis, load_korean_strings_from_datasheets

                log_cb("=== Coverage Analysis ===", 'header')
                category_strings = load_korean_strings_from_datasheets(DATASHEET_OUTPUT)

                if not category_strings:
                    log_cb(f"No datasheets found in: {DATASHEET_OUTPUT}", 'error')
                    log_cb("Generate datasheets first.", 'warning')
                    self._task_queue.put(('done',))
                    return

                log_cb(f"Loaded {len(category_strings)} categories from datasheets")
                progress_cb(30)

                report = run_coverage_analysis(
                    LANGUAGE_FOLDER,
                    VOICE_RECORDING_SHEET_FOLDER,
                    category_strings,
                    DATASHEET_OUTPUT,
                )

                if report.total_master_strings > 0:
                    pct = report.total_covered_strings / report.total_master_strings * 100
                    log_cb(f"Coverage: {report.total_covered_strings:,} / {report.total_master_strings:,} ({pct:.1f}%)", 'success')
                else:
                    log_cb("No master language data found", 'warning')
                progress_cb(100)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"Coverage analysis failed: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _do_system_localizer(self):
        """Run System Sheet Localizer."""
        from tkinter import filedialog

        input_file = filedialog.askopenfilename(
            title="Select System Excel File",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not input_file:
            return

        self._start_operation("Localizing System sheet...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                from config import LANGUAGE_FOLDER, DATASHEET_OUTPUT
                from system_localizer import process_system_sheet

                log_cb("=== System Sheet Localizer ===", 'header')
                input_path = Path(input_file)
                output_folder = DATASHEET_OUTPUT / "System_LQA_All"

                result = process_system_sheet(
                    input_path=input_path,
                    lang_folder=LANGUAGE_FOLDER,
                    output_folder=output_folder
                )

                if result.get("success", False):
                    files_created = result.get("files_created", 0)
                    log_cb(f"Localization complete: {files_created} files created", 'success')
                else:
                    errors = result.get("errors", ["Unknown error"])
                    for err in errors[:5]:
                        log_cb(f"Error: {err}", 'error')
                progress_cb(100)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"Localization failed: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)

    def _set_most_recent_datetime(self):
        now = datetime.now()
        self.tracker_date_var.set(now.strftime("%Y-%m-%d"))
        self.tracker_time_var.set(now.strftime("%H:%M"))

    def _do_set_file_dates(self):
        """Set LastWriteTime on all xlsx files in a selected folder."""
        from tkinter import filedialog
        import os

        date_str = self.tracker_date_var.get().strip()
        time_str = self.tracker_time_var.get().strip()

        if not date_str:
            messagebox.showwarning("No Date", "Please enter a date (YYYY-MM-DD)")
            return

        if not time_str:
            time_str = "12:00"

        try:
            datetime_str = f"{date_str} {time_str}"
            target_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            target_timestamp = target_datetime.timestamp()
        except ValueError:
            messagebox.showerror(
                "Invalid Date/Time",
                f"Invalid format: {date_str} {time_str}\nUse YYYY-MM-DD HH:MM"
            )
            return

        TRACKER_UPDATE_FOLDER.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_QA.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_MASTER_EN.mkdir(parents=True, exist_ok=True)
        TRACKER_UPDATE_MASTER_CN.mkdir(parents=True, exist_ok=True)

        selected_folder = filedialog.askdirectory(
            title="Select Folder to Set File Dates",
            initialdir=str(TRACKER_UPDATE_FOLDER),
            mustexist=True
        )
        if not selected_folder:
            return

        selected_path = Path(selected_folder)
        xlsx_files = list(selected_path.rglob("*.xlsx"))
        xlsx_files = [f for f in xlsx_files if not f.name.startswith("~")]

        if not xlsx_files:
            messagebox.showwarning("No Files", f"No xlsx files found in:\n{selected_path}")
            return

        count = 0
        folders_updated = set()
        for xlsx_path in xlsx_files:
            try:
                os.utime(xlsx_path, (target_timestamp, target_timestamp))
                count += 1
                parent_folder = xlsx_path.parent
                if parent_folder not in folders_updated:
                    os.utime(parent_folder, (target_timestamp, target_timestamp))
                    folders_updated.add(parent_folder)
            except Exception as e:
                self._log(f"Could not set date on {xlsx_path.name}: {e}", 'warning')

        try:
            os.utime(selected_path, (target_timestamp, target_timestamp))
        except Exception:
            pass

        self._log(f"Set date to {date_str} on {count} files + {len(folders_updated)+1} folders", 'success')

    def _do_update_tracker(self):
        """Update tracker from QAFolderForTracker without rebuilding masters."""
        self._start_operation("Updating tracker...")
        log_cb, progress_cb, status_cb = self._make_callbacks()

        def run():
            try:
                from core.tracker_update import update_tracker_only

                log_cb("=== Update Tracker ===", 'header')
                success, message, entries = update_tracker_only()

                if success:
                    if entries:
                        dates = sorted(set(e["date"] for e in entries))
                        users = sorted(set(e["user"] for e in entries))
                        log_cb(f"Tracker updated: {len(entries)} entries", 'success')
                        log_cb(f"  Dates: {', '.join(dates)}")
                        log_cb(f"  Users: {', '.join(users[:10])}")
                    else:
                        log_cb(message, 'info')
                else:
                    log_cb(f"Tracker update failed: {message}", 'error')
                progress_cb(100)
            except Exception as e:
                traceback.print_exc()
                log_cb(f"Tracker update failed: {e}", 'error')
            self._task_queue.put(('done',))

        self._worker_thread = threading.Thread(target=run, daemon=True)
        self._worker_thread.start()
        self.root.after(50, self._poll_queue)


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
