# FactionListGenerator v2.0

A 2-button GUI tool for faction list extraction and multi-language glossary translation.

## Quick Start

```bash
python FactionListGenerator.py
```

## Requirements

- Python 3.8+
- `openpyxl` - Excel handling
- `lxml` - XML parsing (optional, falls back to standard library)

```bash
pip install openpyxl lxml
```

## Configuration

Edit `settings.json` to change drive letter:

```json
{
    "drive_letter": "F",
    "version": "2.0",
    "paths": {
        "factioninfo": "F:\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\factioninfo",
        "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc"
    }
}
```

---

## Button 1: Faction List Generator

### What It Does
1. Parses faction XML files from `factioninfo/` folder
2. Extracts faction names (FactionGroup, Faction, FactionNode)
3. Generates `FactionList.xlsx`
4. (Optional) Filters a selected Excel file by removing rows where **Column A exactly matches** a faction name

### Workflow
```
Click Button 1 → Select Excel file (optional) → Processing → Output
```

### Output
```
Output/
├── FactionList.xlsx           # All faction names with type and source
├── Filtered_<filename>.xlsx   # Input file minus faction matches (if selected)
└── FilterReport_<name>.txt    # What was removed
```

### FactionList.xlsx Format
| Faction Name | Type | Source File |
|--------------|------|-------------|
| 황금군단 | FactionGroup | faction01.xml |
| 황금기사단 | Faction | faction01.xml |
| 기사단장 | FactionNode | faction01.xml |

Color-coded: Gold (FactionGroup), Green (Faction), Blue (FactionNode)

---

## Button 2: List Concatenator + Translator

### What It Does
1. Reads **Column A** from all Excel files in a selected folder
2. Concatenates into one list with category tracking
3. Translates to **ALL** available languages (100+)
4. Adds **English column** for European languages

### Workflow
```
Click Button 2 → Select folder with Excel files → Processing → Output
```

### Input Structure
```
MyFolder/
├── Weapons.xlsx    (Column A: 검, 활, 창...)
├── Monsters.xlsx   (Column A: 고블린, 오크...)
└── Items.xlsx      (Column A: 물약, 열쇠...)
```

### Output
```
Output/
├── CombinedList.xlsx
└── Translations/
    ├── Translated_ENG.xlsx
    ├── Translated_FRE.xlsx
    ├── Translated_GER.xlsx
    ├── Translated_ZHO-CN.xlsx
    ├── Translated_JPN.xlsx
    └── ... (100+ languages)
```

### Translation Output Format

**European Languages (FRE, GER, SPA, ITA, RUS, etc.):**
| SourceText (Korean) | English | Translation (FRE) | Category |
|---------------------|---------|-------------------|----------|
| 검 | Sword | Épée | Weapons |
| 고블린 | Goblin | Gobelin | Monsters |
| 미등록 | NO_TRANSLATION | NO_TRANSLATION | Items |

**Asian Languages (ZHO-CN, ZHO-TW, JPN):**
| SourceText (Korean) | Translation (JPN) | Category |
|---------------------|-------------------|----------|
| 검 | 剣 | Weapons |
| 고블린 | ゴブリン | Monsters |

### NO_TRANSLATION Marking (Red Highlight)
- Translation not found in LOC data
- Translation is empty
- Translation equals Korean source (untranslated)

---

## File Structure

```
FactionListGenerator/
├── FactionListGenerator.py    # Main GUI application
├── translation_utils.py       # LOC XML parsing utilities
├── settings.json              # Configuration (drive letter, paths)
├── README.md                  # This file
└── Output/                    # Generated files (auto-created)
    ├── FactionList.xlsx
    ├── CombinedList.xlsx
    └── Translations/
        └── Translated_*.xlsx
```

---

## Data Sources

| Data | Path |
|------|------|
| Faction XML | `F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\*.xml` |
| LOC Files | `F:\perforce\cd\mainline\resource\GameData\stringtable\loc\languagedata_*.xml` |

---

## Version History

### v2.0 (2025-01-23)
- 2-button GUI interface
- Button 1: Faction list + glossary filtering (exact match, Column A only)
- Button 2: Multi-file concatenation + translation to all languages
- Category column tracking (filename-based)
- English column for European languages
- NO_TRANSLATION marking with red highlight for missing/Korean translations
