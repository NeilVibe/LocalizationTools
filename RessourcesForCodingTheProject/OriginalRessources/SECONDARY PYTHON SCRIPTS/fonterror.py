import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lxml import etree

def extract_string_ids(text):
    # Regex: number in parentheses, followed by [ and any non-] chars, then ]
    pattern = re.compile(r'\((\d+)\)\[[^\]]+\]')
    return pattern.findall(text)

def parse_xml_for_stringids(xml_path, string_ids):
    found_locs = []
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()
        for loc in root.iter("LocStr"):
            sid = loc.get("StringId")
            if sid in string_ids:
                found_locs.append(etree.fromstring(etree.tostring(loc)))
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
    return found_locs

def write_output_xml(locs, out_path):
    root = etree.Element("MatchedLocStrs")
    for loc in locs:
        root.append(loc)
    xml_bytes = etree.tostring(root, pretty_print=True, encoding='UTF-8')
    with open(out_path, "wb") as f:
        f.write(xml_bytes)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("StringID Extractor")
        self.font_error_path = None
        self.lang_data_path = None

        self.frame = ttk.Frame(root, padding=20)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.font_btn = ttk.Button(self.frame, text="Upload FONT ERROR Text File", command=self.load_font_error)
        self.font_btn.grid(row=0, column=0, sticky="ew", pady=5)

        self.font_label = ttk.Label(self.frame, text="No file selected")
        self.font_label.grid(row=0, column=1, sticky="w", padx=10)

        self.lang_btn = ttk.Button(self.frame, text="Upload LANGUAGE DATA XML File", command=self.load_lang_data)
        self.lang_btn.grid(row=1, column=0, sticky="ew", pady=5)

        self.lang_label = ttk.Label(self.frame, text="No file selected")
        self.lang_label.grid(row=1, column=1, sticky="w", padx=10)

        self.run_btn = ttk.Button(self.frame, text="Extract & Save", command=self.run_extraction)
        self.run_btn.grid(row=2, column=0, columnspan=2, pady=15)

        self.status = ttk.Label(self.frame, text="", foreground="blue")
        self.status.grid(row=3, column=0, columnspan=2, sticky="w")

    def load_font_error(self):
        path = filedialog.askopenfilename(title="Select FONT ERROR text file", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if path:
            self.font_error_path = path
            self.font_label.config(text=os.path.basename(path))
        else:
            self.font_error_path = None
            self.font_label.config(text="No file selected")

    def load_lang_data(self):
        path = filedialog.askopenfilename(title="Select LANGUAGE DATA XML file", filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")])
        if path:
            self.lang_data_path = path
            self.lang_label.config(text=os.path.basename(path))
        else:
            self.lang_data_path = None
            self.lang_label.config(text="No file selected")

    def run_extraction(self):
        if not self.font_error_path or not self.lang_data_path:
            messagebox.showerror("Error", "Please select both files.")
            return

        self.status.config(text="Extracting String IDs...")
        self.root.update_idletasks()

        # Step 1: Extract String IDs
        try:
            with open(self.font_error_path, "r", encoding="utf-8") as f:
                text = f.read()
            string_ids = extract_string_ids(text)
            if not string_ids:
                messagebox.showwarning("No IDs", "No String IDs found in FONT ERROR file.")
                self.status.config(text="")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read FONT ERROR file:\n{e}")
            self.status.config(text="")
            return

        # Step 2: Parse XML and collect matching LocStrs
        self.status.config(text="Parsing XML and collecting matches...")
        self.root.update_idletasks()
        locs = parse_xml_for_stringids(self.lang_data_path, set(string_ids))

        if not locs:
            messagebox.showinfo("No Matches", "No matching String IDs found in the XML file.")
            self.status.config(text="")
            return

        # Step 3: Save output
        out_path = filedialog.asksaveasfilename(
            title="Save Output XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if not out_path:
            self.status.config(text="Save cancelled.")
            return

        try:
            write_output_xml(locs, out_path)
            self.status.config(text=f"Extraction complete. Saved to {out_path}")
            messagebox.showinfo("Done", f"Extraction complete.\nSaved to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write output XML:\n{e}")
            self.status.config(text="")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()