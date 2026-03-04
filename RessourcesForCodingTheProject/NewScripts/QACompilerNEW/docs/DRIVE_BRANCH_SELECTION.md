# Drive & Branch Selection — QACompiler

## Problem

1. **No drive selection in GUI** — drive letter is only set during Inno Setup installation. If the user's Perforce drive changes, they must reinstall or manually edit `settings.json`.
2. **No path validation** — if the user sets a wrong branch or drive, the generators silently run with empty data and produce garbage output. No error, no stop, no warning.
3. **Installer asks for drive** — unnecessary friction during install. User should configure drive/branch in the GUI at runtime, not during installation.

## Solution

### 1. GUI: Branch + Drive Row (Top of Window)

Mirror the LanguageDataExporter pattern exactly:

```
┌──────────────────────────────────────────────────────────────┐
│  Branch: [cd_beta    ▼]   Drive: [D ▼]   ● PATHS OK        │
├──────────────────────────────────────────────────────────────┤
│  (rest of GUI unchanged)                                     │
```

**Branch Combobox:**
- Default values: `["cd_beta", "mainline", "cd_alpha", "cd_delta", "cd_lambda"]`
- `cd_beta` is default (most common working branch)
- User can type custom branch names (combobox is editable)
- Triggers `config.update_branch()` on selection or Enter key

**Drive Combobox:**
- Default values: `["C", "D", "E", "F", "G"]`
- User can type custom drive letter
- Triggers `config.update_drive()` on selection or Enter key
- Sanitization: strip, uppercase, single alpha char only

**Validation Indicator:**
- Green "PATHS OK" — all critical paths exist on disk
- Red "PATHS NOT FOUND" — one or more critical paths missing
- Updates immediately on branch/drive change

### 2. Path Validation (Critical Paths)

Check these 3 paths (minimum required for any generator):

| Path | Purpose |
|------|---------|
| `RESOURCE_FOLDER` | StaticInfo XMLs (entity data) |
| `LANGUAGE_FOLDER` | loc XMLs (language tables) |
| `EXPORT_FOLDER` | export__ XMLs (StringID/StrOrigin mapping) |

**Validation function in config.py:**
```python
def validate_paths() -> Tuple[bool, List[str]]:
    """Check if critical paths exist. Returns (all_ok, list_of_missing)."""
```

### 3. Hard Block on Invalid Paths

**Generate button:** If `validate_paths()` returns False, show messagebox error and REFUSE to generate. No silent failures.

**Build button:** Same — refuse if paths invalid.

**Generator entry point:** `generate_datasheets()` calls `validate_paths()` at the very top. If False, raises an error immediately. This is the safety net for CLI mode too.

### 4. Settings Persistence

Same as LanguageDataExporter — `settings.json` next to the executable:

```json
{
  "drive_letter": "D",
  "branch": "cd_beta"
}
```

- Auto-saved on every branch/drive change
- Loaded at startup
- No installer involvement needed

### 5. Installer Change

**Remove the drive selection page from Inno Setup.** The installer just installs files — no drive prompt. User configures drive/branch in the GUI on first launch.

Default `settings.json` ships with `{"drive_letter": "D", "branch": "cd_beta"}`.

## Implementation Files

| File | Action |
|------|--------|
| `config.py` | Add `update_drive()`, `validate_paths()`, update `KNOWN_BRANCHES` order |
| `gui/app.py` | Add drive combobox + validation indicator to branch row |
| `generators/__init__.py` | Add `validate_paths()` call at top of `generate_datasheets()` |
| `installer/QACompiler.iss` | Remove drive selection page |
| `build_exe.bat` | Remove drive prompt, ship default settings.json |

## Validation Behavior Summary

| Paths OK? | Generate Button | Build Button | Indicator |
|-----------|----------------|--------------|-----------|
| All exist | Enabled, runs normally | Enabled | Green "PATHS OK" |
| Any missing | Shows error, refuses | Shows error, refuses | Red "PATHS NOT FOUND" |
