# LanguageDataExporter

Language XML to Categorized Excel Converter with VRS-based story ordering.

## Features

- **Two-tier category clustering**: STORY (VRS-ordered) + GAME_DATA (keyword-based)
- **VoiceRecordingSheet ordering**: STORY strings sorted by EventName for chronological story order
- **Word count reports**: For LQA scheduling with Korean detection
- **GUI and CLI modes**: tkinter interface or command-line
- **Color-coded Excel output**: Category colors matching wordcount6.py style
- **Conditional English column**: Included for EU languages, excluded for ENG/CJK

## Categories

### STORY (VRS-Ordered)
| Category | Description |
|----------|-------------|
| Sequencer | Story cutscenes |
| AIDialog | Ambient/NPC dialog |
| QuestDialog | Quest-related dialog |
| NarrationDialog | Narration/tutorial text |

### GAME_DATA (Keyword-Based)
| Category | Keywords/Folders |
|----------|------------------|
| Item | item, weapon, armor, LookAt/, PatternDescription/ |
| Quest | quest, Quest/, schedule_ |
| Character | character, Character/, Npc/, monster, animal |
| Gimmick | Gimmick/ |
| Skill | Skill/ |
| Knowledge | Knowledge/ |
| Faction | Faction/ |
| UI | Ui/, LocalStringInfo, SymbolText |
| Region | Region/ |
| System_Misc | (default fallback) |

## Usage

### CLI Mode
```bash
python main.py                      # Convert all languages
python main.py --lang eng           # Convert specific language
python main.py --lang eng,fre,ger   # Convert multiple languages
python main.py --dry-run            # Preview without writing
python main.py --list-categories    # Show category distribution
python main.py --word-count         # Include word count report
python main.py --word-count-only    # Only generate word count report
python main.py --gui                # Launch GUI
```

### GUI Mode
```bash
python main.py --gui
```

## Configuration

### Paths (config.py)
- `LOC_FOLDER`: languagedata_*.xml files
- `EXPORT_FOLDER`: Categorized .loc.xml files
- `VOICE_RECORDING_FOLDER`: VoiceRecordingSheet Excel files

### Runtime Settings (settings.json)
Created by installer or `drive_replacer.py`:
```json
{
  "drive_letter": "F",
  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",
  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",
  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__"
}
```

### Category Colors (category_clusters.json)
```json
{
  "Sequencer": "FFE599",       // light-orange
  "AIDialog": "C6EFCE",        // light-green
  "QuestDialog": "C6EFCE",     // light-green
  "NarrationDialog": "C6EFCE", // light-green
  "Item": "D9D2E9",            // light-purple
  ...
}
```

## Output

### Language Excel Files
`GeneratedExcel/LanguageData_{LANG}.xlsx`

| Column | Description |
|--------|-------------|
| StrOrigin | Korean source text |
| Str | Translated text |
| StringID | Unique identifier |
| English | English reference (EU languages only) |
| Category | Assigned category |

### Word Count Report
`GeneratedExcel/WordCountReport.xlsx`
- Summary sheet with all languages
- Per-language sheets with category breakdown
- Korean source words, translation words/chars, untranslated counts

## VRS Ordering

STORY strings are sorted by VoiceRecordingSheet EventName position:

1. Load most recent `.xlsx` from VRS folder
2. Extract EventName from Column W (index 22)
3. Build StringID → SoundEventName mapping from EXPORT XML
4. Sort STORY entries by VRS position

This ensures LQA reviewers see story content in chronological play order.

## Project Structure

```
LanguageDataExporter/
├── main.py                    # CLI entry point
├── config.py                  # Configuration constants
├── category_clusters.json     # Category/color config
├── settings.json              # Runtime settings (created by installer)
├── requirements.txt           # Python dependencies
├── LanguageDataExporter.spec  # PyInstaller config
├── drive_replacer.py          # Drive letter configuration
├── exporter/                  # Core export logic
│   ├── xml_parser.py          # XML parsing + SoundEventName extraction
│   ├── category_mapper.py     # Two-tier clustering
│   └── excel_writer.py        # Excel output with VRS ordering
├── reports/                   # Word count reports
│   ├── word_counter.py        # Word/char counting
│   ├── report_generator.py    # Report data structures
│   └── excel_report.py        # Styled Excel output
├── utils/                     # Shared utilities
│   ├── language_utils.py      # Korean detection, language config
│   └── vrs_ordering.py        # VoiceRecordingSheet ordering
├── gui/                       # tkinter GUI
│   └── app.py                 # GUI application
├── clustering/                # Category clustering (legacy)
└── installer/                 # Inno Setup installer
    └── LanguageDataExporter.iss
```

## Build

### Trigger CI/CD Build
```bash
echo "Build 002" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add -A && git commit -m "Build: LanguageDataExporter" && git push
```

### Local Build
```bash
pip install pyinstaller
pyinstaller LanguageDataExporter.spec --clean
```

## Dependencies

- Python 3.11+
- openpyxl >= 3.1.0
- lxml >= 4.9.0 (optional)
- tkinter (included with Python)
