"""
Dialog Windows

Configuration dialogs for LINE CHECK and TERM CHECK with ENG/KR BASE selection.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional, Callable, List, Dict, Any

try:
    from config import (
        SOURCE_BASE_KR, SOURCE_BASE_ENG,
        get_ui_text, get_settings, get_output_dir
    )
    from core.line_check import run_line_check, save_line_check_results
    from core.term_check import run_term_check, save_term_check_results
except ImportError:
    from ..config import (
        SOURCE_BASE_KR, SOURCE_BASE_ENG,
        get_ui_text, get_settings, get_output_dir
    )
    from ..core.line_check import run_line_check, save_line_check_results
    from ..core.term_check import run_term_check, save_term_check_results


def center_dialog(dialog: tk.Toplevel, parent: tk.Tk) -> None:
    """Center a dialog relative to its parent."""
    dialog.update_idletasks()

    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()

    x = parent_x + (parent_width - dialog_width) // 2
    y = parent_y + (parent_height - dialog_height) // 2

    dialog.geometry(f"+{x}+{y}")


class BaseCheckDialog:
    """Base class for LINE CHECK and TERM CHECK dialogs."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        progress_var: Optional[tk.StringVar] = None
    ):
        self.parent = parent
        self.progress_var = progress_var or tk.StringVar(value="Ready")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        center_dialog(self.dialog, parent)

        # Data storage
        self.source_data: Dict[str, Any] = {'files': None, 'folder': None, 'type': None}
        self.glossary_data: Dict[str, Any] = {'files': None, 'folder': None, 'type': None}
        self.eng_file: Optional[str] = None

        # Variables
        self.mode_var = tk.StringVar(value="self")
        self.source_base_var = tk.StringVar(value=SOURCE_BASE_KR)
        self.filter_sentences_var = tk.BooleanVar(value=True)
        self.length_threshold_var = tk.IntVar(value=15)
        self.min_occurrence_var = tk.IntVar(value=2)

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create dialog widgets."""
        # Source Base Selection (NEW!)
        source_base_frame = ttk.LabelFrame(self.dialog, text=get_ui_text('source_base'))
        source_base_frame.pack(padx=10, pady=5, fill="x")

        ttk.Radiobutton(
            source_base_frame,
            text=get_ui_text('kr_base'),
            variable=self.source_base_var,
            value=SOURCE_BASE_KR,
            command=self._on_source_base_change
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Radiobutton(
            source_base_frame,
            text=get_ui_text('eng_base'),
            variable=self.source_base_var,
            value=SOURCE_BASE_ENG,
            command=self._on_source_base_change
        ).pack(anchor="w", padx=5, pady=2)

        # English file selection (for ENG BASE)
        self.eng_frame = ttk.LabelFrame(self.dialog, text=get_ui_text('select_eng'))
        self.eng_frame.pack(padx=10, pady=5, fill="x")

        self.eng_file_btn = tk.Button(
            self.eng_frame,
            text=get_ui_text('select_files'),
            command=self._select_eng_file,
            state=tk.DISABLED
        )
        self.eng_file_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.eng_label = tk.Label(self.eng_frame, text=get_ui_text('no_data_selected'))
        self.eng_label.pack(side=tk.LEFT, padx=10)

        # Check Mode
        mode_frame = ttk.LabelFrame(self.dialog, text=get_ui_text('check_mode'))
        mode_frame.pack(padx=10, pady=5, fill="x")

        ttk.Radiobutton(
            mode_frame,
            text=get_ui_text('self_check'),
            variable=self.mode_var,
            value="self",
            command=self._on_mode_change
        ).pack(anchor="w", padx=5, pady=2)

        ttk.Radiobutton(
            mode_frame,
            text=get_ui_text('external_check'),
            variable=self.mode_var,
            value="external",
            command=self._on_mode_change
        ).pack(anchor="w", padx=5, pady=2)

        # Source Data
        source_frame = ttk.LabelFrame(self.dialog, text=get_ui_text('source_data'))
        source_frame.pack(padx=10, pady=5, fill="x")

        self.source_file_btn = tk.Button(
            source_frame,
            text=get_ui_text('select_files'),
            command=self._select_source_files
        )
        self.source_file_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.source_folder_btn = tk.Button(
            source_frame,
            text=get_ui_text('select_folder'),
            command=self._select_source_folder
        )
        self.source_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.source_label = tk.Label(source_frame, text=get_ui_text('no_data_selected'))
        self.source_label.pack(side=tk.LEFT, padx=10)

        # External Glossary Data (initially disabled)
        glossary_frame = ttk.LabelFrame(self.dialog, text=get_ui_text('external_glossary'))
        glossary_frame.pack(padx=10, pady=5, fill="x")

        self.glossary_file_btn = tk.Button(
            glossary_frame,
            text=get_ui_text('select_files'),
            command=self._select_glossary_files,
            state=tk.DISABLED
        )
        self.glossary_file_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.glossary_folder_btn = tk.Button(
            glossary_frame,
            text=get_ui_text('select_folder'),
            command=self._select_glossary_folder,
            state=tk.DISABLED
        )
        self.glossary_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.glossary_label = tk.Label(glossary_frame, text=get_ui_text('no_data_selected'))
        self.glossary_label.pack(side=tk.LEFT, padx=10)

        # Options
        options_frame = ttk.LabelFrame(self.dialog, text="Options")
        options_frame.pack(padx=10, pady=5, fill="x")

        ttk.Checkbutton(
            options_frame,
            text="Filter sentences (entries ending with . ? !)",
            variable=self.filter_sentences_var
        ).pack(anchor="w", padx=5, pady=2)

        length_row = tk.Frame(options_frame)
        length_row.pack(anchor="w", padx=5, pady=2)
        tk.Label(length_row, text="Max source length:").pack(side=tk.LEFT)
        tk.Spinbox(
            length_row,
            from_=5, to=50,
            textvariable=self.length_threshold_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)

        occurrence_row = tk.Frame(options_frame)
        occurrence_row.pack(anchor="w", padx=5, pady=2)
        tk.Label(occurrence_row, text="Min occurrences:").pack(side=tk.LEFT)
        tk.Spinbox(
            occurrence_row,
            from_=1, to=10,
            textvariable=self.min_occurrence_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)

        # Start button
        self.start_btn = tk.Button(
            self.dialog,
            text=get_ui_text('start_check'),
            command=self._start_check,
            relief="raised",
            bd=3,
            padx=20,
            pady=5,
            font=('Helvetica', 10, 'bold')
        )
        self.start_btn.pack(pady=15)

        # Progress
        progress_label = tk.Label(self.dialog, textvariable=self.progress_var)
        progress_label.pack(pady=5)

    def _on_source_base_change(self) -> None:
        """Handle source base selection change."""
        if self.source_base_var.get() == SOURCE_BASE_ENG:
            self.eng_file_btn.config(state=tk.NORMAL)
        else:
            self.eng_file_btn.config(state=tk.DISABLED)
            self.eng_file = None
            self.eng_label.config(text=get_ui_text('no_data_selected'))

    def _on_mode_change(self) -> None:
        """Handle check mode change."""
        if self.mode_var.get() == "external":
            self.glossary_file_btn.config(state=tk.NORMAL)
            self.glossary_folder_btn.config(state=tk.NORMAL)
        else:
            self.glossary_file_btn.config(state=tk.DISABLED)
            self.glossary_folder_btn.config(state=tk.DISABLED)

    def _select_eng_file(self) -> None:
        """Select English XML file for ENG BASE."""
        files = filedialog.askopenfilenames(
            title=get_ui_text('select_eng'),
            filetypes=[
                ("XML Files", "*.xml"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.eng_file = files[0]
            self.eng_label.config(text=os.path.basename(self.eng_file))

    def _select_source_files(self) -> None:
        """Select source files."""
        files = filedialog.askopenfilenames(
            title=get_ui_text('select_target'),
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.source_data['files'] = files
            self.source_data['folder'] = None
            self.source_data['type'] = 'files'
            self.source_label.config(text=f"{len(files)} files selected")
            self.source_folder_btn.config(state=tk.DISABLED)

    def _select_source_folder(self) -> None:
        """Select source folder."""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_data['folder'] = folder
            self.source_data['files'] = None
            self.source_data['type'] = 'folder'
            self.source_label.config(text=f"Folder: {os.path.basename(folder)}")
            self.source_file_btn.config(state=tk.DISABLED)

    def _select_glossary_files(self) -> None:
        """Select glossary files."""
        files = filedialog.askopenfilenames(
            title="Select Glossary Files",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.glossary_data['files'] = files
            self.glossary_data['folder'] = None
            self.glossary_data['type'] = 'files'
            self.glossary_label.config(text=f"{len(files)} files selected")
            self.glossary_folder_btn.config(state=tk.DISABLED)

    def _select_glossary_folder(self) -> None:
        """Select glossary folder."""
        folder = filedialog.askdirectory(title="Select Glossary Folder")
        if folder:
            self.glossary_data['folder'] = folder
            self.glossary_data['files'] = None
            self.glossary_data['type'] = 'folder'
            self.glossary_label.config(text=f"Folder: {os.path.basename(folder)}")
            self.glossary_file_btn.config(state=tk.DISABLED)

    def _get_source_files(self) -> List[str]:
        """Get list of source files."""
        if self.source_data['type'] == 'files':
            return list(self.source_data['files'])
        elif self.source_data['type'] == 'folder':
            files = []
            for root, dirs, filenames in os.walk(self.source_data['folder']):
                for filename in filenames:
                    if filename.lower().endswith(('.xml', '.txt', '.tsv')):
                        files.append(os.path.join(root, filename))
            return files
        return []

    def _get_glossary_files(self) -> Optional[List[str]]:
        """Get list of glossary files (or None for self-check)."""
        if self.mode_var.get() == "self":
            return None

        if self.glossary_data['type'] == 'files':
            return list(self.glossary_data['files'])
        elif self.glossary_data['type'] == 'folder':
            files = []
            for root, dirs, filenames in os.walk(self.glossary_data['folder']):
                for filename in filenames:
                    if filename.lower().endswith(('.xml', '.txt', '.tsv')):
                        files.append(os.path.join(root, filename))
            return files
        return None

    def _validate(self) -> bool:
        """Validate dialog inputs."""
        if not self.source_data['type']:
            messagebox.showwarning("Warning", "Please select source data")
            return False

        if self.mode_var.get() == "external" and not self.glossary_data['type']:
            messagebox.showwarning("Warning", "Please select glossary data")
            return False

        if self.source_base_var.get() == SOURCE_BASE_ENG and not self.eng_file:
            messagebox.showwarning("Warning", "Please select English XML file for ENG BASE mode")
            return False

        return True

    def _start_check(self) -> None:
        """Start the check (to be overridden)."""
        raise NotImplementedError


class LineCheckDialog(BaseCheckDialog):
    """LINE CHECK configuration dialog."""

    def __init__(self, parent: tk.Tk, progress_var: Optional[tk.StringVar] = None):
        super().__init__(parent, get_ui_text('line_check_title'), progress_var)

    def _start_check(self) -> None:
        """Start LINE CHECK."""
        if not self._validate():
            return

        # Get output file
        output_path = filedialog.asksaveasfilename(
            title="Save Line Report As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not output_path:
            return

        self.dialog.destroy()

        def task():
            try:
                def progress_callback(msg: str):
                    self.progress_var.set(msg)
                    self.parent.update_idletasks()

                source_files = self._get_source_files()

                results = run_line_check(
                    target_files=source_files,
                    eng_file=self.eng_file,
                    source_base=self.source_base_var.get(),
                    filter_sentences=self.filter_sentences_var.get(),
                    length_threshold=self.length_threshold_var.get(),
                    min_occurrence=self.min_occurrence_var.get(),
                    progress_callback=progress_callback
                )

                # Save results (clean output - no filenames)
                save_line_check_results(results, output_path, include_filenames=False)

                self.progress_var.set(f"LINE CHECK complete: {len(results)} inconsistent sources")
                messagebox.showinfo("Done", f"Line report saved to:\n{output_path}")

            except Exception as e:
                self.progress_var.set(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=task, daemon=True).start()


class TermCheckDialog(BaseCheckDialog):
    """TERM CHECK configuration dialog."""

    def __init__(self, parent: tk.Tk, progress_var: Optional[tk.StringVar] = None):
        super().__init__(parent, get_ui_text('term_check_title'), progress_var)

    def _start_check(self) -> None:
        """Start TERM CHECK."""
        if not self._validate():
            return

        self.dialog.destroy()

        def task():
            try:
                def progress_callback(msg: str):
                    self.progress_var.set(msg)
                    self.parent.update_idletasks()

                source_files = self._get_source_files()
                glossary_files = self._get_glossary_files()

                results = run_term_check(
                    target_files=source_files,
                    glossary_files=glossary_files,
                    eng_file=self.eng_file,
                    source_base=self.source_base_var.get(),
                    filter_sentences=self.filter_sentences_var.get(),
                    length_threshold=self.length_threshold_var.get(),
                    min_occurrence=self.min_occurrence_var.get(),
                    progress_callback=progress_callback
                )

                # Generate output path
                import datetime
                output_dir = get_output_dir()
                dt_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f"TermCheck_{dt_str}.txt")

                # Save results (clean output - no filenames)
                save_term_check_results(results, output_path, include_filenames=False)

                total_issues = sum(r.issue_count for r in results)
                self.progress_var.set(f"TERM CHECK complete: {len(results)} terms, {total_issues} issues")
                messagebox.showinfo("Done", f"Term report saved to:\n{output_path}")

            except Exception as e:
                self.progress_var.set(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=task, daemon=True).start()
