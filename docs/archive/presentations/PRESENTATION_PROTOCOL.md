# LocaNext Presentation Protocol

## Overview

This document defines the standard protocol for creating visual presentations for LocaNext. All presentations follow the same structure: **HTML source + PNG screenshot**.

## Final Presentations (4 Images)

| # | File | Purpose | Audience |
|---|------|---------|----------|
| 1 | `01_full_architecture` | Complete system overview - Desktop, Backend, Database, AI, Security, Tools | All - Technical |
| 2 | `02_licensing_complete` | Qwen Apache 2.0 PROOF + Full stack licensing + Cost comparison + Server options | Management, Finance |
| 3 | `03_apps_ldm_focus` | LDM (flagship CAT tool) + 3 utility apps | End Users, Translators |
| 4 | `04_admin_dashboard` | Admin Dashboard & Telemetry - Session tracking, usage analytics, error alerts | Management, IT |

## Folder Structure

```
docs/presentations/
├── PRESENTATION_PROTOCOL.md   # This file
├── html/                      # Active HTML source files
│   ├── 01_full_architecture.html
│   ├── 02_licensing_complete.html
│   ├── 03_apps_ldm_focus.html
│   └── 04_admin_dashboard.html
├── images/                    # Active PNG screenshots
│   ├── 01_full_architecture.png
│   ├── 02_licensing_complete.png
│   ├── 03_apps_ldm_focus.png
│   └── 04_admin_dashboard.png
└── archive/                   # Archived old presentations
    ├── html/                  # Old HTML files
    └── images/                # Old PNG files
```

---

## Presentation Details

### 1. Full Architecture (`01_full_architecture`)
**Audience:** Technical team, Management
**Content:** Complete system overview in one image
- USER PC: LocaNext.exe (Electron 28 + Svelte 4), Backend Engine (FastAPI), AI/ML Engine (Qwen + FAISS)
- CENTRAL SERVER: API Server (63+ endpoints), Admin Dashboard, Telemetry
- DATABASE: PostgreSQL 14 + PgBouncer (17 tables, 31K/s bulk insert, <10ms FTS)
- TOOLS: 4 apps (XLSTransfer, QuickSearch, KR Similar, LDM)
- SECURITY: 86 tests, IP filter, CORS, JWT, audit logging
**Stats:** 912 tests, 63+ endpoints, 86 security tests, 97% complete, $0 license, 19K+ LOC

### 2. Licensing Complete (`02_licensing_complete`)
**Audience:** Management, Finance, Legal
**Content:** 2x2 grid layout
- Q1: **Qwen License PROOF** - Apache 2.0, HuggingFace URL, official quote, commercial OK
- Q2: **Full Open Source Stack** - Python (PSF), FastAPI (MIT), PostgreSQL, Electron (MIT), FAISS (MIT), Svelte (MIT)
- Q3: **Cost Comparison** - LocaNext $600/yr vs SDL Trados $29,950/yr (10 users) = 98% savings
- Q4: **Server Options** - $0 dev, $50/mo production, self-hosted, unlimited users
**Key Point:** Qwen3-0.6B Apache 2.0 is PROVEN 100% free for commercial use

### 3. Apps with LDM Focus (`03_apps_ldm_focus`)
**Audience:** End users, Translators, Product team
**Content:** LDM takes 50% of space, other tools share 50%
- **LDM (Flagship):** 103K+ rows, 5-Tier TM cascade, Virtual scroll, FTS, PostgreSQL backend, 62% complete
- **XLSTransfer:** Excel transfer with AI matching, 85%+ accuracy, Qwen+FAISS
- **QuickSearch:** TXT/XML search, 100K+ rows, <100ms, regex support
- **KR Similar:** Korean similarity with AI, 83K dictionary pairs
**Layout:** LDM large left panel, 3 tools stacked on right

### 4. Admin Dashboard & Telemetry (`04_admin_dashboard`)
**Audience:** Management, IT, Operations
**Content:** Complete monitoring and analytics dashboard
- **Overview Cards:** Active installations, online now, sessions today, logs today, errors (24h)
- **Live Session Tracking:** User name, machine, started time, duration, status (active/idle/ended)
- **Usage Analytics:** Session stats, tool usage (7 days), performance metrics, error counts
- **Registered Installations:** Online status, version, last seen, session count, error count
- **Recent Activity Logs:** SUCCESS/INFO/WARNING/ERROR with timestamps and messages
- **API Endpoints:** 8 telemetry routes documented
- **Features Bar:** Session tracking, heartbeat, daily stats, tool usage, error alerts, JWT auth
**Key Points:** Real-time monitoring, 30-day retention, admin-only access via JWT

---

## Protocol: Creating/Updating a Presentation

### Step 1: Edit HTML File

```
docs/presentations/html/{number}_{name}.html
```

### Step 2: Design Principles

| Principle | Implementation |
|-----------|----------------|
| **ONE PAGE** | No scrolling - everything visible at once |
| **COMPRESSED** | Dense information, zoom for details |
| **Color coding** | Each section has distinct border color |
| **Stats at bottom** | Summary metrics in footer |
| **High contrast** | Dark background, bright accents |

### Step 3: Generate PNG Screenshot

```bash
cd docs/presentations
npx playwright screenshot --browser chromium --viewport-size=2560,1600 --full-page \
    "file:///home/neil1988/LocalizationTools/docs/presentations/html/filename.html" \
    "images/filename.png"
```

**Note:** `--full-page` ensures the entire content is captured even if it exceeds 1600px height.

### Step 4: Commit Pattern

```bash
git add docs/presentations/html/*.html docs/presentations/images/*.png
git commit -m "Update presentations

- {bullet point 1}
- {bullet point 2}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main && git push gitea main
```

---

## Color Palette

```css
/* Primary colors */
--cyan: #00d4ff;      /* Info, databases */
--green: #7fff7f;     /* Success, positive, FREE */
--orange: #ff6b35;    /* Backend, server */
--gold: #ffd700;      /* Database, premium, LDM */
--purple: #9945ff;    /* Electron, desktop */
--pink: #fa709a;      /* AI/ML, LDM accent */
--red: #ff6b6b;       /* Comparison, competitors */

/* Gradients */
--title-gradient: linear-gradient(90deg, #00d4ff, #7fff7f);
--bg-gradient: linear-gradient(135deg, #0a1628, #1a2940);
```

---

## Quick Commands

```bash
# Generate all PNGs
cd docs/presentations
for f in html/*.html; do
  name=$(basename "$f" .html)
  npx playwright screenshot --browser chromium --viewport-size=2560,1600 --full-page \
      "file:///home/neil1988/LocalizationTools/docs/presentations/$f" \
      "images/${name}.png"
done

# View HTML in browser
xdg-open html/01_full_architecture.html

# Check file sizes
ls -lh images/*.png
```

---

*Last updated: 2025-12-11*
*Consolidated to 3 images: Full Architecture, Licensing (with Qwen Apache 2.0 proof), Apps (LDM focus)*
