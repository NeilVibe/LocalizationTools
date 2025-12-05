# Installation Guide - Step by Step

**For:** IT Department, System Administrators
**Time Required:** ~30 minutes
**Difficulty:** Easy

---

## Prerequisites

### Server Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 20.04+ / Windows Server 2019+ | Ubuntu 22.04 LTS |
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 50 GB | 100 GB |
| Network | Internal network access | Static IP |

### Client Requirements

| Component | Minimum |
|-----------|---------|
| OS | Windows 10+ |
| RAM | 4 GB |
| Disk | 2 GB free |

---

## Installation Overview

```
INSTALLATION STEPS:
═══════════════════════════════════════════════════════════════

Step 1: Install Gitea (Git Server)
        ↓
Step 2: Install Central Telemetry Server
        ↓
Step 3: Install Admin Dashboard
        ↓
Step 4: Deploy Desktop Apps to Users
        ↓
Step 5: Configure & Test

Total time: ~30 minutes
```

---

## Step 1: Install Gitea (Git Server)

### 1.1 Download Gitea

```bash
# Create directory
mkdir -p /opt/gitea/{custom/conf,data,log,repositories}
cd /opt/gitea

# Download Gitea (Linux)
wget https://dl.gitea.com/gitea/1.22.3/gitea-1.22.3-linux-amd64 -O gitea
chmod +x gitea
```

### 1.2 Create Configuration

```bash
cat > /opt/gitea/custom/conf/app.ini << 'EOF'
[server]
PROTOCOL = http
DOMAIN = git.company.local
HTTP_PORT = 3000
ROOT_URL = http://git.company.local:3000/
SSH_PORT = 2222
START_SSH_SERVER = true
OFFLINE_MODE = true

[database]
DB_TYPE = sqlite3
PATH = /opt/gitea/data/gitea.db

[repository]
ROOT = /opt/gitea/repositories

[log]
MODE = file
LEVEL = Info
ROOT_PATH = /opt/gitea/log

[security]
INSTALL_LOCK = false

[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true

[actions]
ENABLED = true
EOF
```

### 1.3 Create Systemd Service

```bash
cat > /etc/systemd/system/gitea.service << 'EOF'
[Unit]
Description=Gitea (Git with a cup of tea)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gitea
ExecStart=/opt/gitea/gitea web
Restart=always
Environment=GITEA_WORK_DIR=/opt/gitea

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable gitea
systemctl start gitea
```

### 1.4 Complete Web Setup

1. Open browser: `http://SERVER_IP:3000`
2. Create admin account
3. Click "Install Gitea"

### 1.5 Create Repository

1. Log in to Gitea
2. Click + → New Repository
3. Name: `LocalizationTools`
4. Create repository

---

## Step 2: Install Central Telemetry Server

### 2.1 Clone Repository

```bash
# From Gitea (internal) or USB transfer
cd /opt
git clone http://git.company.local:3000/admin/LocalizationTools.git
cd LocalizationTools
```

### 2.2 Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.3 Configure Environment

```bash
cat > .env << 'EOF'
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=9999
DATABASE_URL=sqlite:///./central_telemetry.db

# Security
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_IP_RANGES=192.168.0.0/16,10.0.0.0/8

# Telemetry Mode
IS_CENTRAL_SERVER=true
EOF
```

### 2.4 Initialize Database

```bash
python3 scripts/create_admin.py
```

### 2.5 Create Systemd Service

```bash
cat > /etc/systemd/system/locanext-central.service << 'EOF'
[Unit]
Description=LocaNext Central Telemetry Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/LocalizationTools
Environment=PATH=/opt/LocalizationTools/venv/bin
ExecStart=/opt/LocalizationTools/venv/bin/python server/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable locanext-central
systemctl start locanext-central
```

---

## Step 3: Install Admin Dashboard

### 3.1 Build Dashboard

```bash
cd /opt/LocalizationTools/adminDashboard
npm install
npm run build
```

### 3.2 Serve with Nginx (Optional)

```bash
# Install nginx
apt install nginx

# Configure
cat > /etc/nginx/sites-available/locanext-admin << 'EOF'
server {
    listen 5175;
    server_name admin.company.local;
    root /opt/LocalizationTools/adminDashboard/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

ln -s /etc/nginx/sites-available/locanext-admin /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 3.3 Or Run Development Server

```bash
cd /opt/LocalizationTools/adminDashboard
npm run dev -- --host 0.0.0.0 --port 5175
```

---

## Step 4: Deploy Desktop Apps

### 4.1 Build Desktop App

```bash
cd /opt/LocalizationTools/locaNext
npm install
npm run build:win
```

### 4.2 Installer Location

```
Output: /opt/LocalizationTools/locaNext/dist/LocaNext-Setup-X.X.X.exe
```

### 4.3 Deploy to Users

**Option A: Network Share**
```
Copy installer to: \\fileserver\software\LocaNext\
Users run installer from there
```

**Option B: Group Policy (AD)**
```
Deploy via SCCM/Intune/GPO
Silent install: LocaNext-Setup-X.X.X.exe /S
```

**Option C: Manual Distribution**
```
USB drive or email attachment
```

### 4.4 Configure Desktop App

On first run, users need to configure:
1. Central Server URL: `http://telemetry.company.local:9999`
2. Login credentials

Or pre-configure via config file:
```json
// %APPDATA%/LocaNext/config.json
{
  "centralServerUrl": "http://telemetry.company.local:9999",
  "telemetryEnabled": true
}
```

---

## Step 5: Configure & Test

### 5.1 Verify Services

```bash
# Check Gitea
curl http://git.company.local:3000/api/v1/version
# Expected: {"version":"1.22.3"}

# Check Central Server
curl http://telemetry.company.local:9999/health
# Expected: {"status":"healthy"}

# Check Admin Dashboard
curl http://admin.company.local:5175/
# Expected: HTML content
```

### 5.2 Test Desktop App

1. Install on test PC
2. Launch LocaNext
3. Login with admin credentials
4. Run a test operation
5. Verify telemetry in Admin Dashboard

### 5.3 Test Git Operations

```bash
# Clone repository
git clone http://git.company.local:3000/admin/LocalizationTools.git

# Make a change
echo "test" >> README.md

# Commit and push
git add . && git commit -m "Test commit" && git push
```

---

## Troubleshooting

### Gitea Won't Start

```bash
# Check logs
journalctl -u gitea -f

# Common issues:
# - Port 3000 in use: change HTTP_PORT in app.ini
# - Permission denied: check file ownership
```

### Central Server Won't Start

```bash
# Check logs
journalctl -u locanext-central -f

# Common issues:
# - Port 9999 in use: change SERVER_PORT in .env
# - Database locked: stop other processes
```

### Desktop App Can't Connect

```
1. Check firewall allows port 9999
2. Verify CENTRAL_SERVER_URL is correct
3. Test: curl http://telemetry.company.local:9999/health
```

---

## Quick Reference

### Service Commands

```bash
# Gitea
systemctl start/stop/restart gitea
systemctl status gitea

# Central Server
systemctl start/stop/restart locanext-central
systemctl status locanext-central

# View logs
journalctl -u gitea -f
journalctl -u locanext-central -f
```

### URLs

| Service | URL |
|---------|-----|
| Gitea | http://git.company.local:3000 |
| Central Server | http://telemetry.company.local:9999 |
| Admin Dashboard | http://admin.company.local:5175 |

### Default Ports

| Port | Service |
|------|---------|
| 3000 | Gitea Web |
| 2222 | Gitea SSH |
| 9999 | Central Telemetry |
| 5175 | Admin Dashboard |
| 8888 | Desktop Backend (local) |

---

## Installation Checklist

- [ ] Gitea installed and running
- [ ] Gitea admin account created
- [ ] LocalizationTools repo created in Gitea
- [ ] Central Server installed and running
- [ ] Admin Dashboard installed and accessible
- [ ] Desktop installer built
- [ ] Desktop app deployed to test PC
- [ ] All services verified working
- [ ] Firewall rules configured
- [ ] DNS entries added (or hosts files)

---

*Document Version: 2025-12-06*
*Classification: Internal - IT*
