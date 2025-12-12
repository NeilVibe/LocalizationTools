#!/usr/bin/env python3
"""
MemoQ Unconfirmed Eraser
========================
Removes unconfirmed translations from LanguageData by cross-referencing with MemoQ export.

Process:
1. User exports files from MemoQ with unconfirmed strings EMPTIED (Str="")
2. User places those files in a SOURCE FOLDER
3. Script extracts all empty Str="" nodes from SOURCE
4. Script matches nodes in TARGET LanguageData by Stringid + StrOrigin
5. Matching nodes get Str replaced with StrOrigin (translation erased)

Author: LocaNext Tools
Date: 2025-12-12
"""

import os
import re
import stat
import html
import tkinter as tk
from tkinter import filedialog, messagebox
from lxml import etree
import time

# =====================================================================
# GLOBALS
# =====================================================================
source_folder_path = None
target_file_path = None
status_label = None
info_panel = None
btn_source = None
btn_target = None
btn_run = None

# =====================================================================
# CORE FUNCTIONS
# =====================================================================

def normalize_text(txt):
    """
    Ensures consistent text normalization for matching:
    1. Unescape HTML entities (&lt; → <, &amp; → &, etc.)
    2. Strip leading/trailing whitespace
    3. Collapse all internal whitespace (spaces, tabs, newlines) to single space

    This guarantees MemoQ export and LanguageData text are IDENTICAL for matching.
    """
    if not txt:
        return ""
    # Unescape HTML entities
    txt = html.unescape(str(txt))
    # Collapse all whitespace to single space and strip
    txt = re.sub(r'\s+', ' ', txt.strip())
    return txt


def unlock_readonly(path):
    """Remove read-only attribute from file."""
    try:
        current_mode = os.stat(path).st_mode
        os.chmod(path, current_mode | stat.S_IWRITE | stat.S_IWGRP | stat.S_IWOTH)
        print(f"[UNLOCK] Removed read-only from: {path}")
        return True
    except Exception as e:
        print(f"[WARN] Could not unlock {path}: {e}")
        return False


def get_all_xml_files(folder):
    """Recursively get all XML files in folder."""
    files = []
    for dirpath, _, filenames in os.walk(folder):
        for fn in filenames:
            if fn.lower().endswith(".xml"):
                files.append(os.path.join(dirpath, fn))
    return files


def robust_parse_xml(path):
    """Parse XML file with recovery mode."""
    try:
        parser = etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            recover=True
        )
        tree = etree.parse(path, parser)
        return tree, tree.getroot()
    except Exception as e:
        print(f"[ERROR] Cannot parse {path}: {e}")
        return None, None


def extract_empty_nodes_from_source(source_folder):
    """
    Walk source folder, find all XML files, extract nodes where Str="" is empty.
    Returns dict: {(stringid, strorigin): True}
    """
    empty_nodes = {}
    xml_files = get_all_xml_files(source_folder)

    if not xml_files:
        print("[WARN] No XML files found in source folder!")
        return empty_nodes, []

    print(f"\n[SOURCE] Found {len(xml_files)} XML files in source folder")

    file_stats = []

    for xml_path in xml_files:
        tree, root = robust_parse_xml(xml_path)
        if tree is None:
            continue

        count = 0
        # Try different tag names (LocStr, String, etc.)
        for tag in ["LocStr", "String", "string", "locstr"]:
            for node in root.iter(tag):
                # Get attributes (case-insensitive search)
                stringid = None
                strorigin = None
                str_val = None

                for attr_name in node.attrib:
                    lower_attr = attr_name.lower()
                    if lower_attr == "stringid":
                        stringid = node.get(attr_name, "").strip()
                    elif lower_attr == "strorigin":
                        strorigin = node.get(attr_name, "").strip()
                    elif lower_attr == "str":
                        str_val = node.get(attr_name, "")

                # Check if Str is empty (unconfirmed in MemoQ)
                if stringid and strorigin and str_val == "":
                    # CRITICAL: Normalize for consistent matching
                    key = (normalize_text(stringid), normalize_text(strorigin))
                    if key not in empty_nodes:
                        empty_nodes[key] = True
                        count += 1

        if count > 0:
            file_stats.append((os.path.basename(xml_path), count))
            print(f"  - {os.path.basename(xml_path)}: {count} empty nodes")

    print(f"[SOURCE] Total unique empty nodes to process: {len(empty_nodes)}")
    return empty_nodes, file_stats


def process_target_languagedata(target_path, empty_nodes):
    """
    Process target LanguageData XML:
    - Find matching nodes (Stringid + StrOrigin)
    - Replace Str with StrOrigin
    - Save file
    """
    # Unlock read-only if needed
    unlock_readonly(target_path)

    # Parse target file
    tree, root = robust_parse_xml(target_path)
    if tree is None:
        return None, None, None

    # Count total nodes
    total_nodes = 0
    matches_found = 0
    not_found_keys = []

    # Build a map of target nodes for faster lookup
    target_map = {}  # {(stringid, strorigin): node}

    for tag in ["LocStr", "String", "string", "locstr"]:
        for node in root.iter(tag):
            stringid = None
            strorigin = None
            str_attr_name = None
            strorigin_attr_name = None

            for attr_name in node.attrib:
                lower_attr = attr_name.lower()
                if lower_attr == "stringid":
                    stringid = node.get(attr_name, "").strip()
                elif lower_attr == "strorigin":
                    strorigin = node.get(attr_name, "").strip()
                    strorigin_attr_name = attr_name
                elif lower_attr == "str":
                    str_attr_name = attr_name

            if stringid and strorigin:
                total_nodes += 1
                # CRITICAL: Normalize for consistent matching
                key = (normalize_text(stringid), normalize_text(strorigin))
                target_map[key] = (node, str_attr_name, strorigin_attr_name, strorigin)

    print(f"\n[TARGET] Total nodes in target: {total_nodes}")
    print(f"[TARGET] Searching for matches...")

    # Process matches
    processed = 0
    for key in empty_nodes:
        processed += 1
        if processed % 50 == 0 or processed == len(empty_nodes):
            pct = 100 * processed / len(empty_nodes)
            print(f"  [{processed}/{len(empty_nodes)}] {pct:.1f}%", end='\r')

        if key in target_map:
            node, str_attr, strorigin_attr, strorigin_value = target_map[key]
            if str_attr:
                # Replace Str with StrOrigin (erase translation)
                node.set(str_attr, strorigin_value)
                matches_found += 1
        else:
            not_found_keys.append(key)

    print()  # New line after progress

    # Save modified file
    if matches_found > 0:
        # Preserve original encoding and formatting
        tree.write(
            target_path,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True
        )
        print(f"[TARGET] File updated successfully!")

    return matches_found, len(not_found_keys), not_found_keys


# =====================================================================
# MAIN PROCESS
# =====================================================================

def run_process():
    """Main process execution."""
    global source_folder_path, target_file_path, status_label

    if not source_folder_path:
        messagebox.showerror("Error", "Please select a SOURCE folder first.")
        return

    if not target_file_path:
        messagebox.showerror("Error", "Please select a TARGET file first.")
        return

    status_label.config(text="Processing...")

    print("\n" + "="*60)
    print("  MemoQ Unconfirmed Eraser")
    print("="*60)
    print(f"\nSource Folder: {source_folder_path}")
    print(f"Target File: {target_file_path}")

    t0 = time.time()

    # Step 1: Extract empty nodes from source
    status_label.config(text="Scanning source folder...")
    empty_nodes, file_stats = extract_empty_nodes_from_source(source_folder_path)

    if not empty_nodes:
        status_label.config(text="No empty nodes found in source!")
        messagebox.showwarning("Warning", "No empty nodes (Str=\"\") found in source folder.\n\nMake sure the MemoQ export has Str=\"\" for unconfirmed strings.")
        return

    # Step 2: Process target LanguageData
    status_label.config(text="Processing target LanguageData...")
    matches, not_found_count, not_found_keys = process_target_languagedata(target_file_path, empty_nodes)

    if matches is None:
        status_label.config(text="Failed to parse target file!")
        messagebox.showerror("Error", "Failed to parse target LanguageData file.")
        return

    elapsed = time.time() - t0

    # Results
    print("\n" + "="*60)
    print("  RESULTS")
    print("="*60)
    print(f"  Total empty nodes from source: {len(empty_nodes)}")
    print(f"  Matches found and erased: {matches}")
    print(f"  Not found in target: {not_found_count}")
    print(f"  Time: {elapsed:.1f}s")
    print("="*60)

    if not_found_count > 0 and not_found_count <= 20:
        print("\n  Not found keys:")
        for key in not_found_keys[:20]:
            print(f"    - {key[0]} | {key[1][:50]}...")

    status_label.config(text=f"Done! Erased: {matches} | Not found: {not_found_count}")

    messagebox.showinfo(
        "Process Complete",
        f"Source files scanned: {len(file_stats)}\n"
        f"Empty nodes found: {len(empty_nodes)}\n"
        f"─────────────────────\n"
        f"Matches erased: {matches}\n"
        f"Not found in target: {not_found_count}\n"
        f"─────────────────────\n"
        f"Time: {elapsed:.1f}s\n\n"
        f"Target file has been updated!"
    )


# =====================================================================
# GUI CALLBACKS
# =====================================================================

def select_source_folder():
    """Select source folder containing MemoQ exported XMLs."""
    global source_folder_path
    folder = filedialog.askdirectory(title="Select SOURCE Folder (MemoQ Exports)")
    if folder:
        source_folder_path = folder
        btn_source.config(bg="#90EE90")  # Light green
        update_info_panel()
        update_run_button()
        status_label.config(text="Source folder selected.")

        # Quick scan
        xml_files = get_all_xml_files(folder)
        print(f"[INFO] Source folder contains {len(xml_files)} XML files")


def select_target_file():
    """Select target LanguageData XML file."""
    global target_file_path
    file = filedialog.askopenfilename(
        title="Select TARGET LanguageData XML",
        filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
    )
    if file:
        target_file_path = file
        btn_target.config(bg="#90EE90")  # Light green
        update_info_panel()
        update_run_button()
        status_label.config(text="Target file selected.")


def update_run_button():
    """Enable run button when both inputs are selected."""
    if source_folder_path and target_file_path:
        btn_run.config(state="normal", bg="#FF6B6B")  # Coral red
    else:
        btn_run.config(state="disabled", bg="grey")


def update_info_panel():
    """Update info panel with current selections."""
    info_panel.config(state="normal")
    info_panel.delete(1.0, tk.END)
    info_panel.insert(tk.END, "Current Selections:\n")
    info_panel.insert(tk.END, "─" * 50 + "\n")
    info_panel.insert(tk.END, f"SOURCE: {source_folder_path or '[Not selected]'}\n")
    info_panel.insert(tk.END, f"TARGET: {target_file_path or '[Not selected]'}\n")
    info_panel.config(state="disabled")


# =====================================================================
# MAIN GUI
# =====================================================================

def main():
    global btn_source, btn_target, btn_run, status_label, info_panel

    root = tk.Tk()
    root.title("MemoQ Unconfirmed Eraser")
    root.geometry("650x500")
    root.resizable(True, True)

    # Title
    title_frame = tk.Frame(root, pady=15)
    title_frame.pack(fill="x")
    tk.Label(
        title_frame,
        text="MemoQ Unconfirmed Eraser",
        font=("Helvetica", 16, "bold")
    ).pack()
    tk.Label(
        title_frame,
        text="Remove unconfirmed translations from LanguageData",
        font=("Helvetica", 10),
        fg="gray"
    ).pack()

    # Instructions
    instr_frame = tk.Frame(root, padx=20, pady=10)
    instr_frame.pack(fill="x")
    tk.Label(
        instr_frame,
        text="Instructions:\n"
             "1. In MemoQ, EMPTY all unconfirmed strings (set Str=\"\")\n"
             "2. Export those files and place in a folder\n"
             "3. Select that folder as SOURCE\n"
             "4. Select the LanguageData XML as TARGET\n"
             "5. Click RUN - matching translations will be erased",
        justify="left",
        font=("Helvetica", 9),
        fg="#555"
    ).pack(anchor="w")

    # Buttons
    btn_frame = tk.Frame(root, pady=20)
    btn_frame.pack()

    btn_source = tk.Button(
        btn_frame,
        text="Select SOURCE Folder\n(MemoQ Export with empty Str)",
        command=select_source_folder,
        width=35,
        height=3,
        bg="#E0E0E0"
    )
    btn_source.pack(pady=8)

    btn_target = tk.Button(
        btn_frame,
        text="Select TARGET File\n(LanguageData XML to modify)",
        command=select_target_file,
        width=35,
        height=3,
        bg="#E0E0E0"
    )
    btn_target.pack(pady=8)

    btn_run = tk.Button(
        btn_frame,
        text="RUN PROCESS\n(Erase unconfirmed translations)",
        command=run_process,
        width=35,
        height=3,
        bg="grey",
        fg="white",
        font=("Helvetica", 10, "bold"),
        state="disabled"
    )
    btn_run.pack(pady=15)

    # Status
    status_label = tk.Label(
        root,
        text="Select source folder and target file to begin.",
        fg="blue",
        font=("Helvetica", 10)
    )
    status_label.pack(pady=10)

    # Info panel
    info_frame = tk.Frame(root, padx=20)
    info_frame.pack(fill="both", expand=True, pady=10)

    info_panel = tk.Text(
        info_frame,
        height=5,
        wrap="none",
        state="disabled",
        bg="#F5F5F5",
        font=("Consolas", 9)
    )
    info_panel.pack(fill="both", expand=True)

    update_info_panel()

    # Footer
    tk.Label(
        root,
        text="Check console for detailed progress",
        font=("Helvetica", 8),
        fg="gray"
    ).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()
