import os
import sys
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from lxml import etree

print("Translation File Manager XML 프로그램 실행 중입니다 잠시만 기다려 주십시오...", flush=True)
print("- Translation File Manager XML LITE ver. 1201 - By Neil")

# XML Utilities
def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[ERROR] Error reading {file_path!r}: {e}")
        return None
    txt = re.sub(r'&(?!lt;|gt;|amp;|apos;|quot;)', '&amp;', txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    rec_parser = etree.XMLParser(recover=True)
    try:
        recovered = etree.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
    except etree.XMLSyntaxError as e:
        print(f"[ERROR] Fatal parse error (recover mode) on {file_path!r}: {e}")
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

def preprocess_text(text):
    text = re.sub(r'<color:.*?>', '', text)
    text = re.sub(r'<PAColor.*?>|<PAOldColor>', '', text)
    return text

def extract_code_patterns(text):
    pattern = r'\{.*?\}'
    return set(re.findall(pattern, text))

def extract_hyperlinks(text):
    pattern = r'@FromHyperlink_ShowItemTooltip\((\d+)\)'
    return re.findall(pattern, text)

def upload_folder(entry):
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
    if hasattr(entry, 'folderpath') and entry.folderpath:
        button_pattern_check.config(state='normal', bg='pale green')
        button_char.config(state='normal', bg='pale green')
    else:
        button_pattern_check.config(state='disabled', bg='grey')
        button_char.config(state='disabled', bg='grey')

def clear_entry(entry):
    entry.config(state='normal')
    entry.delete(0, tk.END)
    entry.config(state='readonly')
    if hasattr(entry, 'folderpath'):
        delattr(entry, 'folderpath')

def clear_entries():
    clear_entry(entry_A)
    button_pattern_check.config(state='disabled', bg='grey')
    button_char.config(state='disabled', bg='grey')

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
        rb_bdm = tk.Radiobutton(dialog, text="BDM 특수 문자 체크 (▶, {, }, 🔗, |)", variable=var_option, value="BDM")
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
                symbols_result['symbols'] = ["▶", "{", "}", "🔗", "|"]
            elif option == "CUSTOM":
                custom_value = custom_entry.get().strip()
                if not custom_value:
                    messagebox.showerror("Error", "사용자 지정 심볼을 입력해 주세요.")
                    return
                symbols_result['symbols'] = list(custom_value)
            dialog.destroy()
        ok_button = tk.Button(dialog, text="확인", command=on_ok)
        ok_button.pack(pady=10)
        dialog.grab_set()
        dialog.wait_window()
        return symbols_result.get('symbols')
    symbols = get_symbol_set()
    if not symbols:
        return
    if not hasattr(entry_A, 'folderpath') or not entry_A.folderpath:
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
                        str_origin_normalized = preprocess_text(str_origin)
                        str_val_normalized = preprocess_text(str_val)
                        for sym in symbols:
                            if str_origin_normalized.count(sym) != str_val_normalized.count(sym):
                                string_id = loc_str.get("StringId", "")
                                line = f"{string_id}\t\t\t\t\t{str_origin}\t{str_val}\t\t\t\n"
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
                messagebox.showinfo("완료", f"선택된 심볼 ({', '.join(symbols)}) 체크 완료!\n{len(discrepancy_lines)}개의 불일치 발견")
        except Exception as e:
            messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")
    thread = threading.Thread(target=process_xml_files)
    thread.daemon = True
    thread.start()

def pattern_sequence_check():
    """
    For all XML files, extract ALL <LocStr> rows where code pattern sets differ,
    and output a single concatenated XML file (no declaration/doctype) with all those rows,
    under a single <root FileName="...">...</root> where FileName is based on the output file name.
    """
    if not hasattr(entry_A, 'folderpath') or not entry_A.folderpath:
        messagebox.showinfo("안내", "XML 폴더를 선택해 주세요.")
        return

    def process_xml_files():
        try:
            xml_files = get_all_xml_files(entry_A.folderpath)
            if not xml_files:
                messagebox.showinfo("안내", "XML 파일이 없습니다.")
                return

            # Ask for output file
            out_path = filedialog.asksaveasfilename(
                title="결과를 저장할 XML 파일을 선택하세요",
                defaultextension=".xml",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
            if not out_path:
                messagebox.showwarning("경고", "저장 파일이 선택되지 않았습니다.")
                return

            # Use the output file name (without path) for FileName attribute
            out_file_name = os.path.basename(out_path)

            total_files = len(xml_files)
            processed = 0
            mismatched_count = 0

            # Create a single root element
            single_root = etree.Element("root", FileName=out_file_name)

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
                        patterns_origin = extract_code_patterns(str_origin)
                        patterns_str = extract_code_patterns(str_val)
                        if patterns_origin != patterns_str:
                            # Deep copy of element
                            single_root.append(etree.Element("LocStr", **loc_str.attrib))
                            mismatched_count += 1

                    processed += 1
                    if processed % 10 == 0:
                        print(f"처리 중: {processed}/{total_files} 파일")
                except Exception as e:
                    print(f"Error processing {xml_file_path}: {e}")
                    continue

            if mismatched_count == 0:
                messagebox.showinfo("문제 없음", "모든 파일에서 패턴 시퀸스가 일치합니다.")
            else:
                # Write the single root to output file, no xml declaration
                xml_str = etree.tostring(single_root, encoding="utf-8", pretty_print=True, xml_declaration=False, doctype=None).decode("utf-8")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(xml_str)
                    f.write("\n")
                messagebox.showinfo("완료", f"{mismatched_count}개의 불일치 항목이 추출되어 저장되었습니다.")

        except Exception as e:
            messagebox.showerror("Error", f"처리 중 오류 발생: {str(e)}")

    thread = threading.Thread(target=process_xml_files)
    thread.daemon = True
    thread.start()

# --- GUI SETUP ---

root = tk.Tk()
root.title("Translation file Manager XML LITE - Version : 1201 (by Neil)")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = 600
window_height = 400
center_x = int(screen_width // 2 - window_width // 2)
center_y = int(screen_height // 2 - window_height // 2)
root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

label_A = tk.Label(root, text="XML 폴더:", font='Helvetica 12 bold')
label_A.grid(row=0, column=0, padx=10, pady=20, sticky="w")

entry_A = tk.Entry(root, width=50, state='readonly')
entry_A.grid(row=0, column=1, padx=10, pady=20, sticky="ew")

button_A = tk.Button(root, text="폴더 선택", command=lambda: upload_folder(entry_A), 
                     font='Helvetica 10 bold', width=12, height=2)
button_A.grid(row=0, column=2, padx=10, pady=20)

button_pattern_check = tk.Button(root, text="패턴 시퀸스 체크", command=pattern_sequence_check, 
                                height=2, width=20, bg='lightblue', fg='black', 
                                font='Helvetica 12 bold', state='disabled')
button_pattern_check.grid(row=1, column=1, padx=10, pady=20, sticky='ew')

button_char = tk.Button(root, text="문자 개수 체크", command=find_character_discrepancies, 
                       height=2, width=20, bg='lightgreen', fg='black', 
                       font='Helvetica 12 bold', state='disabled')
button_char.grid(row=2, column=1, padx=10, pady=20, sticky='ew')

clear_button = tk.Button(root, text="초기화", command=clear_entries, 
                        bg='lightyellow', fg='black', font='Helvetica 10 bold',
                        width=12, height=1)
clear_button.grid(row=3, column=1, padx=10, pady=20)

for i in range(4):
    root.grid_rowconfigure(i, weight=1)
for j in range(3):
    root.grid_columnconfigure(j, weight=1)

print("실행 완료 !")

root.mainloop()