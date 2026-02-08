#!/usr/bin/env python3
# coding: utf-8
"""
File Eraser By Name v1.0
========================
Standalone GUI tool that compares filenames between a Source and Target folder.
Any file in Target whose stem (case-insensitive, extension-ignored) matches
a stem in Source gets moved to an auto-created "Erased_Files" backup folder.

Usage: python file_eraser_by_name.py
"""

import shutil
import datetime as _dt
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "File Eraser By Name v1.0"
WINDOW_WIDTH = 720
WINDOW_HEIGHT = 620
BUTTON_WIDTH = 20
ENTRY_WIDTH = 55


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class FileEraserGUI:
    """GUI for erasing target files that match source filenames."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Path variables
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the main UI layout."""
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Title
        tk.Label(
            main_frame,
            text="File Eraser By Name",
            font=("Arial", 18, "bold")
        ).pack(pady=(0, 5))

        tk.Label(
            main_frame,
            text="Erase files in Target that match filenames in Source (case-insensitive, extension-ignored)",
            font=("Arial", 9),
            fg="#555555"
        ).pack(pady=(0, 15))

        # === Section 1: Folders ===
        folders_frame = ttk.LabelFrame(main_frame, text="1. Select Folders", padding=10)
        folders_frame.pack(fill="x", pady=5)

        # Source row
        source_frame = ttk.Frame(folders_frame)
        source_frame.pack(fill="x", pady=5)
        ttk.Label(source_frame, text="Source:", width=8).pack(side="left")
        ttk.Entry(source_frame, textvariable=self.source_var, width=ENTRY_WIDTH).pack(
            side="left", padx=5, fill="x", expand=True
        )
        ttk.Button(source_frame, text="Browse", command=self._browse_source, width=10).pack(side="left")

        # Target row
        target_frame = ttk.Frame(folders_frame)
        target_frame.pack(fill="x", pady=5)
        ttk.Label(target_frame, text="Target:", width=8).pack(side="left")
        ttk.Entry(target_frame, textvariable=self.target_var, width=ENTRY_WIDTH).pack(
            side="left", padx=5, fill="x", expand=True
        )
        ttk.Button(target_frame, text="Browse", command=self._browse_target, width=10).pack(side="left")

        # === Section 2: Process ===
        process_frame = ttk.LabelFrame(main_frame, text="2. Process", padding=10)
        process_frame.pack(fill="x", pady=10)

        ttk.Button(
            process_frame,
            text="PROCESS",
            command=self._do_process,
            width=BUTTON_WIDTH
        ).pack(pady=5, ipady=5)

        # === Console Output ===
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding=10)
        console_frame.pack(fill="both", expand=True, pady=10)

        self.console = scrolledtext.ScrolledText(
            console_frame,
            height=12,
            font=("Consolas", 9),
            state="disabled",
            wrap="word"
        )
        self.console.pack(fill="both", expand=True)

        # === Paths Info Box (bottom) ===
        paths_frame = ttk.LabelFrame(main_frame, text="Configured Paths", padding=5)
        paths_frame.pack(fill="x")

        self.paths_label = ttk.Label(
            paths_frame,
            text="Source: (not set)\nTarget: (not set)",
            font=("Courier", 8)
        )
        self.paths_label.pack(anchor="w")

        # Update paths display when variables change
        self.source_var.trace_add("write", self._update_paths_display)
        self.target_var.trace_add("write", self._update_paths_display)

        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))

        self.progress = ttk.Progressbar(status_frame, mode="determinate", length=400)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, width=20).pack(side="right")

    # ---- Path display ----

    def _update_paths_display(self, *_args):
        """Update the bottom paths info box."""
        src = self.source_var.get() or "(not set)"
        tgt = self.target_var.get() or "(not set)"
        self.paths_label.configure(text=f"Source: {src}\nTarget: {tgt}")

    # ---- Browse ----

    def _browse_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_var.set(path)

    def _browse_target(self):
        path = filedialog.askdirectory(title="Select Target Folder")
        if path:
            self.target_var.set(path)

    # ---- Logging helpers ----

    def _log(self, message: str):
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")
        self.root.update()

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.root.update()

    def _set_progress(self, current: int, total: int):
        self.progress["value"] = (current / total * 100) if total > 0 else 0
        self.root.update()

    # ---- Core logic ----

    def _do_process(self):
        """Compare source/target filenames and erase matches from target."""
        source_path = self.source_var.get().strip()
        target_path = self.target_var.get().strip()

        if not source_path:
            messagebox.showwarning("No Source", "Please select a source folder.")
            return
        if not target_path:
            messagebox.showwarning("No Target", "Please select a target folder.")
            return

        source_dir = Path(source_path)
        target_dir = Path(target_path)

        if not source_dir.is_dir():
            messagebox.showerror("Not Found", f"Source folder not found:\n{source_dir}")
            return
        if not target_dir.is_dir():
            messagebox.showerror("Not Found", f"Target folder not found:\n{target_dir}")
            return

        self._clear_console()
        self._set_status("Processing...")
        self._set_progress(0, 1)

        # 1) Collect source stems (case-insensitive)
        source_stems = set()
        for f in source_dir.iterdir():
            if f.is_file():
                source_stems.add(f.stem.lower())

        self._log(f"Source folder: {source_dir}")
        self._log(f"Source files found: {len(source_stems)}")
        self._log("")

        if not source_stems:
            self._log("No files in source folder. Nothing to do.")
            self._set_status("Done (nothing)")
            return

        # 2) Scan target for matches
        target_files = [f for f in target_dir.iterdir() if f.is_file()]
        self._log(f"Target folder: {target_dir}")
        self._log(f"Target files found: {len(target_files)}")
        self._log("")

        matches = []
        for f in target_files:
            if f.stem.lower() in source_stems:
                matches.append(f)

        self._log(f"Matching files to erase: {len(matches)}")
        self._log("")

        if not matches:
            self._log("No matching filenames found. Nothing erased.")
            self._set_status("Done (0 erased)")
            self._set_progress(1, 1)
            messagebox.showinfo("Done", "No matching filenames found.\nNothing was erased.")
            return

        # Confirm before erasing
        confirm = messagebox.askyesno(
            "Confirm Erasure",
            f"Found {len(matches)} file(s) to erase from target.\n\nContinue?",
            icon="warning"
        )
        if not confirm:
            self._log("Cancelled by user.")
            self._set_status("Cancelled")
            return

        # 3) Create Erased_Files backup folder inside target
        timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        erased_dir = target_dir / f"Erased_Files_{timestamp}"
        erased_dir.mkdir(parents=True, exist_ok=True)
        self._log(f"Backup folder: {erased_dir}")
        self._log("")

        # 4) Move matched files to backup
        self._log("=" * 55)
        self._log("ERASING FILES")
        self._log("=" * 55)

        erased_count = 0
        total = len(matches)

        for i, filepath in enumerate(sorted(matches, key=lambda p: p.name.lower()), 1):
            try:
                backup_dest = erased_dir / filepath.name
                # Handle collision (e.g. readme.txt and readme.md both match)
                counter = 1
                while backup_dest.exists():
                    backup_dest = erased_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
                    counter += 1
                shutil.move(str(filepath), str(backup_dest))
                self._log(f"  [{i}/{total}] {filepath.name}")
                erased_count += 1
            except Exception as exc:
                self._log(f"  [{i}/{total}] FAILED: {filepath.name} - {exc}")

            self._set_progress(i, total)

        # 5) Summary
        self._log("")
        self._log("=" * 55)
        self._log("SUMMARY")
        self._log("=" * 55)
        self._log(f"Source files scanned:  {len(source_stems)}")
        self._log(f"Target files scanned:  {len(target_files)}")
        self._log(f"Files erased (moved):  {erased_count}")
        self._log(f"Backup location:       {erased_dir}")

        self._set_status(f"Done ({erased_count} erased)")
        self._set_progress(1, 1)

        messagebox.showinfo(
            "Done",
            f"Erased {erased_count} file(s) from target.\n\n"
            f"Backup saved to:\n{erased_dir.name}"
        )


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    root = tk.Tk()
    FileEraserGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
