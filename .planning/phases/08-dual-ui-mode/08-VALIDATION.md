---
phase: 08
slug: dual-ui-mode
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pytest.ini` (root) |
| **Quick run command** | `pytest tests/unit/ldm/ -x -q --no-header` |
| **Full suite command** | `pytest tests/ -x --ignore=tests/archive --ignore=tests/api --ignore=tests/cdp --ignore=tests/e2e` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ldm/ -x -q --no-header`
- **After every plan wave:** Run `pytest tests/ -x --ignore=tests/archive --ignore=tests/api --ignore=tests/cdp --ignore=tests/e2e`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | DUAL-01 | unit | `pytest tests/unit/ldm/test_filetype_detection.py -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | DUAL-02, DUAL-03 | unit | `pytest tests/unit/ldm/test_filetype_detection.py -x -k columns` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | DUAL-04 | unit | `pytest tests/unit/ldm/test_filetype_detection.py -x -k mode_indicator` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | DUAL-05 | manual | Visual: single VirtualGrid.svelte used for both modes | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_filetype_detection.py` — covers DUAL-01 through DUAL-04
- [ ] `tests/fixtures/xml/gamedev_sample.xml` — non-LocStr XML fixture for Game Dev mode testing

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shared grid infrastructure | DUAL-05 | Architectural verification, not runtime behavior | Confirm single VirtualGrid.svelte used, no duplicate grid component |
| Mode switch without state leaks | DUAL-01 | Requires UI interaction across file switches | Open translator file, switch to gamedev file, verify columns change and no stale state |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
