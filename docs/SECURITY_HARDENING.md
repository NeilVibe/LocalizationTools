# Security Hardening Guide

**Version**: 2512010029
**Last Updated**: 2025-12-01
**Status**: Implementation in Progress

---

## Overview

This guide documents the security hardening measures for LocaNext/LocalizationTools. It covers network security, authentication, input validation, and monitoring required for enterprise deployment.

**Security Levels:**
- **Development**: Relaxed security for local testing
- **Production**: Strict security for enterprise deployment

**Deployment Model**: Internal Enterprise (Closed IP Range)
- Platform is only accessible within company network
- IP range filtering is the primary access control

---

## 0. IP Range Filtering (Primary Security) ✅ IMPLEMENTED

**Status**: ✅ COMPLETE (2025-12-01)

This is the **primary security feature** for internal enterprise deployment. It restricts all API access to specific IP ranges only.

### 0.1 Quick Start

Add one line to your `.env` file:

```bash
# Restrict to your company network
ALLOWED_IP_RANGE=192.168.11.0/24
```

**That's it!** Only IPs in `192.168.11.x` can access the server.

### 0.2 Configuration Options

```bash
# .env file

# Single subnet (most common)
ALLOWED_IP_RANGE=192.168.11.0/24

# Multiple subnets (multiple floors/departments)
ALLOWED_IP_RANGE=192.168.11.0/24,192.168.12.0/24,10.0.0.0/8

# Single IP only
ALLOWED_IP_RANGE=192.168.11.50/32

# Always allow localhost for development (default: true)
IP_FILTER_ALLOW_LOCALHOST=true

# Log blocked attempts for security monitoring (default: true)
IP_FILTER_LOG_BLOCKED=true
```

### 0.3 CIDR Notation Reference

| Notation | IP Range | Addresses |
|----------|----------|-----------|
| `192.168.11.0/24` | 192.168.11.0 - 192.168.11.255 | 256 |
| `192.168.11.0/25` | 192.168.11.0 - 192.168.11.127 | 128 |
| `192.168.11.0/28` | 192.168.11.0 - 192.168.11.15 | 16 |
| `192.168.11.50/32` | 192.168.11.50 only | 1 |
| `10.0.0.0/8` | 10.0.0.0 - 10.255.255.255 | 16M+ |

### 0.4 How It Works

1. Every request is checked against allowed IP ranges
2. Blocked IPs receive `403 Forbidden` response
3. Blocked attempts are logged for security monitoring
4. Localhost is always allowed (for development)
5. Supports `X-Forwarded-For` header for reverse proxy setups

### 0.5 Testing IP Filter

```bash
# Check if IP filter is enabled (look for log message)
python3 server/main.py
# Look for: "IP Filter: ENABLED - Restricting to X range(s)"

# Test blocked IP (from outside range)
curl http://your-server:8888/health
# Should return 403 if your IP is not in allowed range

# Check server logs for blocked attempts
tail -f server/data/logs/server.log | grep "IP Filter"
```

### 0.6 Files

| File | Purpose |
|------|---------|
| `server/middleware/ip_filter.py` | IP filtering middleware |
| `server/config.py` | Configuration (ALLOWED_IP_RANGE) |
| `server/main.py` | Middleware integration |
| `tests/security/test_ip_filter.py` | 24 tests |

---

## 1. CORS & Network Origin Restrictions

### 1.1 Configuration

CORS (Cross-Origin Resource Sharing) controls which domains can make requests to the API.

**Environment Variables:**
```bash
# .env file
CORS_ORIGINS=http://192.168.11.100:5173,http://192.168.11.100:5175
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

**Default Behavior:**
| Mode | Origins Allowed | Use Case |
|------|-----------------|----------|
| Development | `*` (all) | Local testing |
| Production | Whitelist only | Enterprise deployment |

### 1.2 How It Works

```python
# server/config.py
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# In production, this should be:
# CORS_ORIGINS=http://192.168.11.100:5173,http://192.168.11.101:5173
```

### 1.3 IP Range Restrictions

For enterprise environments, restrict to specific subnets:

```bash
# Example: Allow only 11th floor workstations
CORS_ORIGINS=http://192.168.11.0/24:5173

# Example: Allow specific machines
CORS_ORIGINS=http://192.168.11.100:5173,http://192.168.11.101:5173,http://192.168.11.102:5173
```

### 1.4 Testing CORS

```bash
# Test from allowed origin (should work)
curl -H "Origin: http://192.168.11.100:5173" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8888/health

# Test from blocked origin (should fail)
curl -H "Origin: http://evil-site.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8888/health
```

---

## 2. TLS/HTTPS Configuration

### 2.1 Why HTTPS is Required

- All data is encrypted in transit
- Prevents man-in-the-middle attacks
- Required for secure JWT token transmission
- Required for WebSocket security (wss://)

### 2.2 Setup Options

**Option A: Reverse Proxy (Recommended)**

Use nginx or Caddy as a reverse proxy with TLS termination:

```nginx
# /etc/nginx/sites-available/locanext
server {
    listen 443 ssl http2;
    server_name locanext.company.com;

    ssl_certificate /etc/letsencrypt/live/locanext.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/locanext.company.com/privkey.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name locanext.company.com;
    return 301 https://$server_name$request_uri;
}
```

**Option B: Corporate CA Certificate**

If your company provides certificates:

```bash
# Environment variables
SSL_CERT_FILE=/path/to/company-cert.pem
SSL_KEY_FILE=/path/to/company-key.pem
```

### 2.3 WebSocket Security

When using HTTPS, WebSocket must use `wss://`:

```javascript
// Client-side connection
const socket = io("wss://locanext.company.com", {
    transports: ["websocket"]
});
```

---

## 3. Rate Limiting

### 3.1 Configuration

```bash
# .env file
RATE_LIMIT_ENABLED=true
RATE_LIMIT_LOGIN=5/minute          # Prevent brute force
RATE_LIMIT_API=60/minute           # Normal API calls
RATE_LIMIT_UPLOAD=10/minute        # File uploads
RATE_LIMIT_SEARCH=30/minute        # Search operations
```

### 3.2 Default Limits

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/api/v2/auth/login` | 5/min | Prevent brute force |
| `/api/v2/*/create-*` | 10/min | Resource-intensive ops |
| `/api/v2/*/search` | 30/min | Normal usage |
| All other endpoints | 60/min | Default |

### 3.3 IP Blocking

After repeated violations, IPs are temporarily blocked:
- 10 violations in 1 minute → 15 minute block
- 50 violations in 1 hour → 1 hour block

---

## 4. Authentication & JWT Security ✅ IMPLEMENTED

**Status**: ✅ COMPLETE (2025-12-01)

Server now validates security configuration on startup and warns/blocks insecure defaults.

### 4.1 Startup Security Validation

The server automatically checks security configuration on startup:

```
# Example startup output with default values:
SECURITY: SECRET_KEY is using default value! Generate a secure key...
SECURITY: API_KEY is using default value! Generate a secure key...
SECURITY: Default admin password 'admin123' should be changed!
SECURITY: ALLOWED_IP_RANGE not set - server accepts connections from any IP
SECURITY: CORS allows all origins - set CORS_ORIGINS for production
SECURITY: Security configuration has 5 warning(s) - review before production
```

### 4.2 Security Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `warn` (default) | Logs warnings, continues startup | Development |
| `strict` | Fails startup if using defaults | Production |

```bash
# .env file
SECURITY_MODE=strict  # Fail if using default SECRET_KEY/API_KEY
```

### 4.3 Secret Key Requirements

**CRITICAL**: Never use default secrets in production!

```bash
# Generate a secure SECRET_KEY (256-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a secure API_KEY (384-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4.4 Environment Variables

```bash
# .env file - REQUIRED for production
SECRET_KEY=<your-256-bit-secret>
API_KEY=<your-384-bit-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security mode (strict recommended for production)
SECURITY_MODE=strict
```

### 4.5 Token Lifecycle

1. User logs in → Receives access token (30 min) + refresh token (7 days)
2. Access token expires → Client uses refresh token to get new access token
3. Refresh token expires → User must log in again
4. Logout → Both tokens invalidated (blacklisted)

### 4.6 Files

| File | Purpose |
|------|---------|
| `server/config.py` | Security validation functions |
| `server/main.py` | Startup validation integration |
| `tests/security/test_jwt_security.py` | 22 tests |

---

## 5. Input Validation & Injection Prevention

### 5.1 SQL Injection

**Protected by**: SQLAlchemy ORM (parameterized queries)

All database queries use SQLAlchemy, which automatically escapes parameters:

```python
# Safe (parameterized)
user = session.query(User).filter(User.username == username).first()

# Never do this (vulnerable)
# session.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

### 5.2 XSS Prevention

User-provided text should be sanitized before display:

```python
from markupsafe import escape

# Sanitize user input
safe_text = escape(user_input)
```

### 5.3 File Upload Validation

```python
# Allowed file types
ALLOWED_EXTENSIONS = {'.xlsx', '.xls', '.txt'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Validation checks:
# 1. Extension whitelist
# 2. MIME type verification
# 3. File size limit
# 4. Magic bytes validation
```

### 5.4 Path Traversal Prevention

```python
import os
from pathlib import Path

def safe_path(user_path: str, base_dir: Path) -> Path:
    """Ensure path is within allowed directory."""
    full_path = (base_dir / user_path).resolve()
    if not str(full_path).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal detected")
    return full_path
```

---

## 6. Audit Logging ✅ IMPLEMENTED

**Status**: ✅ COMPLETE (2025-12-01)

Security audit logging tracks all security-relevant events for IT compliance.

### 6.1 What Gets Logged

| Event Type | Logged Data | Severity |
|------------|-------------|----------|
| `LOGIN_SUCCESS` | user_id, username, IP, timestamp | INFO |
| `LOGIN_FAILURE` | username, IP, timestamp, reason | WARNING |
| `LOGOUT` | user_id, username, IP, timestamp | INFO |
| `IP_BLOCKED` | IP, reason, endpoint | WARNING |
| `PASSWORD_CHANGE` | user_id, IP, changed_by | INFO |
| `USER_CREATED` | new_username, created_by, IP | INFO |
| `USER_DELETED` | deleted_username, deleted_by, IP | WARNING |
| `RATE_LIMITED` | IP, endpoint | WARNING |
| `SERVER_STARTED` | config_summary | INFO |

### 6.2 Log Location

```bash
# Security audit log file
server/data/logs/security_audit.log
```

### 6.3 Log Format

```
2025-12-01 14:30:45 | WARNING | [LOGIN_FAILURE] | success=False | user=baduser | ip=192.168.1.100 | details={"reason": "Invalid password"}
2025-12-01 14:31:02 | INFO | [LOGIN_SUCCESS] | success=True | user=admin | ip=192.168.1.100
2025-12-01 14:32:15 | WARNING | [IP_BLOCKED] | success=False | ip=10.0.0.1 | details={"reason": "IP not in allowed range"}
```

### 6.4 Viewing Audit Logs

```bash
# View recent security events
tail -f server/data/logs/security_audit.log

# Search for failed logins
grep "LOGIN_FAILURE" server/data/logs/security_audit.log

# Search for blocked IPs
grep "IP_BLOCKED" server/data/logs/security_audit.log

# Count failed logins from specific IP
grep "LOGIN_FAILURE" server/data/logs/security_audit.log | grep "192.168.1.100" | wc -l
```

### 6.5 Programmatic Access

```python
from server.utils.audit_logger import (
    get_recent_audit_events,
    get_failed_login_count,
)

# Get last 100 events
events = get_recent_audit_events(limit=100)

# Count failed logins from IP in last 15 minutes
failures = get_failed_login_count("192.168.1.100", minutes=15)
```

### 6.6 Log Retention

| Log Type | Retention |
|----------|-----------|
| Access logs | 90 days |
| Error logs | 180 days |
| Security audit | 1 year |
| Session logs | 30 days |

### 6.7 Files

| File | Purpose |
|------|---------|
| `server/utils/audit_logger.py` | Audit logging module |
| `server/api/auth_async.py` | Login audit integration |
| `server/middleware/ip_filter.py` | IP block audit integration |
| `tests/security/test_audit_logging.py` | 29 tests |

---

## 7. Network Binding

### 7.1 Development Mode

```bash
# Binds to all interfaces (for local testing)
SERVER_HOST=0.0.0.0
SERVER_PORT=8888
```

### 7.2 Production Mode

```bash
# Binds to localhost only (use with reverse proxy)
SERVER_HOST=127.0.0.1
SERVER_PORT=8888
```

### 7.3 Firewall Rules

```bash
# Allow only local connections to backend
sudo ufw allow from 127.0.0.1 to any port 8888

# Allow HTTPS from internal network
sudo ufw allow from 192.168.11.0/24 to any port 443
```

---

## 8. Production Deployment Checklist

### 8.1 Pre-Deployment

- [ ] Change all default passwords (`admin123`)
- [ ] Generate new SECRET_KEY and API_KEY
- [ ] Configure CORS_ORIGINS whitelist
- [ ] Set up TLS certificates
- [ ] Configure reverse proxy (nginx/Caddy)
- [ ] Set SERVER_HOST to 127.0.0.1
- [ ] Enable rate limiting
- [ ] Configure firewall rules

### 8.2 Post-Deployment

- [ ] Verify HTTPS is working
- [ ] Test CORS restrictions
- [ ] Test rate limiting
- [ ] Verify audit logging
- [ ] Test login/logout flow
- [ ] Verify WebSocket (wss://) works
- [ ] Run security tests

### 8.3 Ongoing Maintenance

- [ ] Weekly dependency updates (pip-audit, npm audit)
- [ ] Monthly security review
- [ ] Quarterly penetration testing
- [ ] Certificate renewal (before expiry)

---

## 9. Environment Variables Reference

### 9.1 Required for Production

```bash
# MANDATORY - Application will fail without these
SECRET_KEY=<256-bit-secret>
CORS_ORIGINS=<comma-separated-origins>
```

### 9.2 Recommended for Production

```bash
# Security
API_KEY=<384-bit-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
RATE_LIMIT_ENABLED=true

# Network
SERVER_HOST=127.0.0.1
PRODUCTION_ORIGIN=https://locanext.company.com

# Database
DATABASE_TYPE=postgresql
POSTGRES_PASSWORD=<strong-password>
```

### 9.3 Optional

```bash
# Monitoring
SENTRY_DSN=<sentry-dsn>
LOG_LEVEL=INFO

# Features
ENABLE_DOCS=false  # Disable API docs in production
DEBUG=false
```

---

## 10. Security Testing

### 10.1 Automated Tests

Run security tests as part of CI:

```bash
# Run security test suite
pytest tests/security/ -v

# Run with coverage
pytest tests/security/ --cov=server --cov-report=html
```

### 10.2 Manual Testing

```bash
# Test CORS
curl -H "Origin: http://evil-site.com" http://localhost:8888/health

# Test rate limiting
for i in {1..10}; do curl http://localhost:8888/api/v2/auth/login; done

# Test SQL injection (should fail gracefully)
curl -X POST http://localhost:8888/api/v2/auth/login \
     -d '{"username": "admin\"; DROP TABLE users; --", "password": "test"}'
```

---

## Quick Reference

### Security Status by Component

| Component | Status | Notes |
|-----------|--------|-------|
| CORS | Configurable | Use CORS_ORIGINS env var |
| TLS/HTTPS | Manual setup | Requires reverse proxy |
| Rate Limiting | Configurable | Use RATE_LIMIT_* env vars |
| JWT Auth | Implemented | Change SECRET_KEY! |
| SQL Injection | Protected | Via SQLAlchemy ORM |
| XSS | Partial | Sanitize user input |
| Audit Logging | Implemented | Check logs directory |
| File Upload | Partial | Extension whitelist |

### Emergency Contacts

For security incidents, contact:
- IT Security Team: security@company.com
- System Admin: admin@company.com

---

## 11. Functionality Verification After Security Changes

**CRITICAL**: Security implementations must NEVER break existing functionality!

### 11.1 Why This Matters

Security middleware (IP filter, CORS, JWT) can accidentally:
- Block legitimate API calls with 403 errors
- Break inter-service communication
- Disrupt authentication flows
- Disconnect WebSocket connections

### 11.2 Verification Protocol

After ANY security change, run this verification:

```bash
# Step 1: Run ALL security tests (must pass 100%)
python -m pytest tests/security/ -v --override-ini="addopts="
# Expected: 86+ tests passed

# Step 2: Run app functionality tests (must pass 100%)
python -m pytest tests/test_kr_similar.py tests/test_quicksearch_phase4.py -v --override-ini="addopts="
# Expected: All passed

# Step 3: Verify security modules load without errors
python3 -c "
from server import config
from server.middleware.ip_filter import IPFilterMiddleware
from server.utils.audit_logger import log_login_success
print('All security modules load correctly')
"

# Step 4: Start server and verify health
python3 server/main.py &
sleep 5
curl -s http://localhost:8888/health | python3 -m json.tool
# Expected: {"status": "healthy", ...}

# Step 5: Verify API endpoints work
curl -s http://localhost:8888/api/v2/kr-similar/health
curl -s http://localhost:8888/api/v2/quicksearch/health
curl -s http://localhost:8888/api/v2/xlstransfer/health
# Expected: All return {"status": "ok"}

# Step 6: Kill test server
pkill -f "python3 server/main.py"
```

### 11.3 What to Check

| Area | What to Verify |
|------|----------------|
| IP Filter | Localhost still works, allowed IPs pass through |
| CORS | Frontend origins not blocked |
| JWT | Login still works, tokens validate |
| Audit | Events logged, no exceptions |
| WebSocket | Real-time updates still function |
| API Endpoints | All 47+ endpoints return expected responses |

### 11.4 If Something Breaks

1. **403 Forbidden errors** → Check IP filter config, CORS origins
2. **401 Unauthorized** → Check JWT SECRET_KEY, token expiry
3. **Connection refused** → Check server binding (0.0.0.0 vs 127.0.0.1)
4. **CORS blocked** → Add origin to CORS_ORIGINS whitelist
5. **WebSocket fails** → Verify wss:// protocol and CORS headers

### 11.5 Reference Documents

- **[TESTING_PROTOCOL.md](TESTING_PROTOCOL.md)** - Full testing procedures with security verification
- **Roadmap.md** - Post-Security Verification Checklist

---

*Document maintained by: Development Team*
*Last security audit: 2025-12-01*
*Last updated: 2025-12-01*
