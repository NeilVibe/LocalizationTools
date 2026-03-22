---
phase: 58
slug: merge-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python3 -m pytest tests/test_merge_api.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/test_merge_api.py -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_merge_api.py -x -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 58-01-01 | 01 | 1 | API-01,API-04 | integration | `pytest tests/test_merge_api.py::test_preview` | ❌ W0 | ⬜ pending |
| 58-02-01 | 02 | 1 | API-02,API-03 | integration | `pytest tests/test_merge_api.py::test_execute` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_merge_api.py` — stubs for API-01 through API-04

*Existing pytest + httpx infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE streaming visible in browser dev tools | API-02 | Real-time stream rendering | Open browser, trigger merge, watch Network tab for EventSource |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
