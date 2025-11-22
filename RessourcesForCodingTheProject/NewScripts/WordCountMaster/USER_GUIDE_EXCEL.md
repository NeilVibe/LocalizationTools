# WordCount Diff Master - Excel Quick Reference Guide

**⚠️ V2.0 UPDATE (2025-11-18) - SIMPLIFIED VERSION**

This guide is for **V2.0** which is MUCH SIMPLER:
- ✅ Always compares TODAY vs. past date
- ✅ Smart categorization (8 days → Weekly, 39 days → Monthly)
- ✅ 4 sheets instead of 6
- ✅ Dynamic period titles
- ❌ NO daily diffs

**See V2_COMPLETE.md for full details!**

**Instructions: Copy each table into Excel as separate sheets or tabs**

---

## SHEET 1: OVERVIEW

| Section | Details |
|---------|---------|
| **Script Name** | wordcount_diff_master.py |
| **Version** | 2.0 (Simplified) |
| **Purpose** | Compare TODAY's data vs. any past date with smart Weekly/Monthly categorization |
| **Location** | RessourcesForCodingTheProject/NewScripts/WordCountMaster/ |
| **Output Files** | WordCountAnalysis_YYYYMMDD_HHMMSS.xlsx (4 sheets), wordcount_history.json |
| **Runtime** | ~1 minute (typical) |
| **Dependencies** | Python 3.7+, lxml, openpyxl |
| **Status** | ✅ V2.0 Complete (1015 lines) |

---

## SHEET 2: QUICK START

| Step | Action | Command/Details | Expected Result |
|------|--------|-----------------|-----------------|
| 1 | Install dependencies | `pip install lxml openpyxl` | Libraries installed |
| 2 | Navigate to folder | `cd RessourcesForCodingTheProject/NewScripts/WordCountMaster/` | In correct directory |
| 3 | Run script | `python wordcount_diff_master.py` | Script starts |
| 4 | Enter date | Type: `2025-11-18` (YYYY-MM-DD) | Script processes data |
| 5 | Wait for completion | 6 phases run (~1 minute) | Excel report generated |
| 6 | Open report | `WordCountAnalysis_YYYYMMDD_HHMMSS.xlsx` | View results in Excel |

---

## SHEET 3: WHAT IT DOES

| Feature | Description | Benefit |
|---------|-------------|---------|
| **Daily Diff** | Compares against yesterday's data | Track daily progress |
| **Weekly Diff** | Compares against data from ~7 days ago | See weekly trends |
| **Monthly Diff** | Compares against data from ~30 days ago | Monitor monthly progress |
| **Historical Tracking** | Maintains complete history in JSON | Never lose data |
| **Multi-Language** | Tracks all languages simultaneously | Single comprehensive view |
| **Category Breakdown** | Detailed analysis by content category | Identify problem areas |
| **Auto-Cleanup** | Deletes old Excel reports | Always current data |
| **Color-Coded** | Green/Red/Gray for changes | Quick visual understanding |

---

## SHEET 4: WORKFLOW

| Phase | What Happens | Duration | Output |
|-------|--------------|----------|--------|
| User Input | Enter data date (YYYY-MM-DD) | 5 seconds | Date captured |
| Phase 1 | Scan XML language files | 20-30 seconds | Word count data collected |
| Phase 2 | Load history from JSON | 1-2 seconds | Previous runs loaded |
| Phase 3 | Calculate diffs (daily/weekly/monthly) | 2-5 seconds | Diff calculations complete |
| Phase 4 | Update JSON history | 1-2 seconds | History saved |
| Phase 5 | Delete old Excel reports | 1 second | Old files removed |
| Phase 6 | Generate new Excel report (6 sheets) | 10-20 seconds | New report created |
| **TOTAL** | **Complete workflow** | **~1 minute** | **Excel + JSON ready** |

---

## SHEET 5: EXCEL REPORT STRUCTURE

### Summary: 6 Sheets Generated

| Sheet # | Sheet Name | Content | Use Case |
|---------|------------|---------|----------|
| 1 | Daily Diff - Full | Language summary with daily changes | Check today's progress |
| 2 | Weekly Diff - Full | Language summary with weekly changes | Weekly team reports |
| 3 | Monthly Diff - Full | Language summary with monthly changes | Monthly stakeholder updates |
| 4 | Daily Diff - Detailed | Category breakdown with daily changes | Identify daily problem areas |
| 5 | Weekly Diff - Detailed | Category breakdown with weekly changes | Track weekly category trends |
| 6 | Monthly Diff - Detailed | Category breakdown with monthly changes | Long-term category analysis |

### Columns in Full Summary Sheets (Sheets 1-3)

| Column | Description | Example Value | Notes |
|--------|-------------|---------------|-------|
| Language | 3-letter language code | ENG, FRA, DEU | Auto-detected from folders |
| Total Words | Total word count | 125,000 | All source words |
| Completed Words | Translated word count | 98,000 | Words with translations |
| Coverage % | Translation completion percentage | 78.4% | Completed/Total × 100 |
| Total Δ | Net change in total words | +2,500 | Green if positive |
| Total Δ% | Percent change in total | +2.0% | Relative change |
| Completed Δ | Net change in completed words | +3,000 | Translation progress |
| Completed Δ% | Percent change in completed | +3.2% | Translation velocity |
| Coverage Δ | Net change in coverage | +0.8 | Percentage point change |
| Coverage Δ% | Percent change in coverage | +1.0% | Relative coverage change |

### Columns in Detailed Sheets (Sheets 4-6)

**IMPORTANT**: Detailed sheets use a per-language table format (matching wordcount1.py):
- Each language has its own table section
- Language title row (bold): "Language: ENG"
- Header row for that language
- Category data rows
- Yellow separator
- Then next language's table

| Column | Description | Example Value | Notes |
|--------|-------------|---------------|-------|
| Category | Content category name | Faction, Main, Sequencer + Other | From folder structure (no Language column!) |
| Total Words | Category total words | 15,000 | Category-specific |
| Completed Words | Category completed words | 14,500 | Category progress |
| Coverage % | Category coverage | 96.7% | Category completion |
| Total Δ | Category total change | +500 | Category growth |
| Total Δ% | Percent change in category total | +3.4% | Category velocity |
| Completed Δ | Category completed change | +400 | Category progress |
| Completed Δ% | Percent change in category completed | +2.8% | Category translation velocity |

---

## SHEET 6: COLOR LEGEND

| Color | RGB Code | Meaning | When You See It | Action |
|-------|----------|---------|-----------------|--------|
| 🟢 Green | #00B050 | Positive change (increase) | Progress made, words added | ✅ Good! Keep going |
| 🔴 Red | #FF0000 | Negative change (decrease) | Words lost, coverage dropped | ⚠️ Investigate why |
| ⚫ Gray | #808080 | No change (zero) | No difference from previous | ℹ️ Normal, no action |
| 🔵 Blue | #4F81BD | Column header | Top row of each sheet | ℹ️ Information only |
| 🟡 Yellow | #FFFF00 | Language separator | Between different languages | ℹ️ Visual separator |

---

## SHEET 7: COMMON SCENARIOS

| Scenario | When to Use | Steps | Expected Outcome |
|----------|-------------|-------|------------------|
| **First Run** | Initial setup | 1. Run script<br>2. Enter today's date<br>3. Note "No comparison data" | JSON history created, baseline set |
| **Daily Tracking** | Every day | 1. Run script daily at same time<br>2. Enter today's date<br>3. Check "Daily Diff - Full" | See yesterday's changes |
| **Weekly Reports** | Every Friday | 1. Run script weekly<br>2. Enter today's date<br>3. Check "Weekly Diff - Full"<br>4. Share with team | 7-day progress report |
| **Monthly Reports** | End of month | 1. Run script monthly<br>2. Enter today's date<br>3. Check "Monthly Diff - Full"<br>4. Share with stakeholders | 30-day progress report |
| **Backfill History** | Add past data | 1. Run with old date (e.g., 2025-10-01)<br>2. Run with next date (2025-10-08)<br>3. Continue chronologically | Historical data populated |
| **Missing Comparison** | "No comparison data" shows | 1. Keep running regularly<br>2. Wait 7 days for weekly<br>3. Wait 30 days for monthly | Diffs appear automatically |

---

## SHEET 8: TROUBLESHOOTING

| Error | Cause | Solution | Prevention |
|-------|-------|----------|------------|
| "Invalid date format" | Wrong date format used | Use YYYY-MM-DD (e.g., 2025-11-18) | Always use ISO format |
| "No such file or directory" | Folder path incorrect | Edit lines 40-41 in script with correct paths | Verify paths before first run |
| "Permission denied" | Excel file open | Close old Excel file | Close files before running |
| All zeros in Excel | XML structure mismatch | Check XML files for `<LocStr>` elements | Verify XML structure matches expected |
| JSONDecodeError | Corrupted history file | Rename to .backup, start fresh | Regular backups of JSON |
| Script hangs | Large XML files | Wait longer, or check for infinite loop | Normal for large datasets |
| Missing languages | Language folder empty | Verify XML files exist in loc folder | Check folder structure |
| Wrong diffs | Incorrect date entered | Re-run with correct date | Double-check date before confirming |

---

## SHEET 9: FILE REFERENCE

### Files Generated

| File Name | Format | Location | Purpose | Auto-Delete? | Backup? |
|-----------|--------|----------|---------|--------------|---------|
| WordCountAnalysis_YYYYMMDD_HHMMSS.xlsx | Excel | Script folder | Main report with all diffs | Yes (old versions) | Optional |
| wordcount_history.json | JSON | Script folder | Complete historical data | No | ✅ YES! |

### Files Required

| File Name | Format | Location | Purpose | Required? |
|-----------|--------|----------|---------|-----------|
| wordcount_diff_master.py | Python | Script folder | Main executable | ✅ Yes |
| LanguageData_*.xml | XML | F:\perforce\...\loc | Source language files | ✅ Yes |
| (export files) | XML | F:\perforce\...\export__ | Export category files | ✅ Yes |

---

## SHEET 10: JSON HISTORY STRUCTURE

| Level | Field | Type | Description | Example |
|-------|-------|------|-------------|---------|
| Root | runs | Array | List of all historical runs | [...] |
| Root | metadata | Object | Summary metadata | {...} |
| runs[0] | run_id | String | Unique run identifier | "2025-11-18_143022" |
| runs[0] | data_date | String | Date of data processed | "2025-11-18" |
| runs[0] | run_timestamp | String | When script was run | "2025-11-18T14:30:22" |
| runs[0] | languages | Object | All language data | {...} |
| languages.ENG | full_summary | Object | Language-level totals | {...} |
| languages.ENG | detailed_categories | Object | Category breakdowns | {...} |
| full_summary | total_words | Number | Total word count | 125000 |
| full_summary | completed_words | Number | Completed word count | 98000 |
| full_summary | word_coverage_pct | Number | Coverage percentage | 78.4 |
| metadata | total_runs | Number | Total number of runs | 42 |
| metadata | first_run | String | Earliest run ID | "2025-10-01_120000" |
| metadata | last_run | String | Most recent run ID | "2025-11-18_143022" |

---

## SHEET 11: CONFIGURATION

### Default Settings

| Setting | Default Value | Location in Script | Customizable? |
|---------|---------------|-------------------|---------------|
| Language folder | F:\perforce\cd\mainline\resource\GameData\stringtable\loc | Line 40 | ✅ Yes |
| Export folder | F:\perforce\cd\mainline\resource\GameData\stringtable\export__ | Line 41 | ✅ Yes |
| History JSON name | wordcount_history.json | Line 42 | ✅ Yes |
| Excel prefix | WordCountAnalysis | Line 43 | ✅ Yes |
| Daily period | 1 day | Line 429 | ✅ Yes |
| Weekly period | 7 days | Line 429 | ✅ Yes |
| Monthly period | 30 days | Line 429 | ✅ Yes |

### How to Customize

| What to Change | Find This Line | Change To | Example |
|----------------|----------------|-----------|---------|
| Language folder path | `LANGUAGE_FOLDER = Path(r"F:\...")` | Your path | `Path(r"C:\MyProject\loc")` |
| Export folder path | `EXPORT_FOLDER = Path(r"F:\...")` | Your path | `Path(r"C:\MyProject\export")` |
| Diff periods | `("daily", 1), ("weekly", 7), ("monthly", 30)` | Your periods | `("daily", 1), ("biweekly", 14), ("quarterly", 90)` |

---

## SHEET 12: BEST PRACTICES

| Practice | Category | Importance | Details | Impact |
|----------|----------|------------|---------|--------|
| Run regularly | Consistency | 🔴 High | Run daily or weekly at same time | Accurate daily diffs |
| Enter correct date | Accuracy | 🔴 High | Use data capture date, not processing date | Correct historical tracking |
| Backup JSON | Safety | 🔴 High | Copy wordcount_history.json weekly | Protect historical data |
| Close old Excel | Stability | 🟡 Medium | Close previous reports before running | Avoid "permission denied" |
| Chronological backfill | Accuracy | 🟡 Medium | Process historical dates in order | Correct diff calculations |
| Same time daily | Consistency | 🟢 Low | Run at same time each day | Consistent 24-hour diffs |
| Archive important reports | Organization | 🟢 Low | Save milestone reports separately | Historical reference |

### DO's ✅

| DO | Why | How |
|----|-----|-----|
| ✅ Run regularly | Maintain continuous history | Schedule daily/weekly runs |
| ✅ Enter correct date | Ensure accurate diffs | Double-check date format |
| ✅ Backup JSON history | Protect your data | Weekly copy to safe location |
| ✅ Close old Excel files | Avoid file locks | Close before running script |
| ✅ Verify first run | Confirm setup works | Check Excel structure after first run |
| ✅ Monitor for anomalies | Catch data issues early | Review large unexpected changes |

### DON'Ts ❌

| DON'T | Why | Instead Do This |
|-------|-----|-----------------|
| ❌ Edit JSON manually | Risk corruption | Let script manage it |
| ❌ Delete JSON file | Lose all history | Rename to .backup if needed |
| ❌ Run with Excel open | File permission errors | Close Excel first |
| ❌ Enter future dates | Confusing diffs | Use actual data date |
| ❌ Skip chronology when backfilling | Incorrect diffs | Process dates in order |
| ❌ Modify XML during run | Data corruption | Wait until script finishes |

---

## SHEET 13: FAQ

| Question | Answer | Details |
|----------|--------|---------|
| How long does it take? | ~1 minute | Depends on file count and size. Typical: 30-90 seconds |
| Can I run multiple times per day? | Yes | Each run creates new timestamped report, appends to history |
| What if I skip days? | No problem | Script finds closest previous run for comparisons |
| Can I delete old runs from JSON? | Not recommended | JSON can handle thousands of runs efficiently |
| Can I compare different projects? | Not currently | Run separate script copies for each project |
| What if XML structure differs? | Modify script | Edit `analyse_file` and `analyse_export_file` functions |
| Can I export to PDF/HTML? | Not yet | Future enhancement (see ROADMAP.md) |
| What languages are supported? | All | Auto-detects any language folders |

---

## SHEET 14: KEYBOARD SHORTCUTS (When Viewing Excel Report)

| Shortcut | Action | Use Case |
|----------|--------|----------|
| Ctrl + Home | Go to cell A1 | Return to top |
| Ctrl + End | Go to last used cell | See full data range |
| Ctrl + Page Down | Next sheet | Navigate between sheets |
| Ctrl + Page Up | Previous sheet | Navigate backward |
| Ctrl + F | Find | Search for specific language/category |
| Alt + H + O + I | Auto-fit column width | Make columns readable |
| Ctrl + Arrow | Jump to edge of data | Quick navigation |
| F5 | Go to cell | Jump to specific cell |

---

## SHEET 15: EXAMPLE DATA

### Example: Full Summary Sheet

| Language | Total Words | Completed Words | Coverage % | Total Δ | Total Δ% | Completed Δ | Completed Δ% |
|----------|-------------|-----------------|------------|---------|----------|-------------|--------------|
| ENG | 125,000 | 98,000 | 78.4% | +2,500 | +2.0% | +3,000 | +3.2% |
| FRA | 110,000 | 88,000 | 80.0% | +1,200 | +1.1% | +2,100 | +2.4% |
| DEU | 115,000 | 92,000 | 80.0% | +800 | +0.7% | +1,500 | +1.7% |
| ESP | 108,000 | 86,000 | 79.6% | +1,000 | +0.9% | +1,800 | +2.1% |
| ITA | 105,000 | 84,000 | 80.0% | +900 | +0.9% | +1,600 | +1.9% |

### Example: Detailed Sheet

**Structure: Each language has its own table**

```
Language: ENG  (bold title row)

| Category          | Total Words | Completed Words | Coverage % | Total Δ | Total Δ% | Completed Δ | Completed Δ% |
|-------------------|-------------|-----------------|------------|---------|----------|-------------|--------------|
| Faction           | 15,000      | 14,500          | 96.7%      | +500    | +3.4%    | +400        | +2.8%        |
| Main              | 25,000      | 24,000          | 96.0%      | +300    | +1.2%    | +250        | +1.0%        |
| Sequencer + Other | 30,000      | 22,000          | 73.3%      | +1,000  | +3.4%    | +1,200      | +5.8%        |
| System            | 20,000      | 15,000          | 75.0%      | +200    | +1.3%    | +150        | +1.0%        |
| World             | 35,000      | 26,500          | 75.7%      | +500    | +1.4%    | +400        | +1.5%        |

═══════════════════════════════════════════════════════  (yellow separator row)

Language: FRA  (bold title row)

| Category          | Total Words | Completed Words | Coverage % | Total Δ | Total Δ% | Completed Δ | Completed Δ% |
|-------------------|-------------|-----------------|------------|---------|----------|-------------|--------------|
| Faction           | 14,800      | 14,200          | 95.9%      | +450    | +3.1%    | +380        | +2.7%        |
| Main              | 24,500      | 23,500          | 95.9%      | +280    | +1.2%    | +240        | +1.0%        |
| Sequencer + Other | 29,000      | 21,500          | 74.1%      | +900    | +3.2%    | +850        | +4.1%        |
| System            | 19,500      | 14,500          | 74.4%      | +180    | +1.2%    | +140        | +1.0%        |
| World             | 34,000      | 25,800          | 75.9%      | +480    | +1.4%    | +380        | +1.5%        |

═══════════════════════════════════════════════════════  (yellow separator row)

... (continues for each language)
```

**Note**: Each language gets its own complete table with headers - this matches the familiar wordcount1.py format!

---

## SHEET 16: METRICS & STATS

| Metric | Value | Notes |
|--------|-------|-------|
| **Script Metrics** | | |
| Lines of Code | 703 | Full implementation |
| Number of Functions | 24 | Well-structured |
| Dependencies | 2 | lxml, openpyxl |
| Python Version Required | 3.7+ | Modern Python |
| Average Runtime | 1 minute | Typical usage |
| **Report Metrics** | | |
| Sheets per Report | 6 | 3 full + 3 detailed |
| Columns per Full Sheet | 10 | Comprehensive data |
| Columns per Detailed Sheet | 9 | Category-specific |
| Colors Used | 5 | Green, Red, Gray, Blue, Yellow |
| **History Metrics** | | |
| Storage Format | JSON | Human-readable |
| Max Runs Recommended | 10,000+ | Efficient storage |
| Backup Frequency | Weekly | Recommended |

---

## SHEET 17: SUPPORT CHECKLIST

### Before Requesting Support

| Check | Status | Details |
|-------|--------|---------|
| ☐ Read troubleshooting section | | See SHEET 8 |
| ☐ Verify Python version | `python --version` | Requires 3.7+ |
| ☐ Verify dependencies installed | `pip list` | Check lxml, openpyxl |
| ☐ Check folder paths | Lines 40-41 | Must exist on system |
| ☐ Verify XML files exist | Browse folders | Check loc and export__ |
| ☐ Check JSON file | Open in text editor | Valid JSON format? |
| ☐ Review error message | Copy exact text | Note line numbers |
| ☐ Try fresh JSON | Rename to .backup | Start clean history |

### Information to Provide

| Info | How to Get It | Why Needed |
|------|---------------|------------|
| Python version | `python --version` | Compatibility check |
| Error message | Copy full output | Diagnosis |
| Script location | Full path | Verify setup |
| XML file sample | First 50 lines | Structure verification |
| JSON excerpt | First run object | History format check |
| OS version | Windows/Linux/Mac | Environment details |

---

## SHEET 18: VERSION INFO

| Field | Value |
|-------|-------|
| **Document Information** | |
| Guide Name | WordCount Diff Master - Excel Quick Reference |
| Version | 1.0 |
| Created | 2025-11-18 |
| Format | Excel Quick Reference (Markdown source) |
| Author | Generated with Claude Code |
| **Script Information** | |
| Script Name | wordcount_diff_master.py |
| Script Version | 1.0 |
| Script Lines | 703 |
| Implementation Status | ✅ Complete |
| Testing Status | Ready for UAT |
| **Related Documents** | |
| Technical Roadmap | ROADMAP.md |
| Confluence Guide | USER_GUIDE_CONFLUENCE.md |
| Source Reference | wordcount1.py |

---

## INSTRUCTIONS FOR EXCEL CONVERSION

### How to Use This Guide in Excel:

1. **Copy each section** (SHEET 1, SHEET 2, etc.) into separate Excel tabs
2. **Format headers** with bold text and colored backgrounds
3. **Apply color coding** according to SHEET 6 (Color Legend)
4. **Auto-fit columns** for readability
5. **Add filters** to data tables for easy searching
6. **Freeze top row** on each sheet for scrolling
7. **Print areas** - Set for each sheet if printing needed

### Recommended Excel Formatting:

| Element | Format | Color |
|---------|--------|-------|
| Sheet tab names | Bold | Blue (#4F81BD) |
| Table headers | Bold, White text | Blue background (#4F81BD) |
| Section headers | Bold, 14pt | Black |
| Data rows | Regular, 11pt | Alternating white/light gray |
| Positive numbers | Green | #00B050 |
| Negative numbers | Red | #FF0000 |
| Zero values | Gray | #808080 |

---

**END OF QUICK REFERENCE GUIDE**

*For detailed technical information, see USER_GUIDE_CONFLUENCE.md*
*For development details, see ROADMAP.md*
