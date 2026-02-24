# QuickTranslate Changelog

## v4.1 — 2026-02-25

### New Feature: "Unique Strings Only" Safe Merge (StrOrigin-Only Mode)

When using **StrOrigin Only** mode, a new checkbox appears: **"Unique strings only (skip duplicates)"**.

**Problem it solves:** StrOrigin-Only matches by Korean text without StringID verification. If the same Korean text appears on multiple rows in your source Excel with different corrections, all target entries get overwritten with one correction — potentially breaking previously correct translations.

**How it works:**
- Counts how many times each StrOrigin appears in your source corrections
- StrOrigin values appearing **exactly once** → merged normally
- StrOrigin values appearing **more than once** → skipped entirely
- Skipped entries are exported to a separate Excel report

**Output:** `KROnly_DuplicateStrings_{timestamp}.xlsx` in the FailedReports folder
- 3 columns: StrOrigin / Correction / StringID
- User deletes unwanted rows, keeps the correct corrections, re-submits via TRANSFER

**Two reports generated when using Unique Only:**
1. `FailureReport_{timestamp}.xlsx` — Global report (all failures, multi-sheet)
2. `KROnly_DuplicateStrings_{timestamp}.xlsx` — Actionable report (duplicates only, 3 columns)

---

## v4.0 — 2026-02-23

### Phase 3 Bug Fixes (39 items)

All Phase 3 bugs fixed across 4 sub-phases:

**3A–3C (20 bugs):**
- Column shift fix in Excel parsing
- StrOrigin Only silent failure fix
- StringID-Only StrOrigin requirement removal
- Dict-overwrite fixes across multiple modules
- Centralized `STRINGID_ATTRS` / `STRORIGIN_ATTRS` / `LOCSTR_TAGS` + `get_attr()` in `xml_parser.py`

**3D (19 polish/quality items):**
- Transfer report formatting improvements
- Edge case handling in fuzzy matching
- Log clarity improvements across all modules
- Error message consistency

### Features in v4.0

- **StrOrigin Only mode** — Match by Korean text alone, fan-out to all entries
- **Fuzzy matching** — FAISS + KR-SBERT two-pass matching for Strict and StrOrigin Only
- **SCRIPT category filtering** — StrOrigin Only auto-skips Dialog/Sequencer entries
- **Transfer scope toggle** — "Transfer ALL" vs "Only untranslated"
- **EventName resolution** — 3-step waterfall for Dialog/Sequencer StringID recovery
- **Failure reports** — XML per-language + multi-sheet Excel with summary/breakdown/details
- **Pre-submission checks** — Korean Check, Pattern Check, Quality Check (AI hallucination + wrong script)
- **staticinfo:knowledge skip rules** — Pattern Check skips these by default (toggle in settings)

---

## v3.x — Earlier

- Substring lookup mode
- StringID-Only mode
- Strict matching mode
- Excel/XML source support
- Recursive language detection
- Multi-language transfer
