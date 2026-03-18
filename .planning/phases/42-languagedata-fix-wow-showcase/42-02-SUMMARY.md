# Phase 42 Plan 02 Summary: 3-Format Mock Data + TM

**Status:** COMPLETE
**Duration:** ~15 min

## Created Files
1. **showcase_ui_strings.xlsx** (28 rows) — UI strings: menus, buttons, messages, tooltips
2. **showcase_dialogue.txt** (28 rows) — Character dialogue: 5 characters × ~6 lines each
3. **showcase_items.loc.xml** (29 rows) — Items, characters, regions, skills with `<br/>` tags

## Mock Data Stats
- **85 total strings** across 3 formats
- Cross-references Codex universe: Varon, Kira, Grimjaw, Lune, Drakmar
- Items: Blackstar Sword, Moonstone Amulet, Plague Cure
- Regions: Blackstar Village, Forgotten Fortress, Ironpeak Mountains
- Mixed statuses: Human-Reviewed, AI-Translated, Machine-Translated, Needs-Review

## TM Created
- **Showcase TM** (id=469): 33 entries from Excel
- **Showcase Dialogue TM** (id=470): 28 entries from TXT
- **Showcase Items TM** (id=471): 29 entries from XML
- **Total: 90 TM entries**

## Project
- "Showcase Demo" project (id=287) under CD platform
- All 3 files uploaded and visible in file explorer
- TMs 469 + 471 activated for file 314 (XML)

## Files Created
- `tests/fixtures/mock_gamedata/localization/generate_showcase_data.py`
- `tests/fixtures/mock_gamedata/localization/showcase_ui_strings.xlsx`
- `tests/fixtures/mock_gamedata/localization/showcase_dialogue.txt`
- `tests/fixtures/mock_gamedata/localization/showcase_items.loc.xml`
- `server/tools/ldm/services/mock_tm_loader.py`

## Verification
- All 3 files open in grid with correct columns
- Screenshot: `phase42-plan02-showcase-xml-grid.png`
