
from __future__ import annotations
import os, sys, time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# --------------------------------------------------------------------------- #
# Resolve base directory for resources/output (EXE-friendly)
# --------------------------------------------------------------------------- #
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# --------------------------------------------------------------------------- #
# DEFAULT CONFIG – can be overridden via CLI
# --------------------------------------------------------------------------- #
INPUT_LIST_PATH  = str(BASE_DIR / "audiotofind.txt")

BRANCHES = {
    "mainline": r"F:\perforce\cd\mainline\resource\Sound\Windows\English(US)",
    "cd_beta":  r"F:\perforce\cd\cd_beta\resource\Sound\Windows\English(US)",
    "cd_theta": r"F:\perforce\cd\cd_theta\resource\Sound\Windows\English(US)",
    "cd_kappa": r"F:\perforce\cd\cd_kappa\resource\Sound\Windows\English(US)",
    "cd_gamma": r"F:\perforce\cd\cd_gamma\resource\Sound\Windows\English(US)",
    "cd_delta": r"F:\perforce\cd\cd_delta\resource\Sound\Windows\English(US)",
}

SEARCH_ROOT      = BRANCHES["mainline"]
FOUND_OUT_PATH   = str(BASE_DIR / "found_audio_files.txt")
MISSING_OUT_PATH = str(BASE_DIR / "missing_audio_files.txt")
PROGRESS_EVERY   = 10
SELECTED_BRANCH  = "mainline"
# --------------------------------------------------------------------------- #

def branch_selector_gui() -> None:
    """Show a Tkinter window with buttons for each branch."""
    global SEARCH_ROOT, SELECTED_BRANCH
    root = tk.Tk()
    root.title("Select Branch")
    root.geometry("300x300")
    tk.Label(root, text="Select Branch", font=("Arial", 14, "bold")).pack(pady=10)

    def select_branch(branch_name: str):
        global SEARCH_ROOT, SELECTED_BRANCH
        SEARCH_ROOT = BRANCHES[branch_name]
        SELECTED_BRANCH = branch_name
        print("\n[STEP 1] Branch Selection")
        print(f"[INFO] Branch selected: {branch_name}")
        print(f"[INFO] Search root set to: {SEARCH_ROOT}\n")
        root.destroy()

    for branch in BRANCHES:
        tk.Button(root, text=branch, width=20, command=lambda b=branch: select_branch(b)).pack(pady=5)

    root.mainloop()

def parse_cli_args() -> None:
    global INPUT_LIST_PATH, SEARCH_ROOT, SELECTED_BRANCH
    if len(sys.argv) == 1:
        return
    if len(sys.argv) == 3:
        INPUT_LIST_PATH = sys.argv[1]
        SEARCH_ROOT     = sys.argv[2]
        SELECTED_BRANCH = "CLI_Custom"
        print("\n[STEP 1] Branch Selection via CLI")
        print(f"[INFO] Input list path: {INPUT_LIST_PATH}")
        print(f"[INFO] Search root set to: {SEARCH_ROOT}\n")
        return
    exe = os.path.basename(sys.argv[0])
    print(f"Usage: {exe} <wanted_list.txt> <root_directory>")
    sys.exit(1)

def validate_paths() -> None:
    print("[STEP 2] Validating Paths")
    bad = False
    if not os.path.isfile(INPUT_LIST_PATH):
        print(f"[ERROR] Input list file does not exist:\n        {INPUT_LIST_PATH}")
        bad = True
    else:
        print(f"[OK] Input list file found: {INPUT_LIST_PATH}")
    if not os.path.isdir(SEARCH_ROOT):
        print(f"[ERROR] Search root directory does not exist:\n        {SEARCH_ROOT}")
        bad = True
    else:
        print(f"[OK] Search root directory found: {SEARCH_ROOT}")
    if bad:
        sys.exit(1)
    print("[INFO] Path validation successful.\n")

def build_file_index(root: str) -> dict[str, set[str]]:
    print("[STEP 3] Building File Index")
    print(f"[INFO] Indexing files under:\n       {root!r}")
    t0 = time.time()
    index: dict[str, set[str]] = {}
    total_files = 0
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            total_files += 1
            if total_files % PROGRESS_EVERY == 0:
                print(f"        Indexed {total_files:,} files so far...")
            abs_path = os.path.join(dirpath, fname)
            name_lower = fname.lower()
            base_lower, _ = os.path.splitext(name_lower)
            index.setdefault(name_lower, set()).add(abs_path)
            index.setdefault(base_lower, set()).add(abs_path)
    elapsed = time.time() - t0
    print(f"[INFO] Indexing DONE – {total_files:,} files discovered in {elapsed:.1f}s\n")
    return index

def find_files(wanted_path: str, index: dict[str, set[str]]) -> tuple[int, int]:
    print("[STEP 4] Searching for Wanted Files")
    found_cnt = missing_cnt = 0
    with open(FOUND_OUT_PATH, "w", encoding="utf-8", newline="") as fout, \
         open(MISSING_OUT_PATH, "w", encoding="utf-8", newline="") as ferr:
        print(f"[INFO] Processing wanted-file list:\n       {wanted_path!r}\n")
        with open(wanted_path, "r", encoding="utf-8", errors="ignore") as fp:
            total_wanted = sum(1 for _ in fp)
            fp.seek(0)
            processed = 0
            for raw in fp:
                wanted = raw.strip()
                if not wanted:
                    continue
                processed += 1
                key = wanted.lower()
                matches = index.get(key)
                if matches:
                    found_cnt += 1
                    for path in sorted(matches):
                        fout.write(path + "\n")
                        print(f"[FOUND] {wanted}  ->  {path}")
                else:
                    missing_cnt += 1
                    ferr.write(wanted + "\n")
                    print(f"[MISS ] {wanted}")
                if processed % PROGRESS_EVERY == 0:
                    print(f"[PROGRESS] {processed}/{total_wanted} wanted files processed...")
    print("\n[STEP 5] Summary Report")
    print("=================================================")
    print(f"Total wanted files           : {found_cnt + missing_cnt}")
    print(f"Found                        : {found_cnt}")
    print(f"Missing                      : {missing_cnt}")
    print("-------------------------------------------------")
    print(f"Output written to:")
    print(f"   Found   -> {FOUND_OUT_PATH}")
    print(f"   Missing -> {MISSING_OUT_PATH}")
    print("=================================================\n")
    return found_cnt, missing_cnt

def main() -> None:
    branch_selector_gui()
    parse_cli_args()
    validate_paths()
    index = build_file_index(SEARCH_ROOT)
    found_cnt, missing_cnt = find_files(INPUT_LIST_PATH, index)
    print("[STEP 6] Process Completed Successfully ✅\n")

    # Show concise summary in a messagebox
    root = tk.Tk()
    root.withdraw()  # Hide main window
    summary = (
        f"Process completed with branch: {SELECTED_BRANCH}\n"
        f"Found: {found_cnt}\n"
        f"Missing: {missing_cnt}\n"
        f"Search root:\n{SEARCH_ROOT}"
    )
    messagebox.showinfo("Summary", summary)
    root.destroy()

if __name__ == "__main__":
    main()
