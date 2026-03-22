---
phase: 56
slug: mock-data-settings
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Node.js assert (store unit test) + svelte-check (frontend compilation) |
| **Config file** | `server/pytest.ini` / `locaNext/tsconfig.json` |
| **Quick run command** | `python -m pytest tests/test_mock_data.py tests/test_path_validation.py -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short && node tests/test_project_settings_store.js` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_mock_data.py tests/test_path_validation.py -x -q --tb=short`
- **After every plan wave:** Run full suite including `node tests/test_project_settings_store.js`
- **Before `/gsd:verify-work`:** Full suite must be green + svelte-check passes
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 56-01-01 | 01 | 1 | MOCK-01, MOCK-02, MOCK-03, MOCK-04 | unit+integration | `python -m pytest tests/test_mock_data.py -x -q` | tests/test_mock_data.py | ⬜ pending |
| 56-01-02 | 01 | 1 | MOCK-01 | integration | `python scripts/setup_mock_data.py --confirm-wipe && sqlite3 server/data/offline.db "SELECT COUNT(*) FROM ldm_projects"` | N/A (CLI) | ⬜ pending |
| 56-02-01 | 02 | 1 | SET-03 | unit | `python -m pytest tests/test_path_validation.py -x -q` | tests/test_path_validation.py | ⬜ pending |
| 56-02-02 | 02 | 1 | SET-01, SET-02 | unit | `node tests/test_project_settings_store.js` | tests/test_project_settings_store.js | ⬜ pending |
| 56-02-03 | 02 | 1 | SET-01, SET-02, SET-03 | compilation | `cd locaNext && npx svelte-check --tsconfig ./tsconfig.json` | N/A (compiler) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage

| Req ID | Behavior | Test File | Test Function(s) |
|--------|----------|-----------|-------------------|
| MOCK-01 | Script creates platform + 3 projects in DB | tests/test_mock_data.py | test_wipe_and_create |
| MOCK-02 | Language auto-detection from project name | tests/test_mock_data.py | test_language_detection |
| MOCK-03 | project_MULTI has language-suffixed subfolders | tests/test_mock_data.py | test_multi_project_folders |
| MOCK-04 | test123 languagedata files (.txt) loadable | tests/test_mock_data.py | test_validate_txt_path, test_validate_xml_path, test_validate_empty_path |
| SET-01 | LOC PATH configurable and persistent | tests/test_project_settings_store.js | set/get round-trip, per-project isolation |
| SET-02 | EXPORT PATH configurable and persistent | tests/test_project_settings_store.js | set/get round-trip, per-project isolation |
| SET-03 | Path validation shows errors for invalid paths | tests/test_path_validation.py | test_validate_valid_xml_path, test_validate_valid_txt_path, test_validate_nonexistent_path, test_validate_not_directory, test_validate_no_langdata |

---

## Wave 0 Requirements

- [ ] `tests/test_mock_data.py` — stubs for MOCK-01, MOCK-02, MOCK-03, MOCK-04 (created by Plan 01 Task 1)
- [ ] `tests/test_path_validation.py` — stubs for SET-03 (created by Plan 02 Task 1)
- [ ] `tests/test_project_settings_store.js` — stubs for SET-01, SET-02 (created by Plan 02 Task 2)

*All test files are created as part of their respective plan tasks (TDD pattern).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Language badge renders correctly | MOCK-03 | Visual UI element | Screenshot file explorer, verify badge text/color |
| Settings page layout | SET-01 | Visual layout | Screenshot Settings dropdown, verify "Project Settings" item; open modal, verify LOC/EXPORT fields present |
| Modal disabled state | SET-01 | UX behavior | With no project selected, verify "Project Settings" button is disabled in dropdown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
