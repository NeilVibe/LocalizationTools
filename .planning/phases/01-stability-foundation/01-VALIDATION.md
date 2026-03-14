---
phase: 1
slug: stability-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `pytest.ini` (exists, needs stability marker added) |
| **Quick run command** | `pytest tests/stability/ -x -q --no-cov` |
| **Full suite command** | `pytest tests/stability/ -v --tb=short` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/stability/ -x -q --no-cov`
- **After every plan wave:** Run `pytest tests/stability/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | STAB-05 | unit | `pytest tests/stability/test_schema_drift.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | STAB-02, STAB-03 | unit | `pytest tests/stability/test_*_repo.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | STAB-01 | integration | `pytest tests/stability/test_startup.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | STAB-04 | integration | `pytest tests/stability/test_zombie.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/stability/__init__.py` — package marker
- [ ] `tests/stability/conftest.py` — mode parametrization, clean_db fixture, game_data_factory, behavioral equivalence helpers
- [ ] `tests/stability/test_platform_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_project_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_folder_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_file_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_row_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_tm_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_qa_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_trash_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_capability_repo.py` — covers STAB-02, STAB-03
- [ ] `tests/stability/test_startup.py` — covers STAB-01
- [ ] `tests/stability/test_zombie.py` — covers STAB-04
- [ ] `tests/stability/test_schema_drift.py` — covers STAB-05
- [ ] `pytest-asyncio` installed (for async repo tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Electron 10-start reliability | STAB-01 | Requires Windows desktop app | Run `playground_install.sh`, launch/close LocaNext 10 times, check Task Manager for zombies |
| Force quit zombie check | STAB-04 | Requires Task Manager kill on Windows | Kill LocaNext from Task Manager, verify no Python processes remain on port 8888 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
