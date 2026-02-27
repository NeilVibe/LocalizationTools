# WIP: Session Recovery & Pending Commits

> **Created:** 2026-02-26 | **Status:** IN PROGRESS

---

## What Was Done (Previous Session — All COMPLETE, Just Uncommitted)

### 1. CLAUDE.md Condensation
- **Status:** ✅ COMPLETE — unstaged changes
- **What:** Major cleanup reducing verbosity by ~40% (485→220 lines)
- **Changes:** Removed verbose explanations, condensed to compact tables, added PRXR reference, added new glossary terms (PRXR, PM, RFC, NewScripts, QSS)
- **File:** `CLAUDE.md`

### 2. PRXR Protocol (Plan-Review-Execute-Review)
- **Status:** ✅ COMPLETE — untracked file
- **What:** Full protocol doc (106 lines): 7-step process, 5-agent review, when to use/skip, anti-patterns
- **File:** `docs/protocols/PRXR.md`

### 3. QuickTranslate: Non-Script Only Filter for Strict Mode
- **Status:** ✅ COMPLETE — unstaged changes across 3 files
- **What:** New checkbox in Strict mode that filters out SCRIPT categories (Dialog/Sequencer)
- **Files changed:**
  - `config.py` — Added `strict_non_script_only: False` default
  - `core/xml_transfer.py` — Filter logic + reporting (30 lines)
  - `gui/app.py` — Full UI wiring: checkbox, visibility, generate/transfer integration (66 lines)
- **How it works:**
  - Strict mode processes ALL entries by default (SCRIPT + NON-SCRIPT) = "FULL MODE"
  - Checkbox enabled → filters out Dialog/Sequencer = "NON-SCRIPT ONLY"
  - Setting persisted in `presubmission_settings.json`
  - Report shows `Script Skipped` count, match rate adjusted

### 4. Script No-Voice Extractor (QSS Tool)
- **Status:** ✅ COMPLETE — untracked file
- **What:** New 807-line QSS tool extracting SCRIPT LocStr without voice data
- **Files:**
  - `QuickStandaloneScripts/script_novoice_extractor.py` (untracked)
  - `QuickStandaloneScripts/QSS.md` (updated docs, unstaged)

---

## Commit Plan

### Commit 1: CLAUDE.md + PRXR Protocol
```
Files: CLAUDE.md, docs/protocols/PRXR.md
Message: "CLAUDE.md: condense to navigation hub + add PRXR protocol doc"
```

### Commit 2: QuickTranslate Non-Script Only
```
Files: config.py, core/xml_transfer.py, gui/app.py
Message: "QuickTranslate: add Non-Script Only filter for Strict match mode"
```

### Commit 3: Script No-Voice Extractor
```
Files: script_novoice_extractor.py, QSS.md
Message: "QSS: add Script No-Voice Extractor v1.0"
```

---

## QuickTranslate Match Type Reference

| Match Type | Scope | Use Case |
|---|---|---|
| **Substring** | Any (lookup only) | Quick Korean text search |
| **StringID-Only** | SCRIPT only (Dialog/Sequencer) | Script translation transfer |
| **Strict** | ALL (FULL MODE) or NON-SCRIPT (checkbox) | High-precision transfer with StringID+StrOrigin |
| **StrOrigin Only** | NON-SCRIPT only (auto-skip SCRIPT) | Fast game-data transfer without StringID |

### Strict Mode: FULL vs NON-SCRIPT

- **FULL MODE (default):** Processes BOTH script and non-script entries. Uses (StringID, StrOrigin) tuple matching.
- **NON-SCRIPT ONLY (checkbox):** Filters out Dialog/Sequencer before matching. Use when you want Strict precision but only for game-data entries (and handle scripts separately via StringID-Only).

---

*Last updated: 2026-02-26*
