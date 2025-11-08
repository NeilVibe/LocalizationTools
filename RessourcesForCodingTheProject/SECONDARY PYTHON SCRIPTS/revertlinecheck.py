import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import pandas as pd
import traceback
from collections import defaultdict
from lxml import etree
import threading
import string

def extract_all_pairs_from_files(file_list, progress_var=None, parent=None):
    all_pairs = []
    total = len(file_list)
    for idx, file_path in enumerate(file_list, start=1):
        if progress_var and parent:
            progress_var.set(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
            parent.update_idletasks()
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    src = locstr.get('StrOrigin', '').strip()
                    tgt = locstr.get('Str', '').strip()
                    if src or tgt:
                        all_pairs.append((src, tgt))
            elif ext in (".txt", ".tsv"):
                df = pd.read_csv(
                    file_path,
                    delimiter="\t",
                    header=None,
                    dtype=str,
                    quoting=3,
                    na_values=[''],
                    keep_default_na=False
                )
                if len(df.columns) >= 7:
                    for _, row in df.iterrows():
                        src = str(row[5]).strip() if pd.notna(row[5]) else ""
                        tgt = str(row[6]).strip() if pd.notna(row[6]) else ""
                        if src or tgt:
                            all_pairs.append((src, tgt))
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return all_pairs

def extract_all_pairs_from_folder(folder_path, progress_var=None, parent=None):
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith((".xml", ".txt", ".tsv")):
                file_list.append(os.path.join(root, file))
    return extract_all_pairs_from_files(file_list, progress_var, parent)

def reversed_line_check():
    dialog = tk.Toplevel(window)
    dialog.title("Reversed Line Check Configuration")
    dialog.geometry("450x500")
    dialog.transient(window)
    dialog.grab_set()

    source_data = {'files': None, 'folder': None, 'type': None}
    glossary_data = {'files': None, 'folder': None, 'type': None}

    mode_frame = ttk.LabelFrame(dialog, text="Check Mode")
    mode_frame.pack(padx=10, pady=5, fill="x")
    mode_var = tk.StringVar(value="self")
    ttk.Radiobutton(mode_frame, text="Target against Self", variable=mode_var, value="self").pack(anchor="w")
    ttk.Radiobutton(mode_frame, text="Target against External Glossary", variable=mode_var, value="external").pack(anchor="w")

    source_frame = ttk.LabelFrame(dialog, text="Source Data")
    source_frame.pack(padx=10, pady=5, fill="x")
    source_file_btn = tk.Button(source_frame, text="Select Files")
    source_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
    source_folder_btn = tk.Button(source_frame, text="Select Folder")
    source_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
    source_label = tk.Label(source_frame, text="No data selected")
    source_label.pack(side=tk.LEFT, padx=10)

    glossary_frame = ttk.LabelFrame(dialog, text="External Glossary Data")
    glossary_frame.pack(padx=10, pady=5, fill="x")
    glossary_file_btn = tk.Button(glossary_frame, text="Select Files", state=tk.DISABLED)
    glossary_file_btn.pack(side=tk.LEFT, padx=5, pady=5)
    glossary_folder_btn = tk.Button(glossary_frame, text="Select Folder", state=tk.DISABLED)
    glossary_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
    glossary_label = tk.Label(glossary_frame, text="No data selected")
    glossary_label.pack(side=tk.LEFT, padx=10)

    filter_frame = ttk.LabelFrame(dialog, text="Post-Processing Filters (Target Text)")
    filter_frame.pack(padx=10, pady=5, fill="x")

    filter_punct_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(filter_frame, text="Filter out if contains punctuation", variable=filter_punct_var).pack(anchor="w", padx=5, pady=2)

    max_length_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(filter_frame, text="Filter out if exceeds maximum length", variable=max_length_var).pack(anchor="w", padx=5, pady=2)

    max_length_entry_var = tk.StringVar(value="50")
    ttk.Label(filter_frame, text="Max Length:").pack(side=tk.LEFT, padx=5)
    max_length_entry = ttk.Entry(filter_frame, textvariable=max_length_entry_var, width=5)
    max_length_entry.pack(side=tk.LEFT, padx=5)

    def on_mode_change(*args):
        if mode_var.get() == "external":
            glossary_file_btn.config(state=tk.NORMAL)
            glossary_folder_btn.config(state=tk.NORMAL)
        else:
            glossary_file_btn.config(state=tk.DISABLED)
            glossary_folder_btn.config(state=tk.DISABLED)
    mode_var.trace('w', on_mode_change)

    def select_source_files():
        files = filedialog.askopenfilenames(
            title="Select Source XML/TXT Files",
            filetypes=[("XML and TXT Files", "*.xml *.txt *.tsv"), ("All Files", "*.*")]
        )
        if files:
            source_data['files'] = files
            source_data['folder'] = None
            source_data['type'] = 'files'
            source_label.config(text=f"{len(files)} files selected")
            source_folder_btn.config(state=tk.DISABLED)

    def select_source_folder():
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            source_data['folder'] = folder
            source_data['files'] = None
            source_data['type'] = 'folder'
            source_label.config(text=f"Folder: {os.path.basename(folder)}")
            source_file_btn.config(state=tk.DISABLED)

    def select_glossary_files():
        files = filedialog.askopenfilenames(
            title="Select Glossary XML/TXT Files",
            filetypes=[("XML and TXT Files", "*.xml *.txt *.tsv"), ("All Files", "*.*")]
        )
        if files:
            glossary_data['files'] = files
            glossary_data['folder'] = None
            glossary_data['type'] = 'files'
            glossary_label.config(text=f"{len(files)} files selected")
            glossary_folder_btn.config(state=tk.DISABLED)

    def select_glossary_folder():
        folder = filedialog.askdirectory(title="Select Glossary Folder")
        if folder:
            glossary_data['folder'] = folder
            glossary_data['files'] = None
            glossary_data['type'] = 'folder'
            glossary_label.config(text=f"Folder: {os.path.basename(folder)}")
            glossary_file_btn.config(state=tk.DISABLED)

    source_file_btn.config(command=select_source_files)
    source_folder_btn.config(command=select_source_folder)
    glossary_file_btn.config(command=select_glossary_files)
    glossary_folder_btn.config(command=select_glossary_folder)

    def start_check():
        if not source_data['type']:
            messagebox.showwarning("Warning", "Please select source data")
            return
        if mode_var.get() == "external" and not glossary_data['type']:
            messagebox.showwarning("Warning", "Please select glossary data")
            return
        dialog.destroy()
        out = filedialog.asksaveasfilename(
            title="Save Reversed Line Report As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not out:
            return

        def task():
            try:
                progress_var.set("Checking reversed line consistency...")
                window.update_idletasks()
                if mode_var.get() == "self":
                    glossary_pairs = extract_all_pairs_from_files(source_data['files'], progress_var, window) if source_data['type'] == 'files' else extract_all_pairs_from_folder(source_data['folder'], progress_var, window)
                else:
                    glossary_pairs = extract_all_pairs_from_files(glossary_data['files'], progress_var, window) if glossary_data['type'] == 'files' else extract_all_pairs_from_folder(glossary_data['folder'], progress_var, window)

                check_files = source_data['files'] if source_data['type'] == 'files' else []
                if source_data['type'] == 'folder':
                    for root, dirs, files in os.walk(source_data['folder']):
                        for file in files:
                            if file.lower().endswith((".xml", ".txt", ".tsv")):
                                check_files.append(os.path.join(root, file))

                tgt_src_file = defaultdict(lambda: defaultdict(set))
                for idx, file_path in enumerate(check_files, 1):
                    progress_var.set(f"Parsing {idx}/{len(check_files)}: {os.path.basename(file_path)}")
                    window.update_idletasks()
                    ext = os.path.splitext(file_path)[1].lower()
                    try:
                        if ext == ".xml":
                            parser = etree.XMLParser(recover=True, resolve_entities=False)
                            tree = etree.parse(file_path, parser)
                            for locstr in tree.xpath('//LocStr'):
                                src = locstr.get('StrOrigin', '').strip()
                                tgt = locstr.get('Str', '').strip()
                                if src and tgt:
                                    tgt_src_file[tgt][src].add(os.path.basename(file_path))
                        elif ext in (".txt", ".tsv"):
                            df = pd.read_csv(
                                file_path,
                                delimiter="\t",
                                header=None,
                                dtype=str,
                                quoting=3,
                                na_values=[''],
                                keep_default_na=False
                            )
                            if len(df.columns) >= 7:
                                for _, row in df.iterrows():
                                    src = str(row[5]).strip() if pd.notna(row[5]) else ""
                                    tgt = str(row[6]).strip() if pd.notna(row[6]) else ""
                                    if src and tgt:
                                        tgt_src_file[tgt][src].add(os.path.basename(file_path))
                    except Exception as e:
                        print(f"Failed {file_path}: {e}")

                inconsistent = {tgt: src_dict for tgt, src_dict in tgt_src_file.items() if len(src_dict) > 1}

                # Apply filters
                if filter_punct_var.get():
                    inconsistent = {tgt: src_dict for tgt, src_dict in inconsistent.items() if not any(ch in string.punctuation for ch in tgt)}
                if max_length_var.get():
                    try:
                        max_len = int(max_length_entry_var.get())
                        inconsistent = {tgt: src_dict for tgt, src_dict in inconsistent.items() if len(tgt) <= max_len}
                    except ValueError:
                        pass

                with open(out, 'w', encoding='utf-8') as f:
                    for tgt, src_dict in sorted(inconsistent.items(), key=lambda x: len(x[0])):
                        f.write(f"{tgt}\n")
                        for src, files in sorted(src_dict.items()):
                            for file in sorted(files):
                                f.write(f"  {src}    [{file}]\n")
                        f.write("\n")

                progress_var.set(f"Reversed line check complete: {len(inconsistent)} targets inconsistent")
                messagebox.showinfo("Done", f"Reversed line report saved to:\n{out}")
            except Exception:
                txt = traceback.format_exc()
                progress_var.set("Error during reversed line check.")
                messagebox.showerror("Error", txt)

        threading.Thread(target=task, daemon=True).start()

    start_btn = tk.Button(dialog, text="Start Check", command=start_check,
                         relief="raised", bd=3, padx=20, pady=5,
                         font=('Helvetica', 10, 'bold'))
    start_btn.pack(pady=10)

window = tk.Tk()
window.title("Reversed Line Check Tool")
window.geometry("500x250")

progress_var = tk.StringVar(value="Ready")
progress_label = tk.Label(window, textvariable=progress_var)
progress_label.pack(pady=5)

btn = tk.Button(window, text="Run Reversed Line Check", command=reversed_line_check,
               font=('Helvetica', 12, 'bold'), relief="raised", bd=3)
btn.pack(pady=20)

window.mainloop()