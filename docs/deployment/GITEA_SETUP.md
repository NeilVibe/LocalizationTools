# Gitea & Git Self-Hosted Setup Guide

**Priority 13 - Patch Server | License: MIT (Company Safe)**

---

## Quick Answer: SSH vs HTTPS?

```
ACCESS METHODS:
│
├── 🔐 SSH (RECOMMENDED for company)
│   ├── How: ssh://USERNAME@server:2222/repo.git
│   ├── Auth: SSH keys (no passwords)
│   ├── Security: Encrypted, key-based
│   ├── Firewall: Port 2222 (Gitea default)
│   └── Setup: One-time key generation
│
├── 🌐 HTTPS
│   ├── How: https://server/repo.git
│   ├── Auth: Username + password (or token)
│   ├── Security: TLS encrypted
│   ├── Firewall: Port 443
│   └── Setup: Needs TLS certificate
│
└── 🏆 WINNER: SSH
    └── No passwords, no certificates, just keys
```

### ⚠️ CRITICAL: Gitea SSH Username Bug

**Gitea's built-in SSH server does NOT use `git` as username!**

It uses your **Linux system username** (from `RUN_USER` in app.ini).

```bash
# WRONG (common mistake):
ssh -T git@gitea-server          # ❌ Permission denied

# CORRECT:
ssh -T your_linux_user@gitea-server   # ✅ Works!
```

Check Gitea logs for this error:
```
Invalid SSH username git - must use USERNAME for all git operations via ssh
```

---

## Part 1: Git Basics (No Server Needed)

### Install Git
```bash
# Linux
sudo apt install git

# Windows (Git Bash)
# Download from https://git-scm.com/download/win
```

### Configure Git
```bash
git config --global user.name "Your Name"
git config --global user.email "you@company.com"
```

### Basic Commands
```bash
git init                    # Create new repo
git clone <url>             # Copy existing repo
git add .                   # Stage all changes
git commit -m "message"     # Save changes
git push origin main        # Upload to server
git pull origin main        # Download from server
git branch feature-x        # Create branch
git checkout feature-x      # Switch branch
git merge feature-x         # Merge branch
git log --oneline           # View history
```

---

## Part 2: SSH Key Setup

### Generate SSH Key (One-Time Per Developer)
```bash
# Generate key pair
ssh-keygen -t ed25519 -C "you@company.com"
# Press Enter for default location (~/.ssh/id_ed25519)
# Optional: Add passphrase for extra security

# Your keys:
# ~/.ssh/id_ed25519      ← Private (NEVER share!)
# ~/.ssh/id_ed25519.pub  ← Public (give to server)
```

### View Your Public Key
```bash
cat ~/.ssh/id_ed25519.pub
# Output: ssh-ed25519 AAAAC3Nz... you@company.com
```

### Test SSH Connection
```bash
ssh -T git@your-gitea-server
# Expected: Hi username! You've successfully authenticated...
```

---

## Part 3: Gitea Server Setup

### Option A: Quick Install (Single Binary)
```bash
# Download Gitea
wget -O gitea https://dl.gitea.com/gitea/1.21/gitea-1.21-linux-amd64
chmod +x gitea

# Create directories
sudo mkdir -p /var/lib/gitea/{custom,data,log}
sudo mkdir -p /etc/gitea
sudo chown -R $USER:$USER /var/lib/gitea /etc/gitea

# Run Gitea
./gitea web
# Open: http://your-server:3000
# Complete setup wizard
```

### Option B: Systemd Service (Production)
```bash
# Create service file
sudo nano /etc/systemd/system/gitea.service
```

```ini
[Unit]
Description=Gitea
After=network.target

[Service]
Type=simple
User=git
Group=git
WorkingDirectory=/var/lib/gitea
ExecStart=/usr/local/bin/gitea web -c /etc/gitea/app.ini
Restart=always
Environment=USER=git HOME=/home/git

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable gitea
sudo systemctl start gitea
sudo systemctl status gitea
```

### Option C: Docker (Easiest Production)
```yaml
# docker-compose.yml
version: "3"
services:
  gitea:
    image: gitea/gitea:latest
    ports:
      - "3000:3000"  # Web UI
      - "2222:22"    # SSH
    volumes:
      - ./gitea-data:/data
    restart: always
```

```bash
docker-compose up -d
```

---

## Part 4: Add Your SSH Key to Gitea

1. Open Gitea: `http://your-server:3000`
2. Login → Settings → SSH/GPG Keys
3. Click "Add Key"
4. Paste your public key (`cat ~/.ssh/id_ed25519.pub`)
5. Save

### Clone via SSH
```bash
git clone ssh://git@your-server:2222/username/locanext.git
# or if using port 22:
git clone git@your-server:username/locanext.git
```

---

## Part 5: Gitea Actions (CI/CD Pipeline)

### Enable Actions (One-Time)
Edit `/etc/gitea/app.ini`:
```ini
[actions]
ENABLED = true
```

Restart Gitea:
```bash
sudo systemctl restart gitea
```

### 🔍 Gitea Action Logs Protocol

**Log Location:**
```
~/gitea/data/actions_log/{owner}/{repo}/{hex_prefix}/{job_id}.log
Example: ~/gitea/data/actions_log/neilvibe/LocaNext/de/222.log
```

---

#### 1. LIST ALL LOGS (Newest First)
```bash
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -10
```
Output: Shows job ID, timestamp, size. **Use timestamp to identify new vs old.**

---

#### 2. CHECK IF A NEW BUILD STARTED
```bash
# Compare timestamps - if newest log timestamp > your push time, new build started
ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1
# Look at timestamp (e.g., "Dec 8 15:52")
```

---

#### 3. WATCH LIVE BUILD (Ongoing)
```bash
# Tail the newest log in real-time (Ctrl+C to stop)
tail -f $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)

# Or if you know the job ID (e.g., 223):
tail -f ~/gitea/data/actions_log/neilvibe/LocaNext/*/223.log
```

---

#### 4. CHECK BUILD RESULT (Completed)
```bash
# Last 50 lines of most recent log (shows success/failure)
tail -50 $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)

# Check for job status
grep -E "Job|SUCCESS|failed|🏁" $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)
```

---

#### 5. FIND ERRORS IN LOG
```bash
# Search for errors/failures in latest log
grep -iE "error|fail|::error" $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)
```

---

#### 6. CHECK VERSION IN BUILD
```bash
# Verify which version the build is using
grep -E "version|v[0-9]{10}" $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1) | head -5
```

---

#### Quick Aliases (add to ~/.bashrc)
```bash
alias gitea-list='ls -lt ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -10'
alias gitea-live='tail -f $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)'
alias gitea-result='tail -50 $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)'
alias gitea-err='grep -iE "error|fail|::error" $(ls -t ~/gitea/data/actions_log/neilvibe/LocaNext/*/*.log | head -1)'
```

---

#### Web UI Method
```
http://localhost:3000/neilvibe/LocaNext/actions
→ Click on run number → Click on job → View logs
```

### Create Workflow File
```bash
# In your repo:
mkdir -p .gitea/workflows
nano .gitea/workflows/build.yml
```

### LocaNext Build Pipeline
```yaml
name: Build LocaNext

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: python -m pytest tests/ -v

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install frontend deps
        run: cd locaNext && npm ci

      - name: Build Electron (Windows)
        run: cd locaNext && npm run build:win

      - name: Deploy to Update Server
        run: |
          scp locaNext/dist/LocaNext-Setup-*.exe update-server:/var/www/updates/
          scp locaNext/dist/latest.yml update-server:/var/www/updates/
```

### Self-Hosted Runner (For Windows Builds)

> **Full Guide:** See [WINDOWS_RUNNER_SETUP.md](WINDOWS_RUNNER_SETUP.md) for complete setup including **Ephemeral Mode** (recommended).

#### Quick Overview

**Recommended: Ephemeral Mode**
- Runner exits after each job (like GitHub Actions)
- No file handle/cleanup issues on Windows
- Fresh registration for every job

**Directory Structure:**
```
C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner\
├── act_runner.exe        # Runner binary
├── run_ephemeral.bat     # Ephemeral wrapper script
├── registration_token.txt # Gitea token
├── config.yaml           # Runner config
└── _work\                # Job workspace
```

#### Quick Start (Ephemeral Mode)

```powershell
# 1. Install prerequisites (Admin PowerShell, one-time)
choco install git -y --params "/GitAndUnixToolsOnPath"
choco install nssm -y

# 2. Create ephemeral service (Admin PowerShell, one-time)
nssm install GiteaActRunner "C:\...\GiteaRunner\run_ephemeral.bat"
nssm set GiteaActRunner AppDirectory "C:\...\GiteaRunner"
nssm start GiteaActRunner
```

See [WINDOWS_RUNNER_SETUP.md](WINDOWS_RUNNER_SETUP.md) for full instructions.

#### Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "git not recognized" | Git not in PATH | Reinstall Git with PATH option |
| "Job failed" after success | File handles (Windows) | Use **Ephemeral Mode** |
| Jobs timeout | Runner not a service | Install as Windows Service |
| Signing errors | electron-builder bug | Add `sign: "./scripts/skip-sign.js"` to package.json |

---

## Part 6: Integration with LocaNext

### Update Server Structure
```
/var/www/updates/
├── latest.yml          # Version info (auto-update checks this)
├── LocaNext-Setup-1.2.0.exe
├── LocaNext-Setup-1.2.1.exe
└── LocaNext-Setup-1.2.2.exe
```

### latest.yml Format
```yaml
version: 1.2.2
files:
  - url: LocaNext-Setup-1.2.2.exe
    sha512: <hash>
    size: 85000000
path: LocaNext-Setup-1.2.2.exe
sha512: <hash>
releaseDate: '2025-12-05T12:00:00.000Z'
```

### Desktop App Config
```javascript
// locaNext/electron/main.js
autoUpdater.setFeedURL({
  provider: 'generic',
  url: 'https://update-server.company.internal/updates'
});
```

---

## Quick Reference

### Daily Developer Workflow
```bash
# Morning: Get latest
git pull origin main

# Work on feature
git checkout -b feature/new-thing
# ... code ...
git add .
git commit -m "Add new thing"

# Push to trigger pipeline
git push origin feature/new-thing

# Create PR in Gitea web UI
# After review: Merge → Pipeline builds → Update available!
```

### Server Admin Cheatsheet
```bash
# Check Gitea status
sudo systemctl status gitea

# View logs
sudo journalctl -u gitea -f

# Backup
tar -czf gitea-backup.tar.gz /var/lib/gitea /etc/gitea

# Update Gitea
wget -O gitea-new https://dl.gitea.com/gitea/1.22/gitea-1.22-linux-amd64
sudo systemctl stop gitea
sudo mv gitea-new /usr/local/bin/gitea
sudo chmod +x /usr/local/bin/gitea
sudo systemctl start gitea
```

---

## Ports Summary

| Service | Port | Protocol |
|---------|------|----------|
| Gitea Web UI | 3000 | HTTP |
| Gitea SSH | 22 or 2222 | SSH |
| Update Server | 80/443 | HTTP(S) |

---

## Security Checklist

- [ ] SSH keys only (disable password auth)
- [ ] Gitea behind reverse proxy with HTTPS
- [ ] Firewall: Only allow internal IPs
- [ ] Regular backups of `/var/lib/gitea`
- [ ] Strong admin password
- [ ] Two-factor auth enabled

---

*Last updated: 2025-12-08*
*License: MIT (Gitea) | GPL v2 (Git)*
