# GRAPHS Tab Redesign Plan

**Created:** 2026-01-05 | **Status:** ✅ IMPLEMENTED

---

## Problem Statement

Current GRAPHS tab is:
- Messy, not agreeable to UIUX standards
- Uses clustered bar charts (hard to read trends)
- Multiple small charts (cluttered)
- No filtering capability
- Data tables exposed and cluttered

**User Request:** ONE big spacious line chart with dots and lines, toggleable legend.

---

## Solution: Single Big Line Chart Dashboard

### Key Changes

| Current | New |
|---------|-----|
| Multiple bar/pie charts | ONE big line chart |
| Cluttered layout | Spacious, clean |
| Raw data tables visible | Hidden data tables |
| No filtering | Legend click-to-toggle (Excel built-in) |

---

## New GRAPHS Tab Layout

**ONE BIG CHART - Simple dots connected by lines:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                         LQA PROGRESS TRACKER                             │
│                                                                          │
│  Rows                                                                    │
│   ▲                                                                      │
│   │                                                                      │
│ 120│                                                       ●──── TOTAL   │
│   │                                                      ╱               │
│   │                                                    ╱                 │
│ 100│                                                 ●                   │
│   │                                                ╱                     │
│   │                                              ╱                       │
│  80│                                  ●────────●           ●──── Alice   │
│   │                                 ╱                     ╱              │
│   │                               ╱                     ╱                │
│  60│                            ●                     ●                  │
│   │                           ╱                      ╱                   │
│   │                         ╱            ●─────────●       ●──── Bob     │
│  40│            ●─────────●            ╱                                 │
│   │           ╱                      ╱                                   │
│   │         ╱              ●───────●               ●──── John            │
│  20│      ●              ╱                        ╱                      │
│   │      ╱             ╱           ●────────────●                        │
│   │    ╱             ╱           ╱                     ●──── Fixed       │
│   0├──●────────────●───────────●──────────────────────────────────→      │
│      01/03       01/04       01/05       01/06              Date         │
│                                                                          │
│   ● Alice    ● Bob    ● John    ● TOTAL    ● Fixed                      │
│               ↑ click any legend item to show/hide                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Chart Specification

### Single Line Chart: LQA Progress Tracker

**Type:** Line Chart with markers (dots + lines)
**Purpose:** Shows cumulative progress over time

| Property | Value |
|----------|-------|
| Type | `LineChart` |
| Style | Lines with marker dots |
| X-axis | Dates |
| Y-axis | Cumulative count |
| Size | **BIG** - 20 cols x 25 rows |
| Legend | Bottom (clickable to toggle series) |

### Data Series

| Series | Data | Color | Description |
|--------|------|-------|-------------|
| Alice | Cumulative Done | Blue `4472C4` | Tester progress |
| Bob | Cumulative Done | Orange `ED7D31` | Tester progress |
| John | Cumulative Done | Green `70AD47` | Tester progress |
| TOTAL | All users combined | Gold `FFC000` | Combined progress |
| Fixed | Cumulative Fixed | Forest `228B22` | Manager resolution |

### Data Transformation

Convert daily values to cumulative sums:

```
Date    | Alice | Bob  | John | TOTAL | Fixed
--------|-------|------|------|-------|------
01/03   | 0     | 0    | 45   | 45    | 0
01/04   | 32    | 0    | 45   | 77    | 2
01/05   | 32    | 28   | 60   | 120   | 5
```

Each row = previous row + today's new values

---

## Filtering / Interactivity

**Excel Built-in (FREE, no code needed):**
- Click any legend item to show/hide that series
- Works automatically in Excel 2013+

---

## Color Palette

| Series | Color | Hex |
|--------|-------|-----|
| User 1 | Blue | `4472C4` |
| User 2 | Orange | `ED7D31` |
| User 3 | Green | `70AD47` |
| User 4 | Teal | `5B9BD5` |
| User 5 | Purple | `7030A0` |
| User 6 | Gray | `A5A5A5` |
| TOTAL | Gold | `FFC000` |
| Fixed | Forest Green | `228B22` |

---

## Implementation Steps

- [ ] Build cumulative data table (hidden in row 50+)
- [ ] Create ONE big LineChart
- [ ] Add markers (dots) to lines
- [ ] Set chart size: 20 cols x 25 rows
- [ ] Position chart at A1
- [ ] Apply colors to series
- [ ] Add title "LQA PROGRESS TRACKER"

---

## Acceptance Criteria

- [ ] ONE big spacious chart (not multiple small ones)
- [ ] Line chart with dots at data points
- [ ] Shows: Users (Done) + TOTAL + Fixed
- [ ] Legend click toggles series
- [ ] Data tables hidden
- [ ] Professional colors
- [ ] Clean, agreeable UIUX

---

*Plan created: 2026-01-05*
*Simplified: 2026-01-05 - Single chart approach*
