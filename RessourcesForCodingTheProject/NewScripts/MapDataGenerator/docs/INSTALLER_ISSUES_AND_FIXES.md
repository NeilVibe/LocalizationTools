# MapDataGenerator Installer Issues and Fixes

This document covers known installer issues for MapDataGenerator, their root causes, and actionable fixes based on comparison with the working QACompiler setup.

---

## Table of Contents

1. [Issue #1: Relative Import Error](#issue-1-relative-import-error)
2. [Issue #2: Missing Drive Selector](#issue-2-missing-drive-selector)
3. [Comparison: QACompiler vs MapDataGenerator](#comparison-qacompiler-vs-mapdatagenerator)
4. [Implementation Steps](#implementation-steps)
5. [References](#references)

---

## Issue #1: Relative Import Error

### Symptom

When running the installed `MapDataGenerator.exe`, the application crashes with:

```
ImportError: attempted relative import with no known parent package
```

### Root Cause

The error originates from `/gui/app.py` which uses a try/except import pattern:

```python
try:
    from config import (...)
    from core.linkage import LinkageResolver, DataMode
    from gui.search_panel import SearchPanel
    # ...
except ImportError:
    from ..config import (...)           # <-- RELATIVE IMPORT
    from ..core.linkage import LinkageResolver, DataMode
    from .search_panel import SearchPanel
    # ...
```

**Why This Fails with PyInstaller:**

1. PyInstaller bundles the application as a frozen executable
2. When running as an EXE, Python's import system doesn't recognize the package hierarchy
3. The `except ImportError` block triggers, attempting relative imports (`from ..config`)
4. Since there's no "parent package" context in the frozen environment, Python raises the error

This is a [well-documented PyInstaller issue](https://github.com/pyinstaller/pyinstaller/issues/2560) - PyInstaller cannot properly handle `__main__.py` entry points with relative imports.

### Solution: Use Absolute Imports Only

**Option A: Remove Relative Import Fallback (Recommended)**

Edit `gui/app.py` and all similar files to use ONLY absolute imports:

```python
# BEFORE (problematic):
try:
    from config import (...)
except ImportError:
    from ..config import (...)  # <-- This causes the PyInstaller error

# AFTER (fixed):
from config import (
    APP_NAME, VERSION, get_settings, save_settings, load_settings,
    get_ui_text, Settings, LANGUAGES, LANGUAGE_NAMES,
    DATA_MODES, DEFAULT_MODE
)
from core.linkage import LinkageResolver, DataMode
from core.language import LanguageManager
from core.search import SearchEngine, SearchResult
from core.audio_handler import AudioHandler
from gui.search_panel import SearchPanel
from gui.result_panel import ResultPanel
from gui.image_viewer import ImageViewer
from gui.audio_viewer import AudioViewer
from gui.map_canvas import MapCanvas
```

**Option B: Ensure `pathex` is Correctly Set in .spec File**

The `.spec` file must include the project root in `pathex` so Python can resolve absolute imports:

```python
# MapDataGenerator.spec
a = Analysis(
    ['main.py'],
    pathex=[str(spec_dir)],  # <-- This is correct, but verify spec_dir resolves properly
    # ...
)
```

**Option C: Use sys.path Manipulation in Entry Point (Like QACompiler)**

QACompiler's `main.py` (line 37) ensures the package is importable:

```python
# Ensure package imports work
sys.path.insert(0, str(Path(__file__).parent))
```

This should be added to MapDataGenerator's `main.py` BEFORE any imports from subpackages.

### Files to Modify (Complete List)

Based on code analysis, these files contain relative imports that will break:

| File | Lines with Relative Imports | Fix Required |
|------|---------------------------|--------------|
| `gui/app.py` | 41-49 (`from ..config`, `from ..core.*`) | Remove entire except block |
| `gui/audio_viewer.py` | 22-23 (`from ..config`, `from ..core.audio_handler`) | Remove except block |
| `gui/map_canvas.py` | 22-24 (`from ..config`, `from ..core.*`) | Remove except block |
| `gui/search_panel.py` | 18 (`from ..config`) | Remove except block |
| `gui/result_panel.py` | 25-26 (`from ..config`, `from ..core.search`) | Remove except block |
| `gui/image_viewer.py` | 20, 29 (`from ..config`, `from ..core.dds_handler`) | Remove except block |
| `core/search.py` | 20 (`from ..utils.filters`) | Remove except block |
| `core/language.py` | 17 (`from ..utils.filters`) | Remove except block |

**Total: 8 files need modification**

---

## Issue #2: Missing Drive Selector

### Symptom

The installer does not ask users which drive their Perforce workspace is on. Users with Perforce on drives other than `F:` cannot use the application without manual configuration.

### Root Cause

The current `MapDataGenerator.iss` Inno Setup script is minimal and lacks the custom wizard page for drive selection that QACompiler has.

**Current MapDataGenerator.iss:**
```inno
[Setup]
DefaultDirName={autopf}\{#MyAppName}
; No drive selection page
; No [Code] section with custom wizard
```

**QACompiler.iss (has drive selector):**
```inno
[Code]
var
  DriveSelectionPage: TInputQueryWizardPage;
  DriveLetter: String;

procedure InitializeWizard();
begin
  DriveSelectionPage := CreateInputQueryPage(wpWelcome,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    '...'
  );
  DriveSelectionPage.Add('Drive Letter (e.g., F, D, E):', False);
  DriveSelectionPage.Values[0] := 'F';
end;
```

### Solution: Add Drive Selector to MapDataGenerator.iss

Add the following sections to `installer/MapDataGenerator.iss`:

```inno
[Code]
var
  DriveSelectionPage: TInputQueryWizardPage;
  DriveLetter: String;

procedure InitializeWizard();
begin
  // Create drive selection page after Welcome page
  DriveSelectionPage := CreateInputQueryPage(wpWelcome,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    'MapDataGenerator needs to know where your Perforce folders are located.' + #13#10 +
    #13#10 +
    'Default paths use F: drive. If your Perforce is on a different drive (D:, E:, etc.), enter just the letter below.'
  );
  DriveSelectionPage.Add('Drive Letter (e.g., F, D, E):', False);
  DriveSelectionPage.Values[0] := 'F';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  DriveInput: String;
begin
  Result := True;

  if CurPageID = DriveSelectionPage.ID then
  begin
    DriveInput := Uppercase(Trim(DriveSelectionPage.Values[0]));

    // Validate: single letter A-Z
    if (Length(DriveInput) <> 1) or (DriveInput[1] < 'A') or (DriveInput[1] > 'Z') then
    begin
      MsgBox('Please enter a single drive letter (A-Z).', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    DriveLetter := DriveInput;

    // Check if drive exists (optional warning)
    if not DirExists(DriveLetter + ':\') then
    begin
      if MsgBox('Drive ' + DriveLetter + ':\ does not appear to exist.' + #13#10 +
                'Are you sure you want to continue?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsPath: String;
  SettingsContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Write settings.json with selected drive letter
    SettingsPath := ExpandConstant('{app}\settings.json');
    SettingsContent := '{"drive_letter": "' + DriveLetter + '", "version": "1.0"}';
    SaveStringToFile(SettingsPath, AnsiString(SettingsContent), False);
  end;
end;

function GetDriveLetter(Param: String): String;
begin
  Result := DriveLetter;
end;
```

### config.py Already Supports This

Good news: `config.py` already has drive letter support via `settings.json`:

```python
def _load_drive_letter() -> str:
    """Load drive letter from settings.json."""
    settings_file = get_base_dir() / "settings.json"
    # ... reads {"drive_letter": "F"} from settings.json
```

The Inno Setup code just needs to CREATE this `settings.json` file during installation.

---

## Comparison: QACompiler vs MapDataGenerator

| Aspect | QACompiler (Working) | MapDataGenerator (Broken) |
|--------|---------------------|--------------------------|
| **Entry Point** | `main.py` with `sys.path.insert(0, ...)` | `main.py` without sys.path fix |
| **Import Style** | Absolute imports only | Mixed (try absolute, except relative) |
| **Spec File** | Includes config.py as data | Missing some data files |
| **Console** | `console=True` (shows debug) | `console=False` (hides errors) |
| **Drive Selector** | Full Inno Setup wizard page | None |
| **settings.json** | Created by installer | Not created |
| **Privileges** | `PrivilegesRequired=lowest` | `PrivilegesRequired=lowest` |
| **Install Location** | `{userdesktop}\QACompiler` | `{autopf}\MapDataGenerator` |

### Key Differences in .spec Files

**QACompiler.spec:**
```python
datas=[
    ('config.py', '.'),              # <-- Includes config
    ('languageTOtester_list.example.txt', '.'),
    ('docs', 'docs'),
    ('README.md', '.'),
],
hiddenimports=[
    'openpyxl', 'lxml', 'lxml.etree',
    'tkinter', 'tkinter.ttk',
    'tkinter.filedialog', 'tkinter.messagebox',
],
```

**MapDataGenerator.spec:**
```python
datas=[
    ('tools', 'tools'),  # vgmstream only
],
hiddenimports=[
    'PIL', 'PIL.Image', 'pillow_dds',
    'lxml', 'lxml.etree',
    'matplotlib', 'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
],
```

**Missing from MapDataGenerator.spec:**
- `('config.py', '.')` - config file should be included
- Core and GUI subpackages should be collected

---

## Implementation Steps

### Step 1: Fix Relative Imports (Priority: CRITICAL)

1. **Edit `main.py`** - Add sys.path fix at the top:
   ```python
   import sys
   from pathlib import Path

   # Ensure package imports work (PyInstaller compatibility)
   sys.path.insert(0, str(Path(__file__).parent))
   ```

2. **Edit `gui/app.py`** - Remove the try/except import block:
   - Delete lines 40-54 (the except ImportError block)
   - Keep only the absolute imports (lines 25-39)

3. **Check all other files** in `gui/` and `core/` for similar patterns

### Step 2: Update .spec File

Update `MapDataGenerator.spec`:

```python
datas=[
    ('tools', 'tools'),
    ('config.py', '.'),  # ADD THIS
],
hiddenimports=[
    'PIL', 'PIL.Image', 'pillow_dds',
    'lxml', 'lxml.etree',
    'matplotlib', 'matplotlib.backends.backend_tkagg',
    'matplotlib.figure',
    'tkinter', 'tkinter.ttk',           # ADD
    'tkinter.filedialog',               # ADD
    'tkinter.messagebox',               # ADD
    # Add all submodules explicitly
    'core', 'core.linkage', 'core.language', 'core.search',
    'core.xml_parser', 'core.dds_handler', 'core.audio_handler',
    'gui', 'gui.app', 'gui.search_panel', 'gui.result_panel',
    'gui.image_viewer', 'gui.audio_viewer', 'gui.map_canvas',
    'utils', 'utils.filters',
],
```

Or use `--collect-submodules` on the command line:
```bash
pyinstaller --collect-submodules core --collect-submodules gui MapDataGenerator.spec
```

### Step 3: Enable Console for Debugging

Temporarily set `console=True` in the .spec file to see errors:

```python
exe = EXE(
    # ...
    console=True,  # CHANGE FROM False - shows errors during testing
    # ...
)
```

### Step 4: Add Drive Selector to Inno Setup

1. Add the `[Code]` section from [Issue #2 Solution](#solution-add-drive-selector-to-mapdatageneratoriss) above
2. Also update the `[Setup]` section to match QACompiler's portable-friendly settings:
   ```inno
   ; PORTABLE INSTALL - Desktop by default (no admin needed)
   DefaultDirName={userdesktop}\MapDataGenerator
   ```

### Step 5: Test the Build

```bash
# Build with PyInstaller
cd /path/to/MapDataGenerator
pyinstaller MapDataGenerator.spec

# Run the EXE directly to see any errors
./dist/MapDataGenerator/MapDataGenerator.exe

# If it works, build the installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\MapDataGenerator.iss
```

---

## References

### PyInstaller Documentation
- [Relative Imports Issue #2560](https://github.com/pyinstaller/pyinstaller/issues/2560) - Handle relative imports in package's `__main__.py`
- [Using PyInstaller - Official Docs](https://pyinstaller.org/en/stable/usage.html)
- [Understanding PyInstaller Hooks](https://pyinstaller.org/en/stable/hooks.html) - `collect_submodules` and `hiddenimports`

### Import Error Solutions
- [ImportError: attempted relative import with no known parent package - GeeksforGeeks](https://www.geeksforgeeks.org/python/how-to-fix-importerror-attempted-relative-import-with-no-known-parent-package/)
- [Fix ImportError - sebhastian.com](https://sebhastian.com/attempted-relative-import-with-no-known-parent-package/)
- [Python Apps the Right Way - Chris Warrick](https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/) - Entry points and scripts

### Inno Setup
- [Inno Setup FAQ](https://jrsoftware.org/isfaq.php)
- [Directory Constants](https://jrsoftware.org/ishelp/topic_consts.htm) - `{sd}`, `{autopf}`, etc.
- [Custom Installation Directory Guide](https://copyprogramming.com/howto/inno-setup-custom-install-path)

### Best Practices
- [How to Use PyInstaller - InfoWorld](https://www.infoworld.com/article/2258008/how-to-use-pyinstaller-to-create-python-executables.html)
- [PyInstaller - Real Python Tutorial](https://realpython.com/pyinstaller-python/)

---

## Summary Checklist

- [ ] Add `sys.path.insert(0, ...)` to `main.py`
- [ ] Remove relative import fallbacks from `gui/app.py`
- [ ] Check and fix all files in `gui/` and `core/` for relative imports
- [ ] Update `MapDataGenerator.spec` with `config.py` and explicit `hiddenimports`
- [ ] Set `console=True` temporarily for debugging
- [ ] Add drive selector `[Code]` section to `MapDataGenerator.iss`
- [ ] Change `DefaultDirName` to `{userdesktop}\MapDataGenerator`
- [ ] Test build and installer on Windows
- [ ] Set `console=False` after confirming everything works

---

*Document created: 2026-02-01*
*Based on analysis of QACompilerNEW (working) vs MapDataGenerator (issues)*
