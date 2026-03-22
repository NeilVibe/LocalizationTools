---
phase: 60
slug: integration-testing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 60 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `server/tests/conftest.py` |
| **Quick run command** | `cd server && python -m pytest tests/test_merge_integration.py -x -q` |
| **Full suite command** | `cd server && python -m pytest tests/test_merge_integration.py -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 1 | MOCK-SETUP | integration | `pytest tests/test_merge_integration.py::test_mock_setup -v` | ❌ W0 | ⬜ pending |
| 60-01-02 | 01 | 1 | MERGE-E2E | integration | `pytest tests/test_merge_integration.py::test_e2e_single_project -v` | ❌ W0 | ⬜ pending |
| 60-01-03 | 01 | 1 | MULTI-LANG | integration | `pytest tests/test_merge_integration.py::test_multi_language_merge -v` | ❌ W0 | ⬜ pending |
| 60-01-04 | 01 | 1 | SSE-STREAM | integration | `pytest tests/test_merge_integration.py::test_sse_progress -v` | ❌ W0 | ⬜ pending |
| 60-02-01 | 02 | 1 | MATCH-EXACT | integration | `pytest tests/test_merge_match_types.py::test_exact_match -v` | ❌ W0 | ⬜ pending |
| 60-02-02 | 02 | 1 | MATCH-FUZZY | integration | `pytest tests/test_merge_match_types.py::test_fuzzy_match -v` | ❌ W0 | ⬜ pending |
| 60-02-03 | 02 | 1 | MATCH-REGEX | integration | `pytest tests/test_merge_match_types.py::test_regex_match -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/tests/test_merge_integration.py` — E2E merge pipeline tests
- [ ] `server/tests/test_merge_match_types.py` — Match type verification tests
- [ ] Test fixtures for mock XML languagedata files

*Existing conftest.py + admin token fixtures cover auth requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI merge modal opens from toolbar | SC-1 | Requires browser | Open Files page, click Merge button, verify modal appears |
| Right-click context menu entry | SC-2 | Requires browser | Right-click project_MULTI folder, verify "Merge to LOCDEV" option |
| SSE progress bar animation | SC-4 | Visual verification | Execute merge, verify progress bar updates smoothly |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
