---
phase: 31
slug: codex-ai-image-generation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-16
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 with pytest-asyncio |
| **Config file** | pytest.ini (existing, comprehensive) |
| **Quick run command** | `python -m pytest tests/unit/ldm/test_ai_image_service.py -x -v` |
| **Full suite command** | `python -m pytest tests/unit/ldm/ -x -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ldm/test_ai_image_service.py -x -v`
- **After every plan wave:** Run `python -m pytest tests/unit/ldm/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | IMG-01 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_generate_image -x` | ❌ W0 | ⬜ pending |
| 31-01-01 | 01 | 1 | IMG-02 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_prompt_templates -x` | ❌ W0 | ⬜ pending |
| 31-01-01 | 01 | 1 | IMG-02 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_aspect_ratios -x` | ❌ W0 | ⬜ pending |
| 31-01-01 | 01 | 1 | IMG-03 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_cache_operations -x` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | IMG-03 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_serve_generated_image -x` | ❌ W0 | ⬜ pending |
| 31-02-01 | 02 | 2 | IMG-04 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_batch_generation -x` | ❌ W0 | ⬜ pending |
| 31-02-01 | 02 | 2 | IMG-04 | unit | `python -m pytest tests/unit/ldm/test_ai_image_service.py::test_batch_progress -x` | ❌ W0 | ⬜ pending |
| 31-02-02 | 02 | 2 | IMG-01 | manual | Playwright screenshot verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_ai_image_service.py` — covers IMG-01, IMG-02, IMG-03, IMG-04 (service layer)
- [ ] Extend `tests/unit/ldm/test_codex_route.py` — covers IMG-03 (serve endpoint), IMG-01 (generate endpoint)
- [ ] Mock `google.genai.Client` — must mock Gemini API calls, never hit real API in tests
- [ ] Test fixtures: sample PNG bytes for mock responses, test entity with full attributes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PlaceholderImage replaced when AI image available | IMG-01 | Visual verification needed | Open Codex, generate image for entity, verify placeholder replaced with AI image |
| Batch progress bar shows correct percentage | IMG-04 | Real-time UI verification | Start batch generation, verify progress bar updates |
| Generated images match entity type aesthetics | IMG-02 | Subjective quality check | Review generated portraits, icons, landscapes for appropriate style |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
