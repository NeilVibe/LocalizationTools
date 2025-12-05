# Security Architecture

**For:** Security Team, IT Security Officers, Compliance
**Classification:** Internal
**Last Audit:** 2025-12-06

---

## Security Summary

| Category | Status | Details |
|----------|--------|---------|
| External Connections | ✅ **NONE** | Zero outbound calls required |
| Data Exfiltration Risk | ✅ **NONE** | All data stays internal |
| Authentication | ✅ **JWT + IP Filter** | Multi-layer auth |
| Audit Logging | ✅ **Complete** | All actions logged |
| Source Code | ✅ **Available** | Full audit capability |
| Dependencies | ✅ **Audited** | All MIT/Apache/BSD |

---

## 1. Network Isolation

### 1.1 No External Connections Required

```
LocaNext Architecture - FULLY AIR-GAPPED CAPABLE
═══════════════════════════════════════════════════

INTERNET                    │ FIREWALL │           INTERNAL NETWORK
                            │          │
    ❌ No API calls ────────┼──────────┼───────► LocaNext App
    ❌ No telemetry ────────┼──────────┼───────► Central Server
    ❌ No updates* ─────────┼──────────┼───────► Gitea Server
    ❌ No license checks ───┼──────────┼───────► Admin Dashboard
                            │          │
                            │  BLOCKED │

* Updates distributed via internal Gitea, not internet
```

### 1.2 Outbound Connection Analysis

| Component | Outbound Calls | Purpose | Can Disable? |
|-----------|---------------|---------|--------------|
| Desktop App | **NONE** | N/A | N/A |
| Backend API | **NONE** | N/A | N/A |
| Korean BERT | **NONE** | Local model | N/A |
| Admin Dashboard | **NONE** | N/A | N/A |
| Gitea | **NONE** | Internal only | N/A |
| Telemetry | **Internal only** | Company server | Yes |

### 1.3 Verification Command

```bash
# Run this to verify no external connections:
netstat -an | grep ESTABLISHED | grep -v "127.0.0.1\|192.168\|10.0\|172.16"
# Should return EMPTY if properly configured
```

---

## 2. Authentication & Authorization

### 2.1 Multi-Layer Authentication

```
Layer 1: IP Range Filtering
├── Only company IPs allowed (192.168.x.x, 10.x.x.x)
├── External IPs blocked at application level
└── 24 security tests verify this

Layer 2: JWT Token Authentication
├── Tokens expire (configurable, default 24h)
├── Secure secret key required
├── Token refresh mechanism
└── 22 security tests verify this

Layer 3: Role-Based Access
├── Admin - full access
├── User - tool access only
├── Read-only - view only
└── Custom roles supported
```

### 2.2 IP Filtering Configuration

```python
# .env configuration
ALLOWED_IP_RANGES=192.168.0.0/16,10.0.0.0/8,172.16.0.0/12
CORS_ORIGINS=http://localhost:5173,http://internal-server:5173
```

### 2.3 Authentication Flow

```
User Request
     │
     ▼
┌─────────────────┐
│ IP Filter Check │ ──── Reject if outside company network
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│ JWT Validation  │ ──── Reject if invalid/expired token
└────────┬────────┘
         │ Pass
         ▼
┌─────────────────┐
│ Role Check      │ ──── Reject if insufficient permissions
└────────┬────────┘
         │ Pass
         ▼
    Process Request
```

---

## 3. Audit Logging

### 3.1 What's Logged

| Event | Logged? | Details Captured |
|-------|---------|------------------|
| Login attempts | ✅ Yes | User, IP, timestamp, success/fail |
| Failed logins | ✅ Yes | User, IP, reason, timestamp |
| Tool operations | ✅ Yes | User, tool, operation, duration |
| File uploads | ✅ Yes | User, filename, size, timestamp |
| Admin actions | ✅ Yes | Admin, action, target, timestamp |
| API calls | ✅ Yes | Endpoint, user, params, response |

### 3.2 Log Location

```
Production Logs:
├── /var/log/locanext/app.log      # Application logs
├── /var/log/locanext/access.log   # Access logs
├── /var/log/locanext/security.log # Security events
└── /var/log/locanext/audit.log    # Audit trail

Desktop Logs:
└── %APPDATA%/LocaNext/logs/       # Windows
└── ~/.config/LocaNext/logs/       # Linux
```

### 3.3 Log Retention

- Default: 90 days
- Configurable via `LOG_RETENTION_DAYS` environment variable
- Automatic rotation at 100MB per file

---

## 4. Data Security

### 4.1 Data at Rest

| Data Type | Storage | Encryption |
|-----------|---------|------------|
| User credentials | Database | Bcrypt hashed |
| Session tokens | Memory | N/A (volatile) |
| Translation files | Local disk | OS-level (BitLocker/LUKS) |
| Dictionaries | Local disk | OS-level |
| Logs | Local disk | OS-level |

### 4.2 Data in Transit

| Connection | Encryption | Protocol |
|------------|------------|----------|
| Internal API | Optional TLS | HTTPS (configurable) |
| WebSocket | Optional TLS | WSS (configurable) |
| Gitea SSH | SSH | Ed25519/RSA |
| Gitea HTTP | Optional TLS | HTTPS (configurable) |

### 4.3 Sensitive Data Handling

```
NEVER STORED:
├── Plaintext passwords (bcrypt only)
├── External API keys (none used)
├── Credit card data (not applicable)
└── PII beyond username/email

STORED SECURELY:
├── Password hashes (bcrypt, cost 12)
├── JWT secrets (environment variable)
└── SSH keys (user responsibility)
```

---

## 5. Security Tests

### 5.1 Test Coverage

```
Security Test Suite: 86 Tests Total
├── IP Filtering Tests:     24 tests ✅
├── CORS Tests:             11 tests ✅
├── JWT Tests:              22 tests ✅
├── Audit Logging Tests:    29 tests ✅
└── All Passing:            86/86 ✅
```

### 5.2 Run Security Tests

```bash
# Run all security tests
cd /path/to/LocalizationTools
python3 -m pytest tests/security/ -v

# Run specific category
python3 -m pytest tests/security/test_ip_filter.py -v
python3 -m pytest tests/security/test_jwt.py -v
python3 -m pytest tests/security/test_audit.py -v
```

---

## 6. Vulnerability Management

### 6.1 Dependency Scanning

```bash
# Python dependencies
pip-audit

# Node dependencies
npm audit

# Both run automatically in CI/CD pipeline
# CRITICAL/HIGH vulnerabilities block deployment
```

### 6.2 Known CVE Policy

| Severity | Action | Timeline |
|----------|--------|----------|
| Critical | Block deployment | Immediate |
| High | Block deployment | Immediate |
| Medium | Review + Plan | 30 days |
| Low | Track | 90 days |

---

## 7. Incident Response

### 7.1 Security Contacts

| Role | Responsibility |
|------|----------------|
| IT Security | Overall security |
| System Admin | Server access |
| App Owner | Application config |

### 7.2 Response Procedure

1. **Detect** - Automated logging alerts
2. **Contain** - Isolate affected system
3. **Investigate** - Review audit logs
4. **Remediate** - Apply fix
5. **Document** - Post-incident report

---

## 8. Compliance Checklist

### 8.1 For Security Team Sign-Off

- [ ] Network isolation verified
- [ ] No external connections confirmed
- [ ] Authentication mechanism approved
- [ ] Audit logging sufficient
- [ ] Source code reviewed
- [ ] Dependencies audited
- [ ] Security tests passing
- [ ] Incident response plan approved

### 8.2 Signature Block

```
Security Approval:

Reviewed by: _______________________
Title:       _______________________
Date:        _______________________
Signature:   _______________________
```

---

*Document Version: 2025-12-06*
*Classification: Internal - Security*
