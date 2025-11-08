import os
import sys
import threading
from collections import defaultdict
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog

from lxml import etree


def robust_parse_xml(path):
    """
    Parse XML file robustly, ignoring undefined entities and missing attributes.
    Returns (tree, root) or (None, None) if parsing fails.
    """
    try:
        parser = etree.XMLParser(
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            recover=True
        )
        tree = etree.parse(path, parser)
        root = tree.getroot()
        return tree, root
    except Exception as e:
        print(f"[WARN] Cannot parse {path}: {e}")
        return None, None


def index_locstrs(root):
    """
    Index LocStr elements by their Str attribute.
    Returns a dict: {Str: element}
    Only includes entries that have Str and StrOrigin attributes.
    """
    index = {}
    for elem in root.findall('.//LocStr'):
        str_val = elem.get('Str')
        str_origin = elem.get('StrOrigin')
        if str_val is not None and str_origin is not None:
            index[str_val] = elem
    return index


class MatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LocStr Matcher - Source File vs Target Folder(s)")
        self.root.geometry("1000x750")

        self.source_file = None
        self.target_folders = []

        main = tk.Frame(root, padx=16, pady=16)
        main.pack(fill=tk.BOTH, expand=True)

        # Source file selection
        src_frame = tk.LabelFrame(main, text="Source File (single XML)", padx=10, pady=10)
        src_frame.pack(fill=tk.X, pady=(0, 12))

        self.src_path_var = tk.StringVar(value="No source file selected")
        tk.Label(src_frame, textvariable=self.src_path_var, anchor="w").pack(fill=tk.X)
        tk.Button(src_frame, text="Select Source File",
                  command=self.select_source_file, bg="#2196F3", fg="white").pack(pady=(8, 0), anchor="w")

        # Target folders selection
        tgt_frame = tk.LabelFrame(main, text="Target Folders (select parent, then choose multiple subfolders)", padx=10, pady=10)
        tgt_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 12))

        list_container = tk.Frame(tgt_frame)
        list_container.pack(fill=tk.X)

        tgt_scrollbar = tk.Scrollbar(list_container)
        tgt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.target_listbox = tk.Listbox(list_container, height=6, yscrollcommand=tgt_scrollbar.set)
        self.target_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tgt_scrollbar.config(command=self.target_listbox.yview)

        btns = tk.Frame(tgt_frame)
        btns.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btns, text="Select Target Folders (Modal Picker)",
                  command=self.select_target_folders_modal, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btns, text="Clear Targets", command=self.clear_target_folders).pack(side=tk.LEFT, padx=(6, 0))

        # Run and export
        action_frame = tk.Frame(main)
        action_frame.pack(fill=tk.X, pady=(6, 12))

        tk.Button(action_frame, text="Run Match (Source vs All Targets)",
                  command=self.start_match, bg="#4CAF50", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        tk.Button(action_frame, text="Export Matched XML",
                  command=self.start_export, bg="#FF9800", fg="white", font=("Arial", 11)).pack(side=tk.LEFT, padx=8)

        # Progress + status
        prog_frame = tk.Frame(main)
        prog_frame.pack(fill=tk.X, pady=(6, 6))
        self.progress_label = tk.Label(prog_frame, text="Ready")
        self.progress_label.pack(anchor="w")
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill=tk.X)

        # Log output
        tk.Label(main, text="Log:").pack(anchor="w", pady=(8, 4))
        self.output_text = scrolledtext.ScrolledText(main, height=20, width=100)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Result data cache
        self.matched_elements = []  # list of lxml elements (deep copies) to export
        self.last_report = ""

    def select_source_file(self):
        path = filedialog.askopenfilename(
            title="Select SOURCE XML file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if path:
            self.source_file = path
            self.src_path_var.set(path)

    def clear_target_folders(self):
        self.target_folders = []
        self.target_listbox.delete(0, tk.END)

    def select_target_folders_modal(self):
        base = filedialog.askdirectory(title="Select a parent directory that contains target subfolders")
        if not base:
            return

        subdirs = []
        for item in os.listdir(base):
            p = os.path.join(base, item)
            if os.path.isdir(p):
                subdirs.append((item, p))

        if not subdirs:
            messagebox.showwarning("No Folders", "No subdirectories found in the selected directory.")
            return

        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Target Folders (Ctrl+Click for multiple)")
        selection_window.geometry("500x600")
        selection_window.grab_set()

        tk.Label(selection_window, text="Select folders:", font=("Arial", 10, "bold")).pack(pady=10)

        list_frame = tk.Frame(selection_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        folder_map = {}
        for name, path in sorted(subdirs):
            listbox.insert(tk.END, name)
            folder_map[listbox.size() - 1] = path

        def on_confirm():
            selections = listbox.curselection()
            self.target_folders = []
            self.target_listbox.delete(0, tk.END)
            for idx in selections:
                folder_path = folder_map[idx]
                self.target_folders.append(folder_path)
                folder_name = os.path.basename(folder_path)
                self.target_listbox.insert(tk.END, f"{folder_name} - {folder_path}")
            selection_window.destroy()

        def on_select_all():
            listbox.select_set(0, tk.END)

        button_frame = tk.Frame(selection_window)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Select All", command=on_select_all).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Confirm", command=on_confirm, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=selection_window.destroy).pack(side=tk.LEFT, padx=5)

    def start_match(self):
        if not self.source_file:
            messagebox.showerror("Error", "Please select a source XML file.")
            return
        if not self.target_folders:
            messagebox.showerror("Error", "Please select target folders.")
            return

        thread = threading.Thread(target=self.run_match)
        thread.start()

    def run_match(self):
        self.output_text.delete(1.0, tk.END)
        self.matched_elements = []
        self.progress_label.config(text="Parsing source...")
        self.progress['value'] = 0
        self.root.update()

        src_tree, src_root = robust_parse_xml(self.source_file)
        if src_root is None:
            self._log(f"[ERROR] Failed to parse source XML: {self.source_file}")
            self.progress_label.config(text="Failed")
            return

        src_index = index_locstrs(src_root)
        total_targets = 0
        for folder in self.target_folders:
            for r, d, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(".xml"):
                        total_targets += 1

        if total_targets == 0:
            self._log("No XML files found in target folders.")
            self.progress_label.config(text="No targets")
            return

        processed = 0
        match_count = 0
        matched_strs = set()

        self._log(f"Source: {self.source_file}")
        self._log(f"Target roots: {len(self.target_folders)} folder(s)")
        self._log("Scanning targets and matching...")

        for folder in self.target_folders:
            for root_dir, dirs, files in os.walk(folder):
                for file in files:
                    if not file.lower().endswith(".xml"):
                        continue
                    tgt_path = os.path.join(root_dir, file)
                    tgt_tree, tgt_root = robust_parse_xml(tgt_path)
                    processed += 1
                    if tgt_root is None:
                        self._log(f"[WARN] Cannot parse target XML: {tgt_path}")
                    else:
                        tgt_index = index_locstrs(tgt_root)
                        # Instead of exporting source element, export the TARGET element
                        for str_val, src_elem in src_index.items():
                            str_origin = src_elem.get('StrOrigin')
                            if str_val == str_origin:
                                continue
                            if str_val in tgt_index and str_val not in matched_strs:
                                copied = etree.fromstring(etree.tostring(tgt_index[str_val]))
                                self.matched_elements.append(copied)
                                matched_strs.add(str_val)
                                match_count += 1

                    self.progress['value'] = (processed / total_targets) * 100
                    self.progress_label.config(text=f"Processed {processed}/{total_targets} target files")
                    self.root.update()

        self._log(f"Done. Matched unique Str values from TARGETS: {match_count}")
        self.last_report = f"Processed {processed} target XML files. Matched {match_count} unique Str entries."
        self.progress['value'] = 100
        self.progress_label.config(text="Completed")

    def start_export(self):
        if not self.matched_elements:
            messagebox.showerror("No Data", "No matched elements to export. Run Match first.")
            return

        default_name = "output_matched"
        file_name = simpledialog.askstring(
            "Output XML Name",
            "Enter the output XML file name (without .xml):",
            initialvalue=default_name,
            parent=self.root
        )
        if not file_name:
            return

        save_path = filedialog.asksaveasfilename(
            title="Save XML File",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")],
            initialfile=f"{file_name}.xml"
        )
        if not save_path:
            return

        thread = threading.Thread(target=self.export_xml, args=(save_path, file_name))
        thread.start()

    def export_xml(self, save_path, file_name):
        try:
            self.progress_label.config(text="Exporting XML...")
            self.progress['value'] = 0
            self.root.update()

            out_root = etree.Element("root", FileName=f"{file_name}.xml")
            total = len(self.matched_elements)
            for i, elem in enumerate(self.matched_elements, 1):
                out_root.append(etree.fromstring(etree.tostring(elem)))
                if i % 100 == 0 or i == total:
                    self.progress['value'] = (i / total) * 100
                    self.root.update()

            xml_bytes = etree.tostring(out_root, encoding="utf-8", pretty_print=True, xml_declaration=False)
            with open(save_path, "wb") as f:
                f.write(xml_bytes)

            self._log(f"Exported {total} LocStr entries from TARGETS to: {save_path}")
            self.progress['value'] = 100
            self.progress_label.config(text="Export completed")
            messagebox.showinfo("Export Completed", f"Exported {total} LocStr entries to:\n{save_path}")
        except Exception as e:
            self._log(f"[ERROR] Failed to export: {e}")
            self.progress_label.config(text="Export failed")
            messagebox.showerror("Export Failed", str(e))

    def _log(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"[{ts}] {text}\n")
        self.output_text.see(tk.END)
        self.root.update()


def main():
    root = tk.Tk()
    app = MatcherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()