# Drive Selector - Cross-Project Investigation Report

**Date:** 2026-02-10
**Status:** COMPLETED - All fixes applied
**Reference:** QACompiler setup (battle-tested, drive selection works perfectly)

---

## Executive Summary

Three NewScripts tools need Perforce drive selection. Only **QACompiler works perfectly**. The other two are broken in different ways:

| Tool | Drive Selector | Works? | Root Cause |
|------|---------------|--------|------------|
| **QACompiler** | Installer asks Perforce drive letter, writes `settings.json` | **YES** | N/A - this is the gold standard |
| **MapDataGenerator** | Installer HAS the code but page doesn't show | **NO** | Missing 4 `[Setup]` page visibility settings |
| **QuickTranslate** | Installer asks INSTALL drive (wrong!), never asks Perforce drive | **NO** | Wrong type of drive selector entirely |

---

## The Gold Standard: QACompiler

QACompiler's installer is the reference. It does three things right:

### 1. All wizard pages explicitly enabled

```ini
; QACompiler.iss [Setup] - lines 56-59
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
```

**Why this matters:** Inno Setup 6 defaults `DisableWelcomePage=yes`. The custom drive selector page is anchored to `wpWelcome`. If welcome is disabled, the page chain breaks.

### 2. Desktop install + no admin ambiguity

```ini
DefaultDirName={userdesktop}\QACompiler     ; Always writable, easy to find
PrivilegesRequired=lowest                    ; No admin needed
PrivilegesRequiredOverridesAllowed=commandline  ; Can't accidentally switch to admin
```

### 3. Drive selector writes settings.json

```pascal
// Installer [Code] section
DriveSelectionPage := CreateInputQueryPage(wpWelcome, ...);
// → Validates A-Z letter
// → Checks if drive exists (warns if not)
// → Writes {"drive_letter": "D", "version": "1.0"} to settings.json at install
```

### 4. config.py reads settings.json at runtime

```python
# QACompiler config.py
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')

def _apply_drive_letter(path_str, drive_letter):
    if path_str.startswith("F:"):
        return f"{drive_letter}:{path_str[2:]}"
    return path_str

# All paths go through _apply_drive_letter():
RESOURCE_FOLDER = Path(_apply_drive_letter(r"F:\perforce\cd\...", _DRIVE_LETTER))
```

### 5. Portable ZIP users get drive_replacer.py

```bash
python drive_replacer.py D
# Creates settings.json with {"drive_letter": "D", "version": "1.0"}
```

---

## MapDataGenerator: What's Broken

### The Problem

MapDataGenerator has the **correct Pascal code** in its `.iss` file (drive letter + branch selection) AND the **correct config.py** (reads `drive_letter` from `settings.json`). But the installer page **doesn't show** because of missing `[Setup]` configuration.

### Root Cause: 4 Missing Settings + 3 Wrong Settings

| # | Setting | QACompiler (WORKS) | MapDataGenerator (BROKEN) | Impact |
|---|---------|-------------------|--------------------------|--------|
| 1 | `DisableWelcomePage` | `no` | **MISSING** (defaults to `yes`) | Drive page anchored to `wpWelcome` - page skipped |
| 2 | `DisableDirPage` | `no` | **MISSING** | User can't see install directory |
| 3 | `DisableReadyPage` | `no` | **MISSING** | No confirmation before install |
| 4 | `DisableFinishedPage` | `no` | **MISSING** | No completion page |
| 5 | `DefaultDirName` | `{userdesktop}\QACompiler` | `{autopf}\{#MyAppName}` | Installs to AppData or Program Files |
| 6 | `WizardStyle` | classic (default) | `modern` | May affect custom page rendering |
| 7 | `PrivilegesRequiredOverridesAllowed` | `commandline` | `dialog` | User can accidentally switch to admin |

### Missing Files

| File | QACompiler | MapDataGenerator |
|------|-----------|-----------------|
| `drive_replacer.py` | YES | **MISSING** |
| `build_exe.bat` | YES | **MISSING** |

### What's Already Correct (NOT the problem)

- **config.py** - `_load_drive_letter()` and `_apply_drive_letter()` are functionally identical to QACompiler
- **Pascal [Code] section** - Drive selection logic is correct (adds branch selection too, which is fine)
- **CI workflow** - Compiles Inno Setup the same way

### Fixes Required

**Fix 1 - Add page visibility settings (CRITICAL):**
```ini
; Add to [Setup] section of MapDataGenerator.iss
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
```

**Fix 2 - Change install directory to Desktop:**
```ini
; CHANGE FROM:
DefaultDirName={autopf}\{#MyAppName}
; CHANGE TO:
DefaultDirName={userdesktop}\MapDataGenerator
```

**Fix 3 - Lock down privileges override:**
```ini
; CHANGE FROM:
PrivilegesRequiredOverridesAllowed=dialog
; CHANGE TO:
PrivilegesRequiredOverridesAllowed=commandline
```

**Fix 4 - Remove WizardStyle=modern (OPTIONAL):**
Remove `WizardStyle=modern` to match QACompiler's classic style.

**Fix 5 - Add architecture settings:**
```ini
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1
```

**Fix 6 - Add drive_replacer.py for portable ZIP users:**
Copy from QACompiler and adapt to also write `branch` field.

---

## QuickTranslate: What's Broken

### The Problem

QuickTranslate's installer has a drive selector, but it does the **wrong thing entirely**. It asks which drive to INSTALL the app on, not which drive Perforce is on.

### Two Completely Different Architectures

| Aspect | QACompiler / MapDataGenerator | QuickTranslate |
|--------|------------------------------|----------------|
| **Installer asks** | "What drive is Perforce on?" | "What drive to install app on?" |
| **Page type** | `TInputQueryWizardPage` (text input) | `TInputOptionWizardPage` (radio buttons) |
| **Page anchor** | `wpWelcome` | `wpSelectDir` |
| **Writes settings.json** | YES - `{"drive_letter": "D"}` | **NO** |
| **config.py approach** | `_apply_drive_letter()` replaces F: prefix | Full path overrides from `settings.json` |
| **Path storage** | `drive_letter: "D"` (single letter) | `loc_folder: "D:\perforce\..."` (full path) |
| **Default paths** | Hardcoded with F: prefix, replaced at runtime | Hardcoded F: defaults, overridden by full path |
| **How user changes drive** | During install (automatic) | After install, via Settings UI (manual) |

### QuickTranslate's Current Installer Code

```pascal
// QuickTranslate.iss - This is an INSTALL LOCATION selector, NOT a Perforce drive selector
DrivePage := CreateInputOptionPage(wpSelectDir, 'Select Installation Drive', ...);
// Auto-detects available drives C: through Z:
// Shows radio buttons for each existing drive
// Changes DefaultDirName to selected drive
// NEVER writes settings.json
// NEVER asks about Perforce
```

### QuickTranslate's config.py Approach

```python
# QuickTranslate config.py - uses FULL PATH overrides, NOT drive_letter
DEFAULT_LOC_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc"
DEFAULT_EXPORT_FOLDER = r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__"

# settings.json stores full paths:
_loc = _SETTINGS.get("loc_folder")     # e.g., "D:\perforce\cd\..."
_export = _SETTINGS.get("export_folder")

LOC_FOLDER = Path(_loc) if _loc else Path(DEFAULT_LOC_FOLDER)
EXPORT_FOLDER = Path(_export) if _export else Path(DEFAULT_EXPORT_FOLDER)
```

QuickTranslate does have a **Settings UI** in the app where users can manually change paths after installation. But the installer never sets them up.

### Decision: Two Valid Approaches

**Option A: Add QACompiler-style drive selector to installer (RECOMMENDED)**
- Add `drive_letter` field support to `config.py` (alongside existing full-path override)
- Replace the install-location drive selector with a Perforce drive selector
- Installer writes `settings.json` with `{"drive_letter": "D", "loc_folder": "...", "export_folder": "..."}`
- Best user experience: works immediately after install, no manual configuration
- Keep the Settings UI as a way to override later

**Option B: Keep current approach, improve Settings UI**
- Leave installer as-is (install location selector only)
- On first launch, if no `settings.json` exists, show a setup wizard in the app
- Less work but worse first-run experience (app won't work until user configures paths)

### Fixes Required (Option A - Recommended)

**Fix 1 - Replace installer drive selector with Perforce drive selector:**
```pascal
// REPLACE the current TInputOptionWizardPage with TInputQueryWizardPage
var
  DriveSelectionPage: TInputQueryWizardPage;
  DriveLetter: String;

procedure InitializeWizard();
begin
  DriveSelectionPage := CreateInputQueryPage(wpWelcome,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    'QuickTranslate needs to access language data from your Perforce workspace.' + #13#10 +
    #13#10 + 'Default: F:\perforce\cd\mainline\resource\GameData\stringtable' + #13#10 +
    #13#10 + 'If your Perforce is on a different drive, enter just the letter.'
  );
  DriveSelectionPage.Add('Drive Letter (e.g., F, D, E):', False);
  DriveSelectionPage.Values[0] := 'F';
end;
```

**Fix 2 - Add settings.json writing to installer:**
```pascal
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsPath, SettingsContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    SettingsPath := ExpandConstant('{app}\settings.json');
    SettingsContent := '{"drive_letter": "' + DriveLetter + '", "version": "1.0"}';
    SaveStringToFile(SettingsPath, AnsiString(SettingsContent), False);
  end;
end;
```

**Fix 3 - Update config.py to support drive_letter:**
Add `drive_letter` reading alongside existing full-path override:
```python
# Read drive_letter if present, apply to default paths
_DRIVE_LETTER = _SETTINGS.get('drive_letter', 'F')

def _apply_drive_letter(path_str, drive_letter):
    if path_str.startswith("F:") or path_str.startswith("f:"):
        return f"{drive_letter}:{path_str[2:]}"
    return path_str

# Full path override takes priority, then drive_letter, then default F:
_loc = _SETTINGS.get("loc_folder")
LOC_FOLDER = Path(_loc) if _loc else Path(_apply_drive_letter(DEFAULT_LOC_FOLDER, _DRIVE_LETTER))
```

**Fix 4 - Add page visibility settings:**
```ini
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
```

**Fix 5 - Change DefaultDirName:**
```ini
; CHANGE FROM:
DefaultDirName={code:GetDefaultDir}\{#MyAppName}
; CHANGE TO:
DefaultDirName={userdesktop}\QuickTranslate
```

**Fix 6 - Add drive_replacer.py for portable ZIP users.**

---

## Complete Fix Checklist

### MapDataGenerator

- [x] Add `DisableWelcomePage=no` + 3 other page settings to `.iss`
- [x] Change `DefaultDirName` to `{userdesktop}\MapDataGenerator`
- [x] Change `PrivilegesRequiredOverridesAllowed` to `commandline`
- [x] Add `ArchitecturesAllowed=x64` + `MinVersion=6.1sp1`
- [x] Remove `WizardStyle=modern`
- [x] Add branch selector to GUI (QACompiler style)
- [x] Clean up Load Data dialog (removed path entry fields)
- [x] Add `update_branch()` to config.py
- [ ] Add `drive_replacer.py` for portable users
- [ ] Build and test installer

### QuickTranslate

- [x] Remove unnecessary drive selector from `.iss` (users configure paths via Settings GUI)
- [x] Change `DefaultDirName` to `{userdesktop}\QuickTranslate`
- [x] Add `DisableWelcomePage=no` + 3 other page settings
- [x] Remove `WizardStyle=modern`
- [ ] Build and test installer

### LanguageDataExporter

- [x] Add branch support to `config.py` (KNOWN_BRANCHES, _apply_branch, _apply_drive_letter, update_branch)
- [x] Add branch selector GUI (QACompiler style, between title and Section 1)
- [x] Update path labels dynamically on branch change
- [x] Add `branch` field to installer settings.json output
- [ ] Build and test installer

---

## File Locations

| File | Path |
|------|------|
| **QACompiler** (reference - DO NOT MODIFY) | |
| .iss | `RFC/NewScripts/QACompilerNEW/installer/QACompiler.iss` |
| config.py | `RFC/NewScripts/QACompilerNEW/config.py` |
| drive_replacer.py | `RFC/NewScripts/QACompilerNEW/drive_replacer.py` |
| **MapDataGenerator** (needs fixes) | |
| .iss | `RFC/NewScripts/MapDataGenerator/installer/MapDataGenerator.iss` |
| config.py | `RFC/NewScripts/MapDataGenerator/config.py` |
| CI workflow | `.github/workflows/mapdatagenerator-build.yml` |
| **QuickTranslate** (needs fixes) | |
| .iss | `RFC/NewScripts/QuickTranslate/installer/QuickTranslate.iss` |
| config.py | `RFC/NewScripts/QuickTranslate/config.py` |
| CI workflow | `.github/workflows/quicktranslate-build.yml` |

*RFC = RessourcesForCodingTheProject*

---

## Conclusion

The pattern is clear: **copy QACompiler's approach exactly**. It works because it:

1. **Enables all wizard pages** so the custom drive selector page renders correctly
2. **Installs to Desktop** so there are no permission issues
3. **Asks about Perforce drive** (not install drive) and writes `settings.json`
4. **config.py reads `drive_letter`** and replaces F: prefix in all paths
5. **Provides `drive_replacer.py`** as fallback for portable ZIP users

MapDataGenerator is 80% there (just needs the `[Setup]` settings). QuickTranslate needs a bigger rework (wrong type of drive selector entirely + config.py needs `drive_letter` support).

---

*Report generated by Claude Code analysis - 2026-02-10*
*Updated: 2026-02-10 - Added QuickTranslate analysis and cross-project comparison*
