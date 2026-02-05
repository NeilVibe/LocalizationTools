
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WHAT THIS TOOL DOES (corrected to your requested logic)

You have two datasets of XML <LocStr .../> nodes:

- TARGET: the place where you want to find strings that contain Korean in Str=""
- SOURCE: the reference set you want to compare against (by key)

Each <LocStr> is identified by a KEY:
    (StrOrigin, StringId)

Your requested process is:

1) Scan TARGET and collect ALL <LocStr> where Str="" contains Korean characters.
   (This is the “Korean set” from TARGET.)

2) Compare those TARGET-Korean keys against SOURCE keys:
   - If the key exists in SOURCE => HIT => discard (filter out)
   - If the key does NOT exist in SOURCE => MISS => keep

3) POST-PROCESS FILTER (NEW):
   - Build an index from MAINLINE EXPORT folder:
       F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__
     mapping StringId -> relative export path
   - Remove any kept node whose StringId is located under:
       System\\Gimmick
       System\\MultiChange

4) Output: a single XML file containing ONLY the kept TARGET <LocStr> nodes
   (concatenated under a <root> wrapper), “clean” output.

RESULT:
- You get an XML of Korean strings that exist in TARGET but are missing from SOURCE
  (by StrOrigin+StringId), minus the ones that live in export__/System/Gimmick or
  export__/System/MultiChange.

NOTES:
- Matching is ONLY by (StrOrigin, StringId). Not by Str text.
- If TARGET has duplicates with same key, we keep the first encountered.
"""

import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import xml.etree.ElementTree as ET
from datetime import datetime
import threading

# Prefer lxml for clean node cloning + pretty output; fallback to ElementTree output if unavailable.
try:
    from lxml import etree as LET
    HAS_LXML = True
except Exception:
    HAS_LXML = False


# -----------------------------
# MAINLINE EXPORT CONFIG (NEW)
# -----------------------------
EXPORT_ROOT = r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__"
EXPORT_FILTER_PREFIXES = (
    os.path.normpath(r"System\Gimmick").lower(),
    os.path.normpath(r"System\MultiChange").lower(),
)

KOREAN_RE = re.compile(r"[\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F]")  # Hangul syllables + Jamo


def has_korean(text: str) -> bool:
    return bool(text and KOREAN_RE.search(text))


def safe_get_attr(elem: ET.Element, name: str) -> str:
    v = elem.get(name)
    return v if v is not None else ""


def iter_locstr_from_file(xml_path: str):
    """
    Yields (key, element) for each <LocStr> in a file.
    key = (StrOrigin, StringId)
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return

    for loc in root.findall(".//LocStr"):
        so = safe_get_attr(loc, "StrOrigin")
        sid = safe_get_attr(loc, "StringId")
        key = (so, sid)
        yield key, loc


def collect_source_keys_from_file(source_file: str):
    """
    Returns set of (StrOrigin, StringId) present in source.
    """
    s = set()
    for key, _loc in iter_locstr_from_file(source_file):
        s.add(key)
    return s


def collect_source_keys_from_folder(source_folder: str):
    """
    Returns set of (StrOrigin, StringId) present in source.
    """
    s = set()
    for root_dir, _, files in os.walk(source_folder):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            fp = os.path.join(root_dir, fn)
            for key, _loc in iter_locstr_from_file(fp):
                s.add(key)
    return s


def collect_target_korean_from_file(target_file: str):
    """
    Returns dict: (StrOrigin, StringId) -> first TARGET LocStr element
    ONLY for LocStr where Str contains Korean.
    """
    m = {}
    for key, loc in iter_locstr_from_file(target_file):
        if key in m:
            continue
        s = safe_get_attr(loc, "Str")
        if has_korean(s):
            m[key] = loc
    return m


def collect_target_korean_from_folder(target_folder: str):
    """
    Returns dict: (StrOrigin, StringId) -> first TARGET LocStr element
    ONLY for LocStr where Str contains Korean.
    """
    m = {}
    for root_dir, _, files in os.walk(target_folder):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            fp = os.path.join(root_dir, fn)
            for key, loc in iter_locstr_from_file(fp):
                if key in m:
                    continue
                s = safe_get_attr(loc, "Str")
                if has_korean(s):
                    m[key] = loc
    return m


# -----------------------------
# EXPORT LOCATION INDEX (NEW)
# -----------------------------
def build_export_stringid_to_relpath_index(export_root: str, progress_cb=None):
    """
    Build index: StringId -> relative path (folder/file) under export_root.
    Uses ElementTree for speed and compatibility.

    If a StringId appears in multiple files, first occurrence wins.
    """
    idx = {}
    export_root = os.path.normpath(export_root)

    if not os.path.isdir(export_root):
        raise FileNotFoundError(f"EXPORT_ROOT not found: {export_root}")

    # Pre-count files for nicer progress (optional)
    xml_files = []
    for r, _, fs in os.walk(export_root):
        for f in fs:
            if f.lower().endswith(".xml"):
                xml_files.append(os.path.join(r, f))

    total = max(len(xml_files), 1)
    for i, fp in enumerate(xml_files, 1):
        if progress_cb and (i == 1 or i % 200 == 0 or i == total):
            pct = int(5 + 20 * (i / total))  # keep this early in the run
            progress_cb(f"Indexing EXPORT (StringId -> path) {i}/{total}...", pct)

        try:
            tree = ET.parse(fp)
            root = tree.getroot()
        except Exception:
            continue

        rel = os.path.relpath(fp, export_root)
        rel_norm = os.path.normpath(rel)

        for loc in root.findall(".//LocStr"):
            sid = loc.get("StringId")
            if not sid:
                continue
            if sid not in idx:
                idx[sid] = rel_norm

    return idx


def is_filtered_by_export_location(string_id: str, export_index: dict) -> bool:
    """
    True if StringId is located under System\\Gimmick or System\\MultiChange in export__.
    """
    if not string_id:
        return False
    rel = export_index.get(string_id)
    if not rel:
        return False
    rel_dir = os.path.dirname(rel)
    rel_dir_norm = os.path.normpath(rel_dir).lower()
    return any(rel_dir_norm.startswith(pref) for pref in EXPORT_FILTER_PREFIXES)


def clone_etree_locstr_to_lxml(loc: ET.Element):
    """
    Convert an ElementTree element to an lxml element by round-tripping bytes.
    """
    b = ET.tostring(loc, encoding="utf-8")
    return LET.fromstring(b)


def write_output_xml(loc_elements, out_path: str):
    """
    loc_elements: list of ET.Element (target nodes)
    Writes <root> ... </root> containing those LocStr nodes.
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if HAS_LXML:
        root = LET.Element("root")
        for loc in loc_elements:
            root.append(clone_etree_locstr_to_lxml(loc))
        xml_bytes = LET.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=True)
        with open(out_path, "wb") as f:
            f.write(xml_bytes)
    else:
        root = ET.Element("root")
        for loc in loc_elements:
            b = ET.tostring(loc, encoding="utf-8")
            root.append(ET.fromstring(b))
        tree = ET.ElementTree(root)
        tree.write(out_path, encoding="utf-8", xml_declaration=True)


def extract_target_korean_missing_in_source(source_path: str, target_path: str, mode: str, progress_cb=None):
    """
    YOUR REQUESTED LOGIC (kept) + NEW POST PROCESS:

    1) Index ALL TARGET LocStr where Str contains Korean => target_korean_map
    2) Collect ALL SOURCE keys => source_keys
    3) Keep only TARGET-Korean keys that are NOT in SOURCE (MISS)
    4) POST: Remove kept nodes whose StringId is located in export__/System/Gimmick or export__/System/MultiChange
    5) Output those TARGET LocStr nodes

    Returns (kept_nodes, stats_dict)
    """
    if mode not in ("file", "folder"):
        raise ValueError("mode must be 'file' or 'folder'")

    if progress_cb:
        progress_cb("Collecting SOURCE keys...", 0)

    if mode == "file":
        source_keys = collect_source_keys_from_file(source_path)
    else:
        source_keys = collect_source_keys_from_folder(source_path)

    if progress_cb:
        progress_cb(f"SOURCE keys: {len(source_keys)}. Collecting TARGET Korean strings...", 20)

    if mode == "file":
        target_korean_map = collect_target_korean_from_file(target_path)
    else:
        target_korean_map = collect_target_korean_from_folder(target_path)

    if progress_cb:
        progress_cb(f"TARGET Korean keys: {len(target_korean_map)}. Filtering MISS (not in SOURCE)...", 50)

    kept = []
    checked = 0
    total = max(len(target_korean_map), 1)

    for key, loc in target_korean_map.items():
        checked += 1
        if key not in source_keys:  # MISS => keep (for now)
            kept.append(loc)

        if progress_cb and (checked % 250 == 0 or checked == total):
            pct = 50 + int(30 * (checked / total))
            progress_cb(f"Checked {checked}/{total}. Kept MISS {len(kept)}...", pct)

    # -----------------------------
    # POST PROCESS (NEW)
    # -----------------------------
    if progress_cb:
        progress_cb(f"Post-process: indexing EXPORT at {EXPORT_ROOT} ...", 82)

    export_index = build_export_stringid_to_relpath_index(EXPORT_ROOT, progress_cb=progress_cb)

    if progress_cb:
        progress_cb("Post-process: filtering by EXPORT location (System/Gimmick, System/MultiChange)...", 88)

    filtered_out_by_export = 0
    kept2 = []
    for i, loc in enumerate(kept, 1):
        sid = safe_get_attr(loc, "StringId")
        if is_filtered_by_export_location(sid, export_index):
            filtered_out_by_export += 1
            continue
        kept2.append(loc)

        if progress_cb and (i % 500 == 0 or i == len(kept)):
            pct = 88 + int(7 * (i / max(len(kept), 1)))
            progress_cb(f"Post-process filtered {filtered_out_by_export}. Remaining {len(kept2)}...", pct)

    stats = {
        "source_keys": len(source_keys),
        "target_korean_keys": len(target_korean_map),
        "kept_missing_before_export_filter": len(kept),
        "filtered_out_by_export_location": filtered_out_by_export,
        "kept_missing": len(kept2),
        "hits_filtered_out": len(target_korean_map) - len(kept),
        "export_index_stringids": len(export_index),
        "export_root": EXPORT_ROOT,
    }

    if progress_cb:
        progress_cb("Done filtering.", 95)

    return kept2, stats


class KoreanMatchExtractorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Extract TARGET Korean LocStr that are MISSING in SOURCE (by StrOrigin+StringId)")
        self.root.geometry("900x650")

        self.mode = tk.StringVar(value="folder")
        self.source_path = tk.StringVar(value="")
        self.target_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="")

        main = tk.Frame(root, padx=14, pady=14)
        main.pack(fill=tk.BOTH, expand=True)

        mode_fr = tk.LabelFrame(main, text="Mode", padx=10, pady=8)
        mode_fr.pack(fill=tk.X)

        tk.Radiobutton(mode_fr, text="Folder mode", variable=self.mode, value="folder", command=self._on_mode_change).pack(side=tk.LEFT, padx=8)
        tk.Radiobutton(mode_fr, text="File mode", variable=self.mode, value="file", command=self._on_mode_change).pack(side=tk.LEFT, padx=8)

        paths_fr = tk.LabelFrame(main, text="Paths", padx=10, pady=10)
        paths_fr.pack(fill=tk.X, pady=10)

        # Source
        tk.Label(paths_fr, text="Source:").grid(row=0, column=0, sticky="w")
        tk.Entry(paths_fr, textvariable=self.source_path).grid(row=0, column=1, sticky="we", padx=6)
        self.btn_source = tk.Button(paths_fr, text="Browse...", command=self._browse_source)
        self.btn_source.grid(row=0, column=2, padx=6)

        # Target
        tk.Label(paths_fr, text="Target:").grid(row=1, column=0, sticky="w")
        tk.Entry(paths_fr, textvariable=self.target_path).grid(row=1, column=1, sticky="we", padx=6)
        self.btn_target = tk.Button(paths_fr, text="Browse...", command=self._browse_target)
        self.btn_target.grid(row=1, column=2, padx=6)

        # Output
        tk.Label(paths_fr, text="Output XML:").grid(row=2, column=0, sticky="w")
        tk.Entry(paths_fr, textvariable=self.output_path).grid(row=2, column=1, sticky="we", padx=6)
        tk.Button(paths_fr, text="Save as...", command=self._browse_output).grid(row=2, column=2, padx=6)

        paths_fr.grid_columnconfigure(1, weight=1)

        act_fr = tk.Frame(main)
        act_fr.pack(fill=tk.X, pady=6)

        tk.Button(act_fr, text="Run", bg="#4CAF50", fg="white", command=self.start).pack(side=tk.LEFT)
        tk.Button(act_fr, text="Quit", command=self.root.destroy).pack(side=tk.LEFT, padx=8)

        prog_fr = tk.Frame(main)
        prog_fr.pack(fill=tk.X, pady=8)
        self.prog_label = tk.Label(prog_fr, text="Ready")
        self.prog_label.pack(anchor="w")
        self.prog = ttk.Progressbar(prog_fr, mode="determinate")
        self.prog.pack(fill=tk.X)

        tk.Label(main, text="Log:").pack(anchor="w")
        self.log = scrolledtext.ScrolledText(main, height=18)
        self.log.pack(fill=tk.BOTH, expand=True)

        self._on_mode_change()

    def _on_mode_change(self):
        m = self.mode.get()
        if m == "folder":
            self.btn_source.config(text="Browse folder...")
            self.btn_target.config(text="Browse folder...")
        else:
            self.btn_source.config(text="Browse file...")
            self.btn_target.config(text="Browse file...")

    def _browse_source(self):
        if self.mode.get() == "folder":
            p = filedialog.askdirectory(title="Select SOURCE folder")
        else:
            p = filedialog.askopenfilename(title="Select SOURCE XML file", filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")])
        if p:
            self.source_path.set(p)
            self._auto_output()

    def _browse_target(self):
        if self.mode.get() == "folder":
            p = filedialog.askdirectory(title="Select TARGET folder")
        else:
            p = filedialog.askopenfilename(title="Select TARGET XML file", filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")])
        if p:
            self.target_path.set(p)
            self._auto_output()

    def _browse_output(self):
        p = filedialog.asksaveasfilename(
            title="Save output XML",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if p:
            self.output_path.set(p)

    def _auto_output(self):
        src = self.source_path.get().strip()
        tgt = self.target_path.get().strip()
        if not src or not tgt:
            return
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src_name = os.path.splitext(os.path.basename(src))[0] if self.mode.get() == "file" else os.path.basename(src.rstrip("/\\"))
        tgt_name = os.path.splitext(os.path.basename(tgt))[0] if self.mode.get() == "file" else os.path.basename(tgt.rstrip("/\\"))
        out_dir = os.path.join(base_dir, "KoreanMissingInSourceExtracts")
        os.makedirs(out_dir, exist_ok=True)
        self.output_path.set(os.path.join(out_dir, f"{tgt_name}_korean_MISSING_in_{src_name}_{ts}.xml"))

    def _progress(self, msg: str, pct: int):
        self.prog_label.config(text=msg)
        self.prog["value"] = max(0, min(100, pct))
        self.root.update()

    def _log(self, s: str):
        self.log.insert(tk.END, s + "\n")
        self.log.see(tk.END)
        self.root.update()

    def start(self):
        src = self.source_path.get().strip()
        tgt = self.target_path.get().strip()
        outp = self.output_path.get().strip()
        m = self.mode.get()

        if not src or not tgt or not outp:
            messagebox.showerror("Error", "Please select Source, Target, and Output path.")
            return

        if m == "file":
            if not os.path.isfile(src) or not os.path.isfile(tgt):
                messagebox.showerror("Error", "In file mode, Source and Target must be files.")
                return
        else:
            if not os.path.isdir(src) or not os.path.isdir(tgt):
                messagebox.showerror("Error", "In folder mode, Source and Target must be folders.")
                return

        self.log.delete(1.0, tk.END)
        self._log(f"Mode  : {m}")
        self._log(f"Source: {src}")
        self._log(f"Target: {tgt}")
        self._log(f"Output: {outp}")
        self._log(f"lxml  : {'YES' if HAS_LXML else 'NO (fallback to ElementTree)'}")
        self._log("")
        self._log("Logic:")
        self._log("  1) Collect ALL TARGET LocStr where Str contains Korean")
        self._log("  2) Remove those whose (StrOrigin,StringId) exists in SOURCE")
        self._log("  3) POST: Remove kept nodes located in export__/System/Gimmick or export__/System/MultiChange")
        self._log("  4) Export remaining TARGET LocStr nodes")
        self._log("")
        self._log(f"EXPORT_ROOT (fixed): {EXPORT_ROOT}")
        self._log("EXPORT filters:")
        self._log("  - System\\Gimmick")
        self._log("  - System\\MultiChange")
        self._log("")

        threading.Thread(target=self._run, args=(src, tgt, outp, m), daemon=True).start()

    def _run(self, src, tgt, outp, mode):
        try:
            self._progress("Starting...", 0)

            kept, stats = extract_target_korean_missing_in_source(
                src, tgt, mode,
                progress_cb=lambda msg, pct: self._progress(msg, pct)
            )

            self._log("STATS")
            self._log("-" * 60)
            self._log(f"SOURCE unique keys (StrOrigin+StringId) : {stats['source_keys']}")
            self._log(f"TARGET Korean unique keys               : {stats['target_korean_keys']}")
            self._log(f"HIT (filtered out; exists in SOURCE)    : {stats['hits_filtered_out']}")
            self._log(f"MISS kept (before export filter)        : {stats['kept_missing_before_export_filter']}")
            self._log(f"Filtered by export location             : {stats['filtered_out_by_export_location']}")
            self._log(f"MISS kept (final)                       : {stats['kept_missing']}")
            self._log(f"EXPORT indexed StringIds                : {stats['export_index_stringids']}")
            self._log("")

            self._progress("Writing output XML...", 98)
            write_output_xml(kept, outp)

            self._progress("Done.", 100)
            self._log(f"Saved: {outp}")
            messagebox.showinfo(
                "Done",
                f"Exported {len(kept)} <LocStr> nodes (TARGET Korean missing in SOURCE, minus export filters).\n\nSaved to:\n{outp}"
            )

        except Exception as e:
            self._progress("Failed.", 0)
            self._log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))


def cli_main(argv):
    """
    Optional CLI usage:
      script.py --mode folder --source /path/src --target /path/tgt --out out.xml
      script.py --mode file   --source a.xml     --target b.xml     --out out.xml

    Output = TARGET LocStr nodes where:
      - TARGET Str contains Korean
      - (StrOrigin,StringId) NOT present in SOURCE
      - POST: StringId NOT located in export__/System/Gimmick or export__/System/MultiChange
    """
    import argparse

    ap = argparse.ArgumentParser(
        description="Extract TARGET LocStr nodes where Str contains Korean and key (StrOrigin+StringId) is MISSING in SOURCE, with export location post-filter."
    )
    ap.add_argument("--mode", choices=["file", "folder"], required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    kept, stats = extract_target_korean_missing_in_source(args.source, args.target, args.mode)
    write_output_xml(kept, args.out)

    print("Done.")
    print(stats)
    print("Saved:", args.out)
    return 0


def main():
    # If user passes CLI args, run CLI; otherwise start GUI.
    if len(sys.argv) > 1:
        sys.exit(cli_main(sys.argv[1:]))

    root = tk.Tk()
    app = KoreanMatchExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()