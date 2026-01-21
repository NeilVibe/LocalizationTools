# Session Context

> Last Updated: 2026-01-21 (Session 55)

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
