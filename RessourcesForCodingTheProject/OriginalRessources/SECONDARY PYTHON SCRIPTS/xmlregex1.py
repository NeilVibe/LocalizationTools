import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from lxml import etree

def fix_bad_entities(xml_text):
    # Ensure only valid XML entities are present
    return re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', xml_text)

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"Error reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None
    strict_parser = etree.XMLParser(recover=False)
    blob = etree.tostring(recovered, encoding='utf-8')
    try:
        return etree.fromstring(blob, parser=strict_parser)
    except etree.XMLSyntaxError:
        return recovered

def get_all_xml_files(input_folder):
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files

def clean_str_parentheses_brackets(text):
    # Remove all (TEXT) and [TEXT], then strip and collapse spaces
    cleaned = re.sub(r'\([^\)]*\)', '', text)
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    return cleaned

def clean_str_asterisks(text):
    # Remove all *TEXT* (asterisk-surrounded), then strip and collapse spaces
    cleaned = re.sub(r'\*[^\*]+\*', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    return cleaned

def replace_newlines_xml(text):
    # Replace \n (literal newline char or backslash-n) with &lt;br/&gt;
    if text is None:
        return text
    # Replace literal newlines
    cleaned = text.replace('\n', '&lt;br/&gt;')
    # Replace escaped newlines
    cleaned = cleaned.replace('\\n', '&lt;br/&gt;')
    return cleaned

def process_xml_file(file_path, mode):
    """
    mode:
        'paren_bracket' - remove (TEXT) and [TEXT] from Str
        'asterisk'      - remove *TEXT* from Str
        'newline'       - replace \n with &lt;br/&gt; in Str and StrOrigin
        'empty_strorigin' - if StrOrigin is empty, set Str to empty as well
    Returns (modified, xml_root)
    """
    xml_root = parse_xml_file(file_path)
    if xml_root is None:
        return False, None
    modified = False
    for loc in xml_root.iter("LocStr"):
        if mode == 'paren_bracket':
            orig = loc.get("Str")
            if orig is not None:
                cleaned = clean_str_parentheses_brackets(orig)
                if cleaned and cleaned != orig:
                    loc.set("Str", cleaned)
                    modified = True
                elif not cleaned:
                    # If result is empty, set Str to "..."
                    loc.set("Str", "...")
                    modified = True
        elif mode == 'asterisk':
            orig = loc.get("Str")
            if orig is not None:
                cleaned = clean_str_asterisks(orig)
                if cleaned and cleaned != orig:
                    loc.set("Str", cleaned)
                    modified = True
                elif not cleaned:
                    # If result is empty, set Str to StrOrigin if available
                    str_origin = loc.get("StrOrigin")
                    if str_origin is not None:
                        loc.set("Str", str_origin)
                        modified = True
                    # If StrOrigin is not available, skip (do not modify)
        elif mode == 'newline':
            orig_str = loc.get("Str")
            orig_strorigin = loc.get("StrOrigin")
            changed = False
            if orig_str is not None:
                cleaned_str = replace_newlines_xml(orig_str)
                if cleaned_str != orig_str:
                    loc.set("Str", cleaned_str)
                    changed = True
            if orig_strorigin is not None:
                cleaned_strorigin = replace_newlines_xml(orig_strorigin)
                if cleaned_strorigin != orig_strorigin:
                    loc.set("StrOrigin", cleaned_strorigin)
                    changed = True
            if changed:
                modified = True
        elif mode == 'empty_strorigin':
            strorigin = loc.get("StrOrigin")
            strval = loc.get("Str")
            # If StrOrigin is None or empty string (including whitespace-only)
            if strorigin is None or strorigin.strip() == "":
                if strval is not None and strval != "":
                    loc.set("Str", "")
                    modified = True
    return modified, xml_root

def write_modified_xml_to_output(xml_root, original_file_path, input_folder, output_folder):
    # Compute relative path
    rel_path = os.path.relpath(original_file_path, input_folder)
    out_file_path = os.path.join(output_folder, rel_path)
    out_dir = os.path.dirname(out_file_path)
    os.makedirs(out_dir, exist_ok=True)
    # Remove the <ROOT> wrapper
    children = list(xml_root)
    xml_bytes = b""
    for child in children:
        xml_bytes += etree.tostring(child, pretty_print=True, encoding='utf-8')
    xml_str = xml_bytes.decode('utf-8')
    with open(out_file_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

def process_folder(folder, mode, gui=None):
    # Output folder in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    output_folder = os.path.join(script_dir, "Regex_Output")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    xml_files = get_all_xml_files(folder)
    total = len(xml_files)
    modified_count = 0
    for idx, file_path in enumerate(xml_files, 1):
        if gui:
            gui.set_status(f"Processing {idx}/{total}: {os.path.basename(file_path)}")
        try:
            modified, xml_root = process_xml_file(file_path, mode)
            if modified:
                write_modified_xml_to_output(xml_root, file_path, folder, output_folder)
                modified_count += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    if gui:
        gui.set_status(f"Done. {modified_count} files modified out of {total}. Output in Regex_Output.")
    else:
        print(f"Done. {modified_count} files modified out of {total}. Output in Regex_Output.")

class RegexXMLCleanerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XML Regex Cleaner")
        self.geometry("600x300")
        self.resizable(False, False)
        self.selected_folder = tk.StringVar()
        self.status_var = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        pad = {'padx': 10, 'pady': 10}
        frm = tk.Frame(self)
        frm.pack(fill="x", **pad)
        btn = tk.Button(frm, text="Select Folder", command=self.select_folder)
        btn.grid(row=0, column=0, sticky="w")
        lbl = tk.Label(frm, textvariable=self.selected_folder, wraplength=500)
        lbl.grid(row=0, column=1, sticky="w", padx=10)
        self.folder_label = lbl

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        tk.Button(
            btn_frame,
            text="Clean (TEXT) and [TEXT] from Str",
            command=self.run_paren_bracket_clean
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        tk.Button(
            btn_frame,
            text="Clean *TEXT* from Str",
            command=self.run_asterisk_clean
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Button(
            btn_frame,
            text="Replace \\n with &lt;br/&gt; in Str and StrOrigin",
            command=self.run_newline_replace
        ).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        tk.Button(
            btn_frame,
            text="Set Str to empty if StrOrigin is empty",
            command=self.run_empty_strorigin_clean
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        status_lbl = tk.Label(self, textvariable=self.status_var, fg="blue", anchor="w")
        status_lbl.pack(fill="x", padx=10, pady=10)

    def select_folder(self):
        fld = filedialog.askdirectory(
            title="Select Folder Containing XML Files"
        )
        if fld:
            self.selected_folder.set(fld)
            self.folder_label.config(text=fld)

    def set_status(self, msg):
        self.status_var.set(msg)
        self.update_idletasks()

    def run_paren_bracket_clean(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        self.set_status("Cleaning (TEXT) and [TEXT] from Str...")
        threading.Thread(
            target=process_folder,
            args=(folder, 'paren_bracket', self),
            daemon=True
        ).start()

    def run_asterisk_clean(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        self.set_status("Cleaning *TEXT* from Str...")
        threading.Thread(
            target=process_folder,
            args=(folder, 'asterisk', self),
            daemon=True
        ).start()

    def run_newline_replace(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        self.set_status("Replacing \\n with &lt;br/&gt; in Str and StrOrigin...")
        threading.Thread(
            target=process_folder,
            args=(folder, 'newline', self),
            daemon=True
        ).start()

    def run_empty_strorigin_clean(self):
        folder = self.selected_folder.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        self.set_status("Setting Str to empty if StrOrigin is empty...")
        threading.Thread(
            target=process_folder,
            args=(folder, 'empty_strorigin', self),
            daemon=True
        ).start()

def main():
    app = RegexXMLCleanerGUI()
    app.mainloop()

if __name__ == "__main__":
    main()