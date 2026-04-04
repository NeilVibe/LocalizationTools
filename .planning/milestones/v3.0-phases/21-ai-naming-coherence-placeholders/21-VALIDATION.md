---
phase: 21
slug: ai-naming-coherence-placeholders
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `tests/conftest.py` (backend) |
| **Quick run command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/unit/ldm/ -x -q --tb=short` |
| **Full suite command** | `cd /home/<USERNAME>/LocalizationTools && python -m pytest tests/ -x -q --tb=short` |
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
| 21-01-01 | 01 | 1 | AINAME-01, AINAME-02, AINAME-03 | unit | `pytest tests/unit/ldm/test_naming_service.py` | No -- W0 | pending |
| 21-01-02 | 01 | 1 | AINAME-01, AINAME-02 | unit | `pytest tests/unit/ldm/test_naming_route.py` | No -- W0 | pending |
| 21-02-01 | 02 | 2 | PLACEHOLDER-01, PLACEHOLDER-02, PLACEHOLDER-03 | type-check | `npx svelte-check` | N/A | pending |
| 21-02-02 | 02 | 2 | AINAME-01, AINAME-02 | type-check | `npx svelte-check` | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_naming_service.py` -- covers AINAME-01/02/03 (similar names, Qwen3 suggestions, Ollama fallback)
- [ ] `tests/unit/ldm/test_naming_route.py` -- covers AINAME-01/02 (API contract)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Similar names appear on Name edit | AINAME-01 | Visual UI verification | Edit a Name field in Game Dev, verify similar names panel |
| AI naming suggestions non-blocking | AINAME-02 | UX timing check | Verify suggestions appear without blocking editing |
| Image placeholder with category icon | PLACEHOLDER-01 | Visual rendering | Navigate to entity with missing image, verify styled SVG |
| Audio placeholder with waveform | PLACEHOLDER-02 | Visual rendering | Navigate to entity with missing audio, verify styled SVG |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
