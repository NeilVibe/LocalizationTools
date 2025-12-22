# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-23 | **Build:** 345 | **Next:** 346

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
| **QA** | ALL 1000+ | ~150MB | Both (default) |
| **QA FULL** | ALL 1000+ | ~2GB | Gitea only (TODO) |
| **TROUBLESHOOT** | Resume | Debug | Both |

---

## QA FULL MODE: IMPLEMENTED

**GITEA ONLY. Never GitHub.** Too complicated + LFS limits.

**Status:** All 5 phases complete. Ready to test.

**WIP Doc:** [QA_FULL_IMPLEMENTATION.md](QA_FULL_IMPLEMENTATION.md)

### What Gets Bundled
| Component | Size |
|-----------|------|
| Qwen model | ~2.3GB |
| Python deps | ~200MB |
| VC++ Redist | ~20MB |
| Base app | ~150MB |

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
- [ ] Build 346 running - testing simplified workflow

---

## KEY DOCS

| Doc | Purpose |
|-----|---------|
| [Roadmap.md](../../Roadmap.md) | Strategic priorities |
| [MASTER_PLAN.md](MASTER_PLAN.md) | What's done & next |
| [ISSUES_TO_FIX.md](ISSUES_TO_FIX.md) | Open bugs (0) |

---

*Clean state. Next: CI/CD QA FULL mode or P25 UX polish.*
