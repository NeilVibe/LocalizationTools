
from _future_ import annotations      # makes all annotations strings (Python 3.7+)
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Set
from lxml import etree

# --------------------------------------------------------------------------- #
#                              XML  UTILITIES                                 #
# --------------------------------------------------------------------------- #
def parse_xml_file(file_path: str):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None

    # escape stray amps
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
    wrapped = "<ROOT>
" + txt + "
</ROOT>"

    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"[ERROR] Fatal parse error (recover mode) on {file_path!r}: {e}")
        return None

    # run again in strict mode
    strict_parser = etree.XMLParser(recover=False)
    blob = etree.tostring(recovered, encoding='utf-8')
    try:
        return etree.fromstring(blob, parser=strict_parser)
    except etree.XMLSyntaxError:
        # if strict failed, fall back to recovered
        return recovered


def get_all_xml_files(input_folder: str):
    xml_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for file in filenames:
            if file.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, file))
    return xml_files


def preprocess_text(text: str) -> str:
    text = re.sub(r'<color:.*?>', '', text)
    text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
    return text


def extract_code_patterns(text: str):
    # “{...}” blocks
    return set(re.findall(r'\{.*?\}', text))


# --------------------------------------------------------------------------- #
#                              GUI ACTIONS                                    #
# --------------------------------------------------------------------------- #
def upload_folder(entry: tk.Entry):
    entry.config(state='normal')
    folderpath = filedialog.askdirectory(title="Select XML Folder")
    if not folderpath:
        messagebox.showwarning("Warning", "폴더가 선택되지 않았습니다.")
        entry.config(state='readonly')
        return
    entry.folderpath = folderpath
    entry.delete(0, tk.END)
    entry.insert(0, os.path.basename(folderpath))
    entry.config(state='readonly')

    if getattr(entry, 'folderpath', None):
        button_pattern_check.config(state='normal', bg='pale green')
        button_char.config(state='normal', bg='pale green')
        button_malformed.config(state='normal', bg='pale green')
    else:
        button_pattern_check.config(state='disabled', bg='grey')
        button_char.config(state='disabled', bg='grey')
        button_malformed.config(state='disabled', bg='grey')


def clear_entry(entry: tk.Entry):
    entry.config(state='normal')
    entry.delete(0, tk.END)
    entry.config(state='readonly')
    if hasattr(entry, 'folderpath'):
        delattr(entry, 'folderpath')


def clear_entries():
    clear_entry(entry_A)
    button_pattern_check.config(state='disabled', bg='grey')
    button_char.config(state='disabled', bg='grey')
    button_malformed.config(state='disabled', bg='grey')


# --------------------------------------------------------------------------- #
#                       MALFORMED CODE CHECK                                  #
# --------------------------------------------------------------------------- #
def check_malformed_patterns():
    """
    Checks the 'Str' attribute for mismatched curly braces { and }.
    Saves results to a new XML file.
    """
    if not getattr(entry_A, 'folderpath', None):
        messagebox.showinfo("안내", "XML 폴더를 선택해 주세요.")
        return

    def is_malformed(text: str) -> bool:
        if not text:
            return False
        balance = 0
        for char in text:
            if char == '{':
                balance += 1
            elif char == '}':
                balance -= 1
            if balance < 0:  # Closing brace before opening brace
                return True
        return balance != 0  # Unclosed brace if balance > 0

    def process():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            if not xml_files:
                return

            out_path = filedialog.asksaveasfilename(
                title="결과를 저장할 XML 파일을 선택하세요",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml")]
            )
            if not out_path:
                return

            root_out = etree.Element("root", FileName=os.path.basename(out_path))
            malformed_count = 0
            
            for xml_file_path in xml_files:
                xml_root = parse_xml_file(xml_file_path)
                if xml_root is None:
                    continue

                for loc_str in xml_root.iter("LocStr"):
                    str_val = loc_str.get("Str", "")
                    if is_malformed(str_val):
                        node = etree.Element("LocStr", loc_str.attrib)
                        root_out.append(node)
                        malformed_count += 1

            if malformed_count == 0:
                messagebox.showinfo("완료", "손상된 코드가 발견되지 않았습니다.")
                return

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(etree.tostring(root_out, encoding="utf-8", pretty_print=True).decode("utf-8"))
            
            messagebox.showinfo("완료", f"{malformed_count}개의 손상된 항목을 찾았습니다.")

        except Exception as e:
            messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")

    threading.Thread(target=process, daemon=True).start()


# --------------------------------------------------------------------------- #
#                       CHARACTER-COUNT DISCREPANCY                           #
# --------------------------------------------------------------------------- #
def find_character_discrepancies():
    def get_symbol_set():
        dialog = tk.Toplevel(root)
        dialog.title("특수 문자 체크 옵션 선택")
        dialog.geometry("350x200")
        var_option = tk.StringVar(value="BDO")
        symbols_result = {}

        tk.Label(dialog, text="어떤 심볼을 체크할까요?").pack(padx=10, pady=10)
        rb_bdo = tk.Radiobutton(dialog, text="BDO 특수 문자 체크 ({, })", variable=var_option, value="BDO")
        rb_bdo.pack(anchor="w", padx=20)
        rb_bdm = tk.Radiobutton(dialog, text="BDM 특수 문자 체크 (▶, {, }, :link:, |)", variable=var_option, value="BDM")
        rb_bdm.pack(anchor="w", padx=20)
        rb_custom = tk.Radiobutton(dialog, text="사용자 지정 문자", variable=var_option, value="CUSTOM")
        rb_custom.pack(anchor="w", padx=20)

        custom_entry = tk.Entry(dialog, state="disabled")
        custom_entry.pack(padx=20, pady=5, fill="x")

        def on_option_change(*args):
            if var_option.get() == "CUSTOM":
                custom_entry.config(state="normal")
            else:
                custom_entry.delete(0, tk.END)
                custom_entry.config(state="disabled")

        var_option.trace("w", on_option_change)

        def on_ok():
            option = var_option.get()
            if option == "BDO":
                symbols_result['symbols'] = ["{", "}"]
            elif option == "BDM":
                symbols_result['symbols'] = ["▶", "{", "}", ":link:", "|"]
            elif option == "CUSTOM":
                custom_value = custom_entry.get().strip()
                if not custom_value:
                    messagebox.showerror("Error", "사용자 지정 심볼을 입력해 주세요.")
                    return
                symbols_result['symbols'] = list(custom_value)
            dialog.destroy()

        tk.Button(dialog, text="확인", command=on_ok).pack(pady=10)
        dialog.grab_set()
        dialog.wait_window()
        return symbols_result.get('symbols')

    symbols = get_symbol_set()
    if not symbols:
        return
    if not getattr(entry_A, 'folderpath', None):
        return

    def process_xml_files():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            discrepancy_lines = []
            for xml_file_path in xml_files:
                xml_root = parse_xml_file(xml_file_path)
                if xml_root is None: continue
                for loc_str in xml_root.iter("LocStr"):
                    s_orig = preprocess_text(loc_str.get("StrOrigin", ""))
                    s_str = preprocess_text(loc_str.get("Str", ""))
                    for sym in symbols:
                        if s_orig.count(sym) != s_str.count(sym):
                            discrepancy_lines.append(f"{loc_str.get('StringId')}\t{loc_str.get('StrOrigin')}\t{loc_str.get('Str')}
")
                            break
            
            if not discrepancy_lines:
                messagebox.showinfo("문제 없음", "모든 심볼의 개수가 일치합니다.")
                return

            path_out = filedialog.asksaveasfilename(defaultextension=".txt")
            if path_out:
                with open(path_out, "w", encoding="utf-8") as f:
                    f.writelines(discrepancy_lines)
                messagebox.showinfo("완료", "체크 완료!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    threading.Thread(target=process_xml_files, daemon=True).start()


# --------------------------------------------------------------------------- #
#                        PATTERN-SEQUENCE  CHECK                              #
# --------------------------------------------------------------------------- #
def pattern_sequence_check():
    if not getattr(entry_A, 'folderpath', None):
        return

    def normalize_staticinfo_pattern(code: str) -> str:
        if re.search(r'\{[^{}]Staticinfo:[^{}]#', code, re.I):
            return code.split('#', 1)[0] + '#}'
        return code

    def normalise_pattern_set(raw_set: Set[str]) -> Set[str]:
        return {normalize_staticinfo_pattern(t) for t in raw_set}

    def process_xml_files():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            out_path = filedialog.asksaveasfilename(defaultextension=".xml")
            if not out_path: return

            root_out = etree.Element("root")
            mismatched_count = 0
            for xml_file_path in xml_files:
                xml_root = parse_xml_file(xml_file_path)
                if xml_root is None: continue
                for loc_str in xml_root.iter("LocStr"):
                    p1 = normalise_pattern_set(extract_code_patterns(loc_str.get("StrOrigin", "")))
                    p2 = normalise_pattern_set(extract_code_patterns(loc_str.get("Str", "")))
                    if p1 != p2:
                        root_out.append(etree.Element("LocStr", loc_str.attrib))
                        mismatched_count += 1

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(etree.tostring(root_out, encoding="utf-8", pretty_print=True).decode("utf-8"))
            messagebox.showinfo("완료", f"{mismatched_count}개 불일치 발견.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    threading.Thread(target=process_xml_files, daemon=True).start()


# --------------------------------------------------------------------------- #
#                               GUI  SETUP                                    #
# --------------------------------------------------------------------------- #
root = tk.Tk()
root.title("Translation file Manager XML LITE - Version : 1201 (by Neil)")
w, h = 650, 450
x = (root.winfo_screenwidth() - w) // 2
y = (root.winfo_screenheight() - h) // 2
root.geometry(f"{w}x{h}+{x}+{y}")

label_A = tk.Label(root, text="XML 폴더:", font='Helvetica 12 bold')
label_A.grid(row=0, column=0, padx=10, pady=20, sticky="w")

entry_A = tk.Entry(root, width=50, state='readonly')
entry_A.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

button_A = tk.Button(root, text="폴더 선택", command=lambda: upload_folder(entry_A), font='Helvetica 10 bold', width=12)
button_A.grid(row=0, column=2, padx=10, pady=20)

button_pattern_check = tk.Button(root, text="패턴 시퀸스 체크", command=pattern_sequence_check, height=2, bg='grey', font='Helvetica 11 bold', state='disabled')
button_pattern_check.grid(row=1, column=1, padx=10, pady=10, sticky='ew')

button_char = tk.Button(root, text="문자 개수 체크", command=find_character_discrepancies, height=2, bg='grey', font='Helvetica 11 bold', state='disabled')
button_char.grid(row=2, column=1, padx=10, pady=10, sticky='ew')

button_malformed = tk.Button(root, text="코드 구조 손상 체크 (Str)", command=check_malformed_patterns, height=2, bg='grey', font='Helvetica 11 bold', state='disabled')
button_malformed.grid(row=3, column=1, padx=10, pady=10, sticky='ew')

clear_button = tk.Button(root, text="초기화", command=clear_entries, bg='lightyellow', font='Helvetica 10 bold')
clear_button.grid(row=4, column=1, padx=10, pady=10)

for i in range(5): root.grid_rowconfigure(i, weight=1)
for j in range(3): root.grid_columnconfigure(j, weight=1)

root.mainloop()