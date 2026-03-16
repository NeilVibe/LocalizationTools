---
phase: 09
slug: translator-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest tests/unit/ldm/test_translator_merge.py tests/unit/ldm/test_postprocess.py -x` |
| **Full suite command** | `python -m pytest tests/unit/ldm/ -x` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ldm/test_translator_merge.py tests/unit/ldm/test_postprocess.py -x`
- **After every plan wave:** Run `python -m pytest tests/unit/ldm/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | TMERGE-01 | unit | `pytest tests/unit/ldm/test_translator_merge.py -x -k strict` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | TMERGE-02 | unit | `pytest tests/unit/ldm/test_translator_merge.py -x -k strorigin` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | TMERGE-03 | unit | `pytest tests/unit/ldm/test_translator_merge.py -x -k fuzzy` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | TMERGE-04 | unit | `pytest tests/unit/ldm/test_postprocess.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_translator_merge.py` — covers TMERGE-01, TMERGE-02, TMERGE-03 + skip guards
- [ ] `tests/unit/ldm/test_postprocess.py` — covers TMERGE-04 (8-step pipeline + CJK + br-tags)
- [ ] `tests/fixtures/xml/merge_source.xml` — source file with corrections
- [ ] `tests/fixtures/xml/merge_target.xml` — target file to merge into

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Merge progress indicator | TMERGE-01 | UI behavior | Trigger merge on large file, verify progress shown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
