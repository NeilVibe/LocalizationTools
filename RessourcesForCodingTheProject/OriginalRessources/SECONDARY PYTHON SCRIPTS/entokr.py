#!/usr/bin/env python3
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from lxml import etree
from openpyxl import Workbook

def fix_bad_entities(xml_text):
    # Fixes unescaped ampersands
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"Error reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None
    return recovered

def get_all_xml_files(input_folder):
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

def is_valid_korean_string(s):
    if not s or not s.strip():
        return False
    # Remove whitespace and symbols, check if any Korean remains
    s_clean = re.sub(r'[\s\W_]+', '', s, flags=re.UNICODE)
    # At least one Korean character (Hangul Syllables: U+AC00–U+D7AF)
    return bool(re.search(r'[\uac00-\ud7af]', s_clean))

def extract_unique_korean_strings(xml_folder):
    """
    Returns a sorted list of unique, valid Korean strings from all XML files in the folder.
    """
    xml_files = get_all_xml_files(xml_folder)
    print(f"Scanning {len(xml_files)} XML files for Korean strings...")
    korean_set = set()
    for xml_path in xml_files:
        xml_root = parse_xml_file(xml_path)
        if xml_root is None:
            continue
        for loc in xml_root.iter("LocStr"):
            kr = loc.get("StrOrigin", "")
            if is_valid_korean_string(kr):
                korean_set.add(kr.strip())
    print(f"Found {len(korean_set)} unique Korean strings.")
    return sorted(korean_set)

def save_korean_strings_to_excel(korean_list, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Korean Strings"
    ws.append(["Korean"])
    for kr in korean_list:
        ws.append([kr])
    wb.save(output_path)
    print(f"Done! Output saved to {output_path}")

# ---- GUI ----
def run_gui():
    root = tk.Tk()
    root.title("Extract Korean Strings from XMLs")
    root.geometry("480x200")

    status_label = tk.Label(root, text="Click 'Extract' to begin.", fg="blue")
    status_label.pack(pady=10)

    def on_extract():
        # Step 1: Select XML folder
        xml_folder = filedialog.askdirectory(title="Select XML Folder")
        if not xml_folder:
            return

        # Step 2: Ask for output file
        output_path = filedialog.asksaveasfilename(
            title="Save Output Excel As",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not output_path:
            return

        status_label.config(text="Processing, please wait...", fg="orange")
        root.update_idletasks()
        try:
            korean_list = extract_unique_korean_strings(xml_folder)
            if not korean_list:
                status_label.config(text="No valid Korean strings found.", fg="red")
                messagebox.showinfo("No Data", "No valid Korean strings found.")
                return
            save_korean_strings_to_excel(korean_list, output_path)
            status_label.config(text=f"Done! Output saved to:\n{output_path}", fg="green")
            messagebox.showinfo("Done", f"Output saved to:\n{output_path}")
        except Exception as e:
            status_label.config(text=f"Error: {e}", fg="red")
            messagebox.showerror("Error", str(e))

    btn = tk.Button(root, text="Extract", command=on_extract, width=30, height=3, bg="red", fg="white")
    btn.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    run_gui()