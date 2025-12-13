# Security Fix Plan - Priority Order

**Created:** 2025-12-14
**Status:** ACTION REQUIRED

---

## Priority 1: CRITICAL (Fix Immediately)

### 1.1 cryptography 3.4.8 → 42.0.2

**Why Critical:** Handles ALL authentication - JWT tokens, password hashing, session security. 8 CVEs including remote code execution risks.

**Impact if not fixed:** Attackers could forge auth tokens, decrypt passwords, bypass authentication.

**Fix:**
```bash
pip install cryptography>=42.0.2
```

**Test After:**
```bash
# Test auth still works
python3 -m pytest tests/unit/test_auth*.py tests/integration/server_tests/test_auth*.py -v
```

**Breaking Changes:** Minor API changes. bcrypt/JWT should still work.

---

### 1.2 starlette 0.38.6 → 0.47.2

**Why Critical:** FastAPI's core. 2 CVEs - request smuggling, path traversal.

**Impact if not fixed:** Attackers could bypass security middleware, access unauthorized paths.

**Fix:**
```bash
pip install starlette>=0.47.2
```

**Test After:**
```bash
# Test all API endpoints
RUN_API_TESTS=1 python3 -m pytest tests/integration/server_tests/ -v
```

**Breaking Changes:** Check FastAPI compatibility. May need FastAPI upgrade too.

---

### 1.3 python-socketio 5.11.0 → 5.14.0

**Why Critical:** WebSocket security. CVE-2025-61765 - authentication bypass.

**Impact if not fixed:** Attackers could connect to WebSocket without auth, see real-time data.

**Fix:**
```bash
pip install python-socketio>=5.14.0
```

**Test After:**
```bash
# Test WebSocket functionality
python3 -m pytest tests/integration/test_websocket*.py -v
```

**Breaking Changes:** Minimal.

---

## Priority 2: HIGH (Fix This Week)

### 2.1 python-multipart 0.0.9 → 0.0.18

**Why High:** File upload parsing. CVE allows DoS via malformed uploads.

**Fix:**
```bash
pip install python-multipart>=0.0.18
```

**Breaking Changes:** None.

---

### 2.2 python-jose 3.3.0 → 3.4.0

**Why High:** JWT token handling. 2 CVEs - token confusion attacks.

**Fix:**
```bash
pip install python-jose>=3.4.0
```

**Breaking Changes:** None.

---

### 2.3 requests 2.32.3 → 2.32.4

**Why High:** HTTP client. CVE for header injection.

**Fix:**
```bash
pip install requests>=2.32.4
```

**Breaking Changes:** None.

---

### 2.4 glob (npm) - Command Injection

**Why High:** HIGH severity but only affects CLI usage during build.

**Fix:**
```bash
cd locaNext && npm audit fix
```

**Breaking Changes:** None - safe fix.

---

## Priority 3: MODERATE (Fix This Month)

### 3.1 torch 2.3.1 → 2.6.0+

**Why Moderate:** Only affects XLSTransfer embeddings. 4 CVEs but requires local code execution.

**Impact:** If user loads malicious model file, could execute code.

**Fix:**
```bash
pip install torch>=2.6.0
```

**Test After:**
```bash
# Test embeddings still work
python3 -m pytest tests/e2e/test_xlstransfer_e2e.py -v
```

**Breaking Changes:** YES - PyTorch API changes. Test thoroughly.

---

### 3.2 urllib3 1.26.5 → 2.x

**Why Moderate:** System package. CVEs require MITM position.

**The "Tricky" Part:**
```bash
# Check current source
pip show urllib3
# Location: /usr/lib/python3/dist-packages  ← SYSTEM PACKAGE

# Option A: Override with pip (may cause conflicts)
pip install urllib3>=2.5.0

# Option B: Use in virtualenv only (cleanest)
python3 -m venv venv
source venv/bin/activate
pip install urllib3>=2.5.0

# Option C: Ubuntu upgrade (if available)
sudo apt update && sudo apt upgrade python3-urllib3
```

**Breaking Changes:** urllib3 2.x has breaking API changes. requests library must be compatible.

---

### 3.3 electron (npm) - ASAR Bypass

**Why Moderate:** Desktop app only. Requires local file access.

**Fix:**
```bash
cd locaNext && npm audit fix --force
# This upgrades electron to 39.x - MAJOR VERSION JUMP
```

**Test After:** Full desktop app testing - all features.

**Breaking Changes:** YES - Electron API changes between major versions.

---

## Priority 4: LOW (Backlog)

### 4.1 Dev Dependencies (npm)

| Package | Issue | Why Low |
|---------|-------|---------|
| esbuild | Dev server leak | Only affects `npm run dev` |
| vite | Depends on esbuild | Dev only |
| @sveltejs/kit | cookie issue | Dev only |

**Fix (when convenient):**
```bash
cd locaNext && npm audit fix --force
# Test dev server still works
npm run dev
```

---

### 4.2 Other pip packages

| Package | Fix | Why Low |
|---------|-----|---------|
| configobj 5.0.6 | 5.0.9 | Config parsing edge case |
| oauthlib 3.2.0 | 3.2.1 | OAuth edge case |
| setuptools 74.0.0 | 78.1.1 | Build-time only |
| ecdsa 0.19.1 | (no fix) | Timing attack, hard to exploit |

---

## Execution Plan

### Step 1: Create Branch
```bash
git checkout -b security/vulnerability-fixes
```

### Step 2: Priority 1 Fixes (CRITICAL)
```bash
pip install \
  cryptography>=42.0.2 \
  starlette>=0.47.2 \
  python-socketio>=5.14.0

# Update requirements.txt
sed -i 's/cryptography.*/cryptography>=42.0.2/' requirements.txt
sed -i 's/starlette.*/starlette>=0.47.2/' requirements.txt
sed -i 's/python-socketio.*/python-socketio>=5.14.0/' requirements.txt
```

### Step 3: Test Critical
```bash
# Start server
python3 server/main.py &
sleep 5

# Run auth tests
RUN_API_TESTS=1 python3 -m pytest tests/integration/server_tests/test_auth*.py -v

# Run full test suite
python3 -m pytest tests/ -v --tb=short
```

### Step 4: Priority 2 Fixes (HIGH)
```bash
pip install \
  python-multipart>=0.0.18 \
  python-jose>=3.4.0 \
  requests>=2.32.4

cd locaNext && npm audit fix
```

### Step 5: Commit & Push
```bash
git add -A
git commit -m "Security: Fix critical vulnerabilities (cryptography, starlette, socketio)"
git push origin security/vulnerability-fixes
```

### Step 6: Priority 3 (Separate PR - More Risk)
```bash
# torch upgrade - separate branch
git checkout -b security/torch-upgrade
pip install torch>=2.6.0
# Full embedding tests required
```

---

## Quick Reference

| Priority | Package | Current | Target | Risk |
|----------|---------|---------|--------|------|
| 1-CRIT | cryptography | 3.4.8 | 42.0.2 | Auth bypass |
| 1-CRIT | starlette | 0.38.6 | 0.47.2 | Path traversal |
| 1-CRIT | python-socketio | 5.11.0 | 5.14.0 | WS auth bypass |
| 2-HIGH | python-multipart | 0.0.9 | 0.0.18 | DoS |
| 2-HIGH | python-jose | 3.3.0 | 3.4.0 | Token confusion |
| 2-HIGH | requests | 2.32.3 | 2.32.4 | Header injection |
| 2-HIGH | glob (npm) | 10.4.5 | fix | Command injection |
| 3-MOD | torch | 2.3.1 | 2.6.0 | Model RCE |
| 3-MOD | urllib3 | 1.26.5 | 2.5.0 | MITM |
| 3-MOD | electron | <35 | 39.x | ASAR bypass |

---

## Timeline Recommendation

- **Today:** Document (DONE)
- **After CI stable:** Priority 1 (cryptography, starlette, socketio)
- **This week:** Priority 2 (multipart, jose, requests, glob)
- **Next week:** Priority 3 (torch, electron)
- **Backlog:** Priority 4, urllib3 (needs planning)

---

## Priority 5: SYSTEM (Ubuntu Packages) - NEW

### 5.1 Ubuntu System Updates

**85 packages need updating** on Ubuntu 22.04.3 LTS

| Component | Current | Status |
|-----------|---------|--------|
| OpenSSL | 3.0.2 (Mar 2022) | ⚠️ Likely has CVEs |
| apt | 2.4.10 | Update available |
| docker.io | 27.5.1 | Update to 28.2.2 |
| containerd | 1.7.24 | Update to 1.7.28 |
| Python | 3.10.12 | Check for updates |
| Node.js | 20.18.3 | Relatively recent |

**Fix:**
```bash
# Preview
apt list --upgradable

# Update all
sudo apt update && sudo apt upgrade -y

# Security-only
sudo unattended-upgrades
```

**Breaking Changes:** Possible - test after update, may need reboot.

---

## Complete Checklist

- [ ] Phase 1: Safe pip fixes (requests, jose, multipart)
- [ ] Phase 2: Safe npm fixes (npm audit fix)
- [ ] Phase 3: Critical pip (cryptography, starlette, socketio)
- [ ] Phase 4: High risk (torch, electron)
- [ ] **Phase 5: Ubuntu system packages (85 pending)**
- [ ] Phase 6: urllib3 (system package, needs virtualenv or OS planning)

---

*Ready to execute when you give the go.*
