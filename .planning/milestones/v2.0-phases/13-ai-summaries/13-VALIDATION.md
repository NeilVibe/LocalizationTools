---
phase: 13
slug: ai-summaries
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 13 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/unit/ldm/test_ai_summary.py -x` |
| **Full suite command** | `pytest tests/unit/ldm/ -x` |
| **Estimated runtime** | ~30 seconds |

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ldm/test_ai_summary.py -x`
- **After every plan wave:** Run `pytest tests/unit/ldm/ -x`
- **Max feedback latency:** 30 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | AISUM-01,04 | unit | `pytest tests/unit/ldm/test_ai_summary.py -x -k endpoint` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | AISUM-02 | unit | `pytest tests/unit/ldm/test_ai_summary.py -x -k cache` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | AISUM-03,05 | unit | `pytest tests/unit/ldm/test_ai_summary.py -x -k fallback` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_ai_summary.py` — covers all AISUM requirements

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Summary renders in ContextTab | AISUM-03 | UI rendering | Select entity string, check ContextTab shows 2-line summary |
| AI unavailable badge | AISUM-05 | UI rendering | Stop Ollama, select string, check badge appears |

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
