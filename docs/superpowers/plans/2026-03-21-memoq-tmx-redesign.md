# MemoQ TMX Redesign — Auto Language Detection Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Completed (2026-03-21)

**Goal:** Replace manual language dropdown with auto-detection from file/folder suffixes, using QuickTranslate's existing `scan_source_for_languages()`.

**Architecture:** Add `SUFFIX_TO_BCP47` mapping + `convert_to_memoq_tmx()` orchestrator to `core/tmx_tools.py`. Update `combine_xmls_to_tmx()` to accept `file_list` + `creation_id` params. Rewrite Section 1 GUI with radio toggle (file/folder) + auto-detect + single convert button.

**Tech Stack:** Python 3, tkinter, lxml, existing `core.source_scanner`

**Spec:** `docs/superpowers/specs/2026-03-21-memoq-tmx-redesign.md`

---

### Task 1: Update `combine_xmls_to_tmx()` — add `file_list` + `creation_id` params

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

- [ ] **Step 1: Update function signature and file discovery**

Change the signature at line 381 from:
```python
def combine_xmls_to_tmx(
    input_folder: str,
    output_file: str,
    target_language: str,
    postprocess: bool = True,
) -> bool:
```
To:
```python
def combine_xmls_to_tmx(
    input_folder: str,
    output_file: str,
    target_language: str,
    postprocess: bool = True,
    file_list: list[str] | None = None,
    creation_id: str | None = None,
) -> bool:
```

At line 394, change:
```python
xml_files = get_all_xml_files(input_folder)
```
To:
```python
xml_files = file_list if file_list else get_all_xml_files(input_folder)
```

- [ ] **Step 2: Use dynamic creation_id**

At line 455-456, change:
```python
creationid="CombinedConversion",
changeid="CombinedConversion"
```
To:
```python
creationid=creation_id or "CombinedConversion",
changeid=creation_id or "CombinedConversion"
```

Same at line 492-493 for description TUs (change `"PAAT"` to `creation_id or "PAAT"`).

- [ ] **Step 3: Verify backwards compatibility**

```bash
python3 -c "
from core.tmx_tools import combine_xmls_to_tmx
import inspect
sig = inspect.signature(combine_xmls_to_tmx)
params = list(sig.parameters.keys())
assert 'file_list' in params
assert 'creation_id' in params
# Defaults should be None (backwards compat)
assert sig.parameters['file_list'].default is None
assert sig.parameters['creation_id'].default is None
print('PASS: signature updated, backwards compatible')
"
```

- [ ] **Step 4: Commit**

```bash
git add core/tmx_tools.py
git commit -m "feat(QuickTranslate): add file_list + creation_id params to combine_xmls_to_tmx"
```

---

### Task 2: Add `SUFFIX_TO_BCP47` mapping + `convert_to_memoq_tmx()` orchestrator

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/tmx_tools.py`

- [ ] **Step 1: Add SUFFIX_TO_BCP47 mapping after existing imports**

Add after the imports section (around line 26):

```python
from pathlib import Path
from datetime import datetime
from .source_scanner import scan_source_for_languages

# QuickTranslate suffix → MemoQ BCP-47 language codes
SUFFIX_TO_BCP47 = {
    "ENG": "en-US",    "FRE": "fr-FR",    "GER": "de-DE",
    "ITA": "it-IT",    "JPN": "ja-JP",    "KOR": "ko",
    "POL": "pl-PL",    "POR-BR": "pt-BR", "RUS": "ru-RU",
    "SPA-ES": "es-ES", "SPA-MX": "es-MX", "TUR": "tr-TR",
    "ZHO-CN": "zh-CN", "ZHO-TW": "zh-TW",
}
```

- [ ] **Step 2: Add orchestrator function at end of file (before Excel section)**

```python
def convert_to_memoq_tmx(input_path: str) -> list[tuple[str, str, bool]]:
    """
    Auto-detect languages from input path, create one MemoQ TMX per language.

    Uses scan_source_for_languages() — same logic as QuickTranslate Tab 1.
    Skips KOR (Korean target produces empty TMX since is_korean_text filters all TUs).

    Returns list of (language_code, output_file, success) tuples.
    """
    path = Path(input_path)
    scan = scan_source_for_languages(path)

    if not scan.lang_files:
        logger.warning("[TMX] No language files detected in: %s", input_path)
        if scan.unrecognized:
            logger.warning("[TMX] %d unrecognized items (no language suffix)", len(scan.unrecognized))
        return []

    creation_id = f"QT_{datetime.now().strftime('%Y%m%d_%H%M')}"

    # Determine output base name
    if path.is_file():
        base_name = path.stem
        output_dir = str(path.parent)
    else:
        base_name = path.name
        output_dir = str(path)

    results = []
    for lang_code, files in scan.lang_files.items():
        upper = lang_code.upper()

        # Skip KOR — would produce empty TMX
        if upper == "KOR":
            logger.info("[TMX] Skipping KOR (source language — would produce empty TMX)")
            continue

        bcp47 = SUFFIX_TO_BCP47.get(upper, lang_code.lower())
        out_file = os.path.join(output_dir, f"{base_name}_{upper}.tmx")

        # Convert Path objects to strings for combine_xmls_to_tmx
        file_list = [str(f) for f in files]

        logger.info("[TMX] Converting %d files for %s → %s (lang=%s)",
                     len(file_list), upper, out_file, bcp47)

        ok = combine_xmls_to_tmx(
            input_folder=output_dir,
            output_file=out_file,
            target_language=bcp47,
            postprocess=True,
            file_list=file_list,
            creation_id=creation_id,
        )
        results.append((upper, out_file, ok))

    return results
```

- [ ] **Step 3: Verify orchestrator imports work**

```bash
python3 -c "
from core.tmx_tools import convert_to_memoq_tmx, SUFFIX_TO_BCP47
assert len(SUFFIX_TO_BCP47) == 14
assert SUFFIX_TO_BCP47['ENG'] == 'en-US'
assert SUFFIX_TO_BCP47['ZHO-CN'] == 'zh-CN'
print('PASS: orchestrator + mapping importable')
"
```

- [ ] **Step 4: Update core/__init__.py exports**

Add `convert_to_memoq_tmx` and `SUFFIX_TO_BCP47` to the imports and `__all__`.

- [ ] **Step 5: Commit**

```bash
git add core/tmx_tools.py core/__init__.py
git commit -m "feat(QuickTranslate): add auto-language TMX orchestrator with SUFFIX_TO_BCP47"
```

---

### Task 3: Rewrite Tab 3 Section 1 GUI — radio toggle + auto-detect

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/tmx_tools_tab.py`

- [ ] **Step 1: Replace Section 1 init and UI**

Replace the `__init__` variables (remove `_target_lang`, add `_mode`, `_path_var`, `_status_var`):

```python
def __init__(self, parent: tk.Widget):
    super().__init__(parent, bg='#f0f0f0')
    self._mode = tk.StringVar(value="folder")
    self._path_var = tk.StringVar()
    self._status_var = tk.StringVar(value="No path selected")
    self._build_ui()
```

Replace Section 1 in `_build_ui()` with:

```python
# Section 1: MemoQ-TMX Conversion
conv_frame = tk.LabelFrame(
    self, text="MemoQ-TMX Conversion",
    font=('Segoe UI', 10, 'bold'),
    bg='#f0f0f0', fg='#555', padx=15, pady=8,
)
conv_frame.pack(fill=tk.X, pady=(0, 12), padx=5)

# Mode toggle (ExtractAnything pattern)
mode_row = tk.Frame(conv_frame, bg='#f0f0f0')
mode_row.pack(fill=tk.X, pady=(0, 6))
tk.Radiobutton(mode_row, text="Folder", variable=self._mode, value="folder",
               bg='#f0f0f0', font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 10))
tk.Radiobutton(mode_row, text="Single File", variable=self._mode, value="file",
               bg='#f0f0f0', font=('Segoe UI', 9)).pack(side=tk.LEFT)

# Path row
path_row = tk.Frame(conv_frame, bg='#f0f0f0')
path_row.pack(fill=tk.X, pady=(0, 6))
tk.Label(path_row, text="Path:", font=('Segoe UI', 9), bg='#f0f0f0').pack(side=tk.LEFT)
tk.Entry(path_row, textvariable=self._path_var, font=('Segoe UI', 9),
         width=50).pack(side=tk.LEFT, padx=(6, 6), fill=tk.X, expand=True)
tk.Button(path_row, text="Browse...", command=self._browse_path,
          font=('Segoe UI', 9), cursor='hand2').pack(side=tk.LEFT)

# Status label (detected languages)
self._status_label = tk.Label(conv_frame, textvariable=self._status_var,
                               font=('Segoe UI', 9), bg='#f0f0f0', fg='#666',
                               anchor='w', wraplength=500)
self._status_label.pack(fill=tk.X, pady=(0, 8))

# Convert button
tk.Button(conv_frame, text="Convert to MemoQ-TMX",
          command=self._on_convert,
          font=('Segoe UI', 9, 'bold'), bg='#4472C4', fg='white',
          relief='flat', padx=14, pady=4, cursor='hand2').pack(anchor='w')
```

- [ ] **Step 2: Replace browse and convert handlers**

Remove: `_browse_source`, `_get_target_lang_code`, `_on_convert_single`, `_on_batch_convert` and the entire batch picker section.

Add new handlers:

```python
def _browse_path(self):
    if self._mode.get() == "folder":
        path = filedialog.askdirectory(title="Select folder with XML/Excel files")
    else:
        path = filedialog.askopenfilename(
            title="Select XML or Excel file",
            filetypes=[("XML files", "*.xml"), ("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")])
    if path:
        self._path_var.set(path)
        self._scan_and_update_status(path)

def _scan_and_update_status(self, path: str):
    """Scan path for languages and update status label."""
    try:
        from pathlib import Path as P
        from core.source_scanner import scan_source_for_languages
        scan = scan_source_for_languages(P(path))
        if scan.lang_files:
            parts = [f"{k.upper()} ({len(v)} files)" for k, v in sorted(scan.lang_files.items())]
            self._status_var.set(f"Detected: {', '.join(parts)}")
            self._status_label.config(fg='#2d7d2d')
        else:
            msg = "No languages detected"
            if scan.unrecognized:
                msg += f" ({len(scan.unrecognized)} unrecognized items)"
            self._status_var.set(msg)
            self._status_label.config(fg='#cc3333')
    except Exception as exc:
        self._status_var.set(f"Scan error: {exc}")
        self._status_label.config(fg='#cc3333')

def _on_convert(self):
    path = self._path_var.get()
    if not path:
        messagebox.showwarning("No Path", "Please select a file or folder first.")
        return

    logger.info("[TMX] Starting MemoQ-TMX conversion: %s", path)

    def _run():
        try:
            results = convert_to_memoq_tmx(path)
            if not results:
                msg = "No languages detected — nothing to convert.\nMake sure files/folders have language suffixes (e.g. FRE/, corrections_GER.xml)"
                self.after(0, lambda: messagebox.showwarning("No Languages", msg))
                return
            summary = []
            for lang, out, ok in results:
                status = "OK" if ok else "FAILED"
                summary.append(f"{lang}: {status}")
            msg = f"MemoQ-TMX conversion complete:\n\n" + "\n".join(summary)
            created = [out for _, out, ok in results if ok]
            if created:
                msg += f"\n\nFiles created in:\n{os.path.dirname(created[0])}"
            self.after(0, lambda: messagebox.showinfo("MemoQ-TMX Complete", msg))
        except Exception as exc:
            err_msg = str(exc)
            logger.error("[TMX] Conversion failed: %s", err_msg, exc_info=True)
            self.after(0, lambda: messagebox.showerror("TMX Error", f"Failed: {err_msg}"))

    threading.Thread(target=_run, daemon=True).start()
```

- [ ] **Step 3: Update imports at top of file**

Replace:
```python
from core.tmx_tools import combine_xmls_to_tmx, batch_tmx_from_folders, clean_and_convert_to_excel
```
With:
```python
from core.tmx_tools import convert_to_memoq_tmx, clean_and_convert_to_excel
```

Remove the `TMX_LANGUAGE_OPTIONS` dict entirely — no longer needed.

- [ ] **Step 4: Verify flake8**

```bash
python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=archive
```
Expected: `0`

- [ ] **Step 5: Commit**

```bash
git add gui/tmx_tools_tab.py
git commit -m "feat(QuickTranslate): redesign TMX tab with auto language detection"
```

---

### Task 4: End-to-End Verification

- [ ] **Step 1: Verify imports**

```bash
python3 -c "
from core.tmx_tools import convert_to_memoq_tmx, SUFFIX_TO_BCP47
from gui.tmx_tools_tab import TMXToolsTab
print('All imports OK')
"
```

- [ ] **Step 2: Verify flake8 clean**

```bash
python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=archive
```

- [ ] **Step 3: Commit all and push**

```bash
git push origin main
```
