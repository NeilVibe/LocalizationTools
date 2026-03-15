---
phase: 17
slug: ai-translation-suggestions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 17 — Validation Strategy

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
| 17-01-01 | 01 | 1 | AISUG-01, AISUG-02, AISUG-04 | unit | `pytest tests/unit/ldm/test_ai_suggestion_service.py` | No -- W0 | pending |
| 17-01-02 | 01 | 1 | AISUG-01, AISUG-02, AISUG-04, AISUG-05 | unit+integration | `pytest tests/unit/ldm/test_ai_suggestion_route.py tests/integration/test_ai_suggestions_e2e.py` | No -- W0 | pending |
| 17-02-01 | 02 | 2 | AISUG-01, AISUG-03 | type-check | `npx svelte-check` | N/A | pending |
| 17-02-02 | 02 | 2 | AISUG-01, AISUG-03 | type-check | `npx svelte-check` | N/A | pending |
| 17-02-03 | 02 | 2 | AISUG-01, AISUG-02, AISUG-03, AISUG-05 | manual | Human-verify checkpoint | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_ai_suggestion_service.py` -- covers AISUG-01 (ranked suggestions), AISUG-02 (blended confidence), AISUG-04 (entity context in prompt)
- [ ] `tests/unit/ldm/test_ai_suggestion_route.py` -- covers AISUG-05 (API endpoint contract)
- [ ] `tests/integration/test_ai_suggestions_e2e.py` -- covers AISUG-01/02/04 (full pipeline with mocked Ollama + embedding engine)

All three files are created in Plan 01 (Task 1 creates service unit tests, Task 2 creates route tests + integration test).

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Right-side panel shows suggestions on segment select | AISUG-01 | Visual UI verification | Select a segment, verify AI Suggestions tab populates |
| Click suggestion applies to field without auto-replace | AISUG-03 | Interaction flow | Click a suggestion, verify it fills field without overwriting |
| "AI unavailable" graceful display | AISUG-05 | Visual UI verification | Stop Ollama, select a segment, verify message appears |
| Confidence score badges with blended scores | AISUG-02 | Visual UI verification | Verify percentage badges appear on suggestion cards |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
