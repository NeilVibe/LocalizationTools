import os
import shutil
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import stat

def make_writable(path):
    try:
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
    except Exception as e:
        print(f"[DEBUG][ERROR] Could not make writable: {path}: {e}")

def fix_bad_entities(xml_text):
    return re.sub(
        r'&(?!lt;|gt;|amp;|apos;|quot;)',
        '&amp;', xml_text
    )

def parse_xml_file(file_path):
    try:
        txt = open(file_path, encoding='utf-8').read()
    except Exception as e:
        print(f"[DEBUG] Error reading {file_path!r}: {e}")
        return None
    txt = fix_bad_entities(txt)
    wrapped = "<ROOT>\n" + txt + "\n</ROOT>"
    try:
        import lxml.etree as ET
        rec_parser = ET.XMLParser(recover=True)
        recovered = ET.fromstring(wrapped.encode('utf-8'), parser=rec_parser)
        strict_parser = ET.XMLParser(recover=False)
        blob = ET.tostring(recovered, encoding='utf-8')
        return ET.fromstring(blob, parser=strict_parser)
    except Exception:
        try:
            import xml.etree.ElementTree as ET
            return ET.fromstring(wrapped)
        except Exception:
            return None

def extract_stringids_from_file(file_path):
    root = parse_xml_file(file_path)
    if root is None:
        return set()
    sids = set()
    for elem in root.iter():
        if 'StringId' in getattr(elem, 'attrib', {}):
            sids.add(elem.attrib['StringId'])
    return sids

def build_export_file_map_by_filename(export_folder):
    file_map = {}
    for dirpath, _, filenames in os.walk(export_folder):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            file_map.setdefault(fname.lower(), []).append(full)
    return file_map

def build_export_stringid_index(export_folder):
    stringid_index = {}
    filename_to_fullpath = {}
    for dirpath, _, filenames in os.walk(export_folder):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            sids = extract_stringids_from_file(full)
            stringid_index[full] = sids
            filename_to_fullpath[fname.lower()] = full
    return stringid_index, filename_to_fullpath

def batch_merge_preview_source_to_target(source_folder, export_folder, target_folder, log_func=print):
    export_file_map = build_export_file_map_by_filename(export_folder)
    merged_files = []
    errors = []
    plan = []
    for dirpath, _, filenames in os.walk(source_folder):
        for fname in filenames:
            src_file = os.path.join(dirpath, fname)
            matches = export_file_map.get(fname.lower(), [])
            fuzzy_ratio = None
            fuzzy_detail = None
            if not matches:
                msg = f"[DEBUG][ERROR] File '{fname}' from source not found in LOOKUP folder"
                print(msg)
                errors.append(msg)
                continue
            elif len(matches) == 1:
                exp = matches[0]
            else:
                src_ids = extract_stringids_from_file(src_file)
                best_ratio = 0.0
                best_path = None
                for exp_path in matches:
                    exp_ids = extract_stringids_from_file(exp_path)
                    if not exp_ids:
                        continue
                    inter = len(src_ids & exp_ids)
                    union = len(src_ids | exp_ids)
                    if union == 0:
                        continue
                    ratio = inter / union
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_path = exp_path
                if best_path:
                    exp = best_path
                    fuzzy_ratio = best_ratio
                    fuzzy_detail = f"(duplicate found, correct path found with highest ratio={best_ratio:.2f})"
                    msg = f"[DEBUG] Duplicate filename '{fname}': picked {exp} by StringId similarity (ratio={best_ratio:.2f})"
                    print(msg)
                    log_func(msg)
                else:
                    exp = matches[0]
                    fuzzy_ratio = None
                    fuzzy_detail = "(duplicate found, fallback to first match, no StringId match)"
                    msg = f"[DEBUG] Duplicate filename '{fname}': fallback to {exp} (no StringId match)"
                    print(msg)
                    log_func(msg)
            rel = os.path.relpath(exp, export_folder)
            tgt = os.path.normpath(os.path.join(target_folder, rel))
            plan.append((src_file, exp, fname, rel, tgt, fuzzy_ratio, fuzzy_detail))
            merged_files.append((src_file, tgt))
            msg = f"[DEBUG] Merge preview: {src_file} → {tgt}"
            print(msg)
            log_func(msg)
    return {"plan": plan, "merged_files": merged_files, "errors": errors}

def batch_merge_execute_source_to_target(source_folder, target_folder, export_folder, summary, log_func=print):
    merged_files = []
    overwritten_files = []
    created_folders = []
    errors = []
    for src, exp, fname, rel, tgt, fuzzy_ratio, fuzzy_detail in summary["plan"]:
        td = os.path.dirname(tgt)
        if not os.path.exists(td):
            try:
                os.makedirs(td, exist_ok=True)
                created_folders.append(os.path.relpath(td, target_folder))
                msg = f"[DEBUG] Created folder: {td}"
                print(msg)
                log_func(msg)
            except Exception as e:
                msg = f"[DEBUG][ERROR] Creating folder {td}: {e}"
                print(msg)
                errors.append(msg)
                continue
        if os.path.exists(tgt):
            overwritten_files.append(tgt)
            msg = f"[DEBUG] Overwriting file: {tgt}"
            print(msg)
            log_func(msg)
            make_writable(tgt)
        else:
            merged_files.append(tgt)
            msg = f"[DEBUG] Copying new file: {src} → {tgt}"
            print(msg)
            log_func(msg)
        try:
            shutil.copy2(src, tgt)
        except Exception as e:
            msg = f"[DEBUG][ERROR] Copying {src} to {tgt}: {e}"
            print(msg)
            errors.append(msg)
    return {
        "merged_files": merged_files,
        "overwritten_files": overwritten_files,
        "created_folders": created_folders,
        "errors": errors,
    }

def fuzzy_force_merge_find_matches(missing_files, export_stringid_index, export_folder, log_func=print, threshold=0.1):
    matches = []
    for src_file, fname in missing_files:
        src_ids = extract_stringids_from_file(src_file)
        if not src_ids:
            msg = f"[DEBUG] No StringIds found in {src_file}, skipping fuzzy match."
            print(msg)
            log_func(msg)
            continue
        best_ratio = 0.0
        best_path = None
        for exp_path, exp_ids in export_stringid_index.items():
            if not exp_ids:
                continue
            inter = len(src_ids & exp_ids)
            union = len(src_ids | exp_ids)
            if union == 0:
                continue
            ratio = inter / union
            if ratio > best_ratio:
                best_ratio = ratio
                best_path = exp_path
        if best_ratio >= threshold and best_path:
            rel = os.path.relpath(best_path, export_folder)
            msg = f"[DEBUG] Fuzzy match: {src_file} → {best_path} (ratio={best_ratio:.2f})"
            print(msg)
            log_func(msg)
            matches.append((
                src_file, best_path, best_ratio,
                os.path.basename(best_path), rel
            ))
        else:
            msg = f"[DEBUG] No fuzzy match for {src_file} (best ratio={best_ratio:.2f})"
            print(msg)
            log_func(msg)
    return matches

def batch_force_merge_plan(source_folder, target_folder, export_folder, summary, log_func=print, threshold=0.1):
    exp_index, _ = build_export_stringid_index(export_folder)
    done = {os.path.basename(fname) for (_, _, fname, _, _, _, _) in summary["plan"]}
    miss = []
    for dirpath, _, fns in os.walk(source_folder):
        for fn in fns:
            if fn not in done:
                miss.append((os.path.join(dirpath, fn), fn))
    raw = fuzzy_force_merge_find_matches(miss, exp_index, export_folder, log_func, threshold)
    plan = []
    for entry in raw:
        src, exp, ratio, exp_fn, rel = entry
        tgt = os.path.normpath(os.path.join(target_folder, rel))
        plan.append((src, exp, ratio, exp_fn, rel, tgt))
        msg = f"[DEBUG] Force merge plan: {src} → {tgt} (ratio={ratio:.2f})"
        print(msg)
        log_func(msg)
    return plan, miss, raw

def batch_force_merge_execute(plan, log_func=print):
    merged_files = []
    overwritten_files = []
    created_folders = []
    errors = []
    for src, exp, ratio, exp_fn, rel, tgt in plan:
        td = os.path.dirname(tgt)
        if not os.path.exists(td):
            try:
                os.makedirs(td, exist_ok=True)
                created_folders.append(os.path.relpath(td))
                msg = f"[DEBUG] Created folder: {td}"
                print(msg)
                log_func(msg)
            except Exception as e:
                msg = f"[DEBUG][ERROR] Creating folder {td}: {e}"
                print(msg)
                errors.append(msg)
                continue
        if os.path.exists(tgt):
            overwritten_files.append(tgt)
            msg = f"[DEBUG] Overwriting file: {tgt}"
            print(msg)
            log_func(msg)
            make_writable(tgt)
        else:
            merged_files.append(tgt)
            msg = f"[DEBUG] Copying new file: {src} → {tgt}"
            print(msg)
            log_func(msg)
        try:
            shutil.copy2(src, tgt)
        except Exception as e:
            msg = f"[DEBUG][ERROR] Copying {src} to {tgt}: {e}"
            print(msg)
            errors.append(msg)
    return {
        "merged_files": merged_files,
        "overwritten_files": overwritten_files,
        "created_folders": created_folders,
        "errors": errors,
    }

class MergePreviewConsoleWindow(tk.Toplevel):
    def __init__(self, master, summary, force_merge_data, confirm_callback, force_merge_callback=None, rename_force_merge_callback=None):
        super().__init__(master)
        self.title("Batch Merge Preview")
        self.geometry("900x600")
        self.confirm_callback = confirm_callback
        self.force_merge_callback = force_merge_callback
        self.rename_force_merge_callback = rename_force_merge_callback

        if isinstance(force_merge_data, tuple):
            force_plan, missing, raw = force_merge_data
        else:
            force_plan = force_merge_data
            missing = {}
            raw = {}

        lbl = ttk.Label(
            self,
            text="Preview of planned merge actions.\n"
                 "You can proceed with normal merge, force merge, or rename & force merge.",
            font=("Arial", 12, "bold")
        )
        lbl.pack(pady=(10, 5))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        normal_frame = ttk.Frame(notebook)
        notebook.add(normal_frame, text="Merge Plan")

        yscroll_normal = tk.Scrollbar(normal_frame)
        yscroll_normal.pack(side=tk.RIGHT, fill=tk.Y)

        self.txt_normal = tk.Text(
            normal_frame, state=tk.NORMAL, wrap=tk.NONE,
            font=("Consolas", 11), bg="#222", fg="#fff",
            yscrollcommand=yscroll_normal.set
        )
        self.txt_normal.pack(fill=tk.BOTH, expand=True)
        yscroll_normal.config(command=self.txt_normal.yview)

        self.txt_normal.insert(tk.END, f"Normal merge files: {len(summary['merged_files'])}\n")
        self.txt_normal.insert(tk.END, f"Force merge files: {len(force_plan)}\n\n")
        self.txt_normal.insert(tk.END, "Normal merge plan:\n")
        for src, exp, fname, rel, tgt, fuzzy_ratio, fuzzy_detail in summary["plan"]:
            base_line = f"{os.path.basename(src)} → {tgt}"
            if fuzzy_detail:
                base_line += f" {fuzzy_detail}"
            self.txt_normal.insert(tk.END, base_line + "\n")
        self.txt_normal.insert(tk.END, "\nForce merge plan:\n")
        for (src, exp, ratio, exp_fn, rel, tgt) in force_plan:
            self.txt_normal.insert(tk.END, f"{os.path.basename(src)} (fuzzy) → {tgt} (ratio={ratio:.2f})\n")
        self.txt_normal.config(state=tk.DISABLED)

        error_frame = ttk.Frame(notebook)
        notebook.add(error_frame, text="Errors")

        yscroll_error = tk.Scrollbar(error_frame)
        yscroll_error.pack(side=tk.RIGHT, fill=tk.Y)

        self.txt_error = tk.Text(
            error_frame, state=tk.NORMAL, wrap=tk.NONE,
            font=("Consolas", 11), bg="#222", fg="#fff",
            yscrollcommand=yscroll_error.set
        )
        self.txt_error.pack(fill=tk.BOTH, expand=True)
        yscroll_error.config(command=self.txt_error.yview)

        errors = summary.get("errors", [])

        self.txt_error.insert(tk.END, "=== 1. ALL ERROR FILES (from normal merge preview) ===\n")
        if errors:
            self.txt_error.insert(tk.END, f"Total: {len(errors)}\n")
            for err in errors:
                self.txt_error.insert(tk.END, f"{err}\n")
        else:
            self.txt_error.insert(tk.END, "No errors encountered during merge preview.\n")
        self.txt_error.insert(tk.END, "\n")

        self.txt_error.insert(tk.END, "=== 2. Error files resolved via fuzzy match ===\n")
        error_files = set()
        for err in errors:
            m = re.match(r"\[DEBUG\]\[ERROR\] File '(.+)' from source not found in LOOKUP folder", err)
            if m:
                fname = m.group(1)
                error_files.add(fname)
        resolved = []
        for entry in raw:
            src_file, best_path, best_ratio, exp_fn, rel = entry
            src_basename = os.path.basename(src_file)
            if src_basename in error_files:
                resolved.append((src_basename, exp_fn, best_ratio, rel))
        if resolved:
            self.txt_error.insert(tk.END, f"Resolved via fuzzy match: {len(resolved)}\n")
            for src_fn, exp_fn, ratio, rel in resolved:
                self.txt_error.insert(
                    tk.END,
                    f"{src_fn} → {exp_fn} (ratio={ratio:.2f})\n"
                )
        else:
            self.txt_error.insert(tk.END, "No error files resolved via fuzzy match.\n")
        self.txt_error.insert(tk.END, "\n")

        self.txt_error.insert(tk.END, "=== 3. Remaining files that cannot be merged even with fuzzy match ===\n")
        unresolved = []
        resolved_fns = {src_fn for src_fn, _, _, _ in resolved}
        for fname in sorted(error_files):
            if fname not in resolved_fns:
                unresolved.append(fname)
        if unresolved:
            self.txt_error.insert(tk.END, f"Unresolved: {len(unresolved)}\n")
            for fname in unresolved:
                self.txt_error.insert(tk.END, f"{fname}\n")
        else:
            self.txt_error.insert(tk.END, "All error files are resolved via fuzzy match.\n")
        self.txt_error.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10, side=tk.BOTTOM)
        self.ok_btn = ttk.Button(
            btn_frame, text="Proceed with Normal Merge", command=self.on_confirm
        )
        self.ok_btn.pack(side=tk.LEFT, padx=5)
        if self.force_merge_callback:
            self.force_btn = ttk.Button(
                btn_frame, text="Force Merge", command=self.on_force_merge
            )
            self.force_btn.pack(side=tk.LEFT, padx=5)
        if self.rename_force_merge_callback:
            self.rename_force_btn = ttk.Button(
                btn_frame, text="Rename & Force Merge", command=self.on_rename_force_merge
            )
            self.rename_force_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self.on_cancel
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()
        self.focus_set()

    def on_confirm(self):
        self.confirm_callback(True)
        self.destroy()

    def on_force_merge(self):
        if self.force_merge_callback:
            self.force_merge_callback()
        self.destroy()

    def on_rename_force_merge(self):
        if self.rename_force_merge_callback:
            self.rename_force_merge_callback()
        self.destroy()

    def on_cancel(self):
        self.confirm_callback(False)
        self.destroy()

class FolderSyncApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Batch Merge Source → Target (with Fuzzy/Force Preview)")
        self.master.geometry("900x500")

        self.source_folder = None
        self.target_folder = None

        frm = ttk.Frame(master)
        frm.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.src_btn = ttk.Button(
            frm, text="Select Source Folder", command=self.select_source
        )
        self.src_btn.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.src_lbl = ttk.Label(
            frm, text="No folder selected",
            font=("Consolas", 11, "bold")
        )
        self.src_lbl.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        self.tgt_btn = ttk.Button(
            frm, text="Select Target Folder", command=self.select_target
        )
        self.tgt_btn.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        self.tgt_lbl = ttk.Label(
            frm, text="No folder selected",
            font=("Consolas", 11, "bold")
        )
        self.tgt_lbl.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.status_txt = tk.Text(
            frm, height=15, width=80,
            state=tk.DISABLED,
            font=("Consolas", 12), bg="#222", fg="#fff"
        )
        self.status_txt.grid(row=2, column=0, columnspan=2,
                             sticky="nsew", padx=5, pady=10)
        frm.grid_rowconfigure(2, weight=1)
        frm.grid_columnconfigure(1, weight=1)

        self.merge_btn = ttk.Button(
            frm, text="Batch Merge Source → Target",
            command=self.batch_merge, state=tk.DISABLED
        )
        self.merge_btn.grid(row=3, column=0, columnspan=2,
                            sticky="ew", padx=5, pady=10)

    def log(self, msg):
        print(msg)
        self.status_txt.config(state=tk.NORMAL)
        self.status_txt.insert(tk.END, msg + "\n")
        self.status_txt.see(tk.END)
        self.status_txt.config(state=tk.DISABLED)
        self.master.update_idletasks()

    def select_source(self):
        folder = filedialog.askdirectory(title="Select Source Folder")
        if not folder:
            return
        self.source_folder = os.path.abspath(folder)
        self.src_lbl.config(text=self.source_folder)
        self.log(f"[DEBUG] Selected Source: {self.source_folder}")
        self.check_ready()

    def select_target(self):
        folder = filedialog.askdirectory(title="Select Target Folder")
        if not folder:
            return
        self.target_folder = os.path.abspath(folder)
        self.tgt_lbl.config(text=self.target_folder)
        self.log(f"[DEBUG] Selected Target: {self.target_folder}")
        self.check_ready()

    def check_ready(self):
        if self.source_folder and self.target_folder:
            self.merge_btn.config(state=tk.NORMAL)

    def batch_merge(self):
        if not (self.source_folder and self.target_folder):
            self.log("[DEBUG] Select Source and Target first.")
            return
        export_folder = filedialog.askdirectory(
            title="Select LOOKUP Folder (export for paths)"
        )
        if not export_folder:
            self.log("[DEBUG] Batch merge cancelled.")
            return

        self.log(f"[DEBUG] Merging Source → Target with preview/fuzzy/force.\nSource: {self.source_folder}\nTarget: {self.target_folder}\nExport: {export_folder}")

        summary = batch_merge_preview_source_to_target(
            self.source_folder, export_folder, self.target_folder, log_func=self.log
        )
        force_merge_data = batch_force_merge_plan(
            self.source_folder, self.target_folder, export_folder, summary,
            log_func=self.log, threshold=0.1
        )
        if isinstance(force_merge_data, tuple):
            force_plan, missing, raw = force_merge_data
        else:
            force_plan = force_merge_data
            missing = {}
            raw = {}

        def on_confirm_merge(ok):
            if not ok:
                self.log("[DEBUG] Batch merge cancelled.")
                return
            self.log("[DEBUG] Executing normal merge...")
            res = batch_merge_execute_source_to_target(
                self.source_folder, self.target_folder, export_folder,
                summary, log_func=self.log
            )
            self.log("[DEBUG] === NORMAL MERGE SUMMARY ===")
            self.log(f"[DEBUG] Folders created: {len(res['created_folders'])}")
            self.log(f"[DEBUG] Files merged: {len(res['merged_files'])}")
            self.log(f"[DEBUG] Files overwritten: {len(res['overwritten_files'])}")
            if res['errors']:
                self.log(f"[DEBUG] Errors: {len(res['errors'])}")
            self.log("[DEBUG] ============================")
            msg = (
                f"Merge complete.\n"
                f"Folders created: {len(res['created_folders'])}\n"
                f"Files merged: {len(res['merged_files'])}\n"
                f"Files overwritten: {len(res['overwritten_files'])}\n"
                f"Errors: {len(res['errors'])}"
            )
            messagebox.showinfo("Batch Merge Complete", msg)

        def on_force_merge():
            self.log("[DEBUG] Executing FORCE MERGE...")
            rn = batch_merge_execute_source_to_target(
                self.source_folder, self.target_folder, export_folder,
                summary, log_func=self.log
            )
            rf = batch_force_merge_execute(force_plan, log_func=self.log)
            created = rn['created_folders'] + rf['created_folders']
            merged = rn['merged_files'] + rf['merged_files']
            over   = rn['overwritten_files'] + rf['overwritten_files']
            errs   = rn['errors'] + rf['errors']
            self.log("[DEBUG] === FORCE MERGE SUMMARY ===")
            self.log(f"[DEBUG] Folders created: {len(created)}")
            self.log(f"[DEBUG] Files merged: {len(merged)}")
            self.log(f"[DEBUG] Files overwritten: {len(over)}")
            if errs:
                self.log(f"[DEBUG] Errors: {len(errs)}")
            self.log("[DEBUG] ===========================")
            msg = (
                f"Force Merge complete.\n"
                f"Folders created: {len(created)}\n"
                f"Files merged: {len(merged)}\n"
                f"Files overwritten: {len(over)}\n"
                f"Errors: {len(errs)}"
            )
            messagebox.showinfo("Force Merge Complete", msg)

        def on_rename_force_merge():
            self.log("[DEBUG] Rename & Force Merge: renaming fuzzy files...")
            new_plan = []
            for (src, exp, ratio, exp_fn, rel, tgt) in force_plan:
                new_src = os.path.join(os.path.dirname(src), exp_fn)
                try:
                    if not os.path.exists(new_src):
                        os.rename(src, new_src)
                        msg = f"[DEBUG] Renamed: {os.path.basename(src)} → {exp_fn}"
                        print(msg)
                        self.log(msg)
                    else:
                        msg = f"[DEBUG] Skipped renaming {src} (target exists: {new_src})"
                        print(msg)
                        self.log(msg)
                except Exception as e:
                    msg = f"[DEBUG][ERROR] Renaming {src} to {new_src}: {e}"
                    print(msg)
                    self.log(msg)
                new_plan.append((new_src, exp, ratio, exp_fn, rel, tgt))
            self.log("[DEBUG] Now performing Force Merge on renamed + normal files...")
            rn = batch_merge_execute_source_to_target(
                self.source_folder, self.target_folder, export_folder,
                summary, log_func=self.log
            )
            rf = batch_force_merge_execute(new_plan, log_func=self.log)
            created = rn['created_folders'] + rf['created_folders']
            merged = rn['merged_files'] + rf['merged_files']
            over   = rn['overwritten_files'] + rf['overwritten_files']
            errs   = rn['errors'] + rf['errors']
            self.log("[DEBUG] === RENAME & FORCE MERGE SUMMARY ===")
            self.log(f"[DEBUG] Folders created: {len(created)}")
            self.log(f"[DEBUG] Files merged: {len(merged)}")
            self.log(f"[DEBUG] Files overwritten: {len(over)}")
            if errs:
                self.log(f"[DEBUG] Errors: {len(errs)}")
            self.log("[DEBUG] ====================================")
            msg = (
                f"Rename & Force Merge complete.\n"
                f"Folders created: {len(created)}\n"
                f"Files merged: {len(merged)}\n"
                f"Files overwritten: {len(over)}\n"
                f"Errors: {len(errs)}"
            )
            messagebox.showinfo("Rename & Force Merge Complete", msg)

        MergePreviewConsoleWindow(
            self.master,
            summary,
            (force_plan, missing, raw),
            on_confirm_merge,
            force_merge_callback=on_force_merge,
            rename_force_merge_callback=on_rename_force_merge
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderSyncApp(root)
    root.mainloop()