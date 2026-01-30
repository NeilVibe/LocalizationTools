# MapDataGenerator

Map/Region Data Visualization Tool for game localization workflows.

## Features

- **Multi-language Search** - Search across 13 languages (ENG, FRE, GER, SPA, POR, ITA, RUS, TUR, POL, ZHO-CN, ZHO-TW, JPN, KOR)
- **DDS Image Display** - View UITextureName images from game textures
- **Linkage Resolution** - Automatic StrKey → KnowledgeKey → UITextureName chain resolution
- **Interactive Map** - Matplotlib-based map with nodes and routes
- **Search Modes** - Contains, Exact, and Fuzzy matching

## Requirements

- Python 3.10+
- Dependencies (see `requirements.txt`):
  - lxml >= 4.9.0
  - Pillow >= 10.0.0
  - pillow-dds >= 1.0.0
  - matplotlib >= 3.7.0

## Installation

### From Source

```bash
pip install -r requirements.txt
python main.py
```

### From Release

Download the latest release from GitHub:
- `MapDataGenerator_Setup.exe` - Windows installer
- `MapDataGenerator_Portable.zip` - Portable version

## Usage

### 1. Load Data

**File → Load Data** or `Ctrl+O`

Select the following folders:
- **Faction Info Folder** - Contains FactionNode XML files
- **Language Data Folder** - Contains LanguageData_*.xml files
- **Knowledge Info Folder** - Contains KnowledgeInfo XML files
- **Waypoint Info Folder** - Contains NodeWayPointInfo XML files
- **Texture Folder** - Contains DDS texture files

### 2. Search

Enter a search term and select:
- **Match Type**: Contains, Exact, or Fuzzy
- **Language**: Select target language for translations

Results show:
- Name (Korean)
- Name (Translated)
- Description
- Position
- StrKey

### 3. View Details

- **Select a result** - Shows image thumbnail and highlights on map
- **Double-click** - Centers map on selected node
- **Click thumbnail** - Opens full-size image

### 4. Map Navigation

- **Hover** - Shows node info and connected routes
- **Click** - Selects node
- **Toolbar** - Pan, zoom, save figure

## Search Examples

| Query | Match Type | Description |
|-------|------------|-------------|
| 애쉬클로 | Contains | Find nodes with "애쉬클로" in any field |
| Ashclaw | Contains | Find English translations |
| FN_Town_001 | Exact | Find by exact StrKey |
| 오크 | Fuzzy | Find similar matches (ratio > 0.6) |

## Data Flow

```
User Search Query
       ↓
[Search Engine] - Normalize, match against nodes
       ↓
[Linkage Resolver] - Resolve UITextureName chain
       ↓
[Language Manager] - Get translations
       ↓
[DDS Handler] - Load/convert images
       ↓
GUI Output: Results + Image + Map
```

## XML Parsing Strategy

Uses the **QACompilerNEW battle-tested pattern** with lxml `recover=True`:

1. **Sanitize** - Regex-based pre-processing:
   - Fix bad entity references (`&` → `&amp;`)
   - Handle newlines inside `<seg>` tags
   - Escape `<` and `&` inside attribute values
   - Tag stack repair for mismatched tags

2. **Wrap** - Add `<ROOT>` element for fragment parsing

3. **Parse with fallback**:
   ```python
   # Try strict first
   ET.XMLParser(huge_tree=True)

   # If fails, use recovery mode
   ET.XMLParser(recover=True, huge_tree=True)
   ```

This handles the game's malformed XML reliably without corrupting attribute values.

## Current Stats (Build 014)

| Data | Count |
|------|-------|
| DDS files indexed | ~9,300 |
| Knowledge entries | ~3,180 (1,634 with images) |
| MAP entries | ~3,410 (48% with images) |
| Language entries | ~95,850 per language |

**Expected "missing" DDS:**
- `createicon` - placeholder in source data
- `ItemIcon_Prefab_*` - in different texture folder
- `AbyssGate_*` - no UITextureName by design

## Linkage Chain

```
FactionNode.StrKey
  → FactionNode.KnowledgeKey
  → KnowledgeInfo.UITextureName
  → (or KnowledgeGroupInfo.UITextureName)
  → .dds file path
```

## Configuration

Settings are saved to `mdg_settings.json`:

- **UI Language** - English / 한국어
- **Search Limit** - Results per page
- **Fuzzy Threshold** - Minimum ratio for fuzzy matches
- **Folder Paths** - Default data folders

## Building

### PyInstaller

```bash
pip install pyinstaller
pyinstaller MapDataGenerator.spec --clean
```

### Inno Setup Installer

```bash
# Requires Inno Setup 6
iscc installer/MapDataGenerator.iss
```

## CI/CD

See `CI.md` for build automation details.

**Trigger build**:
```bash
echo "Build 001" >> MAPDATAGENERATOR_BUILD.txt
git add -A && git commit -m "Build 001" && git push
```

## Project Structure

```
MapDataGenerator/
├── main.py                    # Entry point
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── MapDataGenerator.spec      # PyInstaller spec
├── CI.md                      # CI documentation
├── README.md                  # This file
├── installer/
│   └── MapDataGenerator.iss   # Inno Setup script
├── gui/
│   ├── __init__.py
│   ├── app.py                 # Main window
│   ├── search_panel.py        # Search interface
│   ├── result_panel.py        # Results display
│   ├── image_viewer.py        # DDS viewer
│   └── map_canvas.py          # Map visualization
├── core/
│   ├── __init__.py
│   ├── xml_parser.py          # XML parsing
│   ├── search.py              # Search engine
│   ├── language.py            # Multi-language support
│   ├── linkage.py             # StrKey resolution
│   └── dds_handler.py         # DDS loading
└── utils/
    ├── __init__.py
    └── filters.py             # Text normalization
```

## License

Internal tool for LocaNext project.
