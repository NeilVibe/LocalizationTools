---
phase: 15
slug: mock-gamedata-universe
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `server/tools/ldm/tests/conftest.py` |
| **Quick run command** | `cd server && python -m pytest tools/ldm/tests/test_mock_gamedata.py -x -q` |
| **Full suite command** | `cd server && python -m pytest tools/ldm/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd server && python -m pytest tools/ldm/tests/test_mock_gamedata.py -x -q`
- **After every plan wave:** Run `cd server && python -m pytest tools/ldm/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| (Populated by planner) | | | | | | | |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/tools/ldm/tests/test_mock_gamedata.py` — test stubs for MOCK-01..08
- [ ] `server/tools/ldm/tests/conftest.py` — mock gamedata fixture path

*Existing test infrastructure (478 tests) covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DDS images render in browser | MOCK-03 | Visual check | Load mock item in LocaNext, verify image displays |
| WEM audio plays | MOCK-03 | Audio check | Load mock entity with audio, verify playback |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
