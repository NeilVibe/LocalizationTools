import os
import re
import stat
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lxml import etree

# ---------------- XML Utilities ----------------

def parse_xml_file(file_path: str):
    """
    Read an XML file as text, wrap it in a dummy ROOT element, and return an
    lxml Element after fixing bare '&' characters.  `resolve_entities=False`
    keeps entity references (e.g. &desc;) untouched.
    """
    try:
        # Make sure the file is at least readable
        make_file_writable(file_path)

        with open(file_path, encoding='utf-8') as fh:
            txt = fh.read()
    except Exception as e:
        print(f"[ERROR] Reading {file_path}: {e}")
        return None

    # Escape stray ampersands so the XML stays well-formed
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)

    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        return etree.fromstring(wrapped.encode('utf-8'), parser=parser)
    except Exception as e:
        print(f"[ERROR] Parsing {file_path}: {e}")
        return None


def get_xml_files(path: str):
    """Return a list with a single file or all *.xml files inside a folder."""
    if os.path.isfile(path):
        return [path]

    xml_files = []
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            if f.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, f))
    return xml_files


def make_file_writable(path: str):
    """
    Remove read-only attribute from a file (cross-platform best-effort)
    so that it can be overwritten.  Silently continues on failure.
    """
    try:
        # Fetch current mode and OR with write bits
        current_mode = os.stat(path).st_mode
        os.chmod(path, current_mode | stat.S_IWRITE)
    except Exception:
        pass

# ---------------- Core Functions ----------------

def restore_str_from_strorigin(path: str):
    files = get_xml_files(path)
    changed = 0
    for f in files:
        root = parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in root.iter("LocStr"):
            so = loc.get("StrOrigin")
            if so is not None:
                loc.set("Str", so)
                mod = True

        if mod:
            make_file_writable(f)
            with open(f, "w", encoding="utf-8") as out:
                for child in root:
                    out.write(
                        etree.tostring(child, encoding="utf-8",
                                       pretty_print=True).decode("utf-8")
                    )
            changed += 1
    return changed


def swap_str_with_strorigin(path: str):
    files = get_xml_files(path)
    changed = 0
    for f in files:
        root = parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in root.iter("LocStr"):
            str_val       = loc.get("Str")
            str_origin_val = loc.get("StrOrigin")
            if str_val is not None or str_origin_val is not None:
                loc.set("Str",       str_origin_val if str_origin_val is not None else "")
                loc.set("StrOrigin", str_val        if str_val        is not None else "")
                mod = True

        if mod:
            make_file_writable(f)
            with open(f, "w", encoding="utf-8") as out:
                for child in root:
                    out.write(
                        etree.tostring(child, encoding="utf-8",
                                       pretty_print=True).decode("utf-8")
                    )
            changed += 1
    return changed


def extract_rows(path: str, attr: str, regex: str, is_contained: bool):
    """
    Extract <LocStr> rows whose selected field matches the given regex.

    attr can be:
        • "Str"         → match only Str attribute
        • "StrOrigin"   → match only StrOrigin attribute
        • "StrOrStrOrigin" → match if either Str OR StrOrigin matches

    If `is_contained` is True we keep matches, otherwise we keep non-matches.
    Returns a pretty-printed XML string or None.
    """
    files   = get_xml_files(path)
    matches = []
    pat     = re.compile(regex, re.IGNORECASE)

    for f in files:
        root = parse_xml_file(f)
        if root is None:
            continue

        for loc in root.iter("LocStr"):
            if attr == "StrOrStrOrigin":
                val_str = loc.get("Str") or ""
                val_so  = loc.get("StrOrigin") or ""
                found   = bool(pat.search(val_str) or pat.search(val_so))
            else:
                val   = loc.get(attr) or ""
                found = bool(pat.search(val))

            if (is_contained and found) or (not is_contained and not found):
                matches.append(etree.fromstring(etree.tostring(loc)))

    if not matches:
        return None

    new_root = etree.Element("LocStrs")
    for m in matches:
        new_root.append(m)

    return etree.tostring(new_root, pretty_print=True,
                          encoding="utf-8").decode("utf-8")


def erase_str_matching(path: str, regex: str):
    files   = get_xml_files(path)
    changed = 0
    pat     = re.compile(regex, re.IGNORECASE)

    for f in files:
        root = parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in root.iter("LocStr"):
            val = loc.get("Str")
            if val and pat.search(val):
                loc.set("Str", pat.sub("", val))
                mod = True

        if mod:
            make_file_writable(f)
            with open(f, "w", encoding="utf-8") as out:
                for child in root:
                    out.write(
                        etree.tostring(child, encoding="utf-8",
                                       pretty_print=True).decode("utf-8")
                    )
            changed += 1
    return changed


def modify_str_matching(path: str, search_regex: str, replacement: str) -> int:
    """
    Replace (case-sensitive) every occurrence of *search_regex* with
    *replacement* inside the raw value of each  Str="..."  attribute of every
    .xml file found in *path* (file or folder).  
    The work is done on the **raw XML text** so that entity sequences such as
    “&lt;br/&gt;” are matched literally.

    Returns the number of files that were changed.
    """
    # 1) compile the user-provided pattern first
    try:
        user_pat = re.compile(search_regex)        # case-sensitive
    except re.error as err:
        print(f"[ERROR] Invalid regex: {err}")
        return 0

    # 2) pattern that isolates the Str attribute’s content
    #    group-1  →  attribute head  (e.g.  'Str   ="')
    #    group-2  →  attribute value (without the closing quote)
    attr_pat = re.compile(
        r'(Str\s*=\s*")'            # group-1
        r'((?:[^"\\]|\\.)*)"'       # group-2
        , re.DOTALL)

    changed_files = 0

    for fpath in get_xml_files(path):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                raw_xml = fh.read()
        except Exception as e:
            print(f"[MODIFY] Could not read {fpath}: {e}")
            continue

        file_modified = False

        # callback applied to every Str="...":
        def repl(match: re.Match) -> str:
            nonlocal file_modified
            head  = match.group(1)
            value = match.group(2)
            new_value, n = user_pat.subn(replacement, value)
            if n:
                file_modified = True
            return f'{head}{new_value}"'   # re-append the missing quote

        new_xml = attr_pat.sub(repl, raw_xml)

        if file_modified:
            make_file_writable(fpath)
            try:
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(new_xml)
                changed_files += 1
                print(f"[MODIFY] Updated: {fpath}")
            except Exception as e:
                print(f"[MODIFY] Could not write {fpath}: {e}")
        else:
            print(f"[MODIFY] No change: {fpath}")

    return changed_files


def stack_kr_translation(path: str):
    """
    Append the current Str value below (after) the StrOrigin value separated
    by '<br/>' (literal).  If StrOrigin is empty or missing, StrOrigin is set
    to Str.  Str itself is left untouched.
    """
    files   = get_xml_files(path)
    changed = 0

    for f in files:
        root = parse_xml_file(f)
        if root is None:
            continue

        mod = False
        for loc in root.iter("LocStr"):
            str_val = loc.get("Str")
            if str_val is None:
                continue

            so_val     = loc.get("StrOrigin") or ""
            new_so_val = (so_val + "<br/>" + str_val) if so_val else str_val

            if new_so_val != so_val:
                loc.set("StrOrigin", new_so_val)
                mod = True

        if mod:
            make_file_writable(f)
            with open(f, "w", encoding="utf-8") as out:
                for child in root:
                    out.write(
                        etree.tostring(child, encoding="utf-8",
                                       pretty_print=True).decode("utf-8")
                    )
            changed += 1
    return changed


def replace_strorigin_in_target_by_stringid(source_folder: str,
                                            target_folder: str):
    """
    For every LocStr in TARGET XMLs:
        • Find LocStr in SOURCE XMLs with the same StringId.
        • If found, set TARGET LocStr's StrOrigin to SOURCE LocStr's StrOrigin.
    """
    # Build StringId → StrOrigin map from SOURCE
    stringid_to_strorigin = {}
    for xml_file in get_xml_files(source_folder):
        src_root = parse_xml_file(xml_file)
        if src_root is None:
            continue
        for loc in src_root.iter("LocStr"):
            sid = loc.get("StringId")
            so  = loc.get("StrOrigin")
            if sid and so is not None:
                stringid_to_strorigin[sid] = so

    if not stringid_to_strorigin:
        print("[WARN] No StrOrigin values found in SOURCE folder.")
        return False

    xml_files       = get_xml_files(target_folder)
    changed_files   = 0
    total_locstrs   = 0
    error_files     = 0

    for idx, xml_file in enumerate(xml_files, 1):
        print(f"[Update] {idx}/{len(xml_files)}  {xml_file}")
        tgt_root = parse_xml_file(xml_file)
        if tgt_root is None:
            print(f"[ERROR] Failed to parse: {xml_file}")
            error_files += 1
            continue

        modified = False
        for loc in tgt_root.iter("LocStr"):
            sid = loc.get("StringId")
            if sid is None:
                continue
            new_so = stringid_to_strorigin.get(sid)
            if new_so is not None and loc.get("StrOrigin") != new_so:
                loc.set("StrOrigin", new_so)
                modified = True
                total_locstrs += 1

        if modified:
            make_file_writable(xml_file)
            try:
                if tgt_root.tag == "ROOT":
                    with open(xml_file, "w", encoding="utf-8") as out:
                        for child in tgt_root:
                            out.write(
                                etree.tostring(child, encoding="utf-8",
                                               pretty_print=True).decode("utf-8")
                            )
                else:
                    with open(xml_file, "w", encoding="utf-8") as out:
                        out.write(
                            etree.tostring(tgt_root, encoding="utf-8",
                                           pretty_print=True).decode("utf-8")
                        )
                changed_files += 1
                print("      → Updated")
            except Exception as e:
                print(f"[ERROR] Writing {xml_file}: {e}")
                error_files += 1
        else:
            print("      → No change")

    print("──────── SUMMARY ────────")
    print(f"  Files updated : {changed_files}")
    print(f"  LocStrs edited: {total_locstrs}")
    print(f"  Errors        : {error_files}")
    return changed_files > 0

# ---------------- GUI ----------------

class SimpleXMLTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple XML Tool")
        self.geometry("540x620")
        self.resizable(False, False)

        # UI-control variables
        self.mode            = tk.StringVar(value="folder")
        self.regex_pattern   = tk.StringVar()
        self.is_contained    = tk.BooleanVar(value=True)
        self.extract_field   = tk.StringVar(value="Str")
        self.modify_search   = tk.StringVar()
        self.modify_replace  = tk.StringVar()

        self.create_widgets()

    # ---------- widget construction ----------
    def create_widgets(self):
        frm_mode = tk.LabelFrame(self, text="Mode")
        frm_mode.pack(fill="x", padx=10, pady=5)
        ttk.Radiobutton(frm_mode, text="Folder", variable=self.mode,
                        value="folder").pack(side="left", padx=5)
        ttk.Radiobutton(frm_mode, text="Single File", variable=self.mode,
                        value="file").pack(side="left", padx=5)

        tk.Button(self, text="1. Restore Str from StrOrigin",
                  command=self.do_restore, bg="#e0ffe0")\
            .pack(fill="x", padx=10, pady=5)

        tk.Button(self, text="2. Swap Str with StrOrigin",
                  command=self.do_swap, bg="#fff0b3")\
            .pack(fill="x", padx=10, pady=5)

        # Extract
        frm_extract = tk.LabelFrame(self, text="3. Extract Rows")
        frm_extract.pack(fill="x", padx=10, pady=5)

        tk.Label(frm_extract, text="Regex:").grid(row=0, column=0, sticky="w")
        tk.Entry(frm_extract, textvariable=self.regex_pattern, width=30)\
            .grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(frm_extract, text="is contained",
                        variable=self.is_contained, value=True)\
            .grid(row=0, column=2, padx=5)
        ttk.Radiobutton(frm_extract, text="is NOT contained",
                        variable=self.is_contained, value=False)\
            .grid(row=0, column=3, padx=5)

        tk.Label(frm_extract, text="Field:").grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(frm_extract, text="Str",
                        variable=self.extract_field, value="Str")\
            .grid(row=1, column=1, sticky="w", padx=2)
        ttk.Radiobutton(frm_extract, text="StrOrigin",
                        variable=self.extract_field, value="StrOrigin")\
            .grid(row=1, column=2, sticky="w", padx=2)
        ttk.Radiobutton(frm_extract, text="Str OR StrOrigin",
                        variable=self.extract_field, value="StrOrStrOrigin")\
            .grid(row=1, column=3, sticky="w", padx=2)

        tk.Button(frm_extract, text="Extract", command=self.do_extract,
                  bg="#e0e0ff")\
            .grid(row=2, column=0, columnspan=4, pady=5, sticky="ew")

        # Erase
        tk.Button(self, text="4. Erase Str Matching Regex",
                  command=self.do_erase, bg="#ffe0e0")\
            .pack(fill="x", padx=10, pady=5)

        # Modify
        frm_modify = tk.LabelFrame(self,
                                   text="5. Modify Rows by Str (Regex Replace)")
        frm_modify.pack(fill="x", padx=10, pady=5)

        tk.Label(frm_modify, text="Search Regex:").grid(row=0, column=0,
                                                        sticky="w")
        tk.Entry(frm_modify, textvariable=self.modify_search, width=25)\
            .grid(row=0, column=1, sticky="w")
        tk.Label(frm_modify, text="Replace With:").grid(row=1, column=0,
                                                        sticky="w")
        tk.Entry(frm_modify, textvariable=self.modify_replace, width=25)\
            .grid(row=1, column=1, sticky="w")
        tk.Button(frm_modify, text="Modify", command=self.do_modify,
                  bg="#d0f0ff")\
            .grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")

        # Stack KR / Translation
        tk.Button(self, text="6. Stack KR/Translation",
                  command=self.do_stack, bg="#f0d0ff")\
            .pack(fill="x", padx=10, pady=5)

        # Replace StrOrigin by StringId
        tk.Button(self,
                  text="7. Replace StrOrigin (Source → Target by StringId)",
                  command=self.do_replace_strorigin_by_stringid,
                  bg="#d0ffd0")\
            .pack(fill="x", padx=10, pady=5)

    # ---------- common helpers ----------
    def select_path(self):
        if self.mode.get() == "folder":
            return filedialog.askdirectory(title="Select Folder")
        return filedialog.askopenfilename(title="Select XML File",
                                          filetypes=[("XML Files", "*.xml")])

    # ---------- button callbacks ----------
    def do_restore(self):
        path = self.select_path()
        if not path:
            return
        changed = restore_str_from_strorigin(path)
        messagebox.showinfo("Done", f"Restored in {changed} file(s).")

    def do_swap(self):
        path = self.select_path()
        if not path:
            return
        changed = swap_str_with_strorigin(path)
        messagebox.showinfo("Done",
                            f"Swapped Str and StrOrigin in {changed} file(s).")

    def do_extract(self):
        path = self.select_path()
        if not path:
            return
        regex = self.regex_pattern.get()
        if not regex:
            messagebox.showerror("Error", "Enter a regex pattern.")
            return
        field    = self.extract_field.get()
        xml_str  = extract_rows(path, field, regex, self.is_contained.get())
        if not xml_str:
            messagebox.showinfo("No Matches", "No matching rows found.")
            return
        save_path = filedialog.asksaveasfilename(
            title="Save Extracted XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml")])
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(xml_str)
            messagebox.showinfo("Saved",
                                f"Extracted XML saved to {save_path}")

    def do_erase(self):
        path = self.select_path()
        if not path:
            return
        regex = self.regex_pattern.get()
        if not regex:
            messagebox.showerror("Error", "Enter a regex pattern.")
            return
        changed = erase_str_matching(path, regex)
        messagebox.showinfo("Done", f"Erased matches in {changed} file(s).")

    def do_modify(self):
        path = self.select_path()
        if not path:
            return
        search  = self.modify_search.get()
        replace = self.modify_replace.get()
        if not search:
            messagebox.showerror("Error", "Enter a search regex.")
            return
        changed = modify_str_matching(path, search, replace)
        messagebox.showinfo("Done", f"Modified Str in {changed} file(s).")

    def do_stack(self):
        path = self.select_path()
        if not path:
            return
        changed = stack_kr_translation(path)
        messagebox.showinfo("Done",
                            f"Stacked KR/Translation in {changed} file(s).")

    def do_replace_strorigin_by_stringid(self):
        source_folder = filedialog.askdirectory(
            title="Select SOURCE Folder (reference XMLs)")
        if not source_folder:
            return
        target_folder = filedialog.askdirectory(
            title="Select TARGET Folder (XMLs to update)")
        if not target_folder:
            return
        if not messagebox.askyesno(
            "Confirm",
            "This will OVERWRITE StrOrigin in all XMLs in the TARGET folder\n"
            "based on matching StringId values from the SOURCE folder.\n\n"
            "Continue?"):
            return
        self.config(cursor="wait")
        self.update()
        ok = replace_strorigin_in_target_by_stringid(source_folder,
                                                     target_folder)
        self.config(cursor="")
        if ok:
            messagebox.showinfo("Success",
                                "StrOrigin replaced successfully.\n"
                                "See console for details.")
        else:
            messagebox.showwarning("No Changes",
                                   "No StrOrigin updated (or errors occurred).")

# ---------------- Main ----------------

if __name__ == "__main__":
    app = SimpleXMLTool()
    app.mainloop()