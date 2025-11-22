# Security Policy

## 🔐 Security Overview

This is a **PUBLIC REPOSITORY** containing a localization platform with default development credentials. This document outlines security best practices and vulnerability reporting procedures.

---

## ⚠️ CRITICAL: Default Credentials

### Public Repository Warning

**THIS REPOSITORY CONTAINS PUBLICLY KNOWN DEFAULT CREDENTIALS!**

The following default credentials are hardcoded for **DEVELOPMENT ONLY**:
- **Admin Username**: `admin`
- **Admin Password**: `admin123`
- **Default SECRET_KEY**: `dev-secret-key-CHANGE-IN-PRODUCTION`
- **Default API_KEY**: `dev-key-change-in-production`
- **Default DB Password**: `change_this_password`

### ⛔ NEVER USE IN PRODUCTION

**If you deploy this application with default credentials:**
- ❌ Your system WILL be compromised
- ❌ Anyone can access your admin panel
- ❌ Your data WILL be exposed
- ❌ Your API WILL be vulnerable

---

## ✅ Production Security Checklist

Before deploying to production, you **MUST**:

### 1. Change All Default Passwords
```bash
# Change admin password immediately after first login
# Go to: User Settings → Change Password

# Or via SQL:
UPDATE users SET password_hash = '<bcrypt_hash_of_new_password>'
WHERE username = 'admin';
```

### 2. Set Environment Variables
Create a `.env` file (which is gitignored):
```bash
# REQUIRED: Change ALL of these!
SECRET_KEY=<your-secret-key-here>
API_KEY=<your-api-key-here>
POSTGRES_PASSWORD=<your-db-password>
DATABASE_URL=postgresql://user:password@host/db

# Optional but recommended
ACCESS_TOKEN_EXPIRE_MINUTES=30
SMTP_PASSWORD=<your-smtp-password>
```

### 3. Generate Strong Secrets
```bash
# Generate SECRET_KEY (256-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate API_KEY (384-bit)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate secure random password
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 4. Disable/Remove Default Admin
```sql
-- Disable default admin after creating real admin accounts
UPDATE users SET is_active = false WHERE username = 'admin';

-- Or delete it entirely
DELETE FROM users WHERE username = 'admin';
```

### 5. Security Hardening
- [ ] Change `DEBUG = False` in production
- [ ] Set `ENABLE_DOCS = False` (disable Swagger docs in production)
- [ ] Use strong PostgreSQL password (not SQLite)
- [ ] Enable HTTPS/SSL
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Review CORS settings
- [ ] Set up monitoring/alerts

---

## 🛡️ Security Best Practices

### Environment Variables
**NEVER** commit these files to git:
- `.env`
- `.env.local`
- `.env.production`
- Any file containing passwords, tokens, or keys

Our `.gitignore` protects these patterns:
```
.env*
*_token.txt
*_key.txt
*_secret.txt
*.pem
*.key
id_rsa
credentials.json
secrets.json
```

### Database Security
- Use PostgreSQL in production (not SQLite)
- Use strong passwords (20+ characters)
- Enable SSL connections
- Regular backups
- Restrict network access

### API Security
- Always use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Use prepared statements (SQLAlchemy ORM does this)
- Enable CORS only for trusted origins

### Authentication
- JWT tokens with short expiration
- bcrypt password hashing (12 rounds)
- Require password changes on first login
- Implement password complexity requirements
- Enable account lockout after failed attempts

---

## 🐛 Reporting Security Vulnerabilities

### Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

### How to Report

**DO NOT** create public GitHub issues for security vulnerabilities!

Instead:
1. Email security concerns to: **[YOUR-EMAIL@company.com]**
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Allow up to 48 hours for initial response
4. Allow up to 7 days for a fix to be released

### Disclosure Policy
- Security researchers: Please allow time for fixes before public disclosure
- We will credit reporters in release notes (unless they prefer anonymity)
- Critical vulnerabilities will trigger immediate patching and notification

---

## 🔍 Known Security Considerations

### Public Repository Risks
✅ **Safe**: This repo is safe to public as long as users follow security guidelines
❌ **Unsafe**: Deploying with default credentials
❌ **Unsafe**: Committing `.env` files with real credentials

### Default Credentials
The default `admin/admin123` credentials are:
- ✅ Safe for local development
- ✅ Safe for testing
- ❌ **UNSAFE** for production
- ❌ **UNSAFE** for internet-facing deployments

### Development vs Production
| Component | Development | Production |
|-----------|-------------|------------|
| Database | SQLite | PostgreSQL |
| DEBUG | True | **False** |
| Docs | Enabled | **Disabled** |
| SECRET_KEY | Default | **Strong random** |
| Admin Password | admin123 | **Strong unique** |
| HTTPS | Optional | **Required** |

---

## 📋 Security Audit Checklist

Before going live, verify:

- [ ] Changed all default passwords
- [ ] Set strong SECRET_KEY in .env
- [ ] Set strong API_KEY in .env
- [ ] Using PostgreSQL (not SQLite)
- [ ] DEBUG = False
- [ ] ENABLE_DOCS = False
- [ ] HTTPS enabled
- [ ] CORS restricted to trusted origins
- [ ] Rate limiting enabled
- [ ] Firewall configured
- [ ] Backups configured
- [ ] Monitoring/logging enabled
- [ ] Security headers configured
- [ ] No .env files in git
- [ ] No sensitive data in git history

---

## 🔒 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/)

---

## 📅 Last Updated

2025-11-22

**This repository is for internal/private use. Deploy responsibly.**
