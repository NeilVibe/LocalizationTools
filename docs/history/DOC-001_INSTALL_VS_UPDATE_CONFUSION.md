# DOC-001: Install vs Update - Critical Documentation Confusion

**Created:** 2025-12-28 | **Severity:** CRITICAL | **Status:** ✅ RESOLVED

---

## The Problem

Claude (and documentation) conflates two COMPLETELY DIFFERENT operations:

| Operation | What It Is | When To Use |
|-----------|------------|-------------|
| **INSTALL** | Fresh installation from installer | First time setup, clean slate, testing new builds |
| **UPDATE** | Auto-updater downloads delta | App already installed, just need new version |

## Why This Is Critical

1. **Wrong advice given** - Telling user to "install" when they should just wait for auto-update
2. **Wasted time** - Full reinstall takes minutes, auto-update takes seconds
3. **Different testing scenarios** - Install tests first-run, Update tests upgrade path
4. **Confusion in protocols** - Docs mix these up causing incorrect workflows

---

## INSTALL - Fresh Installation

### What It Does
- Downloads full installer (.exe) from Gitea artifacts
- Runs NSIS installer on Windows
- Creates fresh AppData, fresh config
- First-run setup triggers (Python deps, model download)

### When To Use
- First time installing on a machine
- Testing first-run experience
- Clean slate testing (after uninstall)
- Major version upgrades that require clean install

### Command
```bash
./scripts/playground_install.sh --launch --auto-login
```

### Time: 2-5 minutes (includes setup)

---

## UPDATE - Auto-Updater

### What It Does
- App checks GitHub releases for new version
- Downloads delta/full update in background
- Shows notification to user
- User clicks "Install & Restart"
- App restarts with new version

### When To Use
- App already installed and working
- Just pushed a new build
- Testing the update flow itself
- Normal user workflow

### How To Trigger
1. Open LocaNext (already installed)
2. App auto-checks on startup
3. Or: Menu → Help → Check for Updates
4. Wait for notification
5. Click Download → Install & Restart

### Time: 30 seconds - 2 minutes

---

## Decision Matrix

| Scenario | Use INSTALL | Use UPDATE |
|----------|-------------|------------|
| App not installed yet | ✅ | ❌ |
| App installed, testing new code | ❌ | ✅ |
| Testing first-run setup | ✅ | ❌ |
| Testing auto-updater | ❌ | ✅ |
| Clean slate needed | ✅ | ❌ |
| Quick verification of fix | ❌ | ✅ |
| User reported bug | ❌ | ✅ |

---

## Documents To Fix

| Document | Issue | Fix Needed |
|----------|-------|------------|
| `CLAUDE.md` | Mentions install but not update distinction | Add clear section |
| `testing_toolkit/MASTER_TEST_PROTOCOL.md` | May conflate install/update | Review and clarify |
| `docs/cicd/HOW_TO_BUILD.md` | Build → ??? → Test unclear | Add post-build options |
| `scripts/playground_install.sh` | Name implies only install | Add comments clarifying purpose |

---

## Action Items

1. [x] Add "Install vs Update" section to CLAUDE.md ✅ DONE
2. [x] Update MASTER_TEST_PROTOCOL.md with clear distinction ✅ DONE
3. [x] Create quick reference card (in DOC-001 itself) ✅ DONE
4. [x] Review all docs mentioning "install" or "update" ✅ DONE
5. [x] Add this knowledge to CONFUSION_HISTORY.md (#16) ✅ DONE
6. [x] Update HOW_TO_BUILD.md with post-build section ✅ DONE

---

*This confusion caused incorrect guidance during UI-062 verification discussion*
