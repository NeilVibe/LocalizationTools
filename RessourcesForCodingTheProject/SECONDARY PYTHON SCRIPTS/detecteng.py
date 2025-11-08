import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from lxml import etree
import pandas as pd

def parse_xml_file(file_path):
    try:
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        tree = etree.parse(file_path, parser)
        return tree.getroot()
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        try:
            txt = open(file_path, encoding='utf-8').read()
            txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
            wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
            rec_parser = etree.XMLParser(recover=True)
            recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
            return recovered
        except Exception:
            return None

def extract_locstrs(file_path):
    root = parse_xml_file(file_path)
    if root is None:
        return []
    locstrs = []
    for loc in root.xpath('.//LocStr'):
        str_origin = loc.get("StrOrigin", "")
        # Skip if StrOrigin contains an underscore
        if "_" in str_origin:
            continue
        locstrs.append({
            "File": file_path,
            "StringId": loc.get("StringId", ""),
            "StrOrigin": str_origin,
            "Str": loc.get("Str", ""),
            "Element": loc
        })
    return locstrs

def is_latin_char(char):
    if 'A' <= char <= 'Z' or 'a' <= char <= 'z':
        return True
    if ord(char) in range(0x00C0, 0x024F):  # Latin Extended-A and B
        return True
    if ord(char) in range(0x1E00, 0x1EFF):  # Latin Extended Additional
        return True
    return False

def detect_non_latin_characters(text):
    non_latin_chars = []
    for i, char in enumerate(text):
        if not char.isalpha():
            continue
        if not is_latin_char(char):
            script_name = "Unknown"
            if '\u0400' <= char <= '\u04ff':
                script_name = "Cyrillic"
            elif '\u4e00' <= char <= '\u9fff':
                script_name = "Chinese"
            elif '\u3040' <= char <= '\u309f':
                script_name = "Japanese (Hiragana)"
            elif '\u30a0' <= char <= '\u30ff':
                script_name = "Japanese (Katakana)"
            elif '\uac00' <= char <= '\ud7af':
                script_name = "Korean"
            elif '\u0370' <= char <= '\u03ff':
                script_name = "Greek"
            elif '\u0600' <= char <= '\u06ff':
                script_name = "Arabic"
            elif '\u0590' <= char <= '\u05ff':
                script_name = "Hebrew"
            elif '\u0e00' <= char <= '\u0e7f':
                script_name = "Thai"
            elif '\u0900' <= char <= '\u097f':
                script_name = "Devanagari"
            non_latin_chars.append((char, i, script_name))
    return non_latin_chars

def save_flagged_as_xml(flagged_rows, output_path):
    root = etree.Element("root")
    for row in flagged_rows:
        elem = row.get("Element")
        if elem is not None:
            root.append(etree.fromstring(etree.tostring(elem)))
        else:
            fallback = etree.Element("LocStr")
            fallback.set("StringId", row.get("StringId", ""))
            fallback.set("StrOrigin", row.get("StrOrigin", ""))
            fallback.set("Str", row.get("Str", ""))
            root.append(fallback)
    tree = etree.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=False, pretty_print=True)

def main():
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Step 1", "Select the ENGLISH reference XML file.")
    eng_file = filedialog.askopenfilename(title="Select English Reference XML", filetypes=[("XML files", "*.xml")])
    if not eng_file:
        print("No English file selected.")
        return
    messagebox.showinfo("Step 2", "Select the TARGET language XML file.")
    tgt_file = filedialog.askopenfilename(title="Select Target Language XML", filetypes=[("XML files", "*.xml")])
    if not tgt_file:
        print("No target file selected.")
        return

    eng_locstrs = extract_locstrs(eng_file)
    tgt_locstrs = extract_locstrs(tgt_file)
    eng_str_set = set([row["Str"] for row in eng_locstrs if row["Str"].strip()])

    flagged = []
    for row in tgt_locstrs:
        strval = row["Str"]
        strorigin = row["StrOrigin"]
        # Skip if StrOrigin contains an underscore (for target file)
        if "_" in strorigin:
            continue
        # Skip if STR == STROrigin in TARGET file (new condition)
        if strval == strorigin:
            continue
        # --- New logic: If STR matches any English STR, flag it
        if strval in eng_str_set:
            row["FlagReason"] = "STR matches English reference"
            flagged.append(row)
            continue
        # --- Old logic: non-Latin detection
        non_latin = detect_non_latin_characters(strval)
        if non_latin:
            row["FlagReason"] = f"Non-Latin characters: {', '.join([c for c,_,_ in non_latin])}"
            flagged.append(row)

    if not flagged:
        messagebox.showinfo("Result", "No English STR matches or non-Latin issues found!")
        return

    out_path = filedialog.asksaveasfilename(
        title="Save flagged LocStrs as XML",
        defaultextension=".xml",
        filetypes=[("XML files", "*.xml")],
        initialfile="flagged_lang_mismatches.xml"
    )
    if not out_path:
        print("No output file selected.")
        return

    save_flagged_as_xml(flagged, out_path)
    messagebox.showinfo("Done", f"Flagged LocStrs saved to:\n{out_path}")

if __name__ == "__main__":
    main()