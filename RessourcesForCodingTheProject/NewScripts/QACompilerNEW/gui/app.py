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

Layout: Horizontal split — controls (left) | log + progress (right)
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
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
BUTTON_WIDTH = 40
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
        self.root.resizable(True, True)

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

        # Set sash position after window renders
        self.root.after(100, self._set_initial_sash)

    def _build_ui(self):
        """Build the main UI layout — horizontal split."""
        # === Top bar: Title + Branch/Drive ===
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=(8, 4))

        tk.Label(
            top_frame, text="QA Compiler Suite",
            font=("Arial", 14, "bold")
        ).pack(side="left", padx=(5, 20))

        ttk.Label(top_frame, text="Branch:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 3))

        self.branch_var = tk.StringVar(value=config.get_branch())
        branch_combo = ttk.Combobox(
            top_frame, textvariable=self.branch_var,
            values=KNOWN_BRANCHES, width=18
        )
        branch_combo.pack(side="left", padx=3)

        ttk.Label(top_frame, text="Drive:", font=("Arial", 10, "bold")).pack(side="left", padx=(12, 3))

        self.drive_var = tk.StringVar(value=config.get_drive())
        drive_combo = ttk.Combobox(
            top_frame, textvariable=self.drive_var,
            values=KNOWN_DRIVES, width=4
        )
        drive_combo.pack(side="left", padx=3)

        self.path_status_label = ttk.Label(top_frame, text="", font=("Arial", 10, "bold"))
        self.path_status_label.pack(side="left", padx=12)

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

        ttk.Separator(self.root, orient='horizontal').pack(fill="x", padx=10, pady=(4, 0))

        # === Horizontal PanedWindow: Controls (left) | Log (right) ===
        self._paned = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL, sashwidth=6,
            bg='#cccccc', sashrelief='raised'
        )
        self._paned.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Left pane: scrollable controls ---
        left_outer = tk.Frame(self._paned)

        left_canvas = tk.Canvas(left_outer, highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_outer, orient='vertical', command=left_canvas.yview)
        self._left_inner = tk.Frame(left_canvas, padx=5)

        left_cw = left_canvas.create_window((0, 0), window=self._left_inner, anchor='nw')
        self._left_inner.bind('<Configure>', lambda e: left_canvas.configure(
            scrollregion=left_canvas.bbox('all')))
        left_canvas.bind('<Configure>', lambda e: left_canvas.itemconfigure(
            left_cw, width=e.width))

        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # Mousewheel scrolling for left pane
        def _on_mousewheel(event):
            if event.delta:
                left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                left_canvas.yview_scroll(1, "units")
        left_canvas.bind('<MouseWheel>', _on_mousewheel)
        left_canvas.bind('<Button-4>', _on_mousewheel)
        left_canvas.bind('<Button-5>', _on_mousewheel)
        self._left_inner.bind('<MouseWheel>', _on_mousewheel)
        self._left_inner.bind('<Button-4>', _on_mousewheel)
        self._left_inner.bind('<Button-5>', _on_mousewheel)

        self._build_controls(self._left_inner)

        # --- Right pane: Log + Progress ---
        right_pane = tk.Frame(self._paned, padx=5)

        log_frame = ttk.LabelFrame(right_pane, text="Log", padding=5)
        log_frame.pack(fill="both", expand=True, pady=(0, 5))

        self.log_area = scrolledtext.ScrolledText(
            log_frame, font=('Consolas', 9), relief='solid', bd=1,
            wrap=tk.WORD, state='disabled'
        )
        self.log_area.pack(fill="both", expand=True)

        # Tag colors (QuickTranslate pattern)
        self.log_area.tag_config('info', foreground='#333')
        self.log_area.tag_config('success', foreground='#008000')
        self.log_area.tag_config('warning', foreground='#FF8C00')
        self.log_area.tag_config('error', foreground='#FF0000')
        self.log_area.tag_config('header', foreground='#4a90d9', font=('Consolas', 9, 'bold'))

        # Progress + Status
        progress_frame = tk.Frame(right_pane)
        progress_frame.pack(fill="x", pady=(0, 3))

        self.progress_value = tk.DoubleVar(value=0)
        ttk.Progressbar(
            progress_frame, variable=self.progress_value,
            maximum=100, mode='determinate'
        ).pack(fill="x", pady=(0, 3))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.status_var, font=("Arial", 10)).pack()

        # Add panes
        self._paned.add(left_outer, minsize=400)
        self._paned.add(right_pane, minsize=250)

    def _build_controls(self, parent):
        """Build all control sections in the left pane."""
        # === Section 1: Generate Datasheets ===
        s1 = ttk.LabelFrame(parent, text="1. Generate Datasheets", padding=6)
        s1.pack(fill="x", pady=3)

        checkbox_frame = ttk.Frame(s1)
        checkbox_frame.pack(fill="x", pady=2)

        for i, category in enumerate(CATEGORIES):
            var = tk.BooleanVar(value=True)
            self.category_vars[category] = var
            cb = ttk.Checkbutton(checkbox_frame, text=category, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=1)

        btn_frame = ttk.Frame(s1)
        btn_frame.pack(fill="x", pady=2)

        ttk.Button(btn_frame, text="Select All", command=self._select_all).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Deselect All", command=self._deselect_all).pack(side="left", padx=3)
        ttk.Button(btn_frame, text="Generate Selected", command=self._do_generate).pack(side="right", padx=3)

        # === Section 2: Transfer QA Files ===
        s2 = ttk.LabelFrame(parent, text="2. Transfer QA Files", padding=6)
        s2.pack(fill="x", pady=3)

        ttk.Label(s2, text="Transfer tester work from OLD and NEW folders to QAfolder").pack(pady=1)
        ttk.Button(s2, text="Transfer QA Files", command=self._do_transfer, width=BUTTON_WIDTH).pack(pady=2, ipady=3)

        # === Section 3: Build Master Files ===
        s3 = ttk.LabelFrame(parent, text="3. Build Master Files", padding=6)
        s3.pack(fill="x", pady=3)

        ttk.Label(s3, text="Compile QA files into master files").pack(pady=1)
        ttk.Button(s3, text="Build Master Files", command=self._do_build, width=BUTTON_WIDTH).pack(pady=2, ipady=3)

        # === Section 4: Coverage Analysis ===
        s4 = ttk.LabelFrame(parent, text="4. Coverage Analysis", padding=6)
        s4.pack(fill="x", pady=3)

        ttk.Label(s4, text="Calculate coverage of language data by datasheets").pack(pady=1)
        ttk.Button(s4, text="Run Coverage Analysis", command=self._do_coverage, width=BUTTON_WIDTH).pack(pady=2, ipady=3)

        # === Section 5: System Localizer ===
        s5 = ttk.LabelFrame(parent, text="5. System Sheet Localizer", padding=6)
        s5.pack(fill="x", pady=3)

        ttk.Label(s5, text="Create localized versions of System datasheet").pack(pady=1)
        ttk.Button(s5, text="Localize System Sheet", command=self._do_system_localizer, width=BUTTON_WIDTH).pack(pady=2, ipady=3)

        # === Section 6: Update Tracker Only ===
        s6 = ttk.LabelFrame(parent, text="6. Update Tracker Only", padding=6)
        s6.pack(fill="x", pady=3)

        ttk.Label(s6, text="Retroactively add missing days to tracker").pack(pady=1)

        date_frame = ttk.Frame(s6)
        date_frame.pack(fill="x", pady=2)

        ttk.Label(date_frame, text="Date:").pack(side="left", padx=3)
        self.tracker_date_var = tk.StringVar(value="")
        ttk.Entry(date_frame, textvariable=self.tracker_date_var, width=12).pack(side="left", padx=2)

        ttk.Label(date_frame, text="Time:").pack(side="left", padx=3)
        self.tracker_time_var = tk.StringVar(value="12:00")
        ttk.Entry(date_frame, textvariable=self.tracker_time_var, width=6).pack(side="left", padx=2)

        ttk.Button(date_frame, text="Most Recent", command=self._set_most_recent_datetime, width=11).pack(side="left", padx=3)
        ttk.Button(date_frame, text="Set File Dates...", command=self._do_set_file_dates, width=14).pack(side="left", padx=3)

        ttk.Button(s6, text="Update Tracker", command=self._do_update_tracker, width=BUTTON_WIDTH).pack(pady=2, ipady=3)

    def _set_initial_sash(self):
        """Set PanedWindow sash to ~50% left / 50% right split."""
        total_width = self._paned.winfo_width()
        if total_width > 1:
            self._paned.sash_place(0, int(total_width * 0.50), 0)

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
                log_cb("=== Generate Datasheets ===", 'header')
                log_cb(f"Categories: {', '.join(selected)}")
                results = generate_datasheets(selected, log_callback=log_cb)
                self.last_korean_strings = results.get("korean_strings", {})
                if results.get("errors"):
                    for err in results["errors"]:
                        log_cb(f"Error: {err}", 'error')
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
                from core.populate_new import populate_qa_folder_new
                populate_success, populate_msg = populate_qa_folder_new(log_callback=log_cb)

                if not populate_success:
                    log_cb(f"Populate failed: {populate_msg}", 'error')
                    log_cb("Run 'Generate Datasheets' first, then try again.", 'warning')
                    self._task_queue.put(('done',))
                    return

                progress_cb(30)

                # STEP 2: Transfer
                from core.transfer import transfer_qa_files
                success = transfer_qa_files(log_callback=log_cb)

                if not success:
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
                category_strings = load_korean_strings_from_datasheets(DATASHEET_OUTPUT, log_callback=log_cb)

                if not category_strings:
                    log_cb(f"No datasheets found in: {DATASHEET_OUTPUT}", 'error')
                    log_cb("Generate datasheets first.", 'warning')
                    self._task_queue.put(('done',))
                    return

                progress_cb(30)

                report = run_coverage_analysis(
                    LANGUAGE_FOLDER,
                    VOICE_RECORDING_SHEET_FOLDER,
                    category_strings,
                    DATASHEET_OUTPUT,
                    log_callback=log_cb,
                )

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

                log_cb(f"Input: {input_path.name}")
                log_cb(f"Output: {output_folder}")

                result = process_system_sheet(
                    input_path=input_path,
                    lang_folder=LANGUAGE_FOLDER,
                    output_folder=output_folder,
                    log_callback=log_cb
                )

                if result.get("success", False):
                    files_created = result.get("files_created", 0)
                    languages = result.get("languages", [])
                    log_cb(f"Localization complete: {files_created} files created", 'success')
                    if languages:
                        log_cb(f"Languages: {', '.join(languages)}")
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
                success, message, entries = update_tracker_only(log_callback=log_cb)

                if not success:
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
