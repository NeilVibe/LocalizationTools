import os
import re
import sys
from lxml import etree
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --------- CONFIG ---------
MAPPING_FILE = "mapping.txt"
ROOT_FOLDER = "xml_folder"
# --------------------------

def parse_mapping_file(mapping_path):
    mapping = {}
    with open(mapping_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=>" not in line:
                continue
            src, dst = line.split("=>", 1)
            src = src.strip()
            dst = dst.strip()
            if src:
                mapping[src] = dst
    return mapping

def get_all_xml_files(folder):
    xml_files = []
    for dirpath, _, filenames in os.walk(folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None
    # escape stray &
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"[ERROR] Fatal parse error on {file_path!r}: {e}")
        return None
    strict_parser = etree.XMLParser(recover=False)
    blob = etree.tostring(recovered, encoding='utf-8')
    try:
        return etree.fromstring(blob, parser=strict_parser)
    except etree.XMLSyntaxError:
        return recovered

def make_file_writable(path):
    try:
        os.chmod(path, 0o666)
    except Exception:
        pass

def replace_str_values_in_file(xml_path, mapping, log_func=None):
    xml_root = parse_xml_file(xml_path)
    if xml_root is None:
        if log_func:
            log_func(f"[ERROR] Could not parse {xml_path}")
        return False

    changed = False
    for loc in xml_root.iter("LocStr"):
        orig = loc.get("Str")
        if orig is None:
            continue
        key = orig.strip()
        if key in mapping:
            new_val = mapping[key]
            if orig != new_val:
                loc.set("Str", new_val)
                changed = True
                if log_func:
                    log_func(f"{os.path.basename(xml_path)}: '{orig}' => '{new_val}'")

    if changed:
        make_file_writable(xml_path)
        try:
            with open(xml_path, "w", encoding="utf-8") as f:
                if xml_root.tag == "ROOT":
                    for child in xml_root:
                        f.write(etree.tostring(child, encoding="utf-8", pretty_print=True).decode("utf-8"))
                else:
                    f.write(etree.tostring(xml_root, encoding="utf-8", pretty_print=True).decode("utf-8"))
            if log_func:
                log_func(f"[OK] Updated: {xml_path}")
        except Exception as e:
            if log_func:
                log_func(f"[ERROR] Could not write {xml_path}: {e}")
            return False

    return changed

class XMLMappingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XML Str Mapping Tool")
        self.geometry("700x480")
        self.resizable(False, False)
        self.mapping_file = tk.StringVar(value=MAPPING_FILE)
        self.folder = tk.StringVar(value=ROOT_FOLDER)
        self.create_widgets()

    def create_widgets(self):
        pad = {'padx': 8, 'pady': 8}
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, **pad)

        ttk.Label(frm, text="Mapping file:").grid(row=0, column=0, sticky='w')
        self.mapping_entry = ttk.Entry(frm, textvariable=self.mapping_file, width=60)
        self.mapping_entry.grid(row=0, column=1, sticky='ew')
        ttk.Button(frm, text="Browse...", command=self.browse_mapping).grid(row=0, column=2, **pad)

        ttk.Label(frm, text="XML folder:").grid(row=1, column=0, sticky='w')
        self.folder_entry = ttk.Entry(frm, textvariable=self.folder, width=60)
        self.folder_entry.grid(row=1, column=1, sticky='ew')
        ttk.Button(frm, text="Browse...", command=self.browse_folder).grid(row=1, column=2, **pad)

        self.run_btn = ttk.Button(frm, text="Run Mapping", command=self.run_mapping)
        self.run_btn.grid(row=2, column=1, sticky='ew', pady=(10, 0))

        ttk.Label(frm, text="Log:").grid(row=3, column=0, sticky='nw', pady=(10, 0))
        self.log_text = tk.Text(frm, width=85, height=18, wrap='word',
                                state='disabled', font=('Consolas', 10))
        self.log_text.grid(row=3, column=1, columnspan=2, sticky='nsew', pady=(10, 0))

        frm.grid_columnconfigure(1, weight=1)
        frm.grid_rowconfigure(3, weight=1)

    def browse_mapping(self):
        path = filedialog.askopenfilename(
            title="Select mapping file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.mapping_file.set(path)

    def browse_folder(self):
        path = filedialog.askdirectory(
            title="Select folder containing XML files"
        )
        if path:
            self.folder.set(path)

    def log(self, msg):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', msg + '\n')
        self.log_text.see('end')
        self.log_text.configure(state='disabled')
        self.update_idletasks()

    def run_mapping(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
        mapping_path = self.mapping_file.get()
        folder = self.folder.get()
        self.run_btn.config(state='disabled')
        try:
            if not os.path.isfile(mapping_path):
                messagebox.showerror("Error", f"Mapping file not found:\n{mapping_path}")
                return
            if not os.path.isdir(folder):
                messagebox.showerror("Error", f"Folder not found:\n{folder}")
                return

            self.log(f"Mapping file: {mapping_path}")
            self.log(f"Target folder: {folder}")
            mapping = parse_mapping_file(mapping_path)
            if not mapping:
                self.log(f"[FATAL] No mappings found in {mapping_path}")
                messagebox.showerror("Error", "No mappings found in mapping file.")
                return

            xml_files = get_all_xml_files(folder)
            self.log(f"Found {len(xml_files)} XML files.")
            changed_files = 0
            for xml_path in xml_files:
                if replace_str_values_in_file(xml_path, mapping, log_func=self.log):
                    changed_files += 1

            self.log(f"Done. Files changed: {changed_files} / {len(xml_files)}")
            messagebox.showinfo("Done", f"Processing complete.\nFiles changed: {changed_files} / {len(xml_files)}")
        finally:
            self.run_btn.config(state='normal')

if __name__ == "__main__":
    app = XMLMappingApp()
    app.mainloop()