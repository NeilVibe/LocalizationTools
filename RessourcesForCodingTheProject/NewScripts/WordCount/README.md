# WordCount - Translation Coverage Analysis with Unused String Detection

Enhanced translation coverage analysis tool that identifies and excludes unused strings from `__backup` folders to calculate **True Coverage %**.

## What's New in wordcount7.py

### Unused String Detection

The tool now scans `__backup` folders to identify strings that are no longer in use:

1. **Backup Folder Scanning**: Recursively finds all `__backup` folders (case-insensitive) in:
   - `F:\perforce\cd\mainline\resource\editordata`
   - `F:\perforce\cd\mainline\resource\sequencer`

2. **SEQC File Parsing**: Extracts `DialogStrKey` attribute values from `.seqc` XML files

3. **Cross-Reference**: Matches `DialogStrKey` values with `StringId` in export folder

4. **Category Assignment**: Unused strings are assigned to their respective categories (Faction, Dialog/QuestDialog, etc.)

### New Columns in Excel Output

| Column | Description |
|--------|-------------|
| **Unused Words** | Word count from strings found in backup folders |
| **Effective Words** | Total Words - Unused Words |
| **Coverage %** | Original calculation (includes unused) |
| **True Coverage %** | Excludes unused: `Completed / Effective Words` |

### Example

If a category (e.g., Sequencer/Faction) has:
- Total: 10,000 words
- Completed: 8,000 words
- Unused: 1,000 words (from backup)

Then:
- **Coverage %**: 80% (8,000 / 10,000)
- **True Coverage %**: 88.9% (8,000 / 9,000)

## Excel Sheets

1. **Per-File**: Summary per language file with unused tracking
2. **Detailed Summary**: Category breakdown per language with True Coverage
3. **Unused Strings**: List of DialogStrKey values found in backup folders

## Technical Details

### XML Parsing Pipeline (5-Pass)

Uses battle-tested sanitization from QACompilerNEW:
1. Remove control characters
2. Fix malformed entities (`&` → `&amp;`)
3. Escape `<` in attribute values
4. Escape `&` in attribute values
5. Tag stack repair for malformed XML

### DialogStrKey → StringId Mapping

```
__backup/*.seqc (DialogStrKey="norhernwarrior_9000_boss_00_00007")
         ↓
export__/*.loc.xml (StringId="norhernwarrior_9000_boss_00_00007")
         ↓
Category assignment (Sequencer/Faction/Faction_Pailune)
         ↓
Marked as "unused" in that category's stats
```

## Usage

```bash
python wordcount7.py
```

Then click "Word-Count Process" in the GUI.

## Configuration

Edit constants at top of script:

```python
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER   = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

BACKUP_SCAN_ROOTS = [
    Path(r"F:\perforce\cd\mainline\resource\editordata"),
    Path(r"F:\perforce\cd\mainline\resource\sequencer"),
]
```

## Future Plans

This is currently a monolith script. May be refactored to a tree structure with `main.py` if complexity grows:

```
WordCount/
├── main.py              # Entry point
├── core/
│   ├── xml_parser.py    # XML sanitization
│   ├── scanner.py       # Backup folder scanning
│   └── analyzer.py      # Coverage calculation
├── exporters/
│   └── excel.py         # Excel report generation
└── config.py            # Path configuration
```

---

*Last updated: 2026-02-01*
