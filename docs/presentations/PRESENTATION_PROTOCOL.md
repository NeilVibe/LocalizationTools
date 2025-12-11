# LocaNext Presentation Protocol

## Overview

This document defines the standard protocol for creating visual presentations for LocaNext. All presentations follow the same structure: **HTML source + PNG screenshot**.

## Folder Structure

```
docs/presentations/
├── PRESENTATION_PROTOCOL.md   # This file
├── html/                      # HTML source files
│   ├── 01_full_architecture.html
│   ├── 01_system_architecture_flow.html
│   ├── 02_security_architecture_flow.html
│   ├── 02_tools_detailed.html
│   ├── 03_database_architecture_flow.html
│   ├── 03_licensing_pricing.html
│   ├── 04_full_system_visual.html
│   ├── 05_tool_workflows.html
│   └── 06_user_journey.html
└── images/                    # Generated PNG screenshots
    ├── 01_full_architecture.png
    ├── 01_system_architecture_flow.png
    └── ... (matching HTML files)
```

## Presentation Types

### 1. System Architecture (`01_system_architecture_flow`)
**Audience:** Technical team, IT
**Content:** 2x2 grid showing Desktop App + Backend + Database + AI/ML
**Layout:** SQUARE 2x2 grid, single view, no scroll

### 2. Security Architecture (`02_security_architecture_flow`)
**Audience:** Security team, IT
**Content:** 2x2 grid showing 7 security layers
**Layout:** SQUARE 2x2 grid, single view, no scroll

### 3. Database Architecture (`03_database_architecture_flow`)
**Audience:** DBA, Technical team
**Content:** 2x2 grid showing PgBouncer + PostgreSQL + Indexes + Performance
**Layout:** SQUARE 2x2 grid, single view, no scroll

### 4. Full System Visual (`04_full_system_visual`)
**Audience:** All - MASTER presentation
**Content:** Nested boxes, full width, complete system overview
**Layout:** SQUARE 2x2 grid, single view, no scroll

### 5. Tool Workflows (`05_tool_workflows`)
**Audience:** End users, Translators
**Content:** 2x2 grid showing XLSTransfer, QuickSearch, KR Similar, LDM
**Layout:** SQUARE 2x2 grid, single view, no scroll

### 6. Build & Deploy (`06_user_journey`)
**Audience:** Management, Stakeholders
**Content:** 2x2 grid showing CI/CD Build, User Install, Security, Licensing
**Layout:** SQUARE 2x2 grid, single view, no scroll

---

## Protocol: Creating a New Presentation

### Step 1: Create HTML File

```
docs/presentations/html/{number}_{name}.html
```

**Naming:**
- `01_`, `02_`, etc. for ordering
- Descriptive name: `system_architecture_flow`, `tool_workflows`

### Step 2: MANDATORY 2x2 Square Layout

All presentations MUST use the 2x2 grid format:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LocaNext - {Title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 100%);
            font-family: 'Segoe UI', sans-serif;
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }

        h1 {
            text-align: center;
            font-size: 2rem;
            margin-bottom: 3px;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 15px;
            font-size: 0.75rem;
        }

        /* 2x2 Grid Layout - SQUARE */
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 15px;
            height: calc(100vh - 140px);
            max-height: 800px;
        }

        .quadrant {
            background: linear-gradient(135deg, rgba(20, 30, 40, 0.95), rgba(15, 25, 35, 0.95));
            border: 3px solid;
            border-radius: 16px;
            padding: 15px;
            display: flex;
            flex-direction: column;
        }

        /* Bottom stats footer */
        .bottom-stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 15px;
            padding: 12px 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <h1>LocaNext - {Title}</h1>
    <p class="subtitle">{Subtitle with key technologies}</p>

    <div class="main-grid">
        <!-- Q1: Top Left -->
        <div class="quadrant">...</div>
        <!-- Q2: Top Right -->
        <div class="quadrant">...</div>
        <!-- Q3: Bottom Left -->
        <div class="quadrant">...</div>
        <!-- Q4: Bottom Right -->
        <div class="quadrant">...</div>
    </div>

    <div class="bottom-stats">
        <!-- Summary metrics -->
    </div>
</body>
</html>
```

### Step 3: Design Principles

| Principle | Implementation |
|-----------|----------------|
| **SQUARE 2x2** | Always use 4-quadrant grid |
| **ONE PAGE** | No scrolling - everything visible at once |
| **COMPRESSED** | Dense information, zoom for details |
| **Color coding** | Each quadrant has distinct border color |
| **Stats at bottom** | Summary metrics in footer |
| **High contrast** | Dark background, bright accents |

### Step 4: Generate PNG Screenshot

Use Playwright CLI:

```bash
cd docs/presentations
npx playwright screenshot --viewport-size=2560,1600 \
    "file:///full/path/to/html/filename.html" \
    "images/filename.png"
```

### Step 5: Commit Pattern

```bash
git add docs/presentations/html/*.html docs/presentations/images/*.png
git commit -m "Add/Update {name} presentation - 2x2 layout

- {bullet point 1}
- {bullet point 2}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main && git push gitea main
```

---

## Current Presentations

| HTML File | PNG Image | Purpose | Audience |
|-----------|-----------|---------|----------|
| `01_full_architecture` | ✅ | System overview cards | Technical |
| `01_system_architecture_flow` | ✅ | 2x2 Desktop+Backend+DB+AI | Technical |
| `02_security_architecture_flow` | ✅ | 2x2 Security 7 layers | Security |
| `02_tools_detailed` | ✅ | 4 tools with features | Users |
| `03_database_architecture_flow` | ✅ | 2x2 DB architecture | DBA |
| `03_licensing_pricing` | ✅ | Cost comparison | Finance |
| `04_full_system_visual` | ✅ | MASTER nested boxes | All |
| `05_tool_workflows` | ✅ | 2x2 tool workflows | Users |
| `06_user_journey` | ✅ | 2x2 Build & Deploy | Management |

---

## Color Palette

```css
/* Primary colors - use for quadrant borders */
--cyan: #00d4ff;      /* Info, databases */
--green: #00ff88;     /* Success, positive */
--orange: #ff6b35;    /* Backend, server */
--gold: #ffd700;      /* Database, premium */
--purple: #9945ff;    /* Electron, desktop */
--pink: #ff1493;      /* AI/ML */
--red: #ff4444;       /* Security, danger */

/* Gradients */
--title-gradient: linear-gradient(90deg, #00d4ff, #00ff88);
--bg-gradient: linear-gradient(135deg, #0a0a1a, #1a1a3a);
```

---

## Quick Commands

```bash
# Generate PNG from HTML
cd docs/presentations
npx playwright screenshot --viewport-size=2560,1600 \
    "file:///home/neil1988/LocalizationTools/docs/presentations/html/filename.html" \
    "images/filename.png"

# View HTML in browser
xdg-open html/04_full_system_visual.html

# Check file sizes
ls -lh images/*.png
```

---

*Last updated: 2025-12-11*
