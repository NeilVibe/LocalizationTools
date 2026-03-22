---
phase: 56
slug: backend-service-decomposition
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | server/tests/conftest.py |
| **Quick run command** | `cd server && python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd server && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd server && python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd server && python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 56-01-01 | 01 | 1 | SVC-01 | integration | `python -c "from server.services.mega_index import get_mega_index; print('OK')"` | ❌ W0 | ⬜ pending |
| 56-02-01 | 02 | 1 | SVC-02 | integration | `python -c "from server.services.codex_service import CodexService; print('OK')"` | ❌ W0 | ⬜ pending |
| 56-03-01 | 03 | 1 | SVC-03 | integration | `python -c "from server.services.gamedata_context_service import get_gamedata_context_service; print('OK')"` | ❌ W0 | ⬜ pending |
| 56-XX-verify | ALL | 2 | ALL | smoke | `DEV_MODE=true timeout 10 python server/main.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements — this is a refactoring phase with no new test framework needed.
- Import verification is the primary validation mechanism (package __init__.py re-exports).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Codex pages render | SVC-02 | Requires running browser | Start DEV server, visit /codex, /codex/items, /codex/characters, /codex/regions — confirm data loads |
| Game Dev context panel | SVC-03 | Requires UI interaction | Open Game Dev grid, select a row, verify cross-references appear in context panel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
