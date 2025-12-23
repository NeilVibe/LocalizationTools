# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-23 | **Build:** v25.1223.0811 (FULL) | **Latest LIGHT:** v25.1223.0130

---

## CURRENT STATE: ALL GREEN ✅

| Status | Value |
|--------|-------|
| **Open Issues** | 0 |
| **Tests** | 1068 (GitHub) / 1076 (Gitea) |
| **Coverage** | 47% |
| **CI/CD** | Both verified (Build 345) |

---

## BUILD MODE: QA ONLY

**DEV mode is gone.** Workers technology made full test suite so fast that QA is now the only mode.

| Mode | Tests | Installer | Platform |
|------|-------|-----------|----------|
| **QA** | ALL 1000+ | ~170MB | Both (default) |
| **QA FULL** | ALL 1000+ | ~1.2GB | Gitea only ✅ |
| **TROUBLESHOOT** | Resume | Debug | Both |

---

## QA FULL MODE: VERIFIED ✅

**GITEA ONLY. Never GitHub.** Too complicated + LFS limits.

**Status:** Build succeeded - v25.1223.0811 (1,177 MB)

**WIP Doc:** [QA_FULL_IMPLEMENTATION.md](QA_FULL_IMPLEMENTATION.md)

### Actual vs Expected
| Component | Expected | Actual |
|-----------|----------|--------|
| FULL installer | ~2GB | **1,177 MB** |
| LIGHT installer | ~150MB | **170 MB** |

### How to Trigger
```bash
# QA FULL (Gitea only)
echo "Build QA FULL" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build QA FULL" && git push gitea main
```

### Disk Terrorism Prevention
| Build Type | Max Releases | Max Disk |
|------------|--------------|----------|
| **QA FULL** | 3 | ~6GB |
| **QA (LIGHT)** | 10 | ~1.5GB |

Auto-cleanup deletes old releases to prevent disk bloat.

---

## LAST SESSION (2025-12-23)

- [x] Implemented QA FULL mode (offline installer)
- [x] Simplified CI to 3 modes (Build, Build QA FULL, TROUBLESHOOT)
- [x] DEV mode is dead - QA is now default
- [x] Added disk terrorism prevention (FULL: 3 releases, LIGHT: 10)
- [x] GitHub rejects QA FULL (LFS limits)
- [x] App detects bundled model, skips download
- [x] **QA FULL build verified** - v25.1223.0811 (1,177 MB)

---

## FUTURE WORK

| Task | Priority | Notes |
|------|----------|-------|
| **playground_FULL.sh** | Low | Test script for FULL installer (offline mode verification) |

---

## KEY DOCS

| Doc | Purpose |
|-----|---------|
| [Roadmap.md](../../Roadmap.md) | Strategic priorities |
| [MASTER_PLAN.md](MASTER_PLAN.md) | What's done & next |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Open bugs (0) |

---

*QA FULL verified. Future: playground_FULL.sh for offline testing.*
