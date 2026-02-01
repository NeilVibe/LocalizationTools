
#!/usr/bin/env python3
"""
extract_japanese_nodes.py

Standalone script that pops up file dialogs to select an input XML file,
extracts every element whose Str="..." attribute contains Japanese‐specific
characters (Hiragana, Katakana or Japanese punctuation), and writes all those
elements into a new XML file under a single <root> element.
"""

import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from lxml import etree

def contains_japanese(text: str) -> bool:
    """
    Return True if the text contains any Japanese‐specific characters:
    Hiragana, Katakana (fullwidth or halfwidth), Katakana Phonetic Extensions,
    or Japanese punctuation/iteration marks.
    """
    for ch in text:
        code = ord(ch)
        # Hiragana
        if 0x3040 <= code <= 0x309F:
            return True
        # Katakana
        if 0x30A0 <= code <= 0x30FF:
            return True
        # Katakana Phonetic Extensions
        if 0x31F0 <= code <= 0x31FF:
            return True
        # Halfwidth Katakana
        if 0xFF65 <= code <= 0xFF9F:
            return True
    return False

def extract_japanese_nodes(input_path: str, output_path: str) -> int:
    """
    Parse the input XML, find all elements with a Str attribute containing
    Japanese‐specific characters (as per contains_japanese), copy them into a
    new <root> element, and save the result. Returns the number of elements extracted.
    """
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    tree = etree.parse(input_path, parser)
    src_root = tree.getroot()

    out_root = etree.Element("root")
    count = 0

    for elem in src_root.xpath(".//*[@Str]"):
        val = elem.get("Str", "")
        if contains_japanese(val):
            # deep‐copy the element
            copy_elem = etree.fromstring(etree.tostring(elem))
            out_root.append(copy_elem)
            count += 1

    out_tree = etree.ElementTree(out_root)
    out_tree.write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=True
    )
    return count

def main():
    root = tk.Tk()
    root.withdraw()

    input_path = filedialog.askopenfilename(
        title="Select XML file to scan for Japanese",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if not input_path:
        messagebox.showinfo("Cancelled", "No input file selected. Exiting.")
        sys.exit(0)

    default_name = "japanese_extracted.xml"
    default_dir = os.path.dirname(input_path) or os.getcwd()

    output_path = filedialog.asksaveasfilename(
        title="Save extracted nodes as",
        initialdir=default_dir,
        initialfile=default_name,
        defaultextension=".xml",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if not output_path:
        messagebox.showinfo("Cancelled", "No output file selected. Exiting.")
        sys.exit(0)

    try:
        extracted_count = extract_japanese_nodes(input_path, output_path)
        messagebox.showinfo(
            "Done",
            f"Extracted {extracted_count} element(s) containing Japanese text.\n\n"
            f"Saved to:\n{output_path}"
        )
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
