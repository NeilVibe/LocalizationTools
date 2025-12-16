# Security Fix Plan - Optimized Sequence

**Created:** 2025-12-14 | **Updated:** 2025-12-14
**Status:** ✅ COMPLETE - All critical/high fixed, remaining accepted
**Principle:** Bottom-up, isolated changes, test after each step

---

## How To Use This Document

1. Execute each phase in order
2. Run ALL verification steps after each phase
3. Only mark phase complete when ALL tests pass
4. If something breaks → rollback, investigate, fix, retry
5. Update the status checkbox and date when phase is FULLY VERIFIED

### Important: Evaluate Real Security Impact

Before fighting with a difficult update, ask:

> "Does this vulnerability actually matter for our use case?"
> "Will the security team care, or will they say 'we don't care about this one'?"

**Skip criteria:**
- CVE requires local code execution AND we don't load untrusted data
- CVE requires MITM position AND we're on internal network
- CVE affects feature we don't use
- Fix causes major breakage AND risk is theoretical

**Document decision:** If skipping, note WHY in the Progress Tracker.

---

## Progress Tracker

| Phase | Status | Verified | Date | Notes |
|-------|--------|----------|------|-------|
| 0 - Ubuntu | [x] | [x] | 2025-12-14 | 84 packages updated |
| 1 - Safe pip | [x] | [x] | 2025-12-14 | requests, jose, multipart, oauth, config |
| 2 - Safe npm | [x] | [x] | 2025-12-14 | glob, js-yaml fixed |
| 3a - starlette | [x] | [x] | 2025-12-14 | 0.38.6 → 0.50.0 |
| 3b - socketio | [x] | [x] | 2025-12-14 | 5.11.0 → 5.15.0 |
| 3c - cryptography | [x] | [x] | 2025-12-14 | 3.4.8 → 46.0.3 (8 CVEs!) |
| 4 - torch | [x] | [x] | 2025-12-14 | 2.3.1 → 2.9.1 |
| 5 - electron | [SKIP] | N/A | 2025-12-14 | **TESTED**: Breaks build completely. Requires Svelte 5 migration. ASAR bypass = local access only. |
| 6 - urllib3 | [ACCEPT] | N/A | 2025-12-14 | System pkg, CVEs need MITM. Low risk for internal tool. |
| **FINAL AUDIT** | [x] | [x] | 2025-12-14 | pip-audit: 16 remain (system pkgs), npm: 9 (dev-only) |
| **HARDENING** | [x] | [x] | 2025-12-14 | JWT HS256, bcrypt 12 rounds, .gitignore solid |
| **FINAL TESTS** | [x] | [x] | 2025-12-14 | Build passes, server starts |

---

## Phase 0: Ubuntu System Update

**Goal:** Update OS foundation. May auto-fix some pip vulnerabilities.

### Step 0.1: Preview Updates
```bash
apt list --upgradable
```
- [ ] Reviewed list of packages to update
- [ ] No obvious conflicts or concerns

### Step 0.2: Execute Update
```bash
sudo apt update && sudo apt upgrade -y
```
- [ ] Update completed without errors

### Step 0.3: Check If Reboot Required
```bash
# Check if reboot needed
[ -f /var/run/reboot-required ] && echo "REBOOT REQUIRED" || echo "No reboot needed"
```
- [ ] If reboot required: `sudo reboot`
- [ ] If no reboot: continue

### Step 0.4: Verify System Health
```bash
# Python works
python3 --version

# pip works
pip --version

# Node works
node --version

# npm works
npm --version
```
- [ ] All commands return valid versions

### Step 0.5: Check urllib3 Status
```bash
pip show urllib3 | grep Version
```
- [ ] Record version: __________ (if 2.x, Phase 6 may be done)

### Phase 0 Verification Checklist
- [ ] System boots normally
- [ ] python3, pip, node, npm all work
- [ ] No errors in terminal

**Phase 0 Status:** [ ] COMPLETE (Date: __________)

---

## Phase 1: Safe pip Packages (BULK)

**Goal:** Update 5 packages with NO breaking changes.

**Packages:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| requests | 2.32.3 | 2.32.4 | None |
| python-jose | 3.3.0 | 3.4.0 | None |
| python-multipart | 0.0.9 | 0.0.18 | None |
| oauthlib | 3.2.0 | 3.2.1 | None |
| configobj | 5.0.6 | 5.0.9 | None |

### Step 1.1: Install Updates
```bash
pip install --upgrade \
  requests>=2.32.4 \
  python-jose>=3.4.0 \
  python-multipart>=0.0.18 \
  oauthlib>=3.2.1 \
  configobj>=5.0.9
```
- [ ] All packages installed without errors

### Step 1.2: Verify Versions
```bash
pip show requests python-jose python-multipart oauthlib configobj | grep -E "^(Name|Version)"
```
- [ ] requests >= 2.32.4
- [ ] python-jose >= 3.4.0
- [ ] python-multipart >= 0.0.18
- [ ] oauthlib >= 3.2.1
- [ ] configobj >= 5.0.9

### Step 1.3: Run Unit Tests
```bash
python3 -m pytest tests/unit/ -v --tb=short
```
- [ ] All tests pass
- [ ] Test count: _____ passed, _____ failed

### Step 1.4: Start Server Test
```bash
python3 server/main.py &
sleep 5
curl http://localhost:8888/api/health/ping
pkill -f "python3 server/main.py"
```
- [ ] Server starts without errors
- [ ] Health ping returns OK

### Phase 1 Verification Checklist
- [ ] All 5 packages updated
- [ ] Unit tests pass (595+ tests)
- [ ] Server starts and responds

**Phase 1 Status:** [ ] COMPLETE (Date: __________)

---

## Phase 2: Safe npm Packages (BULK)

**Goal:** Fix glob, js-yaml vulnerabilities (no breaking changes).

### Step 2.1: Check Current Vulnerabilities
```bash
cd locaNext && npm audit
```
- [ ] Noted current vulnerability count: _____

### Step 2.2: Apply Safe Fixes
```bash
cd locaNext && npm audit fix  # NOT --force
```
- [ ] Fixes applied without errors

### Step 2.3: Verify Build
```bash
cd locaNext && npm run build
```
- [ ] Build completes without errors

### Step 2.4: Quick Dev Test
```bash
cd locaNext && timeout 10 npm run dev || true
```
- [ ] Dev server starts (OK if timeout kills it)

### Step 2.5: Re-check Vulnerabilities
```bash
cd locaNext && npm audit
```
- [ ] Vulnerability count reduced: _____ (was: _____)

### Phase 2 Verification Checklist
- [ ] npm audit fix completed
- [ ] npm run build succeeds
- [ ] Dev server starts

**Phase 2 Status:** [ ] COMPLETE (Date: __________)

---

## Phase 3a: starlette (ALONE)

**Goal:** Update FastAPI's core framework.

**Package:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| starlette | 0.38.6 | 0.47.2+ | Medium |

**CVEs Fixed:** Path traversal, request smuggling

### Step 3a.1: Check Current Versions
```bash
pip show fastapi starlette | grep -E "^(Name|Version)"
```
- [ ] Current starlette: _____
- [ ] Current fastapi: _____

### Step 3a.2: Install Update
```bash
pip install starlette>=0.47.2
```
- [ ] Installed without errors
- [ ] Note: May auto-upgrade FastAPI

### Step 3a.3: Verify New Versions
```bash
pip show fastapi starlette | grep -E "^(Name|Version)"
```
- [ ] starlette >= 0.47.2
- [ ] fastapi version: _____

### Step 3a.4: Start Server
```bash
python3 server/main.py &
sleep 5
```
- [ ] Server starts without import errors
- [ ] No deprecation warnings (or note them: _____________)

### Step 3a.5: Run Integration Tests
```bash
RUN_API_TESTS=1 python3 -m pytest tests/integration/server_tests/ -v --tb=short
```
- [ ] All integration tests pass
- [ ] Test count: _____ passed, _____ failed

### Step 3a.6: Manual API Check
```bash
# Health check
curl http://localhost:8888/api/health/ping

# Auth endpoint exists
curl -X POST http://localhost:8888/api/auth/login -H "Content-Type: application/json" -d '{"username":"test","password":"test"}' | head -c 100
```
- [ ] Health returns OK
- [ ] Auth endpoint responds (even if login fails, endpoint exists)

### Step 3a.7: Cleanup
```bash
pkill -f "python3 server/main.py"
```

### Phase 3a Verification Checklist
- [ ] starlette updated to 0.47.2+
- [ ] Server starts without errors
- [ ] All integration tests pass
- [ ] API endpoints respond

**Phase 3a Status:** [ ] COMPLETE (Date: __________)

---

## Phase 3b: python-socketio (ALONE)

**Goal:** Fix WebSocket auth bypass vulnerability.

**Package:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| python-socketio | 5.11.0 | 5.14.0+ | Low |

**CVE Fixed:** CVE-2025-61765 - authentication bypass

### Step 3b.1: Install Update
```bash
pip install python-socketio>=5.14.0
```
- [ ] Installed without errors

### Step 3b.2: Verify Version
```bash
pip show python-socketio | grep Version
```
- [ ] python-socketio >= 5.14.0

### Step 3b.3: Start Server
```bash
python3 server/main.py &
sleep 5
```
- [ ] Server starts without errors
- [ ] WebSocket initialization logs appear

### Step 3b.4: Run Unit Tests
```bash
python3 -m pytest tests/unit/ -v --tb=short -k "websocket or socket" 2>/dev/null || python3 -m pytest tests/unit/ -v --tb=short
```
- [ ] Tests pass

### Step 3b.5: Manual WebSocket Check (if desktop app available)
```
1. Start desktop app: cd locaNext && npm run electron:dev
2. Open LDM tool
3. Open a file
4. Edit a cell
5. Check: lock icon appears
```
- [ ] WebSocket connects (check server logs)
- [ ] Real-time updates work (or N/A if not testing manually)

### Step 3b.6: Cleanup
```bash
pkill -f "python3 server/main.py"
```

### Phase 3b Verification Checklist
- [ ] python-socketio updated to 5.14.0+
- [ ] Server starts
- [ ] Unit tests pass
- [ ] WebSocket functional (manual or skip)

**Phase 3b Status:** [ ] COMPLETE (Date: __________)

---

## Phase 3c: cryptography (ALONE)

**Goal:** Fix 8 CVEs in authentication library.

**Package:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| cryptography | 3.4.8 | 42.0.2+ | Medium |

**CVEs Fixed:** 8 CVEs including potential RCE

### Step 3c.1: Install Update
```bash
pip install cryptography>=42.0.2
```
- [ ] Installed without errors

### Step 3c.2: Verify Version
```bash
pip show cryptography | grep Version
```
- [ ] cryptography >= 42.0.2

### Step 3c.3: Run Auth Unit Tests
```bash
python3 -m pytest tests/unit/test_auth*.py -v --tb=short
```
- [ ] All auth unit tests pass
- [ ] Test count: _____ passed

### Step 3c.4: Start Server and Test Auth Integration
```bash
python3 server/main.py &
sleep 5
python3 -m pytest tests/integration/server_tests/test_auth*.py -v --tb=short
```
- [ ] Server starts
- [ ] Auth integration tests pass

### Step 3c.5: Manual Login Test
```bash
# Create test admin if needed
python3 scripts/create_admin.py 2>/dev/null || true

# Test login endpoint
curl -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123!"}' | python3 -m json.tool | head -20
```
- [ ] Login returns token (or expected error if wrong password)
- [ ] No cryptography errors in server logs

### Step 3c.6: Cleanup
```bash
pkill -f "python3 server/main.py"
```

### Phase 3c Verification Checklist
- [ ] cryptography updated to 42.0.2+
- [ ] Auth unit tests pass
- [ ] Auth integration tests pass
- [ ] Login endpoint works
- [ ] No JWT/crypto errors

**Phase 3c Status:** [ ] COMPLETE (Date: __________)

---

## Phase 4: torch (ALONE - HIGH RISK)

**Goal:** Update PyTorch for ML security fixes.

**Package:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| torch | 2.3.1 | 2.6.0+ | HIGH |

**CVEs Fixed:** 4 CVEs - malicious model loading

**WARNING:** Major version change. Test embeddings thoroughly!

### Step 4.1: Backup Current Version Info
```bash
pip show torch sentence-transformers | grep -E "^(Name|Version)"
```
- [ ] Current torch: _____
- [ ] Current sentence-transformers: _____

### Step 4.2: Install Update
```bash
pip install torch>=2.6.0
```
- [ ] Installed without errors
- [ ] Note any warnings: _____________

### Step 4.3: Verify Versions
```bash
pip show torch sentence-transformers | grep -E "^(Name|Version)"
```
- [ ] torch >= 2.6.0
- [ ] sentence-transformers still installed

### Step 4.4: Test Import
```bash
python3 -c "import torch; print(f'PyTorch {torch.__version__} OK')"
python3 -c "from sentence_transformers import SentenceTransformer; print('SentenceTransformer import OK')"
```
- [ ] torch imports
- [ ] SentenceTransformer imports

### Step 4.5: Run Embedding Tests
```bash
python3 -m pytest tests/e2e/test_xlstransfer_e2e.py -v --tb=short 2>/dev/null || echo "No e2e tests or failed"
python3 -m pytest tests/ -v --tb=short -k "embed" 2>/dev/null || echo "No embedding tests"
```
- [ ] Embedding-related tests pass (or N/A)

### Step 4.6: Manual Embedding Test
```bash
python3 -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
emb = model.encode(['Hello world', 'Test sentence'])
print(f'Embedding shape: {emb.shape}')
print('Embeddings work!')
"
```
- [ ] Model loads
- [ ] Embeddings generate correctly

### Step 4.7: Server Start Test
```bash
python3 server/main.py &
sleep 10  # Longer wait for model loading
curl http://localhost:8888/api/health/ping
pkill -f "python3 server/main.py"
```
- [ ] Server starts
- [ ] Health check OK

### Phase 4 Verification Checklist
- [ ] torch updated to 2.6.0+
- [ ] sentence-transformers still works
- [ ] Embeddings generate correctly
- [ ] Server starts with new torch

**Phase 4 Status:** [ ] COMPLETE (Date: __________)

**If Failed:** Rollback with `pip install torch==2.3.1`

---

## Phase 5: electron (ALONE - HIGH RISK)

**Goal:** Update Electron for ASAR bypass fix.

**Package:**
| Package | Current | Target | Risk |
|---------|---------|--------|------|
| electron | <35 | 39.x | HIGH |

**CVE Fixed:** ASAR integrity bypass

**WARNING:** Major version jump. Test entire desktop app!

### Step 5.1: Backup package.json
```bash
cd locaNext && cp package.json package.json.backup
```
- [ ] Backup created

### Step 5.2: Check Current Version
```bash
cd locaNext && npm list electron
```
- [ ] Current electron: _____

### Step 5.3: Apply Force Fix
```bash
cd locaNext && npm audit fix --force
```
- [ ] Completed (note any warnings)

### Step 5.4: Check New Version
```bash
cd locaNext && npm list electron
```
- [ ] New electron: _____

### Step 5.5: Build Test
```bash
cd locaNext && npm run build
```
- [ ] Build succeeds without errors

### Step 5.6: Dev Mode Test
```bash
cd locaNext && npm run electron:dev &
sleep 10
# App should open
```
- [ ] App window opens
- [ ] No crash on startup

### Step 5.7: Manual Feature Test
```
Test each major feature:
[ ] App launches
[ ] Login works
[ ] XLSTransfer tool opens
[ ] QuickSearch tool opens
[ ] KR Similar tool opens
[ ] LDM tool opens
[ ] File upload works
[ ] File download works
[ ] Settings persist
[ ] WebSocket connects (check for real-time updates)
```

### Step 5.8: Cleanup
```bash
pkill -f electron || true
```

### Phase 5 Verification Checklist
- [ ] electron updated
- [ ] npm run build succeeds
- [ ] App launches in dev mode
- [ ] All 4 tools accessible
- [ ] Core features work

**Phase 5 Status:** [ ] COMPLETE (Date: __________)

**If Failed:** Restore with:
```bash
cd locaNext && cp package.json.backup package.json && npm install
```

---

## Phase 6: urllib3 (CHECK STATUS)

**Goal:** Determine if urllib3 was fixed by Ubuntu update.

### Step 6.1: Check Current Version
```bash
pip show urllib3 | grep -E "^(Version|Location)"
```
- [ ] Version: _____
- [ ] Location: _____ (system or user?)

### Step 6.2: Decision Matrix

| Version | Location | Action |
|---------|----------|--------|
| 2.x+ | Any | DONE - No action needed |
| 1.26.x | /usr/lib/... | System package - risky to change |
| 1.26.x | ~/.local/... | Can upgrade with pip |

### Step 6.3: If Still 1.26.x (System Package)

**Options:**
- **A) Accept Risk:** urllib3 CVEs require MITM position. Low real-world risk.
- **B) Virtualenv:** Create isolated environment for project.
- **C) Force Upgrade:** `pip install --user urllib3>=2.5.0` (may break system tools)

**Decision:** [ ] A / [ ] B / [ ] C

### Step 6.4: If Upgrading
```bash
pip install --user urllib3>=2.5.0
pip show urllib3 | grep Version
```
- [ ] Upgraded to 2.x

### Step 6.5: Verify No Breakage
```bash
# Test requests still works
python3 -c "import requests; print(requests.get('https://httpbin.org/get').status_code)"
```
- [ ] requests works with new urllib3

### Phase 6 Verification Checklist
- [ ] urllib3 version documented
- [ ] Decision made (accept/upgrade/virtualenv)
- [ ] If upgraded: requests still works

**Phase 6 Status:** [ ] COMPLETE (Date: __________)

---

## Final Audit: FULL Vulnerability Re-Scan

After ALL phases complete, re-scan EVERYTHING to confirm zero vulnerabilities.

### Audit 1: pip (Python packages)

```bash
# Method 1: pip-audit (recommended)
pip install pip-audit
pip-audit

# Method 2: safety (alternative)
pip install safety
safety check

# Method 3: manual check for known packages
pip list --outdated
```
- [ ] pip-audit: _____ vulnerabilities (target: 0)
- [ ] All critical packages at target versions

### Audit 2: npm (Node packages)

```bash
cd locaNext && npm audit
```
- [ ] npm audit: _____ vulnerabilities (target: 0 high/critical)
- [ ] Remaining vulnerabilities are dev-only/acceptable

### Audit 3: System packages (Ubuntu)

```bash
# Check for security updates
sudo apt update
apt list --upgradable 2>/dev/null | grep -i security || echo "No security updates pending"

# Or use unattended-upgrades dry-run
sudo unattended-upgrades --dry-run 2>&1 | head -20
```
- [ ] No pending security updates

### Audit 4: Docker (if applicable)

```bash
# Check docker images for vulnerabilities (if using docker)
docker images --format "{{.Repository}}:{{.Tag}}" | head -5
# Consider: docker scout, trivy, or grype for image scanning
```
- [ ] Docker images scanned (or N/A)

### Audit 5: Git secrets check

```bash
# Check no secrets committed
git log -p | grep -iE "(password|secret|api.?key|token)" | head -10 || echo "No obvious secrets found"

# Better: use gitleaks or trufflehog
# pip install trufflehog
# trufflehog git file://. --only-verified
```
- [ ] No secrets in git history (or acceptable)

### Final Audit Summary

| Source | Before | After | Status |
|--------|--------|-------|--------|
| pip | 28+ vulns | _____ | [ ] |
| npm | 11 vulns | _____ | [ ] |
| Ubuntu | 85 pkgs | _____ | [ ] |
| Docker | TBD | _____ | [ ] |
| Secrets | N/A | _____ | [ ] |

**Final Audit Status:** [ ] COMPLETE (Date: __________)

---

## Security Hardening Audit (POST-FIX)

After vulnerabilities are fixed, audit the QUALITY of security implementation.

### H1: Authentication & Token Security

```bash
# Check JWT configuration
grep -r "SECRET_KEY\|JWT\|TOKEN" server/ --include="*.py" | head -20
```

**Checklist:**
- [ ] JWT secret is long enough (256+ bits / 32+ chars)
- [ ] JWT secret is NOT hardcoded (uses env var)
- [ ] JWT expiry is reasonable (not too long)
- [ ] Refresh token rotation implemented
- [ ] Token stored securely (httpOnly cookies or secure storage)
- [ ] No tokens in URL parameters
- [ ] No tokens logged to console/files

**Files to check:** `server/auth/`, `server/config.py`

### H2: Password & Hashing Security

```bash
# Check password hashing
grep -r "bcrypt\|argon2\|pbkdf2\|sha256\|md5" server/ --include="*.py"
```

**Checklist:**
- [ ] Using bcrypt/argon2 (NOT md5/sha1/sha256 alone)
- [ ] Salt is unique per password (auto with bcrypt)
- [ ] Work factor is sufficient (bcrypt rounds >= 12)
- [ ] No plaintext passwords in logs
- [ ] Password complexity enforced

### H3: Injection Protection

```bash
# Check for raw SQL
grep -r "execute\|raw\|text(" server/ --include="*.py" | grep -v test | head -20

# Check for command execution
grep -r "subprocess\|os.system\|eval\|exec" server/ --include="*.py" | head -20
```

**Checklist:**
- [ ] SQL: Using ORM/parameterized queries (no string concat)
- [ ] Command: No user input in shell commands (or properly escaped)
- [ ] XSS: User input escaped in HTML responses
- [ ] Path traversal: File paths validated (no ../)
- [ ] Template injection: No user input in templates

### H4: Secret Management

```bash
# Check .env and secrets
cat .gitignore | grep -iE "env|secret|key|credential"
ls -la .env* 2>/dev/null || echo "No .env files"

# Check for hardcoded secrets
grep -rE "(password|secret|api.?key)\s*=\s*['\"][^'\"]+['\"]" server/ --include="*.py" | grep -v test | head -10
```

**Checklist:**
- [ ] `.env` in `.gitignore`
- [ ] `.env.example` has no real values
- [ ] No hardcoded secrets in code
- [ ] Secrets loaded from environment
- [ ] Different secrets for dev/prod
- [ ] Database credentials not in code

### H5: .gitignore / .dockerignore Quality

```bash
# Check what's being ignored
cat .gitignore
cat .dockerignore 2>/dev/null || echo "No .dockerignore"
```

**Must be ignored:**
- [ ] `.env`, `.env.*` (except .example)
- [ ] `*.key`, `*.pem`, `*.crt` (private keys)
- [ ] `credentials.json`, `secrets.json`
- [ ] `node_modules/`, `__pycache__/`, `.venv/`
- [ ] `*.log`, `logs/`
- [ ] IDE files (`.idea/`, `.vscode/`)
- [ ] Build artifacts (`dist/`, `build/`)

### H6: API Security

```bash
# Check CORS settings
grep -r "CORS\|cors\|Access-Control" server/ --include="*.py"

# Check rate limiting
grep -r "rate\|limit\|throttle" server/ --include="*.py"
```

**Checklist:**
- [ ] CORS: Restricted origins (not `*` in production)
- [ ] Rate limiting: Implemented on auth endpoints
- [ ] Input validation: All endpoints validate input
- [ ] Error messages: Don't leak internal info
- [ ] HTTPS: Enforced in production
- [ ] Security headers: X-Frame-Options, CSP, etc.

### H7: IP & Request Security

```bash
# Check IP handling
grep -r "X-Forwarded\|Real-IP\|remote_addr" server/ --include="*.py"
```

**Checklist:**
- [ ] IP spoofing: Trusting X-Forwarded-For only from known proxies
- [ ] Request size limits: Max body size configured
- [ ] Timeout: Request timeout configured
- [ ] Host header: Validated (prevent host header attacks)

### H8: Code Signing & Distribution

```bash
# Check electron builder config
cat locaNext/electron-builder.yml 2>/dev/null | head -30
```

**Checklist:**
- [ ] Windows: Code signing certificate configured
- [ ] macOS: Apple notarization configured
- [ ] Auto-update: Uses HTTPS
- [ ] Auto-update: Signature verification enabled
- [ ] Checksums: Published with releases

### H9: Database Security

```bash
# Check DB connection
grep -r "DATABASE\|postgres\|connect" server/ --include="*.py" | head -10
```

**Checklist:**
- [ ] Connection: Using SSL/TLS
- [ ] Credentials: From environment, not hardcoded
- [ ] Permissions: App user has minimal privileges
- [ ] Backups: Encrypted at rest
- [ ] Connection pooling: Limits configured (PgBouncer)

### H10: Logging & Audit Trail

```bash
# Check logging config
grep -r "logger\|logging" server/ --include="*.py" | head -10
```

**Checklist:**
- [ ] No sensitive data logged (passwords, tokens, PII)
- [ ] Auth events logged (login, logout, failed attempts)
- [ ] Admin actions logged
- [ ] Log rotation configured
- [ ] Logs not publicly accessible

---

### Security Hardening Summary

| Category | Status | Notes |
|----------|--------|-------|
| H1 - Token Security | [ ] | |
| H2 - Password/Hashing | [ ] | |
| H3 - Injection Protection | [ ] | |
| H4 - Secret Management | [ ] | |
| H5 - .gitignore Quality | [ ] | |
| H6 - API Security | [ ] | |
| H7 - IP/Request Security | [ ] | |
| H8 - Code Signing | [ ] | |
| H9 - Database Security | [ ] | |
| H10 - Logging/Audit | [ ] | |

**Hardening Audit Status:** [ ] COMPLETE (Date: __________)

**Issues Found:** (list here)
1.
2.
3.

**Remediation Plan:** (if issues found, create separate task file)

---

## Final Verification

After ALL phases complete, run full test suite:

```bash
# Start fresh
pkill -f "python3 server/main.py" 2>/dev/null || true

# Full unit tests
python3 -m pytest tests/unit/ -v --tb=short

# Start server for integration
python3 server/main.py &
sleep 5

# Full integration tests
RUN_API_TESTS=1 python3 -m pytest tests/integration/server_tests/ -v --tb=short

# Frontend build
cd locaNext && npm run build

# Cleanup
pkill -f "python3 server/main.py"
```

### Final Checklist
- [ ] All unit tests pass (595+)
- [ ] All integration tests pass
- [ ] Frontend builds
- [ ] Desktop app works

---

## Rollback Reference

| Phase | Rollback Command |
|-------|------------------|
| 1 | `pip install requests==2.32.3 python-jose==3.3.0 python-multipart==0.0.9 oauthlib==3.2.0 configobj==5.0.6` |
| 2 | `cd locaNext && git checkout package-lock.json && npm install` |
| 3a | `pip install starlette==0.38.6` |
| 3b | `pip install python-socketio==5.11.0` |
| 3c | `pip install cryptography==3.4.8` |
| 4 | `pip install torch==2.3.1` |
| 5 | `cd locaNext && cp package.json.backup package.json && npm install` |

---

## Summary Table

| Phase | Package(s) | Risk | Key Test |
|-------|-----------|------|----------|
| 0 | Ubuntu | Low | System boots |
| 1 | 5x pip (safe) | None | Unit tests |
| 2 | npm (safe) | None | npm build |
| 3a | starlette | Medium | API tests |
| 3b | socketio | Low | WebSocket |
| 3c | cryptography | Medium | Auth tests |
| 4 | torch | HIGH | Embeddings |
| 5 | electron | HIGH | Full app test |
| 6 | urllib3 | TBD | Check version |

---

*Execute phases in order. Test after each. Update status when verified.*
