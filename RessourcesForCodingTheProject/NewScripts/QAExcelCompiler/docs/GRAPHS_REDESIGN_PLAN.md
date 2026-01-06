# Progress Tracker Charts - Implementation

**Created:** 2026-01-05 | **Status:** ✅ IMPLEMENTED | **Updated:** 2026-01-06

---

## Overview

The Progress Tracker (`LQA_Tester_ProgressTracker.xlsx`) uses **clustered bar charts** embedded in DAILY and TOTAL sheets. No separate GRAPHS sheet.

---

## Chart Architecture

### DAILY Sheet - 2 Charts

**Chart 1: "Daily Progress: Done by Tester"**
```
        01/03       01/04       01/05       01/06
       [A][B][J]   [A][B][J]   [A][B][J]   [A][B][J]
        ▲           ▲           ▲           ▲
        └── Clustered bars: one per user at each date
```

| Property | Value |
|----------|-------|
| Type | Clustered vertical bar (`col`) |
| X-axis | Dates (MM/DD) |
| Y-axis | Done count |
| Series | One per tester (clustered) |
| Width | Dynamic: `max(15, 6 + num_dates * 2)` |
| Height | 10 |

**Chart 2: "Daily Progress: Actual Issues % by Tester"**

| Property | Value |
|----------|-------|
| Type | Clustered vertical bar (`col`) |
| X-axis | Dates (MM/DD) |
| Y-axis | Actual Issues % |
| Series | One per tester (clustered) |
| Position | Below Chart 1 (15 rows spacing) |

---

### TOTAL Sheet - 2 Charts

**Chart 1: "Total Progress: Done by Tester"**
```
       Alice    Bob    John    Mary
        [A]     [B]     [J]     [M]
        ▲       ▲       ▲       ▲
        └── One bar per tester (cumulative value)
```

| Property | Value |
|----------|-------|
| Type | Clustered vertical bar (`col`) |
| X-axis | Tester names |
| Y-axis | Done count (cumulative) |
| Width | Dynamic: `max(15, 6 + num_users * 2)` |
| Height | 10 |

**Chart 2: "Total Progress: Actual Issues % by Tester"**

| Property | Value |
|----------|-------|
| Type | Clustered vertical bar (`col`) |
| X-axis | Tester names |
| Y-axis | Actual Issues % |
| Position | Below Chart 1 (15 rows spacing) |

---

## Key Principle

**DAILY and TOTAL use IDENTICAL chart style:**
- Same chart type (clustered vertical bars)
- Same layout (2 charts stacked vertically)
- Same colors per user
- Same dynamic width expansion

**Only difference:**
- DAILY: X-axis = Dates (with user clusters per date)
- TOTAL: X-axis = Tester names (cumulative single value)

---

## Color Palette

| Index | Color | Hex |
|-------|-------|-----|
| 0 | Blue | `4472C4` |
| 1 | Orange | `ED7D31` |
| 2 | Green | `70AD47` |
| 3 | Gold | `FFC000` |
| 4 | Teal | `5B9BD5` |
| 5 | Purple | `7030A0` |
| 6 | Red | `C00000` |
| 7 | Cyan | `00B0F0` |

---

## Data Tables

Charts use hidden data tables below the main table:

**DAILY Chart Data (per chart):**
```
Date    | Alice | Bob   | John
--------|-------|-------|------
01/03   | 10    | 5     | 8
01/04   | 15    | 12    | 10
01/05   | 20    | 18    | 15
```

**TOTAL Chart Data (per chart):**
```
Tester | Done
-------|-----
Alice  | 45
Bob    | 35
John   | 33
```

---

## Deprecation Note

The original plan called for a single big line chart with markers. This was **NOT implemented**. We went with clustered bar charts instead because:
1. Better visual distinction between users
2. Easier to compare values at each date
3. Consistent style across DAILY and TOTAL

---

*Implemented: 2026-01-06*
