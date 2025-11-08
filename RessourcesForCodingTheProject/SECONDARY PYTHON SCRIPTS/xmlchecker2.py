from __future__ import annotations      # makes all annotations strings (Python 3.7+)
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Set                           #  ← NEW (PEP-484 generics for Py 3.8)
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
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"

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


def extract_hyperlinks(text: str):
    return re.findall(r'@FromHyperlink_ShowItemTooltip\((\d+)\)', text)


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
    entry.folderpath = folderpath          # dynamic attribute – store full path
    entry.delete(0, tk.END)
    entry.insert(0, os.path.basename(folderpath))
    entry.config(state='readonly')

    if getattr(entry, 'folderpath', None):
        button_pattern_check.config(state='normal', bg='pale green')
        button_char.config(state='normal', bg='pale green')
    else:
        button_pattern_check.config(state='disabled', bg='grey')
        button_char.config(state='disabled', bg='grey')


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
        rb_bdo = tk.Radiobutton(dialog, text="BDO 특수 문자 체크 ({, })",
                                variable=var_option, value="BDO")
        rb_bdo.pack(anchor="w", padx=20)

        rb_bdm = tk.Radiobutton(dialog, text="BDM 특수 문자 체크 (▶, {, }, 🔗, |)",
                                variable=var_option, value="BDM")
        rb_bdm.pack(anchor="w", padx=20)

        rb_custom = tk.Radiobutton(dialog, text="사용자 지정 문자",
                                   variable=var_option, value="CUSTOM")
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
                symbols_result['symbols'] = ["▶", "{", "}", "🔗", "|"]
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
        messagebox.showerror("Error", "XML 폴더를 먼저 선택해 주세요.")
        return

    def process_xml_files():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            discrepancy_lines = []
            total_files = len(xml_files)
            processed = 0

            for xml_file_path in xml_files:
                try:
                    xml_root = parse_xml_file(xml_file_path)
                    if xml_root is None:
                        continue

                    for loc_str in xml_root.iter("LocStr"):
                        str_origin = loc_str.get("StrOrigin", "")
                        str_val = loc_str.get("Str", "")
                        if not str_origin or not str_val:
                            continue

                        str_origin_norm = preprocess_text(str_origin)
                        str_val_norm = preprocess_text(str_val)

                        for sym in symbols:
                            if str_origin_norm.count(sym) != str_val_norm.count(sym):
                                string_id = loc_str.get("StringId", "")
                                line = (f"{string_id}\t\t\t\t\t"
                                        f"{str_origin}\t{str_val}\t\t\t\n")
                                discrepancy_lines.append(line)
                                break

                    processed += 1
                    if processed % 10 == 0:
                        print(f"처리 중: {processed}/{total_files} 파일")

                except Exception as e:
                    print(f"Error processing {xml_file_path}: {e}")
                    continue

            if not discrepancy_lines:
                messagebox.showinfo("문제 없음", "모든 심볼의 개수가 일치합니다.")
                return

            path_out = filedialog.asksaveasfilename(defaultextension=".txt")
            if path_out:
                with open(path_out, "w", encoding="utf-8") as file:
                    file.writelines(discrepancy_lines)
                messagebox.showinfo(
                    "완료",
                    f"선택된 심볼 ({', '.join(symbols)}) 체크 완료!\n"
                    f"{len(discrepancy_lines)}개의 불일치 발견"
                )

        except Exception as e:
            messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")

    threading.Thread(target=process_xml_files, daemon=True).start()


# --------------------------------------------------------------------------- #
#                        PATTERN-SEQUENCE  CHECK                              #
# --------------------------------------------------------------------------- #
def pattern_sequence_check():
    """
    For all XML files under the selected folder, compare the *set of {...} code
    patterns* between StrOrigin and Str in every <LocStr>.  The comparison uses
    a special rule for 'Staticinfo:Knowledge:' codes containing '#'.
    Mismatching rows are written to a single XML chosen by the user.
    """
    if not getattr(entry_A, 'folderpath', None):
        messagebox.showinfo("안내", "XML 폴더를 선택해 주세요.")
        return

    # -------------- helper functions ------------------------------------- #
    def normalize_staticinfo_pattern(code: str) -> str:
        """
        If `code` contains 'Staticinfo:Knowledge:' AND a '#', only compare the
        part up to (and including) this '#'.  Everything after '#' is ignored.
        """
        if re.search(r'\{[^{}]*Staticinfo:[^{}]*#', code, re.I):
            before_hash = code.split('#', 1)[0]
            return before_hash + '#}'     # normalise tail
        return code

    def normalise_pattern_set(raw_set: Set[str]) -> Set[str]:  #  ← FIXED
        return {normalize_staticinfo_pattern(t) for t in raw_set}

    # -------------- threaded processing ---------------------------------- #
    def process_xml_files():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            if not xml_files:
                messagebox.showinfo("안내", "XML 파일이 없습니다.")
                return

            out_path = filedialog.asksaveasfilename(
                title="결과를 저장할 XML 파일을 선택하세요",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
            if not out_path:
                messagebox.showwarning("경고", "저장 파일이 선택되지 않았습니다.")
                return

            root_out = etree.Element("root", FileName=os.path.basename(out_path))
            mismatched_count, processed = 0, 0
            total_files = len(xml_files)

            for xml_file_path in xml_files:
                try:
                    xml_root = parse_xml_file(xml_file_path)
                    if xml_root is None:
                        continue

                    for loc_str in xml_root.iter("LocStr"):
                        s1 = loc_str.get("StrOrigin", "")
                        s2 = loc_str.get("Str", "")
                        if not s1 or not s2:
                            continue

                        p1 = normalise_pattern_set(extract_code_patterns(s1))
                        p2 = normalise_pattern_set(extract_code_patterns(s2))

                        if p1 != p2:
                            root_out.append(etree.Element("LocStr", **loc_str.attrib))
                            mismatched_count += 1

                    processed += 1
                    if processed % 10 == 0:
                        print(f"처리 중: {processed}/{total_files} 파일")

                except Exception as e:
                    print(f"Error processing {xml_file_path}: {e}")
                    continue

            if mismatched_count == 0:
                messagebox.showinfo("문제 없음", "모든 파일에서 패턴 시퀸스가 일치합니다.")
                return

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(etree.tostring(root_out,
                                       encoding="utf-8",
                                       pretty_print=True,
                                       xml_declaration=False).decode("utf-8"))
                f.write("\n")
            messagebox.showinfo("완료",
                                f"{mismatched_count}개의 불일치 항목이 추출되어 저장되었습니다.")

        except Exception as e:
            messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")

    threading.Thread(target=process_xml_files, daemon=True).start()


# --------------------------------------------------------------------------- #
#                               GUI  SETUP                                    #
# --------------------------------------------------------------------------- #
root = tk.Tk()
root.title("Translation file Manager XML LITE - Version : 1201 (by Neil)")

w, h = 600, 400
x = (root.winfo_screenwidth() - w) // 2
y = (root.winfo_screenheight() - h) // 2
root.geometry(f"{w}x{h}+{x}+{y}")

label_A = tk.Label(root, text="XML 폴더:", font='Helvetica 12 bold')
label_A.grid(row=0, column=0, padx=10, pady=20, sticky="w")

entry_A = tk.Entry(root, width=50, state='readonly')
entry_A.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

button_A = tk.Button(root, text="폴더 선택",
                     command=lambda: upload_folder(entry_A),
                     font='Helvetica 10 bold', width=12, height=2)
button_A.grid(row=0, column=2, padx=10, pady=20)

button_pattern_check = tk.Button(root, text="패턴 시퀸스 체크",
                                 command=pattern_sequence_check,
                                 height=2, width=20, bg='lightblue', fg='black',
                                 font='Helvetica 12 bold', state='disabled')
button_pattern_check.grid(row=1, column=1, padx=10, pady=20, sticky='ew')

button_char = tk.Button(root, text="문자 개수 체크",
                        command=find_character_discrepancies,
                        height=2, width=20, bg='lightgreen', fg='black',
                        font='Helvetica 12 bold', state='disabled')
button_char.grid(row=2, column=1, padx=10, pady=20, sticky='ew')

clear_button = tk.Button(root, text="초기화", command=clear_entries,
                         bg='lightyellow', fg='black',
                         font='Helvetica 10 bold', width=12, height=1)
clear_button.grid(row=3, column=1, padx=10, pady=20)

for i in range(4):
    root.grid_rowconfigure(i, weight=1)
for j in range(3):
    root.grid_columnconfigure(j, weight=1)

print("실행 완료 !")
root.mainloop()