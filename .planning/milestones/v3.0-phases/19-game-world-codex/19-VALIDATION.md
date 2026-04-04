---
phase: 19
slug: game-world-codex
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `tests/conftest.py` (backend) |
| **Quick run command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/unit/ldm/ -x -q --tb=short` |
| **Full suite command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/ -x -q --tb=short` |
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
| 19-01-01 | 01 | 1 | CODEX-01, CODEX-02, CODEX-04 | unit | `pytest tests/unit/ldm/test_codex_service.py` | No -- W0 | pending |
| 19-01-02 | 01 | 1 | CODEX-03 | unit | `pytest tests/unit/ldm/test_codex_search.py` | No -- W0 | pending |
| 19-02-01 | 02 | 2 | CODEX-01, CODEX-02, CODEX-05 | type-check | `npx svelte-check` | N/A | pending |
| 19-02-02 | 02 | 2 | CODEX-01 through CODEX-05 | integration | `pytest tests/integration/test_codex_e2e.py` | No -- W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_codex_service.py` -- covers CODEX-01 (entity registry), CODEX-02 (cross-references), CODEX-04 (media paths)
- [ ] `tests/unit/ldm/test_codex_search.py` -- covers CODEX-03 (semantic search with FAISS)
- [ ] `tests/integration/test_codex_e2e.py` -- covers full codex pipeline with mock data

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Character page rendering with image | CODEX-01 | Visual UI verification | Navigate to codex, click character, verify fields render |
| Item page with similar items | CODEX-02 | Visual UI verification | Click item, verify similar items section appears |
| Semantic search results | CODEX-03 | Search quality check | Search for entity, verify relevant results |
| DDS->PNG and WEM->WAV playback | CODEX-04 | Media rendering check | Verify image displays and audio plays |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
