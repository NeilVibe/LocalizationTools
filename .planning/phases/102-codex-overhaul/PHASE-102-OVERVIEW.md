# Phase 102: Codex Overhaul — COMPLETE (2026-03-30)

## Status: COMPLETE ✅

8 commits, 38+ files, +2151/-615 lines, 2 rounds of 8-agent review, 668 tests passing.
Build Light running: run 23748476606.

## What Was Delivered

### 1. Codex Mega Dropdown (Plan 102-02)
- Single "Codex" button with dropdown replaces 5 separate nav buttons
- 8 entries: Items, Characters, Audio, Regions, Quests, Skills, Gimmicks, Knowledge
- Click-outside close, active highlighting, no overlap with other dropdowns

### 2. Bulk Load All Pages (Plan 102-01 + 102-05)
- Removed pagination (offset/limit/has_more) from all 4 existing codex routes + schemas
- All pages: single fetch on mount, $derived client-side filtering, no infinite scroll

### 3. Quest Codex — Full QACompiler Graft (Plan 102-03 + 102-04)
- QuestEntry schema + _parse_quest_info() parser
- Quest type from subfolder: main/faction/challenge/minigame
- Faction subtypes by StrKey pattern: *_Daily→daily, *_Request→region, *_Situation→politics
- codex_quests.py route (3 endpoints: types, detail, list)
- QuestCodexPage.svelte with type tabs + faction subtabs

### 4. Skills + Gimmicks Codex (Plan 102-04 + 102-06)
- codex_skills.py + codex_gimmicks.py routes (2 endpoints each)
- SkillCodexPage.svelte + GimmickCodexPage.svelte (search + card grid)
- Knowledge-codex maps to existing CodexPage

### 5. Greedy DDS Image Resolution (Plan 102-07)
4-phase image lookup expanding MDG's logic:
- **Phase A:** KnowledgeEntry.ui_texture_name → DDS (MDG original)
- **Phase B:** Greedy XML attr scan (texture/icon/image/dds/portrait/thumbnail keywords on entity node + children) → DDS (NEW)
- **Phase C:** entity.knowledge_key → KnowledgeEntry → UITextureName → DDS (was MISSING)
- **Phase D:** Korean name+desc R1 fallback → inherit images from matching entity (EXPANDED)

R1 indexes ALL 7 entity types by BOTH name AND desc.
image_urls: List[str] in all schemas (stacked vertically in UI, deduplicated by stem).

### 6. CRITICAL Fixes
- **Audio NEVER linked:** SoundEventName from LocStr elements now extracted into D11
- **Categories WRONG:** D17 key now uses relative path (Sequencer/Dialog prefix preserved)
- **CategoryService race:** _mega_checked only set after confirmed MegaIndex build
- **CategoryService .lower():** C7 lookup was case-sensitive, mixed-case StringIDs always missed

### 7. Merge Bug Fixes
- BUG-16: 3 missing options in MergeToFileRequest + shared _apply_merge_pre_filters helper
- BUG-14: SSE streaming in FileMergeModal browser mode + cross-chunk eventType persistence
- merge_to_folder: now branches for stringid_only match_mode (was always strict engine)

## Files Created
- locaNext/src/lib/components/pages/QuestCodexPage.svelte
- locaNext/src/lib/components/pages/SkillCodexPage.svelte
- locaNext/src/lib/components/pages/GimmickCodexPage.svelte
- server/tools/ldm/routes/codex_quests.py
- server/tools/ldm/routes/codex_skills.py
- server/tools/ldm/routes/codex_gimmicks.py
- server/tools/ldm/schemas/codex_quests.py
- server/tools/ldm/schemas/codex_skills.py
- server/tools/ldm/schemas/codex_gimmicks.py

## Files Modified (key ones)
- server/tools/ldm/services/mega_index_data_parsers.py (SoundEventName + relative path)
- server/tools/ldm/services/mega_index_entity_parsers.py (quest parser + _collect_texture_refs)
- server/tools/ldm/services/mega_index_builders.py (4-phase DDS + R1 name+desc)
- server/tools/ldm/services/mega_index_schemas.py (QuestEntry)
- server/tools/ldm/services/category_service.py (.lower() + _mega_checked)
- server/tools/ldm/routes/merge_to_disk.py (pre-filters + match_mode branching)
- locaNext/src/routes/+layout.svelte (dropdown nav)
- locaNext/src/lib/components/ldm/FileMergeModal.svelte (SSE streaming)
- All 4 existing codex routes + schemas (pagination removed, image_urls)
- All 3 detail components (multi-image stacking)
