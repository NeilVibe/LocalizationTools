# StrOrigin + FileName Match Mode Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 2-pass `strorigin_filename` match mode to QuickTranslate that uses the export folder filepath index as a matching key component alongside StrOrigin and DescOrigin.

**Architecture:** Reuses existing export folder scanning to build a `{StringID.lower(): filepath}` index. The new mode builds two lookup dicts — PASS1 (3-tuple: StrOrigin+filepath+DescOrigin) and PASS2 (2-tuple: StrOrigin+filepath) — and falls through from PASS1 to PASS2 in the merge loop.

**Tech Stack:** Python 3.11+, lxml, tkinter

**Spec:** `docs/superpowers/specs/2026-03-18-strorigin-filename-matchtype-design.md`

---

### Task 1: Add `build_stringid_to_filepath()` to `language_loader.py`

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/language_loader.py:191` (after `build_stringid_to_subfolder`)
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/__init__.py:14-15` (add export)

- [ ] **Step 1: Add the function after `build_stringid_to_subfolder` (line 191)**

Add this function to `core/language_loader.py` after line 191:

```python
def build_stringid_to_filepath(
    export_folder: Path,
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, str]:
    """
    Build StringID -> relative filepath mapping from export folder structure.

    Maps each StringID (lowercased) to its relative file path within the export folder.
    Example: "str_char_001" -> "UI/characterinfo.loc.xml"

    Used by strorigin_filename match mode to add file-context to matching keys.

    Args:
        export_folder: Path to export__ folder
        progress_callback: Optional callback for progress updates

    Returns:
        Dict mapping StringID (lowercased) to relative filepath string
    """
    if not export_folder.exists():
        return {}

    stringid_to_filepath = {}

    xml_files = list(export_folder.rglob("*.loc.xml"))
    total = max(len(xml_files), 1)

    for i, xml_file in enumerate(xml_files, 1):
        if progress_callback and (i == 1 or i % 200 == 0 or i == total):
            progress_callback(f"Indexing filepaths ({i}/{total})...")

        try:
            rel_path = str(xml_file.relative_to(export_folder)).replace("\\", "/")
        except ValueError:
            continue

        try:
            root = parse_xml_file(xml_file)
            for elem in iter_locstr_elements(root):
                string_id = get_attr(elem, STRINGID_ATTRS).strip()
                if string_id:
                    sid_lower = string_id.lower()
                    if sid_lower not in stringid_to_filepath:
                        stringid_to_filepath[sid_lower] = rel_path
        except Exception:
            continue

    return stringid_to_filepath
```

- [ ] **Step 2: Add to `__init__.py` exports**

In `core/__init__.py`, add `build_stringid_to_filepath` to the import at line 14 and the `__all__` list at line 111:

```python
# At line 14-15:
from .language_loader import (
    build_stringid_to_category,
    build_stringid_to_subfolder,
    build_stringid_to_filepath,
)

# In __all__ list:
"build_stringid_to_filepath",
```

- [ ] **Step 3: Verify function works**

Quick smoke test — open a Python shell and test:
```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.language_loader import build_stringid_to_filepath
from pathlib import Path
import config
idx = build_stringid_to_filepath(config.EXPORT_FOLDER)
print(f'Indexed {len(idx)} StringIDs')
# Show a few samples
for k, v in list(idx.items())[:5]:
    print(f'  {k} -> {v}')
"
```

Expected: prints indexed count and sample `sid -> filepath` mappings.

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/language_loader.py \
       RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/__init__.py
git commit -m "feat(qt): add build_stringid_to_filepath for strorigin_filename match mode"
```

---

### Task 2: Add `strorigin_filename` to config and build correction lookups

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/config.py:29-34`
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:119-193`

- [ ] **Step 1: Add mode to `MATCHING_MODES` in `config.py` line 29-34**

```python
MATCHING_MODES = {
    "stringid_only": "StringID-Only (SCRIPT strings)",
    "strict": "StringID + StrOrigin (Strict)",
    "strorigin_only": "StrOrigin Only (non-script, fills duplicates)",
    "strorigin_descorigin": "StrOrigin + DescOrigin",
    "strorigin_filename": "StrOrigin + FileName (2-pass, export filepath)",
}
```

- [ ] **Step 2: Add `stringid_to_filepath` param and new branch to `_build_correction_lookups` in `xml_transfer.py`**

Change the function signature at line 119 to accept the new param:

```python
def _build_correction_lookups(corrections, match_mode, stringid_to_filepath=None):
```

Update docstring at line 129:

```python
        match_mode: One of "strict", "strorigin_only", "stringid_only",
                    "strorigin_descorigin", "strorigin_filename", "fuzzy"
```

Add new `elif` branch BEFORE the `elif match_mode == "fuzzy":` block (before line 184):

```python
    elif match_mode == "strorigin_filename":
        # PASS1: (normalized_StrOrigin, filepath, normalized_DescOrigin) -> list of (corrected, category, index)
        # PASS2: (normalized_StrOrigin, filepath) -> list of (corrected, category, index)
        correction_lookup = defaultdict(list)       # PASS1
        correction_lookup_nospace = defaultdict(list)  # PASS2 (repurposed)
        _fp_index = stringid_to_filepath or {}
        for i, c in enumerate(corrections):
            origin_norm = normalize_for_matching(c.get("str_origin", ""))
            if not origin_norm:
                continue
            sid_lower = c["string_id"].lower()
            filepath = _fp_index.get(sid_lower, "")
            desc_norm = normalize_for_matching(c.get("desc_origin", ""))
            category = c.get("category", "Uncategorized")
            # PASS1: full 3-tuple (only if descorigin is present)
            if desc_norm:
                correction_lookup[(origin_norm, filepath, desc_norm)].append((c["corrected"], category, i))
            # PASS2: always add to 2-tuple dict
            correction_lookup_nospace[(origin_norm, filepath)].append((c["corrected"], category, i))
        return correction_lookup, correction_lookup_nospace
```

Replace the silent `return None, None` at line 193 with:

```python
    raise ValueError(f"Unknown match_mode: {match_mode}")
```

- [ ] **Step 3: Verify the function doesn't break existing modes**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.xml_transfer import _build_correction_lookups
corrections = [{'string_id': 'TEST1', 'str_origin': 'Hello', 'corrected': 'Bonjour', 'desc_origin': 'greeting'}]
fp_index = {'test1': 'UI/test.loc.xml'}
lookup, lookup_pass2 = _build_correction_lookups(corrections, 'strorigin_filename', stringid_to_filepath=fp_index)
print('PASS1 keys:', list(lookup.keys()))
print('PASS2 keys:', list(lookup_pass2.keys()))
# Also verify existing modes still work
l1, l2 = _build_correction_lookups(corrections, 'strict')
print('Strict still works:', len(l1) > 0)
"
```

Expected:
```
PASS1 keys: [('hello', 'UI/test.loc.xml', 'greeting')]
PASS2 keys: [('hello', 'UI/test.loc.xml')]
Strict still works: True
```

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/config.py \
       RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py
git commit -m "feat(qt): add strorigin_filename branch to config and _build_correction_lookups"
```

---

### Task 3: Add `strorigin_filename` matching to `_fast_folder_merge`

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:1110-1120` (signature)
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:1407` (after `strorigin_descorigin` branch, before Phase C)

- [ ] **Step 1: Add `stringid_to_filepath` param to `_fast_folder_merge` signature**

Change line 1110-1120:

```python
def _fast_folder_merge(
    target_files: List[Path],
    corrections: List[Dict],
    correction_lookup,
    correction_lookup_nospace,
    match_mode: str,
    dry_run: bool,
    only_untranslated: bool,
    log_callback=None,
    progress_callback=None,
    stringid_to_filepath: Optional[Dict[str, str]] = None,
) -> Dict:
```

Update docstring at line 1133 to include `"strorigin_filename"` in the match_mode list.

- [ ] **Step 2: Add the `elif match_mode == "strorigin_filename":` branch in the inner loop**

After the `strorigin_descorigin` block (which ends around line 1470 with the desc transfer), add:

```python
            elif match_mode == "strorigin_filename":
                orig = normalize_for_matching(orig_raw)
                if not orig.strip():
                    continue

                sid_lower = sid.lower()
                _fp_index = stringid_to_filepath or {}
                filepath = _fp_index.get(sid_lower, "")
                desc_raw = get_attr(loc, DESCORIGIN_ATTRS)
                desc = normalize_for_matching(desc_raw)

                # PASS1: (StrOrigin, filepath, DescOrigin) — only if desc present
                match_entries = []
                if desc:
                    match_entries = correction_lookup.get((orig, filepath, desc), [])

                # PASS2 fallback: (StrOrigin, filepath)
                if not match_entries:
                    match_entries = correction_lookup_nospace.get((orig, filepath), [])

                if match_entries:
                    new_str, category, idx = match_entries[-1]
                    for _, _, matched_idx in match_entries:
                        correction_matched[matched_idx] = 1
                    counters_matched += 1
                    file_matched += 1

                    old_str = get_attr(loc, STR_ATTRS)

                    if only_untranslated and old_str and not is_korean_text(old_str):
                        counters_skipped_translated += 1
                        orig_correction = corrections[idx]
                        result["unmatched_details"].append({
                            "string_id": sid,
                            "status": "SKIPPED_TRANSLATED",
                            "old": orig_correction.get("str_origin", ""),
                            "new": orig_correction.get("corrected", ""),
                            "raw_attribs": orig_correction.get("raw_attribs", {}),
                        })
                        continue

                    if _is_no_translation(new_str):
                        logger.debug(f"Skipped 'no translation' for StringId={sid}, preserving existing Str")
                        continue

                    new_str = _convert_linebreaks_for_xml(new_str)
                    if new_str != old_str:
                        if not dry_run:
                            loc.set("Str", new_str)
                        counters_updated += 1
                        file_updated += 1
                        changed = True

                    # Desc transfer
                    orig_correction = corrections[idx]
                    if _try_write_desc(loc, orig_correction, dry_run):
                        counters_desc_updated += 1
                        changed = True
```

**IMPORTANT:** `_fp_index = stringid_to_filepath or {}` must go OUTSIDE the inner loop (before `for loc in all_elements:`, near line 1235 alongside other pre-loop setup). Do NOT put it inside the `elif` block — the code snippet above assumes `_fp_index` is already defined in the pre-loop setup:

```python
        # Pre-loop setup (add near line 1235, before the for loop)
        _fp_index = stringid_to_filepath or {}
```

- [ ] **Step 3: Verify fast_folder_merge accepts the new param without breaking**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 -c "
from core.xml_transfer import _fast_folder_merge
# Just verify the function signature accepts the new param
import inspect
sig = inspect.signature(_fast_folder_merge)
print('Params:', list(sig.parameters.keys()))
assert 'stringid_to_filepath' in sig.parameters, 'Missing param!'
print('OK: stringid_to_filepath param present')
"
```

- [ ] **Step 4: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py
git commit -m "feat(qt): add strorigin_filename 2-pass matching to _fast_folder_merge"
```

---

### Task 4: Wire into `transfer_folder_to_folder`

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:1606-1631` (signature)
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:2246-2290` (lookup cache building)
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:2312-2316` (_fast_merge_modes set)
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py:2368-2374` (_fast_folder_merge call)

- [ ] **Step 1: Add `stringid_to_filepath` param to `transfer_folder_to_folder` signature**

Add after line 1610 (`stringid_to_subfolder`):

```python
    stringid_to_filepath: Optional[Dict[str, str]] = None,
```

Update docstring at line 1647 to include `"strorigin_filename"` in the match_mode list.

- [ ] **Step 2: Add lookup cache building for `strorigin_filename` mode**

After the `elif _base_mode == "strorigin_descorigin":` block (line 2262), add:

```python
        elif _base_mode == "strorigin_filename":
            _lookup_cache[_corr_id] = _build_correction_lookups(
                _corr, "strorigin_filename", stringid_to_filepath=stringid_to_filepath
            )
            logger.info(
                f"Built shared strorigin_filename lookup: "
                f"PASS1={len(_lookup_cache[_corr_id][0]):,} keys, "
                f"PASS2={len(_lookup_cache[_corr_id][1]):,} keys"
            )
```

- [ ] **Step 3: Add `strorigin_filename` to `_fast_merge_modes` set**

At line 2312-2316, add to the set:

```python
    _fast_merge_modes = {
        "strict", "strorigin_only", "stringid_only",
        "strict_fuzzy", "strorigin_only_fuzzy",
        "strorigin_descorigin", "strorigin_descorigin_fuzzy",
        "strorigin_filename",
    }
```

- [ ] **Step 4: Pass `stringid_to_filepath` to `_fast_folder_merge` call**

At the call site (line 2368-2374), add the param:

```python
            fast_result = _fast_folder_merge(
                xml_files, corrections,
                lookup, lookup_nospace,
                _fm_mode,
                dry_run, only_untranslated,
                log_callback, progress_callback,
                stringid_to_filepath=stringid_to_filepath,
            )
```

Also check if there's a second `_fast_folder_merge` call for fuzzy mode (~line 2512) — if so, pass `stringid_to_filepath` there too (though fuzzy is not used with this mode, passing `None` is harmless).

- [ ] **Step 5: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/core/xml_transfer.py
git commit -m "feat(qt): wire strorigin_filename into transfer_folder_to_folder pipeline"
```

---

### Task 5: Wire into GUI (`app.py`)

**Files:**
- Modify: `RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/app.py`

Multiple touch points — all in `app.py`:

- [ ] **Step 1: Add radio button (line 349-354)**

Add to the `match_types` list:

```python
        match_types = [
            ("stringid_only", "StringID-Only (SCRIPT)", "SCRIPT categories only - match by StringID"),
            ("strict", "StringID + StrOrigin (STRICT)", "Requires BOTH to match exactly"),
            ("strorigin_only", "StrOrigin Only", "Match by StrOrigin text only - skips Dialog/Sequencer"),
            ("strorigin_descorigin", "StrOrigin + DescOrigin", "Requires BOTH StrOrigin AND DescOrigin to match"),
            ("strorigin_filename", "StrOrigin + FileName (2-pass)", "Match by StrOrigin + export filepath (precise)"),
        ]
```

- [ ] **Step 2: Add `self.stringid_to_filepath` state (line ~183-184)**

Add alongside the existing state vars:

```python
        self.stringid_to_filepath: Optional[Dict[str, str]] = None
```

And in the reset block (~line 2035-2036):

```python
        self.stringid_to_filepath = None
```

- [ ] **Step 3: Add import in `app.py` (line 106)**

```python
from core.language_loader import build_stringid_to_category, build_stringid_to_subfolder, build_stringid_to_filepath
```

- [ ] **Step 4: Build filepath index in `_load_data_if_needed` (after line 2212, INSIDE the export guard block)**

Add INSIDE the same `if need_sequencer:` guard block, right after the subfolder index build at line 2212. This ensures the filepath index is only built when the export folder is needed (not on every data load):

```python
            # Build filepath mapping for strorigin_filename mode
            self._update_status("Building filepath index...")
            self._log("Building filepath index...", 'info')
            self.stringid_to_filepath = build_stringid_to_filepath(export_folder, self._update_status)
            self._log(f"Indexed {len(self.stringid_to_filepath)} StringIDs to filepaths", 'success')
```

- [ ] **Step 5: Update `_on_match_type_changed` (line 1646-1688)**

Change the `if` at line 1654 to include `strorigin_filename`:

```python
        if match_type in ("strict", "strorigin_only", "strorigin_descorigin", "strorigin_filename"):
```

Inside that block, add handling for `strorigin_filename` — similar to `strorigin_descorigin`:

```python
            if match_type == "strorigin_only":
                self.transfer_scope.set("untranslated")
                self.unique_only_frame.pack(fill=tk.X, pady=(4, 0))
                self._bind_mousewheel_recursive(self.unique_only_frame)
                self.strict_non_script_frame.pack_forget()
            elif match_type == "strorigin_filename":
                # No unique-only, no non-script filter, no fuzzy — but show scope + enable transfer
                self.precision_options_frame.pack_forget()
                self.unique_only_frame.pack_forget()
                self.strict_non_script_frame.pack_forget()
                self.transfer_btn.config(state='normal')
                self.transfer_scope_frame.pack(fill=tk.X, pady=(4, 0))
                self._bind_mousewheel_recursive(self.transfer_scope_frame)
            else:
                # strict or strorigin_descorigin
                self.unique_only_frame.pack_forget()
                self.strict_non_script_frame.pack(fill=tk.X, pady=(4, 0))
                self._bind_mousewheel_recursive(self.strict_non_script_frame)
```

Note: `strorigin_filename` hides the precision frame (no fuzzy), hides unique-only, hides non-script. Shows transfer scope only.

- [ ] **Step 6: Update `_update_match_type_availability` (line 1707-1731)**

Add to the `valid` dict:

```python
        valid = {
            "stringid_only": has_id and has_correction,
            "strict": has_id and has_strorigin and has_correction,
            "strorigin_only": has_strorigin and has_correction,
            "strorigin_descorigin": has_strorigin and has_descorigin and has_correction,
            "strorigin_filename": has_strorigin and has_correction,
        }
```

Add to `reasons` dict:

```python
            "strorigin_filename": "Needs StrOrigin + Correction columns + EXPORT folder",
```

Add to `orig_descs` dict (inside the loop at line 1725-1730):

```python
                    "strorigin_filename": "Match by StrOrigin + export filepath (precise, 2-pass)",
```

- [ ] **Step 7: Update `_validate_columns_for_mode` (line 2300-2324)**

Add before `return True`:

```python
        if mt == "strorigin_filename" and not (has_strorigin and has_correction):
            messagebox.showerror("Error", "StrOrigin + FileName mode requires StrOrigin + Correction columns.\n\n"
                                 "Your source files don't have these columns.")
            return False
```

- [ ] **Step 8: Update load condition and transfer mode mapping (line 3174 and 3204-3214)**

At line 3174, extend the condition to load export data for `strorigin_filename`:

```python
            if match_type in ("stringid_only", "strorigin_only", "strorigin_filename") or (match_type in ("strict", "strorigin_descorigin") and non_script_only):
```

After the `stringid_to_subfolder` assignment at line 3178, add:

```python
                stringid_to_filepath = self.stringid_to_filepath
```

Initialize it before the `if` block (alongside line 3172-3173):

```python
            stringid_to_category = None
            stringid_to_subfolder = None
            stringid_to_filepath = None
```

At line 3204-3214, add the new mode mapping:

```python
            elif match_type == "strorigin_filename":
                transfer_match_mode = "strorigin_filename"
```

Add to `transfer_kwargs` at line 3217-3223:

```python
            transfer_kwargs = {
                "stringid_to_category": stringid_to_category,
                "stringid_to_subfolder": stringid_to_subfolder,
                "stringid_to_filepath": stringid_to_filepath,
                "match_mode": transfer_match_mode,
                "dry_run": False,
                "only_untranslated": only_untranslated,
            }
```

- [ ] **Step 9: Commit**

```bash
git add RessourcesForCodingTheProject/NewScripts/QuickTranslate/gui/app.py
git commit -m "feat(qt): wire strorigin_filename match mode into GUI"
```

---

### Task 6: End-to-end smoke test

**Files:** None (testing only)

- [ ] **Step 1: Launch QuickTranslate and verify the new radio button appears**

```bash
cd RessourcesForCodingTheProject/NewScripts/QuickTranslate
python3 main.py
```

Verify:
- "StrOrigin + FileName (2-pass)" radio button appears in Transfer tab
- Selecting it hides precision options, unique-only, and non-script frames
- Transfer scope frame (all/untranslated) is visible

- [ ] **Step 2: Test with real data**

1. Set source folder to a folder with correction XML files
2. Set target folder to the LOC folder
3. Select "StrOrigin + FileName (2-pass)" mode
4. Click TRANSFER
5. Verify:
   - Filepath index build message in log
   - PASS1/PASS2 lookup key counts in log
   - Corrections matched/not-found counts make sense
   - No crashes

- [ ] **Step 3: Compare results with `strorigin_descorigin` mode**

Run the same source→target with `strorigin_descorigin` and `strorigin_filename` modes. The filename mode should:
- Match MORE strings than `strorigin_descorigin` (PASS2 catches DescOrigin mismatches)
- Match FEWER strings than `strorigin_only` (filepath adds precision)

- [ ] **Step 4: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(qt): strorigin_filename smoke test fixes"
```
