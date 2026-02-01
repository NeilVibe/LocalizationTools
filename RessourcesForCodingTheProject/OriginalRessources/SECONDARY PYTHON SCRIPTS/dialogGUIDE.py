import pandas as pd
import re
import os
from tkinter import Tk, filedialog

def extract_number(text):
    match = re.search(r'(\d+)$', str(text))
    return int(match.group(1)) if match else None

def main():
    # Hide Tkinter root window
    Tk().withdraw()

    # Ask user to select Excel file
    file_path = filedialog.askopenfilename(
        title="Select Excel File",
        filetypes=[("Excel Files", "*.xlsx *.xls")]
    )

    if not file_path:
        print("No file selected. Exiting.")
        return

    # Read Excel file without treating first row as header
    df = pd.read_excel(file_path, header=None)

    # Ensure there are at least 3 columns
    if df.shape[1] < 3:
        print("The file must have at least 3 columns.")
        return

    # Extract number from 3rd column
    df['__sort_key__'] = df.iloc[:, 2].apply(extract_number)

    # Sort by extracted number
    df_sorted = df.sort_values(by='__sort_key__', ascending=True).drop(columns=['__sort_key__'])

    # Create output file path
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_sorted{ext}"

    # Save sorted Excel without header and without index
    df_sorted.to_excel(output_path, index=False, header=False)

    print(f"Sorted file saved as: {output_path}")

if __name__ == "__main__":
    main()