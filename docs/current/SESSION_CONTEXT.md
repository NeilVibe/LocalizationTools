# Session Context

> Last Updated: 2026-01-22 (Session 56)

---

## SESSION 56: QACompiler Progress Tracker Manager Stats Fix

### Problem Solved: Category Mismatch Bug

**Symptom:** Progress Tracker showed nearly ZERO for Fixed/Reported/Checking/NonIssue, and very HIGH Pending - even though Master file compilation was PERFECT.

**Root Cause Identified via MANAGER_STATS_DEBUG.log:**
```
manager_stats categories: ['ANIMAL', 'CAMP', 'DEV', 'MAIN', 'MONSTER', 'NPC'...]
HITS: 0, MISSES: 55
MISS DETAILS: ['김선우/Character:NO_CAT', '김세련/Help:NO_CAT'...]
```

**The Bug:** Category key mismatch
- Tester stats used **folder category**: `Character`, `Quest`, `Help`, `Sequencer`
- Manager stats used **sheet names inside Master**: `MAIN`, `NPC`, `QUEST`, `ANIMAL`
- These NEVER matched → 0 HITS, all lookups failed

**Fix Applied (3 files):**

| File | Change |
|------|--------|
| `core/compiler.py` | `manager_stats[target_category]` instead of `manager_stats[sheet_name]` |
| `core/tracker_update.py` | Extract `target_category` from filename, not sheet_name |
| `tracker/data.py` | Added `get_target_master_category()` import + lookup mapping |

**Both paths now use `target_category`** (Character, Script, System) as the key.

### PENDING ISSUE: Sequencer/Dialog Categories Not Counted

**User Report:** After the fix, most categories work BUT Sequencer and Dialog are not getting counted.

**Category Mapping:**
```
Sequencer → get_target_master_category() → "Script"
Dialog → get_target_master_category() → "Script"
```

**Investigation Needed:**
1. Check new `MANAGER_STATS_DEBUG.log` for:
   - Are `[EN] Script/username` lines present? (collection working?)
   - In LOOKUP PHASE, do Sequencer/Dialog show `NO_CAT` or `NO_USER`?
2. Possible causes:
   - Master_Script.xlsx structure different?
   - STATUS_ columns not found in Script sheets?
   - EventName-based matching issue for Script-type?

**Next Steps:**
1. User will provide new log file after running with the fix
2. Check if Script category stats are being collected
3. Check if lookup is finding them for Sequencer/Dialog entries

### Files Modified This Session

```
RessourcesForCodingTheProject/NewScripts/QACompilerNEW/core/compiler.py
RessourcesForCodingTheProject/NewScripts/QACompilerNEW/core/tracker_update.py
RessourcesForCodingTheProject/NewScripts/QACompilerNEW/tracker/data.py
```

### Build Status

- Build completed successfully on GitHub Actions
- Version includes category mismatch fix
- Pending: Sequencer/Dialog investigation after user provides log

---

## SESSION 55: QACompiler Runtime Config + Comprehensive CI ✅

### Problem: Drive Letter Not Working After Install

**User Report:** Friend installed QACompiler on D: drive, config shows D:, but app still looks for F:

**Root Cause:** PyInstaller compiles config.py into bytecode at build time. Installer patched the `.py` file, but Python uses the frozen bytecode - so F: was permanently baked in.

### Solution: Runtime settings.json

| File | Change |
|------|--------|
| `config.py` | Added `_load_settings()` - reads drive from `settings.json` at runtime |
| `installer/QACompiler.iss` | Writes `settings.json` instead of patching config.py |
| `tracker/coverage.py` | Now imports paths from config.py (no more duplicates) |
| `system_localizer.py` | Imports LANGUAGE_FOLDER from config.py |
| `drive_replacer.py` | Creates `settings.json` instead of modifying source |
| `build_exe.bat` | Simplified - creates `settings.json` in dist folder |

**Test Results:** PyInstaller simulation passed - F: at compile time + D: in settings.json = app uses D: ✓

### Comprehensive CI Validation (5 Checks, 3 Jobs)

**New Pipeline Structure:**
```
Job 1: validation (Ubuntu, ~30s)
  └─ Check trigger, generate version

Job 2: safety-checks (Ubuntu, ~2min)
  ├─ CHECK 1: Python Syntax (py_compile)
  ├─ CHECK 2: Module Imports (catches missing 'import sys')
  ├─ CHECK 3: Flake8 (undefined names, errors)
  ├─ CHECK 4: Security Audit (pip-audit)
  └─ CHECK 5: Pytest Tests

Job 3: build-and-release (Windows, ~10min)
  └─ Only runs if validation passes
```

**CI Caught Real Bugs:**
- `generators/quest.py` - missing `import sys`
- `generators/item.py` - missing `import sys`
- `generators/item.py` - missing `get_first_translation` import

**Local Validation:**
```bash
python ci_validate.py        # Full check
python ci_validate.py --quick  # Fast check
```

### Files Modified

| Category | Files |
|----------|-------|
| Runtime Config | `config.py`, `installer/QACompiler.iss`, `drive_replacer.py`, `build_exe.bat` |
| Import Fixes | `tracker/coverage.py`, `system_localizer.py` |
| Bug Fixes | `generators/quest.py`, `generators/item.py` |
| CI Pipeline | `.github/workflows/qacompiler-build.yml`, `ci_validate.py` |
| Tests | `test_runtime_config.py`, `test_pyinstaller_simulation.py` |

---

## SESSION 54: Custom Subagents + Docs Cleanup ✅

### Created 9 Custom Claude Code Agents

All in `.claude/agents/` with **opus model** for maximum power:

| Agent | Purpose |
|-------|---------|
| `gdp-debugger` | EXTREME precision debugging (GDP philosophy) |
| `code-reviewer` | Svelte 5, repo pattern, security |
| `dev-tester` | DEV mode Playwright testing |
| `windows-debugger` | Windows Electron app bugs |
| `nodejs-debugger` | Node.js/Electron main process |
| `vite-debugger` | Frontend Svelte/Vite |
| `python-debugger` | FastAPI/Python backend |
| `security-auditor` | OWASP, secrets, injection, auth |
| `qacompiler-specialist` | QACompilerNEW project |

---

## Recent Sessions Summary

| Session | Achievement |
|---------|-------------|
| **55** | QACompiler runtime config fix + comprehensive CI (5 checks) |
| **54** | Custom subagents + docs cleanup |
| **53** | Slim installer (594→174 MB) |
| **52** | BUILD-001 initial attempt |
| **51** | UI-113, BUG-044, UI-114 verified |

---

## QACompiler CI Quick Reference

```bash
# Trigger QACompiler build
echo "Build - description" >> QACOMPILER_BUILD.txt
git add -A && git commit -m "QACompiler: description" && git push origin main

# Check build status
gh run list --workflow=qacompiler-build.yml --limit 1

# Local validation before push
cd RessourcesForCodingTheProject/NewScripts/QACompilerNEW
python ci_validate.py --quick
```

---

## Known Technical Debt

| Priority | Issue | Location |
|----------|-------|----------|
| **HIGH** | AsyncSessionWrapper fakes async | `dependencies.py:33-143` |
| **MEDIUM** | SQLite repos use private methods | `row_repo.py`, `tm_repo.py` |

---

*Session 55 | QACompiler v26.121.1431 | Runtime Config + CI Complete*
