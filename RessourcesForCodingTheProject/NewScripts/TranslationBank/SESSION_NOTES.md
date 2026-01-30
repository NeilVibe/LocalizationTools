# Translation Bank - Implementation Session Notes

**Date:** 2026-01-30
**Purpose:** Complete implementation record for session continuity

---

## What Was Built

### Translation Bank - A Translation Recovery Tool

**Problem Solved:** When StringId or StrOrigin changes in XML localization files, translations are lost. This tool recovers them using a 3-level unique key system.

---

## File Structure Created

```
RessourcesForCodingTheProject/NewScripts/TranslationBank/
├── main.py                      # Entry point (launches GUI)
├── config.py                    # Settings, VERSION, drive letters
├── requirements.txt             # Dependencies: lxml
├── TranslationBank.spec         # PyInstaller spec file
├── README.md                    # Project overview
├── USER_GUIDE.md                # Complete user documentation
├── SESSION_NOTES.md             # This file (implementation record)
│
├── gui/
│   ├── __init__.py
│   └── app.py                   # Tkinter GUI (File/Folder modes)
│
├── core/
│   ├── __init__.py
│   ├── xml_parser.py            # Battle-tested XML parsing (from MapDataGenerator)
│   ├── unique_key.py            # 3-level key generation (SHA256)
│   ├── bank_builder.py          # Create bank from XML (PKL/JSON)
│   └── bank_transfer.py         # Transfer with fallback chain
│
└── installer/
    └── TranslationBank.iss      # Inno Setup installer script
```

---

## GitHub Actions Workflow

**File:** `.github/workflows/translationbank-build.yml`

**Trigger File:** `TRANSLATIONBANK_BUILD.txt` (at repo root)

### Workflow Structure (3 Jobs)

1. **validation** (Ubuntu) - Check trigger, auto-generate version
2. **safety-checks** (Ubuntu) - Syntax, imports, flake8, security
3. **build-and-release** (Windows) - PyInstaller, Inno Setup, GitHub Release

### Triple Release Pattern

- `TranslationBank_vX.X.X_Setup.exe` - Windows installer
- `TranslationBank_vX.X.X_Portable.zip` - No-install portable
- `TranslationBank_vX.X.X_Source.zip` - Source code

---

## Core Architecture

### Three-Level Key System

| Level | Key Formula | When Used |
|-------|-------------|-----------|
| **1** | SHA256(StrOrigin + StringId) | Primary match - both match |
| **2** | StringId (normalized) | When Korean text changed |
| **3** | SHA256(StrOrigin + Filename + Prev + Next) | When both changed |

### Bank Format

- **Default:** PKL (pickle) - fast for 150k+ entries
- **Optional:** JSON - human-readable for debugging

### Transfer Logic

```
For each target entry with empty Str="":
    1. Try Level 1 (StrOrigin + StringId) → HIT_LEVEL1
    2. Try Level 2 (StringId only)        → HIT_LEVEL2
    3. Try Level 3 (context-aware)        → HIT_LEVEL3
    4. No match                           → MISS
```

---

## Key Design Decisions

### Why PKL over JSON?
- User has 150k+ XML nodes
- PKL: ~1 sec load, ~15 MB file
- JSON: ~10 sec load, ~80 MB file
- JSON available via checkbox for debugging

### Why Level 3 Uses Filename Not Full Path?
- Filename sufficient when combined with:
  - Korean text (StrOrigin)
  - Previous neighbor's StrOrigin + StringId
  - Next neighbor's StrOrigin + StringId
- This combination makes false matches virtually impossible

### Why SHA256 for Keys?
- Deterministic (same input = same hash)
- Fast computation
- Fixed length (easy indexing)
- Collision probability negligible

---

## How to Trigger a Build

```bash
# Add trigger line
echo "Build 001: Initial release" >> TRANSLATIONBANK_BUILD.txt

# Commit and push
git add -A && git commit -m "Build 001: Initial TranslationBank release"
git push origin main

# Check build status
gh run list --workflow=translationbank-build.yml --limit 3
```

---

## How to Use the Tool

### Create Bank
1. Select source folder (translated XMLs)
2. Click "Generate Bank"
3. Choose save location
4. Bank created as .pkl file

### Transfer Translations
1. Load bank file
2. Select target folder (XMLs needing translations)
3. Click "Transfer"
4. Review report (HIT/MISS statistics)

---

## Files Copied/Referenced

| Source | Destination | Purpose |
|--------|-------------|---------|
| MapDataGenerator/core/xml_parser.py | core/xml_parser.py | Battle-tested XML parsing |
| QACompilerNEW/gui/app.py | Reference | GUI patterns (threading, progress) |
| qacompiler-build.yml | translationbank-build.yml | CI workflow template |

---

## Testing Checklist

- [ ] All Python files compile: `python -m py_compile *.py`
- [ ] GUI launches: `python main.py`
- [ ] Bank creation works with test XML
- [ ] Transfer works with modified XML
- [ ] CI workflow triggers correctly
- [ ] GitHub Release created

---

## Future Enhancements (Not Implemented)

1. CLI mode (`--cli` argument)
2. Batch processing with progress reports
3. Export transfer report to Excel
4. Level 3 confidence scoring
5. GUI dark mode

---

## Contact Points in Code

| Need to Change | File | Location |
|----------------|------|----------|
| Default paths | config.py | Lines 20-30 |
| XML attribute names | config.py | Lines 45-53 |
| Key generation | core/unique_key.py | All functions |
| GUI layout | gui/app.py | _build_ui() method |
| CI modules list | .github/workflows/translationbank-build.yml | Lines 175-185 |

---

*Session notes for continuity - update as needed*
