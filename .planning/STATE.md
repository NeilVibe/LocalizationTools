---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 06-02-PLAN.md (Phase 6 complete)
last_updated: "2026-03-15T15:11:00Z"
last_activity: 2026-03-15 -- Plan 06-02 complete (Mode detection + API smoke tests in SQLite mode)
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 23
  completed_plans: 23
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Flawless end-to-end localization workflow -- upload, TM auto-mirror, search/edit, export -- working seamlessly offline and online, polished enough for executive demos.
**Current focus:** Phase 6 complete. All offline mode detection and API smoke tests passing. Next: Phase 7 or milestone complete.

## Current Position

Phase: 6 of 7 (Offline Demo Validation)
Plan: 2 of 2 in current phase
Status: Phase Complete
Last activity: 2026-03-15 -- Plan 06-02 complete (Mode detection + API smoke tests in SQLite mode)

Progress: [██████████] 100% (23/23 plans across 6 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 16min
- Total execution time: 2.8 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | 79min | 26min |
| 02 | 3 | 47min | 16min |
| 03 | 3 | 32min | 11min |
| 04 | 2 | 10min | 5min |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 03 P03 | 6min | 3 tasks | 5 files |
| Phase 04 P01 | 5min | 2 tasks | 4 files |
| Phase 04 P02 | 5min | 3 tasks | 4 files |
| Phase 04 P02 | 5min | 3 tasks | 4 files |
| Phase 05 P01 | 4min | 2 tasks | 6 files |
| Phase 05 P02 | 4min | 3 tasks | 4 files |
| Phase 5.1 P01 | 5min | 2 tasks | 7 files |
| Phase 5.1 P04 | 4min | 2 tasks | 4 files |
| Phase 5.1 P02 | 5min | 2 tasks | 2 files |
| Phase 5.1 P03 | 4min | 2 tasks | 5 files |
| Phase 5.1 P05 | 2min | 3 tasks | 3 files |
| Phase 06 P01 | 8min | 2 tasks | 2 files |
| Phase 06 P02 | 12min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Offline mode priority over online (demo to executives without server dependency)
- Full UI rework in this milestone (can't demo with rough UI)
- MapDataGenerator as first NewScripts integration (most visual for demos)
- Startup threshold 10s (not 5s) due to heavy import chain (20+ routers)
- All stability tests use SQLite mode to avoid PostgreSQL dependency
- OFFLINE_ONLY_COLUMNS is global (per-table diffs tracked in KNOWN_SCHEMA_DRIFT)
- Pre-existing schema drift documented, not fixed (5 table pairs have column mismatches)
- Template DB caching (session-scoped) for server_local test performance
- Capability repo tests verify stub degradation, not parity
- TM repo SERVER mode had missing owner_id and sqlite3.Row .get() bugs (fixed)
- Playwright E2E tests use API-seeded data (upload via fetch in beforeAll) for reliability
- Explorer navigation uses .grid-row with :text-is() exact match selectors
- Green (#24a148) for confirmed, yellow (#c6a300) for draft, gray for empty status colors
- setTimeout(0) for guard flag reset in confirmInlineEdit (matches cancelInlineEdit pattern)
- confirm-row.spec.ts fully rewritten with current login flow (Mode Selection -> Launcher form)
- CSS-only polish for VirtualGrid (no JS changes = zero perf regression risk)
- User feedback noted for future: status color semantics, right panel tabs, export patterns
- Custom LCS diff over diff-match-patch (zero deps, CJK syllable-level tokenization)
- QA issues as persistent footer below tabs (always visible regardless of active tab)
- Color system: green (#24a148) >= 100%, yellow (#c6a300) >= 92%, orange (#ff832b) >= 75%, red (#da1e28) < 75%
- Auto-mirror uses folder-level scope (one TM per folder, simplest approach)
- Leverage thresholds: score >= 1.0 exact, >= 0.75 fuzzy, else new
- Auto-mirror failure is non-blocking (try/except with warning log)
- TMSearcher tests use hash-only indexes (no FAISS runtime dependency for unit tests)
- [Phase 03]: Leverage bar uses CSS segments (green/yellow/gray) matching established color system
- [Phase 03]: E2E tests use Playwright request fixture for API auth
- [Phase 04]: Model2Vec only for semantic search endpoint (TMSearcher auto-loads via get_current_engine_name)
- [Phase 04]: FastAPI dependency_overrides for route-level test isolation (not module-level patches)
- [Phase 04]: SemanticResults overlay inside search-control, AI badge via in-memory Map, route interception for E2E
- [Phase 05]: Multi-key indexing (StrKey/StringID/KnowledgeKey -> same entry) for MapDataService
- [Phase 05]: Non-blocking backend configure call for offline mode compatibility
- [Phase 05]: Client-side path preview from templates (no server round-trip)
- [Phase 05]: Per-tab fetch (image/audio separately) for lazy loading context
- [Phase 05]: HTML5 audio with CSS filter inversion for dark theme
- [Phase 05]: Tab fade-in via {#key} directive triggering CSS animation
- [Phase 5.1]: Translation source badge in source cell (not target) to avoid cluttering edit area
- [Phase 5.1]: QAFooter collapsed by default, expand on header click (saves vertical space)
- [Phase 5.1]: Purple for AI badge, blue for TM badge -- distinct from status color system
- [Phase 5.1]: Group-based Line Check with O(n) index instead of O(n^2) per-row comparison
- [Phase 5.1]: Term automaton built ONCE per file QA run (not per row) -- saves 50-200ms/request
- [Phase 5.1]: Noise filter MAX_ISSUES_PER_TERM=6 removes false-positive glossary terms
- [Phase 5.1]: GlossaryService integration optional (try/except ImportError fallback)
- [Phase 5.1]: Entity index keyed by term name (not numeric ID) for direct O(1) lookup
- [Phase 5.1]: AC automaton built once at init, reused across all detect_entities() calls
- [Phase 5.1]: lxml recovery mode for XML parsing (handles malformed game data)
- [Phase 5.1]: StrKey-first with KnowledgeKey fallback for indirect image/audio (CTX-03, CTX-04)
- [Phase 5.1]: Graceful degradation returns empty EntityContext (not HTTP errors) when services not loaded
- [Phase 5.1]: /context/status before /context/{string_id} to prevent route shadowing
- [Phase 5.1]: Entity highlight colors match Carbon Tag type colors (purple/teal/cyan/magenta)
- [Phase 5.1]: 503 from context API = not-configured state with settings hint
- [Phase 06]: socketio.ASGIApp.other_asgi_app for TestClient access to inner FastAPI instance
- [Phase 06]: Session-scoped template DB pattern for API smoke tests (copy from Base.metadata.create_all)
- [Phase 06]: Pure repo-level testing validates offline workflow without live server
- [Phase 06]: EntityContext.entities (single list) is the correct field for empty context checks

### Pending Todos

None yet.

### Blockers/Concerns

- TanStack Virtual + Svelte 5 runes compatibility unverified (affects Phase 2 grid implementation)
- SQLite dialect gaps vs PostgreSQL not inventoried (affects Phase 1 and Phase 6)
- TM file explorer: user reports files cannot be moved to folders (may need DB reset, pre-existing issue)

## Session Continuity

Last session: 2026-03-15T15:11:00Z
Stopped at: Completed 06-02-PLAN.md (Phase 6 complete)
Resume file: None
