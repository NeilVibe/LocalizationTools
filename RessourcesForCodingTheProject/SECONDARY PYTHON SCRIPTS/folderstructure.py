import os
import shutil
import re
import stat
from lxml import etree
from tkinter import filedialog, messagebox, Tk

# -------------------- Utility Functions --------------------

def make_writable(path):
    """Make file writable."""
    try:
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
    except Exception as e:
        print(f"[ERROR] Could not make writable: {path}: {e}")

def fix_bad_entities(xml_text):
    """Fix invalid XML entities."""
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    """Parse XML file safely."""
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    try:
        rec_parser = etree.XMLParser(recover=True)
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
        strict_parser = etree.XMLParser(recover=False)
        blob = etree.tostring(recovered, encoding='utf-8')
        return etree.fromstring(blob, parser=strict_parser)
    except Exception:
        return None

def extract_strorigin_list(file_path):
    """Extract all StrOrigin values from XML file."""
    root = parse_xml_file(file_path)
    if root is None:
        return []
    vals = []
    for loc in root.iter("LocStr"):
        val = loc.get("StrOrigin")
        if val:
            vals.append(val.strip())
    return vals

def build_strorigin_index(folder):
    """Build index: file_path -> set of StrOrigin values."""
    index = {}
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if fname.lower().endswith(".xml"):
                full = os.path.join(dirpath, fname)
                vals = extract_strorigin_list(full)
                index[full] = set(vals)
    return index

def similarity_ratio(set_a, set_b):
    """Calculate similarity ratio based on intersection/union of StrOrigin sets."""
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    union = len(set_a | set_b)
    return inter / union if union else 0.0

# -------------------- Main Matching Logic --------------------

def find_matches_by_strorigin(source_folder, target_folder, threshold=0.2):
    """Find matching files between source and target based on StrOrigin similarity."""
    print(f"[INFO] Indexing SOURCE folder: {source_folder}")
    src_index = build_strorigin_index(source_folder)
    print(f"[INFO] Indexed {len(src_index)} source files.")

    print(f"[INFO] Indexing TARGET folder: {target_folder}")
    tgt_index = build_strorigin_index(target_folder)
    print(f"[INFO] Indexed {len(tgt_index)} target files.")

    matches = []
    for src_file, src_vals in src_index.items():
        best_ratio = 0.0
        best_tgt = None
        for tgt_file, tgt_vals in tgt_index.items():
            ratio = similarity_ratio(src_vals, tgt_vals)
            if ratio > best_ratio:
                best_ratio = ratio
                best_tgt = tgt_file
        if best_ratio >= threshold and best_tgt:
            matches.append((src_file, best_tgt, best_ratio))
            print(f"[MATCH] {os.path.basename(src_file)} ↔ {os.path.basename(best_tgt)} (ratio={best_ratio:.2f})")
    return matches

def copy_matches_with_structure(matches, target_folder, output_folder):
    """
    Copy matched TARGET files into output folder,
    preserving their folder structure relative to the TARGET folder.
    """
    copied = 0
    for _, tgt_file, ratio in matches:
        rel_path = os.path.relpath(tgt_file, target_folder)
        out_path = os.path.join(output_folder, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        make_writable(out_path)
        shutil.copy2(tgt_file, out_path)  # <-- Copy from TARGET, not SOURCE
        copied += 1
        print(f"[COPY] {tgt_file} → {out_path} (ratio={ratio:.2f})")
    print(f"[INFO] Copied {copied} matched files to {output_folder}")

# -------------------- GUI Selection --------------------

def main():
    root = Tk()
    root.withdraw()

    source_folder = filedialog.askdirectory(title="Select SOURCE Folder (XML data)")
    if not source_folder:
        messagebox.showerror("Error", "No SOURCE folder selected.")
        return

    target_folder = filedialog.askdirectory(title="Select TARGET Folder (XML data)")
    if not target_folder:
        messagebox.showerror("Error", "No TARGET folder selected.")
        return

    output_folder = filedialog.askdirectory(title="Select OUTPUT Folder (where matched files will be copied)")
    if not output_folder:
        messagebox.showerror("Error", "No OUTPUT folder selected.")
        return

    threshold = 0.2  # 20% similarity
    matches = find_matches_by_strorigin(source_folder, target_folder, threshold=threshold)

    if not matches:
        messagebox.showinfo("No Matches", f"No files matched with similarity ≥ {threshold*100:.0f}%")
        return

    copy_matches_with_structure(matches, target_folder, output_folder)
    messagebox.showinfo("Done", f"Copied {len(matches)} matched files to:\n{output_folder}")

if __name__ == "__main__":
    main()