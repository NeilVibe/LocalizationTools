---
phase: 18
slug: game-dev-grid-file-explorer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `tests/conftest.py` (backend), `locaNext/vitest.config.ts` (frontend) |
| **Quick run command** | `cd /home/neil1988/LocalizationTools && python -m pytest tests/unit/ldm/ -x -q --tb=short` |
| **Full suite command** | `cd /home/neil1988/LocalizationTools && python -m pytest tests/ -x -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ldm/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -x -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | GDEV-01, GDEV-02 | unit | `pytest tests/unit/ldm/test_gamedata_browse_service.py` | No -- W0 | pending |
| 18-01-02 | 01 | 1 | GDEV-03, GDEV-04 | unit | `pytest tests/unit/ldm/test_gamedata_edit_service.py` | No -- W0 | pending |
| 18-02-01 | 02 | 2 | GDEV-01, GDEV-05 | type-check | `npx svelte-check` | N/A | pending |
| 18-02-02 | 02 | 2 | GDEV-02, GDEV-06, GDEV-07 | integration | `pytest tests/integration/test_gamedev_grid.py` | No -- W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_gamedata_browse_service.py` -- covers GDEV-01 (folder scan), GDEV-02 (entity loading)
- [ ] `tests/unit/ldm/test_gamedata_edit_service.py` -- covers GDEV-03 (inline edit save), GDEV-04 (br-tag preservation)
- [ ] `tests/integration/test_gamedev_grid.py` -- covers GDEV-06 (dynamic columns), GDEV-07 (virtual scrolling 1000+ entities)

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| File explorer tree with expand/collapse | GDEV-01 | Visual UI tree interaction | Open Game Dev mode, verify folder tree renders, expand/collapse works |
| Hierarchical grid with nesting indentation | GDEV-02 | Visual UI verification | Click a file, verify entities show parent-child nesting |
| Inline edit saves with br-tag preservation | GDEV-03 | Full round-trip verification | Edit a Name field with newline, save, reload, verify `<br/>` preserved |
| Virtual scrolling smoothness at 1000+ | GDEV-07 | Performance visual check | Load large file, scroll rapidly, verify no jank |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
