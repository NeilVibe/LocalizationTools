# LocaNext Presentation Protocol

## Overview

This document defines the standard protocol for creating visual presentations for LocaNext. All presentations follow the same structure: **HTML source + PNG screenshot**.

## Presentation Types

### 1. System Architecture (`flowcharts/04_full_system_visual`)
**Audience:** Technical team, IT, Security team
**Content:** Full nested box diagram showing Local Machine → Server → Data Layer

### 2. Tool Workflows (`flowcharts/05_tool_workflows`)
**Audience:** End users, Translators, Project Managers
**Content:** Step-by-step workflow for each tool

### 3. User Journey (`flowcharts/06_user_journey`)
**Audience:** Management, Stakeholders
**Content:** From installation to daily use

### 4. ROI/Business Case (`diagrams/03_licensing_pricing`)
**Audience:** Finance, Management, Decision makers
**Content:** Cost comparison, savings, value proposition

---

## Protocol: Creating a New Presentation

### Step 1: Create HTML File

```
docs/presentations/{type}/{number}_{name}.html
```

**Types:**
- `diagrams/` - Info cards, stats, comparisons
- `flowcharts/` - Boxes with arrows, nested containers

**Naming:**
- `01_`, `02_`, etc. for ordering
- Descriptive name: `full_system_visual`, `tool_workflows`

### Step 2: HTML Structure Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LocaNext - {Title}</title>
    <style>
        /* Dark theme background */
        body {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 100%);
            font-family: 'Segoe UI', sans-serif;
            color: #e0e0e0;
            padding: 20px;
        }

        /* Gradient title */
        h1 {
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Container boxes with colored borders */
        .container {
            border: 2px solid #00d4ff;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
        }

        /* Nested inner boxes */
        .inner-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 12px;
        }
    </style>
</head>
<body>
    <!-- Content here -->
</body>
</html>
```

### Step 3: Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Fill the space** | Use CSS Grid or Flexbox for full-width layouts |
| **Nested boxes** | Container → Inner box → Components |
| **Arrows for flow** | CSS pseudo-elements (::before, ::after) |
| **Color coding** | Cyan (#00d4ff), Green (#00ff88), Orange (#ff6b35), Gold (#ffd700) |
| **Stats at bottom** | Summary metrics in footer |
| **High contrast** | Dark background, bright accents |

### Step 4: Generate PNG Screenshot

Use Playwright from `adminDashboard/` directory:

```javascript
// Run from: cd adminDashboard && node -e "..."
const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // 4K viewport for high resolution
    await page.setViewportSize({ width: 2560, height: 1600 });

    await page.goto('file:///path/to/file.html');
    await page.waitForTimeout(1000);

    await page.screenshot({
        path: '/path/to/file.png',
        fullPage: true
    });

    await browser.close();
})();
```

### Step 5: Commit Pattern

```bash
git add docs/presentations/{type}/{files}
git commit -m "Add {name} presentation

- {bullet point 1}
- {bullet point 2}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main && git push gitea main
```

---

## Current Presentations

### Diagrams (`docs/presentations/diagrams/`)

| File | Purpose | Audience |
|------|---------|----------|
| `01_full_architecture` | System + Security + DB overview cards | Technical |
| `02_tools_detailed` | 4 tools with features/workflows | Users |
| `03_licensing_pricing` | Cost comparison, 98% savings | Finance |

### Flowcharts (`docs/presentations/flowcharts/`)

| File | Purpose | Audience |
|------|---------|----------|
| `01_system_architecture_flow` | Top-down data flow | Technical |
| `02_security_architecture_flow` | 7 security layers decision tree | Security |
| `03_database_architecture_flow` | Query → PgBouncer → PostgreSQL | DBA |
| `04_full_system_visual` | **MASTER** - Nested boxes, full width | All |

---

## Needed Presentations

### To Create:

1. **Tool Workflows** (`05_tool_workflows`)
   - XLSTransfer: Select files → Configure → Process → Export
   - QuickSearch: Load file → Search → Navigate results
   - KR Similar: Build dictionary → Search → Find matches
   - LDM: Open file → Edit cells → TM suggestions → Save

2. **User Journey** (`06_user_journey`)
   - Install → First Launch → Login → Select Tool → Work → Results
   - Shows the complete user experience

3. **Deployment Options** (`07_deployment_options`)
   - Standalone (local only)
   - Team (shared server)
   - Enterprise (full stack)

---

## Color Palette

```css
/* Primary colors */
--cyan: #00d4ff;      /* Main accent, info */
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
# Generate all PNGs
cd adminDashboard && node scripts/generate_presentations.js

# View HTML in browser
xdg-open docs/presentations/flowcharts/04_full_system_visual.html

# Check file sizes
ls -lh docs/presentations/**/*.png
```

---

*Last updated: 2025-12-11*
