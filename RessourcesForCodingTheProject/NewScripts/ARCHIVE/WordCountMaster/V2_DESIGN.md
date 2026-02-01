# WordCountMaster V2.0 - Simplified Design

**Date**: 2025-11-18
**Status**: In Progress

---

## 🎯 V2.0 Goals: SIMPLIFICATION

### What Changed?
1. ❌ **Removed**: Daily diffs entirely
2. ✅ **Changed**: Always compare TODAY vs. selected PAST date
3. ✅ **Smart**: Auto-categorize as Weekly or Monthly based on days difference
4. ✅ **Simpler**: 4 sheets instead of 6

---

## 📊 New Workflow

### V1.0 (OLD - Complex):
```
1. User enters DATA DATE (could be past, present, future)
2. Script processes that DATE's data
3. Script calculates diffs:
   - Daily: vs 1 day before that date
   - Weekly: vs 7 days before that date
   - Monthly: vs 30 days before that date
4. Generates 6 sheets (Daily/Weekly/Monthly × Full/Detailed)
```

### V2.0 (NEW - Simple):
```
1. Script processes TODAY's data automatically
2. User enters PAST DATE to compare against
3. Script calculates days difference
4. Script determines category:
   - If closer to 7 days → Weekly
   - If closer to 30 days → Monthly
5. Generates 4 sheets (Weekly/Monthly × Full/Detailed)
   - Only the matching category pair has data
   - Other pair shows "N/A"
```

---

## 🧮 Categorization Logic

### How It Works:

```python
days_diff = today - past_date

# Calculate distances
dist_to_7 = |days_diff - 7|
dist_to_30 = |days_diff - 30|

# Determine category
if dist_to_7 < dist_to_30:
    category = "weekly"
else:
    category = "monthly"
```

### Examples:

| Past Date | Days Ago | Calculation | Category | Reason |
|-----------|----------|-------------|----------|--------|
| 2025-11-10 | 8 | \|8-7\|=1 < \|8-30\|=22 | **Weekly** | Closer to 7 |
| 2025-11-05 | 13 | \|13-7\|=6 < \|13-30\|=17 | **Weekly** | Closer to 7 |
| 2025-10-25 | 24 | \|24-7\|=17 < \|24-30\|=6 | **Monthly** | Closer to 30 |
| 2025-10-10 | 39 | \|39-7\|=32 > \|39-30\|=9 | **Monthly** | Closer to 30 |

---

## 📋 Excel Report Structure

### V1.0 (OLD - 6 sheets):
1. Daily Diff - Full Summary
2. Weekly Diff - Full Summary
3. Monthly Diff - Full Summary
4. Daily Diff - Detailed
5. Weekly Diff - Detailed
6. Monthly Diff - Detailed

### V2.0 (NEW - 4 sheets):
1. **Weekly Diff - Full Summary**
   - Has data if category = "weekly"
   - Shows "N/A - Select date ~7 days ago" if category = "monthly"

2. **Monthly Diff - Full Summary**
   - Has data if category = "monthly"
   - Shows "N/A - Select date ~30 days ago" if category = "weekly"

3. **Weekly Diff - Detailed**
   - Has data if category = "weekly"
   - Shows "N/A" if category = "monthly"

4. **Monthly Diff - Detailed**
   - Has data if category = "monthly"
   - Shows "N/A" if category = "weekly"

---

## 📝 Dynamic Titles

Each sheet with data will have a title showing the exact period:

### Example (8 days comparison):
```
Sheet: "Weekly Diff - Full Summary"
Title in cell A1: "Period: 2025-11-18 to 2025-11-10 (8 days)"
```

### Example (39 days comparison):
```
Sheet: "Monthly Diff - Full Summary"
Title in cell A1: "Period: 2025-11-18 to 2025-10-10 (39 days)"
```

---

## 🔄 Updated Workflow Diagram

```
┌─────────────────────────────┐
│ Run Script                  │
│ (Processes TODAY's data)    │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ TODAY: 2025-11-18           │
│ Enter past date: 2025-11-10 │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Calculate: 8 days difference│
│ |8-7|=1 < |8-30|=22         │
│ → Category: WEEKLY          │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Load past date from history │
│ (2025-11-10)                │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Compare TODAY vs PAST       │
│ Calculate diffs for all     │
│ languages & categories      │
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────┐
│ Generate Excel:             │
│ - Weekly Full ✓ (has data)  │
│ - Monthly Full (N/A)        │
│ - Weekly Detail ✓ (has data)│
│ - Monthly Detail (N/A)      │
│                             │
│ Title: "Period: 2025-11-18  │
│  to 2025-11-10 (8 days)"    │
└─────────────────────────────┘
```

---

## 💾 JSON History Changes

### V1.0 (OLD):
```json
{
  "runs": [
    {
      "run_id": "2025-11-18_143022",
      "data_date": "2025-11-18",  ← Date of the DATA
      "run_timestamp": "2025-11-18T14:30:22",
      "languages": {...}
    }
  ]
}
```

### V2.0 (NEW - Same structure, different meaning):
```json
{
  "runs": [
    {
      "run_id": "2025-11-18_143022",
      "data_date": "2025-11-18",  ← Date script was RUN (always today)
      "run_timestamp": "2025-11-18T14:30:22",
      "languages": {...}  ← Current state of XML files on that date
    }
  ]
}
```

**Key Change**: `data_date` now always equals the date the script was run (today), representing a snapshot of the current XML state.

---

## 🔧 Function Changes

### Removed Functions:
- ❌ `find_comparison_run()` - No longer needed (complex logic)
- ❌ `calculate_all_diffs()` - Replaced with simpler version

### New Functions:
- ✅ `determine_period_category()` - Smart weekly/monthly categorization
- ✅ `find_past_run_in_history()` - Simple exact date lookup
- ✅ `get_comparison_date_from_user()` - Renamed, asks for PAST date

### Modified Functions:
- ✅ `main()` - Simplified workflow
- ✅ `generate_excel_report()` - 4 sheets instead of 6, dynamic titles
- ✅ `create_full_summary_sheet()` - Adds period title
- ✅ `create_detailed_sheet()` - Adds period title

---

## 📖 User Experience Changes

### V1.0 (OLD):
```
Enter the date of the data you're processing:
Date: 2025-11-10
```
→ User could be confused about what date to enter

### V2.0 (NEW):
```
TODAY'S DATE: 2025-11-18
Enter a PAST date to compare against:
Examples:
  - Enter date ~7 days ago  → Shows in Weekly sheets
  - Enter date ~30 days ago → Shows in Monthly sheets
Past date: 2025-11-10
```
→ Crystal clear what to enter!

---

## ✅ Benefits of V2.0

1. **Simpler Logic**: Always compare today vs. past (no complex relative calculations)
2. **Clearer UX**: User knows they're comparing TODAY vs. a PAST date
3. **Fewer Sheets**: 4 instead of 6 (easier to navigate)
4. **Auto-Categorization**: Smart determination of weekly vs. monthly
5. **Exact Periods**: Dynamic titles show precise comparison period
6. **No Daily Clutter**: Removed daily diffs (not needed for most use cases)

---

## 🚀 Use Cases

### Use Case 1: Weekly Progress Check
```
User runs script on Friday
Enters last Friday's date (7 days ago)
→ Gets Weekly sheets showing week-over-week progress
Title: "Period: 2025-11-18 to 2025-11-11 (7 days)"
```

### Use Case 2: Monthly Report
```
User runs script on month-end
Enters date from ~30 days ago
→ Gets Monthly sheets showing month-over-month progress
Title: "Period: 2025-11-18 to 2025-10-19 (30 days)"
```

### Use Case 3: Custom Period (8 days)
```
User runs script today
Enters date from 8 days ago
→ Gets Weekly sheets (8 is closer to 7 than 30)
Title: "Period: 2025-11-18 to 2025-11-10 (8 days)"
→ User sees EXACT period in title!
```

---

## 📋 Implementation Checklist

### Script Updates:
- [ ] ✅ Update header documentation
- [ ] ✅ Rename `get_data_date_from_user()` → `get_comparison_date_from_user()`
- [ ] ✅ Add `determine_period_category()` function
- [ ] ✅ Add `find_past_run_in_history()` function
- [ ] ⏳ Remove `find_comparison_run()` function (complex)
- [ ] ⏳ Simplify `calculate_all_diffs()` → just calculate one set of diffs
- [ ] ⏳ Update `main()` function with new workflow
- [ ] ⏳ Update `generate_excel_report()` to create 4 sheets with dynamic titles
- [ ] ⏳ Update `create_full_summary_sheet()` to add period title row
- [ ] ⏳ Update `create_detailed_sheet()` to add period title row
- [ ] ⏳ Update JSON history append to use today's date

### Documentation Updates:
- [ ] Update ROADMAP.md with V2.0 changelog
- [ ] Update USER_GUIDE_CONFLUENCE.md with new workflow
- [ ] Update USER_GUIDE_EXCEL.md with 4-sheet structure
- [ ] Update WORKFLOW_SUMMARY.md with simplified flow
- [ ] Create V2_MIGRATION_GUIDE.md

---

## 🎯 Next Steps

1. **Complete Script Updates** ⏳ In Progress
2. **Test with Real Data**
3. **Update All Documentation**
4. **Create Migration Guide** (V1 → V2)

---

**Status**: Design Complete, Implementation In Progress
**Version**: 2.0
**Estimated Completion**: Today (2025-11-18)
