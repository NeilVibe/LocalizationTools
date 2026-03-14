---
phase: 5
slug: visual-polish-and-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 5 — Validation Strategy

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Playwright (E2E) |
| **Config file** | `pytest.ini`, `locaNext/playwright.config.ts` |
| **Quick run command** | `pytest tests/unit/ldm/test_mapdata_service.py -x -q` |
| **Full suite command** | `pytest tests/ -x && cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~90 seconds |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | MAP-01, MAP-02 | unit | `pytest tests/unit/ldm/test_mapdata_service.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | UI-04 | E2E | `npx playwright test tests/settings-modal.spec.ts -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | MAP-03 | E2E | `npx playwright test tests/mapdata-context.spec.ts -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | UI-05 | E2E | `npx playwright test tests/visual-polish.spec.ts -x` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_mapdata_service.py` — MAP-01, MAP-02
- [ ] `locaNext/tests/settings-modal.spec.ts` — UI-04
- [ ] `locaNext/tests/mapdata-context.spec.ts` — MAP-03
- [ ] `locaNext/tests/visual-polish.spec.ts` — UI-05

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
