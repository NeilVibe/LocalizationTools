# First-Launch Setup Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken synchronous PG auto-setup with a step-by-step setup wizard that shows real-time progress on the splash screen, handles failures gracefully, and never calls the internet.

**Architecture:** Python `server/setup/` module with 7 idempotent step functions, a sequential runner with progress callbacks, and a state file for crash recovery. Electron parses JSONL from Python stdout to update the splash screen. Setup runs BEFORE FastAPI starts. On failure, falls back to SQLite mode.

**Tech Stack:** Python 3.11 (subprocess, cryptography, dataclasses), Electron (IPC, splash window), PostgreSQL 15.12 portable

**Spec:** `docs/superpowers/specs/2026-04-01-first-launch-setup-wizard-design.md`

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `server/setup/__init__.py` | Data models: StepResult, SetupResult, SetupConfig |
| `server/setup/state.py` | setup_state.json read/write/resume |
| `server/setup/network.py` | LAN IP detection (no internet) |
| `server/setup/credential_store.py` | Config save with NTFS ACLs |
| `server/setup/pg_lifecycle.py` | pg_ctl start/stop/status, find binaries, run_sql |
| `server/setup/steps.py` | 7 step functions (preflight + 6 setup) |
| `server/setup/runner.py` | Sequential orchestrator with progress callbacks |
| `server/setup/jsonl.py` | JSONL stdout emitter for Electron |
| `tests/unit/setup/test_state.py` | State file tests |
| `tests/unit/setup/test_network.py` | LAN IP tests (verifies no internet calls) |
| `tests/unit/setup/test_credential_store.py` | Config save/load tests |
| `tests/unit/setup/test_pg_lifecycle.py` | PG lifecycle tests |
| `tests/unit/setup/test_steps.py` | Step function tests |
| `tests/unit/setup/test_runner.py` | Runner orchestration tests |

### Modified files
| File | Change |
|------|--------|
| `server/main.py` | Delete lines 830-950 (old setup blob). Replace with setup module call + JSONL. |
| `server/api/server_config.py` | Delete lines 278-566 (old setup endpoint). Replace with call to shared module. |
| `locaNext/electron/splash.js` | Add setup mode: step list, progress, error panel, retry/offline buttons. |
| `locaNext/electron/main.js` | JSONL parser, setup message routing, pg_ctl stop on exit, single-instance lock. |
| `server/utils/auth.py` | Add admin token validation (IP + token, not just IP). |
| `.github/workflows/build-electron.yml` | Add `cryptography` to pip install. |

---

## Wave 1: Python Setup Module (Tasks 1-6)

Pure Python, no Electron changes. Testable independently.

---

### Task 1: Data Models + State File

**Files:**
- Create: `server/setup/__init__.py`
- Create: `server/setup/state.py`
- Create: `tests/unit/setup/__init__.py`
- Create: `tests/unit/setup/test_state.py`

- [ ] **Step 1: Write state tests**

See spec Section 5 for SetupState schema. Tests cover: read missing file, roundtrip write/read, get_first_incomplete_step (all done, partial, failed step), valid JSON output.

- [ ] **Step 2: Run tests — verify they fail (ModuleNotFoundError)**

Run: `python -m pytest tests/unit/setup/test_state.py -v`

- [ ] **Step 3: Create `server/setup/__init__.py` with StepResult, SetupResult, SetupConfig dataclasses**

- [ ] **Step 4: Create `server/setup/state.py` with SetupState, read_state, write_state, mark_step_done, mark_step_failed, get_first_incomplete_step, is_setup_complete, STEP_NAMES**

- [ ] **Step 5: Run tests — all pass**

- [ ] **Step 6: Commit**
```
feat(setup): data models + state file with crash recovery
```

---

### Task 2: LAN IP Detection + Credential Store

**Files:**
- Create: `server/setup/network.py`
- Create: `server/setup/credential_store.py`
- Create: `tests/unit/setup/test_network.py`
- Create: `tests/unit/setup/test_credential_store.py`

- [ ] **Step 1: Write network tests — including test_detect_lan_ip_no_internet_call that monkeypatches socket.connect to flag any external IP**

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Create `network.py` — detect_lan_ip() using socket.gethostname()+getaddrinfo, fallback to broadcast 255.255.255.255, final fallback 127.0.0.1. ZERO external connections. Also get_subnet() helper.**

- [ ] **Step 4: Write credential store tests — save/load roundtrip, missing file, parent dir creation**

- [ ] **Step 5: Create `credential_store.py` — save_config (JSON + icacls on Windows, chmod on Linux), load_config**

- [ ] **Step 6: Run all tests — pass**

- [ ] **Step 7: Commit**
```
feat(setup): LAN IP detection (no internet) + credential store
```

---

### Task 3: PG Lifecycle (start/stop/status)

**Files:**
- Create: `server/setup/pg_lifecycle.py`
- Create: `tests/unit/setup/test_pg_lifecycle.py`

- [ ] **Step 1: Write lifecycle tests — find_pg_binaries (missing, found), PgPaths data_dir, is_pg_running mock**

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Create `pg_lifecycle.py` — PgPaths dataclass, find_pg_binaries, _make_env (PATH + lib for DLL), is_pg_running (pg_isready), start_pg (pg_ctl start -w), stop_pg (pg_ctl stop -m fast), run_sql (psql with PGPASSWORD env var, never CLI arg)**

- [ ] **Step 4: Run tests — pass**

- [ ] **Step 5: Commit**
```
feat(setup): PG lifecycle — find, start, stop, run_sql
```

---

### Task 4: Setup Steps (7 step functions)

**Files:**
- Create: `server/setup/steps.py`
- Create: `tests/unit/setup/test_steps.py`

- [ ] **Step 1: Write step tests — port conflict detection, missing binaries, skip-if-initialized, cleanup-on-failure, skip-if-marker-exists, skip-if-certs-exist**

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Create `steps.py` with all 7 functions. Each follows PRE-CHECK/RUN/VERIFY/CLEANUP pattern:**

| Step | Function | Pre-check | Cleanup on failure |
|------|----------|-----------|-------------------|
| 0 | step_preflight_checks | Always runs | N/A |
| 1 | step_init_database | PG_VERSION exists+valid | Delete partial pg_data/ |
| 2 | step_configure_access | pg_hba.conf has marker | Restore backup |
| 3 | step_start_database | pg_isready returns 0 | pg_ctl stop |
| 4 | step_create_account | Role exists in pg_roles | N/A (transactional) |
| 5 | step_create_database | DB exists in pg_database | DROP DATABASE |
| 6 | step_generate_certificates | server.crt+key exist | Delete partial files |

Step 6 uses Python `cryptography` library (not openssl CLI). See spec Section 9 for cert generation code.

- [ ] **Step 4: Run tests — pass**

- [ ] **Step 5: Commit**
```
feat(setup): 7 idempotent step functions with PRE-CHECK/RUN/VERIFY/CLEANUP
```

---

### Task 5: Setup Runner (orchestrator)

**Files:**
- Create: `server/setup/runner.py`
- Create: `tests/unit/setup/test_runner.py`

- [ ] **Step 1: Write runner tests — all steps called, stops on fatal failure, resumes from state file**

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Create `runner.py` — run_setup(config, state_path, on_progress) function. Reads state, skips completed steps, runs remaining. Fatal steps stop execution. Recoverable steps auto-retry once. Optional steps (certs) continue on failure. Writes state after each step.**

Step classification:
- FATAL: preflight_checks, init_database, configure_access, start_database
- RECOVERABLE (auto-retry once): create_account, create_database
- OPTIONAL (skip on failure): generate_certificates

- [ ] **Step 4: Run all setup tests**

Run: `python -m pytest tests/unit/setup/ -v`

- [ ] **Step 5: Commit**
```
feat(setup): sequential runner with state resume, retry, and progress callbacks
```

---

### Task 6: JSONL Emitter + Wire into main.py

**Files:**
- Create: `server/setup/jsonl.py`
- Modify: `server/main.py`

- [ ] **Step 1: Create `jsonl.py` — emit_jsonl, emit_setup_started, emit_setup_step, emit_setup_complete, emit_pg_starting, emit_pg_ready, emit_server_ready. All write JSON + newline to stdout and flush.**

See spec Section 6 for exact JSONL message format.

- [ ] **Step 2: Delete old auto-setup blob from main.py (lines 830-950) and replace with new setup flow:**

```
if __name__ == "__main__":
    1. find_pg_binaries()
    2. read_state()
    3. if not complete: emit_setup_started → run_setup(on_progress=emit_step) → emit_setup_complete → save credentials
    4. if complete: emit_pg_starting → start_pg → emit_pg_ready
    5. uvicorn.run()
```

- [ ] **Step 3: Run existing tests — no regressions**

Run: `python -m pytest tests/ -x --timeout=30 -q`

- [ ] **Step 4: Commit**
```
feat(setup): JSONL emitter + wire setup into main.py startup (replaces old blob)
```

---

## Wave 2: Electron Integration (Tasks 7-9)

---

### Task 7: Splash Screen Setup Mode

**Files:**
- Modify: `locaNext/electron/splash.js`

- [ ] **Step 1: Add setup mode to splash.js**

New exports: showSetupMode(totalSteps), updateSetupStep(index, step, status, durationMs, error), showSetupError(step, errorCode, errorDetail), showSetupComplete(lanIp).

Setup mode HTML (inline data URL, same pattern as existing splash):
- Title: "LocaNext - Server Setup"
- Step list with icons: circle (pending), spinner (running), checkmark (done), X (failed)
- Progress bar: "Step N of 7"
- Error panel (hidden until failure): error message + [Show Full Log] [Retry] [Start Offline] buttons
- Complete panel: "Server ready! LAN IP: xxx.xxx.xxx.xxx"

IPC for retry/offline buttons:
- Retry sends `setup-retry` event to main process
- Start Offline sends `setup-offline` event to main process

Splash should NOT be alwaysOnTop during start_database step (Windows Firewall popup may appear behind it).

- [ ] **Step 2: Commit**
```
feat(electron): splash screen setup mode with step progress and error panel
```

---

### Task 8: main.js JSONL Parsing + PG Stop + Single Instance

**Files:**
- Modify: `locaNext/electron/main.js`

- [ ] **Step 1: Replace stdout handler with JSONL-aware parser**

Buffer partial lines. Lines starting with `{` → try JSON.parse → handleSetupMessage(). Other lines → log file.

- [ ] **Step 2: Add handleSetupMessage() function**

Routes message types to splash functions:
- setup_started → showSetupMode()
- setup_step → updateSetupStep()
- setup_complete → showSetupComplete() or showSetupError()
- pg_starting → updateSplash("Starting database...")
- pg_ready → updateSplash("Starting server...")
- server_ready → (waitForServer will detect /health)

- [ ] **Step 3: Add pg_ctl stop to stopBackendServer()**

BEFORE killing Python process, stop PostgreSQL:
- Use `execFileSync` (safe, list-form, no shell) to call pg_ctl stop -D data_dir -m fast
- 10 second timeout
- Catch errors (PG may not have been running)

- [ ] **Step 4: Add single-instance lock**

Early in file: `app.requestSingleInstanceLock()`. If no lock, quit.

- [ ] **Step 5: Handle IPC from splash retry/offline buttons**

- setup-retry → kill backend, restart with setup
- setup-offline → let backend continue in SQLite mode

- [ ] **Step 6: Commit**
```
feat(electron): JSONL parsing, setup routing, pg_ctl stop, single instance lock
```

---

### Task 9: Build Pipeline + Admin Auth + Old Code Cleanup

**Files:**
- Modify: `.github/workflows/build-electron.yml`
- Modify: `server/utils/auth.py`
- Modify: `server/api/server_config.py`

- [ ] **Step 1: Add `cryptography` to pip install in build-electron.yml (line ~649)**

- [ ] **Step 2: Add validate_admin_token() to server/utils/auth.py**

Checks BOTH: IP is localhost AND Bearer token matches admin_token from config.
Uses `secrets.compare_digest()` for timing-safe comparison.

- [ ] **Step 3: Replace server_config.py setup endpoint**

Delete old `run_server_setup()` body (lines 278-566). Replace with `/setup/retry` endpoint that calls the shared `run_setup()` from `server/setup/runner.py`. Requires admin token. Returns step-by-step results.

- [ ] **Step 4: Verify no 8.8.8.8 references remain**

Run: `grep -r "8.8.8.8" server/`
Expected: No matches

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ --timeout=60 -q`

- [ ] **Step 6: Commit**
```
feat: cryptography in CI, admin token auth, setup retry endpoint, remove 8.8.8.8
```

---

## Execution Summary

| Wave | Tasks | Focus | Dependencies |
|------|-------|-------|-------------|
| **Wave 1** | 1-6 | Python setup module | None — pure Python, testable alone |
| **Wave 2** | 7-9 | Electron + CI + cleanup | Depends on Wave 1 (JSONL protocol) |

**Wave 1 tasks are independent of each other** (Tasks 1-5 build modules, Task 6 wires them together). Tasks 1-5 can be parallelized with agent teams.

**Wave 2 tasks are sequential** (splash depends on message format, main.js depends on splash API, cleanup depends on everything).

**Total: 9 tasks, ~40 steps, 8 new Python files, 6 new test files, 5 modified files, 2 deleted code blocks.**
