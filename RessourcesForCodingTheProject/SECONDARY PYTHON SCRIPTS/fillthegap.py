#!/usr/bin/env python3
"""
Excel Empty Cell Filler Tool
Select one Excel file, choose SOURCE and TARGET columns.
For every empty cell in SOURCE, fill it with the TARGET value in the same row (if it exists).
Saves updated file as *_filled.xlsx.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
from datetime import datetime
import traceback

def log(msg):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def select_file(title):
    """Open file dialog to select Excel file"""
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=[("Excel files", "*.xlsx")]
    )
    return file_path

def column_selector(columns):
    """GUI to select SOURCE and TARGET columns"""
    selections = {}

    def on_ok():
        selections['source_col'] = combo_source.get()
        selections['target_col'] = combo_target.get()
        win.destroy()

    win = tk.Toplevel()
    win.title("Select Columns")

    frm = tk.Frame(win, padx=10, pady=10)
    frm.pack()

    tk.Label(frm, text="SOURCE column (will be filled if empty):").grid(row=0, column=0, sticky="e")
    combo_source = ttk.Combobox(frm, values=columns, state="readonly", width=40)
    combo_source.grid(row=0, column=1)
    combo_source.current(0)

    tk.Label(frm, text="TARGET column (value to copy):").grid(row=1, column=0, sticky="e")
    combo_target = ttk.Combobox(frm, values=columns, state="readonly", width=40)
    combo_target.grid(row=1, column=1)
    combo_target.current(0)

    tk.Button(frm, text="OK", command=on_ok).grid(row=2, column=0, columnspan=2, pady=10)

    win.grab_set()
    win.wait_window()
    return selections

def main():
    root = tk.Tk()
    root.withdraw()  # Hide main window

    try:
        log("Select Excel file...")
        file_path = select_file("Select Excel file")
        if not file_path:
            log("No file selected. Exiting.")
            return

        log(f"Loading file: {file_path}")
        df = pd.read_excel(file_path)
        log(f"File shape: {df.shape}")

        # Column selection
        selections = column_selector(list(df.columns))
        source_col = selections['source_col']
        target_col = selections['target_col']

        log(f"Selected SOURCE column: {source_col}")
        log(f"Selected TARGET column: {target_col}")

        # Fill empty SOURCE cells with TARGET values
        fill_count = 0
        for idx in df.index:
            src_val = df.at[idx, source_col]
            tgt_val = df.at[idx, target_col]
            if (pd.isna(src_val) or str(src_val).strip() == "") and not pd.isna(tgt_val) and str(tgt_val).strip() != "":
                df.at[idx, source_col] = tgt_val
                fill_count += 1

        log(f"Filled {fill_count} empty cells in SOURCE column.")

        # Save updated file
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_filled{ext}"
        df.to_excel(output_path, index=False)
        log(f"Updated file saved as: {output_path}")

        messagebox.showinfo("Success", f"Filling completed!\nCells filled: {fill_count}\nSaved to:\n{output_path}")

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred:\n{e}")

if __name__ == "__main__":
    main()