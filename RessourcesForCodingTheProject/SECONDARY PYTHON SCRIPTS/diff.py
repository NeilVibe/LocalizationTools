import os
import shutil
import re
from lxml import etree as ET
from collections import defaultdict
from tkinter import Tk, filedialog, messagebox, Button, Label
import sys

def fix_bad_entities(xml_text):
    return re.sub(
        r'&(?!lt;|gt;|amp;|apos;|quot;)',
        '&amp;', xml_text
    )

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = ET.XMLParser(recover=True)
    try:
        recovered = ET.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except ET.XMLSyntaxError as e:
        print(f"[ERROR] Parse error (recover mode) on {file_path!r}: {e}")
        return None
    return recovered

def index_folder(folder):
    files_index = {}
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if not fname.lower().endswith('.xml'):
                continue
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, folder)
            root = parse_xml_file(full_path)
            if root is None:
                continue
            rows = []
            for elem in root.iter():
                attrib = dict(elem.attrib)
                if 'StringId' in attrib:
                    rows.append({
                        'StringId': attrib.get('StringId', ''),
                        'attrib': attrib
                    })
            files_index[rel_path] = rows
    return files_index

def build_stringid_set(rows):
    return set(row['StringId'] for row in rows if row['StringId'])

def diff_rows(src_rows, tgt_rows):
    tgt_stringids = build_stringid_set(tgt_rows)
    diff = []
    for row in src_rows:
        sid = row['StringId']
        if sid and sid not in tgt_stringids:
            diff.append(row)
    return diff

def copy_file_with_dirs(src_root, rel_path, dst_root):
    src_path = os.path.join(src_root, rel_path)
    dst_path = os.path.join(dst_root, rel_path)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.copy2(src_path, dst_path)

def extract_diff_files():
    print("Select SOURCE folder (contains XML files to compare and extract from)...")
    Tk().withdraw()
    src_folder = filedialog.askdirectory(title="Select SOURCE folder")
    if not src_folder:
        print("No source folder selected.")
        return
    print("Select TARGET folder (to compare against)...")
    tgt_folder = filedialog.askdirectory(title="Select TARGET folder")
    if not tgt_folder:
        print("No target folder selected.")
        return
    print("Select OUTPUT folder (where to copy differing files)...")
    out_folder = filedialog.askdirectory(title="Select OUTPUT folder")
    if not out_folder:
        print("No output folder selected.")
        return

    print(f"Indexing SOURCE: {src_folder}")
    src_index = index_folder(src_folder)
    print(f"Indexing TARGET: {tgt_folder}")
    tgt_index = index_folder(tgt_folder)

    files_to_extract = []
    for rel_path, src_rows in src_index.items():
        tgt_rows = tgt_index.get(rel_path, [])
        diff = diff_rows(src_rows, tgt_rows)
        if diff:
            files_to_extract.append(rel_path)
            print(f"[DIFF] {rel_path}: {len(diff)} new StringId(s)")

    print(f"\nFound {len(files_to_extract)} files in SOURCE with new StringId(s) vs TARGET.")
    if not files_to_extract:
        messagebox.showinfo("Done", "No differing files found. Nothing to extract.")
        return

    for rel_path in files_to_extract:
        copy_file_with_dirs(src_folder, rel_path, out_folder)
        print(f"Copied: {rel_path}")

    messagebox.showinfo(
        "Extraction Complete",
        f"Extracted {len(files_to_extract)} files to:\n{out_folder}"
    )
    print(f"\nExtraction complete. Files copied to: {out_folder}")

def get_stringid_elements(root):
    """
    Returns a dict: StringId -> element (deepcopy, to avoid parent references)
    """
    from copy import deepcopy
    result = {}
    for elem in root.iter():
        if 'StringId' in elem.attrib:
            sid = elem.attrib['StringId']
            result[sid] = deepcopy(elem)
    return result

def compare_two_xml_files():
    Tk().withdraw()
    file1 = filedialog.askopenfilename(title="Select FIRST XML file to compare", filetypes=[("XML files", "*.xml")])
    if not file1:
        return
    file2 = filedialog.askopenfilename(title="Select SECOND XML file to compare", filetypes=[("XML files", "*.xml")])
    if not file2:
        return
    out_file = filedialog.asksaveasfilename(title="Save DIFF XML as...", defaultextension=".xml", filetypes=[("XML files", "*.xml")])
    if not out_file:
        return

    root1 = parse_xml_file(file1)
    root2 = parse_xml_file(file2)
    if root1 is None or root2 is None:
        messagebox.showerror("Error", "Failed to parse one or both XML files.")
        return

    elems1 = get_stringid_elements(root1)
    elems2 = get_stringid_elements(root2)

    all_ids = set(elems1.keys()) | set(elems2.keys())

    diff_root = ET.Element("XMLDiffReport")
    diff_root.attrib['File1'] = file1
    diff_root.attrib['File2'] = file2

    for sid in sorted(all_ids):
        in1 = sid in elems1
        in2 = sid in elems2
        if in1 and not in2:
            removed = ET.Element("Removed")
            removed.append(elems1[sid])
            diff_root.append(removed)
        elif in2 and not in1:
            added = ET.Element("Added")
            added.append(elems2[sid])
            diff_root.append(added)
        elif in1 and in2:
            # Compare attributes and text
            attribs1 = elems1[sid].attrib
            attribs2 = elems2[sid].attrib
            text1 = (elems1[sid].text or '').strip()
            text2 = (elems2[sid].text or '').strip()
            if attribs1 != attribs2 or text1 != text2:
                modified = ET.Element("Modified")
                old = ET.Element("Old")
                old.append(elems1[sid])
                new = ET.Element("New")
                new.append(elems2[sid])
                modified.append(old)
                modified.append(new)
                diff_root.append(modified)

    if len(diff_root) == 0:
        diff_root.append(ET.Comment("No differences found."))

    try:
        tree = ET.ElementTree(diff_root)
        tree.write(out_file, encoding="utf-8", xml_declaration=True, pretty_print=True)
        messagebox.showinfo("Diff Complete", f"XML diff written to:\n{out_file}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to write diff XML:\n{e}")

def launch_gui():
    root = Tk()
    root.title("XML Diff Tool")

    Label(root, text="XML Diff Tool", font=("Arial", 16, "bold")).pack(pady=10)

    Button(
        root, text="Extract Diff Files (Folder Mode)",
        command=extract_diff_files, width=40, height=2
    ).pack(pady=10)

    Button(
        root, text="Compare Two XML Files (Diff Report)",
        command=compare_two_xml_files, width=40, height=2
    ).pack(pady=10)

    Label(root, text="").pack(pady=5)
    Button(root, text="Exit", command=root.destroy, width=20).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    launch_gui()