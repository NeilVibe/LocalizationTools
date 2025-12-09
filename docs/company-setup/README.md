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
│   └── No external calls (86 security tests)
│
├── LICENSING.md ──────────── License Compliance
│   ├── All dependencies listed
│   ├── 100% MIT/Apache/BSD
│   ├── No GPL contamination
│   └── Commercial use approved
│
├── EQUIPMENT_PRICING.md ──── Server Costs & Specs ⭐ NEW
│   ├── Hardware requirements
│   ├── Pricing tiers (budget/recommended/enterprise)
│   ├── Cloud vs on-premise comparison
│   └── 5-year TCO analysis
│
├── NETWORK.md ────────────── Network Setup
│   ├── Firewall rules
│   ├── Internal DNS
│   ├── Port configuration
│   └── Air-gapped deployment
│
├── INSTALLATION.md ───────── Step-by-Step Install
│   ├── Server requirements
│   ├── Offline installation
│   ├── Gitea setup
│   └── Desktop deployment
│
├── SALES_SHEET.md ────────── For Sales/Management
│   ├── Feature list
│   ├── Cost savings ($296K+ over 5 years)
│   ├── Competitor comparison
│   └── ROI analysis
│
└── OBJECTION_RESPONSES.md ── Answer All Blockers ⭐ NEW
    ├── Security team objections → Responses
    ├── Legal team objections → Responses
    ├── Finance team objections → Responses
    ├── IT team objections → Responses
    ├── Management objections → Responses
    └── Compliance objections → Responses
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

| Step | Document | Audience |
|------|----------|----------|
| 1 | [SECURITY.md](SECURITY.md) | Security team |
| 2 | [LICENSING.md](LICENSING.md) | Legal team |
| 3 | [EQUIPMENT_PRICING.md](EQUIPMENT_PRICING.md) | Finance/Procurement |
| 4 | [NETWORK.md](NETWORK.md) | IT/Network team |
| 5 | [INSTALLATION.md](INSTALLATION.md) | IT/Deployment |
| 6 | [SALES_SHEET.md](SALES_SHEET.md) | Management/Executives |
| 7 | [OBJECTION_RESPONSES.md](OBJECTION_RESPONSES.md) | **Project Champion** (counter all objections) |

---

*Document Version: 2025-12-09*
*Classification: Internal Use*
