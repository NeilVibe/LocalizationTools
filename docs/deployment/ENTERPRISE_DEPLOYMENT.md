# LocaNext - Enterprise Self-Hosted Deployment

## For Companies with Strict Network Security

Deploy LocaNext **entirely within your company network** with NO external dependencies.

- No external internet required (internal network only)
- No GitHub or external services
- Central PostgreSQL for multi-user collaboration
- All updates distributed internally via Gitea
- Maximum security and control

---

## Architecture Overview

```
YOUR COMPANY NETWORK (Closed/Isolated)
│
├── CENTRAL SERVER (192.168.1.100)
│   ├── PostgreSQL:5432      ← All user data
│   ├── Gitea:3000           ← Auto-updates, CI/CD
│   └── LanguageTool:8081    ← Grammar checking (optional)
│
└── EMPLOYEE COMPUTERS (192.168.1.x)
    └── LocaNext.exe
        ├── Embedded Python backend (localhost:8888)
        ├── Connects to central PostgreSQL
        └── Auto-checks Gitea for updates
```

**Key Points:**
- Each PC runs its own embedded backend (localhost:8888)
- Central services are configured via **environment variables**
- **No source code changes needed** - just set env vars

---

## Configuration (Environment Variables)

**Set these in a `.env` file or system environment variables:**

### Essential for Company Deployment

| Variable | Example | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `192.168.1.100` | Central PostgreSQL server |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `localization_admin` | Database username |
| `POSTGRES_PASSWORD` | `your_secure_password` | Database password |
| `POSTGRES_DB` | `localizationtools` | Database name |
| `LANGUAGETOOL_URL` | `http://192.168.1.100:8081/v2/check` | Grammar server |
| `GITEA_URL` | `http://192.168.1.100:3000` | Auto-update server |

### Example .env File

```bash
# Place this in the project root or set as system env vars

# Database (Central PostgreSQL)
POSTGRES_HOST=192.168.1.100
POSTGRES_PORT=5432
POSTGRES_USER=localization_admin
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=localizationtools

# Grammar Check Server (optional)
LANGUAGETOOL_URL=http://192.168.1.100:8081/v2/check

# Auto-Update Server
GITEA_URL=http://192.168.1.100:3000
```

### All Available Variables

**Server:**
| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `127.0.0.1` | Local backend bind address |
| `SERVER_PORT` | `8888` | Local backend port |

**Database:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_MODE` | `auto` | `auto`, `postgres`, or `sqlite` |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `localization_admin` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `change_this_password` | PostgreSQL password |
| `POSTGRES_DB` | `localizationtools` | PostgreSQL database |
| `POSTGRES_CONNECT_TIMEOUT` | `3` | Connection timeout (seconds) |

**External Services:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LANGUAGETOOL_URL` | `http://localhost:8081/v2/check` | Grammar server |
| `CENTRAL_SERVER_URL` | (empty) | Telemetry server (optional) |

**Security:**
| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-...` | JWT signing key (CHANGE!) |
| `ALLOWED_IP_RANGE` | (empty) | IP whitelist (CIDR format) |

**Logging:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `LOG_RETENTION_DAYS` | `90` | Log retention (days) |

---

## Setup Workflow

### Step 1: Server Setup

On your central server (192.168.1.100):

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE USER localization_admin WITH PASSWORD 'your_secure_password';
CREATE DATABASE localizationtools OWNER localization_admin;
\q

# Allow network connections (edit pg_hba.conf)
# Add: host all all 192.168.1.0/24 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 2: Install Gitea (Update Server)

```bash
# Download and install Gitea
wget https://dl.gitea.io/gitea/1.21/gitea-1.21-linux-amd64
chmod +x gitea-1.21-linux-amd64
sudo mv gitea-1.21-linux-amd64 /usr/local/bin/gitea

# Create service and start
sudo systemctl enable gitea
sudo systemctl start gitea
```

### Step 3: Configure .env

Create `.env` in project root:

```bash
POSTGRES_HOST=192.168.1.100
POSTGRES_PASSWORD=your_secure_password
LANGUAGETOOL_URL=http://192.168.1.100:8081/v2/check
GITEA_URL=http://192.168.1.100:3000
SECRET_KEY=your-very-secure-random-key
```

### Step 4: Build Installer

```bash
# Push to Gitea - CI/CD builds automatically
git push company main

# Or build manually
cd locaNext && npm run build && npm run build:electron
```

### Step 5: Distribute to Employees

1. Employees download installer from Gitea releases
2. Install LocaNext.exe
3. App reads env vars or config file, connects to central server
4. Auto-updates work via Gitea

---

## How Configuration Works

```
Priority Order:
1. Environment Variables (highest)
2. .env file in project root
3. %APPDATA%\LocaNext\server-config.json (user config)
4. Default values in server/config.py (lowest)
```

**For employees:** App reads `server-config.json` which stores server IP after first login.

**For build:** Set env vars in CI/CD or `.env` file before building.

---

## Security Benefits

- **No external network access** - everything stays in company network
- **You control updates** - build, approve, distribute
- **Auditable** - security team can inspect all traffic
- **Configurable** - all settings via environment variables, no source code changes

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect to PostgreSQL | Check `POSTGRES_HOST`, firewall, `pg_hba.conf` |
| Updates not detected | Check `GITEA_URL` env var, Gitea running |
| "Offline mode" showing | Check network, `POSTGRES_HOST` reachable |
| Wrong server after install | Check `server-config.json` in %APPDATA% |

**Test connection:**
```bash
# From employee PC
ping 192.168.1.100
curl http://192.168.1.100:3000/api/v1/version
psql -h 192.168.1.100 -U localization_admin -d localizationtools
```

---

## Summary

| What | How |
|------|-----|
| **Configure servers** | Set environment variables (no source changes) |
| **Build** | Push to Gitea or `npm run build:electron` |
| **Distribute** | Employees download from Gitea releases |
| **Updates** | Automatic via Gitea |
| **Security** | 100% internal network |

**The app picks up environment variables automatically on startup - no code changes needed!**
