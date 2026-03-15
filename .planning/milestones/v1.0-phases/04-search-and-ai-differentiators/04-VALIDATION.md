---
phase: 4
slug: search-and-ai-differentiators
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + Playwright |
| **Config file** | `pytest.ini`, `locaNext/playwright.config.ts` |
| **Quick run command** | `python3 -m pytest tests/unit/test_semantic_search.py -x -v` |
| **Full suite command** | `python3 -m pytest tests/unit/ -x -v && cd locaNext && npx playwright test --project=chromium` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** `python3 -m pytest tests/unit/test_tm_search.py tests/unit/test_semantic_search.py -x -v`
- **After every plan wave:** Full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SRCH-01, SRCH-03 | unit | `pytest tests/unit/test_semantic_search.py -x -v` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | AI-01 | unit | `pytest tests/unit/test_tm_search.py -x -v` | ✅ exists | ⬜ pending |
| 04-02-01 | 02 | 2 | SRCH-02 | E2E | `npx playwright test tests/semantic-search.spec.ts -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | AI-02 | E2E | `npx playwright test tests/ai-indicator.spec.ts -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_semantic_search.py` — stubs for SRCH-01, SRCH-03 (semantic endpoint, performance)
- [ ] `locaNext/tests/semantic-search.spec.ts` — stubs for SRCH-02 (UI search results with scores)
- [ ] `locaNext/tests/ai-indicator.spec.ts` — stubs for AI-02 (AI badge in editor)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Search feels instant | SRCH-03 | Subjective perception | Try several searches, check responsiveness |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
