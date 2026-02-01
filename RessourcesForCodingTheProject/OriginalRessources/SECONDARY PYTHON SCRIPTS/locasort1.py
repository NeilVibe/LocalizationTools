import os
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


def center_window(win):
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    x = (win.winfo_screenwidth() // 2) - (w // 2)
    y = (win.winfo_screenheight() // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

SETTINGS_FILE = "locasort_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "export_path": "",
        "locasort_path": "",
        "memoq_projects": [],
        "folder_mapping": {},  # {project: [export_folder, ...]}
        "sub_allocations": {}  # {parent_folder: {child: project}}
    }

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

def get_folders(path):
    if not os.path.isdir(path):
        print(f"[DEBUG] get_folders: '{path}' is not a directory.")
        return []
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    print(f"[DEBUG] get_folders: Folders in '{path}': {folders}")
    return folders

def get_folder_children(path):
    """Return all immediate children (files and folders) of a folder."""
    if not os.path.isdir(path):
        return []
    return os.listdir(path)

def clean_folder(folder_path):
    """
    Remove all contents of the folder, but not the folder itself.
    """
    if not os.path.exists(folder_path):
        print(f"[DEBUG] clean_folder: '{folder_path}' does not exist, nothing to clean.")
        return
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.chmod(file_path, 0o600)
                os.remove(file_path)
                print(f"[DEBUG] clean_folder: Removed file '{file_path}'")
            elif os.path.isdir(file_path):
                # Recursively remove directory
                for root, dirs, files in os.walk(file_path, topdown=False):
                    for momo in files:
                        file_to_remove = os.path.join(root, momo)
                        os.chmod(file_to_remove, 0o600)
                        os.remove(file_to_remove)
                        print(f"[DEBUG] clean_folder: Removed file '{file_to_remove}'")
                    for momo in dirs:
                        dir_to_remove = os.path.join(root, momo)
                        os.chmod(dir_to_remove, 0o700)
                        os.rmdir(dir_to_remove)
                        print(f"[DEBUG] clean_folder: Removed dir '{dir_to_remove}'")
                os.chmod(file_path, 0o700)
                os.rmdir(file_path)
                print(f"[DEBUG] clean_folder: Removed dir '{file_path}'")
        except Exception as e:
            print(f"[DEBUG] clean_folder: Failed to remove '{file_path}': {e}")

def folder_has_sub_allocations(settings, folder):
    """Return True if any children of this folder are allocated to any project."""
    return folder in settings.get("sub_allocations", {}) and bool(settings["sub_allocations"][folder])

def get_sub_allocation_info(settings, folder):
    """Return a string describing sub-allocations for this folder."""
    if not folder_has_sub_allocations(settings, folder):
        return ""
    sub_alloc = settings["sub_allocations"][folder]
    projects = set(sub_alloc.values())
    return f"(sub-parts allocated: {', '.join(projects)})"

def get_unallocated_children(settings, export_path, folder):
    """Return list of children of folder that are not yet allocated to any project."""
    folder_path = os.path.join(export_path, folder)
    all_children = get_folder_children(folder_path)
    allocated = set(settings.get("sub_allocations", {}).get(folder, {}).keys())
    return [c for c in all_children if c not in allocated]

def get_allocated_children(settings, folder, project):
    """Return list of children of folder allocated to this project."""
    sub_alloc = settings.get("sub_allocations", {}).get(folder, {})
    return [c for c, p in sub_alloc.items() if p == project]

class SubPartAllocationWindow(tk.Toplevel):
    def __init__(self, master, settings, export_path, folder, memoq_projects, on_save):
        super().__init__(master)
        self.title(f"Allocate Sub-Parts of '{folder}'")
        # Make window much larger for clarity
        self.geometry("1400x800")
        self.resizable(True, True)
        self.settings = settings
        self.export_path = export_path
        self.folder = folder
        self.memoq_projects = memoq_projects
        self.on_save = on_save

        self.sub_alloc = dict(settings.get("sub_allocations", {}).get(folder, {}))  # {child: project}

        # Left: Unallocated children
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="both", expand=True, padx=30, pady=30)
        tk.Label(left_frame, text="Unallocated Sub-Parts", font=("Arial", 14, "bold")).pack()
        self.unallocated_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED, font=("Arial", 13), width=45, height=32)
        self.unallocated_listbox.pack(pady=10, fill="both", expand=True)
        self.refresh_unallocated()

        # Center: Project selection
        center_frame = tk.Frame(self)
        center_frame.pack(side="left", fill="y", pady=30)
        tk.Label(center_frame, text="Allocate to Project:", font=("Arial", 14)).pack(pady=5)
        self.project_var = tk.StringVar()
        self.project_menu = tk.OptionMenu(center_frame, self.project_var, *memoq_projects)
        self.project_menu.config(font=("Arial", 13), width=22)
        self.project_menu.pack(pady=5)
        tk.Button(center_frame, text="→ Assign →", width=18, font=("Arial", 13), command=self.assign_to_project).pack(pady=30)
        tk.Button(center_frame, text="← Unassign ←", width=18, font=("Arial", 13), command=self.unassign_from_project).pack(pady=30)

        # Right: Allocated children per project
        right_frame = tk.Frame(self)
        right_frame.pack(side="left", fill="both", expand=True, padx=30, pady=30)
        tk.Label(right_frame, text="Allocated Sub-Parts", font=("Arial", 14, "bold")).pack()
        self.allocated_listbox = tk.Listbox(right_frame, selectmode=tk.EXTENDED, font=("Arial", 13), width=45, height=32)
        self.allocated_listbox.pack(pady=10, fill="both", expand=True)
        self.refresh_allocated()

        tk.Button(self, text="Save & Close", font=("Arial", 15, "bold"), bg="#4CAF50", fg="white", command=self.save_and_close).pack(pady=20, side="bottom")

        self.protocol("WM_DELETE_WINDOW", self.save_and_close)
        self.lift()
        self.focus_force()

    def refresh_unallocated(self):
        self.unallocated_listbox.delete(0, tk.END)
        folder_path = os.path.join(self.export_path, self.folder)
        all_children = get_folder_children(folder_path)
        allocated = set(self.sub_alloc.keys())
        for c in sorted([c for c in all_children if c not in allocated]):
            self.unallocated_listbox.insert(tk.END, c)

    def refresh_allocated(self):
        self.allocated_listbox.delete(0, tk.END)
        # Show as "child [project]"
        for c, p in sorted(self.sub_alloc.items()):
            self.allocated_listbox.insert(tk.END, f"{c} [{p}]")

    def assign_to_project(self):
        selected = list(self.unallocated_listbox.curselection())
        if not selected:
            return
        project = self.project_var.get()
        if not project:
            messagebox.showinfo("Select Project", "Please select a MemoQ project to assign to.")
            return
        for i in selected:
            child = self.unallocated_listbox.get(i)
            self.sub_alloc[child] = project
        self.refresh_unallocated()
        self.refresh_allocated()

    def unassign_from_project(self):
        selected = list(self.allocated_listbox.curselection())
        if not selected:
            return
        for i in reversed(selected):
            entry = self.allocated_listbox.get(i)
            child = entry.split(" [")[0]
            if child in self.sub_alloc:
                del self.sub_alloc[child]
        self.refresh_unallocated()
        self.refresh_allocated()

    def save_and_close(self):
        if self.folder not in self.settings.get("sub_allocations", {}):
            self.settings.setdefault("sub_allocations", {})[self.folder] = {}
        self.settings["sub_allocations"][self.folder] = dict(self.sub_alloc)
        self.on_save()
        self.destroy()

class ProjectFolderAssignWindow(tk.Toplevel):
    def __init__(self, master, project, settings, on_assignments_changed):
        super().__init__(master)
        self.title(f"Assign Folders to Project: {project}")
        # Make window much larger for clarity
        self.geometry("1400x900")
        self.resizable(True, True)
        self.project = project
        self.settings = settings
        self.on_assignments_changed = on_assignments_changed

        export_path = self.settings.get("export_path", "")
        all_folders = set(get_folders(export_path))
        assigned_folders = set()
        for proj, folders in self.settings.get("folder_mapping", {}).items():
            if proj != self.project:
                assigned_folders.update(folders)
        project_folders = set(self.settings.get("folder_mapping", {}).get(self.project, []))
        unassigned_folders = sorted(list(all_folders - assigned_folders - project_folders))
        project_folders = sorted(list(project_folders))

        # Left: Available folders
        left_frame = tk.Frame(self)
        left_frame.pack(side="left", fill="both", expand=True, padx=30, pady=30)
        tk.Label(left_frame, text="Available Export Folders", font=("Arial", 14, "bold")).pack()
        self.unassigned_listbox = tk.Listbox(left_frame, selectmode=tk.EXTENDED, font=("Arial", 13), width=45, height=38)
        self.unassigned_listbox.pack(pady=10, fill="both", expand=True)
        for f in unassigned_folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.unassigned_listbox.insert(tk.END, display)

        # Center: Assign/unassign buttons
        center_frame = tk.Frame(self)
        center_frame.pack(side="left", fill="y", pady=30)
        tk.Button(center_frame, text="→ Assign →", width=18, font=("Arial", 13), command=self.assign_folders).pack(pady=30)
        tk.Button(center_frame, text="← Unassign ←", width=18, font=("Arial", 13), command=self.unassign_folders).pack(pady=30)
        tk.Button(center_frame, text="Allocate Sub-Parts", width=18, font=("Arial", 13), command=self.allocate_sub_parts).pack(pady=30)

        # Right: Project folders
        right_frame = tk.Frame(self)
        right_frame.pack(side="left", fill="both", expand=True, padx=30, pady=30)
        tk.Label(right_frame, text=f"Folders in '{project}'", font=("Arial", 14, "bold")).pack()
        self.assigned_listbox = tk.Listbox(right_frame, selectmode=tk.EXTENDED, font=("Arial", 13), width=45, height=38)
        self.assigned_listbox.pack(pady=10, fill="both", expand=True)
        for f in project_folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.assigned_listbox.insert(tk.END, display)

        tk.Button(self, text="Save & Close", font=("Arial", 15, "bold"), bg="#4CAF50", fg="white", command=self.save_and_close).pack(pady=20, side="bottom")

        self.protocol("WM_DELETE_WINDOW", self.save_and_close)
        self.lift()
        self.focus_force()

    def _get_folder_name(self, display):
        # Remove any "★ " and info
        if display.startswith("★ "):
            display = display[2:]
        return display.split(" (sub-parts")[0].strip()

    def assign_folders(self):
        selected = list(self.unassigned_listbox.curselection())
        folders = [self._get_folder_name(self.unassigned_listbox.get(i)) for i in selected]
        for f in folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.assigned_listbox.insert(tk.END, display)
        for i in reversed(selected):
            self.unassigned_listbox.delete(i)

    def unassign_folders(self):
        selected = list(self.assigned_listbox.curselection())
        folders = [self._get_folder_name(self.assigned_listbox.get(i)) for i in selected]
        for f in folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.unassigned_listbox.insert(tk.END, display)
        for i in reversed(selected):
            self.assigned_listbox.delete(i)

    def allocate_sub_parts(self):
        # Can only allocate sub-parts of a folder in the available list
        sel = self.unassigned_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Folder", "Please select a folder from the available list to allocate sub-parts.")
            return
        display = self.unassigned_listbox.get(sel[0])
        folder = self._get_folder_name(display)
        export_path = self.settings.get("export_path", "")
        memoq_projects = self.settings.get("memoq_projects", [])
        def on_save():
            # Refresh both listboxes to update info
            self.refresh_listboxes()
        SubPartAllocationWindow(self, self.settings, export_path, folder, memoq_projects, on_save)

    def refresh_listboxes(self):
        # Rebuild both listboxes with updated info
        export_path = self.settings.get("export_path", "")
        all_folders = set(get_folders(export_path))
        assigned_folders = set()
        for proj, folders in self.settings.get("folder_mapping", {}).items():
            if proj != self.project:
                assigned_folders.update(folders)
        project_folders = set(self.settings.get("folder_mapping", {}).get(self.project, []))
        unassigned_folders = sorted(list(all_folders - assigned_folders - project_folders))
        project_folders = sorted(list(project_folders))

        self.unassigned_listbox.delete(0, tk.END)
        for f in unassigned_folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.unassigned_listbox.insert(tk.END, display)
        self.assigned_listbox.delete(0, tk.END)
        for f in project_folders:
            info = get_sub_allocation_info(self.settings, f)
            display = f if not info else f"★ {f} {info}"
            self.assigned_listbox.insert(tk.END, display)

    def save_and_close(self):
        assigned = [self._get_folder_name(self.assigned_listbox.get(i)) for i in range(self.assigned_listbox.size())]
        self.settings["folder_mapping"][self.project] = assigned
        self.on_assignments_changed()
        self.destroy()

class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings, on_save):
        super().__init__(master)
        self.title("Settings")
        self.geometry("1100x1000")
        self.resizable(True, True)
        self.settings = settings
        self.on_save = on_save

        self.export_path_var = tk.StringVar(value=settings.get("export_path", ""))
        self.locasort_path_var = tk.StringVar(value=settings.get("locasort_path", ""))

        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(top_frame, text="Export Path:", font=("Arial", 12)).grid(row=0, column=0, sticky="w")
        tk.Entry(top_frame, textvariable=self.export_path_var, width=60, font=("Arial", 12)).grid(row=0, column=1, padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_export, font=("Arial", 12)).grid(row=0, column=2, padx=5)

        tk.Label(top_frame, text="LocaSort Path:", font=("Arial", 12)).grid(row=1, column=0, sticky="w")
        tk.Entry(top_frame, textvariable=self.locasort_path_var, width=60, font=("Arial", 12)).grid(row=1, column=1, padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_locasort, font=("Arial", 12)).grid(row=1, column=2, padx=5)

        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="MemoQ Projects", font=("Arial", 14, "bold")).pack(anchor="w")
        self.project_listbox = tk.Listbox(left_frame, selectmode=tk.SINGLE, font=("Arial", 12), width=30, height=30)
        self.project_listbox.pack(fill="both", expand=True, pady=5)
        self.project_listbox.bind('<Double-Button-1>', self.open_project_assign_window)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_project, font=("Arial", 12)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Remove", command=self.remove_project, font=("Arial", 12)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Rename", command=self.rename_project, font=("Arial", 12)).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Assign Folders", command=self.open_project_assign_window, font=("Arial", 12)).pack(side="left", padx=2)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="left", fill="both", expand=True)
        tk.Label(right_frame, text="Instructions", font=("Arial", 13, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(right_frame, text=(
            "1. Add MemoQ projects.\n"
            "2. Double-click a project or select and click 'Assign Folders' to assign export folders.\n"
            "3. Only unassigned folders can be assigned to a project.\n"
            "4. You can now allocate sub-parts (subfolders/files) of a folder to different projects.\n"
            "   - Select a folder and click 'Allocate Sub-Parts' to open the allocation window.\n"
            "   - Folders with sub-parts allocated show a ★ and info.\n"
            "5. Save your settings when done."
        ), font=("Arial", 12), justify="left").pack(anchor="w")

        tk.Button(self, text="Save Settings", command=self.save, font=("Arial", 14, "bold"), bg="#4CAF50", fg="white").pack(pady=15)

        self.update_project_listbox()
        self.protocol("WM_DELETE_WINDOW", self.save)
        self.lift()
        self.focus_force()
        center_window(self)

    def browse_export(self):
        path = filedialog.askdirectory(title="Select Export Path")
        if path:
            self.export_path_var.set(path)
            self.settings["export_path"] = path

    def browse_locasort(self):
        path = filedialog.askdirectory(title="Select LocaSort Path")
        if path:
            self.locasort_path_var.set(path)
            self.settings["locasort_path"] = path

    def update_project_listbox(self):
        self.project_listbox.delete(0, tk.END)
        for proj in self.settings.get("memoq_projects", []):
            self.project_listbox.insert(tk.END, proj)

    def add_project(self):
        name = simpledialog.askstring("Add MemoQ Project", "Enter new MemoQ project name:")
        if name and name not in self.settings["memoq_projects"]:
            self.settings["memoq_projects"].append(name)
            self.settings["folder_mapping"][name] = []
            self.update_project_listbox()
            self.project_listbox.selection_clear(0, tk.END)
            self.project_listbox.selection_set(tk.END)

    def remove_project(self):
        sel = self.project_listbox.curselection()
        if sel:
            proj = self.project_listbox.get(sel[0])
            del self.settings["folder_mapping"][proj]
            self.settings["memoq_projects"].remove(proj)
            # Remove sub_allocations for this project
            for folder in list(self.settings.get("sub_allocations", {})):
                sub_alloc = self.settings["sub_allocations"][folder]
                to_remove = [c for c, p in sub_alloc.items() if p == proj]
                for c in to_remove:
                    del sub_alloc[c]
                if not sub_alloc:
                    del self.settings["sub_allocations"][folder]
            self.update_project_listbox()

    def rename_project(self):
        sel = self.project_listbox.curselection()
        if sel:
            old = self.project_listbox.get(sel[0])
            new = simpledialog.askstring("Rename MemoQ Project", f"Rename '{old}' to:")
            if new and new not in self.settings["memoq_projects"]:
                idx = self.settings["memoq_projects"].index(old)
                self.settings["memoq_projects"][idx] = new
                self.settings["folder_mapping"][new] = self.settings["folder_mapping"].pop(old)
                # Update sub_allocations
                for folder in self.settings.get("sub_allocations", {}):
                    sub_alloc = self.settings["sub_allocations"][folder]
                    for c in list(sub_alloc):
                        if sub_alloc[c] == old:
                            sub_alloc[c] = new
                self.update_project_listbox()
                self.project_listbox.selection_clear(0, tk.END)
                self.project_listbox.selection_set(idx)

    def open_project_assign_window(self, event=None):
        sel = self.project_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Project", "Please select a MemoQ project first.")
            return
        proj = self.project_listbox.get(sel[0])
        def on_assignments_changed():
            pass
        self.settings["export_path"] = self.export_path_var.get()
        ProjectFolderAssignWindow(self, proj, self.settings, on_assignments_changed)

    def save(self):
        for proj in list(self.settings["folder_mapping"]):
            if proj not in self.settings["memoq_projects"]:
                del self.settings["folder_mapping"][proj]
        self.settings["export_path"] = self.export_path_var.get()
        self.settings["locasort_path"] = self.locasort_path_var.get()
        save_settings(self.settings)
        self.on_save(self.settings)
        self.destroy()

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LocaSort GUI")
        self.geometry("500x250")
        self.settings = load_settings()

        tk.Label(self, text="LocaSort", font=("Arial", 22, "bold")).pack(pady=15)
        tk.Button(self, text="Settings", width=22, height=2, font=("Arial", 14), command=self.open_settings).pack(pady=10)
        tk.Button(self, text="Launch LocaSort", width=22, height=2, font=("Arial", 14), command=self.launch_locasort).pack(pady=10)

        self.status_var = tk.StringVar()
        tk.Label(self, textvariable=self.status_var, fg="blue", font=("Arial", 12)).pack(pady=10)

    def open_settings(self):
        self.settings_window = SettingsWindow(self, self.settings, self.on_settings_saved)
        self.settings_window.grab_set()

    def on_settings_saved(self, new_settings):
        self.settings = new_settings

    def launch_locasort(self):
        export_path = self.settings.get("export_path", "")
        locasort_path = self.settings.get("locasort_path", "")
        folder_mapping = self.settings.get("folder_mapping", {})
        memoq_projects = self.settings.get("memoq_projects", [])
        sub_allocations = self.settings.get("sub_allocations", {})

        if not export_path or not locasort_path or not memoq_projects or not folder_mapping:
            messagebox.showerror("Error", "Please configure settings and mappings first.")
            return

        # CLEAN LocaSort folder before re-import (remove all contents, keep the folder)
        try:
            if not os.path.exists(locasort_path):
                os.makedirs(locasort_path, exist_ok=True)
            clean_folder(locasort_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clean LocaSort folder:\n{e}")
            return

        # Create MemoQ project folders in LocaSort
        for proj in memoq_projects:
            dest = os.path.join(locasort_path, proj)
            try:
                os.makedirs(dest, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create folder {dest}:\n{e}")
                return

        # Copy mapped folders
        for memoq_proj, folders in folder_mapping.items():
            for export_folder in folders:
                src = os.path.join(export_path, export_folder)
                dst = os.path.join(locasort_path, memoq_proj, export_folder)
                if os.path.exists(src):
                    if os.path.exists(dst):
                        try:
                            shutil.rmtree(dst)
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to remove previous folder {dst}:\n{e}")
                            return
                    try:
                        shutil.copytree(src, dst)
                        for root, dirs, files in os.walk(dst):
                            for momo in dirs:
                                os.chmod(os.path.join(root, momo), 0o700)
                            for momo in files:
                                os.chmod(os.path.join(root, momo), 0o600)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to copy {src} to {dst}:\n{e}")
                        return
                else:
                    messagebox.showwarning("Warning", f"Source folder does not exist: {src}")

        # Copy sub-allocated children
        for parent_folder, child_map in sub_allocations.items():
            parent_src = os.path.join(export_path, parent_folder)
            for child, project in child_map.items():
                src_path = os.path.join(parent_src, child)
                dst_path = os.path.join(locasort_path, project, parent_folder, child)
                if os.path.exists(src_path):
                    dst_parent = os.path.dirname(dst_path)
                    if not os.path.exists(dst_parent):
                        os.makedirs(dst_parent, exist_ok=True)
                    # Remove previous if exists
                    if os.path.exists(dst_path):
                        try:
                            if os.path.isdir(dst_path):
                                shutil.rmtree(dst_path)
                            else:
                                os.remove(dst_path)
                        except Exception as e:
                            messagebox.showerror("Error", f"Failed to remove previous {dst_path}:\n{e}")
                            return
                    try:
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dst_path)
                            for root, dirs, files in os.walk(dst_path):
                                for momo in dirs:
                                    os.chmod(os.path.join(root, momo), 0o700)
                                for momo in files:
                                    os.chmod(os.path.join(root, momo), 0o600)
                        else:
                            shutil.copy2(src_path, dst_path)
                            os.chmod(dst_path, 0o600)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to copy {src_path} to {dst_path}:\n{e}")
                        return
                else:
                    messagebox.showwarning("Warning", f"Source sub-part does not exist: {src_path}")

        self.status_var.set("LocaSort completed successfully!")
        messagebox.showinfo("Done", "LocaSort completed successfully!")

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()