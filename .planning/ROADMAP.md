# Roadmap: LocaNext v9.0 Build Validation + Real-World Testing

## Overview

v9.0 validates that the built LocaNext app works end-to-end on an offline Windows PC with real-looking data. Starting from mock gamedata that mirrors actual Perforce paths, through build pipeline verification, to language data round-trip testing in the installed app, and finishing with AI-powered visual audit of all pages. Four phases, each delivering a verifiable layer of confidence.

## Phases

- [ ] **Phase 74: Mock Data Foundation** - Perforce-path mock gamedata (DDS/WEM/XML) loadable by PerforcePathService
- [ ] **Phase 75: Build Pipeline** - Light Build produces working installer with internalized merge module
- [ ] **Phase 76: Language Data E2E** - Upload, edit, save, media resolution in built app (offline)
- [ ] **Phase 77: Visual Audit** - Qwen3-VL review of all 5 pages, fix critical issues, screenshot evidence

## Phase Details

### Phase 74: Mock Data Foundation
**Goal**: Mock gamedata mirrors real Perforce folder structure so PerforcePathService resolves DDS, WEM, and XML paths identically to production
**Depends on**: Nothing (first phase of v9.0)
**Requirements**: MOCK-09, MOCK-10, MOCK-11, MOCK-12
**Success Criteria** (what must be TRUE):
  1. Mock gamedata directory tree matches F:\perforce\cd\mainline\ structure (StaticInfo, Texture, Audio folders)
  2. PerforcePathService resolves mock DDS image paths and returns valid PNG thumbnails
  3. PerforcePathService resolves mock WEM audio paths and returns playable audio
  4. Mock .loc.xml files contain realistic multi-language content (EN/KR/JP minimum) with br-tags and entity references
**Plans:** 1/2 plans executed

Plans:
- [x] 74-01-PLAN.md — Valid DDS textures + WAV-content WEM audio + Korean/Chinese audio folders
- [ ] 74-02-PLAN.md — Japanese language data XML + comprehensive verification tests

### Phase 75: Build Pipeline
**Goal**: GitHub Actions Light Build produces a downloadable installer that includes the internalized merge module and runs offline
**Depends on**: Phase 74
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04
**Success Criteria** (what must be TRUE):
  1. PyInstaller spec includes all 14 server/services/merge/ files as hidden imports
  2. Built app executes merge workflow (match + postprocess) without errors or missing modules
  3. GitHub Actions Light Build completes and uploads installer artifact to release
  4. Downloaded .exe installer installs and launches the app on an offline Windows PC
**Plans**: TBD

### Phase 76: Language Data E2E
**Goal**: Users can upload, edit, and save language data in the built app with full media resolution, all working offline
**Depends on**: Phase 75
**Requirements**: LDE2E-01, LDE2E-02, LDE2E-03, LDE2E-04
**Success Criteria** (what must be TRUE):
  1. User uploads a .loc.xml file in the built app and sees all language columns populated in the grid
  2. User edits a cell value, saves, reloads the file, and the edit persists with correct XML encoding
  3. Grid rows show associated DDS images and WEM audio resolved from Perforce-path mock data
  4. All upload/edit/save operations work with SQLite backend (no PostgreSQL required)
**Plans**: TBD

### Phase 77: Visual Audit
**Goal**: Every page passes AI visual review with real-looking data loaded, critical issues fixed, and screenshot evidence captured
**Depends on**: Phase 76
**Requirements**: UIUX-01, UIUX-02, UIUX-03
**Success Criteria** (what must be TRUE):
  1. Qwen3-VL scores all 5 pages (Files, Game Dev, Codex, Map, TM) at 7+/10 with mock data loaded
  2. All critical UIUX issues identified by the visual audit are fixed and re-verified
  3. Screenshot gallery of all 5 pages with real-looking data saved as milestone evidence
**Plans**: TBD

## Progress

**Execution Order:** 74 -> 75 -> 76 -> 77

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 74. Mock Data Foundation | 1/2 | In Progress|  |
| 75. Build Pipeline | 0/TBD | Not started | - |
| 76. Language Data E2E | 0/TBD | Not started | - |
| 77. Visual Audit | 0/TBD | Not started | - |
