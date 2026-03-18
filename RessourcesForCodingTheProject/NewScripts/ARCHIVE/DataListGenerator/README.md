# DataListGenerator v3.0

A modular tool for generating data lists (Factions, Skills, and future types) from game XML files with multi-language translation support.

## Features

- **Button 1: Data List Generator**
  - Generate FactionList.xlsx from factioninfo XML files
  - Generate SkillList.xlsx from skillinfo XML files
  - Checkbox selection for which lists to generate
  - Color-coded type columns

- **Button 2: List Concatenator + Translator**
  - Combine Excel lists from a folder (reads Column A)
  - Translate to all available LOC languages
  - European languages include English column
  - Highlights untranslated entries

## Project Structure

```
DataListGenerator/
├── main.py                      # Entry point (CLI + GUI launcher)
├── config.py                    # Configuration + settings loading
├── translation_utils.py         # Translation utilities (from FactionListGenerator)
├── generators/
│   ├── __init__.py              # Exports generator classes
│   ├── base.py                  # BaseGenerator abstract class
│   ├── faction.py               # FactionGenerator (factioninfo)
│   └── skill.py                 # SkillGenerator (skillinfo)
├── utils/
│   ├── __init__.py
│   ├── xml_parser.py            # XML parsing utilities
│   └── excel_writer.py          # Excel generation utilities
├── gui/
│   ├── __init__.py
│   └── app.py                   # DataToolGUI class
├── settings.json                # Configuration (paths, drive letter)
├── Output/                      # Generated files
│   ├── FactionList.xlsx
│   ├── SkillList.xlsx
│   └── Translations/
└── README.md
```

## Usage

### GUI Mode

```bash
python main.py
```

### Configuration

Edit `settings.json` to configure paths:

```json
{
    "drive_letter": "F",
    "version": "3.0",
    "paths": {
        "factioninfo": "F:\\perforce\\cd\\...\\StaticInfo\\factioninfo",
        "skillinfo": "F:\\perforce\\cd\\...\\StaticInfo\\skillinfo",
        "loc_folder": "F:\\perforce\\cd\\...\\stringtable\\loc"
    }
}
```

## Data Extraction

### Factions
Extracts from factioninfo XML:
- `FactionGroup/@GroupName`
- `Faction/@Name`
- `FactionNode/@Name` (recursive)

### Skills
Extracts from skillinfo XML:
- `SkillInfo/@SkillName`

## Adding New Generators

1. Create a new file in `generators/` (e.g., `item.py`)
2. Extend `BaseGenerator` class
3. Implement the `extract()` method
4. Add to `generators/__init__.py`
5. Add checkbox in `gui/app.py`

Example:

```python
from .base import BaseGenerator, DataEntry

class ItemGenerator(BaseGenerator):
    name = "Item"
    output_filename = "ItemList.xlsx"
    sheet_name = "Item List"
    headers = ["Item Name", "Type", "Source File"]

    def extract(self):
        # Parse XML and return List[DataEntry]
        ...
```

## Requirements

- Python 3.8+
- lxml (recommended, fallback to xml.etree)
- openpyxl

## Version History

- **v3.0**: Modular refactor (from FactionListGenerator v2.0)
  - Separated into generators, utils, gui modules
  - Added SkillGenerator
  - Checkbox selection for generator types
