h1. WordCount Diff Master - User Guide

{warning:title=V2.0 UPDATE - November 2025-11-18}
*THIS GUIDE IS FOR V2.0 (SIMPLIFIED VERSION)*

*Major Changes in V2.0:*
* ❌ Removed daily diffs (only Weekly & Monthly now)
* ✅ Always compares TODAY vs. past date (much simpler!)
* ✅ Smart auto-categorization (8 days → Weekly, 39 days → Monthly)
* ✅ 4 sheets instead of 6
* ✅ Dynamic period titles in each sheet

*See {{V2_COMPLETE.md}} for full V2.0 details and examples!*
{warning}

{panel:title=Quick Reference|borderStyle=solid|borderColor=#ccc|titleBGColor=#4F81BD|titleColor=#fff|bgColor=#f5f5f5}
*Script Name:* {{wordcount_diff_master.py}}
*Version:* 2.0
*Purpose:* Track translation word count changes by comparing TODAY vs. any past date
*Output:* Excel reports with 4 sheets (Weekly/Monthly × Full/Detailed)
*Location:* {{RessourcesForCodingTheProject/NewScripts/WordCountMaster/}}
{panel}

----

h2. 📋 Table of Contents

{toc:minLevel=2|maxLevel=3}

----

h1. Overview

h2. What Does This Script Do?

The *WordCount Diff Master* automatically tracks your translation progress over time and generates comprehensive Excel reports showing:

* ✅ *Daily changes* - What changed since yesterday
* ✅ *Weekly changes* - Progress over the past 7 days
* ✅ *Monthly changes* - Progress over the past 30 days
* ✅ *Historical tracking* - Maintains a complete history in JSON format
* ✅ *Multi-language support* - Tracks all languages simultaneously
* ✅ *Category breakdown* - Detailed analysis by content category

h2. Key Features

{info:title=Smart Diff Tracking}
The script automatically finds the best comparison dates for daily, weekly, and monthly diffs. You just provide the data date, and it handles the rest!
{info}

* *Automated History* - Builds a complete timeline of your translation progress
* *Intelligent Comparisons* - Finds the closest previous run for accurate diffs
* *Color-Coded Reports* - Green for progress, red for decreases, gray for no change
* *Zero Manual Work* - Just run the script and enter the data date
* *Always Up-to-Date* - Old reports are replaced with fresh data each run

----

h1. Prerequisites

h2. Required Software

|| Software || Version || Purpose ||
| Python | 3.7+ | Script runtime |
| lxml | Latest | XML parsing |
| openpyxl | Latest | Excel generation |

h2. Installation

{code:language=bash}
# Install dependencies
pip install lxml openpyxl
{code}

h2. Required Folder Structure

{warning:title=Important Paths}
The script expects these folders to exist on your system:
{warning}

{code}
F:\perforce\cd\mainline\resource\GameData\stringtable\loc      (Language files)
F:\perforce\cd\mainline\resource\GameData\stringtable\export__ (Export files)
{code}

{tip}
If your paths are different, edit lines 40-41 in the script to match your setup.
{tip}

----

h1. How It Works

h2. The Workflow Diagram

{code}
┌─────────────────────────────────────┐
│ 1. User Runs Script                 │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 2. Enter Data Date (YYYY-MM-DD)     │
│    Example: 2025-11-18              │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 3. Script Scans XML Files           │
│    - Parse language files           │
│    - Count total words              │
│    - Count completed words          │
│    - Calculate coverage %           │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 4. Load History (JSON)              │
│    - Read previous runs             │
│    - Find comparison dates          │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 5. Calculate Diffs                  │
│    - Daily: vs yesterday            │
│    - Weekly: vs 7 days ago          │
│    - Monthly: vs 30 days ago        │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 6. Save to History                  │
│    - Append new run to JSON         │
│    - Update metadata                │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 7. Delete Old Excel Reports         │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ 8. Generate New Excel Report        │
│    - 6 sheets with all diffs        │
│    - Color-coded changes            │
│    - Save with timestamp            │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│ ✓ Done! Report Ready                │
└─────────────────────────────────────┘
{code}

h2. Data Flow

{panel:title=Data Flow|borderStyle=solid|borderColor=#4F81BD}
*XML Files* → *Word Count Data* → *JSON History* → *Diff Calculations* → *Excel Report*
{panel}

----

h1. Step-by-Step Usage Guide

h2. Step 1: Navigate to Script Folder

{code:language=bash}
cd RessourcesForCodingTheProject/NewScripts/WordCountMaster/
{code}

h2. Step 2: Run the Script

{code:language=bash}
python wordcount_diff_master.py
{code}

h2. Step 3: Enter Data Date

The script will prompt you:

{noformat}
============================================================
WordCount Diff Master Report Generator
============================================================

============================================================
Enter the date of the data you're processing:
Format: YYYY-MM-DD (e.g., 2025-11-18)
============================================================
Date: _
{noformat}

{info:title=What Date Should I Enter?}
Enter the date that corresponds to *when the translation data was captured*, not necessarily today's date. This allows accurate historical tracking and backfilling.
{info}

*Examples:*
* If you're processing today's data: {{2025-11-18}}
* If you're processing yesterday's data: {{2025-11-17}}
* If you're backfilling historical data: {{2025-10-15}}

h2. Step 4: Wait for Processing

The script will run through 6 phases:

{code}
[1/6] Scanning language files...
      ✓ Processed 12 languages

[2/6] Loading history...
      ✓ Found 15 previous runs

[3/6] Calculating diffs...
      ✓ Daily: vs 2025-11-17
      ✓ Weekly: vs 2025-11-11
      ✓ Monthly: vs 2025-10-18

[4/6] Updating history...
      ✓ History updated (total runs: 16)

[5/6] Cleaning up old reports...
      ✓ Deleted old report: WordCountAnalysis_20251117_143022.xlsx

[6/6] Generating Excel report...
      ✓ Report saved: WordCountAnalysis_20251118_150432.xlsx
{code}

h2. Step 5: Open the Report

{noformat}
============================================================
✓ COMPLETE
============================================================
Report: F:\path\to\WordCountAnalysis_20251118_150432.xlsx
History: F:\path\to\wordcount_history.json
============================================================
{noformat}

{tip:title=Find Your Files}
* *Excel Report:* Same folder as the script, named {{WordCountAnalysis_YYYYMMDD_HHMMSS.xlsx}}
* *JSON History:* Same folder, named {{wordcount_history.json}}
{tip}

----

h1. Understanding the Excel Report

h2. Report Structure

The Excel report contains *6 sheets*:

|| Sheet # || Sheet Name || Content ||
| 1 | Daily Diff - Full | Language summary with daily changes |
| 2 | Weekly Diff - Full | Language summary with weekly changes |
| 3 | Monthly Diff - Full | Language summary with monthly changes |
| 4 | Daily Diff - Detailed | Category breakdown with daily changes |
| 5 | Weekly Diff - Detailed | Category breakdown with weekly changes |
| 6 | Monthly Diff - Detailed | Category breakdown with monthly changes |

h2. Sheet 1-3: Full Summary Sheets

h3. Column Structure

|| Column || Description || Example ||
| Language | 3-letter language code | ENG, FRA, DEU |
| Total Words | Total word count in source | 125,000 |
| Completed Words | Words that have been translated | 98,000 |
| Coverage % | Percentage translated | 78.4% |
| Total Δ | Net change in total words | +2,500 |
| Total Δ% | Percent change in total words | +2.0% |
| Completed Δ | Net change in completed words | +3,000 |
| Completed Δ% | Percent change in completed | +3.2% |
| Coverage Δ | Net change in coverage | +0.8 |
| Coverage Δ% | Percent change in coverage | +1.0% |

h3. Example View

{noformat}
┌──────────┬─────────────┬─────────────────┬────────────┬──────────┬───────────┬───────────────┬─────────────────┐
│ Language │ Total Words │ Completed Words │ Coverage % │ Total Δ  │ Total Δ%  │ Completed Δ   │ Completed Δ%    │
├──────────┼─────────────┼─────────────────┼────────────┼──────────┼───────────┼───────────────┼─────────────────┤
│ ENG      │ 125,000     │ 98,000          │ 78.4%      │ +2,500   │ +2.0%     │ +3,000        │ +3.2%           │
│ FRA      │ 110,000     │ 88,000          │ 80.0%      │ +1,200   │ +1.1%     │ +2,100        │ +2.4%           │
│ DEU      │ 115,000     │ 92,000          │ 80.0%      │ +800     │ +0.7%     │ +1,500        │ +1.7%           │
└──────────┴─────────────┴─────────────────┴────────────┴──────────┴───────────┴───────────────┴─────────────────┘
{noformat}

h2. Sheet 4-6: Detailed Category Sheets

h3. Structure Overview

{info:title=Per-Language Table Format}
Each language has its OWN table section:
# *Language title row* (bold): "Language: ENG"
# *Header row*: Category | Total Words | Completed Words | Coverage % | diffs...
# *Category data rows*: Faction, Main, Sequencer + Other, System, World, etc.
# *Yellow separator row*
# Then next language's table
{info}

This matches the familiar wordcount1.py format - one table per language!

h3. Column Structure

|| Column || Description || Example ||
| Category | Content category name | Faction, Main, Sequencer + Other |
| Total Words | Total words in category | 15,000 |
| Completed Words | Completed words in category | 14,500 |
| Coverage % | Category coverage | 96.7% |
| Total Δ | Net change in total | +500 |
| Total Δ% | Percent change in category total | +3.4% |
| Completed Δ | Net change in completed | +400 |
| Completed Δ% | Percent change in completed | +2.8% |

h3. Example View

{noformat}
Language: ENG                                                   ← Bold title row
┌─────────────────────┬─────────────┬─────────────────┬────────────┬──────────┬───────────┐
│ Category            │ Total Words │ Completed Words │ Coverage % │ Total Δ  │ Total Δ%  │ ← Header
├─────────────────────┼─────────────┼─────────────────┼────────────┼──────────┼───────────┤
│ Faction             │ 15,000      │ 14,500          │ 96.7%      │ +500     │ +3.4%     │
│ Main                │ 25,000      │ 24,000          │ 96.0%      │ +300     │ +1.2%     │
│ Sequencer + Other   │ 30,000      │ 22,000          │ 73.3%      │ +1,000   │ +3.4%     │
│ System              │ 20,000      │ 15,000          │ 75.0%      │ +200     │ +1.3%     │
│ World               │ 35,000      │ 26,500          │ 75.7%      │ +500     │ +1.4%     │
└─────────────────────┴─────────────┴─────────────────┴────────────┴──────────┴───────────┘
════════════════════════════════════════════════════════════════════════════════  ← Yellow separator

Language: FRA                                                   ← Bold title row
┌─────────────────────┬─────────────┬─────────────────┬────────────┬──────────┬───────────┐
│ Category            │ Total Words │ Completed Words │ Coverage % │ Total Δ  │ Total Δ%  │ ← Header
├─────────────────────┼─────────────┼─────────────────┼────────────┼──────────┼───────────┤
│ Faction             │ 14,800      │ 14,200          │ 95.9%      │ +450     │ +3.1%     │
│ Main                │ 24,500      │ 23,500          │ 95.9%      │ +280     │ +1.2%     │
│ Sequencer + Other   │ 29,000      │ 21,500          │ 74.1%      │ +900     │ +3.2%     │
│ System              │ 19,500      │ 14,500          │ 74.4%      │ +180     │ +1.2%     │
│ World               │ 34,000      │ 25,800          │ 75.9%      │ +480     │ +1.4%     │
└─────────────────────┴─────────────┴─────────────────┴────────────┴──────────┴───────────┘
════════════════════════════════════════════════════════════════════════════════  ← Yellow separator

... (and so on for each language)
{noformat}

{note}
*Key Point*: Each language gets its own complete table with headers. This makes it easy to focus on one language at a time!
{note}

h2. Understanding the Colors

{panel:title=Color Legend|borderStyle=solid}
* {color:green}*Green Numbers*{color} = Positive change (progress made!)
* {color:red}*Red Numbers*{color} = Negative change (translation lost or reduced)
* {color:gray}*Gray Numbers*{color} = No change (0)
* *Blue Headers* = Column headers
* *Yellow Rows* = Language separators
{panel}

----

h1. Understanding the JSON History

h2. What is wordcount_history.json?

The JSON file is the *single source of truth* for all historical data. The script:
* Appends new data on each run
* Never deletes historical data
* Uses this data to calculate all diffs

h2. JSON Structure

{code:language=json}
{
  "runs": [
    {
      "run_id": "2025-11-18_143022",
      "data_date": "2025-11-18",
      "run_timestamp": "2025-11-18T14:30:22",
      "languages": {
        "ENG": {
          "full_summary": {
            "total_words": 125000,
            "completed_words": 98000,
            "word_coverage_pct": 78.4
          },
          "detailed_categories": {
            "Faction": {
              "total_words": 15000,
              "completed_words": 14500,
              "word_coverage_pct": 96.67
            }
          }
        }
      }
    }
  ],
  "metadata": {
    "total_runs": 42,
    "first_run": "2025-10-01_120000",
    "last_run": "2025-11-18_143022"
  }
}
{code}

{warning:title=Do Not Manually Edit}
The JSON file is automatically managed by the script. Manual editing may corrupt the history!
{warning}

----

h1. Common Scenarios

h2. Scenario 1: First Time Running the Script

{panel:title=First Run Behavior}
On the first run:
* No history file exists yet
* Script creates {{wordcount_history.json}}
* Excel report shows "No comparison data" for all diffs
* This is *normal* - diffs will appear on the second run
{panel}

*What to do:*
1. Run the script normally
2. Note that all diffs show "No comparison data"
3. Run again tomorrow/next week to see diffs appear

h2. Scenario 2: Daily Progress Tracking

*Goal:* Track progress every day

*Steps:*
1. Run the script daily (e.g., every morning)
2. Enter today's date when prompted
3. Review the "Daily Diff - Full" sheet for today's progress
4. Check "Daily Diff - Detailed" for category-specific changes

{tip:title=Best Practice}
Run at the same time each day for consistent daily diffs (e.g., every morning at 9 AM).
{tip}

h2. Scenario 3: Weekly Progress Reports

*Goal:* Generate weekly progress reports for stakeholders

*Steps:*
1. Run the script once per week (e.g., every Friday)
2. Open the Excel report
3. Focus on "Weekly Diff - Full" sheet
4. Share with team/management

{info}
Weekly diffs show progress over the past ~7 days, comparing against the closest run from a week ago.
{info}

h2. Scenario 4: Backfilling Historical Data

*Goal:* Add historical data from past dates

*Steps:*
1. Run the script with an old date (e.g., {{2025-10-01}})
2. Run again with the next date (e.g., {{2025-10-08}})
3. Continue until you reach the current date
4. Diffs will be calculated based on the dates you enter

{warning}
Process historical dates in chronological order for accurate diffs!
{warning}

h2. Scenario 5: Entering Past Dates (Robust Date Logic)

{panel:title=The Question}
What if I enter a date from 8 days ago? Or 13 days ago? Or 39 days ago?
{panel}

*Answer:* The script handles this perfectly! **All comparisons are relative to the date you enter, not today.**

*Examples:*

|| You Enter || Daily Diff Compares || Weekly Diff Compares || Monthly Diff Compares ||
| 2025-11-18 (today) | vs 2025-11-17 (1 day before) | vs 2025-11-11 (7 days before) | vs 2025-10-19 (30 days before) |
| 2025-11-10 (8 days ago) | vs 2025-11-09 (1 day before that) | vs 2025-11-03 (7 days before that) | vs 2025-10-11 (30 days before that) |
| 2025-11-05 (13 days ago) | vs 2025-11-04 (1 day before that) | vs 2025-10-29 (7 days before that) | vs 2025-10-06 (30 days before that) |
| 2025-10-10 (39 days ago) | vs 2025-10-09 (1 day before that) | vs 2025-10-03 (7 days before that) | vs 2025-09-10 (30 days before that) |

{info:title=Key Insight}
The script finds the *closest* previous run to each target date. So even if you don't have exact matches, it still calculates meaningful diffs!
{info}

*Why this is useful:*
* Backfilling historical data works perfectly
* Processing delayed data (e.g., data from last week) works correctly
* Diffs are always accurate relative to the data date, not when you ran the script

h2. Scenario 6: Missing Comparison Data

{panel:title=When This Happens}
You see "No comparison data" for weekly or monthly diffs.
{panel}

*Why:*
* You haven't been running the script for 7+ or 30+ days yet
* The history doesn't contain runs from those periods

*Solution:*
* Keep running the script regularly
* After 7 days, weekly diffs will appear
* After 30 days, monthly diffs will appear

----

h1. Troubleshooting

h2. Error: "Invalid date format"

{code}
❌ Invalid date format. Please use YYYY-MM-DD
{code}

*Cause:* Date entered in wrong format

*Solution:* Use format {{YYYY-MM-DD}} (e.g., {{2025-11-18}})

|| ❌ Wrong || ✅ Correct ||
| 11-18-2025 | 2025-11-18 |
| 18/11/2025 | 2025-11-18 |
| 2025.11.18 | 2025-11-18 |
| Nov 18 2025 | 2025-11-18 |

h2. Error: "No such file or directory"

{code}
FileNotFoundError: F:\perforce\cd\mainline\resource\GameData\stringtable\loc
{code}

*Cause:* Language folder path doesn't exist on your system

*Solution:* Edit lines 40-41 in the script to match your folder paths:

{code:language=python}
# Change these to your actual paths
LANGUAGE_FOLDER = Path(r"YOUR\PATH\TO\loc")
EXPORT_FOLDER = Path(r"YOUR\PATH\TO\export__")
{code}

h2. Error: "Permission denied" when deleting old reports

{code}
Warning: Could not delete WordCountAnalysis_20251117_143022.xlsx
{code}

*Cause:* Old Excel file is open in Excel

*Solution:* Close the Excel file and run the script again

h2. Excel Report Shows All Zeros

{panel:title=Possible Causes}
* XML files are empty
* XML files have different structure than expected
* Language codes don't match
{panel}

*Solution:*
1. Check that XML files exist in the configured folders
2. Open an XML file and verify it contains {{<LocStr>}} elements
3. Verify the structure matches the expected format

h2. JSON File Corrupted

{code}
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
{code}

*Cause:* {{wordcount_history.json}} is corrupted or empty

*Solution:*
1. Rename {{wordcount_history.json}} to {{wordcount_history.json.backup}}
2. Run the script - it will create a fresh history file
3. You'll lose historical data, but can start fresh

----

h1. Advanced Usage

h2. Customizing Folder Paths

Edit the script (lines 40-41):

{code:language=python}
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")
{code}

Change to your paths:

{code:language=python}
LANGUAGE_FOLDER = Path(r"C:\MyProject\loc")
EXPORT_FOLDER = Path(r"C:\MyProject\export")
{code}

h2. Changing Diff Periods

By default, the script calculates:
* Daily: 1 day back
* Weekly: 7 days back
* Monthly: 30 days back

To customize, edit line 429 in the script:

{code:language=python}
# Change the numbers to your preferred periods
for period, days_back in [("daily", 1), ("weekly", 7), ("monthly", 30)]:
{code}

Examples:
* Bi-weekly: {{("biweekly", 14)}}
* Quarterly: {{("quarterly", 90)}}
* Custom: {{("custom", 5)}}

h2. Automating the Script

h3. Windows Task Scheduler

{code:language=bash}
# Create a batch file: run_wordcount.bat
@echo off
cd C:\path\to\WordCountMaster
python wordcount_diff_master.py
pause
{code}

Schedule it in Task Scheduler to run daily at a specific time.

h3. Linux Cron Job

{code:language=bash}
# Add to crontab (run daily at 9 AM)
0 9 * * * cd /path/to/WordCountMaster && python3 wordcount_diff_master.py
{code}

{warning:title=Automation Note}
Automated runs still require manual date input. You may need to modify the script to accept date as a command-line argument for full automation.
{warning}

----

h1. Best Practices

h2. ✅ Do's

{panel:title=Recommended Practices|borderStyle=solid|borderColor=#00B050}
* ✅ Run the script regularly (daily or weekly)
* ✅ Enter the correct data date (when data was captured)
* ✅ Keep the JSON history file safe - it's your complete record
* ✅ Archive old Excel reports if needed (script keeps only the latest)
* ✅ Run at consistent times for accurate daily diffs
* ✅ Backup {{wordcount_history.json}} periodically
* ✅ Close old Excel reports before running the script
{panel}

h2. ❌ Don'ts

{panel:title=Things to Avoid|borderStyle=solid|borderColor=#FF0000}
* ❌ Don't manually edit {{wordcount_history.json}}
* ❌ Don't delete {{wordcount_history.json}} unless you want to start fresh
* ❌ Don't run the script while old Excel reports are open
* ❌ Don't enter future dates (creates confusing diffs)
* ❌ Don't process dates out of chronological order when backfilling
* ❌ Don't modify the XML source files while script is running
{panel}

h2. Tips for Success

{tip:title=Pro Tips}
# *Consistent Schedule* - Run at the same time for accurate comparisons
# *Meaningful Dates* - Use the actual data capture date, not processing date
# *Backup History* - Copy {{wordcount_history.json}} to a safe location weekly
# *Check First Run* - After first run, verify Excel structure looks correct
# *Watch for Anomalies* - Large unexpected changes may indicate data issues
# *Archive Reports* - Save important milestone reports to a separate folder
{tip}

----

h1. FAQ

h2. Q: How long does the script take to run?

{panel}
*A:* Typically 30-90 seconds, depending on:
* Number of XML files to process
* Size of XML files
* Number of historical runs in JSON
* System performance

For typical usage (~10 languages, ~1000 files), expect ~1 minute.
{panel}

h2. Q: Can I run the script multiple times per day?

{panel}
*A:* Yes! You can run it as many times as you want. Each run:
* Appends to history
* Generates a new timestamped Excel report
* Deletes the previous report

Just be aware that if you run multiple times with the same data date, you'll have duplicate entries in the history.
{panel}

h2. Q: What happens if I skip days?

{panel}
*A:* No problem! The script finds the *closest* previous run for each diff period. If you skip days:
* Daily diff: Compares against the most recent run (even if it's 3 days ago)
* Weekly/Monthly: Finds the closest run to 7/30 days back

The diffs will still be accurate based on what data exists.
{panel}

h2. Q: Can I delete old runs from the JSON history?

{panel}
*A:* Technically yes, but *not recommended*. The JSON file is designed to keep all history. If you must clean it:
1. Open {{wordcount_history.json}} in a text editor
2. Find the {{runs}} array
3. Carefully remove old run objects
4. Update the {{metadata}} section
5. Save and test

*Better approach:* Just let it grow. JSON is efficient and can handle thousands of runs.
{panel}

h2. Q: Can I compare across different projects?

{panel}
*A:* Not with the current version. The script tracks one project at a time. For multiple projects:
* Run separate copies of the script in different folders
* Each will maintain its own {{wordcount_history.json}}
* Each will generate its own Excel reports
{panel}

h2. Q: What if my XML structure is different?

{panel}
*A:* The script expects XML files with:
* {{<LocStr>}} elements
* {{StrOrigin}} attribute (source text)
* {{korean_re}} pattern for detecting Korean

If your structure differs, you'll need to modify the parsing logic in the script (functions {{analyse_file}} and {{analyse_export_file}}).
{panel}

h2. Q: Can I export data to other formats (PDF, HTML)?

{panel}
*A:* Not currently. The script outputs:
* Excel ({{.xlsx}})
* JSON ({{wordcount_history.json}})

Future enhancements could add PDF/HTML export. See the ROADMAP.md for planned features.
{panel}

----

h1. Support & Feedback

h2. Need Help?

{info:title=Getting Support}
If you encounter issues:
1. Check the *Troubleshooting* section above
2. Review the error message carefully
3. Check that your folder paths are correct
4. Verify XML files are in the expected format
5. Contact the script maintainer
{info}

h2. Feature Requests

Have ideas for improvements? Check {{ROADMAP.md}} for planned features, or suggest new ones!

h2. Report Issues

Found a bug? Please report:
* What you were trying to do
* The exact error message
* Your Python version ({{python --version}})
* Sample data (if possible)

----

h1. Appendix

h2. A. File Outputs

|| File || Purpose || Format || Auto-Delete ||
| {{WordCountAnalysis_*.xlsx}} | Main report | Excel | Yes (old versions) |
| {{wordcount_history.json}} | Historical data | JSON | No |

h2. B. Script Metrics

|| Metric || Value ||
| Lines of Code | 703 |
| Number of Functions | 24 |
| Dependencies | lxml, openpyxl |
| Python Version | 3.7+ |
| Average Runtime | 1 minute |

h2. C. Language Codes Supported

The script auto-detects all language folders. Common codes:

|| Code || Language ||
| ENG | English |
| FRA | French |
| DEU | German |
| ESP | Spanish |
| ITA | Italian |
| POL | Polish |
| POR | Portuguese |
| RUS | Russian |
| TUR | Turkish |
| CHN | Chinese |
| JPN | Japanese |
| KOR | Korean |

h2. D. Version History

|| Version || Date || Changes ||
| 1.0 | 2025-11-18 | Initial release |

----

{panel:title=Document Information|borderStyle=solid|bgColor=#f0f0f0}
*Document:* WordCount Diff Master User Guide
*Version:* 1.0
*Last Updated:* 2025-11-18
*Format:* Confluence Wiki Markup
*Author:* Generated with Claude Code
{panel}

----

_For technical implementation details, see {{ROADMAP.md}}_
