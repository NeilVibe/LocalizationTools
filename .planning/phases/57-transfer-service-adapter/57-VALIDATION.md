---
phase: 57
slug: transfer-service-adapter
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python -m pytest tests/test_transfer_adapter.py -x -q` |
| **Full suite command** | `python -m pytest tests/test_transfer_adapter.py tests/test_match_types.py tests/test_folder_merge.py -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_transfer_adapter.py -x -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 57-01-01 | 01 | 1 | XFER-01 | unit | `pytest tests/test_transfer_adapter.py::test_config_shim` | ❌ W0 | ⬜ pending |
| 57-01-02 | 01 | 1 | XFER-01 | unit | `pytest tests/test_transfer_adapter.py::test_import_modules` | ❌ W0 | ⬜ pending |
| 57-02-01 | 02 | 1 | XFER-02,XFER-03 | integration | `pytest tests/test_match_types.py` | ❌ W0 | ⬜ pending |
| 57-02-02 | 02 | 1 | XFER-04 | unit | `pytest tests/test_transfer_adapter.py::test_postprocess` | ❌ W0 | ⬜ pending |
| 57-03-01 | 03 | 2 | XFER-05,XFER-06,XFER-07 | integration | `pytest tests/test_folder_merge.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_transfer_adapter.py` — stubs for XFER-01, XFER-04
- [ ] `tests/test_match_types.py` — stubs for XFER-02, XFER-03
- [ ] `tests/test_folder_merge.py` — stubs for XFER-05, XFER-06, XFER-07

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-language merge with real test123 data | XFER-07 | Real filesystem data needed | Run `setup_mock_data.py`, set LOC PATH to test123, execute merge |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
