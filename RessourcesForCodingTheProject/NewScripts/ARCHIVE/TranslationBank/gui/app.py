"""
Translation Bank GUI
====================
Tkinter GUI for creating and transferring translation banks.

Features:
- File/Folder mode toggle
- Create Bank section (source → bank JSON)
- Transfer section (bank + target → translated target)
- Console output with statistics
- Progress bar
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import sys
import traceback

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    DEFAULT_SOURCE_FOLDER, DEFAULT_BANK_OUTPUT, DEFAULT_TARGET_FOLDER,
    BANK_EXTENSION, BANK_EXTENSION_JSON, log
)


# =============================================================================
# GUI CONFIGURATION
# =============================================================================

WINDOW_TITLE = "Translation Bank v1.0"
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700
BUTTON_WIDTH = 20
ENTRY_WIDTH = 55


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class TranslationBankGUI:
    """GUI for Translation Bank operations."""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Mode: File or Folder
        self.mode_var = tk.StringVar(value="folder")

        # Path variables
        self.source_var = tk.StringVar(value=str(DEFAULT_SOURCE_FOLDER))
        self.bank_var = tk.StringVar()
        self.target_var = tk.StringVar(value=str(DEFAULT_TARGET_FOLDER))

        # JSON mode (for debugging - slower but human-readable)
        self.json_mode_var = tk.BooleanVar(value=False)

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the main UI layout."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = tk.Label(
            main_frame,
            text="Translation Bank",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 15))

        # === Mode Selection ===
        mode_frame = ttk.LabelFrame(main_frame, text="Mode", padding=10)
        mode_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            mode_frame, text="File", variable=self.mode_var,
            value="file", command=self._on_mode_change
        ).pack(side="left", padx=20)

        ttk.Radiobutton(
            mode_frame, text="Folder (Recursive)", variable=self.mode_var,
            value="folder", command=self._on_mode_change
        ).pack(side="left", padx=20)

        # === Section 1: Create Bank ===
        section1_frame = ttk.LabelFrame(main_frame, text="1. Create Bank", padding=10)
        section1_frame.pack(fill="x", pady=10)

        # Source row
        source_frame = ttk.Frame(section1_frame)
        source_frame.pack(fill="x", pady=5)

        ttk.Label(source_frame, text="Source:", width=8).pack(side="left")
        ttk.Entry(
            source_frame, textvariable=self.source_var, width=ENTRY_WIDTH
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            source_frame, text="Browse", command=self._browse_source, width=10
        ).pack(side="left")

        # Options row
        options_frame = ttk.Frame(section1_frame)
        options_frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            options_frame,
            text="Export as JSON (slower, for debugging)",
            variable=self.json_mode_var
        ).pack(side="left", padx=5)

        # Generate button
        generate_btn = ttk.Button(
            section1_frame,
            text="Generate Bank",
            command=self._do_generate_bank,
            width=BUTTON_WIDTH
        )
        generate_btn.pack(pady=10, ipady=5)

        # === Section 2: Transfer Translations ===
        section2_frame = ttk.LabelFrame(main_frame, text="2. Transfer Translations", padding=10)
        section2_frame.pack(fill="x", pady=10)

        # Bank row
        bank_frame = ttk.Frame(section2_frame)
        bank_frame.pack(fill="x", pady=5)

        ttk.Label(bank_frame, text="Bank:", width=8).pack(side="left")
        ttk.Entry(
            bank_frame, textvariable=self.bank_var, width=ENTRY_WIDTH
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            bank_frame, text="Browse", command=self._browse_bank, width=10
        ).pack(side="left")

        # Target row
        target_frame = ttk.Frame(section2_frame)
        target_frame.pack(fill="x", pady=5)

        ttk.Label(target_frame, text="Target:", width=8).pack(side="left")
        ttk.Entry(
            target_frame, textvariable=self.target_var, width=ENTRY_WIDTH
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            target_frame, text="Browse", command=self._browse_target, width=10
        ).pack(side="left")

        # Transfer button
        transfer_btn = ttk.Button(
            section2_frame,
            text="Transfer",
            command=self._do_transfer,
            width=BUTTON_WIDTH
        )
        transfer_btn.pack(pady=10, ipady=5)

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

        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))

        self.progress = ttk.Progressbar(status_frame, mode='determinate', length=400)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            width=20
        )
        status_label.pack(side="right")

    def _on_mode_change(self):
        """Handle mode change."""
        mode = self.mode_var.get()
        self._log(f"Mode changed to: {mode}")

    def _log(self, message: str):
        """Write message to console."""
        self.console.configure(state="normal")
        self.console.insert("end", message + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")
        self.root.update()

    def _clear_console(self):
        """Clear console output."""
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _set_status(self, text: str):
        """Update status text."""
        self.status_var.set(text)
        self.root.update()

    def _set_progress(self, current: int, total: int):
        """Update progress bar."""
        if total > 0:
            pct = current / total * 100
            self.progress["value"] = pct
        else:
            self.progress["value"] = 0
        self.root.update()

    def _browse_source(self):
        """Browse for source file/folder."""
        mode = self.mode_var.get()
        if mode == "file":
            path = filedialog.askopenfilename(
                title="Select Source XML File",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
        else:
            path = filedialog.askdirectory(
                title="Select Source Folder",
                initialdir=str(DEFAULT_SOURCE_FOLDER)
            )

        if path:
            self.source_var.set(path)

    def _browse_bank(self):
        """Browse for bank file."""
        path = filedialog.askopenfilename(
            title="Select Bank File",
            filetypes=[("Bank files", "*.pkl *.json"), ("Pickle files", "*.pkl"), ("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=str(DEFAULT_BANK_OUTPUT)
        )
        if path:
            self.bank_var.set(path)

    def _browse_target(self):
        """Browse for target file/folder."""
        mode = self.mode_var.get()
        if mode == "file":
            path = filedialog.askopenfilename(
                title="Select Target XML File",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
        else:
            path = filedialog.askdirectory(
                title="Select Target Folder",
                initialdir=str(DEFAULT_TARGET_FOLDER)
            )

        if path:
            self.target_var.set(path)

    def _do_generate_bank(self):
        """Generate translation bank from source."""
        source_path = self.source_var.get().strip()
        if not source_path:
            messagebox.showwarning("No Source", "Please select a source file or folder.")
            return

        source = Path(source_path)
        if not source.exists():
            messagebox.showerror("Not Found", f"Source path not found:\n{source}")
            return

        # Determine output extension based on mode
        use_json = self.json_mode_var.get()
        ext = BANK_EXTENSION_JSON if use_json else BANK_EXTENSION

        # Determine output path
        if source.is_file():
            output_name = source.stem + "_bank" + ext
        else:
            output_name = source.name + "_bank" + ext

        output_path = DEFAULT_BANK_OUTPUT / output_name

        # Ask for output location
        if use_json:
            filetypes = [("JSON files", "*.json"), ("All files", "*.*")]
        else:
            filetypes = [("Pickle files", "*.pkl"), ("JSON files", "*.json"), ("All files", "*.*")]

        save_path = filedialog.asksaveasfilename(
            title="Save Bank As",
            defaultextension=ext,
            initialdir=str(DEFAULT_BANK_OUTPUT),
            initialfile=output_name,
            filetypes=filetypes
        )

        if not save_path:
            return

        output_path = Path(save_path)

        self._clear_console()
        self._log(f"Building bank from: {source}")
        self._log(f"Output: {output_path}")
        self._log("")
        self._set_status("Building bank...")

        def run():
            try:
                from core.bank_builder import build_bank, save_bank

                def progress_cb(msg, current, total):
                    self.root.after(0, lambda: self._log(msg))
                    self.root.after(0, lambda: self._set_progress(current, total))

                recursive = self.mode_var.get() == "folder"
                bank = build_bank(source, recursive=recursive, progress_callback=progress_cb)

                if save_bank(bank, output_path):
                    self.root.after(0, lambda: self._on_generate_complete(bank, output_path))
                else:
                    self.root.after(0, lambda: self._on_generate_error("Failed to save bank"))

            except Exception as e:
                traceback.print_exc()
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_generate_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_generate_complete(self, bank, output_path):
        """Handle bank generation complete."""
        self._set_status("Bank generated!")
        self._set_progress(100, 100)

        entry_count = bank["metadata"]["entry_count"]
        l1_count = len(bank["indices"]["level1"])
        l2_count = len(bank["indices"]["level2"])
        l3_count = len(bank["indices"]["level3"])

        self._log("")
        self._log("=" * 50)
        self._log("BANK GENERATION COMPLETE")
        self._log("=" * 50)
        self._log(f"Total entries:   {entry_count:,}")
        self._log(f"Level 1 keys:    {l1_count:,}")
        self._log(f"Level 2 keys:    {l2_count:,}")
        self._log(f"Level 3 keys:    {l3_count:,}")
        self._log(f"Saved to: {output_path}")
        self._log("")

        # Auto-fill bank field for transfer
        self.bank_var.set(str(output_path))

        messagebox.showinfo(
            "Success",
            f"Bank generated!\n\nEntries: {entry_count:,}\nSaved to: {output_path.name}"
        )

    def _on_generate_error(self, error_msg):
        """Handle bank generation error."""
        self._set_status("Generation failed")
        self._set_progress(0, 100)
        self._log(f"ERROR: {error_msg}")
        messagebox.showerror("Error", f"Bank generation failed:\n{error_msg}")

    def _do_transfer(self):
        """Transfer translations from bank to target."""
        bank_path = self.bank_var.get().strip()
        target_path = self.target_var.get().strip()

        if not bank_path:
            messagebox.showwarning("No Bank", "Please select a bank file.")
            return

        if not target_path:
            messagebox.showwarning("No Target", "Please select a target file or folder.")
            return

        bank = Path(bank_path)
        target = Path(target_path)

        if not bank.exists():
            messagebox.showerror("Not Found", f"Bank file not found:\n{bank}")
            return

        if not target.exists():
            messagebox.showerror("Not Found", f"Target path not found:\n{target}")
            return

        # Ask for output location
        mode = self.mode_var.get()
        if mode == "file":
            output_path = filedialog.asksaveasfilename(
                title="Save Translated File As",
                defaultextension=".xml",
                initialdir=str(target.parent),
                initialfile=target.stem + "_translated.xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
        else:
            output_path = filedialog.askdirectory(
                title="Select Output Folder",
                initialdir=str(target.parent)
            )

        if not output_path:
            return

        output = Path(output_path)

        self._clear_console()
        self._log(f"Bank:   {bank}")
        self._log(f"Target: {target}")
        self._log(f"Output: {output}")
        self._log("")
        self._set_status("Transferring...")

        def run():
            try:
                from core.bank_transfer import transfer_translations

                def progress_cb(msg, current, total):
                    self.root.after(0, lambda: self._log(msg))
                    self.root.after(0, lambda: self._set_progress(current, total))

                recursive = self.mode_var.get() == "folder"
                stats = transfer_translations(
                    bank, target, output,
                    recursive=recursive,
                    progress_callback=progress_cb
                )

                self.root.after(0, lambda: self._on_transfer_complete(stats, bank, target))

            except Exception as e:
                traceback.print_exc()
                err_msg = str(e)
                self.root.after(0, lambda msg=err_msg: self._on_transfer_error(msg))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_transfer_complete(self, stats, bank_path, target_path):
        """Handle transfer complete."""
        self._set_status("Transfer complete!")
        self._set_progress(100, 100)

        # Show report in console
        report = stats.to_report(str(bank_path), str(target_path))
        self._log(report)

        # Summary dialog
        if stats.total_entries > 0:
            summary = (
                f"Transfer Complete!\n\n"
                f"Total entries: {stats.total_entries:,}\n"
                f"Hits: {stats.total_hits:,} ({stats.hit_rate:.1f}%)\n"
                f"  Level 1: {stats.hit_level1:,}\n"
                f"  Level 2: {stats.hit_level2:,}\n"
                f"  Level 3: {stats.hit_level3:,}\n"
                f"Misses: {stats.miss:,}\n\n"
                f"Files modified: {stats.files_modified}"
            )
        else:
            summary = "No entries needed translation."

        messagebox.showinfo("Transfer Complete", summary)

    def _on_transfer_error(self, error_msg):
        """Handle transfer error."""
        self._set_status("Transfer failed")
        self._set_progress(0, 100)
        self._log(f"ERROR: {error_msg}")
        messagebox.showerror("Error", f"Transfer failed:\n{error_msg}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def run_gui():
    """Launch the GUI application."""
    root = tk.Tk()
    app = TranslationBankGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
