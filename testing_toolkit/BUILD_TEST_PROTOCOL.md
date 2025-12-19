# Build → Install → Test Protocol

**Complete workflow from code push to test execution**

**Updated:** 2025-12-19 | **Build:** 301

---

## Full Protocol Flow

```
PUSH → WAIT → CHECK → INSTALL → LAUNCH → TEST
```

| Step | Action | Time |
|------|--------|------|
| 1. PUSH | Trigger build | Instant |
| 2. WAIT | Build compiles | ~12-15 min |
| 3. CHECK | Verify release exists | 10 sec |
| 4. INSTALL | Download + install to Playground | ~2 min |
| 5. LAUNCH | Start app with CDP | ~30 sec |
| 6. TEST | Run Node.js CDP tests | ~1 min |

---

## Step 1: PUSH (Trigger Build)

```bash
# From WSL
git push origin main && git push gitea main
```

Build starts automatically on Gitea CI.

---

## Step 2: WAIT (Build Running)

**DO NOT** refresh app or install during build.

Check status:
```bash
# One-liner status check
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" 2>/dev/null | jq -r '.[0] | "\(.status) - \(.conclusion // "running")"'

# Watch mode
watch -n 30 'curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" | jq ".[0] | {status, conclusion}"'
```

Expected: `completed - success`

---

## Step 3: CHECK (Verify Release)

```bash
# Get latest release tag
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/releases?limit=1" | jq -r '.[0].tag_name'
```

Expected: New version tag (e.g., `v25.1219.1118`)

---

## Step 4 & 5: INSTALL + LAUNCH

### Option A: WSL Script (when interop works)

```bash
./scripts/playground_install.sh --launch --auto-login
```

### Option B: Windows CMD (when WSL interop broken)

Run these in **Windows CMD or PowerShell**:

```cmd
REM Kill existing
taskkill /F /IM LocaNext.exe /T 2>nul

REM Run install script
cd C:\path\to\LocalizationTools
powershell -ExecutionPolicy Bypass -File scripts\playground_install.ps1 -LaunchAfterInstall -EnableCDP

REM Or manual install:
REM 1. Download latest from http://172.28.150.120:3000/neilvibe/LocaNext/releases
REM 2. Run installer: LocaNext_v*.exe /S /D=C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
REM 3. Launch: LocaNext.exe --remote-debugging-port=9222
```

### Option C: Just Launch (if already installed)

**Windows:**
```cmd
cd C:\NEIL_PROJECTS_WINDOWSBUILD\LocaNextProject\Playground\LocaNext
LocaNext.exe --remote-debugging-port=9222
```

**WSL (when interop works):**
```bash
/mnt/c/NEIL_PROJECTS_WINDOWSBUILD/LocaNextProject/Playground/LocaNext/LocaNext.exe --remote-debugging-port=9222 &
```

---

## Step 6: TEST (Node.js CDP)

**From WSL** (ports are shared with Windows):

```bash
# Wait for CDP to be ready
sleep 30

# Verify CDP responding
curl -s http://127.0.0.1:9222/json | jq '.[0].url'

# Run tests
cd /home/neil1988/LocalizationTools/testing_toolkit/cdp
node quick_check.js           # Basic page check
node test_server_status.js    # Server/backend status
node test_bug029.js           # Upload as TM test
```

---

## Critical Rules

| Rule | Why |
|------|-----|
| **Never install during build** | Partial artifacts cause errors |
| **Always verify release first** | Avoid testing old code |
| **Wait 30s after launch** | App needs startup time |
| **Use Node.js from WSL** | Ports shared, Node.js works |

---

## WSL Interop Status

WSL can execute Windows binaries when interop is enabled. Sometimes it breaks.

**Check:**
```bash
/mnt/c/Windows/System32/cmd.exe /c "echo test"
```

**If broken:**
- Run install/launch commands directly from Windows CMD
- Node.js CDP tests still work from WSL (ports are shared)

---

## Quick Reference

```bash
# Full flow (when everything works)
git push origin main && git push gitea main
# Wait 12-15 min...
./scripts/playground_install.sh --launch
sleep 30
cd testing_toolkit/cdp && node test_server_status.js
```

---

## Related Docs

| Doc | Purpose |
|-----|---------|
| [PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed install options |
| [cdp/README.md](cdp/README.md) | Node.js CDP testing guide |
| [README.md](README.md) | Testing toolkit overview |

---

*Protocol: Push → Wait → Check → Install → Launch → Test*
