import pandas as pd
import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox

def has_korean(text):
    return re.search(r'[\uac00-\ud7af]', str(text)) is not None

def has_english(text):
    return re.search(r'[A-Za-z]', str(text)) is not None

def has_underscore(text):
    return '_' in str(text)

def is_mixed_korean_english_underscore(text):
    if not isinstance(text, str):
        return False
    return has_korean(text) and has_english(text) and has_underscore(text)

def clean_excel_regex():
    file_path = filedialog.askopenfilename(
        title="Select Excel file to clean (Regex)",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not file_path:
        messagebox.showinfo("No file selected", "No file was selected. Exiting.")
        return

    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl')
    except Exception as e:
        messagebox.showerror("Error", f"Could not read Excel file:\n{e}")
        return

    col_to_use = 0
    mask = df[col_to_use].apply(lambda x: not is_mixed_korean_english_underscore(x))
    df_cleaned = df[mask]

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_cleaned{ext}"

    try:
        df_cleaned.to_excel(output_path, index=False, header=False, engine='openpyxl')
        messagebox.showinfo("Success", f"Cleaned file saved as:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save cleaned Excel file:\n{e}")

def add_ㄴ_to_first_column():
    file_path = filedialog.askopenfilename(
        title="Select Excel file to add ㄴ",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not file_path:
        messagebox.showinfo("No file selected", "No file was selected. Exiting.")
        return

    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl')
    except Exception as e:
        messagebox.showerror("Error", f"Could not read Excel file:\n{e}")
        return

    # Add "ㄴ" at the beginning of each value in the first column
    df[0] = df[0].apply(lambda x: f"ㄴ{x}" if pd.notnull(x) else x)

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_add_ㄴ{ext}"

    try:
        df.to_excel(output_path, index=False, header=False, engine='openpyxl')
        messagebox.showinfo("Success", f"File with ㄴ added saved as:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save Excel file:\n{e}")

def remove_leading_nieun_and_hyphen():
    file_path = filedialog.askopenfilename(
        title="Select Excel file to clean leading ㄴ or - ",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not file_path:
        messagebox.showinfo("No file selected", "No file was selected. Exiting.")
        return

    try:
        df = pd.read_excel(file_path, header=None, engine='openpyxl')
    except Exception as e:
        messagebox.showerror("Error", f"Could not read Excel file:\n{e}")
        return

    def clean_leading(text):
        if pd.isnull(text):
            return text
        # Remove leading "ㄴ" or "- " (hyphen + space) only at the start
        return re.sub(r'^(ㄴ|-\s)', '', str(text))

    df[0] = df[0].apply(clean_leading)

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_no_leading_nieun_hyphen{ext}"

    try:
        df.to_excel(output_path, index=False, header=False, engine='openpyxl')
        messagebox.showinfo("Success", f"File with leading ㄴ or '- ' removed saved as:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not save Excel file:\n{e}")

def main():
    root = tk.Tk()
    root.title("Excel Regex & ㄴ Tool")
    root.geometry("350x220")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(expand=True)

    btn_clean = tk.Button(
        frame, text="Clean Excel (Regex)", width=25, height=2,
        command=clean_excel_regex
    )
    btn_clean.pack(pady=(0, 10))

    btn_add_nieun = tk.Button(
        frame, text="Add ㄴ to First Column", width=25, height=2,
        command=add_ㄴ_to_first_column
    )
    btn_add_nieun.pack(pady=(0, 10))

    btn_remove_leading = tk.Button(
        frame, text="Remove leading ㄴ or '- '", width=25, height=2,
        command=remove_leading_nieun_and_hyphen
    )
    btn_remove_leading.pack()

    root.mainloop()

if __name__ == "__main__":
    main()