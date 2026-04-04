# Project Cleanup Plan

## Root Directory Issues

### Stray Files (should NOT be in root)

| File | Issue | Action |
|------|-------|--------|
| `gamedev_merge_5.xml` | Test file, 7 bytes | Delete |
| `path_settings.json` | Stray config, 36 bytes | Delete or move to `config/` |
| `test_500.tmx` | Test file, 85KB | Move to `test_data/` or delete |
| `test_big_tm.txt` | Test file, 404KB | Move to `test_data/` or delete |
| `test_tm_upload.tmx` | Test file, 356 bytes | Move to `test_data/` or delete |
| `.coverage` | pytest artifact | Add to `.gitignore` if not already |
| `htmlcov/` | Coverage HTML report | Add to `.gitignore` if not already |

### Trigger Files (OK — needed at root per CI docs)

These are correct at root: `BUILD_TRIGGER.txt`, `GITEA_TRIGGER.txt`, `GITHUB_TRIGGER.txt`, all `*_BUILD.txt` files.

### Root Directories Audit

| Directory | Status | Notes |
|-----------|--------|-------|
| `adminDashboard/` | OK | Admin Dashboard SvelteKit app |
| `archive/` | OK | Archived docs |
| `audio/` | CHECK | What's in here? Temp audio cache? |
| `bin/` | OK | vgmstream binaries |
| `config/` | OK | Server configs |
| `docs/` | OK | Documentation hub |
| `htmlcov/` | DELETE/GITIGNORE | pytest coverage output |
| `installer/` | OK | NSIS installer scripts |
| `installer_output/` | GITIGNORE | Build output |
| `landing-page/` | OK | Marketing site |
| `locaNext/` | OK | Main Electron/Svelte app |
| `logs/` | CHECK | Old logs? Should be gitignored |
| `models/` | OK | ML models |
| `node_modules/` | GITIGNORE | Should not be committed |
| `__pycache__/` | GITIGNORE | Python cache |
| `RessourcesForCodingTheProject/` | OK | RFC/NewScripts monolith |
| `runner/` | CHECK | What's in here? |
| `screenshots/` | GITIGNORE | Already gitignored |
| `scripts/` | OK | Utility scripts |
| `server/` | OK | FastAPI backend |
| `test_data/` | OK | Test fixtures |
| `testing_toolkit/` | OK | CDP/Playwright testing tools |
| `tests/` | OK | pytest test suite |
| `tools/` | CHECK | What's in here vs `server/tools/`? |
| `updates/` | CHECK | Auto-update staging? |
| `windows_tests/` | OK | Windows CI test suite |

### .gitignore Check

Verify these are gitignored:
- `htmlcov/`
- `__pycache__/`
- `.coverage`
- `node_modules/`
- `installer_output/`
- `logs/*.log`
- `screenshots/`
- `*.pyc`

## Priority

LOW — cosmetic cleanup, doesn't block Phase 110. Do AFTER auth fix is confirmed working on PEARL.

## Approach

1. Check each `CHECK` directory to understand contents
2. Delete stray test files from root
3. Verify `.gitignore` covers all artifacts
4. Move misplaced files to correct locations
5. Single commit: "chore: clean up root directory"
