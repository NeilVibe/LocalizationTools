# Gitea Runner Rebuild Kit

**Version:** v15 (NUL Byte Fix) | **Status:** PRODUCTION

This folder contains everything needed to rebuild the patched Gitea Actions runner from source.

---

## Why Patched?

Windows PowerShell writes NUL bytes (`\x00`) to `GITHUB_OUTPUT` files. The stock act_runner crashes with:
- `invalid format '\x00'` errors
- `exec: environment variable contains NUL` errors

Our **v15 patch** strips NUL bytes, fixing the issue.

---

## Quick Rebuild

```bash
# From WSL or Linux
cd runner/scripts
chmod +x build_patched_runner.sh
./build_patched_runner.sh

# Deploy to Windows
cp ~/act_runner_build/act_runner/act_runner_patched_v15.exe \
   /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/

# Restart service (from Windows Admin PowerShell)
Restart-Service GiteaActRunner
```

---

## Files

```
runner/
├── patches/
│   └── v15_nul_byte_fix.patch    # The NUL byte fix (apply to nektos/act)
│
├── scripts/
│   ├── build_patched_runner.sh   # Clones repos, applies patch, builds
│   └── install_windows.ps1       # Windows service setup (NSSM)
│
├── configs/
│   └── config.yaml.template      # Runner config template
│
└── README.md                     # This file
```

---

## Current Production Setup

| Item | Value |
|------|-------|
| Binary | `C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\act_runner_patched_v15.exe` |
| Mode | DAEMON (persistent, picks up jobs continuously) |
| Parameters | `-c config.yaml daemon` |
| Service | GiteaActRunner (via NSSM) |
| Auto-start | Yes (SERVICE_AUTO_START) |

---

## First-Time Registration

Before running the service, register the runner with Gitea:

```powershell
cd C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner

# Generate config (one-time)
.\act_runner_patched_v15.exe generate-config > config.yaml

# Register (get token from Gitea → Settings → Actions → Runners)
.\act_runner_patched_v15.exe register `
    --instance http://YOUR_GITEA_IP:3000 `
    --token YOUR_RUNNER_TOKEN `
    --labels "windows-latest:host,windows:host,self-hosted:host,x64:host" `
    --name "windows-runner"
```

---

## Service Management

```powershell
# Status
Get-Service GiteaActRunner

# Stop/Start/Restart
Stop-Service GiteaActRunner
Start-Service GiteaActRunner
Restart-Service GiteaActRunner

# View logs
Get-EventLog -LogName Application -Source nssm -Newest 20
```

---

## The Patch Explained

**File:** `nektos/act/pkg/container/parse_env_file.go`

**What it does:** After reading each line from GITHUB_OUTPUT, strip any NUL bytes:

```go
// V15-PATCH: Strip NUL bytes from line (Windows PowerShell bug)
line = strings.ReplaceAll(line, "\x00", "")
```

This prevents Go's `os/exec` from rejecting environment variables containing NUL.

---

## Why NSSM?

Windows Services require a `ServiceMain` entry point. `act_runner.exe` is a regular console app - it doesn't have this.

**NSSM** (Non-Sucking Service Manager) wraps any executable as a proper Windows Service:
- Handles start/stop/restart correctly
- Sets working directory properly
- Auto-starts on boot

Install via: `choco install nssm -y`

---

## Related Docs

- [WINDOWS_RUNNER_SETUP.md](../docs/deployment/WINDOWS_RUNNER_SETUP.md) - Full setup guide
- [CI_CD_HUB.md](../docs/cicd/CI_CD_HUB.md) - CI/CD documentation

---

*v15 NUL Byte Fix | Production Ready | 2025-12*
