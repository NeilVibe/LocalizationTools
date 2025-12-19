# Build & Test Protocol

**Quick Reference for Build → Test Workflow**

---

## The Protocol

### 1. PUSH (triggers build)
```bash
git push origin main && git push gitea main
```

### 2. WAIT (build takes ~12-15 min)
```bash
# Check build status
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" | jq '.[0] | {status, conclusion, created_at}'

# Or watch it
watch -n 30 'curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" | jq ".[0] | {status, conclusion}"'
```

### 3. INSTALL (only after build completes)
```bash
# Downloads latest release and installs to Playground
./scripts/playground_install.sh --launch --auto-login
```

**Full install documentation:** [PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md)

### 4. TEST (via CDP from WSL)
```bash
cd testing_toolkit/cdp
node test_server_status.js
```

---

## Critical Rules

| Rule | Why |
|------|-----|
| **Never refresh app during build** | Old code + new expectations = confusion |
| **Never install mid-build** | Partial/corrupt artifacts |
| **Always verify build success first** | Failed builds = wasted testing |
| **One install per build** | Clean state for testing |

---

## Build Status Check (One-liner)

```bash
curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" 2>/dev/null | jq -r '.[0] | "\(.status) - \(.conclusion // "running") - \(.created_at)"' || echo "Cannot reach Gitea"
```

---

## Workflow During Build

While waiting for build, you CAN:
- Write more code (don't push yet)
- Review docs
- Plan next tasks
- Write CDP test scripts

You CANNOT:
- Test the pushed changes
- Refresh Playground app
- Run `playground_install.sh`

---

## Quick Status Commands

```bash
# Alias for .bashrc
alias buildstatus='curl -s "http://172.28.150.120:3000/api/v1/repos/neilvibe/LocaNext/actions/runs" | jq ".[0] | {status, conclusion}"'
```

---

## Related Docs

| Doc | Purpose |
|-----|---------|
| [PLAYGROUND_INSTALL_PROTOCOL.md](../docs/testing/PLAYGROUND_INSTALL_PROTOCOL.md) | Detailed install process |
| [cdp/README.md](cdp/README.md) | CDP testing guide |
| [README.md](README.md) | Testing toolkit overview |

---

*Protocol added 2025-12-19*
