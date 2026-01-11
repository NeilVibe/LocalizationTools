# LocaNext Enterprise Deployment Guide

**Version:** 1.0 | **Last Updated:** 2025-12-16

Welcome to the LocaNext Enterprise Deployment documentation. This folder contains everything needed to deploy, configure, and maintain LocaNext in a corporate environment.

---

## Quick Start

1. **New to deployment?** Start with [01_PREREQUISITES.md](01_PREREQUISITES.md)
2. **Setting up server?** See [02_SERVER_SETUP.md](02_SERVER_SETUP.md)
3. **Ready to build?** See [04_BUILD_AND_DEPLOY.md](04_BUILD_AND_DEPLOY.md)
4. **Quick checklist?** See [CHECKLIST.md](CHECKLIST.md)

---

## Documentation Index

| # | Document | Purpose |
|---|----------|---------|
| 01 | [PREREQUISITES.md](01_PREREQUISITES.md) | What you need before starting |
| 02 | [SERVER_SETUP.md](02_SERVER_SETUP.md) | PostgreSQL, Gitea, network setup |
| 03 | [PROJECT_CLONE.md](03_PROJECT_CLONE.md) | Cloning repo and initial config |
| 04 | [BUILD_AND_DEPLOY.md](04_BUILD_AND_DEPLOY.md) | Building installer, distribution |
| 05 | [USER_MANAGEMENT.md](05_USER_MANAGEMENT.md) | Creating users, permissions, passwords |
| 06 | [NETWORK_SECURITY.md](06_NETWORK_SECURITY.md) | IP ranges, firewall, access control |
| 07 | [DASHBOARD_INTEGRATION.md](07_DASHBOARD_INTEGRATION.md) | Sending data to company dashboards |
| 08 | [DATABASE_INTEGRATION.md](08_DATABASE_INTEGRATION.md) | Connecting to external databases |
| 09 | [MAINTENANCE.md](09_MAINTENANCE.md) | Backups, updates, monitoring |
| 10 | [TROUBLESHOOTING.md](10_TROUBLESHOOTING.md) | Common issues and solutions |
| -- | [CHECKLIST.md](CHECKLIST.md) | Quick deployment checklist |
| -- | [API_REFERENCE.md](API_REFERENCE.md) | API endpoints for integrations |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPANY NETWORK (e.g., 10.10.0.0/16)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────┐         ┌─────────────────────────────────┐  │
│   │  Central Server │         │  User Workstations              │  │
│   │  (10.10.30.50)  │         │  (10.10.x.x)                    │  │
│   │                 │         │                                 │  │
│   │  ┌───────────┐  │         │  ┌─────────────────────────┐   │  │
│   │  │ PostgreSQL│◄─┼─────────┼──┤ LocaNext.exe            │   │  │
│   │  │ Port 5432 │  │         │  │ ├─ Embedded Backend     │   │  │
│   │  └───────────┘  │         │  │ ├─ Local FAISS indexes  │   │  │
│   │                 │         │  │ └─ Qwen model (2.3GB)   │   │  │
│   │  ┌───────────┐  │         │  └─────────────────────────┘   │  │
│   │  │  Gitea    │  │         │                                 │  │
│   │  │ Port 3000 │  │         │  Users download installer from  │  │
│   │  └───────────┘  │         │  Gitea and install locally      │  │
│   │                 │         │                                 │  │
│   └─────────────────┘         └─────────────────────────────────┘  │
│                                                                     │
│   ┌─────────────────┐         ┌─────────────────────────────────┐  │
│   │ Company         │         │  Admin Workstation              │  │
│   │ Dashboard       │◄────────┤  - User management              │  │
│   │ (optional)      │         │  - Build & deploy               │  │
│   └─────────────────┘         │  - Monitoring                   │  │
│                               └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Modes

### Mode 1: Offline Only (Simplest)
- Users install app, use locally with SQLite
- No server setup required
- No multi-user features
- **Use case:** Individual translators, evaluation

### Mode 2: Online with Central Server (Recommended)
- Central PostgreSQL for shared data
- Multi-user collaboration
- WebSocket sync
- User authentication
- **Use case:** Team of translators, enterprise

### Mode 3: Hybrid
- Some users online, some offline
- Offline users can work locally and sync later
- **Use case:** Remote workers, field teams

---

## Key Concepts

| Term | Description |
|------|-------------|
| **Central Server** | PostgreSQL database shared by all online users |
| **Embedded Backend** | Python server running inside each LocaNext.exe |
| **Offline Mode** | Local SQLite, single-user, no network required |
| **Online Mode** | Connected to central PostgreSQL, multi-user |
| **Admin Dashboard** | Web UI for user management (optional) |
| **Gitea** | Git server for hosting releases and CI/CD |

---

## Support Contacts

| Role | Contact |
|------|---------|
| Technical Lead | [Your contact here] |
| IT Support | [Company IT here] |
| Documentation | This folder |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-16 | Initial enterprise documentation |

---

*This documentation is designed to be self-contained. Open this folder when deploying LocaNext at a new company.*
