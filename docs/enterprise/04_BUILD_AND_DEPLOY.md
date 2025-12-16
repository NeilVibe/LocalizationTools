# 04 - Build and Deploy

**Purpose:** Building the LocaNext installer and distributing to users

---

## Overview

LocaNext is built as a Windows installer (NSIS) containing:
- Electron app (frontend)
- Embedded Python backend
- Required dependencies

---

## Build Methods

### Method 1: Automatic (Gitea CI/CD) - Recommended

Push to main branch triggers automatic build:

```bash
cd ~/LocaNext

# Make changes or trigger build
echo "Build $(date +%Y%m%d%H%M)" >> GITEA_TRIGGER.txt
git add -A
git commit -m "Trigger build"
git push company main
```

Monitor build: `http://10.10.30.50:3000/locanext/LocaNext/actions`

When complete, release available at: `http://10.10.30.50:3000/locanext/LocaNext/releases`

### Method 2: Manual Build (Admin Workstation)

```bash
cd ~/LocaNext

# Ensure dependencies installed
source venv/bin/activate
cd locaNext && npm install && cd ..

# Build frontend
cd locaNext
npm run build

# Build Electron app with NSIS installer
npm run electron:build

# Output location
ls -la dist/*.exe
```

---

## Build Configuration

### Configure Company Defaults

Before building, update defaults in `server/config.py`:

```python
# Default server for all clients
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "10.10.30.50")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "locanext")
POSTGRES_USER = os.getenv("POSTGRES_USER", "locanext_app")
# Password is NOT hardcoded - users enter via Server Config UI
```

### Configure App Metadata

Edit `locaNext/package.json`:

```json
{
  "name": "locanext",
  "version": "25.1216.1626",
  "description": "LocaNext - Localization Tools Suite",
  "author": "Your Company Name",
  "build": {
    "appId": "com.yourcompany.locanext",
    "productName": "LocaNext",
    "win": {
      "target": "nsis"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "installerIcon": "build/icon.ico",
      "uninstallerIcon": "build/icon.ico"
    }
  }
}
```

---

## Distribution Methods

### Method 1: Gitea Releases (Recommended)

Users download directly from Gitea:

1. **URL:** `http://10.10.30.50:3000/locanext/LocaNext/releases`
2. **Latest release:** Click "Latest" tag
3. **Download:** `LocaNext_vX.X.X_Light_Setup.exe`

### Method 2: Network Share

Copy installer to shared folder:

```bash
# Copy to Windows share
cp dist/LocaNext_*.exe /mnt/share/software/LocaNext/

# Or via PowerShell
Copy-Item "\\wsl$\Ubuntu\home\user\LocaNext\dist\*.exe" "\\fileserver\software\LocaNext\"
```

### Method 3: Email/Direct Transfer

For small teams, email the installer directly (~163MB).

---

## Installation Instructions for Users

### Standard Installation

```
1. Download LocaNext_vX.X.X_Light_Setup.exe from:
   http://10.10.30.50:3000/locanext/LocaNext/releases

2. Run the installer
   - Click "Next"
   - Choose installation directory (default: C:\Program Files\LocaNext)
   - Click "Install"
   - Wait for completion (~60-90 seconds)

3. First Launch
   - LocaNext will start automatically
   - "First Time Setup" will run (1-3 minutes):
     - Installing Python dependencies
     - Downloading Embedding Model (2.3GB)
     - Verifying installation
   - App will restart when complete

4. Login
   - Get credentials from your administrator
   - Enter username and password
   - Click "Login"

5. Server Configuration (if needed)
   - Click server status indicator (top right)
   - Click "Configure"
   - Enter server settings (ask admin if unsure)
   - Click "Save" and restart app
```

### Silent Installation (for IT deployment)

```cmd
LocaNext_vX.X.X_Light_Setup.exe /S /D=C:\Program Files\LocaNext
```

Parameters:
- `/S` - Silent mode (no UI)
- `/D=path` - Installation directory (must be last parameter)

---

## Post-Installation: User Configuration

### First-Time Setup Flow

```
1. App launches → First Time Setup screen
   ├─ Step 1: Installing Python dependencies
   ├─ Step 2: Downloading Embedding Model (2.3GB)
   └─ Step 3: Verifying installation

2. Setup complete → Login screen
   ├─ User enters credentials (from admin)
   └─ If credentials work → Main app

3. If PostgreSQL unreachable:
   └─ App works in Offline mode (SQLite)
   └─ User can configure server later via Settings
```

### Configuring Server Connection

If user needs to configure server settings:

1. Open LDM tool
2. Click server status indicator (globe icon, top toolbar)
3. Click "Configure" button
4. Enter:
   - Host: `10.10.30.50`
   - Port: `5432`
   - Username: `locanext_app`
   - Password: (provided by admin)
   - Database: `locanext`
5. Click "Test Connection"
6. If successful, click "Save"
7. Restart app

---

## Deployment Checklist

### Before Distribution

- [ ] Build completes without errors
- [ ] Installer size is expected (~163MB)
- [ ] Default server configured in `config.py`
- [ ] Version number updated
- [ ] Release created in Gitea
- [ ] Download link works

### User Onboarding

- [ ] User credentials created in system
- [ ] User informed of download location
- [ ] User has installation instructions
- [ ] User knows server settings (if manual config needed)
- [ ] IT aware of firewall requirements (port 5432 to server)

---

## Troubleshooting Builds

### Build Fails

```bash
# Check Node.js version
node --version  # Should be 20.x

# Check npm packages
cd locaNext && npm install

# Check Python
python3 --version  # Should be 3.11+

# Check logs
cat ~/.npm/_logs/*.log | tail -100
```

### Installer Too Large

Expected sizes:
- Installer: ~163 MB
- Installed: ~605 MB

If larger, check for unnecessary files in `dist/`.

### First-Run Setup Fails

Check user's network:
```powershell
# Can reach HuggingFace? (for model download)
Test-NetConnection -ComputerName huggingface.co -Port 443
```

If blocked, model can be pre-installed - see [09_MAINTENANCE.md](09_MAINTENANCE.md).

---

## Version Management

### Version Format

```
YY.MMDD.HHMM
Example: 25.1216.1626
         │  │    │
         │  │    └── Time: 16:26
         │  └────── Date: December 16
         └───────── Year: 2025
```

### Updating Version

```bash
# Update version in package.json
cd locaNext
npm version patch  # or minor, major

# Or manually edit package.json and commit
```

---

## Next Step

Build is ready. Proceed to [05_USER_MANAGEMENT.md](05_USER_MANAGEMENT.md) to set up user accounts.
