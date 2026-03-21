# Project Research Summary

**Project:** LocaNext v5.0 — Offline Bundle + Full Codex Expansion
**Domain:** Game Localization CAT Tool — Entity Codex UIs (Audio/Item/Character/Region) + Production Offline Bundle
**Researched:** 2026-03-21
**Confidence:** HIGH (all research grounded in direct codebase analysis and battle-tested internal docs)

## Executive Summary

LocaNext v5.0 is a feature expansion to an existing production Electron+FastAPI CAT tool. The core pattern is "port proven logic from existing NewScripts tools (MapDataGenerator, QACompiler) into new Svelte 5 UIs wired to new FastAPI services." No greenfield work is needed — every technology is already installed, every data structure already analyzed, and most parsing logic already written in sibling tools. The recommended approach is a dependency-ordered phase structure: extract shared infrastructure (PerforcePathService, AICapabilityService) first, then build each Codex type as an independent service composing from shared primitives, and package last.

The most important architectural insight from research is that GameData (Codex entities, world map nodes, StaticInfo XML) is file-based and intentionally bypasses the Repository/DB layer entirely. New Audio/Item/Character/Region Codex services must follow the same filesystem-scanner + in-memory-registry pattern that CodexService already uses — no CodexRepository classes or SQLite schemas for game entities. The existing split between SQLite offline (translation data only) and filesystem (game data) is the correct architecture and must be maintained strictly.

The primary risk cluster is the offline bundle: PyInstaller DLL placement for FAISS and Model2Vec, SQLite WAL mode for concurrent writes, and UI-level AI degradation (not just API-level try/catch). Research identified 5 critical pitfalls, all with well-documented prevention patterns drawn from existing project documentation. The offline packaging phase must be built last with a mandatory fresh-machine smoke test before any release.

## Key Findings

### Recommended Stack

No new dependencies are required for v5.0. The full stack needed is already installed: Model2Vec 0.7.0 (offline embeddings, bundleable at 128MB), faiss-cpu 1.8.0, vgmstream-cli r1999+ (already in MapDataGenerator/tools/), Pillow 12.1.0 (DDS support built-in since 9.x), and all d3 libraries (d3-zoom, d3-force, d3-selection, d3-drag) already in locaNext/package.json. The only required action is creating `tools/download_model2vec.py` to pre-download model weights at build time and updating electron-builder `extraResources` to bundle the Model2Vec model directory and vgmstream binaries.

**Core technologies:**
- **Model2Vec 0.7.0 + bundled weights**: Offline semantic search (~128MB, no torch dependency, light build safe) — already working via `embedding_engine.py` light mode detection
- **vgmstream-cli r1999+**: WEM-to-WAV conversion (existing in repo at MapDataGenerator/tools/, just needs copying to `bin/vgmstream/` and bundling in Electron extraResources)
- **faiss-cpu 1.8.0**: Vector search for all Codex types — already working, light build safe, no CUDA
- **d3-zoom/force/selection/drag 3.0.0**: Interactive region map — already installed and used for WorldMapPage
- **SQLite via aiosqlite**: Offline entity cache extension (same DB as translation data, schema extension only)
- **pathlib + settings.json**: Perforce path resolution — proven pattern in MapDataGenerator config.py and QACompiler config.py

### Expected Features

All features derived from direct source code analysis of QACompiler generators and MapDataGenerator core modules. Confidence is HIGH.

**Must have (table stakes):**
- Entity card grid with search — reuse existing `CodexPage.svelte` + `CodexCard.svelte` pattern across all 4 new types
- DDS image preview per entity — already built (`/api/ldm/media/dds` endpoint exists, Pillow handles DDS natively)
- Entity detail panel with type-specific fields — extend existing `CodexEntityDetail.svelte`
- Text search (contains/exact + semantic) — port MapDataGenerator's `SearchEngine` multi-field pattern
- Category/group filtering — Item GroupInfo hierarchy, Character filename groups, Region FactionGroup tabs
- Offline-capable core browsing — FAISS + Model2Vec in light bundle, Qwen gracefully absent
- Perforce path configuration — drive letter + branch selection, port from MapDataGenerator settings

**Should have (differentiators):**
- Audio Codex with inline WEM playback — unique among CAT tools; EventName->StringId->StrOrigin chain from AudioIndex
- StringID->Audio inline player in LDM translation grid — click a cell, hear the voice line with script text overlay
- Interactive Region map from WorldPosition data — real FactionNode coordinates via d3-zoom on existing WorldMap pattern
- Knowledge cross-reference chains — 7-pass resolution (Item), 5-pass (Character), displayed as tabs in detail view
- Graceful AI degradation with capability badges — `AIAvailabilityStore` in Svelte, three-state UI per AI-dependent component

**Defer (v2+):**
- VRS chronological ordering — nice audio UX but not critical for MVP
- Shop + SceneObjectData positions on region map — complex 3-hop position chain (KnowledgeInfo -> UIMapTextureInfo -> LevelGimmickSceneObjectInfo)
- Multi-language audio folder switching — adds UI complexity; default to project language
- Full Qwen AI in offline bundle — 2.3GB defeats light bundle purpose; Model2Vec only

### Architecture Approach

The architecture follows composition over extension: each new Codex type gets its own dedicated service class that uses the core `CodexService` registry but owns its data sources, initialization, and API routes. A shared `PerforcePathService` extracted from `MapDataService` provides unified path resolution. An `AICapabilityService` provides runtime engine detection. The existing Repository/Factory pattern for translation data is untouched — GameData remains file-based with in-memory registries only. No new Repository interfaces are needed, which dramatically reduces implementation scope.

**Major components (new or significantly modified):**
1. **PerforcePathService** — Extracted from MapDataService; single source for all Perforce path templates, drive/branch substitution; consumed by all 4 Codex services and existing MapDataService
2. **AICapabilityService** — Runtime detection of Model2Vec, FAISS, Ollama, TTS availability; feeds `AIAvailabilityStore` Svelte global store
3. **AudioCodexService** — WEM scanning + EventName->StringId->StrOrigin chain (port from MapDataGenerator's AudioIndex in linkage.py)
4. **ItemCodexService** — ItemGroupInfo hierarchy + 7-pass knowledge resolution (port data extraction only from QACompiler item.py — no Excel output logic)
5. **CharacterCodexService** — Filename-based grouping + knowledge children (port from QACompiler character.py)
6. **RegionCodexService** — FactionNode tree + WorldPosition data + shop cross-refs (port from QACompiler region.py)
7. **4x Svelte 5 Codex Pages** — All extend generic `CodexLayout.svelte` with slots to avoid 70% code duplication

**File organization for new services:**
```
server/tools/ldm/services/
  perforce_path_service.py     NEW — extracted from mapdata_service.py
  ai_capability_service.py     NEW — runtime engine detection
  codex_audio_service.py       NEW — AudioIndex chain
  codex_item_service.py        NEW — ItemGroupInfo + knowledge resolution
  codex_character_service.py   NEW — filename-based grouping
  codex_region_service.py      NEW — FactionNode tree + WorldPosition
```

### Critical Pitfalls

1. **PyInstaller DLL placement for FAISS/Model2Vec** — Use `hiddenimports` + `copy_metadata` patterns from QuickTranslate/docs/PYINSTALLER_ML_BUNDLING.md. Never `collect_all()`. Mandatory fresh-machine smoke test before release. Error is invisible with `console=False`.
2. **AI features hard-crashing in offline bundle** — Build `AICapabilityService` + `AIAvailabilityStore` in Phase 1 before any Codex UI. Every AI-dependent component must have three states: available/loading/unavailable. Degradation must be at the UI level, not just the API level.
3. **SQLite concurrent write locks** — Enable `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=10000` in Phase 1. Route ALL writes through FastAPI only. Validate before Codex indexing is built. "database is locked" can cause silent optimistic UI failures.
4. **Perforce path resolution without Perforce client** — Add "Data Source" wizard on first launch with Perforce workspace / manual folder / demo mode options. Never crash on missing paths — show placeholder with "Configure data source" link.
5. **Duplicating Perforce path templates across services** — Extract `PerforcePathService` BEFORE any new Codex service is written. If `PATH_TEMPLATES` appears in any new file, stop and refactor.

## Implications for Roadmap

Based on combined research, the dependency graph is clear and dictates a strict 6-phase structure. Foundation must precede Codex UIs. Audio is highest demo-value differentiator. Item and Character can parallelize. Region is most complex (hierarchical tree + map integration). Packaging is last with a hard quality gate.

### Phase 1: Foundation Infrastructure
**Rationale:** Four of five critical pitfalls (#2, #3, #4, #5) are eliminated entirely in this phase. All subsequent Codex services depend on PerforcePathService and AICapabilityService. Building these later multiplies refactoring cost across 4+ services.
**Delivers:** `PerforcePathService` (extracted from MapDataService), `AICapabilityService` + `/api/ldm/capabilities` endpoint, `AIAvailabilityStore` (Svelte global), SQLite WAL mode + busy_timeout, "Data Source" configuration wizard UI, `LIGHT_BUILD` env var, `download_model2vec.py` pre-download script
**Addresses:** Offline capability, Perforce path configuration (table stakes)
**Avoids:** Pitfalls #2 (AI hard crash), #3 (SQLite locks), #4 (missing Perforce paths), #5 (path duplication)

### Phase 2: Audio Codex
**Rationale:** Highest unique demo value — no other CAT tool has WEM-to-WAV playback with script lines. Depends only on Phase 1. MediaConverter already exists, making this lower-risk than complexity implies.
**Delivers:** `AudioCodexService` (WEM scan + AudioIndex chain ported from MapDataGenerator/core/linkage.py), `AudioCodexPage.svelte` (browse/search/play/category tree), StringID->Audio inline player in LDM grid
**Uses:** vgmstream-cli (existing), MediaConverter.convert_wem_to_wav() (existing), PerforcePathService (Phase 1)
**Avoids:** Pitfalls #6 (vgmstream binary distribution — use server-side streaming, not MapDataGenerator's winsound), #7 (Chrome audio cache — `?v=${Date.now()}` + `{#key}` from day one, `Cache-Control: no-cache` on stream endpoint)

### Phase 3: Item Codex
**Rationale:** Highest visual impact after Audio (items have DDS images and rich knowledge trees). Most complex generator (7 knowledge passes, depth clustering) — tackle while team context from QACompiler analysis is fresh. Depends on Phase 1 only.
**Delivers:** `ItemCodexService` (port item.py data extraction only — zero Excel output logic), `ItemCodexPage.svelte` with category hierarchy nav + knowledge tabs
**Uses:** DDS preview API (existing `/api/ldm/media/dds`), CodexService registry, PerforcePathService
**Avoids:** Pitfall #9 (God-class — separate service, not extending CodexService), #10 (over-porting — if any new file imports xlsxwriter or mentions "sheet"/"column"/"header", strip it)

### Phase 4: Character Codex
**Rationale:** Simpler than Item (no depth clustering, no InspectData, filename-based grouping). Can parallelize with Phase 3 if team bandwidth allows — they share zero data sources. Depends on Phase 1 only.
**Delivers:** `CharacterCodexService` (port character.py — filename pattern grouping, knowledge children), `CharacterCodexPage.svelte` with NPC/MONSTER/etc. tabs and Race/Gender/Age/Job detail fields
**Uses:** DDS preview API (existing), CodexService registry, PerforcePathService
**Avoids:** Same pitfalls as Phase 3 (same composition pattern)

### Phase 5: Region Codex + Map
**Rationale:** Most architecturally complex (hierarchical FactionNode tree + WorldPosition coordinates + shop cross-refs). Extends existing WorldMapPage — requires understanding the map integration. Must come after team understands Codex composition pattern from Phases 3-4.
**Delivers:** `RegionCodexService` (port region.py — FactionGroupData tree + WorldPosition parsing), `RegionCodexPage.svelte` with tree navigation + mini-map overlay using real coordinates, WorldMapPage integration
**Uses:** d3-zoom (existing), WorldMapService (existing), PerforcePathService
**Avoids:** Pitfall #4 (missing Perforce paths — Data Source wizard from Phase 1 handles demo fallback)

### Phase 6: AI Degradation + Offline Bundle Packaging
**Rationale:** Packaging and full degradation validation require all features to exist. PyInstaller DLL pitfall is the highest-risk item — must have a fresh-machine test gate. Cannot validate light build flow until all Codex services are complete.
**Delivers:** Full AI degradation wrap across all 4 Codex UIs (`{#if capabilities.X}` guards, three-state components), FAISS index disk caching (mtime-based invalidation to avoid 30s startup block), electron-builder `extraResources` config (Model2Vec + vgmstream), PyInstaller hiddenimports for FAISS/Model2Vec (never `collect_all()`), light build CI variant, fresh-machine E2E test gate
**Avoids:** Pitfall #1 (PyInstaller DLLs — hiddenimports not collect_all; mandatory fresh-machine test), #8 (Codex init blocking — background asyncio task + FAISS disk cache), #11 (light/full drift — runtime detection, not compile-time ifdef), #15 (Electron build size explosion — strip debug symbols, exclude unused numpy subpackages)

### Phase Ordering Rationale

- **Foundation first** because 4 of 5 critical pitfalls originate in missing shared infrastructure. Skipping this phase means revisiting every Codex service later.
- **Audio second** because it's the clearest differentiator (no competitor CAT tool has it) and the data chain is fully analyzed and already implemented in MapDataGenerator — porting is low-risk with high demo impact.
- **Item before Character** because Item has the most complex generator (7 knowledge passes vs. Character's simpler structure) — tackle complexity early while the QACompiler analysis is fresh.
- **Character can parallelize with Item** — zero shared data sources, both depend only on Phase 1.
- **Region last among Codex types** because it requires WorldMapPage integration (more touch points) and the tree structure is the most complex cross-reference in any generator.
- **Packaging last** — cannot validate full offline flow until all features exist; fresh-machine test is a release gate, not an intermediate step.

### Research Flags

Phases that need deeper investigation during planning:

- **Phase 1 (SQLite WAL mode):** Confirm current offline SQLite connection strings and `aiosqlite` usage support WAL mode without breaking existing repo implementations. Verify whether `PRAGMA journal_mode=WAL` must be issued at DB creation or can be applied to existing DBs.
- **Phase 2 (StringID->Audio reverse lookup):** The LDM grid integration requires mapping StrOrigin values back through AudioIndex (StrOrigin -> EventName -> WEM path). Validate the reverse lookup chain against real data before coding — this direction is not explicitly implemented in MapDataGenerator.
- **Phase 5 (coordinate normalization for Region map):** FactionNode WorldPosition is game-space (x, y, z) floats. Validate how existing WorldMapPage normalizes coordinates to SVG viewport before building Region Codex map overlay.
- **Phase 6 (Electron + Python packaging mechanism):** STACK.md says Electron bundles Python via `extraResources` and explicitly excludes PyInstaller for LocaNext. Clarify the exact packaging chain — is the Python backend a frozen PyInstaller exe inside Electron's extraResources, or a raw interpreter + scripts?

Phases with well-documented patterns (can skip `/gsd:research-phase`):

- **Phase 3 (Item Codex):** item.py source fully analyzed (1080 lines), data structures documented in FEATURES.md, composition pattern defined in ARCHITECTURE.md. No research needed.
- **Phase 4 (Character Codex):** character.py source fully analyzed (594 lines), simpler than Item, same established composition pattern. No research needed.
- **Audio vgmstream integration (Phase 2):** Fully implemented and tested in MapDataGenerator/core/audio_handler.py + MediaConverter. Port is mechanical. No research needed beyond reverse lookup validation.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every technology is already installed and version-pinned. Research verified source files directly. No new dependencies needed. |
| Features | HIGH | All features derived from direct source code analysis of QACompiler generators (item.py 1080 lines, character.py 594 lines, region.py 1307 lines) and MapDataGenerator (linkage.py 1326 lines). No guesswork. |
| Architecture | HIGH | Based on deep codebase analysis of all relevant server modules. Factory pattern, CodexService registry, MediaConverter all read directly. Composition pattern clearly defined. |
| Pitfalls | HIGH | All critical pitfalls have project-internal documentation (PyInstaller ML bundling guide, Chrome audio cache bug, offline architecture docs). Not theoretical — these bugs have been hit in production before. |

**Overall confidence:** HIGH

### Gaps to Address

- **Offline packaging mechanism (Electron + Python):** STACK.md explicitly says Electron bundles Python via `extraResources` and excludes PyInstaller for LocaNext. However, Phase 6 planning will need to clarify the exact chain. Address in Phase 6 planning.
- **SQLite schema for offline entity caching:** STACK.md recommends caching parsed XML entity data in SQLite for faster cold starts, but the table schema is unspecified. Design this during Phase 1 planning.
- **Coordinate normalization for Region map:** WorldPosition data is game-space coordinates. The transform to SVG viewport is not documented. Validate against existing WorldMapPage normalization during Phase 5 planning.
- **Audio language default behavior:** FEATURES.md defers multi-language audio switching and says "default to project language." Confirm this works correctly for all 3 audio folder paths (English(US)/Korean/Chinese(PRC)) during Phase 2 planning.

## Sources

### Primary (HIGH confidence)
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/item.py` (1080 lines) — Item data structures and knowledge resolution passes
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/character.py` (594 lines) — Character grouping and knowledge children
- `RessourcesForCodingTheProject/NewScripts/QACompilerNEW/generators/region.py` (1307 lines) — FactionNode tree and WorldPosition parsing
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/linkage.py` (1326 lines) — AudioIndex chain and LinkageResolver pattern
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/core/audio_handler.py` (337 lines) — WEM-to-WAV playback architecture
- `RessourcesForCodingTheProject/NewScripts/MapDataGenerator/config.py` (667 lines) — Perforce path templates and settings persistence pattern
- `server/tools/ldm/services/codex_service.py` — Existing Codex registry and FAISS integration
- `server/tools/ldm/services/mapdata_service.py` — PATH_TEMPLATES pattern and Perforce path resolution
- `server/tools/shared/embedding_engine.py` — Light mode detection and Model2Vec local path resolution
- `server/tools/ldm/services/media_converter.py` — DDS/WEM conversion and vgmstream integration
- `server/repositories/factory.py` — ARCH-001 three-mode repository factory
- `QuickTranslate/docs/PYINSTALLER_ML_BUNDLING.md` — PyInstaller ML bundle patterns (battle-tested)
- `feedback_chrome_audio_cache.md` / `docs/history/DOC-002_CHROME_AUDIO_CACHE_BUG.md` — Chrome audio cache bug (confirmed production issue)

### Secondary (MEDIUM confidence)
- [SQLite WAL mode documentation](https://sqlite.org/lockingv3.html) — concurrent write locking patterns
- [SQLite concurrent writes and WAL](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) — WAL mode behavior under write load
- [electron-builder extraResources](https://www.electron.build/contents.html) — bundling pattern for binaries

### Tertiary (LOW confidence)
- [PyInstaller troubleshooting](https://pyinstaller.org/en/stable/when-things-go-wrong.html) — DLL placement edge cases (validate against fresh-machine test, not documentation alone)

---
*Research completed: 2026-03-21*
*Ready for roadmap: yes*
