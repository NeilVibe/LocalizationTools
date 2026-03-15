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
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `tests/conftest.py` (backend), `locaNext/vitest.config.ts` (frontend) |
| **Quick run command** | `cd tests && python -m pytest unit/ -x -q --tb=short` |
| **Full suite command** | `cd tests && python -m pytest unit/ integration/ -q --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd tests && python -m pytest unit/ -x -q --tb=short`
- **After every plan wave:** Run `cd tests && python -m pytest unit/ integration/ -q --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CAT-01 | unit | `pytest tests/unit/test_category_mapper.py` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | CAT-02, CAT-03 | unit | `pytest tests/unit/test_category_filter.py` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | QA-01, QA-02 | unit | `pytest tests/unit/test_qa_term_check.py` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | QA-03, QA-04 | unit | `pytest tests/unit/test_qa_line_check.py` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 2 | QA-05, QA-06 | unit | `pytest tests/unit/test_qa_dismiss.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_category_mapper.py` — stubs for CAT-01
- [ ] `tests/unit/test_category_filter.py` — stubs for CAT-02, CAT-03
- [ ] `tests/unit/test_qa_term_check.py` — stubs for QA-01, QA-02
- [ ] `tests/unit/test_qa_line_check.py` — stubs for QA-03, QA-04
- [ ] `tests/unit/test_qa_dismiss.py` — stubs for QA-05, QA-06

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Category column visible in grid | CAT-01 | Visual UI verification | Open editor, load file, verify category column renders |
| QA indicators inline in editor | QA-02 | Visual UI verification | Open editor, trigger Term Check, verify inline highlights |
| Filter dropdown UX | CAT-03 | Interaction flow | Click filter, select categories, verify grid updates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
