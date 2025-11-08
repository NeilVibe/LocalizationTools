import pandas as pd
import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox

def is_valid_xlsx(path: str) -> bool:
    """Check if file is a valid XLSX (zip-based) file."""
    if not path.lower().endswith(".xlsx"):
        return False
    try:
        with zipfile.ZipFile(path, 'r') as z:
            # XLSX must contain [Content_Types].xml
            return "[Content_Types].xml" in z.namelist()
    except zipfile.BadZipFile:
        return False

def copy_excel(source_path: str, dest_path: str) -> None:
    all_sheets = pd.read_excel(source_path, sheet_name=None, engine="openpyxl")
    with pd.ExcelWriter(dest_path, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

def main():
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Select Excel File", "Select the source Excel .xlsx file to copy.")
    source_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel files (.xlsx)", "*.xlsx")]
    )
    if not source_path:
        messagebox.showwarning("No file selected", "Operation cancelled.")
        return

    if not is_valid_xlsx(source_path):
        messagebox.showerror("Invalid File", "The selected file is not a valid .xlsx file.")
        return

    folder, filename = os.path.split(source_path)
    name, ext = os.path.splitext(filename)
    dest_path = os.path.join(folder, f"{name}_copy.xlsx")

    try:
        copy_excel(source_path, dest_path)
        messagebox.showinfo("Success", f"Copied to:\n{dest_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to copy:\n{e}")

if __name__ == "__main__":
    main()