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
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `python3 -m pytest tests/integration/test_merge_pipeline.py -x -q --timeout=120` |
| **Full suite command** | `python3 -m pytest tests/integration/test_merge_*.py -v --timeout=120` |
| **Estimated runtime** | ~60 seconds (with live server) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 1 | MOCK-01..04, SET-01..03, API-01..04, XFER-01, XFER-07 | integration | `pytest tests/integration/test_merge_pipeline.py -x -v --timeout=120` | No (W0) | pending |
| 60-02-01 | 02 | 2 | XFER-02..06 (fixtures) | unit | `ls tests/fixtures/merge/*.xml \| wc -l` | No (W0) | pending |
| 60-02-02 | 02 | 2 | XFER-02..06 (match types) | integration | `pytest tests/integration/test_merge_match_types.py -x -v --timeout=120` | No (W0) | pending |

*Status: pending / green / red / flaky*

---

## Per-Test Function Map

### Plan 01: test_merge_pipeline.py

| Test Function | Requirements Covered |
|--------------|---------------------|
| `test_mock_data_setup` | MOCK-01, MOCK-02, MOCK-03, MOCK-04 |
| `test_health_endpoint` | (infrastructure) |
| `test_settings_path_validation` | SET-01, SET-02, SET-03 |
| `test_preview_single_language` | API-01 |
| `test_preview_invalid_match_mode` | API-01 (error handling) |
| `test_execute_streams_sse` | API-02, API-03, XFER-01 |
| `test_multi_language_preview` | API-04, XFER-07 |
| `test_sse_event_types_ordered` | API-02 |

### Plan 02: test_merge_match_types.py

| Test Function | Requirements Covered |
|--------------|---------------------|
| `test_stringid_only_match` | XFER-02 |
| `test_strict_match` | XFER-03 |
| `test_strorigin_filename_match` | XFER-04 |
| `test_only_untranslated_scope` | XFER-06 |
| `test_all_match_modes_valid` | XFER-02, XFER-03, XFER-04 |
| `test_postprocess_runs_on_execute` | XFER-05 |

---

## Wave 0 Requirements

- [ ] `tests/integration/conftest_merge.py` — Shared fixtures (server check, admin auth, temp dirs)
- [ ] `tests/integration/test_merge_pipeline.py` — E2E merge pipeline + settings validation tests
- [ ] `tests/integration/test_merge_match_types.py` — Match type verification tests
- [ ] `tests/fixtures/merge/*.xml` — Synthetic XML fixtures (4 files)

*Existing tests/conftest.py + admin token fixtures cover auth requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Merge button in toolbar opens modal | UI-01 | Requires browser interaction | Open Files page, click Merge button, verify modal appears |
| Right-click context menu entry | UI-02 | Requires browser interaction | Right-click project_MULTI folder, verify "Merge Folder to LOCDEV" option |
| 4-phase modal flow (configure/preview/execute/done) | UI-03 | Visual state machine | Walk through all 4 phases in merge modal |
| Category filter toggle for StringID mode | UI-04 | Visual UI element | Select StringID match type, verify toggle appears |
| Dry-run preview panel | UI-05 | Visual verification | Run preview, verify results panel shows counts |
| Progress display during execution | UI-06 | Visual/animation | Execute merge, verify progress bar updates |
| Summary report on completion | UI-07 | Visual verification | Complete merge, verify done phase shows summary |
| Language badge in modal header | UI-08 | Visual verification | Open modal, verify language badge matches project |
| Multi-language mode detected languages | UI-09 | Visual verification | Open multi-lang merge, verify language list shown |

*UI-01 through UI-09 are manual-only because they require Playwright browser automation or visual inspection. They are NOT covered by the pytest integration tests.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
