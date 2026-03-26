# Research Summary: v13.0 Production Path Resolution

**Domain:** Game localization tool -- path resolution from language data to media assets
**Researched:** 2026-03-26
**Overall confidence:** HIGH (direct source code audit, no external dependencies)

## Executive Summary

LocaNext already has a comprehensive path resolution infrastructure. The PerforcePathService handles 11 Perforce path templates with drive/branch substitution and WSL conversion. The MegaIndex provides 35 O(1) lookup dictionaries built from game data XMLs in a 7-phase pipeline, including composed cross-reference chains (C1-C7) that bridge StringId to image/audio paths. The MapDataService exposes these lookups with 3-tier image resolution and 5-tier audio resolution. Frontend components (ImageTab, AudioTab) are complete and wired through the RightPanel tab system.

The critical gaps are: (1) no frontend UI for branch+drive selection, (2) no path validation feedback, (3) the C6/C7 StringId-to-entity bridge relies on fragile Korean text matching, and (4) mega_index.py at 1311 lines needs splitting. Additionally, 4 code review issues from v11.0 remain unfixed.

The mock gamedata system is complete with 119 files covering all entity types, and DEV mode auto-builds MegaIndex from these fixtures on startup. The infrastructure is solid -- v13.0 is about wiring the last-mile UI and hardening the cross-reference chains, not building from scratch.

## Key Findings

**Stack:** FastAPI backend + Svelte 5 frontend; PerforcePathService + MegaIndex + MapDataService + MediaConverter already built
**Architecture:** 35-dict MegaIndex with 7-phase build pipeline; C1 (image) and C3 (audio) chains working; C7 (StringId->entity) bridge fragile
**Critical pitfall:** C6/C7 Korean text matching is the weakest link -- entity names often differ from StrOrigin text in languagedata files

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Fix v11.0 Code Review Issues** - Low risk cleanup, unblocks clean codebase
   - Addresses: FIX-01 (4 issues: onScrollToRow race, visibleColumns dead code, onSaveComplete, tmSuggestions)
   - Avoids: Accumulating technical debt from prior milestones

2. **Phase 2: Branch+Drive Selector UI + Path Validation** - Foundation for production paths
   - Addresses: PATH-01 (Branch+Drive selector), PATH-02 (path validation)
   - Avoids: Building features before users can configure the system

3. **Phase 3: Image+Audio Chain Wiring + E2E Tests** - The main value delivery
   - Addresses: PATH-03 (image chain), PATH-04 (audio chain), MOCK-01+MOCK-02 (testing)
   - Avoids: C6/C7 fragility by adding StrKey-based matching alongside text matching

4. **Phase 4: MegaIndex Split** - Architecture cleanup
   - Addresses: ARCH-02 (split 1311-line mega_index.py into domain services)
   - Independent of feature work, can be done last

**Phase ordering rationale:**
- FIX-01 first because it is small and removes known bugs from the working tree
- PATH-01/02 before PATH-03/04 because users need configuration UI before chains can be tested with real data
- MOCK before ARCH because mock tests validate chain correctness; ARCH is pure refactoring
- ARCH-02 last because it is independent and benefits from understanding gained during chain work

**Research flags for phases:**
- Phase 2: May need reference to QACompiler/MapDataGenerator branch+drive UI patterns
- Phase 3: C6/C7 fragility is the key risk -- needs careful chain augmentation
- Phase 4: Standard refactoring, unlikely to need research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All code read directly, no external dependencies |
| Features | HIGH | All API endpoints audited, frontend components traced |
| Architecture | HIGH | 35 dicts fully documented, chains traced end-to-end |
| Pitfalls | HIGH | C6/C7 fragility confirmed by code reading, C2 weakness identified |

## Gaps to Address

- How QACompiler/MapDataGenerator handle branch+drive UI (reference for PATH-01)
- Whether tmSuggestions inaccessibility is still relevant after v12.0 TM Intelligence
- VRS ordering (Phase 4 of MegaIndex build is "skipped for now")
- Performance impact of MegaIndex rebuild on branch+drive change (could be slow with real data)
