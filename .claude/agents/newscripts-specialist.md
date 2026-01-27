---
name: newscripts-specialist
description: NewScripts folder specialist. Use when working on mini-projects in RessourcesForCodingTheProject/NewScripts - personal tools, utilities, and potential LocaNext apps.
tools: Read, Grep, Glob, Bash, Edit, Write
model: opus
---

# NewScripts Specialist

## Overview

**Location:** `RessourcesForCodingTheProject/NewScripts/`

Personal tools and mini-projects. Some have CI/CD, some are manual.

---

## Projects with CI/CD (GitHub Actions)

| Project | Trigger File | Purpose |
|---------|--------------|---------|
| **LanguageDataExporter** | `LANGUAGEDATAEXPORTER_BUILD.txt` | XML → Excel with VRS ordering |
| **QACompilerNEW** | `QACOMPILER_BUILD.txt` | QA datasheet generation |

### Build Commands
```bash
# LanguageDataExporter
echo "Build NNN" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add -A && git commit -m "Build" && git push origin main

# QACompilerNEW
echo "Build NNN" >> QACOMPILER_BUILD.txt
git add -A && git commit -m "Build" && git push origin main
```

---

## Projects WITHOUT CI/CD (Manual/Scripts)

| Project | Purpose | How to Run |
|---------|---------|------------|
| **QuickTranslate** | Korean translation lookup | `python main.py` |
| **WordCountMaster** | Word count reports | `python main.py` |
| **GlossarySniffer** | Glossary extraction | `python glossary_sniffer_*.py` |
| **FactionListGenerator** | Faction list generation | `python main.py` |
| **DataListGenerator** | Data list generation | `python main.py` |
| **ExcelRegex** | Excel regex operations | `python main.py` |
| **MemoQUnconfirmedEraser** | MemoQ cleanup | `python main.py` |

---

## Project Details

### LanguageDataExporter
**Location:** `NewScripts/LanguageDataExporter/`
- Converts `languagedata_*.xml` → categorized Excel
- Two-tier clustering: STORY (VRS-ordered) + GAME_DATA
- Word count reports for LQA scheduling
- GUI + CLI modes
- **Agent:** `languagedataexporter-specialist`

### QACompilerNEW
**Location:** `NewScripts/QACompilerNEW/`
- Generates QA datasheets from game data
- Transfer workflow for updates
- Tracker for progress monitoring
- **Agent:** `qacompiler-specialist`

### QuickTranslate
**Location:** `NewScripts/QuickTranslate/`
- Korean ↔ target language lookup
- StringID search
- Reverse lookup (translation → Korean)
- Branch selector for dev/mainline

### WordCountMaster
**Location:** `NewScripts/WordCountMaster/`
- Word count reports across languages
- Category breakdown
- LQA scheduling support

### GlossarySniffer
**Location:** `NewScripts/GlossarySniffer/`
- Extract glossary terms from localization files
- Pattern matching for terminology

---

## File Structure Pattern

Most NewScripts projects follow:
```
ProjectName/
├── main.py              # Entry point
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── README.md            # Documentation
├── *.spec               # PyInstaller (if buildable)
├── installer/           # Inno Setup (if installer needed)
└── [modules]/           # Project-specific modules
```

---

## Key Files by Task

| Need | Check |
|------|-------|
| Add new project | Create folder, add main.py, requirements.txt |
| Build project | Check if trigger file exists, else manual PyInstaller |
| Debug project | Check config.py paths, run with `python main.py --help` |
| Add CI/CD | Create `.github/workflows/projectname-build.yml` |

---

## Common Patterns

### Settings/Config
Most projects use `settings.json` for runtime config:
```json
{
  "drive_letter": "F",
  "loc_folder": "F:\\perforce\\...",
  "export_folder": "F:\\perforce\\..."
}
```

### XML Parsing
Standard pattern from QACompiler:
- lxml with recovery mode
- Case-insensitive attributes
- XML sanitization for malformed files

### Excel Output
Standard pattern with openpyxl:
- Styled headers
- Auto-filter
- Freeze panes
- Category colors
