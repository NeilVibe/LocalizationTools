# Session Context - Claude Handoff Document

**Last Updated:** 2025-12-21 14:30 | **Build:** 315 (PENDING) | **Previous:** 314

---

## CURRENT STATE

### Build 315: CI/CD Cleanup & Fresh Start (PENDING)
- **Problem:** Tags and releases out of sync (7 tags, 20+ releases)
- **Root Cause:** Old cleanup deleted releases but not tags (orphaned)
- **Fix:**
  1. Gitea: Changed MAX_RELEASES from 20 → 10
  2. GitHub: Added cleanup step (was completely missing!)
  3. Nuked all releases/tags on both platforms (fresh start)
  4. Fixed `test_npc.py` - was using read-only property setter
- **Status:** GitHub building, Gitea built `v25.1221.1427`

### CI/CD Discovery: Test Coverage Difference!
| Platform | Test Strategy | Tests Run |
|----------|---------------|-----------|
| **Gitea** | Curated essential list | ~285 tests |
| **GitHub** | All unit/integration/e2e | ~500+ tests |

GitHub caught broken `test_npc.py` that Gitea skipped!

---

## CI/CD ENHANCEMENT IDEA (Future)

### Current State
- **Gitea:** Fast builds (~285 tests, ~5 min)
- **GitHub:** More comprehensive (~500+ tests)

### Proposed Enhancement

| Mode | Tests | Installer | When to Use |
|------|-------|-----------|-------------|
| `Build LIGHT` | ~285 essential | ~150MB | Daily development |
| `Build FULL` | ~285 essential | ~2GB+ | **OFFLINE-READY** release |
| `Build TEST` | ALL (1500+) | None | Pre-release QA |

**`Build FULL` = True Offline Installer:**
- All Python dependencies bundled
- Qwen model (2.3GB) included
- Model2Vec included
- VC++ Redistributable bundled
- Everything runs immediately - ZERO internet needed

**`Build TEST` = Maximum Quality:**
- Run every single test (1500+)
- ~30 min runtime
- Comprehensive coverage before releases

**TODO:**
1. Implement `Build TEST` mode in Gitea workflow
2. Enhance `Build FULL` for true offline capability
3. **P36: CI/CD Test Overhaul** - Reorganize tests into blocks

---

## P36: CI/CD Test Overhaul (NEW)

### Current Test Inventory
- **78 test files**, **1357 test functions**
- Scattered across: unit/, integration/, e2e/, security/, api/, fixtures/

### Proposed: Beautiful Test Blocks
```
tests/blocks/
├── db/           # Database
├── auth/         # Authentication
├── network/      # WebSocket, HTTP
├── security/     # JWT, CORS, XSS
├── processing/   # TM, embeddings, FAISS
├── tools/        # KR Similar, QuickSearch, XLS
├── logging/      # Server/client logs
├── ui/           # API responses
└── performance/  # Latency tests (NEW)
```

### Work Required
1. **Audit** - Review 78 files, find duplicates, map gaps
2. **Reorganize** - Create blocks/, move tests, add markers
3. **Fill Gaps** - Performance tests, error handling
4. **Integrate** - Update CI/CD for `Build TEST`

**Details:** [P36_CICD_TEST_OVERHAUL.md](P36_CICD_TEST_OVERHAUL.md)

---

## WHAT WAS DONE THIS SESSION

### CI/CD Overhaul

| Task | Status |
|------|--------|
| Analyze tags vs releases | DONE |
| Gitea: 20 → 10 releases | DONE |
| GitHub: Add cleanup (was missing!) | DONE |
| Nuke all releases/tags | DONE (42 releases, 14 tags) |
| Fix test_npc.py | DONE |
| Trigger fresh builds | DONE |

### Files Changed

| File | Changes |
|------|---------|
| `.gitea/workflows/build.yml` | MAX_RELEASES 20→10 |
| `.github/workflows/build-electron.yml` | Added cleanup step |
| `tests/unit/test_npc.py` | Fixed: use `_engine` not `model` property |
| `scripts/check_releases_status.sh` | NEW: Check sync status |
| `scripts/cleanup_all_releases_and_tags.sh` | NEW: Nuclear cleanup |

### Current Sync Status
```
Platform   Releases  Tags   Synced?
---------  --------  ----   -------
GitHub     0→1       0→1    Building...
Gitea      1         1      ✅ v25.1221.1427
Local      0         0      ✅ (tags created by CI)
```

---

## PREVIOUS SESSION: Build 314

### UI-047 TM Status Display Fix (VERIFIED)
- **Problem:** TM sidebar showed "Pending" even when database had `status = "ready"`
- **Fix:** Changed `tm.is_indexed` to `tm.status === 'ready'` in FileExplorer.svelte
- **Status:** VERIFIED

---

## KEY PATHS

| What | Path |
|------|------|
| Gitea Workflow | `.gitea/workflows/build.yml` |
| GitHub Workflow | `.github/workflows/build-electron.yml` |
| Release Status Script | `scripts/check_releases_status.sh` |
| Cleanup Script | `scripts/cleanup_all_releases_and_tags.sh` |

---

## NEXT SESSION TODO

1. **Monitor GitHub build** - Should pass now with test fix
2. **Consider `Build TEST` mode** - Comprehensive testing option
3. Ready for new features or bug reports
4. 0 open issues

---

## QUICK COMMANDS

```bash
# Check release/tag sync status
./scripts/check_releases_status.sh

# Nuclear cleanup (if needed)
./scripts/cleanup_all_releases_and_tags.sh --force

# Trigger builds
echo "Build LIGHT" >> GITEA_TRIGGER.txt   # Gitea
echo "Build LIGHT" >> BUILD_TRIGGER.txt   # GitHub
git add -A && git commit -m "Build" && git push origin main && git push gitea main
```

---

*Build 315 pending - CI/CD cleanup complete, fresh start with synced tags/releases*
