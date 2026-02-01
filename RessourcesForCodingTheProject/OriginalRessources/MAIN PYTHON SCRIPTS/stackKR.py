import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox

def process_file():
    input_file = filedialog.askopenfilename(title="Select input file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    
    if not input_file:
        messagebox.showinfo("Info", "No file selected.")
        return
    
    try:
        # Read with pandas
        data = pd.read_csv(input_file, delimiter="\t", header=None, usecols=range(9))
        
        # Get the text from the multiline input box
        inserted_text = text_input.get("1.0", tk.END).strip()
        
        # Replace newlines with '\\n'
        inserted_text = inserted_text.replace('\n', '\\n')
        
        # Combine strings
        data[5] = data[5] + '\\n' + inserted_text + '\\n' + data[6]
        
        output_file = filedialog.asksaveasfilename(title="Save output file", defaultextension=".txt", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        
        if not output_file:
            messagebox.showinfo("Info", "No output file selected.")
            return
        
        # Write using direct file I/O instead of pandas to_csv
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            for _, row in data.iterrows():
                line = '\t'.join(str(x) if pd.notna(x) else '' for x in row)
                f.write(line + '\n')
                
        messagebox.showinfo("Success", f"File {output_file} created successfully.")
    
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def process_two_files():
    # Select first file
    file1 = filedialog.askopenfilename(title="Select first file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    if not file1:
        messagebox.showinfo("Info", "No first file selected.")
        return
        
    # Select second file
    file2 = filedialog.askopenfilename(title="Select second file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    if not file2:
        messagebox.showinfo("Info", "No second file selected.")
        return
    
    try:
        # Read both files
        data1 = pd.read_csv(file1, delimiter="\t", header=None, usecols=range(9))
        data2 = pd.read_csv(file2, delimiter="\t", header=None, usecols=range(9))
        
        # Get the text from the multiline input box
        inserted_text = text_input.get("1.0", tk.END).strip()
        
        # Replace newlines with '\\n'
        inserted_text = inserted_text.replace('\n', '\\n')
        
        # Stack index 6 from both files with the inserted text in between
        stacked_text = data2[6] + '\\n' + inserted_text + '\\n' + data1[6]
        
        # Replace index 5 in first file with stacked result
        data1[5] = stacked_text
        
        # Save the result
        output_file = filedialog.asksaveasfilename(title="Save output file", 
                                                  defaultextension=".txt",
                                                  filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        
        if not output_file:
            messagebox.showinfo("Info", "No output file selected.")
            return
            
        # Write to file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            for _, row in data1.iterrows():
                line = '\t'.join(str(x) if pd.notna(x) else '' for x in row)
                f.write(line + '\n')
                
        messagebox.showinfo("Success", f"File {output_file} created successfully.")
        
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def reverse_columns():
    input_file = filedialog.askopenfilename(title="Select file to reverse columns", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    
    if not input_file:
        messagebox.showinfo("Info", "No file selected.")
        return
    
    try:
        # Read with pandas
        data = pd.read_csv(input_file, delimiter="\t", header=None, usecols=range(9))
        
        # Swap columns 5 and 6
        data[[5, 6]] = data[[6, 5]]
        
        output_file = filedialog.asksaveasfilename(title="Save output file", defaultextension=".txt", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        
        if not output_file:
            messagebox.showinfo("Info", "No output file selected.")
            return
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            for _, row in data.iterrows():
                line = '\t'.join(str(x) if pd.notna(x) else '' for x in row)
                f.write(line + '\n')
                
        messagebox.showinfo("Success", f"File {output_file} created with columns 5 and 6 reversed successfully.")
    
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

# Create the main window
root = tk.Tk()
root.title("File Processor")

# Create and pack the multiline input box
text_input = tk.Text(root, height=10, width=50)
text_input.pack(pady=10)

# Create and pack all buttons
process_button = tk.Button(root, text="Process Single File", command=process_file)
process_button.pack(pady=5)

process_two_files_button = tk.Button(root, text="Process Two Files", command=process_two_files)
process_two_files_button.pack(pady=5)

reverse_button = tk.Button(root, text="Reverse", command=reverse_columns)
reverse_button.pack(pady=5)

# Start the GUI event loop
root.mainloop()