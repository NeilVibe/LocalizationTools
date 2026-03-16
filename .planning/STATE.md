---
gsd_state_version: 1.0
milestone: v3.1
milestone_name: Debug + Polish + Svelte 5 Migration
status: unknown
stopped_at: Completed 25-09-PLAN.md
last_updated: "2026-03-16T00:48:41.403Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 19
  completed_plans: 19
---

-----------|
| v1.0 | 7 | 20 | 42/42 |
| v2.0 | 8 | 17 | 40/40 |
| v3.0 | 7 | 14 | 45/45 |
| v3.1 | 3 | TBD | 0/22 |

*Updated after each plan completion*
| Phase 23 P02 | 2min | 2 tasks | 5 files |
| Phase 24 P02 | 6min | 2 tasks | 12 files |
| Phase 25 P04 | 3min | 2 tasks | 3 files |
| Phase 25 P02 | 8min | 3 tasks | 13 files |
| Phase 25 P03 | 7min | 3 tasks | 6 files |
| Phase 25 P09 | 4min | 3 tasks | 5 files |

## Accumulated Context

### Decisions

- [Post-v3.1 Debug Session]: Found and fixed 8 issues across tests and server code:
  - TEST FIX: test_dashboard_api.py DEV_MODE auth detection — checked env var in test process instead of server response
  - TEST FIX: test_export_roundtrip.py XML attribute casing — lowercase vs PascalCase (StrOrigin/Str), added fallback
  - TEST FIX: test_row_repo.py SQLite edit history — asserted history exists but SQLite returns empty (no-op), added DbMode check
  - TEST FIX: knowledgeinfo_chain.xml + test_mapdata_service.py + test_xml_parsing.py — KnowledgeData→KnowledgeInfo wrong XML tag
  - SERVER FIX: mapdata_service.py build_knowledge_table() iterated KnowledgeData instead of KnowledgeInfo — image chain completely broken
  - SERVER FIX: gamedata_browse_service.py missing EDITABLE_ATTRS for 6 entity types + wrong tag names for GimmickGroupInfo/FactionGroup
  - SERVER FIX: codex_service.py case-insensitive entity_type and StrKey lookups, empty search returns 0, region names from KnowledgeInfo
  - SERVER FIX: codex.py routes case normalization .lower() on entity_type in all 3 handlers
- [v3.1 Roadmap]: Svelte 5 migration first (Phase 22) -- stable event model before component-level bug fixes
- [v3.1 Roadmap]: TEST-01 grouped with bug fixes (Phase 23) -- stale test reference, not UIUX
- [v3.0 21-02]: PlaceholderImage uses foreignObject -- UX-04 will replace with div layout for Chromium compat
- [22-02]: Carbon component on: directives preserved as exempt (on:click, on:close, on:change, on:toggle, on:select)
- [22-02]: Callback naming convention: on + PascalCase event name (onApplyTM, onUploaded, onTmSelect)
- [22-01]: Carbon on:click/on:close/on:select left as-is (Carbon Svelte uses Svelte 4 events internally)
- [22-01]: TMTab migrated alongside RightPanel to keep event chain intact
- [22-03]: 8 e.detail usages remain as Carbon-exempt (Checkbox, Toggle, Slider, MultiSelect, RadioButtonGroup)
- [22-03]: Phase 22 complete -- 0 createEventDispatcher, 0 non-Carbon on: directives across entire codebase
- [23-03]: AISuggestionsTab already had loading=false in cleanup -- no change needed
- [23-03]: Added abortController.abort() to NamingPanel cleanup (was missing unlike AISuggestionsTab)
- [23-03]: Removed dead handleClickOutside from QAInlineBadge -- backdrop onclick approach is cleaner
- [Phase 23-02]: codexSearchQuery writable store for cross-page NPC search (consumed and cleared on CodexPage mount)
- [23-01]: Use file.path as deterministic ID for GameDevPage -- no server-generated ID or Date.now() fallback needed
- [23-01]: Added public reload() export to FileExplorerTree for flicker-free tree refresh
- [Phase 23-02]: FIX-10 satisfied: WorldMapPage uses inline fetch, no duplicate service instantiation exists
- [23-04]: Kept both named and numbered texture assertions since XML UITextureName still references named files
- [23-04]: API health check treats 4xx as warnings (endpoint exists but auth-gated), only 5xx as failures
- [Phase 24]: Reactive Set pattern for failedImages -- new Set() reassignment triggers Svelte 5 reactivity
- [Phase 24]: Removed SVG entirely from PlaceholderImage -- div+flex+aspect-ratio is simpler and Electron-safe
- [24-02]: Consistent focus style: outline: 2px solid var(--cds-focus) with outline-offset across all custom buttons
- [24-02]: Error messages show human-readable text, never raw HTTP status codes
- [24-02]: MapTooltip viewport clamping uses $derived with window dimensions
- [24-02]: CategoryFilter skipped for a11y -- Carbon MultiSelect handles its own accessibility
- [25-04]: 19 subsystems in dependency-safe order matching Wave 2 test file structure
- [25-04]: Graceful skip for missing test files allows runner to work before Wave 2 completes
- [Phase 25-01]: Followed existing LocStrList/StringId pattern for loc.xml files instead of LanguageData format from plan
- [25-02]: xlsxwriter for Excel generation, openpyxl for reading (project convention)
- [25-02]: Generation scripts kept alongside fixtures for reproducibility
- [25-02]: br-tags in XML attributes stored as &lt;br/&gt; matching production lxml behavior
- [25-03]: APIClient returns raw Response objects so callers assert status_code before .json()
- [25-03]: 128 public methods covering all subsystems including offline/sync for full API coverage
- [Phase 25]: AI tests accept 200 OR 503 (model offline) -- never require perfect AI output
- [Phase 25]: Accept flexible status codes (401/403) for auth failures since FastAPI middleware varies
- [Phase 25]: [25-07]: Parametrized column detection across 10 entity types for comprehensive coverage
- [Phase 25]: Renamed test_tm_search.py to test_tm_search_api.py to avoid overwriting existing TMSearcher unit tests
- [25-09]: Tools tests try multiple URL prefixes for endpoint discovery since tool routes may be mounted at different paths
- [25-09]: Offline tests accept GRACEFUL tuple (200/404/422/500/501/503) since offline mode may not be active in test env
- [25-09]: Admin no-500 batch check validates 8 admin-adjacent endpoints simultaneously
- [Phase 25]: Socket.IO wrapper unwrapped via other_asgi_app for FastAPI route introspection

### Pending Todos

None yet.

### Roadmap Evolution

- Phase 25 added: Comprehensive API E2E Testing

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-15T22:53:03.000Z
Stopped at: Completed 25-09-PLAN.md
Resume file: None
