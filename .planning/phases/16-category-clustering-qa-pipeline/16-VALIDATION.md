---
phase: 16
slug: category-clustering-qa-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 16 — Validation Strategy

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
| 16-01-01 | 01 | 1 | CAT-01 | unit | `pytest tests/unit/ldm/test_category_service.py` | No -- W0 | pending |
| 16-01-01 | 01 | 1 | CAT-02 | unit | `pytest tests/unit/ldm/test_rows_category.py` | No -- W0 | pending |
| 16-01-01 | 01 | 1 | CAT-03 | unit | `pytest tests/unit/ldm/test_rows_category_filter.py` | No -- W0 | pending |
| 16-02-01 | 02 | 2 | QA-03, QA-04 | unit | `pytest tests/unit/ldm/test_qa_inline.py` | No -- W0 | pending |
| 16-02-02 | 02 | 2 | QA-01, QA-02, QA-05, QA-06 | integration | `pytest tests/integration/test_qa_pipeline.py` | No -- W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_category_service.py` -- covers CAT-01 (StringID prefix classification + EXPORT path classification)
- [ ] `tests/unit/ldm/test_rows_category.py` -- covers CAT-02 (category field in row response)
- [ ] `tests/unit/ldm/test_rows_category_filter.py` -- covers CAT-03 (multi-category filter query param)
- [ ] `tests/unit/ldm/test_qa_inline.py` -- covers QA-03 (severity tiers), QA-04 (dismiss/resolve data contract)
- [ ] `tests/integration/test_qa_pipeline.py` -- covers QA-01, QA-02, QA-05, QA-06 (full QA run on mock data)
- [ ] Existing `tests/unit/ldm/test_routes_qa.py` has partial coverage for QA-01 through QA-06

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Category column visible in grid | CAT-02 | Visual UI verification | Open editor, load file, verify category column renders with colored tags |
| QA inline badge in grid rows | QA-03 | Visual UI verification | Open editor, trigger QA check, verify inline badges appear on flagged rows |
| Category filter dropdown UX | CAT-03 | Interaction flow | Click multi-select filter, select categories, verify grid updates |
| QA dismiss popover UX | QA-04 | Interaction flow | Click QA badge, click dismiss on an issue, verify it disappears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
