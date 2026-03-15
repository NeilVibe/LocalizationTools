# Project Research Summary

**Project:** LocaNext v2.0 -- Real Data + Dual Platform
**Domain:** Desktop CAT tool + Game Dev platform for localization management
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

LocaNext v2.0 is a "make it real" milestone: replacing mock fixtures with real XML game data parsing, wiring dual Translator/Game Dev UI modes, implementing merge engines (translation transfer and position-aware XML merge), building image/audio media pipelines, and adding local AI context summaries. The critical insight from research is that **almost zero new dependencies are needed** -- every library required is already installed, and every algorithm needed has been battle-tested across 8 NewScripts projects. The v2.0 work is a porting and integration effort, not a greenfield build.

The recommended approach is to treat XML parsing as the absolute foundation (everything depends on it), port proven logic directly from QuickTranslate and MapDataGenerator rather than reinventing, and fill the existing v1.0 scaffolds (MapDataService, GlossaryService, ContextService) with real data. The architecture is sound -- singleton services with lazy init, clean route/service separation, and a VirtualGrid that can switch column configs without duplication. The dual UI should reuse the single VirtualGrid (4048 lines) with mode-specific column configs, not create separate grid components.

The top risks are: (1) br-tag corruption during merge/export round-trips -- three layers of defense must be ported from QuickTranslate, not improvised; (2) stdlib ElementTree vs lxml divergence -- the existing XML handler uses stdlib ET which will fail on real malformed game files; (3) DDS image conversion failing in WSL2 due to platform-guarded imports from MapDataGenerator's Windows-only design; (4) match-type confusion in merge (four distinct types with strict priority ordering). All of these have known solutions in the NewScripts codebase -- the risk is skipping the port and trying to simplify.

## Key Findings

### Recommended Stack

No new Python packages are needed for development. All required libraries (lxml, Pillow, httpx, Model2Vec, xlsxwriter, openpyxl) are already in requirements.txt. The only additions are: `pillow-dds` (Windows build only, for BC7 DDS textures) and `vgmstream-cli` (external binary for WEM audio, bundled not pip-installed). AI summaries use httpx directly against Ollama's REST API -- the `ollama` Python package is unnecessary overhead for a single endpoint call. The frontend needs zero new npm packages.

**Core technologies (all existing):**
- **lxml** (>=4.9.0): XML parsing with sanitizer+recovery -- already used by all NewScripts
- **Pillow** (>=10.0.0) + pillow-dds: DDS texture to PNG conversion -- proven in MapDataGenerator
- **httpx** (0.27.0): Async HTTP client for Ollama REST API -- already a dependency
- **vgmstream-cli** (binary): WEM to WAV audio conversion -- only tool that handles Wwise format
- **Model2Vec** (>=0.3.0): Fuzzy merge matching via semantic embeddings -- already used for TM

### Expected Features

**Must have (table stakes for v2.0):**
- T1: Real XML parsing replacing mock fixtures (the entire point of v2.0)
- T2/T3: Translator merge with StringID + source text matching
- T4: Export to XML with br-tag and format preservation
- T5: Export to Excel (LanguageDataExporter column structure)
- T6/T7/T8: Dual UI mode detection and column layouts
- T9: DDS-to-PNG image display in context panel
- T12: XML sanitizer + recovery for malformed game files
- T13: Postprocessing pipeline (CJK-safe 7-step cleanup)
- T14: Bug fixes (offline TMs, paste, folder 404)

**Should have (differentiators):**
- D1: Fuzzy matching via Model2Vec embeddings (semantic, not edit-distance)
- D2: AI context summaries via local Qwen3 (zero cloud, zero cost)
- D3: Position-aware XML merge for Game Dev mode
- D4: Cross-reference chain resolution (StrKey > image/audio lookups)
- D5: WEM audio playback inline

**Defer to v3.0:**
- Full Game Dev CRUD (create/nest new XML nodes)
- Game World Codex (interactive encyclopedia)
- AI translation suggestions
- XLIFF/TMX import/export
- Auto-generated missing images/audio
- Multi-file batch merge

### Architecture Approach

The v1.0 architecture is sound and does NOT need restructuring. Services exist as singletons with `get_*_service()` factories. The v2.0 work adds 7 new service files and 2 new route files while modifying 3 existing services to fill their scaffolded indexes with real data. The VirtualGrid (4048 lines) is reused for both UI modes via column config objects selected by file type -- building a second grid would be architectural debt.

**Major components (new):**
1. **XMLParsingEngine** -- centralized XML parsing with sanitization, ports QuickTranslate patterns
2. **TranslatorMergeEngine** -- StringID/StrOrigin/fuzzy match + 7-step postprocess pipeline
3. **GameDevMergeEngine** -- position-based node-level merge (completely separate from Translator merge)
4. **ExportService** -- XML (br-tag safe), Excel (xlsxwriter), plain text output
5. **MediaConverter** -- DDS-to-PNG (Pillow) and WEM-to-WAV (vgmstream-cli)
6. **AISummaryService** -- Qwen3-4B via Ollama with cache and graceful degradation
7. **FileTypeDetector** -- LocStr scan to route files to correct UI mode

### Critical Pitfalls

1. **br-tag corruption in merge/export** -- three representations exist (disk/memory/Excel). Port QuickTranslate's three-layer defense exactly. Round-trip tests are mandatory gate.
2. **stdlib ET vs lxml divergence** -- existing XML handler uses stdlib ET which crashes on malformed game data. Migrate to lxml with `recover=True` FIRST, before any real file work.
3. **Match-type priority confusion** -- four distinct match types with strict ordering (strict > StringID-only > StrOrigin-only > fuzzy). Getting the hierarchy wrong causes silent data corruption.
4. **DDS platform gap in WSL2** -- MapDataGenerator's Windows-only `pillow-dds` import guard breaks in WSL2. Remove the platform check, install unconditionally.
5. **Dual UI state leaks** -- Svelte component state from Translator mode persists when switching to Game Dev mode. Use `{#key fileType}` for full remount or explicit state reset.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: XML Parsing Foundation + Bug Fixes
**Rationale:** Every other feature depends on reliable XML parsing. The existing stdlib ET handler must be replaced with lxml before ANY real file work. Bug fixes are independent and can be done in parallel.
**Delivers:** XMLParsingEngine, FileTypeDetector, XML sanitizer, path translator utility, language table parsing, StringIdConsumer deduplication. Plus 3 bug fixes from v1.0.
**Addresses:** T1, T6, T11, T12, T14, D6
**Avoids:** Pitfall 2 (stdlib ET), Pitfall 3 (encoding), Pitfall 12 (WSL paths), Pitfall 14 (Korean regex)

### Phase 2: Dual UI Mode
**Rationale:** High visibility for demos, relatively low complexity (column config switching on existing grid), and required before merge operations can display results correctly.
**Delivers:** Translator and Game Dev column layouts, mode indicator, state isolation between modes.
**Addresses:** T7, T8
**Avoids:** Pitfall 7 (state leaks between modes), Pitfall 20 (Svelte 5 runes misuse)

### Phase 3: Translator Merge
**Rationale:** This is the core value proposition -- without merge, the tool can't do its primary job. Depends on XML parsing (Phase 1). Most complex logic with highest risk of data corruption.
**Delivers:** TranslatorMergeEngine (exact + source + fuzzy match), postprocessing pipeline, merge UI with transactional commit (not optimistic).
**Addresses:** T2, T3, T13, D1
**Avoids:** Pitfall 1 (br-tags), Pitfall 4 (match priority), Pitfall 15 (optimistic UI on batch ops), Pitfall 19 (stale FAISS)

### Phase 4: Export Pipeline
**Rationale:** Natural extension of merge -- translators need to get their work OUT of the tool. Depends on merge producing correct data.
**Delivers:** ExportService for XML (br-tag safe round-trip), Excel (xlsxwriter), plain text. CLI commands for scriptable export.
**Addresses:** T4, T5, D7, D8 (partial)
**Avoids:** Pitfall 1 (br-tag export), Pitfall 16 (Excel library mismatch)

### Phase 5: Image and Audio Pipeline
**Rationale:** High demo impact but independent of merge logic. Can be parallelized with Phase 3/4 if resources allow. Requires binary setup (vgmstream-cli).
**Delivers:** MediaConverter (DDS-to-PNG, WEM-to-WAV), cross-reference chain resolution, missing asset placeholders, wired ImageTab and AudioTab.
**Addresses:** T9, T10, D4, D5
**Avoids:** Pitfall 5 (DDS platform gap), Pitfall 6 (missing vgmstream binary), Pitfall 11 (broken chains)

### Phase 6: Game Dev Merge
**Rationale:** Most complex feature, fundamentally different from Translator merge (position-based vs match-type). Must be implemented AFTER Translator merge is stable -- do not try to generalize.
**Delivers:** GameDevMergeEngine with node/attribute/children-level merge, Game Dev-specific postprocessing.
**Addresses:** D3
**Avoids:** Pitfall 8 (position vs match-type confusion), Pitfall 13 (postprocess corrupting non-text attributes)

### Phase 7: AI Summaries
**Rationale:** Independent of all other features except XML parsing. Lowest risk, impressive demo value. Ollama may not always be available -- graceful degradation is the design, not the exception.
**Delivers:** AISummaryService, per-StringID caching, ContextTab integration, "AI unavailable" badge.
**Addresses:** D2
**Avoids:** Pitfall 9 (LLM timeout), Pitfall 10 (inconsistent JSON output)

### Phase 8: E2E Validation + CLI
**Rationale:** Final validation that all phases integrate correctly. Round-trip tests (parse > merge > export > parse > compare), CLI coverage for automation.
**Delivers:** Integration tests with real XML fixtures, CLI merge/export commands, full round-trip validation.
**Addresses:** D8 (complete)

### Phase Ordering Rationale

- **XML parsing first** because every other feature calls it -- merge, export, media, AI all need parsed data
- **Dual UI before merge** because merge results need the correct column layout to display
- **Translator merge before Game Dev merge** because it's more proven (direct port from QuickTranslate) and validates the merge architecture
- **Export after merge** because export formats the data merge produces
- **Media pipeline is independent** and can run in parallel with merge phases
- **AI summaries last** because they're the most tolerant of delay (graceful degradation built in)
- **Bug fixes in Phase 1** to clear technical debt early and build confidence

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Translator Merge):** Complex match-type logic with CJK edge cases. Port from QuickTranslate is well-documented but integration with LocaNext's data model needs validation.
- **Phase 6 (Game Dev Merge):** No existing implementation to port -- this is new algorithmic work. Position-based XML merge at arbitrary depth is genuinely complex.
- **Phase 7 (AI Summaries):** Prompt engineering for Qwen3-4B structured output needs prototyping with real game data.

Phases with standard patterns (skip research-phase):
- **Phase 1 (XML Parsing):** Direct port from QuickTranslate/MapDataGenerator, extremely well-documented.
- **Phase 2 (Dual UI):** Column config switching is straightforward Svelte 5 pattern.
- **Phase 4 (Export):** xlsxwriter and lxml raw_attribs patterns are proven.
- **Phase 5 (Media):** Direct port from MapDataGenerator handlers.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified against existing requirements.txt. Zero new dependencies for dev. |
| Features | MEDIUM-HIGH | Core features well-understood from NewScripts. Game Dev merge and AI summaries less proven in LocaNext context. |
| Architecture | HIGH | Based on direct codebase inspection. v1.0 scaffolds are well-designed. Integration points are clear. |
| Pitfalls | HIGH | All critical pitfalls sourced from production NewScripts code and existing LocaNext codebase. Known edge cases, not speculation. |

**Overall confidence:** HIGH

### Gaps to Address

- **Game Dev merge algorithm:** No existing NewScripts implementation to port. Position-aware merge at arbitrary XML depth needs design work during Phase 6 planning. QACompiler generators provide data model knowledge but not merge logic.
- **pillow-dds on Linux:** MapDataGenerator uses it on Windows only. Need to verify pillow-dds installs and works correctly in WSL2/Linux. If it doesn't, fallback to Pillow's built-in DDS support (covers DXT1/DXT5 but not BC7).
- **Qwen3 prompt reliability:** Structured JSON output from small models is unpredictable. Need prototype testing with real game strings before committing to a prompt template.
- **Data shape transition:** v1.0 rows use `extra_data` JSON blob. Real XML LocStr elements have 10+ attributes. The mapping between these needs explicit design during Phase 1 planning.
- **vgmstream-cli Linux binary:** Available from GitHub releases but not tested in the LocaNext WSL2 environment. May need compilation from source.

## Sources

### Primary (HIGH confidence)
- QuickTranslate source code: `xml_parser.py`, `xml_io.py`, `xml_transfer.py`, `postprocess.py` -- merge logic, sanitization, br-tag defense
- MapDataGenerator source code: `dds_handler.py`, `audio_handler.py`, `linkage.py` -- media conversion, cross-ref chains
- LocaNext codebase inspection: `VirtualGrid.svelte`, `mapdata_service.py`, `xml_handler.py`, `context_service.py` -- architecture validation
- LocaNext `ARCHITECTURE_SUMMARY.md`, `PROJECT.md`, `REQUIREMENTS.md` -- project documentation
- Project MEMORY.md -- cross-project rules (Korean regex, Excel libs, br-tags)

### Secondary (MEDIUM confidence)
- [Pillow DDS documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) -- native format support
- [Ollama REST API docs](https://docs.ollama.com/api/introduction) -- generate endpoint
- [vgmstream releases](https://github.com/vgmstream/vgmstream/releases) -- binary availability
- [CAT tools comparison 2026](https://geotargetly.com/blog/cat-tools) -- competitive landscape
- [AI in Localization 2025-2028](https://medium.com/@hastur/embracing-ai-in-localization-a-2025-2028-roadmap-a5e9c4cd67b0) -- industry trends

### Tertiary (LOW confidence)
- Game Dev merge approach -- based on general XML diff patterns, no specific reference implementation exists in the codebase

---
*Research completed: 2026-03-15*
*Supersedes: v1.0 SUMMARY.md (demo-ready scope)*
*Ready for roadmap: yes*
