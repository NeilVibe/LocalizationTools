# NewScripts Session Context

> Last Updated: 2026-02-28

---

## 2026-02-28: QuickTranslate — Unbalanced Bracket Check (CRITICAL)

Added stack-based `{`/`}` bracket validation to the pre-submission pattern checker.

### What It Does

- Checks every `Str` (translation) for unbalanced curly brackets
- Catches: missing `}`, missing `{`, wrong nesting like `}text{`
- Runs on **ALL entries** including staticinfo:knowledge (brackets are always critical)
- Outputs separate `MissingBrackets_{LANG}.xml` for immediate focus on critical issues
- Also included in the combined `pattern_errors_{LANG}.xml`

### Output Structure

```
CheckResults/
├── PatternErrors/pattern_errors_ENG.xml   (all issues)
├── MissingBrackets/MissingBrackets_ENG.xml (critical only)
└── ...
```

### Files Changed

| File | Change |
|------|--------|
| `QuickTranslate/core/checker.py` | `_has_unbalanced_brackets()` + 3-tuple return + separate output |
| `QuickTranslate/gui/app.py` | Summary formatting + CRITICAL log lines + `_check_all` totals |

### Build & Review

- GitHub Build: **SUCCESS** (11m7s)
- Code reviewed: 2 issues found + fixed (bracket check should bypass staticinfo skip; `_check_all` summary lumped brackets into pattern count)

---

## 2026-02-27: ExtractAnything — Extract Tab (Build 5)

Added a general-purpose **Extract** tab — pick a source folder, extract all LocStr entries, output Excel + XML per language.

### What It Does

- **Source folder picker** — any folder with language XMLs/Excel
- **Category filter** — All / SCRIPT only / NON-SCRIPT only (uses EXPORT index)
- **Path filter** — reuses global Path Filter from bottom bar
- **Output** — `EXTRACT_{LANG}.xlsx` + `EXTRACT_{LANG}.xml` per language

EXPORT index loaded best-effort: populates Category column even without active filter.

### Files Changed

| File | Change |
|------|--------|
| `ExtractAnything/gui/extract_tab.py` | **NEW** — Extract tab (follows NoVoice pattern) |
| `ExtractAnything/gui/app.py` | Register ExtractTab as first tab |

### Build & Review

- GitHub Build 5: **SUCCESS** (2m10s)
- Code reviewed: 1 bug found + fixed (category column empty when no filter active)

---

## 2026-02-26: ExtractAnything — Python Compatibility (Builds 2-4)

Fixed two portability issues that broke ExtractAnything on end-user machines:

1. **`from __future__ import annotations`** added to all 30 `.py` files — fixes `Path | None` crash on Python < 3.10
2. **Direct imports** replacing relative imports — fixes breakage when folder is renamed (e.g. `ExtractAnything_v26.227_Source`)

### Protocol Established

These two rules now apply to ALL NewScripts projects. See `ExtractAnything/docs/PYTHON_COMPATIBILITY_PROTOCOL.md`.

---

## 2026-02-25: QACompiler — NewCharacter + NewRegion Generators

- **newcharacter.py**: row-per-text, 5 rows/char, 8 columns
- **newregion.py**: rewritten — exact copy of region.py + DisplayName from RegionInfo
- Region knowledge lookup fix: `build_knowledge_name_lookup()` returns `(Name, Desc)` tuples
- Pipeline config added to all 5 files (config, generators/__init__, main, populate_new, coverage)

---

## 2026-02-24: QACompiler — Consumer + Dedup + StringID + NewItem

- StringIdConsumer system for all 12 generators
- NewItem pipeline integration (generator + populate + coverage + CLI)
- RewardKnowledgeKey support across item/newitem/itemknowledgecluster/newcharacter/newregion

---

## 2026-02-23: QuickTranslate — Phase 3 Bug Fixes Complete

All 39 items fixed (3A/3B/3C/3D). Centralized `STRINGID_ATTRS`/`STRORIGIN_ATTRS`/`LOCSTR_TAGS` + `get_attr()` in `xml_parser.py`.

---

## Project Build Status

| Project | CI | Latest Build | Status |
|---------|-----|-------------|--------|
| **ExtractAnything** | GitHub Actions | Build 5 | SUCCESS |
| **QACompiler** | GitHub Actions | — | — |
| **QuickTranslate** | GitHub Actions | Bracket check | SUCCESS |
| **QuickSearch** | GitHub Actions | — | — |
| **LanguageDataExporter** | GitHub Actions | — | — |
