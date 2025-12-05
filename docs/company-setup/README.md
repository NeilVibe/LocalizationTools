# Company Setup - Internal Deployment Guide

**For:** Security Team, IT Department, Sales Team, Management
**Status:** Production Ready
**License:** 100% MIT - Zero Legal Risk

---

## Executive Summary

LocaNext is a **fully internal, self-hosted** localization platform that requires:
- **ZERO external services** after initial setup
- **ZERO cloud dependencies** - runs 100% on company hardware
- **ZERO data leaving your network** - all processing local
- **100% MIT licensed** - no vendor lock-in, no licensing fees, no legal risk

---

## Documentation Tree

```
docs/company-setup/
│
├── README.md ──────────────── You are here (Overview)
│
├── SECURITY.md ───────────── Security Architecture
│   ├── Network isolation
│   ├── Authentication (JWT + IP filtering)
│   ├── Audit logging
│   └── No external calls
│
├── NETWORK.md ────────────── Network Setup
│   ├── Firewall rules
│   ├── Internal DNS
│   ├── Port configuration
│   └── Air-gapped deployment
│
├── LICENSING.md ──────────── License Compliance
│   ├── All dependencies listed
│   ├── 100% MIT/Apache/BSD
│   ├── No GPL contamination
│   └── Commercial use approved
│
├── INSTALLATION.md ───────── Step-by-Step Install
│   ├── Server requirements
│   ├── Offline installation
│   ├── Gitea setup
│   └── Desktop deployment
│
└── SALES_SHEET.md ────────── For Sales/Management
    ├── Feature list
    ├── Cost savings
    ├── Competitor comparison
    └── ROI analysis
```

---

## Quick Facts for Security Team

| Concern | Answer |
|---------|--------|
| External API calls? | **NONE** - fully offline capable |
| Cloud dependencies? | **NONE** - runs on your servers |
| Data transmission? | **Internal network only** |
| User tracking? | **NONE** - no telemetry to outside |
| License type? | **MIT** - do whatever you want |
| Source code? | **100% available** - audit anytime |
| Vendor lock-in? | **ZERO** - you own everything |

---

## Quick Facts for Sales Team

| Question | Answer |
|----------|--------|
| Recurring costs? | **$0** - no subscriptions |
| Per-seat licensing? | **$0** - unlimited users |
| Support contract required? | **No** - optional only |
| Can we modify it? | **Yes** - MIT license |
| Can we resell/bundle? | **Yes** - MIT license |
| Legal review needed? | **Minimal** - MIT is safest |

---

## Architecture Overview

```
COMPANY INTERNAL NETWORK ONLY
══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                    COMPANY FIREWALL                         │
│                  (No inbound from internet)                 │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ GITEA SERVER  │    │ CENTRAL       │    │ ADMIN         │
│ (Git + CI/CD) │    │ TELEMETRY     │    │ DASHBOARD     │
│               │    │ SERVER        │    │               │
│ Port 3000     │    │ Port 9999     │    │ Port 5175     │
│ Internal only │    │ Internal only │    │ Internal only │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     ▲                     │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ EMPLOYEE PC 1 │    │ EMPLOYEE PC 2 │    │ EMPLOYEE PC 3 │
│               │    │               │    │               │
│ LocaNext App  │    │ LocaNext App  │    │ LocaNext App  │
│ (Desktop)     │    │ (Desktop)     │    │ (Desktop)     │
└───────────────┘    └───────────────┘    └───────────────┘

                    ❌ NO INTERNET CONNECTION REQUIRED
                    ❌ NO DATA LEAVES COMPANY NETWORK
                    ❌ NO EXTERNAL API CALLS
                    ✅ 100% INTERNAL PROCESSING
```

---

## What's Included

| Component | Purpose | License |
|-----------|---------|---------|
| LocaNext Desktop | Main application | MIT |
| FastAPI Backend | API server | MIT |
| Gitea | Internal Git server | MIT |
| SQLite/PostgreSQL | Database | Public Domain / PostgreSQL |
| Korean BERT Model | AI translation | Apache 2.0 |
| Electron | Desktop framework | MIT |
| SvelteKit | Frontend framework | MIT |

---

## Next Steps

1. Read [SECURITY.md](SECURITY.md) - For security team approval
2. Read [LICENSING.md](LICENSING.md) - For legal team approval
3. Read [NETWORK.md](NETWORK.md) - For IT/network setup
4. Read [INSTALLATION.md](INSTALLATION.md) - For deployment
5. Read [SALES_SHEET.md](SALES_SHEET.md) - For management/sales

---

*Document Version: 2025-12-06*
*Classification: Internal Use*
