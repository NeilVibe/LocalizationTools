# Enterprise Deployment Checklist

**Purpose:** Quick reference checklist for deploying LocaNext at a new company

---

## Phase 1: Planning (Day 1)

### Information Gathering

- [ ] Server IP address: `________________`
- [ ] Company network range: `________________`
- [ ] Allowed user subnets: `________________`
- [ ] SSH credentials: `________________`
- [ ] Domain name (if any): `________________`

### Requirements Confirmed

- [ ] Server meets requirements (8GB+ RAM, 100GB+ disk)
- [ ] Network access planned (ports 5432, 3000)
- [ ] Admin workstation ready (WSL2 or Linux)
- [ ] Backup storage location identified
- [ ] User list prepared

---

## Phase 2: Server Setup (Day 1-2)

### Operating System

- [ ] Ubuntu 22.04+ LTS installed
- [ ] System updated (`apt update && apt upgrade`)
- [ ] Timezone configured
- [ ] Hostname set

### Firewall

- [ ] UFW installed and enabled
- [ ] SSH allowed (admin subnet only)
- [ ] Port 5432 allowed (company network)
- [ ] Port 3000 allowed (company network)
- [ ] Default deny incoming

### PostgreSQL

- [ ] PostgreSQL 16 installed
- [ ] `listen_addresses = '*'` configured
- [ ] `pg_hba.conf` configured for company network
- [ ] Database `locanext` created
- [ ] User `locanext_app` created
- [ ] User `locanext_admin` created
- [ ] Permissions granted
- [ ] Connection tested from admin workstation

### Gitea

- [ ] Gitea installed
- [ ] Systemd service created
- [ ] Initial configuration completed via web
- [ ] Admin account created
- [ ] Registration disabled
- [ ] Actions enabled

### Gitea Runner

- [ ] Runner installed
- [ ] Runner registered
- [ ] Runner service running
- [ ] Test build triggered successfully

---

## Phase 3: Project Setup (Day 2-3)

### Clone and Configure

- [ ] Project cloned to admin workstation
- [ ] Python venv created
- [ ] Python dependencies installed
- [ ] Node.js dependencies installed
- [ ] `.env` file configured
- [ ] Secret key generated

### Database Initialize

- [ ] Database tables created
- [ ] Admin user created
- [ ] Test connection successful

### CI/CD

- [ ] Repository pushed to company Gitea
- [ ] CI workflow triggered
- [ ] Build passes
- [ ] Installer generated

---

## Phase 4: Security (Day 3)

### Network Security

- [ ] Firewall rules verified
- [ ] PostgreSQL pg_hba.conf restricted
- [ ] Application IP whitelist configured
- [ ] No default passwords in production

### Authentication

- [ ] Strong admin password set
- [ ] Password policy defined
- [ ] Session timeout configured

### Monitoring

- [ ] Health check script created
- [ ] Log rotation configured
- [ ] Alerts configured (email/Slack)

---

## Phase 5: User Setup (Day 3-4)

### User Accounts

- [ ] User list finalized
- [ ] Accounts created in system
- [ ] Temporary passwords set
- [ ] Welcome email template ready

### Documentation

- [ ] Installation guide prepared for users
- [ ] Server settings documented
- [ ] Support contact shared

---

## Phase 6: Testing (Day 4)

### Server Tests

- [ ] PostgreSQL accessible from user network
- [ ] Gitea accessible from user network
- [ ] Backend health check passes

### Client Tests

- [ ] Fresh install works
- [ ] First-run setup completes
- [ ] Login works
- [ ] Offline mode works
- [ ] Online mode connects
- [ ] File upload works
- [ ] Translation editing works
- [ ] Multi-user sync works

### Backup Tests

- [ ] Backup script runs
- [ ] Backup file created
- [ ] Restore tested on test database

---

## Phase 7: Deployment (Day 5)

### Soft Launch (Pilot Group)

- [ ] 3-5 pilot users selected
- [ ] Credentials distributed
- [ ] Installation assisted
- [ ] Feedback collected

### Full Rollout

- [ ] All user accounts created
- [ ] Download link distributed
- [ ] Installation instructions sent
- [ ] Support channel ready

---

## Phase 8: Post-Deployment (Ongoing)

### Week 1

- [ ] Monitor error logs daily
- [ ] Address user issues promptly
- [ ] Collect feedback

### Month 1

- [ ] Performance review
- [ ] First backup verification
- [ ] User training if needed
- [ ] Documentation updates

### Ongoing

- [ ] Weekly backup verification
- [ ] Monthly security updates
- [ ] Quarterly disaster recovery test
- [ ] User account cleanup (remove inactive)

---

## Quick Reference

### Key Commands

```bash
# Start all services
sudo systemctl start postgresql gitea

# Check services
sudo systemctl status postgresql gitea

# View logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log
sudo journalctl -u gitea -f

# Backup database
pg_dump -U postgres locanext | gzip > backup_$(date +%Y%m%d).sql.gz

# Trigger build
echo "Build" >> GITEA_TRIGGER.txt && git add -A && git commit -m "Build" && git push company main
```

### Key URLs

| Service | URL |
|---------|-----|
| Gitea | `http://SERVER_IP:3000` |
| Gitea Releases | `http://SERVER_IP:3000/locanext/LocaNext/releases` |
| Gitea Actions | `http://SERVER_IP:3000/locanext/LocaNext/actions` |

### Key Files

| File | Location |
|------|----------|
| PostgreSQL Config | `/etc/postgresql/16/main/postgresql.conf` |
| PostgreSQL Auth | `/etc/postgresql/16/main/pg_hba.conf` |
| Gitea Config | `/etc/gitea/app.ini` |
| LocaNext Env | `~/LocaNext/.env` |
| User Config (Windows) | `%APPDATA%\LocaNext\server-config.json` |

---

## Completion Sign-Off

| Phase | Completed | Date | Signed |
|-------|-----------|------|--------|
| Planning | [ ] | _____ | _____ |
| Server Setup | [ ] | _____ | _____ |
| Project Setup | [ ] | _____ | _____ |
| Security | [ ] | _____ | _____ |
| User Setup | [ ] | _____ | _____ |
| Testing | [ ] | _____ | _____ |
| Deployment | [ ] | _____ | _____ |

**Deployment Complete:** [ ]
**Date:** _____________
**Admin:** _____________
