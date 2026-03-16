---
phase: 12
slug: game-dev-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 12 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/unit/ldm/test_gamedev_merge.py -x` |
| **Full suite command** | `pytest tests/unit/ldm/ -x` |
| **Estimated runtime** | ~30 seconds |

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ldm/test_gamedev_merge.py -x`
- **After every plan wave:** Run `pytest tests/unit/ldm/ -x`
- **Max feedback latency:** 30 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | GMERGE-01,02,03 | unit | `pytest tests/unit/ldm/test_gamedev_merge.py -x -k diff` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | GMERGE-04,05 | unit | `pytest tests/unit/ldm/test_gamedev_merge.py -x -k depth` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | GMERGE-01 | unit | `pytest tests/unit/ldm/test_gamedev_merge.py -x -k export` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `tests/unit/ldm/test_gamedev_merge.py` — covers all GMERGE requirements
- [ ] `tests/fixtures/xml/gamedev_original.xml` — original XML for diff comparison
- [ ] `tests/fixtures/xml/gamedev_modified.xml` — modified XML with add/remove/modify changes

## Manual-Only Verifications

*All phase behaviors have automated verification.*

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
