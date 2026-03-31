# LAN Server Mode — Requirements & Architecture

**Date:** 2026-04-01
**Status:** REQUIREMENTS GATHERED — needs grill-me + security review before planning
**Priority:** HIGH — blocks multi-user workflow

---

## Goal

One-click installer option: "Set Up as LAN Server" → admin's machine becomes the central database server. Teammates install LocaNext as normal clients, enter the server IP in Settings, and work collaboratively with synced data.

---

## Architecture

```
ADMIN MACHINE (Server Mode)                TEAMMATE MACHINES (Client Mode)
┌──────────────────────────────────┐       ┌──────────────────────────────┐
│ LocaNext (full)                  │       │ LocaNext (full)              │
│ ├── Embedded Python Backend      │       │ ├── Embedded Python Backend   │
│ ├── MegaIndex (local gamedata)   │       │ ├── MegaIndex (local gamedata)│
│ ├── FAISS (local)                │       │ ├── FAISS (local)             │
│ ├── Audio/Image (local)          │       │ ├── Audio/Image (local)       │
│ └── PostgreSQL Server ◄─────────────────►│ └── PG Client → Admin's PG    │
│     ├── All ldm_* tables         │  LAN  │                               │
│     ├── User accounts            │       │ Settings:                     │
│     ├── Sessions + locks         │       │   Server: 192.168.x.x:5432   │
│     └── TM data                  │       └──────────────────────────────┘
└──────────────────────────────────┘
```

**Key principle:** Everything is client-side EXCEPT database operations. Each machine runs its own backend for MegaIndex, FAISS, audio, file parsing. Only row edits, TM, file management, and sync go through PostgreSQL on the server machine.

---

## What the Installer Does (Server Mode Checkbox)

### Step 1: Install Portable PostgreSQL
- Bundle PostgreSQL 15 portable (~100MB) inside the installer
- Extract to `<install>/resources/postgresql/`
- Initialize data directory: `initdb -D <datadir>`
- Set PG superuser password automatically

### Step 2: Configure PostgreSQL for LAN Access
- `postgresql.conf`: `listen_addresses = '*'` (or machine's LAN IP)
- `postgresql.conf`: `port = 5432`
- `pg_hba.conf`: Allow connections from office LAN range only
  ```
  # IPv4 local connections (office LAN only):
  host    localizationtools    locanext_service    192.168.0.0/16    scram-sha-256
  host    localizationtools    locanext_service    10.0.0.0/8        scram-sha-256
  ```
- Start PostgreSQL service (Windows service or background process)

### Step 3: Create Database + Schema
- Create database: `localizationtools`
- Create service account: `locanext_service` with strong auto-generated password
- Run schema initialization (all ldm_* tables + indexes)
- Create default admin user (admin/admin123 → force password change on first login)

### Step 4: Open Firewall Port
- Windows Firewall rule: allow TCP 5432 inbound from LAN range only
- Display the machine's LAN IP and port to the admin: "Your server is ready at 192.168.x.x:5432"

### Step 5: Register Windows Service
- PostgreSQL runs as a Windows service (auto-start on boot)
- Service name: `LocaNextDB`

---

## What Clients Need (Settings UI)

### New Settings Section: "Server Connection"

```
┌─ Server Connection ──────────────────────────┐
│                                               │
│  Mode:  ○ Offline (Local Only)                │
│         ● Online (Connect to Server)          │
│                                               │
│  Server Address:  [192.168.1.100]             │
│  Port:            [5432]                      │
│                                               │
│  Status: ● Connected (PostgreSQL 15.x)        │
│                                               │
│  [Test Connection]                            │
│                                               │
└───────────────────────────────────────────────┘
```

- Client enters IP + Port
- App stores in local config (persists across sessions)
- On startup: auto-test connection → if reachable, online mode; if not, offline fallback
- The PG service account credentials are stored in the client config (set once by admin during team onboarding)

---

## Admin Dashboard (NEW UI Page)

### Location: Settings Menu → "Admin Dashboard" (admin role only)

**Tabs:**
1. **Users** — Create/edit/delete users, assign roles + teams + languages
2. **Teams** — Manage team groups
3. **Access** — Platform/project restriction management
4. **Sessions** — Active users, who's editing what
5. **Database** — Connection status, table sizes, health

### User Management Flow:
1. Admin creates user: username, password, team, language, role
2. Admin gives teammate: server IP + port + their username + temporary password
3. Teammate installs LocaNext → Settings → enters server IP:PORT
4. Teammate logs in with their credentials
5. First login forces password change

---

## Security Model

### Network Security
- PostgreSQL listens on LAN only (private IP range)
- `pg_hba.conf` restricts to office IP ranges (192.168.x.x, 10.x.x.x)
- Windows Firewall rule scoped to LAN subnet only
- NO internet-facing ports
- SSL/TLS on PG connections (optional but recommended)

### Authentication
- App-level: JWT + bcrypt (existing system)
- Database-level: shared service account (`locanext_service`) with strong password
- Individual users managed at app level, not PG level
- Rate limiting on login attempts (existing)

### Data Security
- All data stays on internal LAN
- No cloud dependency
- Backups: admin runs db_manager.sh (existing)
- Passwords: bcrypt hashed, never stored in plaintext

### What Security Team Needs to Know
- Standard PostgreSQL on internal LAN (same as any internal database)
- Only one port opened (5432), restricted to LAN IP range
- Standard auth (JWT + bcrypt), industry standard
- No new external dependencies or cloud services
- All traffic stays within office network

---

## Deliverables

1. **Installer enhancement** — PostgreSQL bundling + auto-setup
2. ~~Admin Dashboard page~~ **ALREADY EXISTS** — `/adminDashboard/` on port 5174 (localhost only)
3. **Client Server Settings** — IP:PORT field in Settings
4. **Security Communication Document** — For security team approval
5. **Security Audit** — Full review of network exposure + auth flow
6. **Setup Guide** — Step-by-step for admin (auto-generated by installer)

---

## Admin Dashboard — ALREADY EXISTS

**Location:** `/adminDashboard/` — separate Svelte+SvelteKit app on port 5174
**Access:** localhost only (admin's machine browser only — inherently secure)

**7 pages already built:**
1. `/` — Overview (quick stats, live activity indicator)
2. `/users` — User Management (create/edit/delete, assign role+team+language, reset password)
3. `/stats` — Stats & Rankings (analytics, medal system)
4. `/logs` — Activity Logs (terminal-style, color-coded, 3 tabs)
5. `/telemetry` — Telemetry Data
6. `/database` — Database Stats (health, table sizes, pool status)
7. `/server` — Server Monitoring

**User creation form fields:** username, password, email, full_name, team, language, department, role, must_change_password
**Docs:** QUICKSTART.md, DASHBOARD_STATUS.md, DASHBOARD_REFACTOR.md, FRONTEND_MONITORING.md

---

## What Already EXISTS (backend + frontend ready)

- **Admin Dashboard** (7 pages, 17+ API endpoints, WebSocket real-time) ← DONE
- User CRUD API (create, update, delete, activate, reset password) ← DONE
- Role system (user/admin/superadmin) ← DONE
- Team + language fields on user model ← DONE
- Resource access control (platform/project restriction + grants) ← DONE
- Capabilities system (4 privileged operations) ← DONE
- WebSocket presence + row locking ← DONE
- 3-mode database detection (PG → SQLite server → SQLite offline) ← DONE
- Auto-fallback on connection failure ← DONE
- Session management + audit logging
- db_manager.sh (backup, reset, analyze)

---

## What Needs to Be BUILT

| Component | Effort | Depends On |
|-----------|--------|-----------|
| Bundle portable PostgreSQL in installer | MEDIUM | Installer scripting |
| Auto-configure PG (pg_hba, listen_addresses) | MEDIUM | PG bundling |
| Windows service registration | SMALL | PG bundling |
| Firewall rule automation | SMALL | PG bundling |
| ~~Admin Dashboard page~~ | ~~LARGE~~ | **ALREADY EXISTS** |
| Server Settings UI in client | SMALL | Config system |
| Security comms document | SMALL | Architecture finalized |
| Security audit | MEDIUM | Implementation done |
| Setup/onboarding guide | SMALL | Everything else |

**Deferred:** Admin build vs User build (separate installer variants) — for another day.

---

## Execution Plan (Step-by-Step for Next Session)

### Phase 1: Research + Grill (use skills)

```
1. /grill-me on the full LAN server architecture
   → Stress-test: What happens when admin machine is off? What if PG crashes?
   → Stress-test: What if two admins install server mode?
   → Stress-test: What if client has stale server IP?

2. /deep-research on portable PostgreSQL bundling for Windows
   → How to bundle PG without full installer?
   → PostgreSQL Portable vs embedded PG?
   → Size impact? Startup time?

3. /architecture-designer → ADR for LAN server mode
   → Document the decision: shared PG, not central API server
   → Document: why localhost-only dashboard is the right call
   → Document: service account vs individual PG accounts
```

### Phase 2: Security (use skills + agents)

```
4. /secure-code-guardian → OWASP review of network exposure
   → PG port exposed on LAN: what are the risks?
   → JWT token in transit: is TLS needed?
   → Service account shared password: is this OK?

5. /security-reviewer → Full audit of auth flow + PG config
   → pg_hba.conf review
   → CORS configuration
   → Rate limiting on network endpoints

6. security-auditor agent → Automated scan

7. /internal-comms → Write "Security Team Communication Document"
   → What we're doing (self-hosted PG on LAN)
   → What ports are opened (5432 only, LAN-restricted)
   → What auth is used (JWT + bcrypt + PG scram-sha-256)
   → What data flows over the network
   → Comparison to standard enterprise DB deployment
```

### Phase 3: Implementation (use skills)

```
8. /postgres-pro → PG configuration scripts
   → postgresql.conf template
   → pg_hba.conf template (LAN-restricted)
   → initdb + createdb + createuser automation

9. /devops-engineer → Installer scripting
   → Electron-builder extraResources for PG
   → Post-install script (Windows service registration)
   → Firewall rule automation (netsh)

10. Svelte Server Settings UI
    → Mode toggle: Offline / Online
    → IP + Port fields
    → Test Connection button
    → Status indicator

11. Config system wiring
    → Save server IP:PORT to local config
    → On startup: test connection → mode decision
```

### Phase 4: Review (agents)

```
12. 8-agent parallel review (same as Phase 107)
    → code-reviewer + silent-failure-hunter + code-simplifier
    → security-auditor + python-reviewer + architecture review
    → /differential-review for security-focused diff
```
