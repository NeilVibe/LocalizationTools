---
phase: 25-comprehensive-api-e2e-testing
plan: 02
subsystem: testing
tags: [fixtures, excel, xml, multilingual, br-tags, upload, xlsxwriter, lxml]

requires:
  - phase: 25-01
    provides: "Core test fixtures (mock gamedata, sample files)"
provides:
  - "8 upload test fixtures (Excel, TXT/TSV, XML) for API upload/merge testing"
  - "3 new language data files (JPN, DEU, ESP) for multilingual testing"
  - "Generation scripts for reproducible fixture creation"
affects: [25-03, 25-04]

tech-stack:
  added: [xlsxwriter, openpyxl]
  patterns: [EU 14-column Excel format, LocStr XML wrapper format, tab-delimited upload format]

key-files:
  created:
    - tests/fixtures/mock_uploads/generate_excel_fixtures.py
    - tests/fixtures/mock_uploads/eu_14col_sample.xlsx
    - tests/fixtures/mock_uploads/eu_14col_korean.xlsx
    - tests/fixtures/mock_uploads/eu_14col_brtags.xlsx
    - tests/fixtures/mock_uploads/tab_delimited_sample.txt
    - tests/fixtures/mock_uploads/tab_delimited_korean.tsv
    - tests/fixtures/mock_uploads/locstr_upload_characterinfo.xml
    - tests/fixtures/mock_uploads/locstr_upload_questinfo.xml
    - tests/fixtures/mock_uploads/locstr_upload_mixed_brtags.xml
    - tests/fixtures/mock_gamedata/stringtable/loc/languagedata_jpn.xml
    - tests/fixtures/mock_gamedata/stringtable/loc/languagedata_deu.xml
    - tests/fixtures/mock_gamedata/stringtable/loc/languagedata_esp.xml
    - tests/fixtures/mock_gamedata/stringtable/loc/generate_multilingual.py
  modified: []

key-decisions:
  - "xlsxwriter for Excel generation (project convention: xlsxwriter for writing, openpyxl for reading)"
  - "Generation scripts kept alongside fixtures for reproducibility"
  - "br-tags in XML use XML-escaped format in attribute values (matching production behavior)"

patterns-established:
  - "EU 14-column format: StrOrigin|ENG|Str|Correction|Text State|STATUS|COMMENT|MEMO1|MEMO2|Category|FileName|StringID|DescOrigin|Desc"
  - "LocStr upload XML uses LanguageData root with LocStr elements using StrKey attribute"
  - "Multilingual files share identical StringId set for cross-language comparison testing"

requirements-completed: [TEST-E2E-03, TEST-E2E-04]

duration: 8min
completed: 2026-03-15
---

# Phase 25 Plan 02: Upload Fixtures & Multilingual Data Summary

**8 upload fixtures (3 Excel EU-14col, 2 TXT/TSV, 3 LocStr XML) plus 3 new language data files (JPN/DEU/ESP) with 704 entries each**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T22:30:34Z
- **Completed:** 2026-03-15T22:38:30Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments
- 3 EU 14-column Excel files with 50/30/25 rows covering mixed entities, Korean source, and br-tag content
- 2 tab-delimited files with Korean Jamo, CJK characters, and full-width punctuation
- 3 LocStr XML files with character, quest, and mixed br-tag entries
- 3 multilingual language data files (JPN/DEU/ESP) with 704 entries each, 37% containing br-tags
- Generation scripts for both Excel and multilingual XML fixtures

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EU 14-column Excel upload fixtures** - `a50d8303` (feat)
2. **Task 2: Create TXT/TSV and LocStr XML upload fixtures** - `25d4572d` (feat)
3. **Task 3: Expand multilingual language data files** - `99b2a02d` (feat)

## Files Created/Modified
- `tests/fixtures/mock_uploads/generate_excel_fixtures.py` - Reproducible Excel fixture generator
- `tests/fixtures/mock_uploads/eu_14col_sample.xlsx` - 50 rows mixed entity data
- `tests/fixtures/mock_uploads/eu_14col_korean.xlsx` - 30 rows Korean source with Jamo
- `tests/fixtures/mock_uploads/eu_14col_brtags.xlsx` - 25 rows with br-tag multiline content
- `tests/fixtures/mock_uploads/tab_delimited_sample.txt` - 40 rows tab-delimited upload format
- `tests/fixtures/mock_uploads/tab_delimited_korean.tsv` - 30 rows Korean with CJK punctuation
- `tests/fixtures/mock_uploads/locstr_upload_characterinfo.xml` - 20 character LocStr entries
- `tests/fixtures/mock_uploads/locstr_upload_questinfo.xml` - 15 quest LocStr entries
- `tests/fixtures/mock_uploads/locstr_upload_mixed_brtags.xml` - 25 mixed entries all with br-tags
- `tests/fixtures/mock_gamedata/stringtable/loc/languagedata_jpn.xml` - 704 Japanese entries
- `tests/fixtures/mock_gamedata/stringtable/loc/languagedata_deu.xml` - 704 German entries
- `tests/fixtures/mock_gamedata/stringtable/loc/languagedata_esp.xml` - 704 Spanish entries
- `tests/fixtures/mock_gamedata/stringtable/loc/generate_multilingual.py` - Multilingual generator

## Decisions Made
- Used xlsxwriter for Excel generation per project convention (xlsxwriter writes, openpyxl reads)
- Kept generation scripts alongside fixtures for reproducibility and future updates
- br-tags stored as `&lt;br/&gt;` in XML attribute values matching production lxml behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Upload fixtures ready for API upload/merge endpoint testing
- 6 language data files covering KOR/ENG/FRE/JPN/DEU/ESP for multilingual round-trip tests
- All fixtures contain realistic game localization content with br-tags for preservation testing

## Self-Check: PASSED

All 11 created files verified present. All 3 task commits verified in git log.

---
*Phase: 25-comprehensive-api-e2e-testing*
*Completed: 2026-03-15*
