# LocaNext - Development Roadmap

> **IMPORTANT**: This roadmap is for the **LocaNext platform ONLY** (infrastructure, APIs, deployment).
> **New Apps**: Can ONLY be added with EXPRESS DIRECT ORDER from user.
> **Standalone Scripts**: Are tracked separately in [`NewScripts/ROADMAP.md`](RessourcesForCodingTheProject/NewScripts/ROADMAP.md).

**Last Updated**: 2025-12-01
**Project Status**: Production Ready - LIGHT Build Strategy
**Current Version**: 2512010029

---

## 📊 Current Status

### Platform Overview
- **Backend**: FastAPI with 23 tool endpoints + 16 admin endpoints
- **Frontend**: SvelteKit with modern UI + Electron desktop
- **Admin Dashboard**: Full analytics, rankings, and activity logs
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Real-time**: WebSocket progress tracking
- **Auth**: JWT-based authentication & sessions
- **AI/ML**: Korean BERT (snunlp/KR-SBERT-V40K-klueNLI-augSTS) - 447MB

### Operational Apps
1. ✅ **XLSTransfer** (App #1) - AI-powered Excel translation with Korean BERT
2. ✅ **QuickSearch** (App #2) - Multi-game dictionary search (15 languages, 4 games)
3. ✅ **KR Similar** (App #3) - Korean semantic similarity search

### Comprehensive E2E Test Coverage (2025-12-01)
| App | Unit Tests | API Tests* | Functions Tested | Status |
|-----|------------|-----------|------------------|--------|
| **KR Similar** | 18 | 9 | All 9 endpoints + core | ✅ COMPLETE |
| **XLSTransfer** | 9 | 8 | All 8 endpoints + core | ✅ COMPLETE |
| **QuickSearch** | 11 | 8 | All 8 endpoints + core | ✅ COMPLETE |
| **Total** | **38** | **25** | **63 tests** | ✅ |

*API tests require server (`RUN_API_TESTS=1`)

### Build Status
| Component | Status | Notes |
|-----------|--------|-------|
| Web Platform | ✅ Done | SvelteKit + FastAPI (localhost) |
| Desktop App | ✅ Done | Electron (Windows .exe, Linux AppImage) |
| Local Build | ✅ Done | 103MB AppImage tested |
| LIGHT Build | ✅ Ready | Post-install model download |
| Version Unification | ✅ Done | 8 files checked, all unified |

---

## ✅ Recent Progress (2025-12-01)

### CI/CD Safety Checks & Build Pipeline - COMPLETE
- ✅ **Safety Checks in CI**: Version validation, pytest, pip-audit, npm audit
- ✅ **Build Pipeline**: Safety checks must pass before Windows/Linux builds start
- ✅ **Model-Aware Tests**: Tests skip automatically when Korean BERT model unavailable (LIGHT builds)
- ✅ **Release v2512010029**: Successfully built and published to GitHub Releases

**CI/CD Pipeline Now Includes**:
1. Version unification check (all 8 files must match)
2. Python E2E tests (137 passing, model tests skip in CI)
3. Python security audit (pip-audit)
4. NPM security audit
5. Windows installer build (Inno Setup)
6. Linux AppImage build
7. Auto-publish to GitHub Releases

### Comprehensive E2E Tests for ALL Apps - COMPLETE
- ✅ **KR Similar**: 18 unit tests + 9 API tests = 27 total
- ✅ **XLSTransfer**: 9 unit tests + 8 API tests = 17 total
- ✅ **QuickSearch**: 11 unit tests + 8 API tests = 19 total
- ✅ **Total**: 38 passing unit tests, 25 API tests (require server)

**Test Files Created:**
- `tests/e2e/test_kr_similar_e2e.py` - Full E2E with real Korean BERT model
- `tests/e2e/test_xlstransfer_e2e.py` - Excel processing + AI translation
- `tests/e2e/test_quicksearch_e2e.py` - Dictionary search functionality

**Fixtures Created:**
- `tests/fixtures/sample_language_data.txt` - KR Similar test data
- `tests/fixtures/sample_dictionary.xlsx` - XLSTransfer test data
- `tests/fixtures/sample_quicksearch_data.txt` - QuickSearch test data
- `tests/fixtures/sample_to_translate.txt` - Translation test data

### Testing Protocol - COMPLETE
- ✅ Created `docs/TESTING_PROTOCOL.md` - Full autonomous testing guide
- ✅ Created `tests/archive/` - Folder for deprecated tests
- ✅ E2E tests now run with real Korean BERT model
- ✅ API tests enabled with `RUN_API_TESTS=1`

### LIGHT Build Strategy - COMPLETE
- ✅ Created `scripts/download_model_silent.bat` - Silent download for wizard
- ✅ Created `installer/locanext_light.iss` - LIGHT installer (no model bundled)
- ✅ Updated `.github/workflows/build-electron.yml` - No LFS required
- ✅ Updated `BUILD_TRIGGER.txt` - VRS-Manager format (LIGHT/FULL)

### VRS-Manager Protocol Alignment - COMPLETE
- ✅ Version unification script checks 8 files
- ✅ Manual builds only (triggers on BUILD_TRIGGER.txt change)
- ✅ Single source of truth: `version.py`
- ✅ All files unified at version `2511221939`

### How LIGHT Build Works
1. GitHub Actions builds without LFS (~100-150MB installer)
2. User runs installer → files copied
3. Post-install → `download_model_silent.bat` runs automatically
4. Model downloads from Hugging Face (official, secure)
5. App ready with AI features

---

## 🎯 Next Steps

### Priority 1: First LIGHT Build ⚡ ✅ COMPLETE
**Status**: DONE (2025-11-30)
**Release**: https://github.com/NeilVibe/LocalizationTools/releases/tag/v2511221939

- [x] Trigger build via BUILD_TRIGGER.txt
- [x] Monitor GitHub Actions for errors (fixed 5 issues)
- [x] Download and test installer artifact
- [x] Create first GitHub Release

**Issues Fixed During Build:**
1. Missing `lib/` files in git (gitignore was too broad)
2. Wrong npm script name (`electron:build` → `build:electron`)
3. Missing `favicon.ico` file (commented out)
4. Invalid `Flags: checked` in Inno Setup Tasks section

### Priority 2: KR Similar (App #3) 🔍 ✅ COMPLETE
**Status**: DONE (2025-11-30)
**Implementation**: `server/tools/kr_similar/` + `server/api/kr_similar_async.py`

#### 2.1 What Was Implemented

**Backend Modules:**
```
server/tools/kr_similar/
├── __init__.py          # Module exports
├── core.py              # Text normalization, parsing, structure adaptation
├── embeddings.py        # Korean BERT model, dictionary creation/loading
└── searcher.py          # FAISS similarity search, auto-translate
```

**API Endpoints (9 total):**
- `GET  /api/v2/kr-similar/health` - Health check
- `GET  /api/v2/kr-similar/status` - Manager status
- `GET  /api/v2/kr-similar/list-dictionaries` - Available dictionaries
- `POST /api/v2/kr-similar/create-dictionary` - Create from files
- `POST /api/v2/kr-similar/load-dictionary` - Load into memory
- `POST /api/v2/kr-similar/search` - Find similar strings
- `POST /api/v2/kr-similar/extract-similar` - Extract similar groups
- `POST /api/v2/kr-similar/auto-translate` - Auto-translate using similarity
- `DELETE /api/v2/kr-similar/clear` - Clear loaded dictionary

**Tests (34 passing):**
- Unit tests: `tests/test_kr_similar.py` (15 tests)
- E2E tests: `tests/e2e/test_kr_similar_e2e.py` (15 tests)
- API test: Included in E2E (4 API-related tests)

**Test Fixtures:**
- `tests/fixtures/sample_language_data.txt` - 20 rows mock data
- Based on real language file structure with code markers

#### 2.2 Technical Details
- **Model**: `snunlp/KR-SBERT-V40K-klueNLI-augSTS` (768-dim embeddings)
- **Index**: FAISS for fast similarity search
- **Dictionary Types**: BDO, BDM, BDC, CD, TEST
- **Embedding Types**: "split" (line-by-line) and "whole" (full text)

---

### Priority 3: Security Hardening & Network Audit 🔒
**Status**: REQUIRED BEFORE ENTERPRISE DEPLOYMENT
**Goal**: Ensure app meets corporate IT security standards (IP restrictions, encryption, audit trails)

This section provides a **step-by-step security checklist** for enterprise deployment. Each item must be verified and implemented before the app is approved by IT security teams.

---

#### 3.1 CORS & Network Origin Restrictions ✅ COMPLETE

**Status**: ✅ IMPLEMENTED (2025-12-01)

**What Was Implemented**:
- ✅ Environment-based CORS configuration (`CORS_ORIGINS` env var)
- ✅ Development mode: Allows all origins for convenience (when no env var set)
- ✅ Production mode: Only whitelisted origins accepted (when `CORS_ORIGINS` set)
- ✅ WebSocket uses same CORS config as HTTP endpoints
- ✅ Production configuration template (`.env.example`)
- ✅ Security tests (11 tests in `tests/security/test_cors_config.py`)

**Configuration (server/config.py)**:
```python
# Development (default - no env vars)
CORS_ALLOW_ALL = True  # All origins allowed for testing

# Production (set CORS_ORIGINS env var)
# Example: CORS_ORIGINS=http://192.168.11.100:5173,http://192.168.11.100:5175
CORS_ALLOW_ALL = False  # Only whitelisted origins
```

**Files Created/Modified**:
- `server/config.py` - Added CORS_ORIGINS env var support
- `server/main.py` - Updated CORS middleware to use config
- `server/utils/websocket.py` - Updated Socket.IO CORS
- `.env.example` - Production configuration template
- `docs/SECURITY_HARDENING.md` - Comprehensive security guide
- `tests/security/test_cors_config.py` - 11 security tests

**Completed Tasks**:
- [x] **3.1.1** Create `.env.example` with production configuration template
- [x] **3.1.2** Update `server/config.py` to read from environment (`CORS_ORIGINS`)
- [x] **3.1.3** Update `server/main.py` to use config-based CORS
- [x] **3.1.4** Update `server/utils/websocket.py` to use same whitelist
- [x] **3.1.5** Create security documentation (`docs/SECURITY_HARDENING.md`)
- [x] **3.1.6** Add security tests (11 tests verifying CORS behavior)

---

#### 3.2 TLS/HTTPS Encryption ⚠️ CRITICAL

**Current Status**: ❌ HTTP Only (Unencrypted)
- All traffic is unencrypted HTTP
- Sensitive data (JWT tokens, passwords) transmitted in plaintext
- Vulnerable to man-in-the-middle attacks

**Required Fix for Production**:
- [ ] **3.2.1** Create TLS configuration guide (`docs/TLS_SETUP.md`)
- [ ] **3.2.2** Add reverse proxy setup (nginx/caddy) with TLS termination
- [ ] **3.2.3** Generate/configure SSL certificates (Let's Encrypt or corporate CA)
- [ ] **3.2.4** Update server config to enforce HTTPS-only redirects
- [ ] **3.2.5** Add HSTS (HTTP Strict Transport Security) header
- [ ] **3.2.6** Configure secure WebSocket (wss://) instead of ws://
- [ ] **3.2.7** Document certificate renewal process

**Certificate Options**:
```
Option A: Let's Encrypt (free, auto-renewal)
Option B: Corporate CA (IT provides certificate)
Option C: Self-signed (testing only - NOT for production)
```

---

#### 3.3 Rate Limiting & DDoS Protection ⚠️ HIGH

**Current Status**: ❌ NO RATE LIMITING
- Any client can make unlimited requests
- Vulnerable to brute-force attacks on /login
- No protection against denial of service

**Required Implementation**:
- [ ] **3.3.1** Install `slowapi` or `fastapi-limiter` package
- [ ] **3.3.2** Add rate limiting middleware to FastAPI
- [ ] **3.3.3** Configure limits per endpoint:
  ```
  /api/v2/auth/login     → 5 requests/minute (prevent brute force)
  /api/v2/*/create-*     → 10 requests/minute (resource-intensive)
  /api/v2/*/search       → 30 requests/minute (normal usage)
  Other endpoints        → 60 requests/minute (default)
  ```
- [ ] **3.3.4** Add IP-based blocking for repeated violations
- [ ] **3.3.5** Log rate limit violations for security monitoring
- [ ] **3.3.6** Add test: Verify rate limiting blocks excessive requests

---

#### 3.4 JWT Token Security ⚠️ HIGH

**Current Status**: ⚠️ PARTIAL (Development Keys)
```python
# server/config.py - CURRENT
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # OK
```

**Security Assessment**:
- ✅ JWT implementation uses PyJWT + bcrypt (industry standard)
- ✅ Passwords hashed with bcrypt (secure)
- ❌ Default SECRET_KEY is weak and public
- ❌ No token refresh mechanism
- ❌ No token revocation/blacklist

**Required Fixes**:
- [ ] **3.4.1** Enforce strong SECRET_KEY in production (min 256-bit)
- [ ] **3.4.2** Add startup check that fails if using default SECRET_KEY
- [ ] **3.4.3** Implement refresh token mechanism
- [ ] **3.4.4** Add token blacklist for logout/revocation
- [ ] **3.4.5** Add JWT expiry validation in all protected endpoints
- [ ] **3.4.6** Log all authentication events (login, logout, token refresh)

---

#### 3.5 Input Validation & Injection Prevention ⚠️ HIGH

**Current Status**: ⚠️ PARTIAL
- ✅ SQLAlchemy ORM prevents SQL injection (parameterized queries)
- ✅ Pydantic schemas validate API input types
- ❌ No XSS sanitization for user-provided text
- ❌ No file type validation beyond extension
- ❌ No content-type verification for uploads

**Required Fixes**:
- [ ] **3.5.1** Add HTML/XSS sanitization for all text inputs
- [ ] **3.5.2** Implement strict file upload validation:
  - Verify MIME type matches extension
  - Scan file headers (magic bytes)
  - Set maximum file size limits
  - Whitelist allowed extensions (.xlsx, .xls, .txt only)
- [ ] **3.5.3** Add path traversal prevention for file operations
- [ ] **3.5.4** Implement Content-Security-Policy headers
- [ ] **3.5.5** Add test: Verify XSS payloads are sanitized
- [ ] **3.5.6** Add test: Verify malicious file uploads are rejected

---

#### 3.6 Audit Logging & Monitoring ⚠️ MEDIUM

**Current Status**: ⚠️ PARTIAL
- ✅ HTTP request logging (method, path, duration)
- ✅ Database operation logging
- ❌ No security-specific audit log
- ❌ No failed login tracking
- ❌ No suspicious activity detection

**Required Implementation**:
- [ ] **3.6.1** Create security audit log table in database
- [ ] **3.6.2** Log all authentication events:
  - Successful logins (user, IP, timestamp)
  - Failed logins (user, IP, timestamp, reason)
  - Password changes
  - Token refreshes
  - Logouts
- [ ] **3.6.3** Log all admin operations (user creation, deletion, permission changes)
- [ ] **3.6.4** Implement failed login lockout (5 failures = 15 min lockout)
- [ ] **3.6.5** Add security event alerting (email/webhook on suspicious activity)
- [ ] **3.6.6** Create audit log viewer in admin dashboard

---

#### 3.7 Secrets Management ✅ COMPLETE

**Status**: ✅ IMPLEMENTED (2025-12-01)

**What Was Implemented**:
- ✅ `.env.example` created with production configuration template
- ✅ Secret generation commands documented
- ✅ Environment-based configuration for all sensitive values
- ✅ Security documentation includes secrets management

**Files Created**:
- `.env.example` - Production configuration template with:
  - SECRET_KEY generation command
  - API_KEY generation command
  - Database credentials section
  - All environment variable documentation

**Completed Tasks**:
- [x] **3.7.1** Secrets use environment variables (already implemented)
- [x] **3.7.2** Create `.env.example` with placeholder values
- [x] **3.7.3** Document secret generation process in `docs/SECURITY_HARDENING.md`

**Remaining (Future)**:
- [ ] **3.7.4** Add startup validation for required environment variables
- [ ] **3.7.5** Implement secret rotation guide for production

---

#### 3.8 Network Binding & Firewall ⚠️ MEDIUM

**Current Status**: ⚠️ RISKY
```python
# server/config.py - CURRENT
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")  # Binds to ALL interfaces!
```

**Security Risk**: Binding to `0.0.0.0` exposes server to ALL network interfaces.

**Required Fixes**:
- [ ] **3.8.1** Change default to `127.0.0.1` (localhost only)
- [ ] **3.8.2** Document firewall rules for production deployment
- [ ] **3.8.3** Create network architecture diagram showing allowed traffic flows
- [ ] **3.8.4** Add deployment checklist with firewall configuration steps

---

#### 3.9 Dependency Security (CI/CD) ✅ IMPLEMENTED

**Current Status**: ✅ DONE (Added 2025-12-01)
- ✅ `pip-audit` runs in CI pipeline
- ✅ `npm audit` runs in CI pipeline
- ✅ Security audits run before every build
- ✅ Build fails if critical vulnerabilities found

**Maintenance Tasks**:
- [ ] **3.9.1** Schedule weekly dependency updates
- [ ] **3.9.2** Create process for reviewing/approving dependency updates
- [ ] **3.9.3** Pin exact versions in requirements.txt for reproducibility

---

#### 3.10 Security Testing in CI ⚠️ IN PROGRESS

**Current Status**: ⚠️ PARTIAL (Started 2025-12-01)
- ✅ Unit tests run in CI
- ✅ Dependency audits run in CI
- ✅ Security test suite created (`tests/security/`)
- ✅ CORS configuration tests (11 tests)
- ❌ No penetration testing yet

**Completed**:
- [x] **3.10.1** Add security test suite (`tests/security/`)
- [x] **3.10.1a** CORS configuration tests (11 tests)

**Remaining**:
- [ ] **3.10.2** Test: Authentication bypass attempts
- [ ] **3.10.3** Test: SQL injection attempts (should all fail)
- [ ] **3.10.4** Test: XSS injection attempts (should all fail)
- [ ] **3.10.5** Test: Path traversal attempts (should all fail)
- [ ] **3.10.6** Test: Rate limiting enforcement
- [ ] **3.10.7** Add OWASP ZAP or similar automated scan to CI (optional)

---

#### 3.11 Data Protection & Privacy ⚠️ LOW

**Current Status**: ⚠️ BASIC
- ✅ Passwords are hashed (bcrypt)
- ❌ No data encryption at rest
- ❌ No PII handling policy
- ❌ No data retention policy

**Tasks for Compliance** (if handling sensitive data):
- [ ] **3.11.1** Document what data is collected and stored
- [ ] **3.11.2** Implement database encryption at rest (if required)
- [ ] **3.11.3** Create data retention policy
- [ ] **3.11.4** Add data export/deletion functionality for GDPR compliance

---

#### Security Checklist Summary

| Category | Status | Priority | Effort |
|----------|--------|----------|--------|
| 3.1 CORS/Origin Restrictions | ✅ Done | CRITICAL | Complete |
| 3.2 TLS/HTTPS | ❌ Not Done | CRITICAL | 4-8 hours |
| 3.3 Rate Limiting | ❌ Not Done | HIGH | 2-4 hours |
| 3.4 JWT Security | ⚠️ Partial | HIGH | 4-6 hours |
| 3.5 Input Validation | ⚠️ Partial | HIGH | 4-6 hours |
| 3.6 Audit Logging | ⚠️ Partial | MEDIUM | 4-8 hours |
| 3.7 Secrets Management | ✅ Done | MEDIUM | Complete |
| 3.8 Network Binding | ⚠️ Risky | MEDIUM | 1-2 hours |
| 3.9 Dependency Security | ✅ Done | MEDIUM | Maintenance |
| 3.10 Security Testing | ⚠️ Partial | MEDIUM | 4-8 hours |
| 3.11 Data Protection | ⚠️ Basic | LOW | 4-8 hours |

**Progress**: 3/11 complete (3.1, 3.7, 3.9)
**Remaining Effort**: ~25-50 hours for full enterprise security compliance

---

### Priority 4: UI/UX Enhancements 🎨
**Status**: Planned
**Goal**: Add Settings menu with About and Preferences

#### 4.1 Settings Dropdown Menu
Add a settings dropdown in the header with:

**About Section:**
- [ ] App name and logo
- [ ] Current version (from version.py)
- [ ] Build date
- [ ] Repository link
- [ ] Update notification (compare local vs latest release)
- [ ] "Check for Updates" button

**Preferences Section:**
- [ ] **Theme**: Dark mode / Light mode toggle
- [ ] **Language**: UI language selection (English, Korean, etc.)
- [ ] **Notifications**: Enable/disable desktop notifications
- [ ] **Auto-update**: Enable/disable auto-update check
- [ ] **Data**: Clear cache, reset preferences

#### 4.2 Implementation Plan
```
Settings Menu Structure:
├── About
│   ├── Version: 2511221939
│   ├── Build: 2025-11-30
│   ├── Check for Updates [button]
│   └── GitHub Repository [link]
│
└── Preferences
    ├── Appearance
    │   ├── Theme: [Dark / Light / System]
    │   └── Accent Color: [dropdown]
    ├── Language
    │   └── UI Language: [English / Korean / ...]
    ├── Notifications
    │   └── Desktop Notifications: [toggle]
    └── Advanced
        ├── Clear Cache [button]
        └── Reset to Defaults [button]
```

#### 4.3 Update Warning System
- Fetch latest release from GitHub API
- Compare version numbers
- Show notification badge on Settings icon if update available
- Display update dialog with changelog

### Priority 5: Admin Dashboard Authentication
**Status**: Pending
- [ ] Add login page for admin dashboard
- [ ] Protect admin routes with auth middleware
- [ ] Role-based access control

### Priority 6: Export Functionality
**Status**: Pending
- [ ] Export rankings to CSV/Excel
- [ ] Export statistics to PDF
- [ ] Download buttons in dashboard

---

## 📋 Build Protocol (VRS-Manager Style)

### Before Building
```bash
# 1. Update version in version.py (if needed)
# 2. Run version unification check
python3 scripts/check_version_unified.py

# 3. If all green ✅, proceed
# 4. Add build trigger
echo "Build LIGHT v2511221939" >> BUILD_TRIGGER.txt

# 5. Commit and push
git add -A && git commit -m "Trigger LIGHT build" && git push
```

### Build Triggers
- `Build LIGHT v[version]` → LIGHT installer (~100-150MB)
- `Build FULL v[version]` → FULL installer (~2GB) [needs LFS quota]

---

## ✅ Completed Milestones

### Core Platform - 100% Complete
- ✅ Backend: FastAPI with 39 endpoints (23 tool + 16 admin)
- ✅ Frontend: SvelteKit + Carbon Design System
- ✅ Admin Dashboard: Analytics, rankings, activity logs
- ✅ Database: SQLite with async SQLAlchemy
- ✅ WebSocket: Real-time progress tracking
- ✅ Auth: JWT-based authentication

### Apps - 3 Complete
- ✅ XLSTransfer (App #1) - AI-powered translation with Korean BERT
- ✅ QuickSearch (App #2) - Multi-game dictionary search
- ✅ KR Similar (App #3) - Korean semantic similarity search (34 tests)

### Distribution Infrastructure - 100% Complete
- ✅ Git LFS configured (model tracked)
- ✅ Version unification (8 files, VRS-Manager protocol)
- ✅ Security audit (no secrets in repo)
- ✅ Model download scripts (Python + batch + silent)
- ✅ Local Electron build tested (103MB AppImage)
- ✅ GitHub Actions workflow (LIGHT build ready)
- ✅ Inno Setup installer (LIGHT version)
- ✅ BUILD_TRIGGER.txt (manual build control)

---

## 🏗️ Architecture Overview

### Technology Stack
- **Frontend**: SvelteKit 2.0 + Carbon Design System
- **Backend**: FastAPI + SQLAlchemy 2.0 (async)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **AI/ML**: Korean BERT via sentence-transformers
- **Desktop**: Electron
- **Build**: Electron-builder + Inno Setup
- **CI/CD**: GitHub Actions (manual trigger)

### Project Structure
```
LocalizationTools/
├── locaNext/              # Frontend (SvelteKit + Electron)
├── adminDashboard/        # Admin UI (SvelteKit)
├── server/                # Backend (FastAPI)
│   ├── api/               # API endpoints
│   ├── database/          # SQLAlchemy models
│   ├── tools/             # Tool implementations
│   └── utils/             # Utilities
├── models/                # AI models (LFS tracked)
│   └── kr-sbert/          # Korean BERT (447MB)
├── scripts/               # Build & setup scripts
├── installer/             # Inno Setup scripts
├── tests/                 # Test suite
└── docs/                  # Documentation
```

---

## 🚀 Quick Start

### Development Mode
```bash
# Terminal 1: Backend
python3 server/main.py
# → http://localhost:8888

# Terminal 2: Frontend
cd locaNext && npm run dev
# → http://localhost:5173

# Terminal 3: Admin Dashboard
cd adminDashboard && npm run dev
# → http://localhost:5174
```

### Access Points
- **Main App**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5174
- **API Docs**: http://localhost:8888/docs
- **Health Check**: http://localhost:8888/health

### Default Credentials
```
Username: admin
Password: admin123
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` | Master navigation hub |
| `Roadmap.md` | This file - status & plans |
| `docs/ADD_NEW_APP_GUIDE.md` | Adding new tools |
| `docs/BUILD_AND_DISTRIBUTION.md` | Build process (LIGHT strategy) |
| `docs/TESTING_GUIDE.md` | Testing procedures |

---

## 🔑 Key Principles

1. **Backend is Flawless** - Never modify core backend without confirmed bug
2. **BaseToolAPI Pattern** - All new apps use shared base class
3. **Real-time Progress** - Every long operation emits WebSocket updates
4. **Comprehensive Logging** - All operations logged for debugging
5. **LIGHT-First Builds** - No bundled models, download post-install
6. **Version Unification** - All 8 files must match before build

---

**Last Updated**: 2025-12-01
**Current Version**: 2512010029
**Current Focus**: Security Hardening & Enterprise Compliance
**Next Milestone**: CORS restrictions, TLS/HTTPS, Rate limiting, Audit logging
**Platform Status**: 3 Apps Complete - All Operational
**Test Status**: 137 passing + 25 skipped (API tests require server)
**Build Status**: ✅ v2512010029 successfully released with safety checks
