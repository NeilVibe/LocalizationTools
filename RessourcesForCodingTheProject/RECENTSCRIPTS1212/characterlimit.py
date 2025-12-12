#!/usr/bin/env python3
import os
import re
import stat
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from lxml import etree

def make_file_writable(path: str):
    """
    Remove read-only attribute so we can re-open or overwrite the file if needed.
    """
    try:
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IWRITE)
    except Exception:
        pass

def parse_xml_file(file_path: str):
    """
    Read an XML file, escape stray '&' characters, wrap it in a dummy <ROOT>...</ROOT>
    so lxml can recover broken markup, and return the parsed Element.
    """
    try:
        make_file_writable(file_path)
        with open(file_path, encoding='utf-8') as fh:
            txt = fh.read()
    except Exception as e:
        print(f"[ERROR] Reading {file_path}: {e}")
        return None

    # Escape stray ampersands
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"

    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        return etree.fromstring(wrapped.encode('utf-8'), parser=parser)
    except Exception as e:
        print(f"[ERROR] Parsing {file_path}: {e}")
        return None

def main():
    # Hide main Tk window
    root = tk.Tk()
    root.withdraw()

    # 1) Ask the user to select an XML file
    xml_path = filedialog.askopenfilename(
        title="Select XML File to Check",
        filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
    )
    if not xml_path:
        return

    # 2) Ask for the length threshold
    threshold = simpledialog.askinteger(
        "Threshold",
        "Flag <LocStr> nodes whose Str length is ≥:",
        initialvalue=100,
        minvalue=1
    )
    if threshold is None:
        return

    # 3) Parse the chosen XML
    doc = parse_xml_file(xml_path)
    if doc is None:
        messagebox.showerror("Error", f"Failed to parse XML:\n{xml_path}")
        return

    # 4) Find and clone all <LocStr> with Str length ≥ threshold
    flagged = []
    for loc in doc.iter("LocStr"):
        val = loc.get("Str") or ""
        if len(val) >= threshold:
            clone = etree.fromstring(etree.tostring(loc))
            flagged.append(clone)

    # 5) If none found, inform user and exit
    if not flagged:
        messagebox.showinfo("No Flags",
                            f"No <LocStr> nodes with Str length ≥ {threshold}.")
        return

    # 6) Build the report document
    report_root = etree.Element("FlaggedLocStrs")
    for node in flagged:
        report_root.append(node)

    # 7) Determine output path (same folder, with suffix)
    base, _ = os.path.splitext(os.path.basename(xml_path))
    output_name = f"{base}_flagged_report.xml"
    output_path = os.path.join(os.path.dirname(xml_path), output_name)

    # 8) Serialize and write the report
    xml_bytes = etree.tostring(
        report_root,
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
    try:
        with open(output_path, "wb") as out_fh:
            out_fh.write(xml_bytes)
        messagebox.showinfo(
            "Report Saved",
            f"{len(flagged)} nodes flagged.\nReport written to:\n{output_path}"
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write report:\n{e}")

if __name__ == "__main__":
    main()