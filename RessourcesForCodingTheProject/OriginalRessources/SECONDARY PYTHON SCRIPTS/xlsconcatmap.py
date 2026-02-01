#!/usr/bin/env python3
"""
Excel Column Mapping Tool - Single Master GUI
Select SOURCE and TARGET Excel files, choose columns to concatenate for matching,
and map a value from SOURCE to TARGET when matches are found.
Mapped output column is appended at the far right of TARGET.
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

def master_column_selector(src_cols, tgt_cols):
    """Single GUI to select all columns at once"""
    selections = {}

    def on_ok():
        selections['col1_src'] = combo_col1_src.get()
        selections['col2_src'] = combo_col2_src.get()
        selections['col_out_src'] = combo_col_out_src.get()
        selections['col1_tgt'] = combo_col1_tgt.get()
        selections['col2_tgt'] = combo_col2_tgt.get()
        selections['col_out_tgt'] = combo_col_out_tgt.get()
        win.destroy()

    win = tk.Toplevel()
    win.title("Select Columns for Mapping")

    frm = tk.Frame(win, padx=10, pady=10)
    frm.pack()

    # SOURCE section
    tk.Label(frm, text="SOURCE Columns", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,5))
    tk.Label(frm, text="First column to concatenate:").grid(row=1, column=0, sticky="e")
    combo_col1_src = ttk.Combobox(frm, values=src_cols, state="readonly", width=40)
    combo_col1_src.grid(row=1, column=1)
    combo_col1_src.current(0)

    tk.Label(frm, text="Second column to concatenate:").grid(row=2, column=0, sticky="e")
    combo_col2_src = ttk.Combobox(frm, values=src_cols, state="readonly", width=40)
    combo_col2_src.grid(row=2, column=1)
    combo_col2_src.current(0)

    tk.Label(frm, text="Output column (value to map):").grid(row=3, column=0, sticky="e")
    combo_col_out_src = ttk.Combobox(frm, values=src_cols, state="readonly", width=40)
    combo_col_out_src.grid(row=3, column=1)
    combo_col_out_src.current(0)

    # TARGET section
    tk.Label(frm, text="TARGET Columns", font=("Arial", 12, "bold")).grid(row=4, column=0, columnspan=2, pady=(10,5))
    tk.Label(frm, text="First column to concatenate:").grid(row=5, column=0, sticky="e")
    combo_col1_tgt = ttk.Combobox(frm, values=tgt_cols, state="readonly", width=40)
    combo_col1_tgt.grid(row=5, column=1)
    combo_col1_tgt.current(0)

    tk.Label(frm, text="Second column to concatenate:").grid(row=6, column=0, sticky="e")
    combo_col2_tgt = ttk.Combobox(frm, values=tgt_cols, state="readonly", width=40)
    combo_col2_tgt.grid(row=6, column=1)
    combo_col2_tgt.current(0)

    tk.Label(frm, text="Output column name (will be appended at far right):").grid(row=7, column=0, sticky="e")
    combo_col_out_tgt = ttk.Combobox(frm, values=tgt_cols + ["<NEW COLUMN>"], state="normal", width=40)
    combo_col_out_tgt.grid(row=7, column=1)
    combo_col_out_tgt.set("<NEW COLUMN>")

    tk.Button(frm, text="OK", command=on_ok).grid(row=8, column=0, columnspan=2, pady=10)

    win.grab_set()
    win.wait_window()
    return selections

def main():
    root = tk.Tk()
    root.withdraw()  # Hide main window

    try:
        log("Select SOURCE Excel file...")
        source_path = select_file("Select SOURCE Excel file")
        if not source_path:
            log("No SOURCE file selected. Exiting.")
            return

        log("Select TARGET Excel file...")
        target_path = select_file("Select TARGET Excel file")
        if not target_path:
            log("No TARGET file selected. Exiting.")
            return

        log(f"Loading SOURCE file: {source_path}")
        df_source = pd.read_excel(source_path)
        log(f"SOURCE shape: {df_source.shape}")

        log(f"Loading TARGET file: {target_path}")
        df_target = pd.read_excel(target_path)
        log(f"TARGET shape: {df_target.shape}")

        # Master column selection
        selections = master_column_selector(list(df_source.columns), list(df_target.columns))
        col1_src_name = selections['col1_src']
        col2_src_name = selections['col2_src']
        col_out_src_name = selections['col_out_src']
        col1_tgt_name = selections['col1_tgt']
        col2_tgt_name = selections['col2_tgt']
        col_out_tgt_name = selections['col_out_tgt']

        log("Creating mapping dictionary from SOURCE...")
        mapping_dict = {}
        for _, row in df_source.iterrows():
            key = str(row[col1_src_name]).strip() + str(row[col2_src_name]).strip()
            mapping_dict[key] = row[col_out_src_name]

        log(f"Mapping dictionary created with {len(mapping_dict)} entries.")

        log("Applying mapping to TARGET...")
        match_count = 0
        mapped_values = []
        for _, row in df_target.iterrows():
            key = str(row[col1_tgt_name]).strip() + str(row[col2_tgt_name]).strip()
            if key in mapping_dict:
                mapped_values.append(mapping_dict[key])
                match_count += 1
            else:
                mapped_values.append(None)

        # Append mapped column at far right
        if col_out_tgt_name == "<NEW COLUMN>":
            col_out_tgt_name = "MappedValue"
        df_target[col_out_tgt_name] = mapped_values

        log(f"Mapping applied. Matches found: {match_count}")

        # Save updated TARGET file
        base, ext = os.path.splitext(target_path)
        output_path = f"{base}_mapped{ext}"
        df_target.to_excel(output_path, index=False)
        log(f"Updated TARGET file saved as: {output_path}")

        messagebox.showinfo("Success", f"Mapping completed!\nMatches found: {match_count}\nSaved to:\n{output_path}")

    except Exception as e:
        log(f"ERROR: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred:\n{e}")

if __name__ == "__main__":
    main()