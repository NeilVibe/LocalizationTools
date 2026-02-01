print("Translation File Manager 프로그램 실행 중입니다 잠시만 기다려 주십시오...", flush=True)
print("- Translation File Manager LITE ver. 0307 - By Neil")
print("- Translation File Manager LITE ver. 0307 - By Neil")
print("- Translation File Manager LITE ver. 0307 - By Neil")
import os
import sys
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
from collections import defaultdict, Counter
import threading
import pandas as pd
import time
import numpy as np
import datetime

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
    # Sub-GUI for selecting symbol set
    def get_symbol_set():
        dialog = tk.Toplevel(root)
        dialog.title("특수 문자 체크 옵션 선택")
        dialog.geometry("350x200")
        
        var_option = tk.StringVar(value="BDO")  # Default selection is BDO
        symbols_result = {}

        tk.Label(dialog, text="어떤 심볼을 체크할까요?").pack(padx=10, pady=10)

        rb_bdo = tk.Radiobutton(dialog, text="BDO 특수 문자 체크 ({, })", variable=var_option, value="BDO")
        rb_bdo.pack(anchor="w", padx=20)
        rb_bdm = tk.Radiobutton(dialog, text="BDM 특수 문자 체크 (▶, {, }, 🔗, |)", variable=var_option, value="BDM")
        rb_bdm.pack(anchor="w", padx=20)
        rb_custom = tk.Radiobutton(dialog, text="사용자 지정 문자", variable=var_option, value="CUSTOM")
        rb_custom.pack(anchor="w", padx=20)

        custom_entry = tk.Entry(dialog, state="disabled")
        custom_entry.pack(padx=20, pady=5, fill="x")

        # Enable or disable the custom entry depending on the selection.
        def on_option_change(*args):
            if var_option.get() == "CUSTOM":
                custom_entry.config(state="normal")
            else:
                custom_entry.delete(0, tk.END)
                custom_entry.config(state="disabled")
        var_option.trace("w", on_option_change)

        def on_ok():
            option = var_option.get()
            if option == "BDO":
                symbols_result['symbols'] = ["{", "}"]
            elif option == "BDM":
                symbols_result['symbols'] = ["▶", "{", "}", "🔗", "|"]
            elif option == "CUSTOM":
                custom_value = custom_entry.get().strip()
                if not custom_value:
                    messagebox.showerror("Error", "사용자 지정 심볼을 입력해 주세요.")
                    return
                # Treat each character as an individual symbol.
                symbols_result['symbols'] = list(custom_value)
            dialog.destroy()

        ok_button = tk.Button(dialog, text="확인", command=on_ok)
        ok_button.pack(pady=10)

        dialog.grab_set()
        dialog.wait_window()
        return symbols_result.get('symbols')

    # Get the list of symbols to check from the sub-GUI.
    symbols = get_symbol_set()
    if not symbols:
        return  # User cancelled or did not complete selection

    # Ensure a source file is selected.
    path_A = entry_A.filepath
    if not path_A:
        messagebox.showerror("Error", "원본 파일을 먼저 선택해 주세요.")
        return

    content_A = trim_columns(path_A)
    discrepancy_lines = []

    for line in content_A:
        columns = line.strip().split('\t')
        # Ensure there are enough columns to compare (columns 5 and 6)
        if len(columns) < 7:
            continue
        col5_normalized = preprocess_text(columns[5])
        col6_normalized = preprocess_text(columns[6])
        # Check each symbol in the chosen set; if any symbol's count differs, mark the line.
        for sym in symbols:
            if col5_normalized.count(sym) != col6_normalized.count(sym):
                discrepancy_lines.append(line)
                break  # Only add the line once
    if not discrepancy_lines:
        messagebox.showinfo("문제 없음", "모든 심볼의 개수가 일치합니다.")
        return

    path_out = filedialog.asksaveasfilename(defaultextension=".txt")
    if path_out:
        with open(path_out, "w", encoding="utf-8") as file:
            file.writelines(discrepancy_lines)
        messagebox.showinfo("완료", f"선택된 심볼 ({', '.join(symbols)}) 체크 완료!")



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
                    progress_window.update_idletasks()  # Changed from progress_parent to progress_window

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

    # Main frame setup 
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Progress frame setup (at same level as main_frame)
    progress_frame = ttk.Frame(parent)  
    progress_var = tk.StringVar()
    progress_label = ttk.Label(progress_frame, textvariable=progress_var)
    progress_label.pack()
    progress_bar = ttk.Progressbar(progress_frame, length=300, mode='determinate')
    progress_bar.pack(pady=5)

    def show_progress():
        main_frame.pack_forget()
        progress_frame.pack(pady=5)
        main_frame.pack(pady=10, after=progress_frame)
        parent.update_idletasks()

    def hide_progress():
        progress_frame.pack_forget()
        progress_var.set("")
        progress_bar['value'] = 0
        parent.update_idletasks()


    def tokenize(text, only_first_line=False):
        lines = re.split(r'\\?\\n', text) if isinstance(text, str) else []
        return [lines[0]] if only_first_line and lines else lines


    def normalize_text_for_comparison(text):
        # Full normalization including case for comparison
        normalized = text.strip()
        normalized = re.sub(r'<Scale[^>]*>|</Scale>', '', normalized)
        normalized = re.sub(r'<color[^>]*>|</color>', '', normalized)
        normalized = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', normalized)
        normalized = re.sub(r'\{AudioVoice[^}]*\}', '', normalized)
        normalized = re.sub(r'\{ChangeScene[^}]*\}', '', normalized)
        normalized = re.sub(r'\{ChangeAction[^}]*\}', '', normalized)
        normalized = re.sub(r'▶', '', normalized)
        normalized = re.sub(r'[.,:?!]', '', normalized)  # Remove punctuation first
        normalized = re.sub(r'\s+', ' ', normalized)     # Then normalize spaces
        normalized = re.sub(r'[‐‑‒–—−]', '-', normalized)
        return normalized.strip()  # Final strip to remove any leading/trailing spaces

    def normalize_text_for_output(text):
        # Only remove formatting codes, preserve case and everything else
        normalized = text.strip()
        normalized = re.sub(r'<Scale[^>]*>|</Scale>', '', normalized)
        normalized = re.sub(r'<color[^>]*>|</color>', '', normalized)
        normalized = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', normalized)
        normalized = re.sub(r'\{AudioVoice[^}]*\}', '', normalized)
        normalized = re.sub(r'\{ChangeScene[^}]*\}', '', normalized)
        normalized = re.sub(r'\{ChangeAction[^}]*\}', '', normalized)
        return normalized.strip()


    class CategorySelectorDialog(tk.Toplevel):
        def __init__(self, parent, filepath):
            super().__init__(parent)
            self.title("카테고리 선택")
            self.geometry('1200x900')
            
            self.selected_categories = set()
            
            # Create main frame with scrollbar
            main_frame = ttk.Frame(self)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            scrollbar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            
            # Create grid frame
            grid_frame = ttk.Frame(scrollable_frame)
            grid_frame.pack(fill="both", expand=True)
            num_columns = 3
            for i in range(num_columns):
                grid_frame.columnconfigure(i, weight=1, uniform="column")

            # Get categories and their volumes
            high_volume_cats, low_volume_cats, total_lines = analyze_category_relationships(file_path.get())
            
            # Get available space dimensions
            self.update_idletasks()  # Ensure we have current dimensions
            available_width = 1150  # Account for scrollbar and padding
            available_height = 800  # Account for buttons and padding
            
            # Calculate optimal grid dimensions
            total_cats = len(high_volume_cats)
            num_rows = (total_cats + num_columns - 1) // num_columns
            
            # Calculate base box dimensions
            base_width = (available_width - (num_columns + 1) * 20) // num_columns
            base_height = (available_height - (num_rows + 1) * 20) // (num_rows + 1)  # +1 for low volume section
            
            # Get max volume for scaling
            max_volume = max(vol for _, vol in high_volume_cats)
            
            # Display high volume categories
            for i, (cat, volume) in enumerate(high_volume_cats):
                row = i // num_columns
                col = i % num_columns
                
                # Calculate size ratio based on volume
                volume_ratio = (volume / max_volume) ** 0.3  # Use cube root for more balanced scaling
                relative_size = max(0.6, volume_ratio)
                
                actual_height = int(base_height * relative_size)
                
                cat_frame = tk.LabelFrame(grid_frame, relief="groove", bd=2, cursor="hand2")
                cat_frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew",
                             ipadx=int(base_width * 0.1),
                             ipady=int(actual_height * 0.2))
                
                grid_frame.rowconfigure(row, weight=1)
                
                # Scale font size with box size
                font_size = int(min(actual_height * 0.15, 20))  # Cap maximum font size
                header = tk.Label(
                    cat_frame,
                    text=f"Category {cat}\n{volume:.1f}%",
                    font=('Helvetica', font_size, 'bold'),
                    cursor="hand2"
                )
                header.pack(expand=True, fill="both", padx=5, pady=5)
                
                def make_toggle_command(frame, cat_num, widgets):
                    def toggle(event=None):
                        if cat_num in self.selected_categories:
                            self.selected_categories.remove(cat_num)
                            frame.configure(bg='SystemButtonFace')
                            for w in widgets:
                                w.configure(bg='SystemButtonFace')
                        else:
                            self.selected_categories.add(cat_num)
                            frame.configure(bg='pale green')
                            for w in widgets:
                                w.configure(bg='pale green')
                        self.update_display()
                    return toggle
                
                toggle_command = make_toggle_command(cat_frame, cat, [header])
                cat_frame.bind('<Button-1>', toggle_command)
                header.bind('<Button-1>', toggle_command)

            # Display low volume bundle
            if low_volume_cats:
                row = (len(high_volume_cats) + num_columns - 1) // num_columns
                col = 0
                
                total_low_volume = sum(vol for _, vol in low_volume_cats)
                cat_count = len(low_volume_cats)
                
                low_frame = tk.LabelFrame(grid_frame, relief="groove", bd=2, cursor="hand2")
                low_frame.grid(row=row, column=col, columnspan=num_columns, padx=10, pady=5, sticky="nsew")
                
                low_header = tk.Label(
                    low_frame,
                    text=f"소규모 카테고리 (총 {cat_count}개, {total_low_volume:.1f}%)",
                    font=('Helvetica', 12, 'bold'),
                    cursor="hand2"
                )
                low_header.pack(anchor="w", padx=5, pady=5)
                
                def toggle_low_volume(event=None):
                    low_cats = {cat for cat, _ in low_volume_cats}
                    if any(cat in self.selected_categories for cat, _ in low_volume_cats):
                        self.selected_categories.difference_update(low_cats)
                        low_frame.configure(bg='SystemButtonFace')
                        low_header.configure(bg='SystemButtonFace')
                    else:
                        self.selected_categories.update(low_cats)
                        low_frame.configure(bg='pale green')
                        low_header.configure(bg='pale green')
                    self.update_display()
                
                low_frame.bind('<Button-1>', toggle_low_volume)
                low_header.bind('<Button-1>', toggle_low_volume)

            # Buttons at bottom
            button_frame = ttk.Frame(scrollable_frame)
            button_frame.pack(fill="x", padx=10, pady=20)
            
            confirm_button = tk.Button(
                button_frame,
                text="확인",
                command=self.confirm,
                font=('Helvetica', 12, 'bold'),
                width=15,
                height=2
            )
            confirm_button.pack(side="right", padx=10)
            
            cancel_button = tk.Button(
                button_frame,
                text="취소",
                command=self.destroy,
                font=('Helvetica', 12, 'bold'),
                width=15,
                height=2
            )
            cancel_button.pack(side="right", padx=10)

        def update_display(self):
            categories_text.delete('1.0', tk.END)
            categories_text.insert('1.0', ', '.join(map(str, sorted(self.selected_categories))))

        def confirm(self):
            if not self.selected_categories:
                messagebox.showerror("Error", "카테고리를 선택해주세요.")
                return
            self.update_display()
            self.destroy()

    def on_file_select():
        chosen_file = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt")]
        )
        if chosen_file:
            file_path.set(chosen_file)
            button_select_file.config(text="선택 완료", bg='pale green')
            file_label.config(text=os.path.basename(chosen_file))
            CategorySelectorDialog(parent, chosen_file)

    def analyze_category_relationships(filepath):
        category_counts = defaultdict(int)
        total_lines = 0
        
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                total_lines += 1
                columns = line.strip().split('\t')
                if len(columns) > 5:
                    category = columns[0]
                    category_counts[category] += 1

        # Calculate volumes
        volumes = {cat: (count/total_lines)*100 
                  for cat, count in category_counts.items()}
        
        # Separate high and low volume categories
        high_volume_cats = [(cat, vol) for cat, vol in volumes.items() 
                           if vol >= 1]
        low_volume_cats = [(cat, vol) for cat, vol in volumes.items() 
                          if vol < 1]
        
        # Sort high volume categories by volume
        high_volume_cats.sort(key=lambda x: x[1], reverse=True)
        
        return high_volume_cats, low_volume_cats, total_lines



    def validate_manual_categories(input_text, filepath):
        """Validates manually entered categories against the data file"""
        if not file_path.get():
            messagebox.showerror("Error", "먼저 파일을 선택해 주세요.")
            return
            
        if not input_text.strip():
            return set()

        # Get available categories from file
        available_cats = set()
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                cols = line.strip().split('\t')
                if cols:
                    available_cats.add(cols[0])

        # Get current categories from text widget
        current_cats = set(cat.strip() for cat in categories_text.get('1.0', tk.END).strip().split(',') if cat.strip())

        # Process input categories
        new_cats = set()
        for cat in input_text.split(','):
            cat = cat.strip()
            if not cat:
                continue
            if not cat.isdigit():
                messagebox.showerror("Error", f"'{cat}'는 유효한 카테고리 번호가 아닙니다.")
                continue
            if cat not in available_cats:
                messagebox.showerror("Error", f"카테고리 {cat}는 현재 데이터에 존재하지 않습니다.")
                continue
            if cat in current_cats:
                messagebox.showwarning("Warning", f"카테고리 {cat}는 이미 선택되어 있습니다.")
                continue
            new_cats.add(cat)

        # Update the categories text widget with new categories
        if new_cats:
            current_cats.update(new_cats)
            categories_text.delete('1.0', tk.END)
            categories_text.insert('1.0', ', '.join(sorted(current_cats)))
            entry_categories.delete(0, tk.END)



    def process_file(filepath, output_filepath, only_first_line, max_line_length, categories):
        def process_thread():
            try:
                show_progress()
                progress_var.set("분석 시작 중...")
                progress_bar['value'] = 5
                parent.update_idletasks()

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

                progress_var.set("번역문 처리 중...")
                progress_bar['value'] = 60
                parent.update_idletasks()

                with open(filepath, 'r', encoding='utf-8') as file:
                    for line in file:
                        columns = line.strip().split('\t')
                        if len(columns) >= 7 and (not categories or columns[0] in categories):
                            kr_lines = tokenize(columns[5], only_first_line=only_first_line)
                            fr_lines = tokenize(columns[6], only_first_line=only_first_line)
                            
                            for kr, fr in zip(kr_lines, fr_lines):
                                if len(kr) <= max_line_length:
                                    kr_normalized = normalize_text_for_comparison(kr)
                                    fr_normalized = normalize_text_for_comparison(fr)
                                    kr_to_fr[kr_normalized].append({
                                        'normalized': fr_normalized,
                                        'original_fr': fr.strip(),
                                        'original_kr': kr.strip()
                                    })

                progress_var.set("결과 분석 중...")
                progress_bar['value'] = 80
                parent.update_idletasks()

                for kr_norm, translations in kr_to_fr.items():
                    normalized_versions = [t['normalized'] for t in translations]
                    normalized_count = Counter(normalized_versions)
                    
                    if len(normalized_count) > 1:
                        original_kr = translations[0]['original_kr']
                        original_groups = defaultdict(list)
                        
                        for trans in translations:
                            original_groups[trans['normalized']].append(trans['original_fr'])
                        
                        total = len(translations)
                        percentages = {}
                        translations_dict = {}
                        
                        for norm_text, orig_translations in original_groups.items():
                            count = len(orig_translations)
                            percentage = (count / total) * 100
                            percentages[norm_text] = percentage
                            # Store first original translation for this normalized version
                            translations_dict[orig_translations[0]] = percentage
                        
                        min_percentage = min(percentages.values())
                        category = categorize_percentage(min_percentage)
                        categorized_results[category].append((original_kr, translations_dict))

                with open(output_filepath, 'w', encoding='utf-8') as report:
                    for category, blocks in categorized_results.items():
                        if blocks:
                            report.write(f"{'='*20} Category: {category} {'='*20}\n")
                            sorted_blocks = sorted(blocks, key=sort_by_kr_length)
                            for kr, translations in sorted_blocks:
                                report.write(f"{kr}\n")
                                for fr, percentage in sorted(translations.items(), key=lambda x: x[1], reverse=True):
                                    report.write(f"  {percentage:.2f}%: {fr}\n")
                                report.write("\n")
                            report.write("\n" * 2)

                progress_var.set("완료!")
                progress_bar['value'] = 100
                parent.update_idletasks()
                
                parent.after(1000, hide_progress)
                messagebox.showinfo("Success", f"처리가 완료되었습니다.\n저장 위치: {output_filepath}")

            except Exception as e:
                messagebox.showerror("Error", f"Processing error: {str(e)}")
                progress_var.set("처리 중 오류 발생")
                progress_bar['value'] = 0
                hide_progress()

        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()

    def on_process_click():
       if not file_path.get():
           messagebox.showerror("Error", "파일을 선택해 주세요.")
           return
           
       try:
           first_line_only = var_first_line.get()
           
           if custom_var.get():
               max_length_input = entry_length.get().strip()
               if not max_length_input:
                   messagebox.showerror("Error", "최대 글자수를 입력해 주세요.")
                   return
               try:
                   max_length = int(max_length_input)
                   if max_length <= 0:
                       raise ValueError("Maximum length must be a positive integer")
               except ValueError:
                   messagebox.showerror("Error", "올바른 최대 글자수를 입력해 주세요. (양의 정수)")
                   return
           else:
               max_length = int(length_var.get())

           categories_input = categories_text.get('1.0', tk.END).strip()

           if not categories_input:
               messagebox.showerror("Error", "하나 이상의 카테고리를 선택해 주세요.")
               return

           timestamp = datetime.datetime.now().strftime("%m%d")
           
           _, low_volume_cats, _ = analyze_category_relationships(file_path.get())
           low_volume_category_numbers = {str(cat) for cat, _ in low_volume_cats}
           
           selected_categories = set(cat.strip() for cat in categories_input.split(','))
           regular_categories = selected_categories - low_volume_category_numbers
           has_low_volume = bool(selected_categories & low_volume_category_numbers)
           
           if regular_categories and has_low_volume:
               filename = f"{timestamp}_Line Autocheck_Category_{'_'.join(sorted(regular_categories))}_소규모카테고리.txt"
           elif regular_categories:
               filename = f"{timestamp}_Line Autocheck_Category_{'_'.join(sorted(regular_categories))}.txt"
           elif has_low_volume:
               filename = f"{timestamp}_Line Autocheck_소규모카테고리.txt"
           else:
               filename = f"{timestamp}_Line Autocheck.txt"

           if getattr(sys, 'frozen', False):
               script_dir = os.path.dirname(sys.executable)
           else:
               script_dir = os.path.dirname(os.path.abspath(__file__))

           output_dir = os.path.join(script_dir, "Line_Autocheck_Results")
           os.makedirs(output_dir, exist_ok=True)
           output_path = os.path.join(output_dir, filename)

           process_file(
               file_path.get(),
               output_path,
               first_line_only,
               max_length,
               regular_categories
           )

       except Exception as e:
           messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")


    # File selection frame
    file_frame = ttk.Frame(main_frame)
    file_frame.pack(fill="x", pady=(0, 10))
    
    file_path = tk.StringVar()
    button_select_file = tk.Button(
        file_frame,
        text="파일 선택",
        command=on_file_select,
        height=2,
        width=15,
        font=('Helvetica', 12, 'bold')
    )
    button_select_file.pack(side="left", padx=5)
    
    file_label = ttk.Label(file_frame, text="")
    file_label.pack(side="left", padx=5)

    # Parameters frame
    param_frame = ttk.LabelFrame(main_frame, text="설정")
    param_frame.pack(fill="x", pady=10)

    var_first_line = tk.BooleanVar(value=False)
    ttk.Checkbutton(param_frame, text="첫 라인만 비교", variable=var_first_line).pack(anchor="w", padx=5, pady=2)

    # Length frame with radio buttons and custom option
    length_frame = ttk.LabelFrame(main_frame, text="국문 길이")
    length_frame.pack(fill="x", pady=10)

    length_options_frame = ttk.Frame(length_frame)
    length_options_frame.pack(fill="x", padx=5, pady=5)

    length_var = tk.StringVar(value="50")
    custom_var = tk.BooleanVar(value=False)

    def toggle_custom_entry(*args):
        if custom_var.get():
            entry_length.config(state='normal')
            length_var.set('')  # This deselects all radio buttons
            for rb in [short_rb, medium_rb, long_rb]:
                rb.config(state='disabled')
        else:
            entry_length.delete(0, tk.END)
            entry_length.config(state='disabled')
            length_var.set('50')  # Select medium option
            for rb in [short_rb, medium_rb, long_rb]:
                rb.config(state='normal')

    short_rb = ttk.Radiobutton(length_options_frame, text="하", variable=length_var, value="25")
    medium_rb = ttk.Radiobutton(length_options_frame, text="중", variable=length_var, value="50")
    long_rb = ttk.Radiobutton(length_options_frame, text="상", variable=length_var, value="100")
    custom_cb = ttk.Checkbutton(length_options_frame, text="사용자 지정", variable=custom_var, command=toggle_custom_entry)
    entry_length = ttk.Entry(length_options_frame, width=10, state='disabled')

    short_rb.pack(side="left", padx=5)
    medium_rb.pack(side="left", padx=5)
    long_rb.pack(side="left", padx=5)
    custom_cb.pack(side="left", padx=5)
    entry_length.pack(side="left", padx=5)

    # Manual category input frame
    cat_input_frame = ttk.Frame(main_frame)
    cat_input_frame.pack(fill="x", pady=5)
    ttk.Label(cat_input_frame, text="카테고리 수동 추가 입력:", font=('Helvetica', 10, 'bold')).pack(side="left")
    entry_categories = ttk.Entry(cat_input_frame)
    entry_categories.pack(side="left", padx=5, fill="x", expand=True)
    ttk.Button(cat_input_frame, text="추가", command=lambda: validate_manual_categories(entry_categories.get(), file_path.get())).pack(side="left", padx=5)

    # Categories frame
    categories_frame = ttk.LabelFrame(main_frame, text="선택된 카테고리")
    categories_frame.pack(fill="x", pady=10)
    categories_text = tk.Text(categories_frame, height=10, wrap=tk.WORD)
    categories_text.pack(fill="x", padx=5, pady=5)

    # Process button
    process_button = tk.Button(
        main_frame,
        text="진행",
        command=lambda: on_process_click() if file_path.get() else messagebox.showerror("Error", "파일을 선택해 주세요."),
        height=2,
        width=15,
        font=('Helvetica', 12, 'bold'),
        bg='pale green'
    )
    process_button.pack(pady=10)


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




# Create a new tkinter window
root = tk.Tk()
root.title("Translation file Manager LITE - Version : 0307 (by Neil)")

# Set the window icon
root.iconbitmap("images/favicon.ico")

# Calculate the center coordinates
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = 800
window_height = 800
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
analyzer_tab = ttk.Frame(notebook)

# Add the tabs to the notebook with their respective names
notebook.add(main_tab, text='메인')
notebook.add(analyzer_tab, text='라인 통일성 분석')

# Populate the Language Data Analyzer tab
language_data_analyzer_tab(analyzer_tab)

# Create labels for path indications
label_A = tk.Label(main_tab, text="원본 파일:", font='Helvetica 10 bold')
label_A.grid(row=0, column=1, padx=(0, 30), sticky="w")
entry_A = tk.Entry(main_tab, width=60)  # Specify width of the entry box
entry_A.filepath = ""
entry_A.grid(row=0, column=1, padx=(30, 0), pady=10, columnspan=3, sticky="e")

label_B = tk.Label(main_tab, text="비교 파일:", font='Helvetica 10 bold')
label_B.grid(row=1, column=1, padx=(0, 30), sticky="w")
entry_B = tk.Entry(main_tab, width=60)  # Specify width of the entry box
entry_B.filepath = ""
entry_B.grid(row=1, column=1, padx=(30, 0), pady=10, columnspan=3, sticky="e")

# Create buttons to upload files
button_A = tk.Button(main_tab, text="파일 찾기", command=lambda: upload_file(entry_A), font='Helvetica 10 bold')
button_A.grid(row=0, column=4, padx=6, sticky='w')
button_B = tk.Button(main_tab, text="파일 찾기", command=lambda: upload_file(entry_B), font='Helvetica 10 bold')
button_B.grid(row=1, column=4, padx=6, sticky='w')


button_info2 = tk.Button(main_tab, text="?", command=display_info_message1, height=1, width=2, bg='light blue', font='Helvetica 10 bold')
button_info2.grid(row=3, column=1, padx=10, sticky='e')

button_info3 = tk.Button(main_tab, text="About", command=display_info_message2, height=1, width=10, bg='light blue', font='Helvetica 10 bold')
button_info3.grid(row=0, column=0, padx=10, sticky='w')

button_info4 = tk.Button(main_tab, text="?", command=display_info_message3, height=1, width=2, bg='light blue', font='Helvetica 10 bold')
button_info4.grid(row=7, column=1, padx=10, sticky='e')


button_go = tk.Button(main_tab, text="스트링 제거\n(키값+원문+번역 동일)", command=lambda: [string_eraser(entry_A.filepath, entry_B.filepath)], height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_go.grid(row=3, column=2, padx=10, pady=10, sticky='ew')

button_go_short = tk.Button(main_tab, text="스트링 제거\n(키값+원문 동일)", command=lambda: [string_eraser_short(entry_A.filepath, entry_B.filepath)], height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_go_short.grid(row=4, column=2, padx=10, pady=10, sticky='ew')

button_extract = tk.Button(main_tab, text="Key1 기준\n렝데 스트링 추출", command=lambda: extract_lines_by_number(entry_A.filepath, entry_B.filepath), height=2, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_extract.grid(row=5, column=2, padx=10, pady=10, sticky='ew')


button_open_extractnodiffy = tk.Button(main_tab, text="단순 국문 수정 추출", command=open_extract_no_diff, height=1, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_open_extractnodiffy.grid(row=7, column=2, padx=10, pady=10, sticky='ew')

button_pattern_check = tk.Button(main_tab, text="패턴 시퀸스 체크", command=pattern_sequence_check, height=1, width=20, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_pattern_check.grid(row=8, column=2, padx=10, pady=10, sticky='ew')


button_char = tk.Button(main_tab, text="문자 개수 체크", command=find_character_discrepancies, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_char.grid(row=9, column=2, padx=10, pady=10, sticky='ew')

button_extract_diff_count = tk.Button(main_tab, text="라인 개수 체크", command=extract_lines_with_different_count, height=1, width=30, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_extract_diff_count.grid(row=10, column=2, padx=10, pady=10, sticky='ew')

button_match_line_breaks = tk.Button(main_tab, text="라인 개수 맞추기", command=match_line_breaks_streamlined, height=1, width=30, bg='white', fg='black', font='Helvetica 10 bold', state='disabled')
button_match_line_breaks.grid(row=11, column=2, padx=10, pady=10, sticky='ew')


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



clear_button = tk.Button(main_tab, text="초기화", command=clear_entries, bg='white', fg='black', font='Helvetica 10 bold')
clear_button.grid(row=0, column=5, padx=10, pady=10, sticky='w')


# Configure the grid to align properly
for i in range(10):  # Adjust the range if you add more rows
    main_tab.grid_rowconfigure(i, weight=1)
for j in range(6):  # Adjust the range if you add more columns
    main_tab.grid_columnconfigure(j, weight=1)

print("실행 완료 !")

# Start the tkinter event loop
root.mainloop()