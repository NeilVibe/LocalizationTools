# Patch Server Setup Guide

**LocaNext Internal Update Distribution**

This guide covers setting up Gitea as a full patch server for distributing LocaNext updates within a company network.

---

## Architecture Overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PATCH SERVER ARCHITECTURE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║   DEVELOPMENT                      DISTRIBUTION                              ║
║   ───────────                      ────────────                              ║
║                                                                              ║
║   ┌─────────────┐                  ┌─────────────┐     ┌─────────────┐      ║
║   │   GitHub    │   (Public)       │   Gitea     │     │  Desktop    │      ║
║   │   Actions   │──────────────────│   Server    │────▶│    Apps     │      ║
║   │  (Builder)  │   Mirror         │ (Patch Srv) │     │  (Users)    │      ║
║   └─────────────┘                  └─────────────┘     └─────────────┘      ║
║         │                                │                    │              ║
║         │                                │                    │              ║
║         ▼                                ▼                    ▼              ║
║   ┌─────────────┐                  ┌─────────────┐     ┌─────────────┐      ║
║   │  GitHub     │                  │   Gitea     │     │ Auto-Update │      ║
║   │  Releases   │                  │  Releases   │     │   Check     │      ║
║   │  (Public)   │                  │ (Internal)  │     │ (on launch) │      ║
║   └─────────────┘                  └─────────────┘     └─────────────┘      ║
║                                                                              ║
║   OPTION A: Build on GitHub, Mirror to Gitea (RECOMMENDED)                   ║
║   OPTION B: Build on Gitea with self-hosted Windows runner                   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Option A: GitHub Build + Gitea Mirror (Recommended)

**Why this is recommended:**
- GitHub has free Windows runners
- No need to set up self-hosted runner
- Gitea just serves as internal mirror
- Simpler maintenance

### Step 1: GitHub Builds (Already Working)

GitHub Actions builds the installer on every triggered push:
```
.github/workflows/build-electron.yml
  └── Produces: LocaNext-Setup.exe + latest.yml
```

### Step 2: Mirror Releases to Gitea

After GitHub creates a release, mirror it to Gitea:

```bash
# Script: scripts/mirror_release_to_gitea.sh

#!/bin/bash
# Mirror latest GitHub release to Gitea

GITHUB_REPO="NeilVibe/LocalizationTools"
GITEA_URL="http://localhost:3000"
GITEA_REPO="neilvibe/LocaNext"
GITEA_TOKEN="${GITEA_TOKEN}"

# Get latest GitHub release
LATEST=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest")
TAG=$(echo "$LATEST" | jq -r '.tag_name')
VERSION=$(echo "$LATEST" | jq -r '.name')

echo "Mirroring release: $TAG ($VERSION)"

# Download assets
mkdir -p /tmp/release
curl -L -o /tmp/release/LocaNext-Setup.exe \
  "https://github.com/${GITHUB_REPO}/releases/download/${TAG}/LocaNext-Setup.exe"
curl -L -o /tmp/release/latest.yml \
  "https://github.com/${GITHUB_REPO}/releases/download/${TAG}/latest.yml"

# Create Gitea release
curl -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"tag_name\": \"${TAG}\",
    \"name\": \"${VERSION}\",
    \"body\": \"Mirrored from GitHub release.\",
    \"draft\": false,
    \"prerelease\": false
  }"

# Get release ID
RELEASE_ID=$(curl -s "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/tags/${TAG}" \
  -H "Authorization: token ${GITEA_TOKEN}" | jq -r '.id')

# Upload assets
curl -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}/assets" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -F "attachment=@/tmp/release/LocaNext-Setup.exe"

curl -X POST "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}/assets" \
  -H "Authorization: token ${GITEA_TOKEN}" \
  -F "attachment=@/tmp/release/latest.yml"

echo "Release mirrored successfully!"

# Cleanup
rm -rf /tmp/release
```

### Step 3: Auto-Mirror with Gitea Webhook

Add a webhook in Gitea to auto-mirror when GitHub releases:

1. Go to Gitea → Settings → Webhooks
2. Add webhook pointing to mirror script
3. Or run mirror script as cron job:

```bash
# Cron: Check for new releases every hour
0 * * * * /path/to/scripts/mirror_release_to_gitea.sh
```

---

## Option B: Full Gitea Build (Self-Hosted Runner)

**Why you might want this:**
- Complete independence from GitHub
- All builds internal
- Full control

### Step 1: Set Up Self-Hosted Windows Runner

Gitea Actions needs a Windows machine to build Electron apps.

```powershell
# On Windows machine (can be your dev machine or a VM)

# Download Gitea Act Runner
Invoke-WebRequest -Uri "https://dl.gitea.com/act_runner/0.2.6/act_runner-0.2.6-windows-amd64.exe" -OutFile "act_runner.exe"

# Register with Gitea
.\act_runner.exe register --instance http://localhost:3000 --token YOUR_RUNNER_TOKEN

# Start runner
.\act_runner.exe daemon
```

**Runner Token:** Get from Gitea → Site Administration → Actions → Runners

### Step 2: Update Gitea Workflow

Replace `.gitea/workflows/build.yml`:

```yaml
name: Build LocaNext (Gitea)

on:
  push:
    branches: [main]
    paths:
      - 'BUILD_TRIGGER.txt'
  workflow_dispatch:

jobs:
  build:
    runs-on: windows  # Uses self-hosted Windows runner
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Get version
        id: version
        shell: bash
        run: |
          VERSION=$(python -c "from version import SEMANTIC_VERSION; print(SEMANTIC_VERSION)")
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Install dependencies
        working-directory: locaNext
        run: npm ci

      - name: Build
        working-directory: locaNext
        run: npm run build:win

      - name: Create Release
        uses: https://gitea.com/actions/release-action@main
        with:
          files: |
            locaNext/dist/*.exe
            locaNext/dist/latest.yml
          api_key: ${{ secrets.GITEA_TOKEN }}
          tag: v${{ steps.version.outputs.version }}
          title: LocaNext v${{ steps.version.outputs.version }}
```

### Step 3: Create Gitea Token

1. Gitea → User Settings → Applications → Generate Token
2. Add as repository secret: `GITEA_TOKEN`

---

## Build Retention Policy

Keep only the latest 2 builds to save disk space.

### Cleanup Script

```bash
#!/bin/bash
# scripts/cleanup_old_releases.sh
# Keep only the latest N releases

GITEA_URL="http://localhost:3000"
GITEA_REPO="neilvibe/LocaNext"
GITEA_TOKEN="${GITEA_TOKEN}"
KEEP_COUNT=2

# Get all releases sorted by date
RELEASES=$(curl -s "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases" \
  -H "Authorization: token ${GITEA_TOKEN}" | jq -r '.[].id')

# Count releases
TOTAL=$(echo "$RELEASES" | wc -l)

if [ "$TOTAL" -gt "$KEEP_COUNT" ]; then
  # Delete old releases (keep first N)
  echo "$RELEASES" | tail -n +$((KEEP_COUNT + 1)) | while read RELEASE_ID; do
    echo "Deleting release $RELEASE_ID"
    curl -X DELETE "${GITEA_URL}/api/v1/repos/${GITEA_REPO}/releases/${RELEASE_ID}" \
      -H "Authorization: token ${GITEA_TOKEN}"
  done
fi

echo "Cleanup complete. Kept latest $KEEP_COUNT releases."
```

### Cron for Auto-Cleanup

```bash
# Run daily at midnight
0 0 * * * /path/to/scripts/cleanup_old_releases.sh
```

---

## Desktop App Configuration

### Update Source Selection

In `locaNext/electron/updater.js`:

```javascript
// Set UPDATE_SERVER environment variable:
// - 'github' (default) - Public GitHub releases
// - 'gitea' - Internal Gitea server
// - Custom URL - Any HTTP server with latest.yml

const UPDATE_SERVER = process.env.UPDATE_SERVER || 'github';
```

### For Company Deployment

Create a `.env` file or set in startup script:

```bash
# For internal company users
UPDATE_SERVER=gitea
GITEA_URL=http://your-gitea-server:3000
```

---

## Auto-Update Flow

```
Desktop App Launch
       │
       ▼
┌──────────────────┐
│ Check latest.yml │
│ from Patch Server│
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Compare versions │────▶│ Download .exe if │
│ (current vs new) │     │ newer available  │
└──────────────────┘     └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ Prompt user to   │
                         │ install update   │
                         └──────────────────┘
```

---

## Quick Setup Checklist

### Option A (Mirror)
- [ ] GitHub builds working (check Actions)
- [ ] Create Gitea token
- [ ] Run `mirror_release_to_gitea.sh` manually first
- [ ] Set up cron for auto-mirror
- [ ] Set up cleanup cron
- [ ] Test auto-update with `UPDATE_SERVER=gitea`

### Option B (Full Gitea)
- [ ] Install Act Runner on Windows machine
- [ ] Register runner with Gitea
- [ ] Create Gitea token as secret
- [ ] Update `.gitea/workflows/build.yml`
- [ ] Trigger test build
- [ ] Set up cleanup cron
- [ ] Test auto-update

---

## Troubleshooting

### Auto-Update Not Finding Updates

1. Check `latest.yml` is accessible:
   ```bash
   curl http://localhost:3000/neilvibe/LocaNext/releases/download/latest/latest.yml
   ```

2. Check version format matches

3. Check firewall allows connection

### Runner Not Picking Up Jobs

1. Check runner is registered: Gitea → Admin → Runners
2. Check runner is running: `act_runner.exe daemon`
3. Check workflow syntax

### Build Failing

1. Check all dependencies installed on runner
2. Check Git LFS configured
3. Check Node.js and Python paths

---

## Related Documents

- [GITEA_SETUP.md](GITEA_SETUP.md) - Gitea server installation
- [BUILD_AND_DISTRIBUTION.md](BUILD_AND_DISTRIBUTION.md) - Build process
- [locaNext/electron/updater.js](../locaNext/electron/updater.js) - Update configuration

---

*Created: 2025-12-07 | Priority 13 - Patch Server*
