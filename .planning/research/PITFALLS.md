# Domain Pitfalls

**Domain:** Offline Production Bundle + Full Codex Expansion for Electron+FastAPI Desktop App
**Researched:** 2026-03-21
**Milestone:** v5.0

---

## Critical Pitfalls

Mistakes that cause rewrites, build failures, or production crashes.

### Pitfall 1: PyInstaller FAISS/Model2Vec DLL Placement (collect_all Trap)

**What goes wrong:** FAISS ships vendored DLLs in `faiss_cpu.libs/`. Model2Vec depends on tokenizers (Rust binary `.pyd`). Using `collect_all()` for either preserves subdirectory structure, placing DLLs where Windows secure DLL search cannot find them. Build works on dev machine (VC++ Redist installed system-wide), crashes on fresh machines with `WinError 1114`.

**Why it happens:** Same root cause as the torch c10.dll disaster documented in `QuickTranslate/docs/PYINSTALLER_ML_BUNDLING.md`. Windows 3.8+ secure DLL search ignores PATH for implicit DLL dependencies. DLLs in subdirectories cannot find vcruntime140.dll in a parent directory.

**Consequences:** App crashes on launch on target machines. Error invisible when `console=False`. Days of debugging.

**Prevention:**
- FAISS: Use `hiddenimports=['faiss', 'faiss.swigfaiss', 'faiss.swigfaiss_avx2', 'faiss.loader']` + `copy_metadata('faiss-cpu')` -- binary analysis places DLLs flat
- Model2Vec: Use `hiddenimports=['tokenizers', 'model2vec', 'model2vec.distill', 'model2vec.model']` + `copy_metadata('tokenizers', 'model2vec')`
- NEVER `collect_all('faiss')`, `collect_all('faiss_cpu')`, or `collect_all('tokenizers')`
- Bundle Model2Vec model directory as data: `datas=[('path/to/model', 'model2vec_model')]`
- Include the 3-layer runtime hook (add_dll_directory + PATH + ctypes pre-load)
- Add crash logging + tkinter error dialog for `console=False` builds
- Post-build smoke test: `python -c "from model2vec import StaticModel; import faiss"` in frozen exe
- **Test on a FRESH Windows machine** -- dev machine always works

**Detection:** App crashes immediately on launch. Codex search returns empty. TM match percentages are 0. Check `crash.log` or run with `console=True`.

**Phase:** Bundling/packaging phase. Block release on fresh-machine test.

---

### Pitfall 2: AI Features Hard-Crashing in Offline Bundle

**What goes wrong:** Codex UI calls Ollama/Qwen endpoint, gets connection refused, shows unhandled error or blank page. "Graceful degradation" implemented as try/catch around Ollama calls, but UI still shows AI-related elements that do nothing when clicked.

**Why it happens:** Developer tests with Ollama running locally. Forgets offline bundle has no Qwen. Frontend assumes AI endpoints always return data. Degradation implemented at API level but NOT at UI level.

**Consequences:** Offline bundle appears broken. Executive demo fails. Users click "Generate Summary" and nothing happens.

**Prevention:**
- Create `AICapabilityService` in Phase 1. Backend endpoints return structured "unavailable" responses (not 500 errors)
- Create global `AIAvailabilityStore` in Svelte tracking each engine:
  ```
  { qwen: 'unavailable', faiss: 'available', tts: 'unavailable', model2vec: 'available' }
  ```
- Probe AI endpoints at startup and periodically (every 60s)
- Every AI-dependent UI section uses `{#if capabilities.ai_summary}` guards
- Each AI-powered component shows three states: available, loading, unavailable (grayed + tooltip)
- Light build should set `AI_FEATURES_ENABLED=false` to disable AI UI entirely
- **Test the degraded path**: run with `LOCANEXT_LIGHT_BUILD=true` and Ollama stopped. Every page must render cleanly

**Detection:** Start app without Ollama. Every page with AI features should show clear "unavailable" state, not empty/broken.

**Phase:** Graceful degradation phase. Must be a separate dedicated phase, built before feature phases.

---

### Pitfall 3: SQLite Concurrent Access from Electron + FastAPI

**What goes wrong:** In offline-only bundle, both Electron renderer (via IPC) and embedded FastAPI write to same SQLite database. SQLite allows only one writer. Under load (rapid cell edits + Codex indexing + TM operations), "database is locked" errors appear.

**Why it happens:** Current offline architecture uses SQLite as simple fallback behind PostgreSQL. In v5.0 offline-only mode, SQLite IS the primary database. Write volume increases dramatically.

**Consequences:** Random "database is locked" errors. Optimistic UI shows success but write silently fails.

**Prevention:**
- Enable WAL mode: `PRAGMA journal_mode=WAL;` at database creation
- Set busy timeout: `PRAGMA busy_timeout=10000;` (10 seconds minimum)
- Serialize writes through a single writer queue (asyncio queue or dedicated writer thread)
- Route ALL writes through FastAPI -- never open SQLite from Electron main process directly
- Test with 50+ rapid cell edits while Codex is indexing in background

**Detection:** "database is locked" errors in logs. Cells appear saved but revert on reload.

**Phase:** Offline parity audit phase. Must validate BEFORE building Codex indexing.

---

### Pitfall 4: Perforce Path Resolution Without Perforce Client

**What goes wrong:** MapDataGenerator config uses hardcoded Windows paths (`F:\perforce\cd\mainline\resource\...`). On machines without Perforce client or different workspace mappings, ALL paths are wrong. No gamedata loads. The entire Codex is empty.

**Why it happens:** MapDataGenerator was designed for developer machines. LocaNext targets translators who may not have Perforce. The `settings.json` drive letter selection handles only the drive letter, not arbitrary workspace roots.

**Consequences:** Complete feature failure on non-Perforce machines. App appears broken with no explanation.

**Prevention:**
- Add "Data Source" configuration wizard on first launch:
  - Option A: Perforce workspace (auto-detect via `p4 set P4ROOT` or manual path)
  - Option B: Manual folder selection (browse to `resource/GameData/`)
  - Option C: Pre-bundled sample data (demo mode)
- Extract `PerforcePathService` FIRST -- all services import path templates from one source. Never duplicate `_PATH_TEMPLATES` across services
- Validate paths at startup, show clear warning for missing paths
- Never crash on missing paths -- show placeholder content with "Configure data source" link
- Fall back to `mock_gamedata` (tests/fixtures/) when paths don't exist

**Detection:** All Codex tabs show "No data found". Images show placeholders everywhere.

**Phase:** Perforce parsing phase. Must be solved BEFORE Codex UI work starts.

---

### Pitfall 5: Duplicating Perforce Path Resolution Across Services

**What goes wrong:** Each new Codex service (Audio, Item, Character, Region) implements its own PATH_TEMPLATES dict and drive/branch substitution logic, copying from MapDataService.

**Why it happens:** MapDataService has templates inline. Copying seems faster than refactoring.

**Consequences:** When Perforce paths change (new branch, folder restructure), 5+ files need updating. Templates diverge silently. Bugs appear in one Codex type but not others.

**Prevention:** Extract `PerforcePathService` as a shared service FIRST, before building any new Codex service. All services import path templates from this single source. MapDataGenerator's `config.py` shows the right pattern: centralized `_PATH_TEMPLATES` with `generate_default_paths(drive, branch)`.

**Detection:** If you see `PATH_TEMPLATES` or `generate_paths()` duplicated in any new file, stop and refactor.

**Phase:** Foundation phase. Must be complete before any Codex service work.

---

## Moderate Pitfalls

### Pitfall 6: vgmstream Binary Distribution and Playback Architecture Mismatch

**What goes wrong:** Audio Codex depends on `vgmstream-cli` for WEM-to-WAV. The existing MapDataGenerator uses `winsound.PlaySound()` (Windows-only). LocaNext runs in Electron/Chromium where audio plays via HTML5 `<audio>`.

**Why it happens:** Different playback architectures. MapDataGenerator is tkinter desktop app. LocaNext is web-based in Electron.

**Consequences:** Audio works in MapDataGenerator but fails in LocaNext. "vgmstream not found" if binary not bundled.

**Prevention:**
- Serve converted WAV via FastAPI streaming endpoint (already exists: `media_converter.py`)
- Bundle `vgmstream-cli` binary in app's `tools/` directory per platform
- Use HTML5 `<audio>` with cache-busted URLs (`?v=${Date.now()}`)
- Use `{#key audioUrl}` in Svelte for element recreation
- Add `crossorigin="anonymous"` for cross-port loading (5173->8888)
- Handle missing WEM gracefully -- "Audio unavailable" not a crash
- Reuse `MediaConverter.convert_wem_to_wav()` from server, NOT MapDataGenerator's `AudioHandler`

**Detection:** Audio player shows "vgmstream not found" or plays stale audio.

**Phase:** Audio Codex UI phase.

---

### Pitfall 7: Chrome Audio Caching Breaking Playback

**What goes wrong:** Chrome caches 404 responses for audio URLs permanently. Once an audio URL returns 404, subsequent requests always get cached 404, even after the real file exists.

**Why it happens:** Documented LocaNext bug (`feedback_chrome_audio_cache.md`, `DOC-002`). Chromium aggressively caches error responses for `<audio>` and `<video>` elements. Persists across page refreshes. `cache.clear()` does NOT fix it.

**Consequences:** Audio plays on first load but fails after refresh. Only works in incognito.

**Prevention:**
- ALWAYS add `?v=${Date.now()}` to audio src URLs
- ALWAYS use `{#key audioUrl}` to force `<audio>` element recreation
- ALWAYS use `src=` directly on `<audio>`, NOT `<source>` child elements
- ALWAYS add `crossorigin="anonymous"` for cross-port loading
- Server-side: return `Cache-Control: no-cache` headers for audio streaming endpoints
- Never serve 404 before conversion complete -- return 202 "converting" instead

**Detection:** Audio plays for first item but not subsequent items after navigating away and back.

**Phase:** Audio Codex UI phase. Apply from the FIRST audio implementation.

---

### Pitfall 8: Codex Service Initialization Blocking Server Startup

**What goes wrong:** `CodexService.initialize()` scans all StaticInfo XMLs and builds FAISS index. With thousands of files across 10+ directories, this takes 5-30 seconds. First user action hangs.

**Why it happens:** Current `codex_service.py` is lazy-initialized on first request. V5.0 expands to 4 Codex types plus cross-refs, increasing scan time.

**Prevention:**
- Initialize Codex in background task at startup: `asyncio.create_task(codex.initialize())`
- Show loading indicator: "Codex indexing... (X/Y entities)"
- Cache FAISS index to disk (`faiss.write_index` / `faiss.read_index`). Rebuild only when source XML mtimes change
- If FAISS build fails, Codex still works for browsing (no semantic search)

**Detection:** App takes 30+ seconds to respond to first Codex query.

**Phase:** Codex implementation phase. Design cache-first architecture from the start.

---

### Pitfall 9: Monolithic CodexService Expansion (God-Class)

**What goes wrong:** All Audio/Item/Character/Region logic gets added as methods on the existing CodexService class (currently 565 lines).

**Why it happens:** CodexService already has `_registry` with all entity types. Adding type-specific methods seems natural.

**Consequences:** 2000+ line god-class. Audio logic mixed with region map logic. Impossible to test independently.

**Prevention:** Composition -- each Codex type gets its own service class that USES the core CodexService registry but has its own initialization, data sources, and API. CodexService stays as the shared entity registry.

**Detection:** If `codex_service.py` grows beyond 700 lines, it needs splitting.

**Phase:** Before implementing any new Codex type.

---

### Pitfall 10: Porting QACompiler Generator Logic Incorrectly

**What goes wrong:** QACompiler generators have complex XML parsing with cross-referencing, StringIdConsumer pattern, and generator-specific column layouts. When porting to FastAPI, developers either over-port (Excel formatting logic) or under-port (missing edge cases).

**Why it happens:** Generator source is complex (7 knowledge passes, depth clustering, StringIdConsumer dedup). Hard to separate DATA logic from OUTPUT logic. Past bugs: join key mistakes (Key vs StrKey), path guessing failures (`qacompiler_newskill_bugs.md`).

**Consequences:** Codex shows wrong data. Character names don't resolve. Region positions wrong.

**Prevention:**
- Read existing generator source FIRST (CLAUDE.md rule: "Research before implementing")
- Port only DATA EXTRACTION logic (XML parsing, knowledge resolution, cross-references)
- Skip everything related to Excel output (column formatting, sheet creation, DataValidation)
- If ported code imports xlsxwriter or mentions "sheet"/"column"/"header", it includes output logic to strip
- Compare output row-for-row against QACompiler Excel for same XML input
- Keep `StringIdConsumer` pattern: one fresh consumer per language, `eng_tbl -> consumer=None`

**Detection:** Compare Codex entity counts and field values against QACompiler Excel.

**Phase:** Each Codex type phase. Block on comparison test passing.

---

### Pitfall 11: Light vs Full Build Configuration Drift

**What goes wrong:** Two build configurations share 95% of code but diverge in 5%. Features added to full build accidentally assumed present in light build.

**Prevention:**
- Use single build with runtime feature detection, NOT compile-time ifdef
- Feature availability via `shutil.which()` and probe responses
- CI builds both variants with smoke tests
- Every optional import wrapped in try/except at module level

**Detection:** Light build CI passes but crashes when user opens specific feature.

**Phase:** Bundling phase. Design feature detection pattern first.

---

## Minor Pitfalls

### Pitfall 12: Adding Codex Entities to Repository/DB Layer (Anti-Pattern)

**What goes wrong:** Developer creates `CodexRepository` interface + implementations to store Codex entities in DB.

**Why it happens:** Factory/Repo pattern is well-established. Feels natural.

**Consequences:** Massive effort. Creates sync problem -- XML files are source of truth, DB copy goes stale.

**Prevention:** GameData is FILE-BASED. CodexService scans XML directly. In-memory registry IS the "database." No new repository needed.

**Detection:** If `codex_repository.py` is being created, stop.

---

### Pitfall 13: Mock GameData Missing Audio/Image Files

**What goes wrong:** Tests pass but Audio Codex shows nothing in dev mode because mock_gamedata has XML but no WEM/DDS files.

**Prevention:** Add mock WEM/DDS files to `tests/fixtures/mock_gamedata/`. Even 1-second silent WAV and 4x4 pixel DDS suffice.

---

### Pitfall 14: Svelte Component Bloat from 4 Codex UIs

**What goes wrong:** Four Codex UIs share 70% of UI but built as 4 separate components with duplicated code.

**Prevention:** Build generic `CodexLayout.svelte` with slots for type-specific content. Use Svelte 5 snippets for customization.

---

### Pitfall 15: Electron Build Size Explosion

**What goes wrong:** Light build target ~200MB but FAISS + Model2Vec + vgmstream + Pillow pushes to 500MB+.

**Prevention:** Exclude unused numpy/scipy subpackages. Strip debug symbols. Use `--onedir` not `--onefile`. Monitor build size in CI.

---

### Pitfall 16: WEM Files Missing on Translator Machines

**What goes wrong:** WEM files in Perforce sound directories not synced by translators.

**Prevention:** Show clear counts: "42/150 audio files available." Browse entries even without audio -- show script text and metadata.

---

### Pitfall 17: FAISS Index Size with Empty Audio Descriptions

**What goes wrong:** Audio entries have minimal/empty text metadata. FAISS index contains garbage vectors.

**Prevention:** Only index entities with meaningful text (name + description > 10 chars). Audio entries without descriptions still browsable but not semantic-searchable.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Foundation (paths) | #4, #5 - Path resolution + duplication | Extract PerforcePathService FIRST |
| Foundation (AI) | #2 - AI hard crash | AICapabilityService from day 1 |
| Offline bundle packaging | #1 - PyInstaller DLL placement | hiddenimports pattern, fresh-machine test |
| SQLite-only mode | #3 - Concurrent write locks | WAL mode, single writer queue |
| Audio Codex UI | #6, #7 - vgmstream + Chrome cache | Server-side conversion, cache-busting |
| Item/Character Codex | #9, #10 - God-class + over-porting | Separate services, data-only port |
| Region Codex | #4 - Perforce paths missing | Graceful degradation to mock data |
| Codex search | #8 - Init blocking | Background init, FAISS disk cache |
| Build configuration | #11 - Light/full drift | Runtime feature detection |
| New Codex endpoints | #12 - DB-backing Codex | Keep file-based, no new repos |
| Svelte UI | #14 - Component duplication | Generic CodexLayout |

---

## Sources

- `QuickTranslate/docs/PYINSTALLER_ML_BUNDLING.md` -- battle-tested PyInstaller patterns (HIGH confidence)
- `MapDataGenerator/docs/INSTALLER_ISSUES_AND_FIXES.md` -- known installer issues (HIGH confidence)
- `MapDataGenerator/core/audio_handler.py` -- WEM conversion pattern (HIGH confidence)
- `server/tools/ldm/services/media_converter.py` -- existing server-side conversion (HIGH confidence)
- `server/tools/ldm/services/codex_service.py` -- existing Codex architecture (HIGH confidence)
- `server/tools/ldm/services/mapdata_service.py` -- PATH_TEMPLATES pattern (HIGH confidence)
- `docs/architecture/OFFLINE_ONLINE_ARCHITECTURE.md` -- offline patterns (HIGH confidence)
- `docs/architecture/ARCHITECTURE_SUMMARY.md` -- repository pattern (HIGH confidence)
- `feedback_chrome_audio_cache.md` -- Chrome audio cache bug (HIGH confidence)
- [PyInstaller troubleshooting](https://pyinstaller.org/en/stable/when-things-go-wrong.html) (MEDIUM confidence)
- [SQLite locking docs](https://sqlite.org/lockingv3.html) (HIGH confidence)
- [SQLite concurrent writes and WAL](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) (MEDIUM confidence)
- [Electron audio autoplay issues](https://thecodersblog.com/electron-video-player-sound-autoplay-2025) (MEDIUM confidence)

---

*Researched: 2026-03-21 | 17 pitfalls catalogued (5 critical, 6 moderate, 6 minor)*
