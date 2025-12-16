# 03 - Project Clone and Initial Setup

**Purpose:** Cloning LocaNext repository and configuring for your company

---

## Overview

This guide walks through:
1. Creating the project folder
2. Cloning the repository
3. Configuring for your company
4. Setting up the development environment

---

## Step 1: Create Project Folder

### On Admin Workstation (WSL)

```bash
# Create project directory
mkdir -p ~/LocaNext
cd ~/LocaNext

# Verify location
pwd
# Should show: /home/[username]/LocaNext
```

---

## Step 2: Clone Repository

### Option A: From Original Source

```bash
# Clone from source (if you have access)
git clone https://github.com/YOUR_ORG/LocaNext.git .

# Or from your Gitea
git clone http://10.10.30.50:3000/YOUR_ORG/LocaNext.git .
```

### Option B: Copy from USB/Network Share

```bash
# If received via file transfer
cp -r /path/to/LocaNext/* ~/LocaNext/
cd ~/LocaNext
git init
git add -A
git commit -m "Initial import"
```

### Option C: First-time Setup (Push to New Gitea)

```bash
# After cloning or copying
cd ~/LocaNext

# Add company Gitea as remote
git remote add company http://10.10.30.50:3000/locanext/LocaNext.git

# Push to company Gitea
git push -u company main
```

---

## Step 3: Install Dependencies

### 3.1 Backend (Python)

```bash
cd ~/LocaNext

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify
python --version
pip list | grep -E "fastapi|sqlalchemy|psycopg2"
```

### 3.2 Frontend (Node.js)

```bash
cd ~/LocaNext/locaNext

# Install dependencies
npm install

# Verify
npm list --depth=0 | head -20
```

### 3.3 Admin Dashboard (if used)

```bash
cd ~/LocaNext/adminDashboard

# Install dependencies
npm install
```

---

## Step 4: Configure for Company

### 4.1 Environment Variables

Create `.env` file in project root:

```bash
cd ~/LocaNext
cp .env.example .env  # If exists, otherwise create new
vim .env
```

Configure:
```bash
# Database - Central PostgreSQL
POSTGRES_HOST=10.10.30.50
POSTGRES_PORT=5432
POSTGRES_USER=locanext_app
POSTGRES_PASSWORD=YOUR_APP_PASSWORD
POSTGRES_DB=locanext

# Database mode
DATABASE_MODE=auto  # auto, postgresql, sqlite

# Connection settings
POSTGRES_CONNECT_TIMEOUT=5

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8888

# Security
SECRET_KEY=GENERATE_A_RANDOM_64_CHAR_STRING
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Logging
LOG_LEVEL=INFO

# Company-specific
COMPANY_NAME=Your Company Name
ALLOWED_IP_RANGES=10.10.0.0/16
```

### 4.2 Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copy output to SECRET_KEY in .env
```

### 4.3 Configure IP Restrictions

Edit `server/config.py` or use environment variable:

```python
# In server/config.py - find and modify
ALLOWED_IP_RANGES = os.getenv("ALLOWED_IP_RANGES", "10.10.0.0/16").split(",")
```

### 4.4 Configure Default Server for Clients

Edit `server/config.py`:

```python
# Default PostgreSQL settings for client apps
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "10.10.30.50")  # Company server
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "locanext_app")
POSTGRES_DB = os.getenv("POSTGRES_DB", "locanext")
# Password should be set via user config or env var, not hardcoded
```

---

## Step 5: Initialize Database

### 5.1 Run Migrations

```bash
cd ~/LocaNext
source venv/bin/activate

# Initialize database tables
python3 -c "from server.database.db_setup import init_db; init_db()"
```

### 5.2 Create Admin User

```bash
python3 scripts/create_admin.py
# Follow prompts to create admin user
```

Or programmatically:
```bash
python3 -c "
from server.auth.user_manager import UserManager
um = UserManager()
um.create_user('admin', 'admin@company.com', 'CHANGE_THIS_PASSWORD', role='admin')
print('Admin user created')
"
```

---

## Step 6: Test Local Setup

### 6.1 Start Backend

```bash
cd ~/LocaNext
source venv/bin/activate
python3 server/main.py
```

### 6.2 Test Health (in another terminal)

```bash
curl http://localhost:8888/health | jq
```

Expected:
```json
{
  "status": "healthy",
  "database": "connected",
  "database_type": "postgresql",
  "local_mode": false,
  "version": "25.x.x"
}
```

### 6.3 Test API

```bash
# Get API docs
curl http://localhost:8888/docs

# Test login (if user created)
curl -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "YOUR_PASSWORD"}'
```

---

## Step 7: Configure Gitea CI/CD

### 7.1 Push Workflow Files

Ensure `.gitea/workflows/build.yml` exists and is configured:

```yaml
name: Build LocaNext

on:
  push:
    branches: [main]

env:
  POSTGRES_HOST: localhost
  POSTGRES_PORT: 5432
  POSTGRES_USER: locanext_ci
  POSTGRES_PASSWORD: locanext_ci_test
  POSTGRES_DB: locanext_ci_test

jobs:
  build:
    runs-on: ubuntu-latest
    # ... (existing workflow)
```

### 7.2 Create CI Database User

On PostgreSQL server:
```sql
CREATE USER locanext_ci WITH ENCRYPTED PASSWORD 'locanext_ci_test';
CREATE DATABASE locanext_ci_test OWNER locanext_ci;
```

### 7.3 Push and Trigger Build

```bash
cd ~/LocaNext
git add -A
git commit -m "Configure for company deployment"
git push company main
```

Check Gitea Actions: `http://10.10.30.50:3000/locanext/LocaNext/actions`

---

## Step 8: Verify Setup

### Checklist

- [ ] Project cloned to `~/LocaNext`
- [ ] Python venv created and dependencies installed
- [ ] Node.js dependencies installed
- [ ] `.env` configured with company values
- [ ] Database tables initialized
- [ ] Admin user created
- [ ] Backend starts and connects to PostgreSQL
- [ ] Health check returns `database_type: postgresql`
- [ ] Gitea CI/CD triggered and passes

---

## Directory Structure After Setup

```
~/LocaNext/
├── .env                    # Company configuration
├── .gitea/workflows/       # CI/CD workflows
├── venv/                   # Python virtual environment
├── server/                 # Backend code
├── locaNext/               # Frontend (Electron + Svelte)
├── adminDashboard/         # Admin web UI
├── docs/
│   └── enterprise/         # This documentation
├── scripts/                # Utility scripts
└── tests/                  # Test suite
```

---

## Next Step

Project is cloned and configured. Proceed to [04_BUILD_AND_DEPLOY.md](04_BUILD_AND_DEPLOY.md) to build the installer.
