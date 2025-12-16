# Enterprise Deployment Hub

**Version:** 1.0 | **For:** New company deployments

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Where to start?** | [CHECKLIST.md](CHECKLIST.md) |
| **Server setup?** | [02_SERVER_SETUP.md](02_SERVER_SETUP.md) |
| **Build & deploy?** | [04_BUILD_AND_DEPLOY.md](04_BUILD_AND_DEPLOY.md) |
| **Create users?** | [05_USER_MANAGEMENT.md](05_USER_MANAGEMENT.md) |
| **Security config?** | [06_NETWORK_SECURITY.md](06_NETWORK_SECURITY.md) |
| **Something broken?** | [10_TROUBLESHOOTING.md](10_TROUBLESHOOTING.md) |
| **API endpoints?** | [API_REFERENCE.md](API_REFERENCE.md) |

---

## 5-Minute Overview

**LocaNext** = Translation tools suite (Electron + Python backend)

```
User PCs                         Company Server
┌─────────────────┐              ┌─────────────────┐
│ LocaNext.exe    │───────────►  │ PostgreSQL:5432 │
│ ├─ Frontend     │              │ Gitea:3000      │
│ ├─ Backend      │              └─────────────────┘
│ └─ Local models │
└─────────────────┘
```

**Online mode:** Central PostgreSQL, multi-user, sync
**Offline mode:** Local SQLite, single-user, no network

---

## Deployment Steps (TL;DR)

```
1. SERVER    → Install PostgreSQL + Gitea
2. CLONE     → Clone repo, configure .env
3. BUILD     → Push to Gitea, CI builds installer
4. USERS     → Create accounts via API/dashboard
5. DEPLOY    → Users download from Gitea releases
6. CONFIGURE → Users enter server settings, login
```

---

## Key Commands

```bash
# Server health
sudo systemctl status postgresql gitea

# Build
git push company main  # Triggers CI

# Create user (API)
curl -X POST http://SERVER:8888/api/users \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"username":"X","password":"Y","role":"translator"}'

# Backup
pg_dump -U postgres locanext | gzip > backup.sql.gz
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Gitea | `http://SERVER_IP:3000` |
| Releases | `http://SERVER_IP:3000/locanext/LocaNext/releases` |
| API Docs | `http://SERVER_IP:8888/docs` |
| Health | `http://SERVER_IP:8888/health` |

---

## Key Files

| File | Purpose |
|------|---------|
| `.env` | Server configuration |
| `server/config.py` | Default settings |
| `pg_hba.conf` | PostgreSQL access control |
| `%APPDATA%\LocaNext\server-config.json` | User's server config |

---

## Key Ports

| Port | Service | Open To |
|------|---------|---------|
| 5432 | PostgreSQL | Company LAN only |
| 3000 | Gitea | Company LAN only |
| 22 | SSH | Admin subnet only |

---

## Documentation Index

```
docs/enterprise/
├── HUB.md                    ← YOU ARE HERE
├── CHECKLIST.md              ← Start here (step-by-step)
├── 01_PREREQUISITES.md       ← Requirements
├── 02_SERVER_SETUP.md        ← PostgreSQL, Gitea
├── 03_PROJECT_CLONE.md       ← Clone, configure
├── 04_BUILD_AND_DEPLOY.md    ← Build installer
├── 05_USER_MANAGEMENT.md     ← Users, passwords
├── 06_NETWORK_SECURITY.md    ← IP whitelist, firewall
├── 07_DASHBOARD_INTEGRATION.md ← External metrics
├── 08_DATABASE_INTEGRATION.md  ← External databases
├── 09_MAINTENANCE.md         ← Backups, updates
├── 10_TROUBLESHOOTING.md     ← Fix problems
├── API_REFERENCE.md          ← REST API
└── README.md                 ← Full overview
```

---

## Quick Troubleshooting

| Problem | Check |
|---------|-------|
| App shows "Offline" | Server reachable? Config saved? |
| Can't login | User exists? Password correct? |
| Build fails | Check Gitea Actions logs |
| Connection refused | PostgreSQL running? Firewall? |

**Full guide:** [10_TROUBLESHOOTING.md](10_TROUBLESHOOTING.md)

---

## First Session Checklist

1. Read [CHECKLIST.md](CHECKLIST.md)
2. Gather server IP, network range from IT
3. SSH into server
4. Follow [02_SERVER_SETUP.md](02_SERVER_SETUP.md)
5. Clone project per [03_PROJECT_CLONE.md](03_PROJECT_CLONE.md)
6. Build per [04_BUILD_AND_DEPLOY.md](04_BUILD_AND_DEPLOY.md)
7. Create users per [05_USER_MANAGEMENT.md](05_USER_MANAGEMENT.md)
8. Distribute to users

---

*Open this file first when deploying at a new company.*
