
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
import re
import sys
import os

def extract_ids_from_text(text):
    """
    Extract ANYTHING between parentheses, excluding (U+xxxx) unicode notes.
    Keeps order and removes duplicates.
    """
    # Match anything between parentheses except those starting with U+
    raw_ids = re.findall(r'\((?!U\+)[^)]+\)', text)
    cleaned_ids = [rid.strip("()") for rid in raw_ids]
    seen = set()
    ordered = []
    for sid in cleaned_ids:
        if sid not in seen:
            seen.add(sid)
            ordered.append(sid)
    return ordered

def load_text_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def parse_languagedata_xml(path):
    """
    Parse XML and build a mapping from StringId -> list of LocStr elements.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    id_map = {}
    for loc in root.findall('.//LocStr'):
        sid = loc.get('StringId')
        if sid:
            id_map.setdefault(sid, []).append(loc)
    return id_map

def build_output_root(id_list, id_map):
    """
    Build a new XML root containing cloned LocStr elements for each ID in order.
    """
    out_root = ET.Element('root')
    for sid in id_list:
        for elem in id_map.get(sid, []):
            xml_bytes = ET.tostring(elem, encoding='utf-8')
            new_elem = ET.fromstring(xml_bytes)
            out_root.append(new_elem)
    return out_root

def indent(elem, level=0):
    """
    Pretty-print indentation for XML output.
    """
    i = "\n" + level*"    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        for child in elem:
            indent(child, level+1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def main():
    root = tk.Tk()
    root.withdraw()

    # 1) Select the text file
    txt_path = filedialog.askopenfilename(
        title="Select the text file with your IDs in parentheses",
        filetypes=[("Text files","*.txt"),("All files","*.*")]
    )
    if not txt_path:
        messagebox.showerror("Error","No text file selected.")
        sys.exit(1)

    # 2) Select the languagedata XML
    xml_path = filedialog.askopenfilename(
        title="Select the languagedata XML file",
        filetypes=[("XML files","*.xml"),("All files","*.*")]
    )
    if not xml_path:
        messagebox.showerror("Error","No languagedata XML selected.")
        sys.exit(1)

    # 3) Choose where to save the result
    default_name = os.path.splitext(os.path.basename(txt_path))[0] + "_extracted.xml"
    out_path = filedialog.asksaveasfilename(
        title="Save output XML as",
        defaultextension=".xml",
        initialfile=default_name,
        filetypes=[("XML files","*.xml"),("All files","*.*")]
    )
    if not out_path:
        messagebox.showerror("Error","No output file specified.")
        sys.exit(1)

    # Extract IDs from text
    content = load_text_file(txt_path)
    id_list = extract_ids_from_text(content)
    if not id_list:
        messagebox.showwarning("Warning","No IDs found in the text file.")

    # Parse the languagedata XML and index by StringId
    id_map = parse_languagedata_xml(xml_path)

    # Warn about missing IDs
    missing = [sid for sid in id_list if sid not in id_map]
    if missing:
        msg = f"{len(missing)} IDs not found in XML:\n" + ", ".join(missing[:10])
        if len(missing) > 10:
            msg += f"\n... and {len(missing)-10} more"
        messagebox.showwarning("Warning", msg)

    # Build output tree
    out_root = build_output_root(id_list, id_map)
    indent(out_root)
    tree = ET.ElementTree(out_root)
    tree.write(out_path, encoding='utf-8', xml_declaration=False)

    total = sum(len(id_map.get(sid,())) for sid in id_list)
    messagebox.showinfo("Done", f"Extracted {total} <LocStr> elements →\n{out_path}")

if __name__ == "__main__":
    main()