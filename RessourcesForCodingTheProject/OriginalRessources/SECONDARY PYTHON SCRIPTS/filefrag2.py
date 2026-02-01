import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

def extract_root_header_footer(lines, element_tag='LocStr'):
    """
    Given the lines of an XML file, extract:
    - header: all lines up to the first <LocStr ...>
    - elements: all <LocStr .../> lines
    - footer: all lines after the last <LocStr .../>
    """
    elem_re = re.compile(rf'^\s*<{element_tag}\b')
    header = []
    elements = []
    footer = []
    in_elements = False
    for line in lines:
        if elem_re.match(line):
            in_elements = True
            elements.append(line)
        elif not in_elements:
            header.append(line)
        else:
            footer.append(line)
    # Remove trailing blank lines from elements (if any)
    while elements and elements[-1].strip() == '':
        elements.pop()
    return header, elements, footer

def write_fragment(path, header, elements, footer):
    with open(path, 'w', encoding='utf-8') as f:
        for line in header:
            f.write(line)
        for line in elements:
            f.write(line)
        for line in footer:
            f.write(line)
        # Ensure exactly two trailing newlines
        f.write('\n' * (2 - sum(1 for _ in re.finditer(r'\n', ''.join(footer)[-2:]))))

def split_xml_file(path, n, element_tag='LocStr'):
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    header, elements, footer = extract_root_header_footer(lines, element_tag)
    total = len(elements)
    if n > total:
        raise ValueError(f"Cannot split {total} elements into {n} fragments.")
    q, r = divmod(total, n)
    slices = []
    start = 0
    for i in range(n):
        end = start + q + (1 if i < r else 0)
        slices.append((start, end))
        start = end
    base_dir = os.path.dirname(path)
    base_name, ext = os.path.splitext(os.path.basename(path))
    out_paths = []
    for idx, (s, e) in enumerate(slices, start=1):
        frag_elements = elements[s:e]
        out = os.path.join(base_dir, f"{base_name}_{idx}{ext}")
        write_fragment(out, header, frag_elements, footer)
        out_paths.append(out)
    return out_paths

def unify_xml_files(reference_path, fragment_paths, element_tag='LocStr'):
    # Use header/footer from reference file
    with open(reference_path, encoding='utf-8') as f:
        ref_lines = f.readlines()
    header, _, footer = extract_root_header_footer(ref_lines, element_tag)
    all_elements = []
    for frag in fragment_paths:
        with open(frag, encoding='utf-8') as f:
            lines = f.readlines()
        _, elements, _ = extract_root_header_footer(lines, element_tag)
        all_elements.extend(elements)
    base_dir = os.path.dirname(reference_path)
    base_name, ext = os.path.splitext(os.path.basename(reference_path))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(base_dir, f"{base_name}_unified_{stamp}{ext}")
    write_fragment(out, header, all_elements, footer)
    return out

# --- GUI ---

class FragmentUnifyWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Fragment / Unify XML File (IDENTICAL FORMAT)")
        self.geometry("800x600")

        self.reference_file = None
        self.header = None
        self.elements = None
        self.footer = None
        self.fragment_files = []

        # Header
        ttk.Label(self, text="STEP 1: Select the reference XML file", font=("Arial", 12, "bold")).pack(pady=5)
        btn_frame = ttk.Frame(self)
        btn_frame.pack()
        ttk.Button(btn_frame, text="Load Reference", command=self.load_reference).pack(side=tk.LEFT, padx=5)
        self.ref_label = ttk.Label(btn_frame, text="No file loaded", font=("Consolas", 10))
        self.ref_label.pack(side=tk.LEFT)

        # Phase container
        self.phase_label = ttk.Label(self, text="CHOOSE: Fragment or Unify?", font=("Arial", 11, "underline"))
        self.phase_label.pack(pady=10)

        choice_frame = ttk.Frame(self)
        choice_frame.pack()
        ttk.Button(choice_frame, text="Fragment", command=self.phase_fragment).pack(side=tk.LEFT, padx=10)
        ttk.Button(choice_frame, text="Unify",   command=self.phase_unify).pack(side=tk.LEFT, padx=10)

        # dynamic body
        self.body = ttk.Frame(self)
        self.body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # status
        self.status = tk.Text(self, height=6, bg="#222", fg="#fff", font=("Consolas",10), state=tk.DISABLED)
        self.status.pack(fill=tk.X, padx=10, pady=5)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.destroy()
        if self.master:
            self.master.destroy()

    def log(self, msg):
        self.status.config(state=tk.NORMAL)
        self.status.insert(tk.END, msg + "\n")
        self.status.see(tk.END)
        self.status.config(state=tk.DISABLED)
        self.update_idletasks()
        print(msg)

    def load_reference(self):
        path = filedialog.askopenfilename(
            title="Select Reference XML File",
            filetypes=[("XML Files","*.xml"),("All","*.*")]
        )
        if not path:
            return
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        header, elements, footer = extract_root_header_footer(lines)
        if not elements:
            messagebox.showerror("Parse Error", f"No <LocStr .../> elements found in {path}")
            return
        self.reference_file = path
        self.header = header
        self.elements = elements
        self.footer = footer
        self.ref_label.config(text=os.path.basename(path))
        self.log(f"[REF] Loaded {path}, {len(elements)} elements found.")

    def phase_fragment(self):
        if not self.elements:
            messagebox.showwarning("No Reference", "Please load a reference file first.")
            return
        for w in self.body.winfo_children(): w.destroy()
        self.phase_label.config(text="PHASE 2: Fragment Reference File")

        f2 = ttk.Frame(self.body); f2.pack(pady=5)
        ttk.Label(f2, text="Number of fragments:", font=("Arial",11)).pack(side=tk.LEFT)
        self.num_frag_var = tk.IntVar(value=2)
        ttk.Entry(f2, textvariable=self.num_frag_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(f2, text="Go Fragment!", command=self.do_fragment).pack(side=tk.LEFT, padx=10)

    def do_fragment(self):
        try:
            n = int(self.num_frag_var.get())
            assert n > 0
        except:
            self.log("[ERROR] Invalid number of fragments.")
            return
        total = len(self.elements)
        if n > total:
            self.log(f"[ERROR] Cannot split {total} elements into {n} fragments.")
            return
        try:
            out_paths = split_xml_file(self.reference_file, n)
            for out in out_paths:
                self.log(f"[FRAGMENT] Wrote {out}")
            if out_paths:
                messagebox.showinfo("Fragment Done", "Process complete!")
        except Exception as ex:
            self.log(f"[ERROR] {ex}")

    def phase_unify(self):
        if not self.reference_file:
            messagebox.showwarning("No Reference", "Please load a reference file first.")
            return
        for w in self.body.winfo_children(): w.destroy()
        self.phase_label.config(text="PHASE 2: Unify Fragments")

        ttk.Button(self.body, text="Select Fragment Files", command=self.upload_fragments).pack(pady=5)
        self.list_frag = tk.Listbox(self.body, height=6, font=("Consolas",10))
        self.list_frag.pack(fill=tk.X, pady=5)
        self.btn_unify = ttk.Button(self.body, text="Unify to Single XML", command=self.do_unify, state=tk.DISABLED)
        self.btn_unify.pack(pady=5)

    def upload_fragments(self):
        files = filedialog.askopenfilenames(
            title="Select Fragments",
            filetypes=[("XML Files","*.xml"),("All","*.*")]
        )
        if not files:
            return
        # sort them by index in filename
        def idx_of(f):
            m = re.search(r"_(\d+)\.xml$", os.path.basename(f), re.IGNORECASE)
            return int(m.group(1)) if m else 9999
        self.fragment_files = sorted(files, key=idx_of)
        self.list_frag.delete(0,tk.END)
        for f in self.fragment_files:
            self.list_frag.insert(tk.END, os.path.basename(f))
        self.log(f"[UNIFY] {len(self.fragment_files)} fragments selected.")
        self.btn_unify.config(state=tk.NORMAL)

    def do_unify(self):
        try:
            out = unify_xml_files(self.reference_file, self.fragment_files)
            self.log(f"[UNIFY] Wrote unified file: {out}")
            messagebox.showinfo("Unify Done", "Process complete!")
        except Exception as ex:
            self.log(f"[ERROR] {ex}")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()   # we only need the Toplevel
    FragmentUnifyWindow(root)
    root.mainloop()