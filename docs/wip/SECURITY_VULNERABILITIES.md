# Security Vulnerabilities Tracker

**Created:** 2025-12-14
**Status:** Documented, not yet fixed
**Priority:** Medium (fix after CI stabilizes)

---

## Summary

| Source | Total | High | Moderate | Low |
|--------|-------|------|----------|-----|
| npm | 11 | 1 | 7 | 3 |
| pip | 28+ | ~10 | ~15 | ~3 |
| **Ubuntu/apt** | **85** | TBD | TBD | TBD |

---

## Ubuntu System Packages (NEW - 2025-12-14)

**85 packages need updating** on Ubuntu 22.04.3 LTS (jammy)

### Key System Components

| Package | Current | Status |
|---------|---------|--------|
| OpenSSL | 3.0.2 (Mar 2022) | ⚠️ Likely has CVEs |
| Python | 3.10.12 | Check for updates |
| Node.js | 20.18.3 | Relatively recent |
| apt | 2.4.10 | Update available |
| docker.io | 27.5.1 | Update to 28.2.2 |
| containerd | 1.7.24 | Update to 1.7.28 |

### Fix Command
```bash
# Check what needs updating
apt list --upgradable

# Update all system packages (requires sudo)
sudo apt update && sudo apt upgrade -y

# For security-only updates
sudo unattended-upgrades --dry-run  # Preview
sudo unattended-upgrades            # Apply
```

### Notes
- System updates may require reboot
- Test application after system updates
- Consider scheduling during maintenance window

---

## npm Vulnerabilities (locaNext/)

### HIGH Priority

| Package | Vulnerability | Fix |
|---------|--------------|-----|
| `glob` 10.2.0-10.4.5 | Command injection via CLI (GHSA-5j98-mcp5-4vw2) | `npm audit fix` |

### MODERATE Priority

| Package | Vulnerability | Fix | Breaking? |
|---------|--------------|-----|-----------|
| `electron` <35.7.5 | ASAR integrity bypass | `npm audit fix --force` | YES - major version |
| `esbuild` <=0.24.2 | Dev server request leak | vite upgrade | YES |
| `vite` 0.11.0-6.1.6 | Depends on esbuild | upgrade to 6.4.1 | YES |
| `js-yaml` 4.0.0-4.1.0 | Prototype pollution | `npm audit fix` | No |
| `cookie` <0.7.0 | Out of bounds chars | sveltejs/kit upgrade | YES |

### LOW Priority

| Package | Vulnerability | Notes |
|---------|--------------|-------|
| `@sveltejs/kit` | Depends on cookie | Dev dependency |
| `@sveltejs/adapter-static` | Depends on kit | Dev dependency |

### Quick Fix (Safe)

```bash
cd locaNext
npm audit fix  # Fixes glob, js-yaml (non-breaking)
```

### Breaking Changes (Test First)

```bash
cd locaNext
npm audit fix --force  # Upgrades electron, vite, sveltejs - TEST THOROUGHLY
```

---

## pip Vulnerabilities (Python)

### CRITICAL - cryptography 3.4.8 (8 CVEs)

| CVE | Severity | Fix Version |
|-----|----------|-------------|
| CVE-2023-0286 | High | 39.0.1 |
| CVE-2023-23931 | High | 39.0.1 |
| CVE-2023-50782 | High | 42.0.0 |
| CVE-2024-0727 | High | 42.0.2 |
| GHSA-5cpq-8wj7-hf2v | Moderate | 41.0.0 |
| GHSA-jm77-qphf-c4w8 | Moderate | 41.0.3 |
| GHSA-v8gr-m533-ghj9 | Moderate | 41.0.4 |
| PYSEC-2023-254 | Moderate | 41.0.6 |

**Risk:** Used for JWT tokens, password hashing
**Fix:** `pip install cryptography>=42.0.2`
**Breaking?:** Possible API changes, test auth flows

### HIGH - torch 2.3.1 (4 CVEs)

| CVE | Fix Version |
|-----|-------------|
| PYSEC-2024-259 | 2.5.0 |
| PYSEC-2025-41 | 2.6.0 |
| CVE-2025-2953 | 2.7.1rc1 |
| CVE-2025-3730 | 2.8.0 |

**Risk:** ML model loading (XLSTransfer embeddings)
**Fix:** `pip install torch>=2.6.0`
**Breaking?:** YES - PyTorch major version, test embeddings

### HIGH - urllib3 1.26.5 (5 CVEs)

| CVE | Fix Version |
|-----|-------------|
| PYSEC-2023-192 | 1.26.17 |
| PYSEC-2023-212 | 1.26.18 |
| CVE-2024-37891 | 1.26.19 |
| CVE-2025-50181 | 2.5.0 |
| CVE-2025-66418 | 2.6.0 |

**Risk:** HTTP requests (API calls)
**Fix:** System package (Ubuntu) - harder to upgrade
**Breaking?:** urllib3 2.x has breaking changes

### MODERATE Priority

| Package | Version | CVEs | Fix Version |
|---------|---------|------|-------------|
| starlette | 0.38.6 | 2 | 0.47.2 |
| python-socketio | 5.11.0 | 1 | 5.14.0 |
| python-multipart | 0.0.9 | 1 | 0.0.18 |
| python-jose | 3.3.0 | 2 | 3.4.0 |
| requests | 2.32.3 | 1 | 2.32.4 |
| setuptools | 74.0.0 | 1 | 78.1.1 |
| oauthlib | 3.2.0 | 1 | 3.2.1 |
| configobj | 5.0.6 | 1 | 5.0.9 |
| ecdsa | 0.19.1 | 1 | (no fix) |

---

## Fix Strategy

### Phase 1: Safe Fixes (No Breaking Changes)

```bash
# npm - safe fixes
cd locaNext && npm audit fix

# pip - safe fixes
pip install --upgrade \
  requests>=2.32.4 \
  python-jose>=3.4.0 \
  python-multipart>=0.0.18 \
  oauthlib>=3.2.1 \
  configobj>=5.0.9
```

### Phase 2: Moderate Risk (Test Required)

```bash
# pip - test auth and websocket after
pip install --upgrade \
  starlette>=0.47.2 \
  python-socketio>=5.14.0 \
  cryptography>=42.0.2
```

### Phase 3: High Risk (Major Testing)

```bash
# npm - electron upgrade (test desktop app thoroughly)
cd locaNext && npm audit fix --force

# pip - torch upgrade (test XLSTransfer embeddings)
pip install torch>=2.6.0
```

### Phase 4: System Level (Coordinate with IT)

- urllib3 upgrade (Ubuntu system package)
- May require OS-level updates

---

## Notes

- Most vulnerabilities require specific attack conditions
- Dev dependencies (vite, esbuild) only affect development, not production
- electron vulnerabilities affect desktop app security
- cryptography/torch are the most critical for production

---

## Checklist

- [ ] Phase 1: Safe npm fixes
- [ ] Phase 1: Safe pip fixes
- [ ] Phase 2: starlette/socketio upgrade
- [ ] Phase 2: cryptography upgrade
- [ ] Phase 3: electron upgrade + test desktop
- [ ] Phase 3: torch upgrade + test embeddings
- [ ] Phase 4: urllib3 (system level)

---

*Last updated: 2025-12-14*
