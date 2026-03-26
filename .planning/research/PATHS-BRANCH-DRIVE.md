# Branch + Drive Selection: Cross-Project Pattern Analysis

**Researched:** 2026-03-26
**Confidence:** HIGH (direct source code analysis of 3 production apps)
**Purpose:** Inform PATH-01 implementation in LocaNext v13.0

---

## Executive Summary

All 3 NewScripts apps (QACompiler, MapDataGenerator, LanguageDataExporter) share an identical Branch+Drive selection pattern. The pattern is simple, proven, and consistent: two ttk.Combobox widgets (one for branch, one for drive) backed by a `settings.json` file persisted next to the executable. On change, all Perforce-dependent paths are rebuilt from templates using string replacement.

LocaNext should replicate this exact pattern in Svelte 5, adapted for the client-server architecture (selection in frontend, path resolution on backend).

---

## 1. UI Widget Pattern

All three apps use **ttk.Combobox** (dropdown with optional typing).

### QACompiler (top bar, always visible)

```
[QA Compiler Suite]  Branch: [cd_beta  v]  Drive: [D v]  [PATHS OK]
```

- Branch and Drive sit in the **top bar** next to the title, always visible
- Branch combobox: width=18, editable (can type custom branch names)
- Drive combobox: width=4, editable
- Path status label immediately right: green "PATHS OK" or red "PATHS NOT FOUND"
- Changes apply **immediately** on selection (no Save button needed)

### MapDataGenerator (settings dialog)

```
[Settings Dialog]
  Perforce Configuration
    Drive Letter: [D v]  (readonly, A-Z generated)
    Branch:       [cd_beta v]  (editable)
    Preview:      D:\perforce\cd\cd_beta\resource\GameData\...
```

- Drive and Branch are inside a **Settings dialog** (not top bar)
- Drive combobox: **state="readonly"**, values generated A-Z programmatically
- Branch combobox: editable, values from KNOWN_BRANCHES
- **Live path preview** updates as you type (reactive trace_add)
- Changes require clicking "Save" button (dialog-based)
- **Auto-reloads data** after save if drive or branch changed

### LanguageDataExporter (top area, always visible)

```
Branch: [mainline v] | Drive: [F v]  Branch: mainline  Drive: F
```

- Branch and Drive in a **dedicated row** below the title
- Separator between Branch and Drive comboboxes
- Status label shows current values: "Branch: mainline  Drive: F" (green)
- Below: read-only "Configured Paths" section showing resolved LOC, EXPORT, VRS paths
- Changes apply **immediately** on selection

### Recommendation for LocaNext

Use the **QACompiler pattern** (always-visible top bar with immediate feedback). It is the most ergonomic:
- No dialog needed to change branch/drive
- Immediate path validation feedback
- Single row, minimal screen real estate

---

## 2. Branch Discovery

Branches are **hardcoded** as a known list. No runtime discovery.

| App | KNOWN_BRANCHES | Default |
|-----|---------------|---------|
| QACompiler | `["cd_beta", "mainline", "cd_alpha", "cd_delta", "cd_lambda"]` | `cd_beta` |
| MapDataGenerator | `["mainline", "cd_beta", "cd_alpha", "cd_lambda"]` | `mainline` |
| LanguageDataExporter | `["mainline", "cd_beta", "cd_alpha", "cd_lambda"]` | `mainline` |

Key observations:
- QACompiler has `cd_delta` (others do not) and defaults to `cd_beta`
- MapDataGenerator and LDE default to `mainline`
- Comboboxes are **editable** (QACompiler, LDE) or have a known list (MDG), allowing users to type arbitrary branch names not in the list
- The branch name replaces `"mainline"` in all path templates via simple string replacement

### For LocaNext

Use the **union of all branches**: `["mainline", "cd_beta", "cd_alpha", "cd_delta", "cd_lambda"]` with default `cd_beta` (most commonly used in practice). Allow custom typing.

---

## 3. Drive Letter Selection

| App | KNOWN_DRIVES | Default | Generation |
|-----|-------------|---------|------------|
| QACompiler | `["C", "D", "E", "F", "G"]` | `D` | Hardcoded list |
| MapDataGenerator | `A-Z` (all 26) | `F` | `[chr(c) for c in range(ord('A'), ord('Z') + 1)]` |
| LanguageDataExporter | `["D", "E", "F"]` | `F` | Hardcoded list |

Key observations:
- QACompiler defaults to D, others default to F
- MapDataGenerator generates all 26 letters programmatically
- Drive letter is stored as a **single uppercase character** (no colon)
- The drive replaces `"F:"` prefix in all path templates

### Validation

All three apps validate the drive letter identically:

```python
def update_drive(new_drive: str):
    clean = new_drive.strip().rstrip(':').upper()
    if not clean or not clean[0].isalpha():
        print(f"WARNING: Invalid drive letter ignored: {new_drive!r}")
        return
    _DRIVE_LETTER = clean[0]
```

### For LocaNext

Use `["C", "D", "E", "F", "G"]` (QACompiler's list -- practical on Windows workstations). Default to `D`. Since LocaNext runs on WSL/desktop, only common drive letters matter.

---

## 4. Path Template System

All apps use the same pattern: **templates with F: drive and mainline branch as placeholders**, resolved at runtime.

### Template Format (QACompiler)

```python
_PATH_TEMPLATES = {
    "RESOURCE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo",
    "LANGUAGE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    "EXPORT_FOLDER":   r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    # ... 12 total templates
}
```

### Resolution Functions (identical across all 3 apps)

```python
def _apply_drive_letter(path_str: str, drive_letter: str) -> str:
    """Replace F: drive prefix with configured drive letter."""
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter.upper()}:{path_str[2:]}"
    return path_str

def _apply_branch(path_str: str, branch: str) -> str:
    """Replace 'mainline' with configured branch name."""
    return path_str.replace("mainline", branch)

def _build_path(template: str) -> Path:
    """Build Path from template, applying drive letter and branch."""
    return Path(_apply_branch(_apply_drive_letter(template, _DRIVE_LETTER), _BRANCH))
```

### Combined Path Formula

```
{DRIVE}:\perforce\cd\{BRANCH}\resource\GameData\...
```

The common root is always: `{DRIVE}:\perforce\cd\{BRANCH}\`

### Path Rebuild on Change

When either branch or drive changes, ALL path globals are rebuilt:

```python
def _rebuild_paths():
    """Rebuild ALL Perforce-dependent globals from templates."""
    global RESOURCE_FOLDER, LANGUAGE_FOLDER, EXPORT_FOLDER, ...
    RESOURCE_FOLDER = _build_path(_PATH_TEMPLATES["RESOURCE_FOLDER"])
    LANGUAGE_FOLDER = _build_path(_PATH_TEMPLATES["LANGUAGE_FOLDER"])
    # ... all paths
```

### LocaNext Path Templates Needed

Based on existing mock gamedata structure and media resolution requirements:

| Template Key | Path |
|-------------|------|
| `STATICINFO_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\StaticInfo` |
| `LANGUAGE_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\stringtable\loc` |
| `EXPORT_FOLDER` | `F:\perforce\cd\mainline\resource\GameData\stringtable\export__` |
| `TEXTURE_FOLDER` | `F:\perforce\common\mainline\commonresource\ui\texture\image` |
| `AUDIO_FOLDER` | `F:\perforce\cd\mainline\resource\sound\windows\English(US)` |

Note: `TEXTURE_FOLDER` uses `perforce\common` (not `perforce\cd`) -- different root structure. Branch replacement still works via string replace.

---

## 5. Path Validation

### QACompiler (the most complete)

```python
def validate_paths() -> tuple:
    """Check if critical Perforce paths exist.
    Returns: (all_ok: bool, missing: list[str])
    """
    critical = {
        "RESOURCE_FOLDER": RESOURCE_FOLDER,
        "LANGUAGE_FOLDER": LANGUAGE_FOLDER,
        "EXPORT_FOLDER": EXPORT_FOLDER,
    }
    missing = [name for name, path in critical.items() if not path.exists()]
    return (len(missing) == 0, missing)
```

Validation is called:
1. **On startup** (`self._update_path_status()` in `__init__`)
2. **On every branch/drive change** (immediately after `config.update_branch/drive`)
3. **Before any operation** (generate datasheets checks and blocks with error dialog)

### UI Feedback

**Top bar indicator (always visible):**
- Green text: `"PATHS OK"` -- all critical folders exist
- Red text: `"PATHS NOT FOUND"` -- at least one missing

**Error dialog (on action attempt):**
```
Path Error
Cannot generate -- paths not found:

  RESOURCE_FOLDER
  LANGUAGE_FOLDER

Check your Branch and Drive settings.
```

### MapDataGenerator

No explicit `validate_paths()` function. Validation happens implicitly when data loading fails. Less robust.

### LanguageDataExporter

Shows resolved paths as labels but does not have an explicit validation indicator. Relies on operation-time errors.

### For LocaNext

Replicate QACompiler's approach:
1. **Persistent status indicator** next to Branch/Drive selectors
2. **Validate on startup, on change, and before operations**
3. **Show which specific paths are missing** (not just "error")
4. **API endpoint** for backend validation: POST `/api/paths/validate` returns `{ok: bool, missing: [{name, path}]}`

---

## 6. Error States

| Error | QACompiler | MDG | LDE |
|-------|-----------|-----|-----|
| Missing drive | Red "PATHS NOT FOUND" + blocks operations | Silent until data load fails | Silent until export fails |
| Wrong branch | Red "PATHS NOT FOUND" | Preview shows wrong path | Path labels update (user can see) |
| Partial data | Lists specific missing folders | No specific feedback | No specific feedback |
| Invalid drive letter | Ignored with warning log | Ignored with warning log | Ignored with warning log |
| Empty branch | Silently skipped | Falls back to "mainline" | Silently skipped |

### For LocaNext

Implement all QACompiler error states plus:
- **Color-coded per-path status** (like LDE's path info section but with checkmarks/X marks)
- Toast notification on change: "Paths updated. 3/3 OK" or "Paths updated. 1/3 missing: TEXTURE_FOLDER"

---

## 7. Persistence Mechanism

All three apps persist to **`settings.json`** next to the executable.

### File Format

```json
{
  "drive_letter": "D",
  "branch": "cd_beta"
}
```

### Persistence Flow

1. **Load on startup**: `config.py` reads `settings.json` at module import time
2. **Save on change**: GUI calls `config.update_branch()` / `config.update_drive()` which:
   - Updates the global variable
   - Rebuilds all paths
   - Saves essential keys to `settings.json`
3. **Essential keys only**: QACompiler saves only `drive_letter` + `branch` (not computed paths)

### QACompiler save logic

```python
def _save_settings(settings_dict: dict):
    """Save only essential keys to settings.json."""
    essential = {k: settings_dict[k] for k in ("drive_letter", "branch") if k in settings_dict}
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(essential, f, indent=2)
```

### MapDataGenerator (more complex)

Uses a `Settings` dataclass with ALL preferences (font, language, search, etc.) serialized together. Has a migration system for old `mdg_settings.json` files.

### Installer Integration

All apps have a `drive_replacer.py` that the Windows installer calls during build:

```bash
python drive_replacer.py D dist/QACompiler/settings.json
```

This pre-configures the drive letter for the target machine.

### For LocaNext

- Store in LocaNext's own `settings.json` or in the database user preferences table
- Since LocaNext has a backend, persist via API: `PUT /api/settings/perforce {branch, drive_letter}`
- Frontend stores in reactive state, backend stores in DB/JSON
- Load on app startup via API call

---

## 8. Architecture for LocaNext (Svelte 5 + FastAPI)

### Frontend (Svelte 5)

```svelte
<!-- BranchDriveSelector.svelte -->
<script>
  let branch = $state('cd_beta');
  let drive = $state('D');
  let pathStatus = $state({ ok: false, missing: [] });

  const KNOWN_BRANCHES = ['mainline', 'cd_beta', 'cd_alpha', 'cd_delta', 'cd_lambda'];
  const KNOWN_DRIVES = ['C', 'D', 'E', 'F', 'G'];

  async function onSelectionChange() {
    const res = await fetch('/api/settings/perforce', {
      method: 'PUT',
      body: JSON.stringify({ branch, drive_letter: drive })
    });
    // Validate paths after update
    const validation = await fetch('/api/paths/validate');
    pathStatus = await validation.json();
  }
</script>

<div class="branch-drive-bar">
  <label>Branch:</label>
  <select bind:value={branch} onchange={onSelectionChange}>
    {#each KNOWN_BRANCHES as b (b)}
      <option value={b}>{b}</option>
    {/each}
  </select>

  <label>Drive:</label>
  <select bind:value={drive} onchange={onSelectionChange}>
    {#each KNOWN_DRIVES as d (d)}
      <option value={d}>{d}:</option>
    {/each}
  </select>

  <span class="status" class:ok={pathStatus.ok} class:error={!pathStatus.ok}>
    {pathStatus.ok ? 'PATHS OK' : `PATHS NOT FOUND (${pathStatus.missing.length})`}
  </span>
</div>
```

### Backend (FastAPI)

```python
# Path templates (same as QACompiler/MDG/LDE)
_PATH_TEMPLATES = {
    "STATICINFO_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo",
    "LANGUAGE_FOLDER": r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    "TEXTURE_FOLDER": r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    "AUDIO_FOLDER": r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
}

@router.put("/api/settings/perforce")
async def update_perforce_settings(branch: str, drive_letter: str):
    # Validate, rebuild paths, persist
    ...

@router.get("/api/paths/validate")
async def validate_paths():
    missing = [name for name, path in resolved_paths.items() if not path.exists()]
    return {"ok": len(missing) == 0, "missing": missing}
```

---

## 9. Key Constants to Replicate

### From QACompiler config.py

```python
KNOWN_BRANCHES = ["cd_beta", "mainline", "cd_alpha", "cd_delta", "cd_lambda"]
KNOWN_DRIVES = ["C", "D", "E", "F", "G"]

# Default values
DEFAULT_BRANCH = "cd_beta"
DEFAULT_DRIVE = "D"
```

### Path template root pattern

```
{DRIVE}:\perforce\cd\{BRANCH}\resource\...     (game data)
{DRIVE}:\perforce\common\{BRANCH}\...          (common resources like textures)
```

---

## 10. Critical Implementation Details

1. **String replacement order matters**: Apply drive FIRST, then branch. Both functions are pure string operations.

2. **Branch replacement is global**: `path_str.replace("mainline", branch)` replaces ALL occurrences. This works because "mainline" only appears once in each template (as the branch segment).

3. **Drive replacement is prefix-only**: Only replaces if path starts with `F:` or `f:`. Safe for paths that don't start with the default drive.

4. **Validation checks folder existence**: `path.exists()` on the resolved Path. Simple, fast, sufficient.

5. **Persistence is immediate**: Every change writes to disk. No "unsaved changes" state.

6. **No Perforce client dependency**: The apps do NOT query Perforce for available branches. They assume the Perforce workspace is already synced and mapped to the local drive.

7. **The `common` tree has a different root**: Texture paths use `perforce\common\mainline\...` not `perforce\cd\mainline\...`. The branch replacement still works because it's just string replacement of "mainline".

---

## Sources

All findings from direct source code analysis:

| File | Location |
|------|----------|
| QACompiler config.py | `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/config.py` |
| QACompiler gui/app.py | `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/gui/app.py` |
| MapDataGenerator config.py | `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/config.py` |
| MapDataGenerator gui/app.py | `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/gui/app.py` |
| LanguageDataExporter config.py | `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/config.py` |
| LanguageDataExporter gui/app.py | `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/gui/app.py` |
| QACompiler drive_replacer.py | `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/drive_replacer.py` |
| LDE drive_replacer.py | `RessourcesForCodingTheProject/NewScripts/LanguageDataExporter/drive_replacer.py` |
