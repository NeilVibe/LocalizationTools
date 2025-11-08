import tkinter as tk
from tkinter import filedialog, messagebox
import os

def trim_columns(path_in):
    columns_to_keep = list(range(9))
    trimmed_lines = []
    with open(path_in, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            columns = line.rstrip('\n').split('\t')
            if len(columns) < 9:
                columns += [''] * (9 - len(columns))
            new_line = '\t'.join([columns[i] for i in columns_to_keep]) + '\n'
            trimmed_lines.append(new_line)
    return trimmed_lines

class TermListGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("글로소리 자동 추출 ver. 1224 (By Neil)")
        self.root.geometry("600x400")
        
        self.source_file = tk.StringVar()
        self.target_file = tk.StringVar()
        self.exclude_file = tk.StringVar()
        
        self.default_color = "#f0f0f0"
        self.success_color = "#90EE90"
        self.process_button_color = "#FF6B6B"  # Red for full mode
        self.partial_mode_color = "#9370DB"    # Purple for partial mode
        
        self.button_font = ('Arial', 10, 'bold')
        self.process_button_font = ('Arial', 12, 'bold')
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.reset_button = tk.Button(main_frame,
                                text="모두 초기화",
                                command=self.reset_all,
                                width=15,
                                height=1,
                                font=self.button_font)
        self.reset_button.pack(anchor='ne')
        
        self.source_button = tk.Button(main_frame, 
                                     text="렝귀지 데이터 파일 선택", 
                                     command=self.select_source_file, 
                                     width=30,
                                     height=2,
                                     font=self.button_font)
        self.source_button.pack(pady=10)
        
        self.exclude_button = tk.Button(main_frame, 
                                      text="스트링 제거 파일 선택", 
                                      command=self.select_exclude_file, 
                                      width=30,
                                      height=2,
                                      font=self.button_font)
        self.exclude_button.pack(pady=10)
        
        self.target_button = tk.Button(main_frame, 
                                     text="클로즈 파일 선택", 
                                     command=self.select_target_file, 
                                     width=30,
                                     height=2,
                                     font=self.button_font)
        self.target_button.pack(pady=10)
        
        self.process_button = tk.Button(main_frame, 
                                      text="추출 진행", 
                                      command=self.process_files,
                                      width=40,
                                      height=3,
                                      state=tk.DISABLED,
                                      bg=self.default_color,
                                      font=self.process_button_font)
        self.process_button.pack(pady=30)

    def reset_all(self):
        self.source_file.set("")
        self.target_file.set("")
        self.exclude_file.set("")
        
        self.source_button.config(
            text="렝귀지 데이터 파일 선택",
            bg=self.default_color
        )
        self.exclude_button.config(
            text="스트링 제거 파일 선택",
            bg=self.default_color
        )
        self.target_button.config(
            text="클로즈 파일 선택",
            bg=self.default_color
        )
        
        self.process_button.config(
            state=tk.DISABLED,
            bg=self.default_color
        )
        
    def select_source_file(self):
        filename = filedialog.askopenfilename(title="렝귀지 데이터 파일 선택", 
                                            filetypes=[("Text Files", "*.txt")])
        if filename:
            self.source_file.set(filename)
            self.source_button.config(text="렝귀지 데이터 파일 - 업로드 완료", 
                                   bg=self.success_color)
            self.check_files()
            
    def select_target_file(self):
        filename = filedialog.askopenfilename(title="클로즈 파일 선택", 
                                            filetypes=[("Text Files", "*.txt")])
        if filename:
            self.target_file.set(filename)
            self.target_button.config(text="클로즈 파일 - 업로드 완료", 
                                   bg=self.success_color)
            self.check_files()
            
    def select_exclude_file(self):
        filename = filedialog.askopenfilename(title="스트링 제거 파일 선택", 
                                            filetypes=[("Text Files", "*.txt")])
        if filename:
            self.exclude_file.set(filename)
            self.exclude_button.config(text="스트링 제거 파일 - 업로드 완료", 
                                    bg=self.success_color)
            self.check_files()
            
    def check_files(self):
        if self.source_file.get() and self.target_file.get() and self.exclude_file.get():
            self.process_button.config(
                state=tk.NORMAL, 
                bg=self.process_button_color
            )
        elif self.target_file.get() and self.exclude_file.get():
            self.process_button.config(
                state=tk.NORMAL, 
                bg=self.partial_mode_color
            )
        else:
            self.process_button.config(
                state=tk.DISABLED, 
                bg=self.default_color
            )
            
    def process_files(self):
        output_file = filedialog.asksaveasfilename(title="Save output file", 
                                                  defaultextension=".txt", 
                                                  filetypes=[("Text Files", "*.txt")])
        if not output_file:
            return
            
        try:
            # Load exclusion terms
            print("Loading exclusion strings...")
            exclude_trimmed = trim_columns(self.exclude_file.get())
            exclude_terms = set()
            for line in exclude_trimmed:
                cols = line.split('\t')
                if len(cols) > 5:
                    exclude_terms.add(cols[5].strip())
            print(f"Loaded {len(exclude_terms)} exclusion terms")

            # Load source terms if file provided
            source_terms = set()
            if self.source_file.get():
                print("Processing source file...")
                source_trimmed = trim_columns(self.source_file.get())
                for line in source_trimmed:
                    cols = line.split('\t')
                    if len(cols) > 5:
                        source_terms.add(cols[5].strip())
                print(f"Loaded {len(source_terms)} source terms")

            # Process target file
            print("Processing target file...")
            target_trimmed = trim_columns(self.target_file.get())
            
            categories = ['0', '1', '4', '8', '20', '28', '30', '59']
            new_terms = []
            seen_terms = set()
            excluded_count = 0
            filtered_count = 0

            for line in target_trimmed:
                cols = line.split('\t')
                if len(cols) < 9:
                    continue
                    
                category = cols[0]
                key4 = cols[4]
                kr_term = cols[5].strip()
                
                # Check category conditions
                is_valid = False
                if category == '1' and key4 in ['0', '1']:
                    is_valid = True
                elif category in categories and category != '1' and key4 == '0':
                    is_valid = True
                    
                if (is_valid and 
                    len(kr_term) <= 22 and 
                    '<null>' not in kr_term and 
                    kr_term.strip()):
                    
                    filtered_count += 1
                    if ((kr_term not in source_terms or not self.source_file.get()) and 
                        kr_term not in seen_terms and 
                        kr_term not in exclude_terms):
                        new_terms.append(line)
                        seen_terms.add(kr_term)
                    elif kr_term in exclude_terms:
                        excluded_count += 1

            print(f"Writing {len(new_terms)} new terms to file...")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.writelines(new_terms)

            success_message = (
                f"New term list created with:\n"
                f"- {len(new_terms)} unique new terms\n"
                f"- Removed {filtered_count - len(new_terms)} duplicates"
            )
            
            if self.source_file.get():
                success_message += "/existing terms"
            success_message += f"\n- Excluded {excluded_count} terms from exclusion list"
            
            messagebox.showinfo("Success", success_message)
            
        except Exception as e:
            print(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    app = TermListGUI()
    app.root.mainloop()