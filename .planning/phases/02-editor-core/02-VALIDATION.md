---
phase: 2
slug: editor-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright (frontend E2E) + pytest (backend unit) |
| **Config file** | `locaNext/playwright.config.ts` (Playwright), `tests/conftest.py` (pytest) |
| **Quick run command** | `cd locaNext && npx playwright test tests/confirm-row.spec.ts tests/search-verified.spec.ts -x` |
| **Full suite command** | `cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd locaNext && npx playwright test tests/confirm-row.spec.ts tests/search-verified.spec.ts -x`
- **After every plan wave:** Run `cd locaNext && npx playwright test --project=chromium`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | EDIT-01 | E2E perf | `cd locaNext && npx playwright test tests/grid-performance.spec.ts -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | EDIT-02 | E2E visual | `cd locaNext && npx playwright test tests/grid-status-colors.spec.ts -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | EDIT-03 | E2E | `cd locaNext && npx playwright test tests/search-verified.spec.ts -x` | ✅ partial | ⬜ pending |
| 02-02-01 | 02 | 1 | EDIT-04 | E2E regression | `cd locaNext && npx playwright test tests/grid-save-no-overflow.spec.ts -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | EDIT-05 | E2E | `cd locaNext && npx playwright test tests/confirm-row.spec.ts -x` | ✅ partial | ⬜ pending |
| 02-03-01 | 03 | 2 | EDIT-06 | API integration | `python3 -m pytest tests/integration/test_export_roundtrip.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | UI-01 | E2E screenshot | `cd locaNext && npx playwright test tests/grid-visual-quality.spec.ts -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `locaNext/tests/grid-performance.spec.ts` — stubs for EDIT-01 (10K+ segments scroll perf)
- [ ] `locaNext/tests/grid-status-colors.spec.ts` — stubs for EDIT-02 (3-state color verification)
- [ ] `locaNext/tests/grid-save-no-overflow.spec.ts` — stubs for EDIT-04 (Ctrl+S overflow regression)
- [ ] `tests/integration/test_export_roundtrip.py` — stubs for EDIT-06 (XML roundtrip with br-tags)
- [ ] `locaNext/tests/grid-visual-quality.spec.ts` — stubs for UI-01 (screenshot comparison)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grid feels responsive at 10K rows | EDIT-01 | FPS measurement in headless is approximate | Open 10K file, scroll rapidly, check for jank |
| Executive demo visual quality | UI-01 | Subjective assessment | Screenshot review by stakeholder |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
