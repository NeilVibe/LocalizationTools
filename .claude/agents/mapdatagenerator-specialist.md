---
name: mapdatagenerator-specialist
description: MapDataGenerator project specialist. Use when working on map data visualization, XML parsing, multi-language search, DDS image display, or GUI tkinter/ttk operations.
tools: Read, Grep, Glob, Bash, Edit, Write, mcp__openviking__*
model: opus
---

# MapDataGenerator Specialist

## What Is MapDataGenerator?

**Map/Region Data Visualization Tool** - A tkinter GUI application for searching and visualizing game map data from XML files.

**Location:** `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/`

**Core Functions:**
1. **Search** game data across 13 languages (MAP, CHARACTER, ITEM, AUDIO modes)
2. **Display** DDS textures via UITextureName linkage
3. **Visualize** maps with nodes, routes, and coordinates
4. **Play** WEM audio files via vgmstream

## Project Structure

```
MapDataGenerator/
├── main.py                    # Entry point
├── config.py                  # Settings, paths, constants
│
├── core/                      # Data processing
│   ├── xml_parser.py          # XML parsing with lxml
│   ├── language.py            # Multi-language support (13 languages)
│   ├── linkage.py             # LinkageResolver (StrKey → Knowledge → UI)
│   ├── search.py              # Search engine (contains, exact, fuzzy)
│   ├── dds_handler.py         # DDS texture loading (requires pillow-dds)
│   └── audio_handler.py       # WEM audio via vgmstream-cli
│
├── gui/                       # Tkinter GUI (ttk themed)
│   ├── app.py                 # Main application window
│   ├── search_panel.py        # Search interface
│   ├── result_panel.py        # Results display (Treeview + details)
│   ├── map_canvas.py          # Matplotlib map visualization
│   ├── image_viewer.py        # DDS image display
│   └── audio_viewer.py        # Audio player controls
│
├── utils/
│   └── filters.py             # Text filtering utilities
│
├── tools/                     # External tools
│   └── vgmstream-cli.exe      # Audio decoder
│
├── installer/
│   └── MapDataGenerator.iss   # Inno Setup script
│
├── logs/                      # Runtime logs
└── cache/                     # DDS cache
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| GUI | Tkinter + ttk (themed) |
| XML | lxml |
| Images | Pillow + pillow-dds |
| Maps | Matplotlib |
| Audio | vgmstream-cli |
| Build | PyInstaller |

## CRITICAL: ttk vs tk Widget Rules

**This is THE #1 source of bugs!** ttk widgets are NOT the same as tk widgets.

### The Problem Pattern (CAUSES CRASH)

```python
# ❌ WRONG - ttk widgets DON'T support cget("background")
bg = self._detail_frame.cget("background")  # TclError: unknown option "-background"

# ❌ WRONG - hasattr doesn't help because cget() EXISTS, just doesn't work
bg = frame.cget("background") if hasattr(frame, "cget") else "#f0f0f0"  # STILL CRASHES!
```

### The Correct Patterns

```python
from tkinter import ttk

# ✅ CORRECT - Use ttk.Style for ttk widget colors
style = ttk.Style()
bg_color = style.lookup("TLabelframe", "background") or "#f0f0f0"

# ✅ CORRECT - Use style name for different widget types
frame_bg = style.lookup("TFrame", "background")
button_bg = style.lookup("TButton", "background")

# ✅ CORRECT - For tk.Text inside ttk container, pass style-derived color
text_widget = tk.Text(ttk_frame, background=bg_color)
```

### ttk Style Names

| Widget | Style Name |
|--------|------------|
| ttk.Frame | TFrame |
| ttk.LabelFrame | TLabelframe |
| ttk.Button | TButton |
| ttk.Label | TLabel |
| ttk.Entry | TEntry |
| ttk.Treeview | Treeview |
| ttk.Combobox | TCombobox |

### What Works on ttk vs tk

| Operation | tk.Widget | ttk.Widget |
|-----------|-----------|------------|
| `.cget("background")` | ✅ Works | ❌ CRASH |
| `.configure(bg="red")` | ✅ Works | ❌ CRASH |
| `["background"]` | ✅ Works | ❌ CRASH |
| `style.lookup(stylename, "background")` | N/A | ✅ Works |
| `style.configure(stylename, background="red")` | N/A | ✅ Works |

## XML Newline Convention (CRITICAL!)

**Newlines in XML language data = `<br/>` tags. NOT `&#10;`, NOT `\n`.**

```xml
<!-- CORRECT -->
KR="첫 번째 줄<br/>두 번째 줄"

<!-- WRONG -->
KR="첫 번째 줄&#10;두 번째 줄"
```

All MapDataGenerator modules (xml_parser, search, language) MUST preserve `<br/>` tags. When displaying in GUI, split on `<br/>` for visual line breaks but never alter the underlying data.

## Search Modes

| Mode | Data Source | Columns |
|------|-------------|---------|
| MAP | regioninfo_*.xml | Region, Knowledge, Position |
| CHARACTER | character_*.xml | Name, Title, Faction |
| ITEM | iteminfo_*.xml | Name, Description, Type |
| AUDIO | sound_*.xml | Name, File, Duration |

## Languages Supported (13)

KR, EN, JP, TW, CN, DE, FR, RU, ES, PT, TH, ID, TR

## Linkage Resolution Chain

```
SearchResult.StrKey
    → Knowledge entry (KnowledgeKey)
        → UITextureName
            → DDS file path
                → Display in image viewer
```

## GUI Validation for CI

**CRITICAL:** Always include GUI modules in import validation!

```python
# Must validate ALL of these:
modules = [
    'config',
    'core.xml_parser',
    'core.language',
    'core.linkage',
    'core.search',
    'core.dds_handler',
    'utils.filters',
    # GUI - These MUST be validated or runtime crashes escape!
    'gui.app',
    'gui.result_panel',
    'gui.search_panel',
    'gui.map_canvas',
    'gui.image_viewer',
    'gui.audio_viewer',
]
```

## Common Tasks

### Fix GUI Bug

1. Identify which GUI file: `gui/{module}.py`
2. Check if issue involves ttk vs tk (see patterns above)
3. Test headless: `xvfb-run python -c "from gui.app import MapDataGeneratorApp; app = MapDataGeneratorApp()"`

### Add New Search Mode

1. Add mode to `config.py` SEARCH_MODES
2. Create parser in `core/xml_parser.py`
3. Add columns to `gui/result_panel.py`
4. Update search in `core/search.py`

### Fix DDS Display

1. Check `core/dds_handler.py`
2. Verify pillow-dds is installed (Windows only)
3. Check linkage chain in `core/linkage.py`

## Debugging

```bash
# Navigate to project
cd RessourcesForCodingTheProject/NewScripts/MapDataGenerator

# Syntax check all
python -m py_compile main.py config.py core/*.py gui/*.py utils/*.py

# Import test (including GUI!)
python -c "from gui.app import MapDataGeneratorApp; print('OK')"

# Headless GUI test (Linux with Xvfb)
xvfb-run python -c "
from gui.app import MapDataGeneratorApp
app = MapDataGeneratorApp()
print('GUI instantiation successful')
"

# Run app
python main.py
```

## CI/CD - GitHub Actions

### Workflow File
`.github/workflows/mapdatagenerator-build.yml`

### Trigger Build
```bash
echo "Build" >> MAPDATAGENERATOR_BUILD.txt
git add MAPDATAGENERATOR_BUILD.txt
git commit -m "Trigger MapDataGenerator build"
git push origin main
```

### CI Checks (5 Total)

| Check | What It Catches |
|-------|-----------------|
| 1. Python Syntax | SyntaxError |
| 2. Module Imports | Missing imports, import errors (INCLUDING GUI!) |
| 3. Flake8 | Undefined names, critical errors |
| 4. Security Audit | Vulnerable dependencies |
| 5. GUI Smoke Test | **Runtime crashes from ttk/tk misuse** (Xvfb headless) |

### CHECK 5 is CRITICAL

The GUI smoke test catches errors that static analysis CANNOT detect:
- ttk.cget("background") crashes
- Widget instantiation failures
- Style/theme initialization errors

Without CHECK 5, builds succeed but users get runtime crashes!

## Output Format for Issues

```
## MapDataGenerator Issue: [Description]

### Category
[GUI/Core/Config/Build]

### File
`{path/to/file.py}:{line}`

### Problem
[What's wrong]

### Fix
```python
# Code fix
```

### Test
```bash
xvfb-run python -c "from gui.app import MapDataGeneratorApp; app = MapDataGeneratorApp()"
```
```

## Key Files by Task

| Task | Primary File | Secondary |
|------|--------------|-----------|
| Search logic | `core/search.py` | `xml_parser.py` |
| Language support | `core/language.py` | `config.py` |
| DDS display | `core/dds_handler.py` | `linkage.py` |
| Audio playback | `core/audio_handler.py` | - |
| Main GUI | `gui/app.py` | All gui/*.py |
| Results display | `gui/result_panel.py` | - |
| Search input | `gui/search_panel.py` | - |
| Map visualization | `gui/map_canvas.py` | - |
| Config/paths | `config.py` | - |

## CRITICAL: PyInstaller Import Pattern

**This is THE #2 source of bugs!** Relative imports break in PyInstaller frozen executables.

### The Problem Pattern (CAUSES CRASH)

```python
# ❌ WRONG - try/except with relative import fallbacks
try:
    from config import APP_NAME
except ImportError:
    from ..config import APP_NAME  # CRASHES in frozen .exe!
```

**Why it fails:** In PyInstaller, `from ..config` tries to go up one directory level, but the frozen executable has no parent package context.

### The Correct Pattern (QACompiler Style)

```python
import sys
from pathlib import Path

# ✅ CORRECT - Add parent to sys.path BEFORE any imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# ✅ CORRECT - Then use ONLY absolute imports
from config import APP_NAME
from core.linkage import LinkageResolver
from gui.search_panel import SearchPanel
```

### Files That MUST Have sys.path.insert

Every file in `gui/` and `core/` that imports from parent:
- `gui/app.py` - Has it ✅
- `gui/search_panel.py` - Has it ✅
- `gui/result_panel.py` - Has it ✅
- `gui/image_viewer.py` - Has it ✅
- `gui/audio_viewer.py` - Has it ✅
- `gui/map_canvas.py` - Has it ✅
- `core/language.py` - Has it ✅
- `core/search.py` - Has it ✅

### __init__.py Files Are Different

Package `__init__.py` files CAN use relative imports (`.`):
```python
# ✅ OK in __init__.py
from .app import MapDataGeneratorApp  # Relative to same package
from .xml_parser import parse_xml
```

### Debugging Import Issues

```bash
# Test imports work before PyInstaller
python -c "
import sys
sys.path.insert(0, '.')
from gui.app import MapDataGeneratorApp
print('OK')
"
```

## Recent Fixes

| Issue | Fix | Date |
|-------|-----|------|
| `ttk.cget("background")` crash | Use `ttk.Style().lookup()` | 2026-02-01 |
| GUI modules not validated in CI | Added gui.* to import list | 2026-02-01 |
| No headless GUI test | Added CHECK 5 with Xvfb | 2026-02-01 |
| **Relative import crash in .exe** | **Remove try/except fallbacks, use sys.path.insert + absolute imports** | 2026-02-01 |
| unittest excluded breaks pyparsing | Don't exclude unittest or pyparsing.testing | 2026-02-01 |
