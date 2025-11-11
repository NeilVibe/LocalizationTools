# Project Cleanup Plan

## Problem: 58 MARKDOWN FILES (should be ~15 max)

### ROOT LEVEL: 17 files → Should be 7

**KEEP:**
- ✅ `README.md` - Main project documentation
- ✅ `Claude.md` - Instructions for Claude AI
- ✅ `Roadmap.md` - Main roadmap (consolidate others into this)
- ✅ `BEST_PRACTICES.md` - Development best practices
- ✅ `MONITORING_GUIDE.md` - System monitoring and troubleshooting
- ✅ `QUICK_TEST_COMMANDS.md` - Quick reference for testing (NEW)
- ✅ `SYSTEM_TEST_REPORT_2025-11-10.md` - Latest test report (NEW)

**DELETE (10 temporary/duplicate files):**
- ❌ `ROADMAP_UPDATE_2025-11-10.md` - Merge into Roadmap.md, then delete
- ❌ `README_FOR_USER.md` - Redundant with README.md
- ❌ `FIXES_2025-11-10_PART2.md` - Temporary session notes
- ❌ `FIX_PLAN.md` - Temporary session notes
- ❌ `ISSUE_ANALYSIS.md` - Temporary session notes
- ❌ `PHASE3_TESTING_CHECKLIST.md` - Temporary session notes
- ❌ `PROGRESS_TRACKING_TEST_RESULTS.md` - Temporary session notes
- ❌ `SESSION_SUMMARY_2025-11-10.md` - Temporary session notes
- ❌ `TEST_COMPLETE_FLOW.md` - Temporary session notes
- ❌ `WELCOME_BACK_PART2.md` - Temporary session notes

### DOCS FOLDER: 16 files → Should be ~12

**CONSOLIDATE:**
- `docs/MONITORING_SYSTEM.md` + `docs/MONITORING_SYSTEM_FIXED.md` → Keep one
- `docs/TESTING.md` + `docs/TESTING_GUIDE.md` → Keep TESTING_GUIDE.md

**DELETE:**
- ❌ `docs/MONITORING_SYSTEM_FIXED.md` (merge into MONITORING_SYSTEM.md)
- ❌ `docs/TESTING.md` (keep TESTING_GUIDE.md)

### SCRIPTS FOLDER: 2 READMEs

**CONSOLIDATE:**
- ❌ `scripts/SCRIPTS_README.md` - Merge into scripts/README.md

### OTHER DUPLICATES

**In subdirectories:**
- `adminDashboard/README.md` and `adminDashboard/QUICKSTART.md` (both OK, different purposes)
- `locaNext/README.md` and `locaNext/QUICKSTART.md` (both OK, different purposes)

### SUMMARY

**Files to delete:** 13
**Files to consolidate:** 3
**Final count:** ~42 markdown files (down from 58)

### CLEANUP COMMANDS

```bash
# Delete temporary session notes (ROOT)
rm -f ROADMAP_UPDATE_2025-11-10.md
rm -f README_FOR_USER.md
rm -f FIXES_2025-11-10_PART2.md
rm -f FIX_PLAN.md
rm -f ISSUE_ANALYSIS.md
rm -f PHASE3_TESTING_CHECKLIST.md
rm -f PROGRESS_TRACKING_TEST_RESULTS.md
rm -f SESSION_SUMMARY_2025-11-10.md
rm -f TEST_COMPLETE_FLOW.md
rm -f WELCOME_BACK_PART2.md

# Delete duplicates in docs
rm -f docs/MONITORING_SYSTEM_FIXED.md
rm -f docs/TESTING.md

# Delete duplicate in scripts
rm -f scripts/SCRIPTS_README.md
```

## OTHER PARASITIC FILES TO CHECK

Need to check for:
- Empty database files
- Duplicate log files
- Temp/cache files
- Old backup files

