import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import threading

def get_relative_paths(root_folder):
    """
    Recursively walk the folder and return a set of all relative file and directory paths,
    relative to the selected parent folder.
    """
    path_set = set()
    for dirpath, dirnames, filenames in os.walk(root_folder):
        rel_dir = os.path.relpath(dirpath, root_folder)
        # Normalize "." to "" for root
        rel_dir = "" if rel_dir == "." else rel_dir.replace("\\", "/")
        # Add the directory itself
        path_set.add(rel_dir)
        # Add files with their relative paths
        for fname in filenames:
            rel_file = os.path.join(rel_dir, fname) if rel_dir else fname
            path_set.add(rel_file.replace("\\", "/"))
    return path_set

class FolderStructureComparer:
    def __init__(self, root):
        self.root = root
        self.root.title("Folder Structure & Path Comparer")
        self.root.geometry("900x550")
        self.source_folder = ""
        self.target_folder = ""

        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Source selection
        src_frame = tk.Frame(main_frame)
        src_frame.pack(fill=tk.X, pady=10)
        tk.Label(src_frame, text="Source Parent Folder:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.src_entry = tk.Entry(src_frame, width=80)
        self.src_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(src_frame, text="Select...", command=self.select_source, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

        # Target selection
        tgt_frame = tk.Frame(main_frame)
        tgt_frame.pack(fill=tk.X, pady=10)
        tk.Label(tgt_frame, text="Target Parent Folder:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.tgt_entry = tk.Entry(tgt_frame, width=80)
        self.tgt_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(tgt_frame, text="Select...", command=self.select_target, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

        # Compare button
        tk.Button(main_frame, text="Compare Structures & Paths", command=self.start_comparison,
                  bg="#4CAF50", fg="white", font=("Arial", 12), pady=10).pack(pady=(20, 5))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)
        self.progress_label = tk.Label(main_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W)

        # Output area
        tk.Label(main_frame, text="Comparison Output:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(main_frame, height=18, width=110)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=10)

    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Parent Folder")
        if folder:
            self.source_folder = folder
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, folder)

    def select_target(self):
        folder = filedialog.askdirectory(title="Select Target Parent Folder")
        if folder:
            self.target_folder = folder
            self.tgt_entry.delete(0, tk.END)
            self.tgt_entry.insert(0, folder)

    def start_comparison(self):
        if not self.source_folder or not self.target_folder:
            messagebox.showerror("Error", "Please select both source and target parent folders.")
            return
        thread = threading.Thread(target=self.compare_folders)
        thread.start()

    def compare_folders(self):
        self.progress_label.config(text="Comparing folder and file path structures...")
        self.progress['value'] = 0
        self.output_text.delete(1.0, tk.END)
        self.root.update()

        src = self.source_folder
        tgt = self.target_folder

        src_set = get_relative_paths(src)
        tgt_set = get_relative_paths(tgt)

        self.progress['value'] = 50
        self.root.update()

        only_in_src = sorted(src_set - tgt_set)
        only_in_tgt = sorted(tgt_set - src_set)
        in_both = sorted(src_set & tgt_set)

        report = []
        report.append(f"Source Parent: {src}")
        report.append(f"Target Parent: {tgt}")
        report.append("="*80)
        if not only_in_src and not only_in_tgt:
            report.append("✓ Structures and ALL RELATIVE PATHS are IDENTICAL! All folders and files match.")
        else:
            if only_in_src:
                report.append(f"\nPaths ONLY in SOURCE ({len(only_in_src)}):")
                for path in only_in_src:
                    report.append(f"  [S] {path or '.'}")
            if only_in_tgt:
                report.append(f"\nPaths ONLY in TARGET ({len(only_in_tgt)}):")
                for path in only_in_tgt:
                    report.append(f"  [T] {path or '.'}")
            report.append(f"\nPaths present in BOTH: {len(in_both)}")

        self.progress['value'] = 100
        self.progress_label.config(text="Comparison complete!")
        self.output_text.insert(tk.END, "\n".join(report))
        self.root.update()

def main():
    root = tk.Tk()
    app = FolderStructureComparer(root)
    root.mainloop()

if __name__ == "__main__":
    main()