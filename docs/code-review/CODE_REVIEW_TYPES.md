# Code Review Types

**Created:** 2025-12-15 | **Lesson:** Different systems need different reviews

---

## Why Multiple Review Types?

The Gitea CPU incident (706% CPU, 506 restarts) was NOT caught by CI/CD Code Review because:
- CI/CD Code Review checks **workflow files** (.yml)
- The bug was in **systemd service configuration** (infrastructure)
- Different domain = different review

---

## Review Types

### 1. CI/CD Code Review

**Scope:** Workflow files only

| Check | Files |
|-------|-------|
| Job dependencies | `.gitea/workflows/*.yml` |
| Version passing | `.github/workflows/*.yml` |
| Caching logic | |
| Artifact handling | |
| Build commands | |

**Does NOT check:** Runner services, systemd, auto-start configs

---

### 2. CI/CD Infrastructure Review

**Scope:** Everything OUTSIDE workflow files that affects CI/CD

| Check | Location |
|-------|----------|
| systemd services | `/etc/systemd/system/gitea*.service` |
| Auto-start configs | `Restart=always` is DANGEROUS |
| Runner registration | Multiple runners = multiple polling |
| Polling intervals | Default 2s is too aggressive |
| Service dependencies | Runner shouldn't start without Gitea |

**Commands:**
```bash
# Check for dangerous auto-restart
grep -r "Restart=always" /etc/systemd/system/

# Check registered runners
systemctl list-units | grep -i runner

# Check polling
grep -i "interval\|poll" ~/gitea/*.yaml
```

---

### 3. Electron Runtime Review

**Scope:** Desktop app code that runs AFTER build

| Check | Files |
|-------|-------|
| Path resolution (dev vs prod) | `electron/main.js` |
| extraResources paths | `package.json` |
| First-run setup | `electron/first-run-setup.js` |
| Error handling | `electron/repair.js` |
| IPC handlers | `electron/preload.js` |

**Key question:** "Does this work in PACKAGED app, not just dev?"

---

### 4. Installer UX Review

**Scope:** User experience during installation

| Check | Location |
|-------|----------|
| Progress display | NSIS config, `installer-ui.nsh` |
| Error dialogs | Setup window HTML |
| Exit options | Closable on error? |
| Silent install flags | `/S /D=path` |

---

## Review Checklist by Phase

### Before Build
- [ ] CI/CD Code Review (workflow files)
- [ ] CI/CD Infrastructure Review (services, runners)

### After Build, Before Release
- [ ] Electron Runtime Review (packaged app paths)
- [ ] Installer UX Review (install experience)

### After Incident
- [ ] Root cause analysis
- [ ] Which review would have caught it?
- [ ] Update that review's checklist

---

## Incidents & Lessons

| Date | Incident | Root Cause | Missed By | Now Covered By |
|------|----------|------------|-----------|----------------|
| 2025-12-14 | Path bug (ENOENT) | Wrong path in prod | CI/CD Code Review | Electron Runtime Review |
| 2025-12-14 | 706% CPU | systemd Restart=always | CI/CD Code Review | CI/CD Infrastructure Review |

---

## Quick Reference

```
CI/CD Code Review         → workflow .yml files
CI/CD Infrastructure Review → systemd, runners, services
Electron Runtime Review   → desktop app in prod mode
Installer UX Review       → user install experience
```

---

*Created after 706% CPU incident that nearly killed the user's computer.*
