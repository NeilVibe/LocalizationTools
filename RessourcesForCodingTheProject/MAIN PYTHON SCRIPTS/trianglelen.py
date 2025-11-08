import pandas as pd
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os

def normalize_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return ''
    # Remove Scale codes
    text = re.sub(r'<Scale[^>]*>|</Scale>', '', text)
    # Remove color codes
    text = re.sub(r'<color[^>]*>|</color>', '', text)
    # Remove PAColor codes
    text = re.sub(r'<PAColor[^>]*>|<PAOldColor>', '', text)
    # Remove Style tags
    text = re.sub(r'<Style:[^>]*>', '', text)
    # Remove special new lines
    text = re.sub(r'\\n', '', text)
    # Remove content in curly braces
    text = re.sub(r'\{[^}]*\}', '', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def simulate_word_wrap(text, max_width=61):
    """Simulates automatic word wrapping based on maximum line width."""
    words = text.split()
    wrapped_lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        # Check if adding this word would exceed the line width
        word_length = len(word)
        space_length = 1 if current_length > 0 else 0
        
        if current_length + word_length + space_length <= max_width:
            # Add to current line
            current_line.append(word)
            current_length += word_length + space_length
        else:
            # Start a new line
            wrapped_lines.append(' '.join(current_line))
            current_line = [word]
            current_length = word_length
    
    # Don't forget the last line
    if current_line:
        wrapped_lines.append(' '.join(current_line))
    
    return wrapped_lines

def is_text_too_long_for_gui(text, max_lines=4, max_width=61):
    """Checks if text would be too long for the interface after word wrapping."""
    wrapped_lines = simulate_word_wrap(text, max_width)
    return len(wrapped_lines) > max_lines

def process_file(file_path):
    status_label.config(text=f"Processing {os.path.basename(file_path)}...")
    root.update()
    
    try:
        data = pd.read_csv(file_path, delimiter="\t", header=None, usecols=range(9))
    except Exception as e:
        messagebox.showerror("Error", f"Error loading file: {str(e)}")
        status_label.config(text="Ready")
        return
    
    # Process rows
    extracted_rows = []
    
    for idx, row in data.iterrows():
        # Check if first column is "2"
        if str(row[0]) != "2":
            continue
        
        # Check if index 6 contains ▶
        content = row[6] if len(row) > 6 and not pd.isna(row[6]) else ""
        if not isinstance(content, str) or "▶" not in content:
            continue
        
        # Normalize the content
        normalized = normalize_text(content)
        
        # Split by ▶ and check each line
        lines = normalized.split("▶")
        
        for line in lines:
            line = line.strip()
            if line and is_text_too_long_for_gui(line, max_lines=4, max_width=61):
                extracted_rows.append(row)
                break
    
    # Write extracted rows to output file
    if extracted_rows:
        output_file = file_path.rsplit('.', 1)[0] + '_extracted.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in extracted_rows:
                f.write('\t'.join([str(cell) if not pd.isna(cell) else '' for cell in row]) + '\n')
        
        messagebox.showinfo("Success", f"Extracted {len(extracted_rows)} rows to:\n{os.path.basename(output_file)}")
        status_label.config(text=f"Extracted {len(extracted_rows)} rows")
    else:
        messagebox.showinfo("No Issues Found", "No problematic text found in the file. No extraction needed.")
        status_label.config(text="No issues found")

def upload_file():
    file_path = filedialog.askopenfilename(
        title="Select Input File",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)
        process_file(file_path)

# Create main window
root = tk.Tk()
root.title("Text Extractor")
root.geometry("600x200")
root.resizable(True, True)

# Create frame
main_frame = ttk.Frame(root, padding="20")
main_frame.pack(fill=tk.BOTH, expand=True)

# File entry and browse button
file_frame = ttk.Frame(main_frame)
file_frame.pack(fill=tk.X, pady=10)

file_label = ttk.Label(file_frame, text="File:")
file_label.pack(side=tk.LEFT, padx=(0, 5))

file_entry = ttk.Entry(file_frame)
file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

browse_button = ttk.Button(file_frame, text="Browse", command=upload_file)
browse_button.pack(side=tk.LEFT)

# Status label
status_frame = ttk.Frame(main_frame)
status_frame.pack(fill=tk.X, pady=10)

status_label = ttk.Label(status_frame, text="Ready")
status_label.pack(anchor=tk.W)

# Description
description = ttk.Label(
    main_frame, 
    text="This tool extracts rows where the first column is '2',\n"
         "the text contains '▶', and at least one text segment\n"
         "would be too long to display properly in the GUI.",
    justify=tk.LEFT
)
description.pack(anchor=tk.W, pady=10)

# Button frame
button_frame = ttk.Frame(main_frame)
button_frame.pack(fill=tk.X, pady=10)

process_button = ttk.Button(
    button_frame, 
    text="Process Selected File", 
    command=lambda: process_file(file_entry.get()) if file_entry.get() else None
)
process_button.pack(side=tk.RIGHT)

# Run the application
if __name__ == "__main__":
    root.mainloop()