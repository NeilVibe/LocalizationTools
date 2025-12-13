# Pipeline Architecture

**CI/CD Pipeline Design & Theory**

---

## Pipeline Philosophy

### Official Builds: Full Rebuild

For release builds (`Build LIGHT`, `Build FULL`), every build starts fresh:

```
┌──────────────────────────────────────────────────────────┐
│  ✓ Clean state - no stale artifacts                     │
│  ✓ Reproducible - same input = same output              │
│  ✓ No "works on CI but not locally" bugs                │
│  ✓ Simple to debug - no cache corruption                │
└──────────────────────────────────────────────────────────┘
```

### Troubleshoot Mode: Fast Iteration

For debugging CI failures:

```
┌──────────────────────────────────────────────────────────┐
│  TEST ONLY path/to/test.py   → Run single test file     │
│  TROUBLESHOOT                → Run all, save checkpoint │
│  CONTINUE                    → Resume (same run only)   │
└──────────────────────────────────────────────────────────┘
```

**Note:** CONTINUE only works within the same CI run (checkpoints in /tmp are ephemeral).
Use `TEST ONLY` for fast iteration across multiple runs.

### What We DO Cache

| Cache | Why It's Safe |
|-------|---------------|
| npm packages | Versioned, immutable |
| pip packages | Versioned, immutable |
| Docker layers | Content-addressed |

### What We DON'T Cache

| Don't Cache | Why It's Dangerous |
|-------------|-------------------|
| Test results | False positives possible |
| Build artifacts within job | Stale state |
| Compiled code between runs | Version mismatch |

---

## Job Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE JOBS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ JOB 1: check-build-trigger                              │   │
│  │ ─────────────────────────────                           │   │
│  │ Runner: ubuntu-latest (Linux)                           │   │
│  │ Duration: ~10 seconds                                   │   │
│  │                                                         │   │
│  │ Steps:                                                  │   │
│  │ 1. Checkout code                                        │   │
│  │ 2. Parse GITEA_TRIGGER.txt                             │   │
│  │ 3. AUTO-GENERATE version (YY.MMDD.HHMM in KST)         │   │
│  │ 4. Output: should_build, version, build_type           │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│                            ↓ (if should_build == true)          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ JOB 2: safety-checks                                    │   │
│  │ ───────────────────                                     │   │
│  │ Runner: ubuntu-latest (Linux, host mode)                │   │
│  │ Duration: ~5-15 minutes                                 │   │
│  │                                                         │   │
│  │ Steps:                                                  │   │
│  │ 1. Checkout code                                        │   │
│  │ 2. INJECT VERSION into all files                       │   │
│  │ 3. Install Python + Node dependencies                  │   │
│  │ 4. Run version unification check                       │   │
│  │ 5. Run pytest (900+ tests)                             │   │
│  │ 6. Run pip-audit (security)                            │   │
│  └─────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│                            ↓ (needs: safety-checks)             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ JOB 3: build-windows                                    │   │
│  │ ───────────────────                                     │   │
│  │ Runner: self-hosted (Windows)                           │   │
│  │ Duration: ~10-20 minutes                                │   │
│  │                                                         │   │
│  │ Steps:                                                  │   │
│  │ 1. Checkout code                                        │   │
│  │ 2. INJECT VERSION into all files                       │   │
│  │ 3. Verify Python, Node, Git installations              │   │
│  │ 4. Install dependencies                                 │   │
│  │ 5. Build Svelte frontend                               │   │
│  │ 6. Build Electron app (electron-builder)               │   │
│  │ 7. Create portable ZIP                                  │   │
│  │ 8. Generate latest.yml for auto-updater               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Version Injection Flow

```
BUILD TRIGGER
     │
     ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 1: Generate Version (Job 1 - Linux)                   │
│                                                            │
│ VERSION=$(TZ='Asia/Seoul' date '+%y.%m%d.%H%M')           │
│ Example: 25.1213.1640                                      │
└────────────────────────────────────────────────────────────┘
     │
     ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 2: Inject Version (Job 2 & 3)                         │
│                                                            │
│ Files updated:                                             │
│ ├── version.py:     VERSION = "25.1213.1640"              │
│ ├── package.json:   "version": "25.1213.1640"             │
│ ├── *.iss:          #define MyAppVersion "25.1213.1640"   │
│                                                            │
│ Method:                                                    │
│ - Linux: sed -i "s/VERSION = .*/VERSION = \"$V\"/"        │
│ - Windows: PowerShell -replace                             │
└────────────────────────────────────────────────────────────┘
     │
     ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 3: Validate (Job 2)                                   │
│                                                            │
│ python3 scripts/check_version_unified.py                   │
│                                                            │
│ CRITICAL files must match (blocks build):                  │
│ ├── version.py                                             │
│ ├── server/config.py                                       │
│ ├── package.json                                           │
│ └── installer/*.iss                                        │
│                                                            │
│ INFORMATIONAL files (warn only):                           │
│ ├── README.md                                              │
│ ├── CLAUDE.md                                              │
│ └── Roadmap.md                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Runner Configuration

### Linux Runner (Host Mode)

```yaml
runs-on: ubuntu-latest
# Actually runs on WSL2 Linux in host mode
# Uses system Python 3.11, Node, PostgreSQL directly
```

**Why host mode?**
- Faster startup (no container overhead)
- Direct access to host PostgreSQL
- Simpler dependency management

### Windows Runner (Self-Hosted)

```yaml
runs-on: self-hosted
# Runs on local Windows machine
# Pre-installed: Python 3.13, Node 20, Git
```

**Why self-hosted?**
- Gitea doesn't have Windows cloud runners
- electron-builder requires Windows for NSIS
- Code signing needs Windows environment

---

## Dependency Strategy

### Job Dependencies

```
check-build-trigger
        ↓
        ↓ outputs: version, should_build
        ↓
safety-checks (needs: check-build-trigger)
        ↓
        ↓ if: success
        ↓
build-windows (needs: safety-checks)
```

### Why This Order?

1. **check-build-trigger first** - Fast, decides if we should continue
2. **safety-checks second** - Catch bugs before expensive Windows build
3. **build-windows last** - Only runs if tests pass

---

## Failure Recovery

### Re-running Jobs

Gitea/GitHub support "Re-run failed jobs only":
- If `safety-checks` fails → Fix code → Re-run just that job
- If `build-windows` fails → Re-run without re-running tests

### When to Full Rebuild

- Version injection issues
- Cache corruption suspected
- Dependency version changes

---

*Last updated: 2025-12-13*
