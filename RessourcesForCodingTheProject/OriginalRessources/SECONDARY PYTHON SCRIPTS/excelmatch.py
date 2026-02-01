import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import io

def process_files():
    # Select the match table file (Korean-English)
    match_file = filedialog.askopenfilename(
        title="Select Match Table Excel File (KR-EN)",
        filetypes=[("Excel Files", "*.xlsx *.xls")]
    )
    if not match_file:
        return

    # Select the English-only file
    english_file = filedialog.askopenfilename(
        title="Select English-only Excel File",
        filetypes=[("Excel Files", "*.xlsx *.xls")]
    )
    if not english_file:
        return

    try:
        # Read match table into memory (Korean, English)
        with open(match_file, 'rb') as f:
            match_bytes = io.BytesIO(f.read())
        match_df = pd.read_excel(match_bytes, engine='openpyxl', dtype=str)
        match_df.columns = match_df.columns.str.strip()
        match_df = match_df.dropna(subset=[match_df.columns[0], match_df.columns[1]])
        # Build fast lookup: English -> Korean
        en_to_kr = dict(zip(match_df.iloc[:, 1].str.strip(), match_df.iloc[:, 0].str.strip()))

        # Read English-only file into memory
        with open(english_file, 'rb') as f:
            english_bytes = io.BytesIO(f.read())
        en_df = pd.read_excel(english_bytes, engine='openpyxl', dtype=str)
        en_df.columns = en_df.columns.str.strip()
        # Ensure at least one column
        if en_df.shape[1] < 1:
            messagebox.showerror("Error", "English file must have at least one column.")
            return

        # Insert KR match in 2nd column
        en_col = en_df.columns[0]
        en_df.insert(1, 'Korean', en_df[en_col].map(lambda x: en_to_kr.get(str(x).strip(), "")))

        # Save output
        out_file = filedialog.asksaveasfilename(
            title="Save Output Excel File",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not out_file:
            return
        en_df.to_excel(out_file, index=False, engine='openpyxl')
        messagebox.showinfo("Success", f"Output saved to:\n{out_file}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")

# --- GUI ---
root = tk.Tk()
root.title("KR-EN Excel Match Table Processor")
root.geometry("400x180")
root.resizable(False, False)

frame = tk.Frame(root, padx=20, pady=40)
frame.pack(expand=True)

btn = tk.Button(
    frame,
    text="Select Excel Files and Process",
    font=("Arial", 14),
    width=30,
    height=2,
    command=process_files
)
btn.pack()

root.mainloop()