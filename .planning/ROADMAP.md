# Roadmap: LocaNext v6.0 Showcase Offline Transfer

## Overview

Enable translators to open languagedata files, translate offline, and merge changes back into LOC/LOCDEV using QuickTranslate's proven transfer logic. Foundation phase sets up mock data and path settings, then the transfer adapter imports QuickTranslate core modules directly (sys.path, never copy), the API layer exposes merge with SSE streaming, the UI delivers a single-page merge modal with phase-driven state, and integration testing verifies the full pipeline with real test data.

## Phases

- [x] **Phase 56: Mock Data + Settings** - CLI mock DB setup with 3 projects + LOC/EXPORT path configuration in Settings (completed 2026-03-22)
- [x] **Phase 57: Transfer Service Adapter** - Import QuickTranslate core modules via sys.path for 3 match types, postprocess, and multi-language merge (completed 2026-03-22)
- [x] **Phase 58: Merge API** - REST endpoints for dry-run preview and SSE-streamed merge execution (completed 2026-03-22)
- [x] **Phase 59: Merge UI** - Single-page merge modal with configure/preview/execute/done phases and dual entry points (completed 2026-03-22)
- [ ] **Phase 60: Integration Testing** - End-to-end pipeline verification with mock data and real test files

## Phase Details

### Phase 56: Mock Data + Settings
**Goal**: Users have a clean mock environment with configured paths so all subsequent merge work has data to operate on
**Depends on**: Nothing (first phase)
**Requirements**: MOCK-01, MOCK-02, MOCK-03, MOCK-04, SET-01, SET-02, SET-03
**Success Criteria** (what must be TRUE):
  1. Running `python scripts/setup_mock_data.py --confirm-wipe` creates a fresh DB with project_FRE, project_ENG, and project_MULTI visible in the file explorer
  2. Each mock project auto-detects its language from the project name and displays the correct language badge (French, English, Multi)
  3. User can set LOC PATH and EXPORT PATH in the Settings page, values persist across app restarts, and invalid paths show validation errors
  4. Test languagedata files from the test123 directory load correctly when pointed to by LOC PATH
**Plans**: 3 plans (Wave 1: modal component, Wave 2: entry points + multi-lang polish)

Plans:
- [x] 56-01-PLAN.md -- CLI mock DB script with --confirm-wipe, 3 projects, language auto-detection
- [x] 56-02-PLAN.md -- Settings UI for LOC PATH + EXPORT PATH with validation and persistence

### Phase 57: Transfer Service Adapter
**Goal**: QuickTranslate's proven transfer logic is available as a LocaNext service via adapter import, supporting all 3 match types and the full postprocess pipeline
**Depends on**: Phase 56
**Requirements**: XFER-01, XFER-02, XFER-03, XFER-04, XFER-05, XFER-06, XFER-07
**Success Criteria** (what must be TRUE):
  1. The adapter successfully imports QuickTranslate modules (xml_transfer, postprocess, source_scanner, language_loader) via sys.path without copying any Sacred Script code
  2. StringID Only match type correctly transfers entries with case-insensitive matching and SCRIPT/ALL category filtering
  3. StringID+StrOrigin and StrOrigin+FileName 2PASS match types produce identical results to QuickTranslate standalone execution on the same test data
  4. The 8-step postprocess pipeline (newlines, apostrophes, entities, etc.) runs after every merge and produces clean output
  5. Multi-language folder merge scans a source folder, auto-detects language suffixes per file/subfolder, and merges each language into the correct target
**Plans**: 3 plans (Wave 1: foundation, Wave 2: match types + multi-lang parallel)

Plans:
- [x] 57-01-PLAN.md -- Config shim + sys.path adapter import layer with test fixtures (XFER-01)
- [x] 57-02-PLAN.md -- execute_transfer with 3 match types, scope, postprocess (XFER-02..06)
- [x] 57-03-PLAN.md -- Multi-language folder merge with language auto-detection (XFER-07)

### Phase 58: Merge API
**Goal**: FastAPI endpoints expose merge preview (dry-run) and execution (SSE streaming) so the frontend can drive the merge workflow
**Depends on**: Phase 57
**Requirements**: API-01, API-02, API-03, API-04
**Success Criteria** (what must be TRUE):
  1. POST /api/merge/preview returns a dry-run summary with file count, entry count, match count, and overwrite warnings without modifying any files
  2. POST /api/merge/execute streams progress via SSE with per-file updates and postprocess step notifications
  3. On completion, the merge response includes matched, skipped, and overwritten counts as a summary report
  4. Multi-language preview mode scans the source folder and returns a per-language breakdown of files and expected matches
**Plans**: 3 plans (Wave 1: modal component, Wave 2: entry points + multi-lang polish)

Plans:
- [x] 58-01-PLAN.md -- Preview endpoint (dry-run summary) + multi-language preview
- [x] 58-02-PLAN.md -- Execute endpoint with SSE streaming + completion summary

### Phase 59: Merge UI
**Goal**: Users can merge translations back to LOCDEV through a polished single-page modal with full control over match type, scope, and preview
**Depends on**: Phase 58
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09
**Success Criteria** (what must be TRUE):
  1. "Merge to LOCDEV" button appears in the main toolbar and opens the merge modal for the current project
  2. Right-click on a folder in file explorer shows "Merge Folder to LOCDEV" option that opens the modal in multi-language mode
  3. The merge modal walks through configure (target folder, match type, scope) then preview (dry-run results) then execute (progress bar) then done (summary report) as a single-page flow
  4. Category filter toggle appears only when StringID match type is selected, and language badge in the modal header matches the auto-detected project language
  5. Multi-language mode displays detected languages with file counts before merge, and the summary report shows per-language matched/skipped/overwritten counts
**Plans**: 3 plans (Wave 1: modal component, Wave 2: entry points + multi-lang polish)

Plans:
- [x] 59-01-PLAN.md -- Merge modal component with phase-driven state (configure/preview/execute/done)
- [x] 59-02-PLAN.md -- Toolbar button + right-click context menu entry points
- [x] 59-03-PLAN.md -- Multi-language mode UI (language detection display, per-language summary)

### Phase 60: Integration Testing
**Goal**: The full merge pipeline is verified end-to-end with mock data and real test files, confirming all phases work together
**Depends on**: Phase 56, Phase 57, Phase 58, Phase 59
**Requirements**: (verification phase -- validates all 26 requirements in context)
**Success Criteria** (what must be TRUE):
  1. A complete merge workflow (mock setup, configure paths, open modal, preview, execute, verify output) succeeds using mock project_FRE data
  2. Multi-language merge via right-click on project_MULTI folder correctly processes FRE and ENG subfolders with separate merge results
  3. All 3 match types produce correct merge output when tested against the test123 real data files
  4. SSE progress events stream correctly to the UI during merge execution (no dropped events, progress reaches 100%)
**Plans**: 2 plans (Wave 1: pipeline tests, Wave 2: match type tests)

Plans:
- [ ] 60-01-PLAN.md -- E2E pipeline tests (mock setup, settings validation, single-project preview/execute/SSE, multi-language preview)
- [ ] 60-02-PLAN.md -- Match type verification with synthetic XML fixtures (all 3 modes + scope filter)

## Progress

**Execution Order:**
Phases execute sequentially: 56 → 57 → 58 → 59 → 60

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 56. Mock Data + Settings | v6.0 | 2/2 | Complete    | 2026-03-22 |
| 57. Transfer Service Adapter | v6.0 | 3/3 | Complete    | 2026-03-22 |
| 58. Merge API | v6.0 | 2/2 | Complete    | 2026-03-22 |
| 59. Merge UI | v6.0 | 3/3 | Complete    | 2026-03-22 |
| 60. Integration Testing | v6.0 | 0/2 | Not started | - |
