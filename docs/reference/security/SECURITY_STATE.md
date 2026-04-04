# LocaNext Security State — Full Audit (2026-04-04)

> **5-agent parallel security audit.** This document captures the COMPLETE security posture of LocaNext.

---

## Architecture Overview

```
[User PC - Electron]                    [Admin PC - Electron + PG]
 ├─ Svelte 5 SPA                         ├─ Svelte 5 SPA
 ├─ Embedded Python Backend               ├─ Embedded Python Backend (FastAPI)
 ├─ SQLite (offline fallback)             ├─ PostgreSQL 16 (bundled)
 └─ JWT in localStorage                  ├─ Self-signed TLS certs (generated)
                                          ├─ Windows Firewall rule (/16 LAN)
        ── HTTP+WS over LAN ──>          └─ Socket.IO WebSocket
```

---

## What's ROCK SOLID (Implemented & Working)

| Layer | What | How | Files |
|-------|------|-----|-------|
| **Password Hashing** | bcrypt, 12 rounds | `bcrypt.hashpw()` + `bcrypt.checkpw()` | `server/utils/auth.py:23-40` |
| **JWT Auth** | HS256 with configurable secret, 60min expiry | PyJWT encode/decode | `server/utils/auth.py:75-164` |
| **RBAC** | 3-tier: user/admin/superadmin | Hierarchy with protected user_id=1 | `server/services/auth_service.py:28-31` |
| **Login Rate Limiting** | 5 attempts / 15 min per IP | Failed login counter + HTTP 429 | `server/api/auth_async.py:32-89` |
| **SQL Injection Prevention** | SQLAlchemy ORM exclusively | Parameterized queries, no raw SQL | All repositories |
| **Identifier Validation** | Regex allowlist for DB identifiers | `_SAFE_IDENT_RE = r'^[a-z][a-z0-9_]{0,62}$'` | `server/setup/steps.py:23` |
| **Audit Logging** | 16 event types, severity levels | Dedicated `security_audit.log` | `server/utils/audit_logger.py` |
| **Credential Storage** | OS-level file permissions | Windows: icacls, Linux: chmod 0600 | `server/setup/credential_store.py` |
| **IP Filtering** | CIDR-based middleware | X-Forwarded-For support, configurable | `server/middleware/ip_filter.py` |
| **Timing Attack Prevention** | `secrets.compare_digest()` for admin token | Constant-time comparison | `server/utils/auth.py:356` |
| **PG Password Generation** | `secrets.token_urlsafe(24)` | Cryptographically secure random | `server/setup/steps.py:605` |
| **PG Auth** | scram-sha-256 | pg_hba.conf template | `server/setup/steps.py:253` |
| **Firewall** | Windows netsh, /16 LAN scope | Auto-created on startup + setup wizard | `server/setup/steps.py:119-145`, `server/main.py:1121-1145` |
| **SSL Certs** | Self-signed RSA 2048, 10yr, SAN with LAN IP | Python `cryptography` library | `server/setup/steps.py:721-842` |
| **PG SSL** | `ssl = on` in postgresql.conf if certs exist | Two-phase: start plain, enable SSL | `server/setup/steps.py:922-935` |
| **Electron Sandbox** | nodeIntegration=false, contextIsolation=true | Preload script with safe IPC bridge | `locaNext/electron/main.js:957-960` |
| **Sensitive Log Redaction** | password, token, secret, api_key masked | Middleware intercept | `server/middleware/logging_middleware.py:52-56` |
| **Startup Security Check** | Validates SECRET_KEY, API_KEY, admin password | Warns or fails based on SECURITY_MODE | `server/config.py:529-621` |
| **Offline Token Rejection** | OFFLINE_MODE tokens blocked in PG mode | Prevents unauthenticated network access | `server/utils/auth.py:134-150` |
| **DEV_MODE Guard** | Auto-auth only from localhost | Prevents network bypass | `server/utils/dependencies.py:318-321` |

---

## Client-to-Server Connection: How It Works

```
User Build (10.35.46.x)  ──── HTTP + WebSocket ────>  Admin Build (10.35.34.x:8888)
                                                            │
                                                            ├─ FastAPI (port 8888, 0.0.0.0 in LAN mode)
                                                            │   └─ JWT Bearer auth on every request
                                                            │
                                                            └─ PostgreSQL (port 5432)
                                                                ├─ ssl = on (self-signed cert)
                                                                ├─ pg_hba: host ... scram-sha-256
                                                                ├─ Firewall: /16 LAN scope
                                                                └─ Password: secrets.token_urlsafe(24)
```

**PG Connection Security:**
- pg_hba.conf uses `host` (not `hostssl`) — allows BOTH SSL and non-SSL
- PG has `ssl = on` — **server OFFERS SSL**
- psycopg2 auto-negotiates SSL when server offers it
- **Result: Connection IS encrypted via SSL negotiation**
- scram-sha-256 auth means password is NEVER sent in plaintext (even without SSL)

**FastAPI Connection:**
- HTTP (not HTTPS) — Electron app connects over LAN
- JWT Bearer token in Authorization header
- WebSocket auth via Socket.IO `auth: { token }` parameter
- CORS restricted to known origins in production

---

## What Could Be Stronger (Known Gaps)

### HIGH Priority

| Gap | Current State | Risk | Recommendation |
|-----|--------------|------|----------------|
| **FastAPI runs HTTP** | No TLS on port 8888 | LAN traffic sniffable | Add uvicorn SSL or nginx reverse proxy |
| **WebSocket over WS** | Not WSS | Real-time data unencrypted | Enable WSS with same TLS cert |
| **JWT secret default** | `"dev-secret-key-CHANGE-IN-PRODUCTION"` | Token forgery if unchanged | SECURITY_MODE=strict enforces change |
| **Admin password default** | `admin/admin123` | Trivial login | Force password change on first login |
| **CORS_ALLOW_ALL in LAN** | `True` when no CORS_ORIGINS set | Cross-origin attacks | Set explicit CORS_ORIGINS |
| **localStorage JWT** | Token in localStorage | XSS can steal token | Move to httpOnly cookie or memory |
| **Credentials base64** | "Remember me" uses btoa() | Trivially reversible | Use proper encryption or remove |
| **No CSP headers** | Missing Content-Security-Policy | XSS easier | Add CSP meta tag or header |

### MEDIUM Priority

| Gap | Current State | Risk | Recommendation |
|-----|--------------|------|----------------|
| **SQLite unencrypted** | offline.db in plaintext | Local data exposure | SQLCipher encryption |
| **RSA 2048 certs** | Self-signed, 2048-bit | Below current best practice | Upgrade to 4096-bit |
| **Private key unencrypted** | server.key stored without passphrase | Key theft | Add passphrase protection |
| **No code signing** | Electron installer unsigned | User can't verify authenticity | Sign with code-signing cert |
| **DB URL logged** | Credentials in startup log | Log file exposure | Redact password in logged URL |
| **Backups unencrypted** | pg_dump stored plaintext | Backup theft | GPG-encrypt backups |
| **File upload no whitelist** | Any file type accepted | Malicious upload | Whitelist .xlsx, .xml, .tmx only |
| **100MB upload limit** | MAX_REQUEST_SIZE = 100MB | DoS vector | Reduce to 20MB |
| **Telemetry on by default** | Sends data to central server | Privacy concern | Default to OFF, require opt-in |
| **No token refresh** | 401 → logout (reactive) | Bad UX, session drops | Proactive token refresh before expiry |

### LOW Priority / Future

| Gap | Recommendation |
|-----|---------------|
| Row-level security (RLS) in PG | Prevent cross-user data access at DB level |
| HS256 → RS256 JWT | Asymmetric signing (better for multi-service) |
| API key rotation | Auto-rotate keys periodically |
| SIEM integration | Ship audit logs to remote collector |
| Penetration testing | External security audit |
| pgcrypto for PII fields | Field-level encryption for email, names |

---

## Security Configuration Reference

### Environment Variables

```bash
# CRITICAL — Change these in production
SECRET_KEY=<random-64-char-string>
API_KEY=<random-32-char-string>
SECURITY_MODE=strict              # Fails startup if defaults unchanged

# Network
SERVER_HOST=0.0.0.0               # LAN mode (127.0.0.1 for localhost-only)
ALLOWED_IP_RANGE=10.35.0.0/16     # CIDR range for your LAN
CORS_ORIGINS=http://10.35.34.1:5173,app://.

# Database
POSTGRES_PASSWORD=<auto-generated> # Setup wizard generates this
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Features
DEV_MODE=false                    # NEVER true in production
PRODUCTION=true
TELEMETRY_ENABLED=false           # Opt-in only
ENABLE_DOCS=false                 # Disable Swagger UI
```

### Files & Permissions

| File | Contents | Permissions |
|------|----------|-------------|
| `server-config.json` | PG password, admin token, secret key | 0600 (owner only) |
| `server.key` | PG TLS private key | 0600 + icacls restricted |
| `server.crt` | PG TLS certificate | World-readable (public) |
| `path_settings.json` | Drive/branch (no secrets) | Default |
| `offline.db` | SQLite database (unencrypted) | Default |
| `security_audit.log` | Audit events | Default |

### Ports & Protocols

| Port | Service | Protocol | Binding | Auth |
|------|---------|----------|---------|------|
| 8888 | FastAPI | HTTP | 0.0.0.0 (LAN) or 127.0.0.1 | JWT Bearer |
| 8885 | Admin Dashboard | HTTP | localhost | JWT Bearer |
| 5432 | PostgreSQL | SSL (negotiated) | 0.0.0.0 | scram-sha-256 |
| /ws/socket.io | WebSocket | WS | Same as 8888 | JWT in auth param |

---

## Existing Security Documentation

| Document | Path | Covers |
|----------|------|--------|
| Network Security | `docs/reference/enterprise/06_NETWORK_SECURITY.md` | 6 security layers, firewall, PG access |
| Security Hardening | `docs/reference/security/SECURITY_HARDENING.md` | IP filtering, CIDR guide |
| Security & Logging | `docs/reference/security/SECURITY_AND_LOGGING.md` | CORS, log monitoring |
| LAN Security (Korean) | `docs/security/LAN_SERVER_SECURITY_KR.md` | Full threat model, OWASP, PIPA |
| User Management | `docs/reference/enterprise/05_USER_MANAGEMENT.md` | Roles, passwords, sessions |
| Security Architecture PDF | `docs/presentations/LocaNext_Security_Architecture.pdf` | Executive presentation |
| Auth Model (Memory) | `memory/reference_lan_server_auth_model.md` | LAN auth architecture |

---

## OWASP Top 10 Status

| # | Vulnerability | Status | Implementation |
|---|--------------|--------|----------------|
| A01 | Broken Access Control | **PROTECTED** | RBAC + JWT + IP filter + admin localhost-only |
| A02 | Cryptographic Failures | **PARTIAL** | bcrypt + PG SSL + scram-sha-256, but HTTP not HTTPS |
| A03 | Injection | **PROTECTED** | SQLAlchemy ORM, Pydantic validation, identifier regex |
| A04 | Insecure Design | **PROTECTED** | Security-by-default config, startup validation |
| A05 | Security Misconfiguration | **PARTIAL** | Warns on defaults, but doesn't enforce by default |
| A06 | Vulnerable Components | **OK** | Dependencies patched (PyJWT, FastAPI, torch) |
| A07 | Auth Failures | **PROTECTED** | Rate limiting, bcrypt, token expiry, audit logging |
| A08 | Software/Data Integrity | **PARTIAL** | No code signing, no update verification |
| A09 | Logging/Monitoring | **PROTECTED** | Audit logger, 16 event types, 3-month retention |
| A10 | SSRF | **PROTECTED** | No external URL fetching in user-facing endpoints |

---

*Generated by 5-agent parallel security audit. Last updated: 2026-04-04.*
