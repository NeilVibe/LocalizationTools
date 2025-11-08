from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter
from tkinter import Tk, messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename

import pandas as pd


def pick_file_open(prompt: str) -> Path:
    file_path = askopenfilename(
        title=prompt,
        filetypes=(
            ("Excel workbooks", "*.xlsx *.xlsm *.xls"),
            ("All files", "*.*"),
        ),
    )
    if not file_path:
        messagebox.showinfo("Aborted", "Operation cancelled by user.")
        sys.exit(0)
    return Path(file_path)


def pick_file_save(default_name: str) -> Path:
    file_path = asksaveasfilename(
        title="Save filtered SOURCE as...",
        initialfile=default_name,
        defaultextension=".xlsx",
        filetypes=(("Excel workbook", "*.xlsx"),),
        confirmoverwrite=True,
    )
    if not file_path:
        messagebox.showinfo("Aborted", "Operation cancelled by user.")
        sys.exit(0)
    return Path(file_path)


def read_excel(file_path: Path) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path, dtype="object", engine="openpyxl")
    except Exception as exc:
        messagebox.showerror("Read error", f"Could not read\n{file_path}\n\n{exc}")
        sys.exit(1)
    return df.astype(str).fillna("")


def build_target_blob(target_df: pd.DataFrame) -> str:
    # Flatten, strip whitespace, normalise spaces, lower-case
    flattened_iter = (
        str(cell).strip().replace("\xa0", " ") for cell in target_df.values.ravel()
    )
    return "\n".join(flattened_iter).lower()


def filter_source(source_df: pd.DataFrame, target_blob: str) -> pd.DataFrame:
    col_a = source_df.iloc[:, 0].fillna("").astype(str)
    total_rows = len(col_a)
    keep_mask: list[bool] = []

    t0 = perf_counter()
    for idx, original_value in enumerate(col_a, 1):
        probe = original_value.strip().replace("\xa0", " ").lower()
        keep = probe != "" and probe in target_blob
        keep_mask.append(keep)
        print(
            f"[{idx:>6}/{total_rows}] "
            f"{original_value!r:<30} ➜ {'KEEP' if keep else 'DROP'}"
        )
    print(f"\nScanned {total_rows} rows in {perf_counter() - t0:.2f} s\n")

    keep_series = pd.Series(keep_mask, index=source_df.index)
    return source_df[keep_series]


def main() -> None:
    root = Tk()
    root.withdraw()

    print("Select SOURCE workbook ...")
    source_path = pick_file_open("Select SOURCE workbook")

    print("Select TARGET workbook ...")
    target_path = pick_file_open("Select TARGET workbook")

    default_output_name = f"{source_path.stem}_filtered.xlsx"
    print("Choose destination file ...")
    output_path = pick_file_save(default_output_name)

    t_all = perf_counter()

    print(f"\nReading SOURCE : {source_path}")
    source_df = read_excel(source_path)

    print(f"Reading TARGET : {target_path}")
    target_df = read_excel(target_path)

    print("\nBuilding substring-lookup blob from TARGET ...")
    target_blob = build_target_blob(target_df)
    print(f"TARGET text corpus size: {len(target_blob):,} characters\n")

    print("Filtering SOURCE ...")
    filtered_df = filter_source(source_df, target_blob)

    kept = len(filtered_df)
    dropped = len(source_df) - kept
    print(f"Rows kept   : {kept:,}")
    print(f"Rows dropped: {dropped:,}")

    print(f"\nWriting output → {output_path}")
    try:
        filtered_df.to_excel(output_path, index=False, engine="openpyxl")
    except Exception as exc:
        messagebox.showerror("Write error", f"Could not write output file:\n\n{exc}")
        sys.exit(1)

    elapsed = perf_counter() - t_all
    print(f"Done in {elapsed:.2f} s")

    messagebox.showinfo(
        "Finished",
        f"Filtering complete!\n\n"
        f"Rows kept   : {kept:,}\n"
        f"Rows dropped: {dropped:,}\n\n"
        f"Output written to:\n{output_path}"
    )


if __name__ == "__main__":
    main()