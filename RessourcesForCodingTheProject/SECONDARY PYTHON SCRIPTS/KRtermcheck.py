import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import pandas as pd
import re
import threading
import os
import sys
import time
import traceback
import csv
import datetime
from lxml import etree
from collections import defaultdict
import ahocorasick

progress_var = None
progress_bar = None
window = None

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def center_dialog(dialog, parent):
    dialog.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    x = parent_x + (parent_width - dialog_width) // 2
    y = parent_y + (parent_height - dialog_height) // 2
    dialog.geometry(f"+{x}+{y}")

def normalize_dictionary_text(text):
    if not isinstance(text, str):
        return ""
    balanced_indices = set()
    quote_indices = [i for i, char in enumerate(text) if char == '"']
    for i in range(0, len(quote_indices) - 1, 2):
        balanced_indices.add(quote_indices[i])
        balanced_indices.add(quote_indices[i + 1])
    result = []
    for i, char in enumerate(text):
        if char == '"' and i not in balanced_indices:
            continue
        result.append(char)
    text = ''.join(result)
    text = re.sub(r'[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]+', ' ', text)
    text = re.sub(r'[\u200B-\u200F\u202A-\u202E]+', '', text)
    text = re.sub(r'[\u2019\u2018\u02BC\u2032\u0060\u00B4]', "'", text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_korean(text):
    return bool(re.search(r'[\uac00-\ud7a3]', text))

def is_sentence(text):
    return bool(re.search(r'[.?!。？！]\s*$', text.strip()))

def contains_excessive_punctuation(text):
    punct_count = len(re.findall(r'[.,;:!?()[\]{}\"\'`~@#$%^&*+=|\\/<>]', text))
    if len(text) > 0:
        punct_ratio = punct_count / len(text)
        return punct_ratio > 0.3
    return False

def extract_all_pairs_from_files(file_list, progress_callback=None):
    all_pairs = []
    total = len(file_list)
    for idx, file_path in enumerate(file_list, start=1):
        if progress_callback:
            progress_callback(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    en = locstr.get('StrOrigin', '').strip()
                    kr = locstr.get('Str', '').strip()
                    if en or kr:
                        all_pairs.append((en, kr))
            elif ext in (".txt", ".tsv"):
                df = pd.read_csv(
                    file_path,
                    delimiter="\t",
                    header=None,
                    dtype=str,
                    quoting=csv.QUOTE_NONE,
                    quotechar=None,
                    escapechar=None,
                    na_values=[''],
                    keep_default_na=False
                )
                if len(df.columns) >= 7:
                    for _, row in df.iterrows():
                        en = str(row[5]).strip() if pd.notna(row[5]) else ""
                        kr = str(row[6]).strip() if pd.notna(row[6]) else ""
                        if en or kr:
                            all_pairs.append((en, kr))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
    return all_pairs

def extract_all_locstrs_from_files(file_list, progress_callback=None):
    all_entries = []
    total = len(file_list)
    for idx, file_path in enumerate(file_list, start=1):
        if progress_callback:
            progress_callback(f"Reading file {idx}/{total}: {os.path.basename(file_path)}")
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".xml":
                parser = etree.XMLParser(recover=True, resolve_entities=False)
                tree = etree.parse(file_path, parser)
                for locstr in tree.xpath('//LocStr'):
                    entry = {
                        'Source': locstr.get('StrOrigin', '').strip(),
                        'Target': locstr.get('Str', '').strip(),
                        'xml_path': file_path,
                        'locstr_id': locstr.get('ID', '')
                    }
                    all_entries.append(entry)
            elif ext in (".txt", ".tsv"):
                df = pd.read_csv(
                    file_path,
                    delimiter="\t",
                    header=None,
                    dtype=str,
                    quoting=csv.QUOTE_NONE,
                    quotechar=None,
                    escapechar=None,
                    na_values=[''],
                    keep_default_na=False
                )
                if len(df.columns) >= 7:
                    for _, row in df.iterrows():
                        str_key = " ".join(str(row[i]).strip() if pd.notna(row[i]) else '' 
                                         for i in range(min(5, len(row))))
                        entry = {
                            'Source': str(row[5]).strip() if pd.notna(row[5]) else "",
                            'Target': str(row[6]).strip() if pd.notna(row[6]) else "",
                            'xml_path': file_path,
                            'locstr_id': str_key
                        }
                        all_entries.append(entry)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
    return all_entries

def glossary_filter(pairs, length_threshold, filter_sentences, filter_punctuation):
    filtered = []
    for src, tgt in pairs:
        if not src or not tgt:
            continue
        if len(src) >= length_threshold:
            continue
        if filter_sentences and (is_sentence(src) or is_sentence(tgt)):
            continue
        if filter_punctuation:
            if contains_excessive_punctuation(src) or contains_excessive_punctuation(tgt):
                continue
        filtered.append((src, tgt))
    return filtered

def normalize_for_korean_matching(text):
    if not text:
        return ""
    text = re.sub(r'<color[^>]*>|</color>', '', text)
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)
    text = re.sub(r'\{AudioVoice[^}]*\}', '', text)
    text = re.sub(r'\{ChangeScene[^}]*\}', '', text)
    text = re.sub(r'\{ChangeAction[^}]*\}', '', text)
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s*([^\s\w])\s*', r'\1', text)
    return text.strip()

def korean_term_check(source_files, glossary_files, params, progress_callback=None):
    try:
        if progress_callback:
            progress_callback("Extracting glossary from source files...")
        glossary_pairs = extract_all_pairs_from_files(glossary_files if glossary_files else source_files, progress_callback)
        filtered = glossary_filter(
            glossary_pairs,
            params['length_threshold'],
            params['filter_sentences'],
            params['filter_punctuation']
        )
        source_to_korean = defaultdict(lambda: defaultdict(int))
        for src, tgt in filtered:
            source_to_korean[src][tgt] += 1
        glossary_terms = []
        for src, korean_dict in source_to_korean.items():
            total_occurrences = sum(korean_dict.values())
            if total_occurrences >= params['min_occurrence']:
                most_frequent_kr = max(korean_dict.items(), key=lambda x: x[1])[0]
                glossary_terms.append((src, most_frequent_kr))
        if not glossary_terms:
            if progress_callback:
                progress_callback("No glossary terms found with current filters.")
            return []
        if progress_callback:
            progress_callback("Building Aho-Corasick automaton...")
        automaton = ahocorasick.Automaton()
        term_to_korean = {}
        for idx, (en_term, kr_ref) in enumerate(glossary_terms):
            automaton.add_word(en_term.lower(), (idx, en_term))
            term_to_korean[idx] = (en_term, kr_ref, normalize_for_korean_matching(kr_ref))
        automaton.make_automaton()
        if progress_callback:
            progress_callback("Starting Aho-Corasick scan for Korean inconsistencies...")
        all_entries = extract_all_locstrs_from_files(source_files, progress_callback)
        issues = defaultdict(list)
        MAX_ISSUE_LINES = 10
        for entry in all_entries:
            src = entry['Source']
            tgt = entry['Target']
            if not src or not tgt:
                continue
            src_lower = src.lower()
            matches_found = set()
            for end_index, (pattern_id, original_term) in automaton.iter(src_lower):
                matches_found.add(pattern_id)
            for pattern_id in matches_found:
                en_term, kr_ref, norm_kr_ref = term_to_korean[pattern_id]
                norm_tgt = normalize_for_korean_matching(tgt)
                if norm_kr_ref not in norm_tgt:
                    issue_key = (en_term, kr_ref)
                    if len(issues[issue_key]) < MAX_ISSUE_LINES:
                        issues[issue_key].append({
                            'source': src,
                            'target': tgt,
                            'file': os.path.basename(entry['xml_path'])
                        })
        if progress_callback:
            progress_callback(f"Term check complete: {len(issues)} Korean inconsistencies found")
        return sorted(issues.items(), key=lambda x: len(x[0][0]))
    except Exception as e:
        print(f"Error in korean_term_check: {e}")
        traceback.print_exc()
        return []

def create_gui():
    global progress_var, progress_bar, window
    window = tk.Tk()
    window.title("Korean Target Term Check - Consistency Checker")
    window.geometry("500x650")
    params_frame = ttk.LabelFrame(window, text="Glossary Extraction Parameters")
    params_frame.pack(padx=10, pady=10, fill="x")
    tk.Label(params_frame, text="Max source (English) length:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    length_var = tk.IntVar(value=20)
    tk.Spinbox(params_frame, from_=3, to=50, textvariable=length_var, width=10).grid(row=0, column=1, padx=5, pady=5)
    tk.Label(params_frame, text="Minimum occurrence count:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    occurrence_var = tk.IntVar(value=2)
    tk.Spinbox(params_frame, from_=1, to=50, textvariable=occurrence_var, width=10).grid(row=1, column=1, padx=5, pady=5)
    filter_sentences_var = tk.BooleanVar(value=True)
    tk.Checkbutton(params_frame, text="Filter out sentences (. ? !)", 
                   variable=filter_sentences_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    filter_punctuation_var = tk.BooleanVar(value=True)
    tk.Checkbutton(params_frame, text="Filter excessive punctuation", 
                   variable=filter_punctuation_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    files_frame = ttk.LabelFrame(window, text="File Selection")
    files_frame.pack(padx=10, pady=10, fill="x")
    source_files = []
    source_label = tk.Label(files_frame, text="No source files selected", anchor="w")
    source_label.pack(fill="x", padx=5, pady=5)
    def select_source_files():
        files = filedialog.askopenfilenames(
            title="Select Source XML/TXT Files to Check",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("XML Files", "*.xml"),
                ("Text Files", "*.txt;*.tsv"),
                ("All Files", "*.*")
            ]
        )
        if files:
            source_files.clear()
            source_files.extend(files)
            source_label.config(text=f"{len(files)} source files selected")
    tk.Button(files_frame, text="Select Source Files", command=select_source_files).pack(pady=5)
    glossary_files = []
    glossary_label = tk.Label(files_frame, text="No glossary files selected (will use source)", anchor="w")
    glossary_label.pack(fill="x", padx=5, pady=5)
    def select_glossary_files():
        files = filedialog.askopenfilenames(
            title="Select Glossary XML/TXT Files (Optional)",
            filetypes=[
                ("XML and TXT Files", "*.xml *.txt *.tsv"),
                ("XML Files", "*.xml"),
                ("Text Files", "*.txt;*.tsv"),
                ("All Files", "*.*")
            ]
        )
        if files:
            glossary_files.clear()
            glossary_files.extend(files)
            glossary_label.config(text=f"{len(files)} glossary files selected")
    tk.Button(files_frame, text="Select Glossary Files (Optional)", command=select_glossary_files).pack(pady=5)
    progress_frame = ttk.Frame(window)
    progress_frame.pack(padx=10, pady=10, fill="x")
    progress_var = tk.StringVar(value="Ready")
    tk.Label(progress_frame, textvariable=progress_var).pack()
    progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
    progress_bar.pack(fill="x", pady=5)
    def run_check():
        if not source_files:
            messagebox.showwarning("Warning", "Please select source files to check")
            return
        output_file = filedialog.asksaveasfilename(
            title="Save Korean Term Check Report As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")]
        )
        if not output_file:
            return
        params = {
            'length_threshold': length_var.get(),
            'min_occurrence': occurrence_var.get(),
            'filter_sentences': filter_sentences_var.get(),
            'filter_punctuation': filter_punctuation_var.get()
        }
        def progress_callback(msg):
            progress_var.set(msg)
            window.update_idletasks()
        def task():
            try:
                progress_bar.start()
                issues = korean_term_check(
                    source_files, 
                    glossary_files if glossary_files else None,
                    params,
                    progress_callback
                )
                # Write TXT
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("="*80 + "\n")
                    f.write("KOREAN TARGET TERM CHECK REPORT\n")
                    f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Source files checked: {len(source_files)}\n")
                    f.write(f"Glossary source: {'External' if glossary_files else 'Self'}\n")
                    f.write(f"Issues found: {len(issues)}\n")
                    f.write("="*80 + "\n\n")
                    for (en_term, kr_ref), problem_lines in issues:
                        f.write(f"English Term: {en_term}\n")
                        f.write(f"Expected Korean: {kr_ref}\n")
                        f.write("-" * 40 + "\n")
                        for problem in problem_lines:
                            f.write(f"File: {problem['file']}\n")
                            f.write(f"Source: {problem['source']}\n")
                            f.write(f"Korean: {problem['target']}\n")
                            f.write("\n")
                        f.write("=" * 80 + "\n\n")
                # Write Excel (one block per cell)
                excel_file = os.path.splitext(output_file)[0] + "_termcheck.xlsx"
                blocks = []
                for (en_term, kr_ref), problem_lines in issues:
                    block_lines = [
                        f"English Term: {en_term}",
                        f"Expected Korean: {kr_ref}",
                        "-" * 40
                    ]
                    for problem in problem_lines:
                        block_lines.append(f"File: {problem['file']}")
                        block_lines.append(f"Source: {problem['source']}")
                        block_lines.append(f"Korean: {problem['target']}")
                        block_lines.append("")
                    block_lines.append("=" * 80)
                    blocks.append("\n".join(block_lines))
                df = pd.DataFrame(blocks, columns=["Term Check Results"])
                df.to_excel(excel_file, index=False)
                progress_bar.stop()
                progress_var.set(f"Complete! Found {len(issues)} Korean inconsistencies")
                messagebox.showinfo("Complete", 
                    f"Korean term check complete!\n\n"
                    f"Found {len(issues)} terms with Korean inconsistencies\n"
                    f"Text report: {output_file}\n"
                    f"Excel report: {excel_file}")
            except Exception as e:
                progress_bar.stop()
                progress_var.set("Error occurred")
                messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
                traceback.print_exc()
        threading.Thread(target=task, daemon=True).start()
    tk.Button(window, text="Run Korean Term Check", command=run_check,
              bg="green", fg="white", font=('Helvetica', 12, 'bold'),
              padx=20, pady=10).pack(pady=20)
    options_frame = ttk.LabelFrame(window, text="Advanced Options")
    options_frame.pack(padx=10, pady=10, fill="x")
    tk.Label(options_frame, text="• Check uses Aho-Corasick for ultra-fast scanning", 
             font=('Helvetica', 9)).pack(anchor="w", padx=5, pady=2)
    tk.Label(options_frame, text="• Detects when English terms have inconsistent Korean translations", 
             font=('Helvetica', 9)).pack(anchor="w", padx=5, pady=2)
    tk.Label(options_frame, text="• Applies sophisticated filtering to reduce false positives", 
             font=('Helvetica', 9)).pack(anchor="w", padx=5, pady=2)
    window.mainloop()

if __name__ == "__main__":
    create_gui()