import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from lxml import etree

# ---------------- XML Utilities ----------------

def fix_bad_entities(xml_text):
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        messagebox.showerror("Error", f"Error reading XML file:\n{e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    try:
        return etree.fromstring(wrapped.encode('utf-8'), parser=etree.XMLParser(recover=True))
    except Exception as e:
        messagebox.showerror("Error", f"Error parsing XML file:\n{e}")
        return None

def extract_stringids_from_xml(file_path):
    root = parse_xml_file(file_path)
    if root is None:
        return set()
    sids = set()
    for elem in root.iter():
        if 'StringId' in elem.attrib:
            sids.add(elem.attrib['StringId'])
    return sids

# ---------------- Excel Utilities ----------------

def read_third_column_values(excel_path):
    try:
        df = pd.read_excel(excel_path, header=None)
    except Exception as e:
        messagebox.showerror("Error", f"Error reading Excel file:\n{e}")
        return set()
    if df.shape[1] < 3:
        messagebox.showerror("Error", "Excel file has less than 3 columns.")
        return set()
    col_values = df.iloc[:, 2].dropna().astype(str).str.strip()
    return set(col_values)

# ---------------- Matching Utilities ----------------

def find_partial_matches(excel_ids, xml_ids):
    """Return dict of excel_id -> matching_xml_ids for partial matches."""
    partial_matches = {}
    for eid in excel_ids:
        if eid in xml_ids:
            continue  # exact match already handled
        matches = [xid for xid in xml_ids if eid in xid]
        if matches:
            partial_matches[eid] = matches
    return partial_matches

# ---------------- GUI App ----------------

class StringIdCheckerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Excel vs XML StringId Checker (Exact + Partial)")
        self.geometry("900x650")

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(frm)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Select Excel File", command=self.select_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Select XML File", command=self.select_xml).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Check StringIds", command=self.check_stringids).pack(side=tk.LEFT, padx=5)

        self.report_txt = tk.Text(frm, wrap=tk.NONE, font=("Consolas", 10), bg="#222", fg="#fff")
        self.report_txt.pack(fill=tk.BOTH, expand=True, pady=5)

        yscroll = tk.Scrollbar(frm, command=self.report_txt.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_txt.config(yscrollcommand=yscroll.set)

        self.excel_path = None
        self.xml_path = None

    def select_excel(self):
        path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx;*.xls")])
        if path:
            self.excel_path = path
            messagebox.showinfo("Excel Selected", f"Excel file selected:\n{path}")

    def select_xml(self):
        path = filedialog.askopenfilename(title="Select XML File", filetypes=[("XML Files", "*.xml")])
        if path:
            self.xml_path = path
            messagebox.showinfo("XML Selected", f"XML file selected:\n{path}")

    def check_stringids(self):
        if not self.excel_path or not self.xml_path:
            messagebox.showerror("Error", "Please select both Excel and XML files first.")
            return

        excel_ids = read_third_column_values(self.excel_path)
        xml_ids = extract_stringids_from_xml(self.xml_path)

        missing_exact = sorted(excel_ids - xml_ids)
        extra = sorted(xml_ids - excel_ids)

        # Check partial matches for missing ones
        partial_matches = find_partial_matches(missing_exact, xml_ids)
        matched_partially = set(partial_matches.keys())
        still_missing = sorted(set(missing_exact) - matched_partially)

        report_lines = []
        report_lines.append(f"Excel file: {os.path.basename(self.excel_path)}")
        report_lines.append(f"XML file: {os.path.basename(self.xml_path)}")
        report_lines.append(f"Total IDs in Excel (3rd col): {len(excel_ids)}")
        report_lines.append(f"Total IDs in XML: {len(xml_ids)}")
        report_lines.append("")

        if not still_missing and not matched_partially:
            report_lines.append("✅ All Excel StringIds are present in XML.")
        else:
            if still_missing:
                report_lines.append(f"❌ Missing in XML ({len(still_missing)}):")
                report_lines.extend(still_missing)
                report_lines.append("")
            if matched_partially:
                report_lines.append(f"🔍 Partial Matches ({len(matched_partially)}):")
                for eid, matches in partial_matches.items():
                    report_lines.append(f"{eid}  -->  {', '.join(matches)}")
                report_lines.append("")

        if extra:
            report_lines.append(f"⚠ Extra in XML not in Excel ({len(extra)}):")
            report_lines.extend(extra)

        self.report_txt.config(state=tk.NORMAL)
        self.report_txt.delete(1.0, tk.END)
        self.report_txt.insert(tk.END, "\n".join(report_lines))
        self.report_txt.config(state=tk.DISABLED)

# ---------------- Main ----------------

if __name__ == "__main__":
    app = StringIdCheckerApp()
    app.mainloop()