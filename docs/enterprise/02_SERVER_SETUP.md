# 02 - Server Setup

**Purpose:** Setting up the central server (PostgreSQL, Gitea, services)

---

## Overview

This guide assumes:
- Server IP: `10.10.30.50` (replace with your actual IP)
- Server OS: Ubuntu 22.04+ LTS
- Company network: `10.10.0.0/16`

---

## Step 1: Initial Server Configuration

### 1.1 SSH into Server

```bash
ssh admin@10.10.30.50
```

### 1.2 Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop ufw
```

### 1.3 Set Hostname

```bash
sudo hostnamectl set-hostname locanext-server
echo "10.10.30.50 locanext-server" | sudo tee -a /etc/hosts
```

### 1.4 Configure Firewall

```bash
# Enable UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (restrict to admin subnet)
sudo ufw allow from 10.10.30.0/24 to any port 22

# Allow PostgreSQL (company network only)
sudo ufw allow from 10.10.0.0/16 to any port 5432

# Allow Gitea (company network only)
sudo ufw allow from 10.10.0.0/16 to any port 3000

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```

---

## Step 2: Install PostgreSQL

### 2.1 Install PostgreSQL 16

```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL 16
sudo apt install -y postgresql-16 postgresql-contrib-16

# Verify installation
sudo systemctl status postgresql
psql --version
```

### 2.2 Configure PostgreSQL for Network Access

```bash
# Edit postgresql.conf
sudo vim /etc/postgresql/16/main/postgresql.conf
```

Find and modify:
```ini
# Listen on all interfaces (or specific IP)
listen_addresses = '*'

# Performance tuning (adjust based on server RAM)
shared_buffers = 2GB              # 25% of RAM
effective_cache_size = 6GB        # 75% of RAM
maintenance_work_mem = 512MB
work_mem = 64MB
max_connections = 200
```

### 2.3 Configure Client Authentication

```bash
# Edit pg_hba.conf
sudo vim /etc/postgresql/16/main/pg_hba.conf
```

Add at the end (before any "reject" rules):
```
# LocaNext connections from company network
host    locanext        locanext_app    10.10.0.0/16    scram-sha-256
host    locanext        locanext_admin  10.10.30.0/24   scram-sha-256
```

### 2.4 Restart PostgreSQL

```bash
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### 2.5 Create Database and Users

```bash
# Switch to postgres user
sudo -u postgres psql
```

Run these SQL commands:
```sql
-- Create database
CREATE DATABASE locanext;

-- Create application user (for LocaNext clients)
CREATE USER locanext_app WITH ENCRYPTED PASSWORD 'CHANGE_THIS_STRONG_PASSWORD';
GRANT CONNECT ON DATABASE locanext TO locanext_app;

-- Create admin user (for management)
CREATE USER locanext_admin WITH ENCRYPTED PASSWORD 'CHANGE_THIS_ADMIN_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE locanext TO locanext_admin;

-- Connect to locanext database
\c locanext

-- Grant schema permissions
GRANT USAGE ON SCHEMA public TO locanext_app;
GRANT CREATE ON SCHEMA public TO locanext_admin;

-- App user permissions (read/write data, not schema)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO locanext_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO locanext_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO locanext_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO locanext_app;

-- Exit
\q
```

### 2.6 Test Connection

```bash
# Test from server itself
psql -h localhost -U locanext_app -d locanext -c "SELECT version();"

# Test from admin workstation (run on your machine)
psql -h 10.10.30.50 -U locanext_app -d locanext -c "SELECT version();"
```

---

## Step 3: Install Gitea

### 3.1 Create Gitea User

```bash
sudo adduser --system --shell /bin/bash --group --disabled-password --home /home/gitea gitea
```

### 3.2 Download and Install Gitea

```bash
# Download latest Gitea
wget -O /tmp/gitea https://dl.gitea.com/gitea/1.21/gitea-1.21-linux-amd64
sudo mv /tmp/gitea /usr/local/bin/gitea
sudo chmod +x /usr/local/bin/gitea

# Create directories
sudo mkdir -p /var/lib/gitea/{custom,data,log}
sudo mkdir -p /etc/gitea
sudo chown -R gitea:gitea /var/lib/gitea
sudo chown root:gitea /etc/gitea
sudo chmod 770 /etc/gitea
```

### 3.3 Create Systemd Service

```bash
sudo vim /etc/systemd/system/gitea.service
```

Paste:
```ini
[Unit]
Description=Gitea (Git with a cup of tea)
After=syslog.target
After=network.target
After=postgresql.service

[Service]
RestartSec=2s
Type=simple
User=gitea
Group=gitea
WorkingDirectory=/var/lib/gitea/
ExecStart=/usr/local/bin/gitea web --config /etc/gitea/app.ini
Restart=always
Environment=USER=gitea HOME=/home/gitea GITEA_WORK_DIR=/var/lib/gitea

[Install]
WantedBy=multi-user.target
```

### 3.4 Start Gitea

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitea
sudo systemctl start gitea
```

### 3.5 Configure Gitea (Web UI)

1. Open browser: `http://10.10.30.50:3000`
2. Complete initial configuration:
   - **Database Type:** PostgreSQL
   - **Host:** `127.0.0.1:5432`
   - **User:** `locanext_admin`
   - **Password:** (the admin password you set)
   - **Database Name:** `locanext` (or create separate `gitea` database)
   - **Site Title:** `LocaNext - Company Name`
   - **Server Domain:** `10.10.30.50`
   - **SSH Port:** 22
   - **HTTP Port:** 3000
   - **Base URL:** `http://10.10.30.50:3000/`
3. Create admin account when prompted

### 3.6 Configure Gitea Settings

Edit `/etc/gitea/app.ini`:
```ini
[server]
DOMAIN           = 10.10.30.50
HTTP_PORT        = 3000
ROOT_URL         = http://10.10.30.50:3000/
DISABLE_SSH      = false
SSH_PORT         = 22
LFS_START_SERVER = true

[repository]
DEFAULT_BRANCH = main

[security]
INSTALL_LOCK = true

[service]
DISABLE_REGISTRATION = true  # Admin creates accounts manually

[actions]
ENABLED = true  # Enable CI/CD
```

Restart:
```bash
sudo systemctl restart gitea
```

---

## Step 4: Install Gitea Actions Runner

For CI/CD to build LocaNext:

### 4.1 Download Runner

```bash
# Create runner directory
sudo mkdir -p /opt/gitea-runner
cd /opt/gitea-runner

# Download runner
sudo wget https://dl.gitea.com/act_runner/0.2.6/act_runner-0.2.6-linux-amd64 -O act_runner
sudo chmod +x act_runner
```

### 4.2 Register Runner

```bash
# Get registration token from Gitea:
# Settings > Actions > Runners > Create new Runner

# Register
./act_runner register --no-interactive \
  --instance http://10.10.30.50:3000 \
  --token YOUR_REGISTRATION_TOKEN \
  --name "locanext-runner" \
  --labels "ubuntu-latest:docker://node:20"
```

### 4.3 Create Runner Service

```bash
sudo vim /etc/systemd/system/gitea-runner.service
```

Paste:
```ini
[Unit]
Description=Gitea Actions Runner
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gitea-runner
ExecStart=/opt/gitea-runner/act_runner daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitea-runner
sudo systemctl start gitea-runner
```

---

## Step 5: Install Build Dependencies

For building LocaNext on the server:

```bash
# Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Build tools
sudo apt install -y build-essential

# Wine (for Windows builds)
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine64 wine32

# Verify
node --version   # v20.x.x
python3.11 --version
wine --version
```

---

## Step 6: Verify Setup

### Test PostgreSQL

```bash
psql -h 10.10.30.50 -U locanext_app -d locanext -c "SELECT 'PostgreSQL OK' as status;"
```

### Test Gitea

```bash
curl -s http://10.10.30.50:3000/api/v1/version | jq
```

### Check Services

```bash
sudo systemctl status postgresql
sudo systemctl status gitea
sudo systemctl status gitea-runner
```

---

## Server Credentials Summary

Document these securely:

```
PostgreSQL:
  Host: 10.10.30.50
  Port: 5432
  Database: locanext
  App User: locanext_app / [PASSWORD]
  Admin User: locanext_admin / [PASSWORD]

Gitea:
  URL: http://10.10.30.50:3000
  Admin: [USERNAME] / [PASSWORD]

SSH:
  Host: 10.10.30.50
  Port: 22
  User: admin
```

---

## Next Step

Server is ready. Proceed to [03_PROJECT_CLONE.md](03_PROJECT_CLONE.md) to clone the LocaNext project.
