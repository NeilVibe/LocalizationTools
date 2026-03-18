# Translation Bank

A robust translation transfer tool that solves the problem of lost translations when StringId or StrOrigin changes in XML localization files.

## Problem

When StringId or StrOrigin changes in XML localization files:
- Direct mapping breaks
- Translations in `Str` attribute are lost
- Manual re-translation required

## Solution

Translation Bank stores translations with multiple key types, enabling transfer even when primary keys change.

## Three-Level Key System

| Level | Key Components | When Used |
|-------|---------------|-----------|
| **1** | StrOrigin + StringId | Primary match (most reliable) |
| **2** | StringId only | When StrOrigin changed but StringId exists |
| **3** | StrOrigin + Filename + Adjacent Nodes | When both changed (context-aware) |

### Level 3 Adjacent Node Concept

For string B at position N, neighbors are A (N-1) and C (N+1).

Key = hash(StrOrigin_B, Filename, StrOrigin_A+StringId_A, StrOrigin_C+StringId_C)

If neighbors match, confirms correct position even with changed IDs.

## Installation

```bash
cd TranslationBank
pip install -r requirements.txt
```

## Usage

### GUI Mode (Default)

```bash
python main.py
```

### Workflow

1. **Create Bank**: Select translated XML files → Generate bank JSON
2. **Transfer**: Load bank + select target XML → Apply translations

## File Structure

```
TranslationBank/
├── main.py                 # Entry point
├── config.py               # Settings, drive letters
├── requirements.txt        # lxml
├── gui/
│   ├── __init__.py
│   └── app.py              # Tkinter GUI
├── core/
│   ├── __init__.py
│   ├── xml_parser.py       # XML parsing (battle-tested)
│   ├── unique_key.py       # 3-level key generation
│   ├── bank_builder.py     # Create bank from XML
│   └── bank_transfer.py    # Transfer with fallbacks
└── README.md
```

## Bank Format

Default is **PKL** (pickle) for fast load/save with 150k+ entries.
JSON available via checkbox for debugging (human-readable).

### Structure (JSON example)

```json
{
  "metadata": {
    "created": "2026-01-30T12:00:00",
    "source_path": "D:/path/to/source",
    "entry_count": 12345
  },
  "entries": [
    {
      "string_id": "12345",
      "str_origin": "Korean text here",
      "str_translated": "English translation",
      "filename": "LanguageData_eng.xml",
      "position": 42,
      "prev_context": "prev_origin|prev_id",
      "next_context": "next_origin|next_id"
    }
  ],
  "indices": {
    "level1": {"hash1": 0, "hash2": 1},
    "level2": {"12345": [0, 5, 10]},
    "level3": {"hash3": 0}
  }
}
```

## Transfer Report Example

```
══════════════════════════════════════════════════════════════════
              TRANSLATION BANK TRANSFER REPORT
══════════════════════════════════════════════════════════════════

Bank:   translation_bank.json (12,345 entries)
Target: D:\new_files\ (156 XML files)

──────────────────────────────────────────────────────────────────
                     MATCH SUMMARY
──────────────────────────────────────────────────────────────────
Total Target Entries:     10,234
──────────────────────────────────────────────────────────────────
HIT  (Total):              9,567    (93.5%)
  Level 1 (StrOrigin+ID):  7,890    (77.1%)
  Level 2 (ID only):       1,432    (14.0%)
  Level 3 (Context):         245    ( 2.4%)
──────────────────────────────────────────────────────────────────
MISS:                        667    ( 6.5%)
══════════════════════════════════════════════════════════════════
```

## Configuration

Edit `config.py` to set default paths:

```python
DATA_DRIVE = "D:"
DEFAULT_SOURCE_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_Translated")
DEFAULT_TARGET_FOLDER = Path(f"{DATA_DRIVE}/LanguageData_New")
```
