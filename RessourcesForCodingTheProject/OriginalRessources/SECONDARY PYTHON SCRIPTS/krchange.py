import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import xml.etree.ElementTree as ET

def get_relative_path_with_parents(full_path, base_folder):
    # Returns last 2 parent folders + filename, relative to base_folder
    rel_path = os.path.relpath(full_path, base_folder)
    parts = rel_path.split(os.sep)
    if len(parts) >= 3:
        return os.path.join(parts[-3], parts[-2], parts[-1])
    elif len(parts) == 2:
        return os.path.join(parts[-2], parts[-1])
    else:
        return parts[-1]

def collect_stringid_to_strorigin(folder):
    """
    Recursively walks folder, parses XML files, and returns:
    {
        StringId: [
            (StrOrigin, full_path)
        ]
    }
    and also a mapping of file to its rows:
    {
        full_path: {
            StringId: StrOrigin
        }
    }
    """
    stringid_map = {}
    file_rows = {}
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith('.xml'):
                full_path = os.path.join(root, file)
                try:
                    tree = ET.parse(full_path)
                    xml_root = tree.getroot()
                    rows = {}
                    for locstr in xml_root.findall('.//LocStr'):
                        stringid = locstr.get('StringId', '').strip()
                        strorigin = locstr.get('StrOrigin', '').strip()
                        if stringid:
                            rows[stringid] = strorigin
                            if stringid not in stringid_map:
                                stringid_map[stringid] = []
                            stringid_map[stringid].append((strorigin, full_path))
                    file_rows[full_path] = rows
                except Exception as e:
                    # Could log error if needed
                    pass
    return stringid_map, file_rows

def compare_source_target(source_folder, target_folder):
    # Build maps for both folders
    source_stringid_map, source_file_rows = collect_stringid_to_strorigin(source_folder)
    target_stringid_map, target_file_rows = collect_stringid_to_strorigin(target_folder)

    # For each StringId in target, check if it exists in source
    report_lines = []
    for target_file, target_rows in target_file_rows.items():
        for stringid, target_strorigin in target_rows.items():
            # Is this StringId in source?
            found = False
            for source_strorigin, source_file in source_stringid_map.get(stringid, []):
                if source_strorigin != target_strorigin:
                    # Output as requested
                    report_lines.append("SOURCE FILE: " + get_relative_path_with_parents(source_file, source_folder))
                    report_lines.append(f"{stringid} // {source_strorigin}")
                    report_lines.append("TARGET FILE: " + get_relative_path_with_parents(target_file, target_folder))
                    report_lines.append(f"{stringid} // {target_strorigin}")
                    report_lines.append("-" * 60)
                    found = True
            # If not found, skip (we only care about same StringId, different StrOrigin)
    if not report_lines:
        report_lines.append("No StringId found in both Source and Target with different StrOrigin.")
    return "\n".join(report_lines)

class CompareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("StringId/StrOrigin XML Compare")
        self.root.geometry("900x700")

        self.source_folder = None
        self.target_folder = None

        # GUI Layout
        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Source
        src_frame = tk.Frame(frame)
        src_frame.pack(fill=tk.X, pady=5)
        tk.Label(src_frame, text="Source Folder:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.src_label = tk.Label(src_frame, text="(not selected)", fg="gray")
        self.src_label.pack(side=tk.LEFT, padx=10)
        tk.Button(src_frame, text="Select Source Folder", command=self.select_source, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=10)

        # Target
        tgt_frame = tk.Frame(frame)
        tgt_frame.pack(fill=tk.X, pady=5)
        tk.Label(tgt_frame, text="Target Folder:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.tgt_label = tk.Label(tgt_frame, text="(not selected)", fg="gray")
        self.tgt_label.pack(side=tk.LEFT, padx=10)
        tk.Button(tgt_frame, text="Select Target Folder", command=self.select_target, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=10)

        # Compare button
        tk.Button(frame, text="Compare", command=self.run_compare, bg="#4CAF50", fg="white", font=("Arial", 12), pady=8).pack(pady=20)

        # Output
        tk.Label(frame, text="Report Output:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(frame, height=25, width=120, font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=10)

    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_folder = folder
            self.src_label.config(text=folder, fg="black")

    def select_target(self):
        folder = filedialog.askdirectory(title="Select Target Folder")
        if folder:
            self.target_folder = folder
            self.tgt_label.config(text=folder, fg="black")

    def run_compare(self):
        if not self.source_folder or not self.target_folder:
            messagebox.showerror("Error", "Please select both Source and Target folders.")
            return
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, "Comparing, please wait...\n")
        self.root.update()
        report = compare_source_target(self.source_folder, self.target_folder)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, report)

def main():
    root = tk.Tk()
    app = CompareApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()