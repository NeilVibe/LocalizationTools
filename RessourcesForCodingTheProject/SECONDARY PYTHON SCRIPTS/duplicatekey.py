import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from collections import defaultdict, Counter

try:
    from lxml import etree as ET
except ImportError:
    import sys
    print("This script requires lxml. Install with: pip install lxml")
    sys.exit(1)

def fix_bad_entities(xml_text):
    # Replace bad & with &amp; except for valid entities
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[DEBUG] Error reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = ET.XMLParser(recover=True)
    try:
        recovered = ET.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except ET.XMLSyntaxError as e:
        print(f"[DEBUG] Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None
    strict_parser = ET.XMLParser(recover=False)
    blob = ET.tostring(recovered, encoding='utf-8')
    try:
        return ET.fromstring(blob, parser=strict_parser)
    except ET.XMLSyntaxError:
        return recovered

def extract_stringids_from_file(file_path):
    root = parse_xml_file(file_path)
    if root is None:
        return []
    sids = []
    for elem in root.iter():
        if 'StringId' in elem.attrib:
            sids.append(elem.attrib['StringId'])
    return sids

def extract_stringids_with_strorigin_from_file(file_path):
    """
    Returns a list of tuples: (StringId, StrOrigin or None)
    """
    root = parse_xml_file(file_path)
    if root is None:
        return []
    sids = []
    for elem in root.iter():
        if 'StringId' in elem.attrib:
            sid = elem.attrib['StringId']
            strorigin = elem.attrib.get('StrOrigin')
            sids.append((sid, strorigin))
    return sids

def scan_folder_for_stringids(folder):
    """
    Returns:
        file_to_stringids: dict of file_path -> list of StringIds (may have duplicates)
        stringid_to_files: dict of StringId -> set of file_paths where it appears
    """
    file_to_stringids = {}
    stringid_to_files = defaultdict(set)
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if not fname.lower().endswith('.xml'):
                continue
            full_path = os.path.join(dirpath, fname)
            sids = extract_stringids_from_file(full_path)
            file_to_stringids[full_path] = sids
            for sid in sids:
                stringid_to_files[sid].add(full_path)
    return file_to_stringids, stringid_to_files

def scan_folder_for_stringids_with_strorigin(folder):
    """
    Returns:
        sid_to_file_strorigin: dict of StringId -> dict of file_path -> set of StrOrigin values
    """
    sid_to_file_strorigin = defaultdict(lambda: defaultdict(set))
    for dirpath, _, filenames in os.walk(folder):
        for fname in filenames:
            if not fname.lower().endswith('.xml'):
                continue
            full_path = os.path.join(dirpath, fname)
            sid_strorigins = extract_stringids_with_strorigin_from_file(full_path)
            for sid, strorigin in sid_strorigins:
                sid_to_file_strorigin[sid][full_path].add(strorigin)
    return sid_to_file_strorigin

def generate_duplicate_report(file_to_stringids, stringid_to_files):
    """
    Returns a string report in the requested format.
    """
    lines = []
    # 1. Duplicates within the same file
    per_file_blocks = []
    for file, sids in sorted(file_to_stringids.items()):
        counter = Counter(sids)
        dups = [sid for sid, count in counter.items() if count > 1]
        if dups:
            block = []
            block.append(os.path.basename(file))
            for sid in sorted(dups):
                block.append(sid)
            per_file_blocks.append('\n'.join(block))
    if per_file_blocks:
        lines.append('\n' + '\n==============\n'.join(per_file_blocks) + '\n')

    # 2. Duplicates across files
    cross_file_blocks = []
    cross_file_dups = [(sid, files) for sid, files in stringid_to_files.items() if len(files) > 1]
    # Group by the set of files
    fileset_to_sids = defaultdict(list)
    for sid, files in cross_file_dups:
        fileset = tuple(sorted(os.path.basename(f) for f in files))
        fileset_to_sids[fileset].append(sid)
    for fileset, sids in sorted(fileset_to_sids.items()):
        block = []
        block.append(' // '.join(fileset))
        for sid in sorted(sids):
            block.append(sid)
        cross_file_blocks.append('\n'.join(block))
    if cross_file_blocks:
        if per_file_blocks:
            lines.append('\n==============\n')
        lines.append('\n==============\n'.join(cross_file_blocks) + '\n')

    if not lines:
        lines.append("No duplicate StringIds found.\n")
    return ''.join(lines)

def generate_strorigin_diff_report(sid_to_file_strorigin):
    """
    Returns a string report for StringIds that appear in multiple files with different StrOrigin values.
    """
    lines = []
    found = False
    for sid, file_strorigins in sorted(sid_to_file_strorigin.items()):
        if len(file_strorigins) < 2:
            continue  # Only interested in StringIds present in multiple files
        # Collect all StrOrigin values across all files for this sid
        all_strorigins = set()
        for strorigins in file_strorigins.values():
            all_strorigins.update(strorigins)
        if len(all_strorigins) > 1:
            found = True
            lines.append(f"StringId: {sid}")
            for file, strorigins in sorted(file_strorigins.items()):
                pretty_file = os.path.basename(file)
                pretty_strorigins = ', '.join(
                    "(missing)" if s is None else f'"{s}"' for s in sorted(strorigins, key=lambda x: x if x is not None else "")
                )
                lines.append(f"  {pretty_file}: {pretty_strorigins}")
            lines.append("==============")
    if not found:
        return "No StringIds with different StrOrigin values found across files.\n"
    return '\n'.join(lines)

def get_script_directory():
    return os.path.dirname(os.path.abspath(__file__))

def auto_save_report(report_text, suffix=""):
    script_dir = get_script_directory()
    base = "duplicate_stringid_report"
    if suffix:
        base += f"_{suffix}"
    report_path = os.path.join(script_dir, f"{base}.txt")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        return report_path
    except Exception as e:
        print(f"[DEBUG] Could not auto-save report: {e}")
        return None

class DuplicateStringIdCheckerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Duplicate StringId Checker")
        self.master.geometry("900x600")

        frm = ttk.Frame(master)
        frm.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(pady=10)

        self.scan_all_btn = ttk.Button(
            btn_frame, text="Scan All Duplicates", command=self.scan_all_duplicates
        )
        self.scan_all_btn.pack(side=tk.LEFT, padx=5)

        self.scan_strorigin_btn = ttk.Button(
            btn_frame, text="Scan Duplicates with Different StrOrigin", command=self.scan_strorigin_duplicates
        )
        self.scan_strorigin_btn.pack(side=tk.LEFT, padx=5)

        self.report_txt = tk.Text(
            frm, height=30, width=120, state=tk.DISABLED,
            font=("Consolas", 11), bg="#222", fg="#fff", wrap=tk.NONE
        )
        self.report_txt.pack(fill=tk.BOTH, expand=True, pady=10)

        yscroll = tk.Scrollbar(frm, command=self.report_txt.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_txt.config(yscrollcommand=yscroll.set)

        self.save_btn = ttk.Button(
            frm, text="Save Report to File", command=self.save_report, state=tk.DISABLED
        )
        self.save_btn.pack(pady=5)

        self.report = ""
        self.auto_report_path = None
        self.report_suffix = ""

    def scan_all_duplicates(self):
        folder = filedialog.askdirectory(title="Select Folder to Scan for Duplicate StringIds")
        if not folder:
            return
        self.report_txt.config(state=tk.NORMAL)
        self.report_txt.delete(1.0, tk.END)
        self.report_txt.insert(tk.END, f"Scanning folder: {folder}\n")
        self.report_txt.config(state=tk.DISABLED)
        self.master.update_idletasks()

        file_to_stringids, stringid_to_files = scan_folder_for_stringids(folder)
        report = generate_duplicate_report(file_to_stringids, stringid_to_files)
        self.report = report
        self.report_suffix = "all"
        self.report_txt.config(state=tk.NORMAL)
        self.report_txt.delete(1.0, tk.END)
        self.report_txt.insert(tk.END, report)
        self.report_txt.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)

        # Auto-save report
        self.auto_report_path = auto_save_report(report, suffix="all")
        if self.auto_report_path:
            messagebox.showinfo(
                "Scan Complete",
                f"Duplicate StringId scan complete.\nSee report below.\n\n"
                f"Report auto-saved to:\n{self.auto_report_path}"
            )
        else:
            messagebox.showinfo(
                "Scan Complete",
                "Duplicate StringId scan complete.\nSee report below."
            )

    def scan_strorigin_duplicates(self):
        folder = filedialog.askdirectory(title="Select Folder to Scan for StringIds with Different StrOrigin")
        if not folder:
            return
        self.report_txt.config(state=tk.NORMAL)
        self.report_txt.delete(1.0, tk.END)
        self.report_txt.insert(tk.END, f"Scanning folder: {folder}\n")
        self.report_txt.config(state=tk.DISABLED)
        self.master.update_idletasks()

        sid_to_file_strorigin = scan_folder_for_stringids_with_strorigin(folder)
        report = generate_strorigin_diff_report(sid_to_file_strorigin)
        self.report = report
        self.report_suffix = "strorigin"
        self.report_txt.config(state=tk.NORMAL)
        self.report_txt.delete(1.0, tk.END)
        self.report_txt.insert(tk.END, report)
        self.report_txt.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)

        # Auto-save report
        self.auto_report_path = auto_save_report(report, suffix="strorigin")
        if self.auto_report_path:
            messagebox.showinfo(
                "Scan Complete",
                f"Scan for StringIds with different StrOrigin complete.\nSee report below.\n\n"
                f"Report auto-saved to:\n{self.auto_report_path}"
            )
        else:
            messagebox.showinfo(
                "Scan Complete",
                "Scan for StringIds with different StrOrigin complete.\nSee report below."
            )

    def save_report(self):
        if not self.report:
            return
        default_name = "duplicate_stringid_report"
        if self.report_suffix:
            default_name += f"_{self.report_suffix}"
        file = filedialog.asksaveasfilename(
            title="Save Report As",
            defaultextension=".txt",
            initialfile=default_name + ".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file:
            return
        try:
            with open(file, "w", encoding="utf-8") as f:
                f.write(self.report)
            messagebox.showinfo("Saved", f"Report saved to:\n{file}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save report:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DuplicateStringIdCheckerApp(root)
    root.mainloop()