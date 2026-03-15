---
phase: 5.1
slug: contextual-intelligence-qa-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 5.1 — Validation Strategy

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Playwright (E2E) |
| **Quick run command** | `pytest tests/unit/ldm/test_glossary_service.py tests/unit/ldm/test_qa_engine.py -x -v` |
| **Full suite command** | `pytest tests/ -x && cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Per-Task Verification Map

| Req | Test Type | Automated Command | Status |
|-----|-----------|-------------------|--------|
| CTX-01 | unit | `pytest tests/unit/ldm/test_glossary_service.py -x` | ⬜ |
| CTX-02 | unit | `pytest tests/unit/ldm/test_glossary_service.py::test_ac_detection -x` | ⬜ |
| CTX-03-05 | E2E | `npx playwright test tests/context-panel.spec.ts -x` | ⬜ |
| CTX-06 | unit | `pytest tests/unit/ldm/test_category_clustering.py -x` | ⬜ |
| CTX-07 | E2E | `npx playwright test tests/ai-indicator.spec.ts -x` | ⬜ |
| CTX-08-10 | E2E | `npx playwright test tests/context-panel.spec.ts -x` | ⬜ |
| QA-01 | unit | `pytest tests/unit/ldm/test_qa_engine.py::test_line_check -x` | ⬜ |
| QA-02 | unit | `pytest tests/unit/ldm/test_qa_engine.py::test_term_check -x` | ⬜ |
| QA-03 | E2E | `npx playwright test tests/qa-panel.spec.ts -x` | ⬜ |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
