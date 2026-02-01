# WordCount Diff Master - Workflow Summary

**⚠️ V2.0 UPDATE (2025-11-18)**

This is the **V2.0 SIMPLIFIED** workflow. Major changes:
- ❌ No daily diffs
- ✅ Always compares TODAY vs. past date
- ✅ Smart categorization (Weekly or Monthly)
- ✅ 4 sheets instead of 6
- ✅ Period titles in sheets

**See V2_COMPLETE.md for complete details!**

---

## 🎯 What This Script Does in 30 Seconds

**Compares TODAY's translation data against any past date, with smart auto-categorization as Weekly or Monthly.**

---

## 📊 V2.0 Simple Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER STARTS SCRIPT                       │
│              python wordcount_diff_master.py                │
│          (Automatically processes TODAY's data)             │
└────────────────────────┬────────────────────────────────────┘
                         ▼
                ┌──────────────────────┐
                │ TODAY: 2025-11-18    │
                │ Enter PAST date:     │
                │ 2025-11-10           │
                └────────┬─────────────┘
                         ▼
        ┌────────────────────────────────┐
        │  SCRIPT AUTOMATICALLY DOES:    │
        │                                │
        │  1️⃣  Scans TODAY's XML files   │
        │  2️⃣  Counts words              │
        │  3️⃣  Loads history             │
        │  4️⃣  Finds past date data      │
        │  5️⃣  Smart categorization:     │
        │     8 days → WEEKLY ✅         │
        │  6️⃣  Calculates diffs          │
        │  7️⃣  Updates history           │
        │  8️⃣  Generates Excel (4 sheets)│
        │                                │
        │      (~1 minute total)         │
        └────────────────┬───────────────┘
                         ▼
           ┌──────────────────────────────────┐
           │   OUTPUT FILES READY:            │
           │                                  │
           │ ✅ Excel Report (4 sheets)        │
           │   - Weekly Full ✅ (has data)     │
           │   - Monthly Full (N/A)          │
           │   - Weekly Detail ✅ (has data)   │
           │   - Monthly Detail (N/A)        │
           │                                  │
           │ ✅ JSON History (updated)         │
           │   - Today's data saved          │
           └──────────────────────────────────┘
```

---

## 🔢 Step-by-Step Process

### Phase 0: User Input
**What happens:** You enter the date of the data you're processing
**Example:** `2025-11-18`
**Duration:** 5 seconds

### Phase 1: Scan XML Files
**What happens:** Script reads all language XML files and export files
**Processing:**
- Iterates through `loc` folder for language files
- Reads `export__` folder for category structure
- Parses XML to extract text data

**Duration:** 20-30 seconds

### Phase 2: Count Words
**What happens:** Script analyzes each file
**Processing:**
- Counts total words (source text)
- Counts completed words (translated text)
- Calculates coverage percentage
- Groups by language and category

**Duration:** Included in Phase 1

### Phase 3: Load History
**What happens:** Script reads `wordcount_history.json`
**Processing:**
- Loads all previous runs
- Identifies comparison points:
  - Daily: Most recent previous run
  - Weekly: Run from ~7 days ago
  - Monthly: Run from ~30 days ago

**Duration:** 1-2 seconds

### Phase 4: Calculate Diffs
**What happens:** Script compares current vs. previous data
**Calculations:**
- **Net change:** Current value - Previous value
- **Percent change:** (Change / Previous) × 100

**For each metric:**
- Total words (daily, weekly, monthly)
- Completed words (daily, weekly, monthly)
- Coverage % (daily, weekly, monthly)

**Duration:** 2-5 seconds

### Phase 5: Update History
**What happens:** Script appends new run to JSON
**Processing:**
- Creates new run object with timestamp
- Appends to `runs` array
- Updates metadata (total runs, last run date)
- Saves to `wordcount_history.json`

**Duration:** 1-2 seconds

### Phase 6: Delete Old Reports
**What happens:** Script removes previous Excel reports
**Processing:**
- Finds all files matching `WordCountAnalysis_*.xlsx`
- Deletes old versions
- Keeps only the newest report

**Duration:** 1 second

### Phase 7: Generate Excel Report
**What happens:** Script creates new Excel file with 6 sheets
**Sheets created:**
1. Daily Diff - Full Summary
2. Weekly Diff - Full Summary
3. Monthly Diff - Full Summary
4. Daily Diff - Detailed Categories
5. Weekly Diff - Detailed Categories
6. Monthly Diff - Detailed Categories

**Formatting applied:**
- Blue headers with white text
- Green for positive changes
- Red for negative changes
- Gray for no change
- Yellow separators between languages

**Duration:** 10-20 seconds

---

## 📁 Data Flow

```
XML Files → Word Count Data → Current Run Object
                                      ↓
                              JSON History (load)
                                      ↓
                              Comparison Points
                                      ↓
                              Diff Calculations
                                      ↓
                        JSON History (save with new run)
                                      ↓
                               Excel Report
```

---

## 🔄 Continuous Tracking Workflow

### First Run
```
Run 1 (2025-11-01) → Creates history
                   → Excel shows: "No comparison data"
```

### Second Run (Daily diff appears)
```
Run 2 (2025-11-02) → Compares vs Run 1
                   → Excel shows: Daily diffs only
                   → Weekly/Monthly: "No comparison data"
```

### Eighth Run (Weekly diff appears)
```
Run 8 (2025-11-08) → Compares vs Run 1 (7 days back)
                   → Excel shows: Daily + Weekly diffs
                   → Monthly: "No comparison data"
```

### Thirty-First Run (All diffs appear)
```
Run 31 (2025-12-01) → Compares vs Run 1 (30 days back)
                    → Excel shows: Daily + Weekly + Monthly diffs
                    → Full tracking active ✓
```

---

## 🎨 How Diffs Are Calculated

### Example: Daily Diff

**Previous Run (2025-11-17):**
- ENG Total Words: 120,000
- ENG Completed Words: 95,000

**Current Run (2025-11-18):**
- ENG Total Words: 125,000
- ENG Completed Words: 98,000

**Calculated Diffs:**
- Total Δ: 125,000 - 120,000 = **+5,000** (green)
- Total Δ%: (5,000 / 120,000) × 100 = **+4.17%** (green)
- Completed Δ: 98,000 - 95,000 = **+3,000** (green)
- Completed Δ%: (3,000 / 95,000) × 100 = **+3.16%** (green)

### Example: Weekly Diff

**Run from 7 days ago (2025-11-11):**
- FRA Completed Words: 80,000

**Current Run (2025-11-18):**
- FRA Completed Words: 88,000

**Calculated Diff:**
- Completed Δ: 88,000 - 80,000 = **+8,000** (green)
- Completed Δ%: (8,000 / 80,000) × 100 = **+10.0%** (green)

---

## 📊 Excel Report Details

### What Each Sheet Shows

**Full Summary Sheets (1-3):**
- One row per language
- Overall totals and coverage
- Aggregated diffs across all categories

**Detailed Sheets (4-6):**
- **Per-language table format** (matches wordcount1.py)
- Each language has its own table section:
  - Language title row (bold): "Language: ENG"
  - Header row: Category | Total Words | Completed Words | Coverage % | diffs...
  - Category data rows: Faction, Main, Sequencer + Other, System, World, etc.
  - Yellow separator row
  - Then next language's table
- Makes it easy to focus on one language at a time!

### Reading the Report

**Green numbers** = Progress! More words translated
**Red numbers** = Decrease (investigate why)
**Gray numbers** = No change

**Example interpretation:**
```
ENG | Total Δ: +2,500 | Completed Δ: +3,000
```
**Means:** English source grew by 2,500 words, but translations grew by 3,000 words.
**Conclusion:** Translators are catching up! Coverage is improving.

---

## 🗂️ File Management

### Files Created

| File | When Created | Auto-Delete? | Backup? |
|------|--------------|--------------|---------|
| `wordcount_history.json` | First run | ❌ Never | ✅ Yes (weekly) |
| `WordCountAnalysis_*.xlsx` | Every run | ✅ Old versions | Optional |

### Storage Pattern

```
After 30 runs:
├── wordcount_history.json          (1 file, ~500KB)
└── WordCountAnalysis_20251118_150432.xlsx  (1 file, latest only)
```

**Key point:** Only ONE Excel file exists at a time (latest). All historical data is in JSON.

---

## 🎯 Use Cases

### Daily Progress Tracking
**Frequency:** Every day at 9 AM
**Sheet to review:** Daily Diff - Full
**Goal:** Track yesterday's progress
**Audience:** Team leads

### Weekly Team Reports
**Frequency:** Every Friday
**Sheet to review:** Weekly Diff - Full
**Goal:** 7-day progress summary
**Audience:** Project managers

### Monthly Stakeholder Updates
**Frequency:** End of month
**Sheet to review:** Monthly Diff - Full + Detailed
**Goal:** 30-day progress and category analysis
**Audience:** Executives, stakeholders

### Problem Identification
**Frequency:** As needed
**Sheet to review:** Detailed sheets
**Goal:** Find categories with low/negative progress
**Audience:** Team leads, translators

---

## 🔍 Behind the Scenes: Smart Comparison Logic

### How the Script Finds Comparison Runs

**User enters:** 2025-11-18

**Daily (1 day back):**
1. Target date: 2025-11-17
2. Script searches JSON for runs before 2025-11-18
3. Finds closest to 2025-11-17
4. Uses that run for daily diff

**Weekly (7 days back):**
1. Target date: 2025-11-11
2. Script searches JSON for runs before 2025-11-18
3. Finds closest to 2025-11-11 (could be 11-10 or 11-12)
4. Uses that run for weekly diff

**Monthly (30 days back):**
1. Target date: 2025-10-19
2. Script searches JSON for runs before 2025-11-18
3. Finds closest to 2025-10-19 (could be 10-18 or 10-20)
4. Uses that run for monthly diff

**Result:** Flexible, works even with irregular run schedules!

---

## 💡 Key Design Decisions

### Why JSON for History?
✅ Human-readable (can open and inspect)
✅ Easy to query
✅ No database setup needed
✅ Git-friendly (can track in version control)
✅ Fast for thousands of runs

### Why Delete Old Excel Files?
✅ Prevents confusion about which report is current
✅ Saves disk space
✅ Forces use of latest data
✅ JSON is the source of truth anyway

### Why User-Provided Date?
✅ Data date ≠ processing date
✅ Allows backfilling historical data
✅ More accurate diff calculations
✅ Flexibility for different scenarios

---

## 📈 Growth Pattern

### History File Growth

| Runs | JSON Size | Disk Space | Performance |
|------|-----------|------------|-------------|
| 10 | ~50 KB | Minimal | Instant |
| 100 | ~500 KB | Negligible | <1 second |
| 1,000 | ~5 MB | Small | ~2 seconds |
| 10,000 | ~50 MB | Moderate | ~10 seconds |

**Recommendation:** Can easily handle years of daily runs (365 runs/year = 1.8 MB/year)

---

## 🚀 Performance Characteristics

### What Affects Runtime?

| Factor | Impact | Typical Range |
|--------|--------|---------------|
| Number of XML files | High | 20-90 seconds |
| Size of XML files | Medium | +10-30 seconds for large files |
| Number of languages | Medium | +5 seconds per 10 languages |
| Number of historical runs | Low | +1 second per 1000 runs |
| Disk speed | Low | SSD vs HDD: ~10 second difference |

### Typical Runtimes

| Scenario | Runtime |
|----------|---------|
| Small project (5 languages, 500 files) | 30 seconds |
| Medium project (10 languages, 1000 files) | 60 seconds |
| Large project (15 languages, 2000 files) | 90 seconds |

---

## 📋 Summary Checklist

### Before Running
- [ ] Python 3.7+ installed
- [ ] Dependencies installed (`pip install lxml openpyxl`)
- [ ] Folder paths configured (lines 40-41)
- [ ] XML files exist in configured folders
- [ ] Old Excel reports closed

### During Run
- [ ] Enter correct date (YYYY-MM-DD)
- [ ] Wait for all 6 phases to complete (~1 minute)
- [ ] Note any error messages

### After Run
- [ ] Excel report generated successfully
- [ ] JSON history updated
- [ ] Review Excel for expected data
- [ ] Check for anomalies (unexpected large changes)
- [ ] Backup JSON if first run or milestone

---

## 📚 Related Documentation

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `ROADMAP.md` | Technical implementation details | Development/debugging |
| `USER_GUIDE_CONFLUENCE.md` | Comprehensive user guide | Full reference |
| `USER_GUIDE_EXCEL.md` | Quick reference tables | Quick lookups |
| `wordcount_diff_master.py` | Source code | Customization/troubleshooting |

---

**Last Updated:** 2025-11-18
**Version:** 1.0
**Status:** Production Ready

---

*For questions or issues, review the troubleshooting sections in the user guides.*
