from __future__ import annotations
import os
import sys
import time

# --------------------------------------------------------------------------- #
# DEFAULT CONFIG – **your original hard-coded paths are kept**
# --------------------------------------------------------------------------- #
INPUT_LIST_PATH  = r"C:\Users\PEARL\Desktop\CD SCRIPTS\WorkingScripts\audiotofind.txt"
SEARCH_ROOT      = r"F:\perforce\cd\mainline\resource\Sound\Windows\English(US)"
FOUND_OUT_PATH   = "found_audio_files.txt"
MISSING_OUT_PATH = "missing_audio_files.txt"
PROGRESS_EVERY   = 1000      # How often (in file count) to print progress while scanning
# --------------------------------------------------------------------------- #


def parse_cli_args() -> None:
    """
    Accept zero or two CLI args:

        audiofind.py               -> use hard-coded defaults
        audiofind.py <list> <root> -> override the two paths
    """
    global INPUT_LIST_PATH, SEARCH_ROOT

    if len(sys.argv) == 1:
        return                                 # keep defaults
    if len(sys.argv) == 3:
        INPUT_LIST_PATH = sys.argv[1]
        SEARCH_ROOT     = sys.argv[2]
        return

    exe = os.path.basename(sys.argv[0])
    print(f"Usage: {exe} <wanted_list.txt> <root_directory>")
    print("   • With no arguments the script uses the hard-coded defaults.")
    sys.exit(1)


###########################################################################
# 1. Sanity checks
###########################################################################
def validate_paths() -> None:
    bad = False
    if not os.path.isfile(INPUT_LIST_PATH):
        print(f"[ERROR] Input list file does not exist:\n        {INPUT_LIST_PATH}")
        bad = True
    if not os.path.isdir(SEARCH_ROOT):
        print(f"[ERROR] Search root directory does not exist:\n        {SEARCH_ROOT}")
        bad = True
    if bad:
        sys.exit(1)


###########################################################################
# 2. Build an index of every file inside SEARCH_ROOT (case- & ext-tolerant)
###########################################################################
def build_file_index(root: str) -> dict[str, set[str]]:
    """
    Walk SEARCH_ROOT and build a dict mapping:
        • lowercase full filenames          -> {absolute paths}
        • lowercase filenames w/out ext     -> {absolute paths}
    This allows both case-insensitive matching and optional extension matching.
    """
    print(f"[INFO] Indexing files under:\n       {root!r}")
    t0 = time.time()

    index: dict[str, set[str]] = {}   # key -> {absolute paths}
    total_files = 0

    for dirpath, _, filenames in os.walk(root):
        total_files += len(filenames)
        if total_files % PROGRESS_EVERY == 0:
            print(f"        indexed {total_files:,} files so far...")

        for fname in filenames:
            abs_path = os.path.join(dirpath, fname)
            name_lower = fname.lower()
            base_lower, _ = os.path.splitext(name_lower)

            # Full name key (e.g. "laser.wav")
            index.setdefault(name_lower, set()).add(abs_path)
            # Base-name key (e.g. "laser")
            index.setdefault(base_lower, set()).add(abs_path)

    elapsed = time.time() - t0
    print(f"[INFO] Indexing DONE – {total_files:,} files discovered in {elapsed:.1f}s\n")
    return index


###########################################################################
# 3. Process wanted files, write outputs
###########################################################################
def find_files(wanted_path: str, index: dict[str, set[str]]) -> None:
    found_cnt   = 0
    missing_cnt = 0

    with open(FOUND_OUT_PATH,   "w", encoding="utf-8", newline="") as fout, \
         open(MISSING_OUT_PATH, "w", encoding="utf-8", newline="") as ferr:

        print(f"[INFO] Processing wanted-file list:\n       {wanted_path!r}\n")
        with open(wanted_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line_no, raw in enumerate(fp, 1):
                wanted = raw.strip()
                if not wanted:                         # skip blank lines
                    continue

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

    # Summary
    print("\n==================== SUMMARY ====================")
    print(f"Total wanted files           : {found_cnt + missing_cnt}")
    print(f"Found                        : {found_cnt}")
    print(f"Missing                      : {missing_cnt}")
    print("-------------------------------------------------")
    print(f"Output written to:")
    print(f"   Found   -> {os.path.abspath(FOUND_OUT_PATH)}")
    print(f"   Missing -> {os.path.abspath(MISSING_OUT_PATH)}")
    print("=================================================\n")


###########################################################################
# 4. Entry point
###########################################################################
def main() -> None:
    parse_cli_args()      # optional overrides
    validate_paths()
    index = build_file_index(SEARCH_ROOT)
    find_files(INPUT_LIST_PATH, index)


if __name__ == "__main__":
    main()