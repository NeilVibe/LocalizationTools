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

## 4. Authentication & JWT Security

### 4.1 Secret Key Requirements

**CRITICAL**: Never use default secrets in production!

```bash
# Generate a secure SECRET_KEY (256-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate a secure API_KEY (384-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4.2 Environment Variables

```bash
# .env file - REQUIRED for production
SECRET_KEY=<your-256-bit-secret>
API_KEY=<your-384-bit-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 4.3 Token Lifecycle

1. User logs in → Receives access token (30 min) + refresh token (7 days)
2. Access token expires → Client uses refresh token to get new access token
3. Refresh token expires → User must log in again
4. Logout → Both tokens invalidated (blacklisted)

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

## 6. Audit Logging

### 6.1 What Gets Logged

| Event | Logged Data |
|-------|-------------|
| Login Success | user_id, IP, timestamp |
| Login Failure | username, IP, timestamp, reason |
| Password Change | user_id, IP, timestamp |
| Admin Actions | user_id, action, target, timestamp |
| API Errors | endpoint, error, IP, timestamp |

### 6.2 Log Retention

| Log Type | Retention |
|----------|-----------|
| Access logs | 90 days |
| Error logs | 180 days |
| Security audit | 1 year |
| Session logs | 30 days |

### 6.3 Viewing Audit Logs

```bash
# View recent security events
tail -f server/data/logs/security_audit.log

# Search for failed logins
grep "LOGIN_FAILED" server/data/logs/security_audit.log
```

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

*Document maintained by: Development Team*
*Last security audit: [Date of last audit]*
