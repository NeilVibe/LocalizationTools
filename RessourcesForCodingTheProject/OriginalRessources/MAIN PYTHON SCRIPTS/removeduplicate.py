import tkinter as tk 
from tkinter import filedialog

def remove_duplicate_rows():
    # Create and hide root window
    root = tk.Tk()
    root.withdraw()
    
    # Get input file
    input_file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not input_file:
        print("No file selected")
        return
        
    # Get output file
    output_file = filedialog.asksaveasfilename(defaultextension=".txt")
    if not output_file:
        print("No output location selected") 
        return

    # Track unique rows by their columns 5 and 6
    seen_content = set()
    unique_rows = []
    
    # Process the file
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            cols = line.strip().split('\t')
            if len(cols) >= 7:
                # Use columns 5 and 6 as key
                content_key = (cols[5], cols[6])
                # Only keep first occurrence
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    unique_rows.append(line)

    # Write unique rows to output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(unique_rows)
        
    print(f"Done! Kept {len(unique_rows)} unique rows")

if __name__ == "__main__":
    remove_duplicate_rows()