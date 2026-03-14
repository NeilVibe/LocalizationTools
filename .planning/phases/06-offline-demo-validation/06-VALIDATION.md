---
phase: 6
slug: offline-demo-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Playwright (E2E) |
| **Quick run command** | `DB_MODE=sqlite pytest tests/integration/test_offline_demo.py -x -v` |
| **Full suite command** | `DB_MODE=sqlite pytest tests/ -x && cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~120 seconds |

---

## Per-Task Verification Map

| Req | Test Type | Automated Command | Status |
|-----|-----------|-------------------|--------|
| OFFL-01 | integration | `DB_MODE=sqlite pytest tests/integration/test_offline_demo.py -x` | ⬜ |
| OFFL-02 | integration | `DB_MODE=sqlite pytest tests/integration/test_offline_parity.py -x` | ⬜ |
| OFFL-03 | unit | `pytest tests/unit/test_mode_switch.py -x` | ⬜ |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
