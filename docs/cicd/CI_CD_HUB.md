# CI/CD Hub

**LocaNext Continuous Integration & Deployment**

---

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **CI/CD Primary** | Gitea Actions | Self-hosted, Linux runner (host mode) |
| **CI/CD Secondary** | GitHub Actions | Cloud, Windows runner |
| **Installer Builder** | electron-builder 26.x | Native NSIS support |
| **Installer Format** | NSIS (Nullsoft) | Replaced Inno Setup in P28 |
| **Build Output** | `LocaNext_v*.exe` | ~200MB Light, ~2GB Full |

---

## Quick Reference

| Need | Go To |
|------|-------|
| Build now? | [HOW_TO_BUILD.md](HOW_TO_BUILD.md) |
| Build failed? | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Pipeline details? | [PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md) |
| Version format? | [VERSION_SYSTEM.md](VERSION_SYSTEM.md) |
| **Runner services?** | [RUNNER_SERVICE_SETUP.md](RUNNER_SERVICE_SETUP.md) |
| **CPU issues?** | [../troubleshooting/GITEA_SAFETY_PROTOCOL.md](../troubleshooting/GITEA_SAFETY_PROTOCOL.md) |

---

## Build Modes

**DEV mode is DEAD.** Workers technology made full test suite so fast that QA is now the only mode.

| Mode | Trigger | Platform | Description |
|------|---------|----------|-------------|
| **QA** | `Build QA` or `Build` | Both | ALL 1000+ tests + light installer (~150MB) |
| **QA FULL** | `Build QA FULL` | Gitea only | ALL 1000+ tests + offline installer (~2GB) [TODO] |
| **TROUBLESHOOT** | `TROUBLESHOOT` | Both | Smart checkpoint mode |

### Why QA Only?

| Before | After |
|--------|-------|
| DEV mode skipped tests | No more DEV mode |
| "Tests too slow" | Workers = fast |
| Risk of shipping untested code | ALL tests, every build |

---

## QA FULL Implementation Plan (TODO)

**GITEA ONLY. Never GitHub.** Too complicated + LFS bandwidth limits.

**Goal:** True offline installer (~2GB) for deployments with no internet.

### What Gets Bundled

| Component | Size | Notes |
|-----------|------|-------|
| Qwen model | ~2.3GB | `Qwen/Qwen2.5-0.5B-Instruct` |
| Python deps | ~200MB | All pip packages pre-installed |
| VC++ Redist | ~20MB | Visual C++ runtime |
| Base app | ~150MB | Same as QA |

### Implementation Steps

1. **Detect mode in CI**
   - Parse `Build QA FULL` from trigger file
   - Set `FULL_MODE=true` environment variable

2. **Download Qwen model during build**
   - Use `huggingface-hub` to download model
   - Cache in `models/qwen/` directory
   - Include in installer

3. **Bundle VC++ Redistributable**
   - Download `vc_redist.x64.exe`
   - Include in installer, run silently on install

4. **Skip model download on user PC**
   - If model exists locally, skip HuggingFace download
   - Detect via `models/qwen/config.json` presence

5. **Update NSIS installer script**
   - Add model files to installer
   - Add VC++ silent install step

### Platform Restriction

- **Gitea only** - GitHub has LFS bandwidth limits
- Add check in GitHub workflow to reject QA FULL triggers

---

## TROUBLESHOOT Mode

Smart checkpoint that **persists across CI runs**:

```
1. Trigger: TROUBLESHOOT
   ↓
2. No checkpoint? → Run all tests
   Checkpoint exists? → Run that test first
   ↓
3. Test fails? → Save checkpoint, exit
   ↓
4. Fix code, push, trigger TROUBLESHOOT again
   ↓
5. Repeat until all pass
   ↓
6. Do Build QA for official release
```

**Checkpoint location:** `/home/neil1988/.locanext_checkpoint`

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LOCANEXT CI/CD PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TRIGGER: Push to main with trigger in GITEA_TRIGGER.txt           │
│                          ↓                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 1: check-build-trigger (Linux)                          │   │
│  │ - Parse GITEA_TRIGGER.txt                                   │   │
│  │ - AUTO-GENERATE version: YY.MMDD.HHMM                       │   │
│  │ - Detect mode: OFFICIAL or TROUBLESHOOT                     │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 2: safety-checks (Linux)                                │   │
│  │ - Inject version into all files                             │   │
│  │ - Run pytest (900+ tests)                                   │   │
│  │ - TROUBLESHOOT: Save checkpoint on failure                  │   │
│  │ - Security audit                                            │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             ↓ (if mode=official)                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ JOB 3: build-windows (Windows self-hosted)                  │   │
│  │ - Build Electron app with electron-builder                  │   │
│  │ - Create NSIS installer (.exe)                              │   │
│  │ - Generate latest.yml for auto-updater                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Version System

**Unified Format:** `YY.MMDD.HHMM` (e.g., `25.1213.1540`)

- Valid semver (25.1213.1540 = X.Y.Z)
- Human readable (Dec 13, 2025, 15:40 KST)
- Auto-generated by pipeline
- Injected into all files automatically

---

## Quick Start

```bash
# QA build (default - all tests)
echo "Build QA" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build" && git push origin main && git push gitea main

# Troubleshoot mode
echo "TROUBLESHOOT" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Troubleshoot" && git push origin main && git push gitea main
```

---

## Log Locations

```bash
# Find latest build logs
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/ | head -5

# Check for errors
cat ~/gitea/data/actions_log/neilvibe/LocaNext/<folder>/*.log | grep -E "FAILED|error"

# Check checkpoint
cat ~/.locanext_checkpoint
```

---

## Windows CI Testing (Build 879+)

**Full 3-tier Windows testing with CDP integration.**

### Test Pipeline

```
Windows CI Pipeline:
├── Tier 1: pytest (62 tests in windows_tests/)
│   └── Paths, encoding, Excel, models, server connectivity
├── Tier 2: Smoke Test
│   └── Silent NSIS install + file verification + health check
└── Tier 3: CDP Integration Tests
    ├── TEST 1: SQLite (offline) mode
    │   └── Launch app → quick_check.js
    └── TEST 2: PostgreSQL (online) mode
        └── Launch app → login.js → quick_check.js → test_server_status.js
```

### Gitea Secrets (REQUIRED for Online Tests)

| Secret | Purpose | Value |
|--------|---------|-------|
| `CI_DB_HOST` | PostgreSQL server address | `172.28.150.120` |
| `CI_TEST_USER` | Test user (role=user, NOT admin) | `ci_tester` |
| `CI_TEST_PASS` | Test user password | (encrypted in Gitea) |

**To configure:** Gitea repo → Settings → Secrets → Add

**SECURITY:** Uses `ci_tester` with limited `user` role, NOT super admin.

### pytest Tests (windows_tests/)

| File | Count | What It Tests |
|------|-------|---------------|
| `test_windows_paths.py` | 15 | AppData, UserProfile, Downloads |
| `test_windows_server.py` | 12 | Server, DB, socket connectivity |
| `test_windows_encoding.py` | 14 | UTF-8, BOM, Korean |
| `test_windows_excel.py` | 11 | openpyxl, Korean, large files |
| `test_windows_models.py` | 10 | PKL, FAISS, numpy |

### CDP Tests (testing_toolkit/cdp/)

| Script | Mode | What It Does |
|--------|------|--------------|
| `quick_check.js` | Both | Page state, URL, DOM verification |
| `login.js` | Online | Login with env credentials |
| `test_server_status.js` | Online | Server panel, DB connection |

### Environment Variables

```yaml
# Passed from Gitea secrets to CDP scripts
CDP_TEST_USER: ${{ secrets.CI_TEST_USER }}
CDP_TEST_PASS: ${{ secrets.CI_TEST_PASS }}
```

### CI Fix History

| Build | Fix |
|-------|-----|
| 852-855 | PowerShell syntax fixes |
| 858-874 | conftest.py isolation → moved to windows_tests/ |
| 877 | CI edge cases (SYSTEM user, socket errors) |
| 878 | Added basic CDP tests (SQLite only) |
| 879 | Dual-mode CDP tests (SQLite + PostgreSQL) |
| 880 | Security: Removed neil/neil fallback, require env credentials |

---

*Last updated: 2025-12-25*
