---
phase: 3
slug: tm-workflow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (frontend E2E) + pytest (backend API) |
| **Config file** | `locaNext/playwright.config.ts`, `tests/conftest.py` |
| **Quick run command** | `cd locaNext && npx playwright test --grep "tm" -x` |
| **Full suite command** | `cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd locaNext && npx playwright test --grep "tm" -x`
- **After every plan wave:** Run `cd locaNext && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TM-01 | E2E | `npx playwright test tests/tm-auto-mirror.spec.ts -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TM-02 | E2E | `npx playwright test tests/tm-assignment-test.spec.ts -x` | ✅ needs update | ⬜ pending |
| 03-02-01 | 02 | 1 | TM-03 | E2E | `npx playwright test tests/tm-color-diff.spec.ts -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | TM-05 | API | `pytest tests/api/test_tm_search.py -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | TM-04 | API+E2E | `pytest tests/api/test_leverage.py -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | UI-02, UI-03 | E2E visual | `npx playwright test tests/tm-explorer-polish.spec.ts -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `locaNext/tests/tm-auto-mirror.spec.ts` — stubs for TM-01 (upload triggers TM creation)
- [ ] `locaNext/tests/tm-color-diff.spec.ts` — stubs for TM-03 (color-coded matches, word diff)
- [ ] `locaNext/tests/tm-explorer-polish.spec.ts` — stubs for UI-03 (visual quality)
- [ ] `tests/api/test_leverage.py` — stubs for TM-04 (leverage stats API)
- [ ] `tests/api/test_tm_search.py` — stubs for TM-05 (Model2Vec cascade search)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tree visual polish quality | UI-02, UI-03 | Subjective assessment | Screenshot review — trees look professional |
| Word-level diff readability | TM-03 | Visual quality check | Verify Korean syllable-level diff is readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
