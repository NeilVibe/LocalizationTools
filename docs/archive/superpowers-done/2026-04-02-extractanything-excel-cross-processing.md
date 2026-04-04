# ExtractAnything Excel Cross-Processing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all ExtractAnything operations (Erase, Add) work identically on both XML and Excel targets, achieving full cross-format parity like QuickTranslate.

**Architecture:** The `input_parser.py` already normalizes XML/Excel into identical `{string_id, str_origin, str_value, raw_attribs}` dicts. Diff/Extract already work cross-format. We extend String Erase and String Add engines to handle Excel targets (remove/append rows) and accept Excel source files, then update GUI file dialogs to allow both formats.

**Tech Stack:** openpyxl (Excel read/write), lxml (XML), xlsxwriter (Excel output reports)

---

### Task 1: Extend string_eraser_engine for Excel targets

**Files:**
- Modify: `RFC/NewScripts/ExtractAnything/core/string_eraser_engine.py`

- [ ] **Step 1: Add `erase_from_excel()` function**

Add after `erase_from_xml()` (after line 155). This function reads an Excel file, filters out matching rows, and writes it back:

```python
def erase_from_excel(
    target_path: Path,
    keys: set[tuple],
    nospace_keys: set[tuple],
    *,
    log_fn=None,
) -> list[dict]:
    """Remove matching rows from an Excel file.

    Reads with openpyxl, filters rows by (StringID, StrOrigin) match,
    writes back with openpyxl (preserving headers).
    Returns a report list of ``{string_id, status, old_value}``.
    """
    import openpyxl
    from .excel_reader import detect_headers
    from .text_utils import convert_linebreaks_for_xml

    try:
        wb = openpyxl.load_workbook(str(target_path))
        ws = wb.active
    except Exception as exc:
        if log_fn:
            log_fn(f"  Cannot open {target_path.name}: {exc}", "warning")
        return []

    hdrs = detect_headers(ws)
    sid_col = hdrs.get("stringid")
    so_col = hdrs.get("strorigin")
    str_col = hdrs.get("str")

    if sid_col is None:
        if log_fn:
            log_fn(f"  {target_path.name}: no StringID column — skipped", "warning")
        wb.close()
        return []

    report: list[dict] = []
    rows_to_delete: list[int] = []  # 1-based row numbers

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
        sid_val = str(row[sid_col].value).strip() if sid_col < len(row) and row[sid_col].value else ""
        if not sid_val:
            continue

        so_val = str(row[so_col].value).strip() if so_col is not None and so_col < len(row) and row[so_col].value else ""
        so_val = convert_linebreaks_for_xml(so_val)

        nt = normalize_text(so_val)
        key = (sid_val.lower(), nt)
        key_nospace = (sid_val.lower(), normalize_nospace(nt))

        if key not in keys and key_nospace not in nospace_keys:
            continue

        # Matched
        str_val = str(row[str_col].value).strip() if str_col is not None and str_col < len(row) and row[str_col].value else ""

        if not str_val:
            report.append({"string_id": sid_val, "status": "ALREADY_EMPTY", "old_value": ""})
            continue

        rows_to_delete.append(row_idx)
        report.append({"string_id": sid_val, "status": "ERASED", "old_value": str_val[:60]})

    if not rows_to_delete:
        wb.close()
        return report

    # Delete rows bottom-up to preserve indices
    for row_idx in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_idx, 1)

    # Backup before write
    bak_path = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        shutil.copy2(target_path, bak_path)
    except Exception as exc:
        logger.error("CANNOT create backup of %s: %s — aborting write", target_path.name, exc)
        if log_fn:
            log_fn(f"  SKIPPED {target_path.name}: backup failed", "error")
        wb.close()
        return []

    wb.save(str(target_path))
    wb.close()
    return report
```

- [ ] **Step 2: Add `load_source_keys_from_file()` dispatcher**

Add after `load_source_keys_from_xml()` (after line 42). Single-file dispatcher that routes XML or Excel:

```python
def load_source_keys_from_file(file_path: Path) -> tuple[set[tuple], set[tuple]]:
    """Load erase keys from a single XML or Excel file (auto-detect by extension)."""
    suffix = file_path.suffix.lower()
    if suffix == ".xml":
        return load_source_keys_from_xml(file_path)
    elif suffix in (".xlsx", ".xls"):
        from .excel_reader import read_erase_keys_from_excel
        return read_erase_keys_from_excel(file_path)
    else:
        logger.warning("Unsupported source file type: %s", file_path.name)
        return set(), set()
```

- [ ] **Step 3: Update `erase_folder_from_file()` to scan XML + Excel targets and use dispatcher**

Replace the existing function to handle both target types:

```python
def erase_folder_from_file(
    source_path: Path,
    target_folder: Path,
    *,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, list[dict]]:
    """Erase entries matching *source_path* from all XML/Excel in *target_folder*."""
    if log_fn:
        log_fn("Loading erase keys from source file...", "header")
    keys, nospace_keys = load_source_keys_from_file(source_path)

    if not keys:
        if log_fn:
            log_fn("No erase keys found in source file.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Source: {source_path.name} — {len(keys)} erase keys")
        log_fn(f"Target folder: {target_folder}")

    # Scan for both XML and Excel targets
    target_files: list[Path] = []
    for pat in ("*.xml", "*.xlsx"):
        target_files.extend(target_folder.rglob(pat))
    target_files = sorted(set(f for f in target_files
                              if not f.name.startswith("~$")
                              and not _is_same_file(source_path, f)))

    total = len(target_files)
    if not target_files:
        if log_fn:
            log_fn("No XML/Excel files in target folder.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Found {total} target files (XML + Excel). Scanning...")

    full_report: list[dict] = []
    total_erased = 0

    for i, fpath in enumerate(target_files, 1):
        if progress_fn:
            progress_fn(i * 100 // total)

        suffix = fpath.suffix.lower()
        if suffix == ".xml":
            file_report = erase_from_xml(fpath, keys, nospace_keys, log_fn=log_fn)
        elif suffix in (".xlsx", ".xls"):
            file_report = erase_from_excel(fpath, keys, nospace_keys, log_fn=log_fn)
        else:
            continue

        if file_report:
            for r in file_report:
                r["target_file"] = fpath.name
            erased = sum(1 for r in file_report if r["status"] == "ERASED")
            total_erased += erased
            full_report.extend(file_report)
            if log_fn:
                log_fn(f"  {fpath.name}: {erased} erased")

    return total_erased, full_report
```

- [ ] **Step 4: Update `erase_folder()` to also scan Excel targets**

Same pattern — add Excel scanning alongside XML:

Replace line 181 `xml_files = sorted(target_folder.rglob("*.xml"))` and the processing loop to scan both formats using the same pattern as the updated `erase_folder_from_file`.

- [ ] **Step 5: Commit**

```bash
git add RFC/NewScripts/ExtractAnything/core/string_eraser_engine.py
git commit -m "feat(ExtractAnything): cross-format erase — XML + Excel targets"
```

---

### Task 2: Extend string_add_engine for Excel source + targets

**Files:**
- Modify: `RFC/NewScripts/ExtractAnything/core/string_add_engine.py`

- [ ] **Step 1: Add `_collect_source_entries_from_file()` dispatcher**

Replace the XML-only `_collect_source_entries()` with a format-aware dispatcher:

```python
def _collect_source_entries_from_file(source_path: Path) -> list[dict]:
    """Parse source XML or Excel and return entries with key field."""
    suffix = source_path.suffix.lower()

    if suffix == ".xml":
        return _collect_source_entries(source_path)
    elif suffix in (".xlsx", ".xls"):
        from .input_parser import parse_input_file
        entries, _ = parse_input_file(source_path)
        # Add the key field expected by add logic
        for entry in entries:
            sid = entry.get("string_id", "")
            so = entry.get("str_origin", "")
            entry["key"] = _make_key(sid, so)
            # Ensure raw_attribs has standard attrs for XML output
            if not entry.get("raw_attribs"):
                entry["raw_attribs"] = {}
            ra = entry["raw_attribs"]
            if "StringId" not in ra and sid:
                ra["StringId"] = sid
            if "StrOrigin" not in ra and so:
                ra["StrOrigin"] = so
            sv = entry.get("str_value", "")
            if "Str" not in ra and sv:
                ra["Str"] = sv
        return entries
    else:
        logger.warning("Unsupported source type: %s", source_path.name)
        return []
```

- [ ] **Step 2: Add `_add_to_excel_target()` function**

Add after `_add_to_target()`. Appends missing rows to an existing Excel file:

```python
def _add_to_excel_target(
    source_entries: list[dict],
    target_path: Path,
    *,
    log_fn=None,
) -> tuple[int, list[dict]]:
    """Diff *source_entries* vs *target_path* (Excel) and append missing rows.

    Returns ``(count_added, report)``.
    """
    import openpyxl
    from .excel_reader import detect_headers
    from .text_utils import convert_linebreaks_for_xml, br_to_newline

    try:
        wb = openpyxl.load_workbook(str(target_path))
        ws = wb.active
    except Exception as exc:
        if log_fn:
            log_fn(f"  Cannot open {target_path.name}: {exc}", "warning")
        return 0, []

    hdrs = detect_headers(ws)
    sid_col = hdrs.get("stringid")
    so_col = hdrs.get("strorigin")
    str_col = hdrs.get("str")

    if sid_col is None:
        if log_fn:
            log_fn(f"  {target_path.name}: no StringID column — skipped", "warning")
        wb.close()
        return 0, []

    # Collect existing keys from target
    target_keys: set[tuple] = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        sid = str(row[sid_col]).strip() if sid_col < len(row) and row[sid_col] else ""
        if not sid:
            continue
        so = str(row[so_col]).strip() if so_col is not None and so_col < len(row) and row[so_col] else ""
        so = convert_linebreaks_for_xml(so)
        target_keys.add(_make_key(sid, so))

    if not target_keys:
        if log_fn:
            log_fn(f"  {target_path.name}: skipped (no entries)", "warning")
        wb.close()
        return 0, []

    # Find missing
    missing = [e for e in source_entries if e["key"] not in target_keys]
    if not missing:
        wb.close()
        return 0, []

    # Append rows — use detected column positions
    report: list[dict] = []
    for entry in missing:
        next_row = ws.max_row + 1
        sid = entry.get("string_id", "")
        so = entry.get("str_origin", "")
        sv = entry.get("str_value", "")

        # Convert <br/> to newline for Excel display
        so_excel = br_to_newline(so)
        sv_excel = br_to_newline(sv)

        # Write into detected column positions
        cell_sid = ws.cell(row=next_row, column=sid_col + 1, value=sid)
        cell_sid.number_format = '@'  # Text format for StringID

        if so_col is not None:
            ws.cell(row=next_row, column=so_col + 1, value=so_excel)
        if str_col is not None:
            ws.cell(row=next_row, column=str_col + 1, value=sv_excel)

        report.append({
            "string_id": sid,
            "status": "ADDED",
            "target_file": target_path.name,
        })

    wb.save(str(target_path))
    wb.close()
    return len(report), report
```

- [ ] **Step 3: Update `add_missing_folder()` to use dispatcher + scan both formats**

```python
def add_missing_folder(
    source_path: Path,
    target_folder: Path,
    *,
    log_fn=None,
    progress_fn=None,
) -> tuple[int, list[dict]]:
    """Add missing entries from *source_path* (XML or Excel) to all XML/Excel in *target_folder*."""
    if log_fn:
        log_fn(f"Source: {source_path.name}")
        log_fn(f"Target folder: {target_folder}")

    source_entries = _collect_source_entries_from_file(source_path)
    if not source_entries:
        if log_fn:
            log_fn("No entries found in source.", "warning")
        return 0, []

    source_entries = _dedup_source_entries(source_entries)
    if log_fn:
        log_fn(f"Source: {len(source_entries):,} unique entries")

    # Scan for both XML and Excel targets
    target_files: list[Path] = []
    for pat in ("*.xml", "*.xlsx"):
        target_files.extend(target_folder.rglob(pat))
    target_files = sorted(set(f for f in target_files
                              if not f.name.startswith("~$")
                              and not _is_same_file(source_path, f)))

    total = len(target_files)
    if not target_files:
        if log_fn:
            log_fn("No XML/Excel files in target folder.", "warning")
        return 0, []

    if log_fn:
        log_fn(f"Found {total} target files (XML + Excel)")

    full_report: list[dict] = []
    total_added = 0

    for i, fpath in enumerate(target_files, 1):
        if progress_fn:
            progress_fn(i * 100 // total)

        suffix = fpath.suffix.lower()
        if suffix == ".xml":
            added, file_report = _add_to_target(source_entries, fpath, log_fn=log_fn)
        elif suffix in (".xlsx", ".xls"):
            added, file_report = _add_to_excel_target(source_entries, fpath, log_fn=log_fn)
        else:
            continue

        if file_report:
            total_added += added
            full_report.extend(file_report)
            if log_fn:
                log_fn(f"  {fpath.name}: {added} added", "success")
        else:
            if log_fn:
                log_fn(f"  {fpath.name}: nothing to add")

    return total_added, full_report
```

- [ ] **Step 4: Commit**

```bash
git add RFC/NewScripts/ExtractAnything/core/string_add_engine.py
git commit -m "feat(ExtractAnything): cross-format add — Excel source + Excel/XML targets"
```

---

### Task 3: Update GUI tabs for cross-format file dialogs

**Files:**
- Modify: `RFC/NewScripts/ExtractAnything/gui/string_eraser_tab.py`
- Modify: `RFC/NewScripts/ExtractAnything/gui/string_add_tab.py`

- [ ] **Step 1: Update StringEraserTab file dialog and labels**

Change `_XML_FILETYPES` to accept both formats and update UI labels:

```python
_CROSS_FILETYPES = [("XML & Excel files", "*.xml *.xlsx"), ("XML files", "*.xml"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
```

Update label frame text from "Source XML" to "Source (XML or Excel)" and "Target XMLs folder" to "Target folder (XML & Excel)". Update the file count in confirmation dialog to count both XML and Excel.

- [ ] **Step 2: Update StringAddTab file dialog and labels**

Same pattern — replace `_XML_FILETYPES` with `_CROSS_FILETYPES`, update labels to reflect cross-format support, update confirmation dialog file count.

- [ ] **Step 3: Commit**

```bash
git add RFC/NewScripts/ExtractAnything/gui/string_eraser_tab.py RFC/NewScripts/ExtractAnything/gui/string_add_tab.py
git commit -m "feat(ExtractAnything): update Str Erase/Add tabs for cross-format dialogs"
```

---

### Task 4: Code review

- [ ] **Step 1: Run code-reviewer agent on all modified files**
- [ ] **Step 2: Fix any issues found**
- [ ] **Step 3: Final commit if needed**
