# DOC-001: Install vs Update Confusion

**Issue ID:** DOC-001
**Date:** 2026-02-01
**Status:** Documented
**Category:** Process Documentation

---

## Problem Statement

Confusion between INSTALL and UPDATE operations when deploying new builds to the Playground test environment. This led to:
- Unnecessary full reinstalls when a simple update would suffice
- Wasted time (2-5 min vs 30 sec - 2 min)
- Potential loss of local state during unnecessary reinstalls

---

## The Distinction

| Aspect | INSTALL | UPDATE |
|--------|---------|--------|
| **What** | Fresh installation from .exe | Auto-updater downloads new version |
| **When** | First time, clean slate, testing first-run | App already installed, just need new code |
| **Time** | 2-5 min (includes Python setup) | 30 sec - 2 min |
| **Command** | `./scripts/playground_install.sh` | Just open the app, it auto-updates |
| **Local State** | Cleared | Preserved |
| **Python Deps** | Reinstalled | Kept |
| **Qwen Model** | Re-downloaded (2.3GB) | Kept |

---

## Decision Tree: Which To Use?

```
App NOT installed yet?          --> INSTALL
App installed, testing new fix? --> UPDATE (just open the app!)
Testing first-run experience?   --> INSTALL (after uninstall)
Testing auto-updater itself?    --> UPDATE
Quick verification of fix?      --> UPDATE
Need clean state?               --> INSTALL (after uninstall)
```

---

## UPDATE Flow (Most Common!)

1. Push code to Gitea --> Build completes
2. Open LocaNext on Windows (already installed)
3. App auto-checks for updates on startup
4. Notification appears --> Download --> Restart
5. Verify fix in new version

**Key insight:** For 90% of testing scenarios, UPDATE is the right choice.

---

## INSTALL Flow (Rare!)

1. Uninstall existing app (if any)
2. Run `./scripts/playground_install.sh --launch --auto-login`
3. Wait for first-run setup (Python deps, model)
4. App launches fresh

**Use only when:**
- App is not installed
- Testing first-run experience
- Need completely clean slate
- Debugging installation issues

---

## Root Cause

The confusion arose because:
1. Both operations result in "having the latest version"
2. The mental model was "build completed = need to install"
3. Auto-update capability was underutilized

---

## Resolution

1. Added explicit INSTALL vs UPDATE section to CLAUDE.md
2. Created this documentation file for reference
3. Updated workflow to default to UPDATE unless INSTALL is specifically needed

---

## References

- CLAUDE.md: "INSTALL vs UPDATE (CRITICAL DISTINCTION!)" section
- `./scripts/playground_install.sh` - Installation script
- Auto-updater module in LocaNext Electron app

---

*Documented to prevent future confusion and save time.*
