"""
TMX Tools Tab — Tab 3 in QuickTranslate.

Section 1: MemoQ-TMX Conversion (single + batch)
Section 2: TMX Cleaner → Excel export
"""
from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

logger = logging.getLogger(__name__)

# TMX BCP-47 language codes (intentionally separate from config.LANGUAGE_NAMES)
TMX_LANGUAGE_OPTIONS = {
    "English (US)": "en-US",
    "French (FR)": "fr-FR",
    "German (DE)": "de-DE",
    "Traditional Chinese (TW)": "zh-TW",
    "Simplified Chinese (CN)": "zh-CN",
    "Japanese (JP)": "ja-JP",
    "Italian (IT)": "it-IT",
    "Portuguese (Brazil)": "pt-BR",
    "Russian (RU)": "ru-RU",
    "European Spanish (ES)": "es-ES",
    "Latin American Spanish (MX)": "es-MX",
    "Polish (PL)": "pl-PL",
    "Turkish (TR)": "tr-TR",
}


class TMXToolsTab(tk.Frame):
    """TMX Tools tab with conversion and cleaning sections."""

    def __init__(self, parent: tk.Widget, log_callback=None):
        super().__init__(parent, bg='#f0f0f0')
        self._log_callback = log_callback
        self._source_folder = tk.StringVar()
        self._target_lang = tk.StringVar(value="English (US)")

        self._build_ui()

    def _build_ui(self):
        # ============================================================
        # Section 1: MemoQ-TMX Conversion
        # ============================================================
        conv_frame = tk.LabelFrame(
            self, text="MemoQ-TMX Conversion",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        conv_frame.pack(fill=tk.X, pady=(0, 12), padx=5)

        # Source folder
        src_row = tk.Frame(conv_frame, bg='#f0f0f0')
        src_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(src_row, text="Source Folder:", font=('Segoe UI', 9),
                 bg='#f0f0f0').pack(side=tk.LEFT)
        tk.Button(src_row, text="Browse...", command=self._browse_source,
                  font=('Segoe UI', 9), cursor='hand2').pack(side=tk.LEFT, padx=(8, 0))
        self._src_label = tk.Label(src_row, textvariable=self._source_folder,
                                   font=('Segoe UI', 9), bg='#f0f0f0', fg='#333',
                                   anchor='w', wraplength=400)
        self._src_label.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

        # Target language
        lang_row = tk.Frame(conv_frame, bg='#f0f0f0')
        lang_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lang_row, text="Target Language:", font=('Segoe UI', 9),
                 bg='#f0f0f0').pack(side=tk.LEFT)
        lang_combo = ttk.Combobox(lang_row, textvariable=self._target_lang,
                                  values=list(TMX_LANGUAGE_OPTIONS.keys()),
                                  state='readonly', width=30)
        lang_combo.pack(side=tk.LEFT, padx=(8, 0))

        # Buttons
        btn_row = tk.Frame(conv_frame, bg='#f0f0f0')
        btn_row.pack(fill=tk.X, pady=(0, 4))
        tk.Button(btn_row, text="Convert Single Folder",
                  command=self._on_convert_single,
                  font=('Segoe UI', 9, 'bold'), bg='#4472C4', fg='white',
                  relief='flat', padx=14, pady=4, cursor='hand2').pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_row, text="Batch Convert (Multi-Folder)",
                  command=self._on_batch_convert,
                  font=('Segoe UI', 9, 'bold'), bg='#4472C4', fg='white',
                  relief='flat', padx=14, pady=4, cursor='hand2').pack(side=tk.LEFT)

        # ============================================================
        # Section 2: TMX Cleaner → Excel
        # ============================================================
        clean_frame = tk.LabelFrame(
            self, text="TMX Cleaner -> Excel",
            font=('Segoe UI', 10, 'bold'),
            bg='#f0f0f0', fg='#555', padx=15, pady=8,
        )
        clean_frame.pack(fill=tk.X, pady=(0, 8), padx=5)

        desc = tk.Label(
            clean_frame,
            text="Select a TMX file to clean all CAT tool markup and export to Excel (3 columns: StrOrigin, Correction, StringID).",
            font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
            wraplength=500, justify='left',
        )
        desc.pack(fill=tk.X, pady=(0, 8))

        tk.Button(clean_frame, text="Select TMX -> Clean & Export to Excel",
                  command=self._on_clean_to_excel,
                  font=('Segoe UI', 9, 'bold'), bg='#5cb85c', fg='white',
                  relief='flat', padx=14, pady=4, cursor='hand2').pack(anchor='w')

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------
    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select source folder with XML files")
        if folder:
            self._source_folder.set(folder)

    def _get_target_lang_code(self) -> str:
        name = self._target_lang.get()
        return TMX_LANGUAGE_OPTIONS.get(name, "en-US")

    # ------------------------------------------------------------------
    # Convert Single
    # ------------------------------------------------------------------
    def _on_convert_single(self):
        folder = self._source_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("No Folder", "Please select a source folder first.")
            return

        out_file = filedialog.asksaveasfilename(
            title="Save TMX as...",
            defaultextension=".tmx",
            filetypes=[("TMX files", "*.tmx")],
            initialfile=os.path.basename(folder) + ".tmx",
        )
        if not out_file:
            return

        lang_code = self._get_target_lang_code()
        logger.info(f"[TMX Convert] Single: {folder} -> {out_file} ({lang_code})")

        def _run():
            from core.tmx_tools import combine_xmls_to_tmx
            ok = combine_xmls_to_tmx(folder, out_file, lang_code, postprocess=True)
            msg = f"TMX created: {out_file}" if ok else "TMX conversion failed — check logs."
            self.after(0, lambda: messagebox.showinfo("TMX Conversion", msg))

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # Batch Convert
    # ------------------------------------------------------------------
    def _on_batch_convert(self):
        base_folder = filedialog.askdirectory(title="Select parent folder containing subfolders")
        if not base_folder:
            return

        # List subfolders
        subfolders = sorted([
            os.path.join(base_folder, d) for d in os.listdir(base_folder)
            if os.path.isdir(os.path.join(base_folder, d))
        ])
        if not subfolders:
            messagebox.showwarning("No Subfolders", "No subfolders found in selected directory.")
            return

        # Subfolder picker dialog
        picker = tk.Toplevel(self)
        picker.title("Select subfolders to convert")
        picker.geometry("500x400")
        picker.transient(self.winfo_toplevel())
        picker.grab_set()

        tk.Label(picker, text="Select subfolders (Ctrl+Click for multiple):",
                 font=('Segoe UI', 10)).pack(padx=10, pady=(10, 5), anchor='w')

        listbox = tk.Listbox(picker, selectmode=tk.EXTENDED, font=('Segoe UI', 9))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for sf in subfolders:
            listbox.insert(tk.END, os.path.basename(sf))

        # MemoQ postprocess toggle
        pp_var = tk.BooleanVar(value=True)
        tk.Checkbutton(picker, text="MemoQ postprocess (bpt/ept/ph wrapping)",
                       variable=pp_var, font=('Segoe UI', 9)).pack(padx=10, anchor='w')

        def _do_batch():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Select at least one subfolder.")
                return
            selected = [subfolders[i] for i in selection]
            picker.destroy()

            out_dir = filedialog.askdirectory(title="Select output directory for TMX files")
            if not out_dir:
                return

            lang_code = self._get_target_lang_code()
            postprocess = pp_var.get()
            logger.info(f"[TMX Batch] {len(selected)} folders -> {out_dir} ({lang_code}, pp={postprocess})")

            def _run():
                from core.tmx_tools import batch_tmx_from_folders
                results = batch_tmx_from_folders(selected, out_dir, lang_code, postprocess=postprocess)
                ok_count = sum(1 for _, _, ok in results if ok)
                msg = f"Batch complete: {ok_count}/{len(results)} succeeded.\nOutput: {out_dir}"
                self.after(0, lambda: messagebox.showinfo("Batch TMX", msg))

            threading.Thread(target=_run, daemon=True).start()

        tk.Button(picker, text="Convert Selected", command=_do_batch,
                  font=('Segoe UI', 10, 'bold'), bg='#4472C4', fg='white',
                  relief='flat', padx=14, pady=4).pack(pady=10)

    # ------------------------------------------------------------------
    # TMX Cleaner → Excel
    # ------------------------------------------------------------------
    def _on_clean_to_excel(self):
        fpath = filedialog.askopenfilename(
            title="Select TMX file to clean and convert to Excel",
            filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")]
        )
        if not fpath:
            return

        logger.info(f"[TMX Cleaner] Processing: {fpath}")

        def _run():
            from core.tmx_tools import clean_and_convert_to_excel
            try:
                out = clean_and_convert_to_excel(fpath)
                self.after(0, lambda: messagebox.showinfo(
                    "TMX Cleaner", f"Excel exported:\n{out}"))
            except Exception as e:
                logger.error(f"TMX Cleaner failed: {e}", exc_info=True)
                self.after(0, lambda: messagebox.showerror(
                    "TMX Cleaner Error", f"Failed: {e}"))

        threading.Thread(target=_run, daemon=True).start()
