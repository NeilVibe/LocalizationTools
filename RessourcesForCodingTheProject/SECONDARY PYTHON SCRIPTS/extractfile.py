import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class FileExtractorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("File Extractor by Substring")
        self.master.geometry("600x350")
        self.folder_path = None

        # --- GUI Layout ---
        frm = ttk.Frame(master)
        frm.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Folder selection
        self.folder_btn = ttk.Button(frm, text="Select Folder", command=self.select_folder)
        self.folder_btn.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.folder_lbl = ttk.Label(frm, text="No folder selected", font=("Consolas", 10))
        self.folder_lbl.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # Substring entry
        self.substr_lbl = ttk.Label(frm, text="Substring to search in filenames:")
        self.substr_lbl.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.substr_entry = ttk.Entry(frm, width=30)
        self.substr_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Output folder name entry
        self.outfolder_lbl = ttk.Label(frm, text="Output folder name:")
        self.outfolder_lbl.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.outfolder_entry = ttk.Entry(frm, width=30)
        self.outfolder_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Extract button
        self.extract_btn = ttk.Button(frm, text="Extract Matching Files", command=self.extract_files)
        self.extract_btn.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=15)

        # Status text
        self.status_txt = tk.Text(frm, height=8, width=70, state=tk.DISABLED, font=("Consolas", 10), bg="#222", fg="#fff")
        self.status_txt.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        frm.grid_rowconfigure(4, weight=1)
        frm.grid_columnconfigure(1, weight=1)

    def log(self, msg):
        self.status_txt.config(state=tk.NORMAL)
        self.status_txt.insert(tk.END, msg + "\n")
        self.status_txt.see(tk.END)
        self.status_txt.config(state=tk.DISABLED)
        self.master.update_idletasks()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder:
            self.folder_path = folder
            self.folder_lbl.config(text=self.folder_path)
            self.log(f"[INFO] Selected folder: {self.folder_path}")

    def extract_files(self):
        if not self.folder_path:
            messagebox.showwarning("No Folder", "Please select a folder to scan.")
            return
        substr = self.substr_entry.get().strip()
        if not substr:
            messagebox.showwarning("No Substring", "Please enter a substring to search for.")
            return
        outfolder_name = self.outfolder_entry.get().strip()
        if not outfolder_name:
            messagebox.showwarning("No Output Folder", "Please enter a name for the output folder.")
            return

        # Output folder in script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outfolder_path = os.path.join(script_dir, outfolder_name)
        os.makedirs(outfolder_path, exist_ok=True)

        self.log(f"[INFO] Scanning for files containing '{substr}' in their name...")
        matches = []
        for dirpath, _, filenames in os.walk(self.folder_path):
            for fname in filenames:
                if substr in fname:
                    fullpath = os.path.join(dirpath, fname)
                    matches.append(fullpath)

        if not matches:
            self.log("[INFO] No matching files found.")
            messagebox.showinfo("No Matches", "No files found with the specified substring.")
            return

        self.log(f"[INFO] Found {len(matches)} matching files. Copying to '{outfolder_path}'...")
        copied = 0
        for src in matches:
            try:
                # If duplicate names, add a number suffix
                basename = os.path.basename(src)
                dst = os.path.join(outfolder_path, basename)
                base, ext = os.path.splitext(basename)
                count = 1
                while os.path.exists(dst):
                    dst = os.path.join(outfolder_path, f"{base}_{count}{ext}")
                    count += 1
                shutil.copy2(src, dst)
                copied += 1
                self.log(f"[OK] Copied: {src} -> {dst}")
            except Exception as e:
                self.log(f"[ERROR] Failed to copy {src}: {e}")

        self.log(f"[DONE] Extraction complete. {copied} files copied to '{outfolder_path}'.")
        messagebox.showinfo("Extraction Complete", f"{copied} files copied to:\n{outfolder_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileExtractorApp(root)
    root.mainloop()