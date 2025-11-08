print("Translation File Manager 프로그램 실행 중입니다 잠시만 기다려 주십시오...")
print("- Translation File Manager ver. 0116 - By Neil")
print("- Translation File Manager ver. 0116 - By Neil")
print("- Translation File Manager ver. 0116 - By Neil")
import os
import sys
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog, scrolledtext, font
from collections import defaultdict, Counter
import threading
import pandas as pd
import time
import numpy as np
print("FAISS 패키지 불러오고 있습니다...")
import faiss
print("Sentence Transformer 패키지 불러오고 있습니다...")
from sentence_transformers import SentenceTransformer
print("Pickle 패키지 불러오고 있습니다...")
import pickle
import traceback
from traceback import print_exc
print("TQDM 패키지 불러오고 있습니다...")
import tqdm
print("오 ! 거의 다 왔습니다 ! TORCH 패키지 불러오고 있습니다...")
import torch
import pyperclip
from concurrent.futures import ThreadPoolExecutor



try:
    import pyi_splash  # PyInstaller splash screen functionality
    splash_active = True
except ImportError:
    splash_active = False


# Define the on_copy function to handle the copy event
def on_copy(event=None):
    try:
        widget = event.widget
        # Get the selected text
        selection = widget.selection_get()
        clipboard_text = selection.replace("❓❓", "")
        # Use pyperclip to set the clipboard content
        pyperclip.copy(clipboard_text)
        # Verify the clipboard content
        clipboard_content = pyperclip.paste()       
        return "break"  # Prevent the default copying behavior
    except tk.TclError:
        pass  # Handle the case where no text is selected
        
        

def on_closing():
    root.destroy()  # Destroy the root window
    sys.exit()      # Exit the Python interpreter


def center_window(window, width, height):
    # Get the screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Calculate the center coordinates
    center_x = int(screen_width / 2 - width / 2)
    center_y = int(screen_height / 2 - height / 2)
    
    # Position the window at the center of the screen
    window.geometry(f'{width}x{height}+{center_x}+{center_y}')


def create_progress_bar_window(parent):
    progress_window = tk.Toplevel(parent)
    progress_window.title("진행 상황")
    progress_window.geometry('300x100')

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100, length=280)
    progress_bar.pack(pady=20)

    # Create a label for showing progress in percentage
    progress_label = tk.Label(progress_window, text="0% 완료")
    progress_label.pack()

    return progress_window, progress_var, progress_label



# Function to upload a file
def upload_file(entry):
    entry.config(state='normal')
    filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    
    if not filepath:
        messagebox.showwarning("Warning", "파일 선택되지 않았습니다.")
        entry.config(state='readonly')
        return

    # Store full filepath in entry widget's attribute
    entry.filepath = filepath
    # Show only filename in the entry field
    entry.delete(0, tk.END)
    entry.insert(0, os.path.basename(filepath))
    entry.config(state='readonly')

    # Update the state and color of the pattern check button based on file upload
    if entry_A.filepath:
        button_pattern_check.config(state='normal', bg='pale green')
        button_char.config(state='normal', bg='pale green')
        button_extract_diff_count.config(state='normal', bg='pale green')
        button_match_line_breaks.config(state='normal', bg='pale green')
        button_hyperlink_check.config(state='normal', bg='pale green')
        button_compare_files.config(state='disabled', bg='grey')
        
    else:
        button_pattern_check.config(state='disabled', bg='grey')  # Disable and turn grey
        button_char.config(state='disabled', bg='grey')
        button_match_line_breaks.config(state='disabled', bg='grey')
        button_hyperlink_check.config(state='disabled', bg='grey')

    # Check if both files are uploaded for other buttons
    if entry_A.filepath and entry_B.filepath:
        button_go.config(state='normal', bg='pale green')  # Enable the button
        button_go_short.config(state='normal', bg='pale green')
        button_extract.config(state='normal', bg='pale green')  # Enable the 'Key1 기준 렝데 스트링 추출' button
        button_open_extractnodiffy.config(state='normal', bg='pale green')  # Enable the '단순 국문 수정 추출' button
        button_pattern_check.config(state='disabled', bg='grey')
        button_char.config(state='disabled', bg='grey')
        button_extract_diff_count.config(state='disabled', bg='grey') 
        button_match_line_breaks.config(state='disabled', bg='grey')
        button_hyperlink_check.config(state='disabled', bg='grey')
        button_compare_files.config(state='normal', bg='pale green')
    else:
        button_go.config(state='disabled', bg='grey')  # Disable the button
        button_go_short.config(state='disabled', bg='grey')
        button_extract.config(state='disabled', bg='grey')  # Disable the 'Key1 기준 렝데 스트링 추출' button
        button_open_extractnodiffy.config(state='disabled', bg='grey')  # Disable the '단순 국문 수정 추출' button
        button_compare_files.config(state='disabled', bg='grey')


def clear_entry(entry):
    entry.config(state='normal')
    entry.delete(0, tk.END)
    entry.config(state='readonly')

def clear_entries():
    clear_entry(entry_A)
    clear_entry(entry_B)
    
    # Reset the state and color of all buttons
    button_pattern_check.config(state='disabled', bg='grey')
    button_char.config(state='disabled', bg='grey')
    button_extract_diff_count.config(state='disabled', bg='grey')
    button_go.config(state='disabled', bg='grey')
    button_go_short.config(state='disabled', bg='grey')
    button_extract.config(state='disabled', bg='grey')
    button_open_extractnodiffy.config(state='disabled', bg='grey')
    button_match_line_breaks.config(state='disabled', bg='grey')
    button_compare_files.config(state='disabled', bg='grey')
    button_hyperlink_check.config(state='disabled', bg='grey')


def trim_columns(path_in):
    # Columns to keep (zero-based indices)
    columns_to_keep = list(range(9))
    trimmed_lines = []
    with open(path_in, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            # Split the line into columns without stripping
            columns = line.rstrip('\n').split('\t')
            # If there are fewer columns than needed, append empty strings
            if len(columns) < 9:
                columns += [''] * (9 - len(columns))
            # Keep the desired columns and join them back into a line with a newline at the end
            new_line = '\t'.join([columns[i] for i in columns_to_keep]) + '\n'
            trimmed_lines.append(new_line)
    return trimmed_lines


def display_info_message1():
    message = "제거 진행 완료 후 신규 렝데를 바로 커밋해도 됩니다."
    messagebox.showinfo("Information", message)
	
def display_info_message2():
    message = "Translation file Manager LITE (version : 1231)\nDesigned and coded by Neil Schmitt."
    messagebox.showinfo("Information", message)
    
def display_info_message3():
    message = "클로즈와 렝데 비교해 단순히 띄어쓰기 또는 구두점으로 수정된 스트링들 따로 추출함."
    messagebox.showinfo("Information", message)

def display_info_message4():
    message = "Update 기능을 최초로 사용하시는 경우에 렝귀지 데이터 분석 파일 생성해야 하기 때문에 약 6~8 시간 소요가 됩니다."
    messagebox.showinfo("Information", message)        
	
# Function to perform string erasing
def string_eraser(path_A, path_B):
    # First, keep only the first 10 columns in path_A
    content_A = trim_columns(path_A)

    # Write trimmed data to a temporary file
    temp_file_path = "temp_file.txt"
    with open(temp_file_path, "w", encoding="utf-8") as file:
        file.writelines(content_A)

    # Read from the temporary file for the erasing operation
    with open(temp_file_path, "r", encoding="utf-8") as file:
        content_A = file.readlines()

    path_out = filedialog.asksaveasfilename(defaultextension=".txt")
    if not path_out:  # If the user cancels the save dialog, return
        return

    # Display a message to indicate the output file has been chosen
    messagebox.showinfo("Output file selected !", "파일 선택 완료. 스트링 제거 잠시 후 시작합니다.")

    with open(path_B, "r", encoding="utf-8") as file:
        content_B = file.read()

    # Build a set of tuples for lines in content_B
    set_B = set(tuple(line.split('\t')[0:7]) for line in content_B.splitlines())

    # Filter lines from content_A and also get erased lines
    lines_A = []
    lines_erased = []
    for line in content_A:
        if tuple(line.split('\t')[0:7]) not in set_B:
            lines_A.append(line)
        else:
            lines_erased.append(line)

    with open(path_out, "w", encoding="utf-8") as file:
        file.writelines(lines_A)
    
    # Write erased lines to a separate file
    path_erased = path_out.rsplit('.', 1)[0] + '_erased.txt'
    with open(path_erased, "w", encoding="utf-8") as file:
        file.writelines(lines_erased)

    # Clear the entry fields and reset their state to normal
    entry_A.config(state='normal')
    entry_A.delete(0, tk.END)
    entry_B.config(state='normal')
    entry_B.delete(0, tk.END)
    
    # Show message box with job done notification
    messagebox.showinfo("Job done!", "스트링 제거 완료!")

    # Remove the temporary file
    os.remove(temp_file_path)

# Function to perform string erasing but only compare to the korean, not the translation
def string_eraser_short(path_A, path_B):
    # First, keep only the first 10 columns in path_A
    content_A = trim_columns(path_A)

    # Write trimmed data to a temporary file
    temp_file_path = "temp_file.txt"
    with open(temp_file_path, "w", encoding="utf-8") as file:
        file.writelines(content_A)

    # Read from the temporary file for the erasing operation
    with open(temp_file_path, "r", encoding="utf-8") as file:
        content_A = file.readlines()

    path_out = filedialog.asksaveasfilename(defaultextension=".txt")
    if not path_out:  # If the user cancels the save dialog, return
        return

    # Display a message to indicate the output file has been chosen
    messagebox.showinfo("Output file selected !", "파일 선택 완료. 스트링 제거 잠시 후 시작합니다.")

    with open(path_B, "r", encoding="utf-8") as file:
        content_B = file.read()

    # Build a set of tuples for lines in content_B
    set_B = set(tuple(line.split('\t')[0:6]) for line in content_B.splitlines())

    # Filter lines from content_A and also get erased lines
    lines_A = []
    lines_erased = []
    for line in content_A:
        if tuple(line.split('\t')[0:6]) not in set_B:
            lines_A.append(line)
        else:
            lines_erased.append(line)

    with open(path_out, "w", encoding="utf-8") as file:
        file.writelines(lines_A)
    
    # Write erased lines to a separate file
    path_erased = path_out.rsplit('.', 1)[0] + '_erased.txt'
    with open(path_erased, "w", encoding="utf-8") as file:
        file.writelines(lines_erased)

    # Clear the entry fields and reset their state to normal
    entry_A.config(state='normal')
    entry_A.delete(0, tk.END)
    entry_B.config(state='normal')
    entry_B.delete(0, tk.END)
    
    # Show message box with job done notification
    messagebox.showinfo("Job done!", "스트링 제거 완료!")

    # Remove the temporary file
    os.remove(temp_file_path)

def preprocess_text(text):
    # Remove substrings that match the specified patterns
    #text = re.sub(r'<Scale:[0-9.]+>', '', text)
    text = re.sub(r'<color:.*?>', '', text)
    # Added pattern to match <PAColor.*?> and <PAOldColor>
    text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
    return text

def find_character_discrepancies():
    # Get the specified character from the input field
    char = entry_char.get()

    # Check if the character entry is empty
    if not char.strip():
        messagebox.showwarning("Warning", "체크할 문자 먼저 선택해 주세요")
        return

    path_A = entry_A.filepath
    content_A = trim_columns(path_A)

    # Normalize and filter lines where column 5 and column 6 have different counts of the specified character after normalization
    discrepancy_lines = []
    for line in content_A:
        columns = line.strip().split('\t')
        # Apply normalization to columns 5 and 6
        col5_normalized = preprocess_text(columns[5])
        col6_normalized = preprocess_text(columns[6])
        if col5_normalized.count(char) != col6_normalized.count(char):
            discrepancy_lines.append(line)

    if not discrepancy_lines:
        messagebox.showinfo("문제 없음", "이상 없습니다")
        return

    path_out = filedialog.asksaveasfilename(defaultextension=".txt")
    if path_out:
        with open(path_out, "w", encoding="utf-8") as file:
            file.writelines(discrepancy_lines)
        messagebox.showinfo("완료", f"Character '{char}' 체크 완료!")

    # Clear the entry field for character input and reset its state to normal
    entry_char.config(state='normal')
    entry_char.delete(0, tk.END)


def extract_lines_by_number(path_A, path_B):
    # First, keep only the first 10 columns in path_A
    content_A = trim_columns(path_A)

    # Read Path B and get the list of numbers
    with open(path_B, "r", encoding="utf-8") as file:
        numbers_B = [line.strip() for line in file.read().splitlines()]

    # Filter lines from content_A that have the numbers from file B in their first column
    filtered_lines = [line for line in content_A if line.split('\t')[1].strip() in numbers_B]

    path_out = filedialog.asksaveasfilename(defaultextension=".txt")
    if not path_out:  # If the user cancels the save dialog, return
        return

    with open(path_out, "w", encoding="utf-8") as file:
        file.writelines(filtered_lines)
        
    # Show message box with job done notification
    messagebox.showinfo("작업 완료!", "Number matching lines extraction complete!")
    
    
    
def extract_code_patterns(text):
    """
    Extracts code patterns enclosed within '{}' from the given text.
    Returns a set of these patterns.
    """
    pattern = r'\{.*?\}'
    return set(re.findall(pattern, text))

def pattern_sequence_check():
    """
    Compares code patterns in index 5 and 6 of a line and
    extracts lines where these patterns don't match.
    """
    path_A = entry_A.filepath
    if not path_A:
        messagebox.showinfo("안내", "파일 업로드 해 주세요.")
        return

    content_A = trim_columns(path_A)

    extracted_lines = []
    for line in content_A:
        columns = line.strip().split('\t')
        if len(columns) < 7:
            continue

        patterns_5 = extract_code_patterns(columns[5])
        patterns_6 = extract_code_patterns(columns[6])

        if patterns_5 != patterns_6:
            extracted_lines.append(line)

    if not extracted_lines:
        messagebox.showinfo("문제 없음", "이상 없습니다")
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text files", "*.txt")])
    if save_path:
        with open(save_path, 'w', encoding='utf-8') as file:
            file.writelines(extracted_lines)
        messagebox.showinfo("추출 완료", "패턴 시퀸스 틀린 스트링 저장되었습니다.")
       


def extract_no_diff_tab(output_path, progress_window, progress_var, progress_label):
    def normalize_text(text):
        # Remove patterns "(방어구)" and "(무기)" with optional preceding spaces
        text = re.sub(r'\s*\((방어구|무기)\)', '', text)
        
        # Remove any HTML-like color codes
        text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
        
        # Directly remove "으" from "블랙스톤으로", adjusting for prior removals
        text = text.replace("블랙스톤으로", "블랙스톤로")
        
        # Normalize "과" and "와" following the removals, choosing one for standardization
        # Here, I'll choose "와" for all instances for simplicity; adjust as needed for your text
        text = text.replace("블랙스톤과", "블랙스톤와")
        
        # Remove all other whitespaces and punctuation
        text = re.sub(r'\s+|[.,:!?"\'-]', '', text)
        return text

    def read_and_process_file(filepath, data_dict, progress_offset, total_lines, mark_for_extraction=False):
        progress_step = max(total_lines // 100, 1)  # Avoid division by zero
        with open(filepath, 'r', encoding='utf-8') as file:
            for line_count, line in enumerate(file, 1):
                parts = line.split('\t')
                if len(parts) >= 6:
                    key = tuple(parts[:5])
                    normalized_text = normalize_text(parts[5])
                    if mark_for_extraction:
                        if key in data_dict and data_dict[key][1] == normalized_text and data_dict[key][0] != line.strip():
                            data_dict[key] = (data_dict[key][0], normalized_text, True)  # Update for extraction
                    else:
                        data_dict[key] = (line.strip(), normalized_text, False)  # Default False for extraction

                if line_count % progress_step == 0:
                    progress = progress_offset + (line_count / total_lines) * 50
                    progress_var.set(progress)
                    progress_label.config(text=f"{progress:.2f}% 완료")
                    progress_window.update_idletasks()

    file1_path = entry_A.filepath
    file2_path = entry_B.filepath
    total_lines_file1 = sum(1 for _ in open(file1_path, 'r', encoding='utf-8'))
    total_lines_file2 = sum(1 for _ in open(file2_path, 'r', encoding='utf-8'))

    data_dict = {}
    read_and_process_file(file1_path, data_dict, 0, total_lines_file1)
    read_and_process_file(file2_path, data_dict, 50, total_lines_file2, mark_for_extraction=True)

    # Write changes to output file
    with open(output_path, 'w', encoding='utf-8') as output_file:
        for key, (original_line, _, marked_for_extraction) in data_dict.items():
            if marked_for_extraction:
                output_file.write(original_line + '\n')

    progress_var.set(100)
    progress_label.config(text="100%")
    messagebox.showinfo("완료", "추출 성공적으로 완료되었습니다 !")
    progress_window.destroy()

    if not (file1_path and file2_path and output_path):
        messagebox.showwarning("Cancelled", "Please upload both files first and specify an output file.")
        progress_window.destroy()



def open_extract_no_diff():
    extractnodiff_window = tk.Toplevel(root)
    extractnodiff_window.withdraw()
    extractnodiff_window.title("KR NO CHANGE EXTRACT")

    progress_window, progress_var, progress_label = create_progress_bar_window(extractnodiff_window)

    output_path = filedialog.asksaveasfilename(
        title="Save output as",
        defaultextension=".txt",
        filetypes=[("Text Files", "*.txt")]
    )

    if output_path:
        extract_no_diff_tab(output_path, progress_window, progress_var, progress_label)
    else:
        messagebox.showwarning("Cancelled", "Operation cancelled.")
        progress_window.destroy()




def language_data_analyzer_tab(parent):
    def tokenize(text, only_first_line=False):
        lines = re.split(r'\\?\\n', text) if isinstance(text, str) else []
        return [lines[0]] if only_first_line and lines else lines

    def contains_color_code(text):
        return '<PAColor' in text

    def normalize_text(text, consider_punctuation, consider_case):
        normalized_text = text.strip()  # Trim leading and trailing spaces
        normalized_text = re.sub(r'\s+', ' ', normalized_text)
        normalized_text = re.sub(r'[‐‑‒–—−]', '-', normalized_text)
        if not consider_punctuation:
            normalized_text = re.sub(r'[.,:?!]', '', normalized_text)
        if not consider_case:
            normalized_text = normalized_text.lower()
        return normalized_text

    def process_file(filepath, output_filepath, only_first_line, max_line_length, categories, consider_punctuation, var_consider_case, filter_color_code):
        kr_to_fr = defaultdict(list)
        categorized_results = {
            '30-70%': [],
            '10-30% or 70-90%': [],
            'other': []
        }

        def sort_by_kr_length(item):
            kr, _ = item
            return len(kr)

        def categorize_percentage(percentage):
            if 30 <= percentage <= 70:
                return '30-70%'
            elif 10 <= percentage < 30 or 70 < percentage <= 90:
                return '10-30% or 70-90%'
            else:
                return 'other'

        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                columns = line.strip().split('\t')
                if len(columns) >= 7 and (not categories or columns[0] in categories or 'All Categories' in categories):
                    kr_line = tokenize(columns[5], only_first_line=only_first_line)
                    fr_line = tokenize(columns[6], only_first_line=only_first_line)
                    for kr, fr in zip(kr_line, fr_line):
                        if filter_color_code and contains_color_code(fr):
                            continue
                        if len(kr) <= max_line_length:
                            normalized_fr = normalize_text(fr, consider_punctuation, var_consider_case.get())
                            kr_to_fr[kr].append((fr, normalized_fr))

        for kr, fr_tuples in kr_to_fr.items():
            comparison_fr_list = [normalized_fr for original_fr, normalized_fr in fr_tuples]
            comparison_count = Counter(comparison_fr_list)

            if len(comparison_count) > 1:
                original_fr_list = [original_fr for original_fr, normalized_fr in fr_tuples]
                original_fr_count = Counter(original_fr_list)
                percentages = {original_fr: original_fr_count[original_fr] / len(original_fr_list) * 100 for original_fr in set(original_fr_list)}
                min_percentage = min(percentages.values(), default=0)
                category = categorize_percentage(min_percentage)
                categorized_results[category].append((kr, percentages))

        with open(output_filepath, 'w', encoding='utf-8') as report:
            for category, blocks in categorized_results.items():
                if blocks:
                    report.write(f"{'='*20} Category: {category} {'='*20}\n")
                    sorted_blocks = sorted(blocks, key=sort_by_kr_length)
                    for kr, translations in sorted_blocks:
                        report.write(f"{kr}\n")
                        for fr, percentage in translations.items():
                            report.write(f"  {percentage:.2f}%: {fr}\n")
                        report.write("\n")
                    report.write("\n" * 10)

    def on_file_select():
        chosen_file = filedialog.askopenfilename()
        if chosen_file:
            file_path.set(chosen_file)
            button_select_file.config(text="선택 완료")
            label_file_name.config(text=os.path.basename(chosen_file))

    def on_all_categories():
        if var_all_categories.get():
            entry_categories.config(state=tk.DISABLED)
            entry_categories.delete(0, tk.END)
            entry_categories.insert(0, "전체 카테고리")
        else:
            entry_categories.config(state=tk.NORMAL)
            entry_categories.delete(0, tk.END)

    def save_file_dialog():
        return filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])

    def on_process_click():
        max_length = int(entry_max_length.get()) if entry_max_length.get().isdigit() else float('inf')
        selected_categories = set(entry_categories.get().split(', ')) if entry_categories.get() and entry_categories.get() != "전체 카테고리" else set()
        output_file_path = save_file_dialog()
        if output_file_path:
            process_file(file_path.get(), output_file_path, var_only_first_line.get(), max_length, selected_categories, var_consider_punctuation.get(), var_consider_case, var_filter_color_code.get())
            messagebox.showinfo("Job Done!", "File saved to: " + output_file_path)
        else:
            messagebox.showinfo("Cancelled", "File save cancelled")

    file_path = tk.StringVar()
    var_only_first_line = tk.BooleanVar(value=True)
    var_consider_punctuation = tk.BooleanVar()
    var_consider_case = tk.BooleanVar()
    var_filter_color_code = tk.BooleanVar(value=True)
    var_all_categories = tk.BooleanVar(value=False)
    entry_max_length = tk.Entry(parent)
    entry_categories = tk.Entry(parent)

    button_select_file = tk.Button(parent, text="파일 선택", command=on_file_select, height=2, width=15, font=('Helvetica', 12, 'bold'), foreground='black')
    button_select_file.pack()

    label_file_name = tk.Label(parent, text="")
    label_file_name.pack()

    tk.Checkbutton(parent, text="첫 라인만 비교", variable=var_only_first_line, font=('Helvetica', 12, 'bold'), foreground='black').pack(pady=(5, 5))
    tk.Label(parent, text="국문 최대 글자수:", font=('Helvetica', 12, 'bold'), foreground='black').pack(pady=(5, 5))
    entry_max_length.pack(pady=(5, 5))
    tk.Label(parent, text="카테고리 선택 (예: 0, 50):", font=('Helvetica', 12, 'bold'), foreground='black').pack(pady=(5, 5))
    entry_categories.pack(pady=(5, 5))
    tk.Checkbutton(parent, text="구두점 비교 (.,:?!)", variable=var_consider_punctuation).pack(pady=(5, 5))
    tk.Checkbutton(parent, text="대소문자 구분", variable=var_consider_case).pack(pady=(5, 5))
    tk.Checkbutton(parent, text="컬러코드 무시", variable=var_filter_color_code).pack(pady=(5, 5))
    tk.Checkbutton(parent, text="전체 카테고리", variable=var_all_categories, command=on_all_categories, font=('Helvetica', 12, 'bold'), foreground='black').pack(pady=(5, 5))
    tk.Button(parent, text="진행", command=on_process_click, height=2, width=6, font=('Helvetica', 12, 'bold'), background='green', foreground='black').pack(pady=(5, 5))


def open_language_data_analyzer():
    language_data_analyzer_tab(analyzer_tab)





def extract_lines_with_different_count():
    def tokenize(text):
        return re.split(r'\\?\\n', text)

    def filter_lines(file_path):
        filtered_lines = []
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                columns = line.strip().split('\t')
                if len(columns) > 6:
                    column_5_tokens = tokenize(columns[5])
                    column_6_tokens = tokenize(columns[6])
                    if len(column_5_tokens) != len(column_6_tokens):
                        filtered_lines.append(line)
        return filtered_lines

    file_path = entry_A.filepath
    if file_path:
        filtered_lines = filter_lines(file_path)
        if filtered_lines:
            save_path = filedialog.asksaveasfilename(defaultextension=".txt", title="Save File")
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.writelines(filtered_lines)
                messagebox.showinfo("Success", "File saved successfully.")
            else:
                messagebox.showinfo("Cancelled", "File save cancelled.")
        else:
            messagebox.showinfo("No Lines Found", "No lines with different counts found.")
    else:
        messagebox.showinfo("No File Selected", "Please select a file first.")






def match_line_breaks_streamlined():
    file_path = entry_A.filepath
    if not file_path:
        messagebox.showerror("Error", "Please select an input file.")
        return

    output_path = filedialog.asksaveasfilename(defaultextension=".txt", title="Select Output File")
    if not output_path:
        messagebox.showerror("Error", "Please select an output file.")
        return

    def transform_text(input_text, lines_parameter):
        words = input_text.split()
        average_words_per_line = max(1, len(words) // lines_parameter)
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(current_line) >= average_words_per_line:
                lines.append(' '.join(current_line))
                current_line = []
        if current_line:
            lines[-1] += ' ' + ' '.join(current_line)
        while len(lines) > lines_parameter:
            lines[-2] += ' ' + lines[-1]
            del lines[-1]
        for i in range(1, len(lines)):
            if lines[i][0] in {'!', '?'}:
                lines[i-1] = lines[i-1].rstrip() + ' ' + lines[i][0]
                lines[i] = lines[i][1:].lstrip()
            elif lines[i][0] in {',', '.'}:
                lines[i-1] = lines[i-1].rstrip() + lines[i][0]
                lines[i] = lines[i][1:].lstrip()
        return '\\n'.join(lines).strip()

    try:
        data = pd.read_csv(file_path, delimiter="\t", header=None, usecols=range(9), dtype=str)
        data[6] = data[6].apply(lambda text: text.replace('\\n', ' '))  # Replace existing line breaks with space
        data['num_linebreaks'] = data[5].apply(lambda text: text.count('\\n') + 1)  # Count number of lines in COL5
        data['target_num_linebreaks'] = data['num_linebreaks']  # Target is based on COL5
        for i in range(len(data)):
            lines_parameter = data.loc[i, 'target_num_linebreaks']
            transformed_text = transform_text(data.loc[i, 6], lines_parameter)
            data.loc[i, 6] = transformed_text
        data.iloc[:, :9].to_csv(output_path, sep="\t", header=None, index=False, quoting=3)  # Use QUOTE_NONE
        messagebox.showinfo("Success", "Line breaks have been matched successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")





def compare_files_thread():
    old_file = entry_A.filepath
    new_file = entry_B.filepath
    
    if not old_file or not new_file:
        messagebox.showerror("Error", "Please select both files.")
        return
    
    try:
        # Trim columns for both files
        old_content = trim_columns(old_file)
        new_content = trim_columns(new_file)
        
        # Create a set of old content for quick lookup
        old_content_set = set(old_content)
        
        # Compare lines and keep only modified ones
        modified_lines = []
        total_lines = len(new_content)
        
        for i, new_line in enumerate(new_content, 1):
            if new_line not in old_content_set:
                modified_lines.append(new_line)
                
        if not modified_lines:
            messagebox.showinfo("결과", "수정된 스트링이 없습니다.")
            return
        
        # Save modified lines
        output_file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f_out:
                f_out.writelines(modified_lines)
            messagebox.showinfo("완료", "수정된 스트링 추출 완료!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
    finally:
        button_compare_files.config(state='normal')

def compare_files():
    button_compare_files.config(state='disabled')
    thread = threading.Thread(target=compare_files_thread)
    thread.start()



def check_hyperlink_sequences():
    """
    Compares hyperlink sequences between Korean and translated text.
    Extracts lines where hyperlink sequences don't match.
    """
    path_A = entry_A.filepath
    if not path_A:
        messagebox.showinfo("안내", "파일 업로드 해 주세요.")
        return

    def extract_hyperlinks(text):
        """
        Extracts hyperlinks from text in the format '@FromHyperlink_ShowItemTooltip(number)'.
        Returns a list of the hyperlink numbers.
        """
        pattern = r'@FromHyperlink_ShowItemTooltip\((\d+)\)'
        return re.findall(pattern, text)

    content_A = trim_columns(path_A)
    extracted_lines = []
    
    for line in content_A:
        columns = line.strip().split('\t')
        if len(columns) < 7:
            continue

        hyperlinks_5 = extract_hyperlinks(columns[5])
        hyperlinks_6 = extract_hyperlinks(columns[6])

        if hyperlinks_5 != hyperlinks_6:
            extracted_lines.append(line)

    if not extracted_lines:
        messagebox.showinfo("문제 없음", "이상 없습니다")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")]
    )
    
    if save_path:
        with open(save_path, 'w', encoding='utf-8') as file:
            file.writelines(extracted_lines)
        messagebox.showinfo("추출 완료", "하이퍼링크 시퀸스 틀린 스트링 저장되었습니다.")









# Initialize the SentenceTransformer model
model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
# global variables
embeddings = None
embeddings_dict = None
index = None
lang_data_path = None
def translation_tab(parent):
    global embeddings, embeddings_dict, index, lang_data_path
        
    def tokenize(text):
        return re.split(r'\\?\\n', text) if isinstance(text, str) else []

    def read_file(filepath, progress_var, total_files, progress_offset):
        data = {}
        original_lines = {}
        df = pd.read_csv(filepath, delimiter="\t", header=None, usecols=range(9))
        total_lines = len(df)
        progress_step = total_lines // 100 or 1

        for i, row in df.iterrows():
            key = i  # Or any other way you want to uniquely identify rows
            korean_text = row[5]  # Assuming column 5 has the Korean text
            data[key] = tokenize(korean_text)
            original_lines[key] = '\t'.join(row.astype(str))  # Join all columns to form the full line

            if i % progress_step == 0 or i == total_lines:
                progress_var.set(progress_offset + (i / total_lines) * 50 / total_files)
                progress_window.update_idletasks()

        return data, original_lines


    def load_embeddings_and_dict(embeddings_file_path, dict_file_path):
        global embeddings, embeddings_dict, index
        try:
            embeddings = np.load(embeddings_file_path)
            with open(dict_file_path, 'rb') as file:
                embeddings_dict = pickle.load(file)
            print("Loaded precomputed embeddings and dictionary.")
            if index is None:
                index = create_faiss_index(embeddings)
            return embeddings, embeddings_dict, True
        except FileNotFoundError as e:
            print("Error: Embeddings or dictionary file not found.")
            return np.array([]), {}, False


    def create_faiss_index(embeddings):
        global index
        print("Creating FAISS index using IndexFlatIP...")
        d = embeddings.shape[1]  # Dimensionality of the vectors
        index = faiss.IndexFlatIP(d)  # Using IndexFlatIP for inner product (cosine similarity)
        faiss.normalize_L2(embeddings)  # Normalize the embeddings to unit length
        index.add(embeddings)  # Add the embeddings to the index
        print("Done !")
        return index


    def select_dict_type(action):
        """Display a window with three buttons for selecting the dictionary type."""

        dict_window = tk.Toplevel(parent)
        dict_window.title("Select Dictionary Type")
        
        window_width = 300
        window_height = 150
        
        parent.update()
        
        main_window_width = parent.winfo_width()
        main_window_height = parent.winfo_height()
        main_window_x = parent.winfo_x()
        main_window_y = parent.winfo_y()
        
        x_position = main_window_x + (main_window_width - window_width) // 2
        y_position = main_window_y + (main_window_height - window_height) // 2
        
        dict_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")        
        
        

        def on_dict_type_select(dict_type):
            dict_window.destroy()
            if action == "load":
                on_load_button_click(dict_type)
            elif action == "update":
                on_update_button_click(dict_type)

        bdo_button = tk.Button(dict_window, text="BDO", command=lambda: on_dict_type_select("BDO"))
        bdo_button.pack(pady=5)

        bdm_button = tk.Button(dict_window, text="BDM", command=lambda: on_dict_type_select("BDM"))
        bdm_button.pack(pady=5)

        bdc_button = tk.Button(dict_window, text="BDC", command=lambda: on_dict_type_select("BDC"))
        bdc_button.pack(pady=5)



    def on_load_button_click(dict_type=None):
        global embeddings, embeddings_dict, index
        if not dict_type:
            select_dict_type("load")
        else:
            # Use the file names directly if they are in the same directory as your script
            embeddings_file_path = f'{dict_type}/embeddings.npy'
            dict_file_path = f'{dict_type}/dictionary.pkl'

            embeddings, embeddings_dict, load_success = load_embeddings_and_dict(embeddings_file_path, dict_file_path)

            if load_success:
                load_files_button.config(text=f"{dict_type} Loaded", font='Helvetica 10 bold', bg="green")
                translate_button.config(state=tk.NORMAL)
            else:
                messagebox.showerror("오류", f"{dict_type} NPY/PKL 파일 찾을 수 없습니다.")
                # Optionally, you might want to update the button's appearance or disable other buttons
                load_files_button.config(text="Load", bg="default")
                translate_button.config(state=tk.DISABLED)  # Disable the translate button if loading failed


    def on_update_button_click(dict_type=None):
        global lang_data_path
        if not dict_type:
            select_dict_type("update")
        else:
            lang_data_path = filedialog.askopenfilename(title=f"Select {dict_type} language data file", filetypes=[("Text files", "*.txt")])
            if lang_data_path:
                # Create the directory if it doesn't exist
                os.makedirs(dict_type, exist_ok=True)
                
                embeddings_file_path = os.path.join(dict_type, 'embeddings.npy')
                dict_file_path = os.path.join(dict_type, 'dictionary.pkl')
                progress_window, progress_var, progress_label = create_progress_bar_window(parent)

                def threaded_update_embeddings():
                    update_embeddings_and_dict(embeddings_file_path, dict_file_path, progress_var, progress_label, progress_window)
                    progress_window.destroy()  # Close the progress window once update is complete

                # Create and start a new thread for the update_embeddings_and_dict function
                update_thread = threading.Thread(target=threaded_update_embeddings)
                update_thread.start()

            else:
                messagebox.showwarning("File Load Cancelled", f"No {dict_type} language data file was selected. Update process is aborted.")


    def update_embeddings_and_dict(embeddings_file_path, dict_file_path, progress_var, progress_label, progress_window):
        global embeddings, embeddings_dict, index, lang_data_path
        print("Starting the embeddings update process...")
        progress_label.config(text="NPY/PKL 최신화 프로세스 시작하겠습니다.")
        progress_window.update_idletasks()        

        # Initialize or load existing embeddings, dictionary, and translation data
        existing_embeddings, existing_dict, load_success = load_embeddings_and_dict(embeddings_file_path, dict_file_path)

        
        # If no embeddings and dictionary are found, initialize new structures and batch process for new embeddings
        if existing_embeddings.size == 0 or not existing_dict:
            print("No precomputed embeddings or dictionary found. Initializing new structures...")
            progress_label.config(text="Initializing new structures and processing new embeddings in batches...")
            progress_window.update_idletasks()

            # Process the new data
            print("\nProcessing the data... (first step)")
            progress_label.config(text="데이터 분석 중... (Step 1)")
            progress_window.update_idletasks()               
            updated_data = pd.read_csv(lang_data_path, delimiter="\t", header=None, usecols=[5, 6])
            updated_data.columns = ['Korean', 'French']  # Explicitly name the columns
            updated_data.dropna(inplace=True)
            
            # Tokenize the Korean and French text
            korean_lines = []
            french_lines = []
            total_rows = len(updated_data)
            processed_rows = 0
            for _, row in updated_data.iterrows():
                korean_tokens = tokenize(row['Korean'])
                french_tokens = tokenize(row['French'])
                if len(korean_tokens) == len(french_tokens):  # Ensure token lengths match
                    korean_lines.extend(korean_tokens)
                    french_lines.extend(french_tokens)
                processed_rows += 1

                # Update progress after processing each row
                if processed_rows % (total_rows // 100) == 0 or processed_rows == total_rows:
                    progress_percentage = (processed_rows / total_rows) * 100
                    progress_var.set(progress_percentage)
                    progress_label.config(text=f"Processing row: {progress_percentage:.2f}%")
                    progress_window.update_idletasks()
                    
                    
                print(f"Processed rows: {processed_rows}/{total_rows}", end='\r')


            tokenized_updated_data = pd.DataFrame({'Korean': korean_lines, 'French': french_lines})

            # Group by Korean strings and keep the most frequent French translation
            print("\nGrouping the strings... (second step)")
            progress_label.config(text="스트링 정리 중... (Step 2)")
            progress_window.update_idletasks()               
            grouped_data = tokenized_updated_data.groupby('Korean')['French'].apply(lambda x: x.value_counts().index[0]).reset_index()
            tokenized_updated_data = grouped_data

            # Batch processing for generating new embeddings
            print("\nGenerating new embeddings... (final step)")
            progress_label.config(text="NPY/PKL 파일 생성하겠습니다 (Final Step)")
            progress_window.update_idletasks()            
            batch_size = 100
            for i in range(0, len(tokenized_updated_data), batch_size):
                batch_data = tokenized_updated_data['Korean'][i:i + batch_size].tolist()
                batch_embeddings = model.encode(batch_data)
                if existing_embeddings.size == 0:
                    existing_embeddings = np.array(batch_embeddings)
                else:
                    existing_embeddings = np.vstack((existing_embeddings, batch_embeddings))
                progress_var.set((i / len(tokenized_updated_data)) * 100)
                progress_label.config(text=f"Embedding progress: {progress_var.get():.2f}%")
                progress_window.update_idletasks()
                print(f"Embedding progress: {i}/{len(tokenized_updated_data)}", end='\r')

            # Save the embeddings and the dictionary
            np.save(embeddings_file_path, existing_embeddings)
            translation_dict = dict(zip(tokenized_updated_data['Korean'], tokenized_updated_data['French']))
            with open(dict_file_path, 'wb') as file:
                pickle.dump(translation_dict, file)

        # If embeddings and dictionary are found, update them with new or changed strings
        else:
            print("Existing embeddings and dictionary found. Updating with new or changed strings...")
            progress_label.config(text="NPY/PKL 파일 찾았습니다. 다음 단계로 넘어가겠습니다.")
            progress_window.update_idletasks()

            # Load existing data from pickle file
            with open(dict_file_path, 'rb') as file:
                existing_translation_dict = pickle.load(file)
            existing_data = pd.DataFrame(list(existing_translation_dict.items()), columns=['Korean', 'French'])

            # Process updated data
            updated_data = pd.read_csv(lang_data_path, delimiter="\t", header=None, usecols=[5, 6])
            updated_data.columns = ['Korean', 'French']
            updated_data.dropna(inplace=True)

            korean_lines = []
            french_lines = []
            total_rows = len(updated_data)
            processed_rows = 0
            for _, row in updated_data.iterrows():
                korean_tokens = tokenize(row['Korean'])
                french_tokens = tokenize(row['French'])
                if len(korean_tokens) == len(french_tokens):
                    korean_lines.extend(korean_tokens)
                    french_lines.extend(french_tokens)
                processed_rows += 1

                if processed_rows % (total_rows // 100) == 0 or processed_rows == total_rows:
                    progress_percentage = (processed_rows / total_rows) * 100
                    progress_var.set(progress_percentage)
                    progress_label.config(text=f"Processing row: {progress_percentage:.2f}% ({processed_rows}/{total_rows})")
                    progress_window.update_idletasks()
                    
                    
                print(f"Processed rows: {processed_rows}/{total_rows}", end='\r')

            tokenized_updated_data = pd.DataFrame({'Korean': korean_lines, 'French': french_lines})

            # Group by Korean strings and keep the most frequent French translation
            print("\nGrouping the strings... (first step)")
            progress_label.config(text="스트링 정리 중... (Step 1)")
            progress_window.update_idletasks()            
            grouped_data = tokenized_updated_data.groupby('Korean')['French'].apply(lambda x: x.value_counts().index[0]).reset_index()
            tokenized_updated_data = grouped_data

            # Save the processed updated data to a temporary pickle file
            temp_pkl_path = "temp_translation_dict.pkl"
            with open(temp_pkl_path, 'wb') as file:
                pickle.dump(dict(zip(tokenized_updated_data['Korean'], tokenized_updated_data['French'])), file)

            # Load the processed updated data from the temporary pickle file
            with open(temp_pkl_path, 'rb') as file:
                updated_translation_dict = pickle.load(file)
            processed_updated_data = pd.DataFrame(list(updated_translation_dict.items()), columns=['Korean', 'French'])

            # Compare the two datasets
            print("\nGrouping the strings...(second step)")
            progress_label.config(text="스트링 비교 중... (Step 2)")
            progress_window.update_idletasks()               
            diff_mask = ~processed_updated_data.set_index(['Korean', 'French']).index.isin(existing_data.set_index(['Korean', 'French']).index)
            new_or_changed_strings = processed_updated_data[diff_mask]

            # Clean up the temporary pickle file
            os.remove(temp_pkl_path)

            print(f'Identified {len(new_or_changed_strings)} new or changed strings.')
            progress_label.config(text=f"신규 및 변경된 스트링 {len(new_or_changed_strings)}개 찾았습니다 - 최신화 시작하겠습니다.")
            progress_window.update_idletasks()
            
            # Update existing embeddings and dictionary
            print("\nUpdating the strings... (final step)")
            progress_label.config(text="최신화 중...")
            progress_window.update_idletasks()            
            total_lines = len(new_or_changed_strings)
            processed_count = 0  # Initialize the count of processed lines

            for idx, row in new_or_changed_strings.iterrows():
                korean, french = row['Korean'], row['French']
                embedding = model.encode([korean])[0]  # Encode the Korean text

                if korean in existing_dict:
                    existing_index = list(existing_dict.keys()).index(korean)
                    existing_embeddings[existing_index, :] = embedding
                else:
                    existing_embeddings = np.vstack([existing_embeddings, embedding])

                existing_dict[korean] = french


                processed_count += 1  # Increment the count of processed items
                progress_percentage = (processed_count / total_lines) * 100  # Calculate progress
                progress_var.set(progress_percentage)
                progress_label.config(text=f"Update progress: {progress_percentage:.2f}% ({processed_count}/{total_lines})")
                progress_window.update_idletasks()
                print(f"Processed lines: {processed_count}/{total_lines}", end='\r')



            # Save the updated embeddings and dictionary
            np.save(embeddings_file_path, existing_embeddings)
            with open(dict_file_path, 'wb') as file:
                pickle.dump(existing_dict, file)

            print(f"\nFinished processing {len(existing_embeddings)} embeddings.")
            print("Embeddings and dictionary updated and saved.")
            progress_var.set(100)  # Set progress to 100%
            progress_label.config(text="Update progress: 100%")

        print("\nUpdating fully completed.\n")
        progress_label.config(text="작업 모두 완료되었습니다 !")
        progress_window.update_idletasks()
        messagebox.showinfo("완료", "최신화 완료되었습니다.")

    # Function to perform translation
    def perform_translation():
        global embeddings, embeddings_dict, index
        
        ref_kr_sentences = pd.Series(list(embeddings_dict.keys()))
        
        def preprocess_text(text):
            # Remove substrings that match the specified patterns
            text = re.sub(r'<Scale:[0-9.]+>', '', text)
            text = re.sub(r'<color:.*?>', '', text)
            return text

        def simple_number_replace(original, translated, best_match_korean):
            # Extract color codes and their positions
            color_codes = [(m.group(0), m.start()) for m in re.finditer(r'<PAColor.*?>|<PAOldColor>', translated)]
            
            # Remove color codes for processing
            translated_no_color = re.sub(r'<PAColor.*?>|<PAOldColor>', '', translated)
            
            # Extract numbers and their positions from original and best match Korean texts
            orig_nums = [(m.group(0), m.start()) for m in re.finditer(r'\d{1,3}(?:[,\s]\d{3})*', original)]
            best_match_korean_nums = [(m.group(0), m.start()) for m in re.finditer(r'\d{1,3}(?:[,\s]\d{3})*', best_match_korean)] if best_match_korean else []
            trans_nums = [(m.group(0), m.start()) for m in re.finditer(r'\d{1,3}(?:[,\s]\d{3})*', translated_no_color)]
            
            # Create a mapping of numbers from the best match Korean text to the original text
            num_mapping = {}
            if len(orig_nums) == len(best_match_korean_nums):
                for (orig_num, _), (korean_num, _) in zip(orig_nums, best_match_korean_nums):
                    num_mapping[korean_num] = orig_num
            
            # If the number of digits in both sentences are the same, proceed with replacement
            if len(orig_nums) == len(best_match_korean_nums):
                offset = 0
                for trans_num, trans_pos in trans_nums:
                    # Find the original number using the mapping created with the best match Korean text
                    orig_num = num_mapping.get(trans_num)
                    if orig_num:
                        # Replace the number
                        translated_no_color = translated_no_color[:trans_pos + offset] + orig_num + translated_no_color[trans_pos + offset + len(trans_num):]
                        offset += len(orig_num) - len(trans_num)  # Update offset

            # Put back the color codes
            for code, pos in reversed(color_codes):
                translated_no_color = translated_no_color[:pos] + code + translated_no_color[pos:]

            return translated_no_color

        def tokenize(text):
            if isinstance(text, str):
                lines_special = text.split('\\n')
                lines_normal = [line for special_line in lines_special for line in special_line.split('\n')]
                return lines_normal
            else:
                return []

        def get_matches(distances, indices, num_results):
            matches = []
            for best_match_indices, distance_scores in zip(indices, distances):
                best_matches = sorted(zip(best_match_indices, distance_scores), key=lambda x: -x[1])[:num_results]
                for best_match_index, distance_score in best_matches:
                    if best_match_index >= len(embeddings):
                        continue  # Skip if index is out of range
                    best_match_korean = list(embeddings_dict.keys())[best_match_index]  # Access the key by index
                    if best_match_korean not in embeddings_dict:
                        continue  # Skip if key not found in dictionary
                    best_match_translation = embeddings_dict[best_match_korean]
                    matches.append((best_match_korean, best_match_translation, distance_score))
            return matches

        def process_batch(batch):
            main_kr_batch = batch.tolist()
            results = []
            
            for sentence in main_kr_batch:
                sentence_embeddings = model.encode([sentence])
                faiss.normalize_L2(sentence_embeddings)
                distances, indices = index.search(sentence_embeddings, 4)
                sentence_matches = [match for match in get_matches(distances, indices, 4) if match[2] >= embedding_threshold]
                results.append((sentence, sentence_matches))  # Always append, even if sentence_matches is empty
            
            return results

        input_text = text_entry.get("1.0", "end-1c")
        input_text = preprocess_text(input_text)
        if input_text.strip() == '':
            messagebox.showerror("Error", "Input field is empty. Please enter some text.")
            return

        try:
            embedding_threshold = float(embedding_threshold_entry.get())
            if embedding_threshold < 0 or embedding_threshold > 1:
                raise ValueError("일치율은 0 ~ 1 사이에 선택하셔야 합니다. (예 : 0.9 = 90% 유사함)")
            if embedding_threshold == 0:
                raise ValueError("0 수치를 선택할 수 없습니다.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return  # Exit the function if the input is not valid

        lines = tokenize(input_text)
        full_reconstruction = []
        result_text.delete("1.0", tk.END)
        result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))

        try:
            for line in lines:
                if not line.strip():  # If the line is originally an empty line
                    full_reconstruction.append('')
                    continue
                results = process_batch(pd.Series([line]))
                for original_sentence, matches in results:
                    if not matches or not original_sentence:
                        full_reconstruction.append('❓❓')  # Add special symbol for missing translation
                        continue
                    matches.sort(key=lambda x: -x[2])
                    best_match_translation = matches[0][1]

                    best_match_korean, best_match_translation, _ = matches[0] # Getting the best match Korean sentence along with its translation
                    final_translation = simple_number_replace(original_sentence, best_match_translation, best_match_korean)
                    
                    # Automatically remove color codes if the original sentence doesn't have them
                    if '<PAColor' not in original_sentence and '<PAOldColor>' not in original_sentence:
                        final_translation = re.sub(r'<PAColor.*?>|<PAOldColor>', '', final_translation)
                  
                    full_reconstruction.append(final_translation)

            result_text.insert(tk.END, "최종 결과:\n\n")
            result_text.insert(tk.END, "\n".join(full_reconstruction), "bold")
            result_text.insert(tk.END, "\n\n\n\n")

            result_text.insert(tk.END, "일치율 결과:\n\n")
            for line in lines:
                batch = tokenize(line)
                results = process_batch(pd.Series(batch))
                if results:
                    for sentence, matches in results:
                        for i, (kr, fr, similarity_score) in enumerate(matches):
                            if i < 2:
                                result_text.insert(tk.END, f"Korean found:\n{kr}\nTranslation:\n{fr}\nAccuracy score:\n{similarity_score * 100:.1f}%\n\n")

        except Exception as e:
            print_exc()
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")



 
    # UI components for the translation tab
    text_entry_label = tk.Label(parent, text="Input Text:", font='Helvetica 10 bold')
    text_entry_label.pack(pady=5)

    text_entry = scrolledtext.ScrolledText(parent, height=20, width=200)
    text_entry.pack(pady=10)

    result_text = scrolledtext.ScrolledText(parent, height=30, width=200)
    result_text.pack(pady=10)

    # Bind the Control-c event to the on_copy function
    result_text.bind("<Control-c>", on_copy)


    embedding_threshold_label = tk.Label(parent, text="최소 일치율:", font='Helvetica 10 bold')
    embedding_threshold_label.pack(pady=5)

    embedding_threshold_entry = tk.Entry(parent)
    embedding_threshold_entry.pack(pady=10)

    embedding_threshold_entry.insert(0, "0.9")

    load_files_button = tk.Button(parent, text="Load", font='Helvetica 10 bold', command=lambda: on_load_button_click(), height=1, width=15)
    load_files_button.pack(pady=(0, 10))  # Pack the load button with padding at the bottom

    update_files_button = tk.Button(parent, text="Update", font='Helvetica 10 bold', command=lambda: on_update_button_click(), height=1, width=15)
    update_files_button.pack(pady=(0, 10))  # Pack the update button with padding at the bottom

    translate_button = tk.Button(parent, text="Search", font='Helvetica 10 bold', command=perform_translation, height=3, width=15, state=tk.DISABLED)
    translate_button.pack()

    button_info5 = tk.Button(parent, text="업데이트 시 주의 사항", command=display_info_message4, height=1, width=20, bg='light blue', font='Helvetica 10 bold')
    button_info5.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor=tk.SE)  # Place the notice button in the bottom right corner


def open_translation_tab():
    translation_tab(translation_text_frame)


def on_tab_changed(event):
    selected_tab = event.widget.select()
    tab_text = event.widget.tab(selected_tab, "text")
    
    # Store current position before resizing
    current_x = root.winfo_x()
    current_y = root.winfo_y()
    
    # Adjust only the size based on the selected tab
    if tab_text == '메인':
        new_width, new_height = 1000, 700
    elif tab_text == '통일성 분석기':
        new_width, new_height = 700, 475
    elif tab_text == '번역 검색 엔진':
        new_width, new_height = 1600, 1000
    else:
        return
    
    # Update geometry while maintaining position
    root.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")


# Create a new tkinter window
root = tk.Tk()
root.title("Translation file Manager ver. 0116 (by Neil)")

# Set the window icon
root.iconbitmap("images/TFMnew123.ico")

# Calculate the center coordinates
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = 1000
window_height = 1000
center_x = int(screen_width // 2 - window_width // 2)
center_y = int(screen_height // 2 - window_height // 2)

# Set the window size and position
root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

# Customize the style of the notebook tabs
style = ttk.Style()
style.configure('TNotebook.Tab', font=('Helvetica', '12', 'bold'))

# Create the notebook (tab control)
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill='both')  # Pack to make it visible

# Create the frames for each tab
main_tab = ttk.Frame(notebook)
datasearch_text_frame = ttk.Frame(notebook)
translation_text_frame = ttk.Frame(notebook)
analyzer_tab = ttk.Frame(notebook)

# Add the tabs to the notebook with their respective names
notebook.add(main_tab, text='메인')
notebook.add(translation_text_frame, text='번역 검색 엔진')
notebook.add(analyzer_tab, text='통일성 분석기')


# Populate the Unicity Simpler Checker
language_data_analyzer_tab(analyzer_tab)
# Populate the Translation tab
translation_tab(translation_text_frame)

notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

# Create labels for path indications
label_A = tk.Label(main_tab, text="원본 파일:", font='Helvetica 10 bold')
label_A.grid(row=0, column=1, padx=(0, 70), sticky="w")
entry_A = tk.Entry(main_tab, width=60)  # Specify width of the entry box
entry_A.filepath = ""
entry_A.grid(row=0, column=1, padx=(70, 0), pady=10, columnspan=3, sticky="e")

label_B = tk.Label(main_tab, text="비교 파일:", font='Helvetica 10 bold')
label_B.grid(row=1, column=1, padx=(0, 70), sticky="w")
entry_B = tk.Entry(main_tab, width=60)  # Specify width of the entry box
entry_B.filepath = ""
entry_B.grid(row=1, column=1, padx=(70, 0), pady=10, columnspan=3, sticky="e")

# Create buttons to upload files
button_A = tk.Button(main_tab, text="파일 찾기", font='Helvetica 10 bold', command=lambda: upload_file(entry_A))
button_A.grid(row=0, column=4, padx=6, sticky='w')
button_B = tk.Button(main_tab, text="파일 찾기", font='Helvetica 10 bold', command=lambda: upload_file(entry_B))
button_B.grid(row=1, column=4, padx=6, sticky='w')


button_info2 = tk.Button(main_tab, text="?", command=display_info_message1, height=1, width=2, bg='light blue', font='Helvetica 10 bold')
button_info2.grid(row=3, column=1, padx=10, sticky='e')

button_info3 = tk.Button(main_tab, text="About", command=display_info_message2, height=1, width=10, bg='light blue', font='Helvetica 10 bold')
button_info3.grid(row=0, column=0, padx=10, sticky='w')

button_info4 = tk.Button(main_tab, text="?", command=display_info_message3, height=1, width=2, bg='light blue', font='Helvetica 10 bold')
button_info4.grid(row=6, column=1, padx=10, sticky='e')

button_go = tk.Button(main_tab, text="스트링 제거\n(키값+원문+번역 동일)", command=lambda: [string_eraser(entry_A.filepath, entry_B.filepath)], height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_go.grid(row=3, column=2, padx=10, pady=10, sticky='ew')

button_go_short = tk.Button(main_tab, text="스트링 제거\n(키값+원문 동일)", command=lambda: [string_eraser_short(entry_A.filepath, entry_B.filepath)], height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_go_short.grid(row=4, column=2, padx=10, pady=10, sticky='ew')

button_extract = tk.Button(main_tab, text="Key1 기준\n렝데 스트링 추출", command=lambda: extract_lines_by_number(entry_A.filepath, entry_B.filepath), height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_extract.grid(row=5, column=2, padx=10, pady=10, sticky='ew')

button_open_extractnodiffy = tk.Button(main_tab, text="단순 국문 수정 추출", command=open_extract_no_diff, height=1, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_open_extractnodiffy.grid(row=6, column=2, padx=10, pady=10, sticky='ew')

button_pattern_check = tk.Button(main_tab, text="패턴 시퀸스 체크", command=pattern_sequence_check, height=1, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_pattern_check.grid(row=7, column=2, padx=10, pady=10, sticky='ew')

button_char = tk.Button(main_tab, text="문자 개수 체크", command=find_character_discrepancies, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_char.grid(row=8, column=2, padx=10, pady=10, sticky='ew')

label_char = tk.Label(main_tab, text="비교값:", fg='black', font='Helvetica 10 bold')
label_char.grid(row=8, column=1, padx=(0, 1), sticky='w')

entry_char = tk.Entry(main_tab, width=16)
entry_char.grid(row=8, column=1, padx=(1, 0), sticky='e')

button_extract_diff_count = tk.Button(main_tab, text="라인 개수 체크", command=extract_lines_with_different_count, height=1, width=30, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_extract_diff_count.grid(row=9, column=2, padx=10, pady=10, sticky='ew')

button_match_line_breaks = tk.Button(main_tab, text="라인 개수 맞추기", command=match_line_breaks_streamlined, height=1, width=30, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_match_line_breaks.grid(row=10, column=2, padx=10, pady=10, sticky='ew')


button_compare_files = tk.Button(main_tab, text="변경된 스트링 추출", command=compare_files, 
                                height=1, width=30, bg='white', fg='black', 
                                font='Helvetica 10 bold', state='disabled')
button_compare_files.grid(row=12, column=2, padx=10, pady=10, sticky='ew')


button_hyperlink_check = tk.Button(main_tab, text="하이퍼링크 체크", 
                                 command=check_hyperlink_sequences,
                                 height=1, width=20,
                                 bg='white', fg='black',
                                 font='Helvetica 10 bold',
                                 state='disabled')
button_hyperlink_check.grid(row=13, column=2, padx=10, pady=10, sticky='ew')


clear_button = tk.Button(main_tab, text="초기화", command=clear_entries, width=10, bg='white', fg='black', font='Helvetica 10 bold')
clear_button.grid(row=0, column=5, padx=10, pady=10, sticky='w')


# Configure the grid to align properly
for i in range(10):  # Adjust the range if you add more rows
    main_tab.grid_rowconfigure(i, weight=1)
for j in range(6):  # Adjust the range if you add more columns
    main_tab.grid_columnconfigure(j, weight=1)

print("실행 완료 !")
root.protocol("WM_DELETE_WINDOW", on_closing)
if splash_active:
    pyi_splash.close()  # Close the splash screen

root.update()  # Update the window
root.deiconify()  # Show the main window

# Start the tkinter event loop
root.mainloop()
