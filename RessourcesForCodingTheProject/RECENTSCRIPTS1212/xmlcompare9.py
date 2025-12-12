#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import hashlib
from datetime import datetime
import threading

# for fuzzy similarity in StrOrigin checks
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

class TranslationComparer:
    def __init__(self, root):
        self.root = root
        self.root.title("Translation Files Comparer - Multi-Folder Support")
        self.root.geometry("1000x800")

        # folders
        self.source_folders = []
        self.target_folders = []

        # load fuzzy model
        try:
            self.embedding_model = SentenceTransformer("KRTransformer")
            self.low_sim_threshold = 0.899
            self.high_sim_threshold = 0.999
            print("✓ Fuzzy model loaded (dim=", 
                  self.embedding_model.get_sentence_embedding_dimension(), ")")
        except Exception as e:
            messagebox.showwarning("Fuzzy Model",
                                   f"Could not load KRTransformer model:\n{e}\nFuzzy features disabled.")
            self.embedding_model = None

        # -- build UI --
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Source folders
        src_fr = tk.Frame(main_frame)
        src_fr.pack(fill=tk.X, pady=5)
        tk.Label(src_fr, text="Source Folders:", font=("Arial",10,"bold")).pack(anchor=tk.W)
        sf_lst_fr = tk.Frame(src_fr); sf_lst_fr.pack(fill=tk.X)
        self.src_listbox = tk.Listbox(sf_lst_fr, height=4)
        self.src_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Scrollbar(sf_lst_fr, command=self.src_listbox.yview).pack(side=tk.RIGHT,fill=tk.Y)
        self.src_listbox.config(yscrollcommand=lambda f,s: None)
        btn_sf = tk.Frame(src_fr); btn_sf.pack(fill=tk.X)
        tk.Button(btn_sf, text="Select Source Folders",
                  bg="#2196F3", fg="white",
                  command=self.select_source_folders).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_sf, text="Clear All",
                  command=self.clear_source_folders).pack(side=tk.LEFT, padx=5)

        # Target folders
        tgt_fr = tk.Frame(main_frame)
        tgt_fr.pack(fill=tk.X, pady=5)
        tk.Label(tgt_fr, text="Target Folders:", font=("Arial",10,"bold")).pack(anchor=tk.W)
        tf_lst_fr = tk.Frame(tgt_fr); tf_lst_fr.pack(fill=tk.X)
        self.tgt_listbox = tk.Listbox(tf_lst_fr, height=4)
        self.tgt_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Scrollbar(tf_lst_fr, command=self.tgt_listbox.yview).pack(side=tk.RIGHT,fill=tk.Y)
        self.tgt_listbox.config(yscrollcommand=lambda f,s: None)
        btn_tf = tk.Frame(tgt_fr); btn_tf.pack(fill=tk.X)
        tk.Button(btn_tf, text="Select Target Folders",
                  bg="#2196F3", fg="white",
                  command=self.select_target_folders).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_tf, text="Clear All",
                  command=self.clear_target_folders).pack(side=tk.LEFT, padx=5)

        # Action buttons
        tk.Button(main_frame, text="Compare All Combinations",
                  bg="#4CAF50", fg="white", font=("Arial",12),
                  command=self.start_comparison).pack(pady=10)
        tk.Button(main_frame, text="Export Differences as XML",
                  bg="#FF9800", fg="white", font=("Arial",12),
                  command=self.start_export_differences_xml).pack(pady=5)
        tk.Button(main_frame, text="Export Identical Strings as XML",
                  bg="#00BCD4", fg="white", font=("Arial",12),
                  command=self.start_export_identical_strings_xml).pack(pady=5)

        tk.Button(main_frame, text="Check Duplicates Between Source and Target",
                  bg="#E91E63", fg="white", font=("Arial",12),
                  command=self.start_check_duplicates).pack(pady=5)
        tk.Button(main_frame, text="Check Translation Changes",
                  bg="#9C27B0", fg="white", font=("Arial",12),
                  command=self.start_check_translation_changes).pack(pady=5)
        tk.Button(main_frame, text="Check StrOrigin Changes",
                  bg="#3F51B5", fg="white", font=("Arial",12),
                  command=self.start_check_strorigin_changes).pack(pady=5)

        # Progress
        pf = tk.Frame(main_frame)
        pf.pack(fill=tk.X, pady=5)
        self.progress_label = tk.Label(pf, text="Ready")
        self.progress_label.pack(anchor=tk.W)
        self.progress = ttk.Progressbar(pf, mode="determinate")
        self.progress.pack(fill=tk.X)

        # Output
        tk.Label(main_frame, text="Output:").pack(anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(main_frame, height=20)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    # ---------------- folder selection ----------------
    def select_source_folders(self):
        d = filedialog.askdirectory(title="Select a Parent for Source Folders")
        if not d: return
        self.source_folders.clear()
        self.src_listbox.delete(0,tk.END)
        self.show_folder_selection_dialog(d, is_source=True)

    def select_target_folders(self):
        d = filedialog.askdirectory(title="Select a Parent for Target Folders")
        if not d: return
        self.target_folders.clear()
        self.tgt_listbox.delete(0,tk.END)
        self.show_folder_selection_dialog(d, is_source=False)

    def show_folder_selection_dialog(self, parent_dir, is_source):
        subs = [os.path.join(parent_dir, f) for f in os.listdir(parent_dir)
                if os.path.isdir(os.path.join(parent_dir, f))]
        if not subs:
            messagebox.showwarning("No subdirs", "No subdirectories found.")
            return
        win = tk.Toplevel(self.root)
        win.title("Select Folders (Ctrl+Click multi)")
        win.geometry("600x400")  # bigger popup size
        lb = tk.Listbox(win, selectmode=tk.EXTENDED, font=("Arial", 12))
        lb.pack(fill=tk.BOTH, expand=True)
        # show only parent folder name + current folder name
        for p in sorted(subs):
            parent_name = os.path.basename(os.path.dirname(p))
            current_name = os.path.basename(p)
            lb.insert(tk.END, f"{parent_name}/{current_name}")
        def confirm():
            sel = lb.curselection()
            for i in sel:
                # extract current folder name from display text
                display_text = lb.get(i)
                current_name = display_text.split("/")[-1]
                full_path = os.path.join(parent_dir, current_name)
                if is_source:
                    self.source_folders.append(full_path)
                    self.src_listbox.insert(tk.END, display_text)
                else:
                    self.target_folders.append(full_path)
                    self.tgt_listbox.insert(tk.END, display_text)
            win.destroy()
        btnf = tk.Frame(win); btnf.pack(pady=5)
        tk.Button(btnf, text="Select All", command=lambda: lb.select_set(0, tk.END)).pack(side=tk.LEFT)
        tk.Button(btnf, text="Confirm", bg="#4CAF50", fg="white", command=confirm).pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="Cancel", command=win.destroy).pack(side=tk.LEFT)

    def clear_source_folders(self):
        self.source_folders.clear(); self.src_listbox.delete(0,tk.END)
    def clear_target_folders(self):
        self.target_folders.clear(); self.tgt_listbox.delete(0,tk.END)

    # ---------------- utilities ----------------
    def create_row_signature(self, elem):
        s = elem.get('StrOrigin','')+"|"+elem.get('StringId','')
        return hashlib.md5(s.encode()).hexdigest()

    def get_file_display_path(self, fid, paths_map):
        if fid not in paths_map: return fid
        rp = paths_map[fid].split(os.sep)
        return "/".join(rp[-3:]) if len(rp)>2 else "/".join(rp)

    def find_subset_files(self, folder):
        file_sigs = {}
        file_paths = {}
        for r,d,fs in os.walk(folder):
            for f in fs:
                if not f.lower().endswith(".xml"): continue
                fp = os.path.join(r,f)
                try:
                    tree = ET.parse(fp)
                    root = tree.getroot()
                    fid = root.get("FileName", os.path.relpath(fp,folder))
                    rel = os.path.relpath(fp,folder)
                    file_paths[fid] = rel
                    sset = set()
                    for e in root.findall(".//LocStr"):
                        sset.add(self.create_row_signature(e))
                    if sset:
                        file_sigs[fid] = sset
                except: pass
        subset = set()
        rels = []
        for a,sa in file_sigs.items():
            if a in subset: continue
            for b,sb in file_sigs.items():
                if a==b or b in subset: continue
                if len(sa)<len(sb):
                    common = sa & sb
                    pct = len(common)/len(sa)*100
                    if pct>=20:
                        subset.add(a)
                        rels.append({
                            "subset": self.get_file_display_path(a,file_paths),
                            "superset": self.get_file_display_path(b,file_paths),
                            "overlap":pct,
                            "subset_size":len(sa),
                            "superset_size":len(sb)
                        })
                        break
        return subset, rels

    def build_mega_table(self, folder, excluded):
        mega = {}
        file_rc = defaultdict(int)
        file_paths = {}
        for r,d,fs in os.walk(folder):
            for f in fs:
                if not f.lower().endswith(".xml"): continue
                fp = os.path.join(r,f)
                try:
                    tree = ET.parse(fp); rt = tree.getroot()
                    fid = rt.get("FileName", os.path.relpath(fp,folder))
                    if fid in excluded: continue
                    rel = os.path.relpath(fp,folder)
                    file_paths[fid] = rel
                    for i,el in enumerate(rt.findall(".//LocStr")):
                        sig = self.create_row_signature(el)
                        mega.setdefault(sig,[]).append({"file":fid,"element":el,"idx":i})
                        file_rc[fid]+=1
                except: pass
        # build file_signatures
        file_sigs = {}
        for sig,occ in mega.items():
            for o in occ:
                file_sigs.setdefault(o["file"],set()).add(sig)
        return mega, file_sigs, file_rc, file_paths

    # -------------- FULL COMPARISON --------------
    def compare_single_pair(self, src, tgt):
        lines = []
        sname = os.path.basename(src); tname = os.path.basename(tgt)
        ssub, srels = self.find_subset_files(src)
        tsub, trels = self.find_subset_files(tgt)
        if srels or trels:
            lines.append("SUBSET FILES DETECTED AND EXCLUDED:")
            lines.append("-"*60)
            if srels:
                lines.append(f"In {sname}:")
                for x in srels:
                    lines.append(f"  - \"{x['subset']}\" subset of \"{x['superset']}\" "
                                 f"({x['overlap']:.1f}% overlap)")
            if trels:
                lines.append(f"In {tname}:")
                for x in trels:
                    lines.append(f"  - \"{x['subset']}\" subset of \"{x['superset']}\" "
                                 f"({x['overlap']:.1f}% overlap)")
            lines.append("")
        stbl, sfs, srcounts, spaths = self.build_mega_table(src, ssub)
        ttbl, tfs, tcounts, tpaths = self.build_mega_table(tgt, tsub)
        ssigs = set(stbl.keys()); tsigs = set(ttbl.keys())
        miss = ssigs - tsigs; extra = tsigs - ssigs
        fm = defaultdict(list); fe = defaultdict(list)
        for sig in miss:
            for occ in stbl[sig]:
                e = occ["element"]
                fm[occ["file"]].append({
                    "StrOrigin":e.get("StrOrigin",""),
                    "StringId":e.get("StringId","")
                })
        for sig in extra:
            for occ in ttbl[sig]:
                e = occ["element"]
                fe[occ["file"]].append({
                    "StrOrigin":e.get("StrOrigin",""),
                    "StringId":e.get("StringId","")
                })
        comp_missing=[]; part_missing={}
        for f,det in fm.items():
            tot=srcounts.get(f,0)
            if det and len(det)==tot:
                comp_missing.append((self.get_file_display_path(f,spaths),tot))
            else:
                part_missing[f]={"missing":det,"total":tot}
        comp_extra=[]; part_extra={}
        for f,det in fe.items():
            if f not in sfs:
                comp_extra.append((self.get_file_display_path(f,tpaths),len(det)))
            else:
                part_extra[f]=det

        # header
        lines.append(f"COMPARISON REPORT - {tname} vs {sname}")
        lines.append("="*80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Source: {src}")
        lines.append(f"Target: {tgt}")
        lines.append(f"Excluded subsets: {len(ssub)} src, {len(tsub)} tgt\n")

        if not (comp_missing or comp_extra or part_missing or part_extra):
            lines.append("✓ No differences found.")
        else:
            if comp_missing:
                lines.append(f"COMPLETELY MISSING FILES IN TARGET ({len(comp_missing)}):")
                for p,c in sorted(comp_missing):
                    lines.append(f"  - {p} ({c} rows)")
                lines.append("")
            if comp_extra:
                lines.append(f"COMPLETELY EXTRA FILES IN TARGET ({len(comp_extra)}):")
                for p,c in sorted(comp_extra):
                    lines.append(f"  - {p} ({c} rows)")
                lines.append("")
            difffiles = set(part_missing)|set(part_extra)
            if difffiles:
                lines.append(f"FILES WITH PARTIAL DIFFERENCES ({len(difffiles)}):")
                lines.append("-"*80)
                for f in sorted(difffiles):
                    dp = self.get_file_display_path(f, 
                         spaths if f in spaths else tpaths)
                    lines.append(f"\nFile: {dp}")
                    lines.append("-"*60)
                    if f in part_missing:
                        a = part_missing[f]["missing"]
                        lines.append(f"  MISSING ROWS ({len(a)}):")
                        for e in a[:10]:
                            lines.append(f"    - StrOrigin=\"{e['StrOrigin']}\", StringId=\"{e['StringId']}\"")
                        if len(a)>10:
                            lines.append(f"    ... and {len(a)-10} more")
                    if f in part_extra:
                        a = part_extra[f]
                        lines.append(f"  EXTRA ROWS ({len(a)}):")
                        for e in a[:10]:
                            lines.append(f"    - StrOrigin=\"{e['StrOrigin']}\", StringId=\"{e['StringId']}\"")
                        if len(a)>10:
                            lines.append(f"    ... and {len(a)-10} more")
                lines.append("")
            # stats
            lines.append("TOTAL STATISTICS:")
            lines.append(f"  - Source rows : {len(ssigs)}")
            lines.append(f"  - Target rows : {len(tsigs)}")
            lines.append(f"  - Missing rows: {len(miss)}")
            lines.append(f"  - Extra rows  : {len(extra)}")
            lines.append(f"  - Missing files completely: {len(comp_missing)}")
            lines.append(f"  - Extra files completely  : {len(comp_extra)}")
            lines.append(f"  - Files with partial diffs: {len(difffiles)}")
        return "\n".join(lines), bool(comp_missing or comp_extra or part_missing or part_extra)

    def start_comparison(self):
        if not self.source_folders or not self.target_folders:
            messagebox.showerror("Error","Select at least one source and one target.")
            return
        threading.Thread(target=self.run_comparisons, daemon=True).start()

    def run_comparisons(self):
        total = len(self.source_folders)*len(self.target_folders)
        idx = 0
        base = os.path.dirname(os.path.abspath(__file__))
        for s in self.source_folders:
            sd = os.path.basename(s)
            rpt_dir = os.path.join(base, f"Source_{sd}_compare")
            os.makedirs(rpt_dir, exist_ok=True)
            for t in self.target_folders:
                idx +=1
                tn = os.path.basename(t)
                self.progress['value'] = idx/total*100
                self.progress_label.config(text=f"{idx}/{total}: {sd}→{tn}")
                self.output_text.delete(1.0,tk.END)
                self.output_text.insert(tk.END, f"Comparing {sd} → {tn}\n")
                self.root.update()
                rpt, diff = self.compare_single_pair(s,t)
                self.output_text.insert(tk.END, rpt+"\n")
                self.root.update()
                path = os.path.join(rpt_dir, f"{tn}_report.txt")
                with open(path,"w",encoding="utf-8") as f: f.write(rpt)
                self.output_text.insert(tk.END,f"\nSaved: {path}\n")
                self.root.update()
        self.progress['value']=100
        self.progress_label.config(text="Done all comparisons")
        messagebox.showinfo("Completed",f"Done {total} comparisons.\nReports in Source_*_compare dirs.")









    # ------------------ EXPORT XML ------------------
    def prompt_condition_selection(self):
        """
        Pops up a small dialog that lets the user choose which type of
        difference to export.

        Returns
        -------
        str  | None
            One of: "changed", "new", "both", "str_changed"
            None   if the user cancelled the dialog.
        """
        win = tk.Toplevel(self.root)
        win.title("Choose what to export")
        win.grab_set()                       # modal
        win.resizable(False, False)

        tk.Label(
            win, text="What kind of differences do you want to export?",
            font=("Arial", 11, "bold")
        ).pack(padx=15, pady=10, anchor="w")

        choice_var = tk.StringVar(value="both")
        opts = [
            ("Only StrOrigin changed for existing StringId", "changed"),
            ("Only NEW StringIds", "new"),
            ("Both of the above", "both"),
            ("StrOrigin+StringId identical BUT Str changed", "str_changed")
        ]

        for txt, val in opts:
            tk.Radiobutton(
                win, text=txt, variable=choice_var, value=val
            ).pack(anchor="w", padx=25, pady=2)

        btn_fr = tk.Frame(win)
        btn_fr.pack(pady=10)
        def _ok():
            win.destroy()
        def _cancel():
            choice_var.set("")   # sentinel for cancel
            win.destroy()

        tk.Button(btn_fr, text="OK",    width=10, command=_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_fr, text="Cancel", width=10, command=_cancel).pack(side=tk.LEFT, padx=5)

        self.root.wait_window(win)
        return choice_var.get() or None



    def start_export_differences_xml(self):
        """
        Allow multiple source folders but exactly ONE target folder.
        Each source will be compared sequentially against the single target.
        """
        if not self.source_folders or len(self.target_folders) != 1:
            messagebox.showerror(
                "Error",
                "Please select at least ONE source folder and exactly ONE target folder."
            )
            return

        # ask which differences to export
        mode = self.prompt_condition_selection()
        if mode not in {"changed", "new", "both", "str_changed"}:
            return  # user cancelled

        # run each source against the single target in background
        tgt_folder = self.target_folders[0]
        threading.Thread(
            target=self.run_export_differences_multiple_sources,
            args=(self.source_folders, tgt_folder, mode),
            daemon=True
        ).start()

    def run_export_differences_multiple_sources(self, sources, target, mode):
        """
        Modified: 
          - No blocking messagebox at the end.
          - All outputs go into one folder: MultiOutput_against_{targetFolderName}
        """
        total = len(sources)
        tgt_name = os.path.basename(target)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(base_dir, f"MultiOutput_against_{tgt_name}")
        os.makedirs(out_dir, exist_ok=True)

        for idx, src in enumerate(sources, start=1):
            self.progress_label.config(
                text=f"[{idx}/{total}] Exporting differences: {os.path.basename(src)} → {tgt_name}"
            )
            self.progress["value"] = (idx - 1) / total * 100
            self.root.update()
            self.export_differences_xml(src, target, mode, out_dir_override=out_dir)

        self.progress["value"] = 100
        self.progress_label.config(text="All difference exports completed")
        # Removed messagebox.showinfo
        

    def export_differences_xml(self, src, tgt, mode, out_dir_override=None):
        from lxml import etree

        self.progress_label.config(text="Exporting XML ...")
        self.progress["value"] = 0
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Source: {src}\nTarget: {tgt}\nMode  : {mode}\n\n")
        self.root.update()

        def build_maps(folder, keep_elements=False):
            sid_to_strorigin = {}
            sid_to_str       = {}
            sid_to_element   = {} if keep_elements else None
            for root_dir, _, files in os.walk(folder):
                for fname in files:
                    if not fname.lower().endswith(".xml"):
                        continue
                    path = os.path.join(root_dir, fname)
                    try:
                        tree = ET.parse(path)
                        r = tree.getroot()
                        for loc in r.findall(".//LocStr"):
                            sid = loc.get("StringId", "")
                            if not sid:
                                continue
                            if sid in sid_to_strorigin:
                                continue
                            sid_to_strorigin[sid] = loc.get("StrOrigin", "")
                            sid_to_str[sid]       = loc.get("Str", "")
                            if keep_elements:
                                sid_to_element[sid] = loc
                    except Exception:
                        pass
            return (sid_to_strorigin, sid_to_str, sid_to_element)

        src_sid_map, src_str_map, _          = build_maps(src, keep_elements=False)
        tgt_sid_map, tgt_str_map, tgt_elem_m = build_maps(tgt, keep_elements=True)

        export_sids = set()
        if mode in {"new", "both"}:
            export_sids.update(set(tgt_sid_map) - set(src_sid_map))
        if mode in {"changed", "both"}:
            common = set(src_sid_map) & set(tgt_sid_map)
            export_sids.update({sid for sid in common if src_sid_map[sid] != tgt_sid_map[sid]})
        if mode == "str_changed":
            common = set(src_sid_map) & set(tgt_sid_map)
            export_sids.update({
                sid for sid in common
                if src_sid_map[sid] == tgt_sid_map[sid] and src_str_map[sid] != tgt_str_map[sid]
            })

        root_el = etree.Element("root")
        total = len(export_sids)
        for i, sid in enumerate(sorted(export_sids)):
            loc = tgt_elem_m[sid]
            root_el.append(etree.fromstring(ET.tostring(loc, encoding="utf-8")))
            if (i + 1) % 100 == 0 or i + 1 == total:
                self.progress["value"] = (i + 1) / max(total, 1) * 100
                self.root.update()

        base_dir   = os.path.dirname(os.path.abspath(__file__))
        src_name   = os.path.basename(src)
        tgt_name   = os.path.basename(tgt)
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir    = out_dir_override or os.path.join(base_dir, f"Source_{src_name}_compare")
        os.makedirs(out_dir, exist_ok=True)
        out_file   = os.path.join(out_dir, f"{src_name}_VS_{tgt_name}_{mode}_diff_{ts}.xml")

        try:
            xml_bytes = etree.tostring(root_el, pretty_print=True, encoding="UTF-8", xml_declaration=True)
            with open(out_file, "wb") as fh:
                fh.write(xml_bytes)
            self.output_text.insert(tk.END, f"Exported {total} <LocStr> nodes to:\n{out_file}\n")
            self.progress_label.config(text="Export finished")
            self.progress["value"] = 100
        except Exception as e:
            self.output_text.insert(tk.END, f"ERROR: {e}\n")
            self.progress_label.config(text="Export failed")

    # --------------- DUPLICATE CHECK ---------------
    def start_check_duplicates(self):
        if len(self.source_folders)!=1 or len(self.target_folders)!=1:
            messagebox.showerror("Error","Select exactly one source and one target for duplicate check.")
            return
        threading.Thread(target=self.check_duplicates_between_source_target, daemon=True).start()

    def check_duplicates_between_source_target(self):
        self.progress_label.config(text="Checking duplicates...")
        self.progress['value']=0
        self.output_text.delete(1.0,tk.END); self.root.update()
        src=self.source_folders[0]; tgt=self.target_folders[0]
        def collect(fld):
            d=defaultdict(list)
            for r,_,fs in os.walk(fld):
                for f in fs:
                    if not f.lower().endswith(".xml"): continue
                    fp=os.path.join(r,f)
                    try:
                        t=ET.parse(fp); rt=t.getroot()
                        fid=rt.get("FileName",os.path.relpath(fp,fld))
                        rel=os.path.relpath(fp,fld)
                        for e in rt.findall(".//LocStr"):
                            so=e.get("StrOrigin","")
                            sid=e.get("StringId","")
                            sv=e.get("Str","")
                            if not so or so==sv: continue
                            d[(so,sid)].append({
                                "file":fid,"rel":rel,
                                "StringId":sid,"StrOrigin":so,"Str":sv
                            })
                    except: pass
            return d
        src_e = collect(src)
        tgt_e = collect(tgt)
        common = set(src_e)&set(tgt_e)
        rpt=[]
        rpt.append("DUPLICATES WITH DIFFERENT Str VALUES")
        rpt.append("="*80)
        rpt.append(f"Source: {src}")
        rpt.append(f"Target: {tgt}")
        rpt.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        cnt=0
        for k in sorted(common):
            for se in src_e[k]:
                for te in tgt_e[k]:
                    if se["Str"]!=te["Str"]:
                        cnt+=1
                        rpt.append(f"File: {se['rel']}")
                        rpt.append(f"   Source: {se['StrOrigin']}/{se['StringId']}/Str=\"{se['Str']}\"")
                        rpt.append(f"   Target: {te['StrOrigin']}/{te['StringId']}/Str=\"{te['Str']}\"")
                        rpt.append("")
        if cnt==0:
            rpt.append("✓ No differing duplicates found.")
        self.output_text.delete(1.0,tk.END)
        self.output_text.insert(tk.END,"\n".join(rpt))
        self.progress['value']=100
        self.progress_label.config(text="Done duplicate check")
        # save
        base=os.path.dirname(__file__)
        td=os.path.basename(tgt)
        sd=os.path.basename(src)
        outd=os.path.join(base,f"Source_{sd}_compare"); os.makedirs(outd,exist_ok=True)
        path=os.path.join(outd,f"{td}_str_diff_duplicates_report.txt")
        with open(path,"w",encoding="utf-8") as f: f.write("\n".join(rpt))
        self.output_text.insert(tk.END,f"\nSaved: {path}\n")
        messagebox.showinfo("Done","Report saved to:\n"+path)







    # ------------------ EXPORT IDENTICAL STRINGS ------------------
    def prompt_identical_match_mode(self):
        """
        Ask user whether to match on Str+StrOrigin+StringId or Str+StrOrigin only.
        """
        win = tk.Toplevel(self.root)
        win.title("Choose match mode")
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text="Select match criteria:", font=("Arial", 11, "bold")).pack(padx=15, pady=10, anchor="w")

        choice_var = tk.StringVar(value="all")
        opts = [
            ("Match on Str + StrOrigin + StringId", "all"),
            ("Match on Str + StrOrigin only", "noid")
        ]
        for txt, val in opts:
            tk.Radiobutton(win, text=txt, variable=choice_var, value=val).pack(anchor="w", padx=25, pady=2)

        btn_fr = tk.Frame(win)
        btn_fr.pack(pady=10)
        def _ok(): win.destroy()
        def _cancel(): choice_var.set(""); win.destroy()

        tk.Button(btn_fr, text="OK", width=10, command=_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_fr, text="Cancel", width=10, command=_cancel).pack(side=tk.LEFT, padx=5)

        self.root.wait_window(win)
        return choice_var.get() or None

    def start_export_identical_strings_xml(self):
        """
        Allow multiple source folders but exactly ONE target folder.
        Each source will be compared sequentially against the single target.
        """
        if not self.source_folders or len(self.target_folders) != 1:
            messagebox.showerror(
                "Error",
                "Please select at least ONE source folder and exactly ONE target folder."
            )
            return

        mode = self.prompt_identical_match_mode()
        if mode not in {"all", "noid"}:
            return

        tgt_folder = self.target_folders[0]
        threading.Thread(
            target=self.run_export_identical_multiple_sources,
            args=(self.source_folders, tgt_folder, mode),
            daemon=True
        ).start()

    def run_export_identical_multiple_sources(self, sources, target, mode):
        """
        Modified:
          - No blocking messagebox at the end.
          - All outputs go into one folder: MultiOutput_against_{targetFolderName}
        """
        total = len(sources)
        tgt_name = os.path.basename(target)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(base_dir, f"MultiOutput_against_{tgt_name}")
        os.makedirs(out_dir, exist_ok=True)

        for idx, src in enumerate(sources, start=1):
            self.progress_label.config(
                text=f"[{idx}/{total}] Exporting identical strings: {os.path.basename(src)} → {tgt_name}"
            )
            self.progress["value"] = (idx - 1) / total * 100
            self.root.update()
            self.export_identical_strings_xml(src, target, mode, out_dir_override=out_dir)

        self.progress["value"] = 100
        self.progress_label.config(text="All identical string exports completed")
        # Removed messagebox.showinfo

    def export_identical_strings_xml(self, src, tgt, mode, out_dir_override=None):
        from lxml import etree

        self.progress_label.config(text="Exporting identical strings XML ...")
        self.progress["value"] = 0
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Source: {src}\nTarget: {tgt}\nMode  : {mode}\n\n")
        self.root.update()

        def collect(folder):
            data = {}
            for root_dir, _, files in os.walk(folder):
                for fname in files:
                    if not fname.lower().endswith(".xml"):
                        continue
                    path = os.path.join(root_dir, fname)
                    try:
                        tree = ET.parse(path)
                        r = tree.getroot()
                        for loc in r.findall(".//LocStr"):
                            sid = loc.get("StringId", "")
                            so  = loc.get("StrOrigin", "")
                            sv  = loc.get("Str", "")
                            key = (sv, so, sid) if mode == "all" else (sv, so)
                            if key not in data:
                                data[key] = loc
                    except Exception:
                        pass
            return data

        src_map = collect(src)
        tgt_map = collect(tgt)

        common_keys = set(src_map) & set(tgt_map)
        filtered_keys = [k for k in common_keys if tgt_map[k].get("Str", "") != tgt_map[k].get("StrOrigin", "")]

        root_el = etree.Element("root")
        total = len(filtered_keys)
        for i, key in enumerate(sorted(filtered_keys)):
            loc = tgt_map[key]
            root_el.append(etree.fromstring(ET.tostring(loc, encoding="utf-8")))
            if (i + 1) % 100 == 0 or i + 1 == total:
                self.progress["value"] = (i + 1) / max(total, 1) * 100
                self.root.update()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        src_name = os.path.basename(src)
        tgt_name = os.path.basename(tgt)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = out_dir_override or os.path.join(base_dir, f"Source_{src_name}_compare")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"{src_name}_VS_{tgt_name}_identical_{mode}_{ts}.xml")

        try:
            xml_bytes = etree.tostring(root_el, pretty_print=True, encoding="UTF-8", xml_declaration=True)
            with open(out_file, "wb") as fh:
                fh.write(xml_bytes)
            self.output_text.insert(tk.END, f"Exported {total} identical <LocStr> nodes (after filter) to:\n{out_file}\n")
            self.progress_label.config(text="Export finished")
            self.progress["value"] = 100
        except Exception as e:
            self.output_text.insert(tk.END, f"ERROR: {e}\n")
            self.progress_label.config(text="Export failed")







    # ---------- TRANSLATION CHANGES & ADDITIONS ----------
    def start_check_translation_changes(self):
        if len(self.source_folders)!=1 or len(self.target_folders)!=1:
            messagebox.showerror("Error","Select exactly one source and one target for translation changes.")
            return
        threading.Thread(target=self.check_translation_changes_between_source_target, daemon=True).start()

    def check_translation_changes_between_source_target(self):
        self.progress_label.config(text="Checking translation changes/additions...")
        self.progress['value']=0
        self.output_text.delete(1.0,tk.END); self.root.update()

        # collect StringId->Str
        def collect(folder):
            fm={}
            for r,_,fs in os.walk(folder):
                for f in fs:
                    if not f.lower().endswith(".xml"): continue
                    fp=os.path.join(r,f)
                    try:
                        t=ET.parse(fp); rt=t.getroot()
                        fid=rt.get("FileName",os.path.relpath(fp,folder))
                        mp={}
                        for e in rt.findall(".//LocStr"):
                            sid=e.get("StringId",""); sv=e.get("Str","")
                            mp[sid]=sv
                        fm[fid]=mp
                    except: pass
            return fm

        src=self.source_folders[0]; tgt=self.target_folders[0]
        src_map, tgt_map = collect(src), collect(tgt)
        common_files = set(src_map)&set(tgt_map)
        tot = len(common_files); done=0

        total_changes=0; total_additions=0; total_identical_additions=0
        total_change_chars=0; total_change_words=0
        total_add_chars=0; total_add_words=0
        total_ident_add_chars=0; total_ident_add_words=0

        details=[]
        for fid in sorted(common_files):
            done+=1
            p = done/tot*100
            self.progress['value']=p
            self.progress_label.config(text=f"{done}/{tot} : {fid}")
            self.root.update()

            src_dict = src_map[fid]
            tgt_dict = tgt_map[fid]
            src_vals = set(src_dict.values())

            diffs=[]; adds=[]; idents=[]
            for sid in set(src_dict)&set(tgt_dict):
                if src_dict[sid]!=tgt_dict[sid]:
                    diffs.append({
                        "StringId":sid,
                        "SourceStr":src_dict[sid],
                        "TargetStr":tgt_dict[sid]
                    })
                    total_change_chars += len(tgt_dict[sid])
                    total_change_words += len(tgt_dict[sid].split())

            for sid in set(tgt_dict)-set(src_dict):
                tv = tgt_dict[sid]
                if tv in src_vals:
                    idents.append({"StringId":sid,"TargetStr":tv})
                    total_ident_add_chars += len(tv)
                    total_ident_add_words += len(tv.split())
                else:
                    adds.append({"StringId":sid,"TargetStr":tv})
                    total_add_chars += len(tv)
                    total_add_words += len(tv.split())

            if diffs:
                total_changes += len(diffs)
                details.append(f"File: \"{fid}\" - CHANGES ({len(diffs)})")
                for d in diffs[:10]:
                    details.append(f"  - {d['StringId']}: \"{d['SourceStr']}\" → \"{d['TargetStr']}\"")
                if len(diffs)>10:
                    details.append(f"    ... and {len(diffs)-10} more changes")
                details.append("")

            if adds:
                total_additions += len(adds)
                details.append(f"File: \"{fid}\" - ADDITIONS ({len(adds)})")
                for a in adds[:10]:
                    details.append(f"  - {a['StringId']}: \"{a['TargetStr']}\"")
                if len(adds)>10:
                    details.append(f"    ... and {len(adds)-10} more additions")
                details.append("")

            if idents:
                total_identical_additions += len(idents)
                details.append(f"File: \"{fid}\" - IDENTICAL ADDITIONS ({len(idents)})")
                for ii in idents[:10]:
                    details.append(f"  - {ii['StringId']}: \"{ii['TargetStr']}\"")
                if len(idents)>10:
                    details.append(f"    ... and {len(idents)-10} more identical additions")
                details.append("")

        # build summary & report
        rpt=[]
        rpt.append("TRANSLATION (Str) CHANGES & ADDITIONS REPORT")
        rpt.append("="*80)
        rpt.append(f"Source: {src}")
        rpt.append(f"Target: {tgt}")
        rpt.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # SUMMARY
        grand_words = total_change_words + total_add_words + total_ident_add_words
        rpt.append("SUMMARY")
        rpt.append("-"*80)
        rpt.append(f"Total files compared   : {tot}")
        rpt.append(f"Grand total words to recheck or retranslate : {grand_words}")
        rpt.append(f"Total words to retranslate (changes + new additions) : {total_change_words + total_add_words}")
        rpt.append(f"Total words to recheck      (changes + identical additions): {total_change_words + total_ident_add_words}")
        rpt.append("")
        # char stats
        rpt.append("Character counts:")
        rpt.append(f"  - changed chars   (changes)       : {total_change_chars}")
        rpt.append(f"  - added chars     (new additions) : {total_add_chars}")
        rpt.append(f"  - identical added chars           : {total_ident_add_chars}")
        rpt.append(f"  - GRAND total chars              : {total_change_chars + total_add_chars + total_ident_add_chars}")
        rpt.append("")

        # DETAILS
        if details:
            rpt.append("DETAILS")
            rpt.append("-"*80)
            rpt.extend(details)
        else:
            rpt.append("✓ No translation changes or additions detected.\n")

        # output
        self.output_text.delete(1.0,tk.END)
        self.output_text.insert(tk.END, "\n".join(rpt))
        self.progress['value']=100
        self.progress_label.config(text="Translation check done")
        self.root.update()

        # save
        base=os.path.dirname(__file__)
        td=os.path.basename(tgt); sd=os.path.basename(src)
        od=os.path.join(base,f"Source_{sd}_compare"); os.makedirs(od,exist_ok=True)
        path=os.path.join(od,f"{td}_translation_changes_additions_report.txt")
        with open(path,"w",encoding="utf-8") as f: f.write("\n".join(rpt))
        self.output_text.insert(tk.END,f"\nSaved: {path}\n")
        messagebox.showinfo("Done","Report saved to:\n"+path)

    # ---------- STRORIGIN CHANGES & ADDITIONS with FUZZY ----------
    def start_check_strorigin_changes(self):
        if len(self.source_folders)!=1 or len(self.target_folders)!=1:
            messagebox.showerror("Error","Select exactly one source and one target for StrOrigin check.")
            return
        threading.Thread(target=self.check_strorigin_changes_between_source_target,
                         daemon=True).start()

    def calculate_text_similarity(self, a, b):
        if not self.embedding_model or not a or not b:
            return 0.0
        emb1 = self.embedding_model.encode([a], convert_to_numpy=True)
        emb2 = self.embedding_model.encode([b], convert_to_numpy=True)
        faiss.normalize_L2(emb1)
        faiss.normalize_L2(emb2)
        return float(np.dot(emb1[0], emb2[0]))

    def check_strorigin_changes_between_source_target(self):
        self.progress_label.config(text="Checking StrOrigin changes/additions...")
        self.progress['value']=0
        self.output_text.delete(1.0,tk.END); self.root.update()

        def collect(folder):
            fm = {}
            for r,_,fs in os.walk(folder):
                for f in fs:
                    if not f.lower().endswith(".xml"): continue
                    fp=os.path.join(r,f)
                    try:
                        t=ET.parse(fp); rt=t.getroot()
                        fid=rt.get("FileName",os.path.relpath(fp,folder))
                        mp={}
                        for e in rt.findall(".//LocStr"):
                            sid=e.get("StringId","")
                            so=e.get("StrOrigin","")
                            mp[sid]=so
                        fm[fid]=mp
                    except: pass
            return fm

        src=self.source_folders[0]; tgt=self.target_folders[0]
        src_map, tgt_map = collect(src), collect(tgt)
        common_files = set(src_map)&set(tgt_map)
        tot = len(common_files); done=0

        total_changes=0; total_additions=0; total_identical_additions=0
        total_change_words=0; total_add_words=0; total_ident_add_words=0
        fuzzy_low_words=0; fuzzy_mid_words=0

        file_change_counts = defaultdict(int)  # track changes per file

        details=[]
        for fid in sorted(common_files):
            done+=1
            p=done/tot*100
            self.progress['value']=p
            self.progress_label.config(text=f"{done}/{tot} : {fid}")
            self.root.update()

            sdict = src_map[fid]; tdict = tgt_map[fid]
            svals = set(sdict.values())

            diffs=[]; adds=[]; idents=[]
            for sid in set(sdict)&set(tdict):
                so=sdict[sid]; to=tdict[sid]
                if so!=to:
                    diffs.append({"StringId":sid,"Src":so,"Tgt":to})
                    wc = len(to.split()); total_change_words+=wc
                    file_change_counts[fid] += wc
                    sim = self.calculate_text_similarity(so,to)
                    if sim < self.low_sim_threshold:
                        fuzzy_low_words+=wc
                    else:
                        fuzzy_mid_words+=wc

            for sid in set(tdict)-set(sdict):
                to=tdict[sid]
                if to in svals:
                    idents.append({"StringId":sid,"Tgt":to})
                    wc=len(to.split()); total_ident_add_words+=wc
                else:
                    adds.append({"StringId":sid,"Tgt":to})
                    wc=len(to.split()); total_add_words+=wc

            total_changes+=len(diffs)
            total_additions+=len(adds)
            total_identical_additions+=len(idents)

            if diffs:
                details.append(f"File: \"{fid}\" - CHANGES ({len(diffs)})")
                for d in diffs[:10]:
                    details.append(f"  - {d['StringId']}: \"{d['Src']}\" → \"{d['Tgt']}\"")
                if len(diffs)>10:
                    details.append(f"    ... and {len(diffs)-10} more")
                details.append("")
            if adds:
                details.append(f"File: \"{fid}\" - ADDITIONS ({len(adds)})")
                for a in adds[:10]:
                    details.append(f"  - {a['StringId']}: \"{a['Tgt']}\"")
                if len(adds)>10:
                    details.append(f"    ... and {len(adds)-10} more")
                details.append("")
            if idents:
                details.append(f"File: \"{fid}\" - IDENTICAL ADDITIONS ({len(idents)})")
                for i in idents[:10]:
                    details.append(f"  - {i['StringId']}: \"{i['Tgt']}\"")
                if len(idents)>10:
                    details.append(f"    ... and {len(idents)-10} more identical additions")
                details.append("")

        # build report
        rpt=[]
        rpt.append("STRORIGIN CHANGES & ADDITIONS REPORT")
        rpt.append("="*80)
        rpt.append(f"Source: {src}")
        rpt.append(f"Target: {tgt}")
        rpt.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # SUMMARY
        grand_total_words = total_change_words + total_add_words + total_ident_add_words
        rpt.append("SUMMARY")
        rpt.append("-"*80)
        rpt.append(f"Total files compared   : {tot}")
        rpt.append(f"Grand total word count (ALL conditions) : {grand_total_words}")
        rpt.append(f"Grand total word count (Changes below 89% + New Addition) : {fuzzy_low_words + total_add_words}")
        rpt.append(f"Grand total word count (All Changes + New Addition) : {total_change_words + total_add_words}")
        rpt.append(f"Grand total word count (Changes above 89% + Identical Addition) : {fuzzy_mid_words + total_ident_add_words}")
        rpt.append("")
        rpt.append(f"Total words for Changes (all similarity) : {total_change_words}")
        rpt.append(f"Total words for Changes above 89% : {fuzzy_mid_words}")
        rpt.append(f"Total words for Changes below 89% : {fuzzy_low_words}")
        rpt.append(f"Total words for New Addition : {total_add_words}")
        rpt.append(f"Total words for Identical Addition : {total_ident_add_words}")
        rpt.append("")

        # TOP 50 most modified files
        if file_change_counts:
            rpt.append("TOP 50 MOST MODIFIED FILES (by word changes)")
            rpt.append("-"*80)
            for fid, count in sorted(file_change_counts.items(), key=lambda x: x[1], reverse=True)[:50]:
                rpt.append(f"{fid}: {count} words changed")
            rpt.append("")

        # details
        if details:
            rpt.append("DETAILS")
            rpt.append("-"*80)
            rpt.extend(details)
        else:
            rpt.append("✓ No StrOrigin changes or additions detected.\n")

        # output & save
        self.output_text.delete(1.0,tk.END)
        self.output_text.insert(tk.END, "\n".join(rpt))
        self.progress['value']=100
        self.progress_label.config(text="StrOrigin check done")
        self.root.update()

        base=os.path.dirname(__file__)
        sd=os.path.basename(src); td=os.path.basename(tgt)
        od=os.path.join(base,f"Source_{sd}_compare"); os.makedirs(od,exist_ok=True)
        path=os.path.join(od,f"{td}_strorigin_changes_additions_report.txt")
        with open(path,"w",encoding="utf-8") as f: f.write("\n".join(rpt))
        self.output_text.insert(tk.END,f"\nSaved: {path}\n")
        messagebox.showinfo("Done","Report saved to:\n"+path)

def main():
    root = tk.Tk()
    app = TranslationComparer(root)
    root.mainloop()

if __name__ == "__main__":
    main()