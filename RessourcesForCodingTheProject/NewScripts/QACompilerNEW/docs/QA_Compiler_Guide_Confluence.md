{toc:printable=true|style=disc|maxLevel=3|indent=20px|minLevel=1|class=bigpink|exclude=[1];.*|type=list|outline=true|include=.*}

----

h1. QA Compiler Suite v2.0 - Complete User Guide

{panel:title=Document Info|borderStyle=solid|borderColor=#ccc|titleBGColor=#f0f0f0|bgColor=#ffffff}
*Version:* 2.0.0
*Last Updated:* 2025-01-15
*Status:* Production Ready
{panel}

----

h2. 1. Overview

The *QA Compiler Suite v2.0* is a unified tool for managing Language Quality Assurance (LQA) workflows.

{info:title=Key Capabilities}
* *Datasheet Generation* - Create Excel datasheets from game XML sources
* *File Transfer* - Preserve tester work when updating datasheets
* *Master File Building* - Compile QA files with manager workflow
* *Coverage Analysis* - Calculate coverage and word counts
{info}

h3. Key Features

||Feature||Description||
|EN/CN Separation|Automatic routing of testers to English or Chinese master files|
|Manager Workflow|STATUS columns for FIXED/REPORTED/CHECKING/NON-ISSUE tracking|
|Progress Tracker|Automatic daily/total statistics with rankings|
|Category Clustering|Skill and Help merge into System; Gimmick merges into Item|
|Image Handling|Automatic image copying with hyperlink preservation|

----

h2. 2. Requirements

h3. Software Requirements

||Requirement||Version||Notes||
|Python|3.8+|Required|
|openpyxl|Latest|Excel file handling|
|lxml|Latest|XML parsing|
|tkinter|Built-in|GUI (included with Python)|

{code:language=bash|title=Installation}
pip install openpyxl lxml
{code}

h3. Access Requirements

{warning:title=Required Access}
* Read access to game resource paths (Perforce workspace)
* Write access to output folders
* Network access to {{F:\perforce\cd\mainline\}}
{warning}

----

h2. 3. Installation & Setup

h3. Step 1: Extract the Package

Extract {{QACompilerNEW.zip}} to your desired location:

{code}
C:\Tools\QACompilerNEW\
{code}

h3. Step 2: Configure Paths

Edit {{config.py}} to match your environment:

{code:language=python|title=config.py}
# Game resource paths (MUST be accessible)
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
{code}

h3. Step 3: Set Up Tester Mapping

Create or edit {{languageTOtester_list.txt}}:

{code:title=languageTOtester_list.txt}
ENG
TesterName1
TesterName2

ZHO-CN
TesterName3
TesterName4
{code}

h3. Step 4: Create Required Folders

{note}
Folders are auto-created on first run, or create manually:
{note}

{code}
QACompilerNEW/
├── QAfolder/           # Compiled QA files
├── QAfolderOLD/        # OLD QA files for transfer
├── QAfolderNEW/        # NEW datasheets for transfer
├── Masterfolder_EN/    # English master output
├── Masterfolder_CN/    # Chinese master output
└── GeneratedDatasheets/ # Generated datasheets
{code}

h3. Step 5: Verify Setup

{code:language=bash}
python main.py --version
python main.py --list
{code}

----

h2. 4. Folder Structure

h3. Complete Directory Layout

{code:title=Directory Structure}
QACompilerNEW/
│
├── main.py                      # Entry point (GUI + CLI)
├── config.py                    # All configuration
├── languageTOtester_list.txt    # Tester -> Language mapping
│
├── core/                        # Compiler core modules
│   ├── compiler.py              # Main orchestration
│   ├── transfer.py              # File transfer logic
│   ├── discovery.py             # QA folder detection
│   ├── processing.py            # Sheet processing
│   └── excel_ops.py             # Excel operations
│
├── generators/                  # Datasheet generators
│   ├── base.py                  # Shared utilities
│   ├── quest.py                 # Quest datasheets
│   ├── knowledge.py             # Knowledge datasheets
│   ├── item.py                  # Item datasheets
│   └── ...                      # Other generators
│
├── tracker/                     # Progress tracker
│   ├── data.py                  # Data operations
│   ├── daily.py                 # DAILY sheet builder
│   └── total.py                 # TOTAL sheet + rankings
│
├── gui/                         # GUI module
│   └── app.py                   # Tkinter application
│
├── QAfolder/                    # Working QA files
├── Masterfolder_EN/             # English output
├── Masterfolder_CN/             # Chinese output
└── GeneratedDatasheets/         # Generated datasheets
{code}

h3. QA Folder Naming Convention

{warning:title=CRITICAL}
QA folders MUST follow this exact naming: *\{TesterName\}_\{Category\}*
{warning}

||Valid Examples||Invalid Examples||
|John_Quest|John Quest (spaces)|
|Mary_Item|Mary-Item (hyphens)|
|Chen_Knowledge|chen knowledge (lowercase + space)|

*Valid Categories:* Quest, Knowledge, Item, Region, System, Character, Skill, Help, Gimmick

----

h2. 5. Configuration

h3. Path Configuration

{code:language=python|title=config.py - Paths}
# Game resource paths
RESOURCE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\StaticInfo")
LANGUAGE_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc")
EXPORT_FOLDER = Path(r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__")

# Quest-specific paths
QUESTGROUPINFO_FILE = Path(r"...\questgroupinfo.staticinfo.xml")
SCENARIO_FOLDER = Path(r"...\scenario")
FACTION_QUEST_FOLDER = Path(r"...\quest\faction")
FACTIONINFO_FOLDER = Path(r"...\StaticInfo\factioninfo")
{code}

h3. Category Clustering

||Input Category||Target Master||
|Skill|Master_System.xlsx|
|Help|Master_System.xlsx|
|Gimmick|Master_Item.xlsx|

h3. Translation Column Mapping

||Category||ENG Column||Other Column||
|Quest|2|3|
|Knowledge|2|3|
|Item|5 (ItemName)|7|
|System|1 (CONTENT)|1|

----

h2. 6. Functionalities

h3. 6.1 Generate Datasheets

{panel:title=Purpose|borderStyle=solid|borderColor=#006699|titleBGColor=#006699|titleColor=#ffffff|bgColor=#e6f3ff}
Create Excel datasheets from game XML files for QA testers
{panel}

h4. What It Does

# Reads game XML source files (StaticInfo)
# Loads language translation tables
# Builds structured Excel workbooks with translations

h4. Output Columns

||Column||Description||
|Original|Korean source text|
|ENG|English translation|
|Translation|Target language (hidden for ENG)|
|StringKey|Identifier for commands|
|Command|/complete, /teleport commands|
|STATUS|Dropdown: ISSUE, NO ISSUE, BLOCKED, KOREAN|
|COMMENT|Tester notes|
|STRINGID|Unique string identifier|
|SCREENSHOT|Screenshot reference|

----

h3. 6.2 Transfer QA Files

{panel:title=Purpose|borderStyle=solid|borderColor=#006699|titleBGColor=#006699|titleColor=#ffffff|bgColor=#e6f3ff}
Transfer tester work from OLD datasheets to NEW datasheets while preserving all QA data
{panel}

h4. How It Works

{code:title=Transfer Flow}
QAfolderOLD/          QAfolderNEW/          QAfolder/
(Tester's work)  +    (New empty)     =    (Merged result)
   STATUS                Empty               STATUS preserved
   COMMENT               Empty               COMMENT preserved
   SCREENSHOT            Empty               SCREENSHOT preserved
{code}

h4. Matching Algorithm (Two-Pass)

||Pass||Standard Categories||Item Category||
|1 - Exact|STRINGID + Translation|ItemName + ItemDesc + STRINGID|
|2 - Fallback|Translation only|ItemName + ItemDesc only|

----

h3. 6.3 Build Master Files

{panel:title=Purpose|borderStyle=solid|borderColor=#006699|titleBGColor=#006699|titleColor=#ffffff|bgColor=#e6f3ff}
Compile individual QA files into centralized Master files with manager workflow support
{panel}

h4. What It Does

# Discovers all QA folders in {{QAfolder/}}
# Routes testers to EN or CN based on mapping
# Creates/updates Master files per category
# Adds per-user columns: STATUS, COMMENT, SCREENSHOT
# Copies images with unique names
# Preserves manager status
# Updates Progress Tracker

h4. Per-User Columns Added

* {{STATUS_\{Username\}}} - Manager status
* {{COMMENT_\{Username\}}} - Notes with metadata
* {{SCREENSHOT_\{Username\}}} - Image references

----

h3. 6.4 Coverage Analysis

{panel:title=Purpose|borderStyle=solid|borderColor=#006699|titleBGColor=#006699|titleColor=#ffffff|bgColor=#e6f3ff}
Calculate how much of the language data is covered by generated datasheets
{panel}

h4. Metrics

* *String Coverage:* Unique Korean strings in datasheets vs. language master
* *Word Count:* Total words (EN) or characters (CN) per category

h4. Output

* Terminal report with coverage percentages
* Excel file: {{Coverage_Report_YYYYMMDD_HHMMSS.xlsx}}

----

h2. 7. GUI Usage

h3. Launching the GUI

{code:language=bash}
python main.py
# or
python main.py --gui
{code}

h3. GUI Layout

{panel:bgColor=#f5f5f5}
{code}
┌──────────────────────────────────────────────────┐
│           QA Compiler Suite v2.0                 │
├──────────────────────────────────────────────────┤
│  1. Generate Datasheets                          │
│     ☑ Quest      ☑ Knowledge   ☑ Item            │
│     [Select All] [Deselect] [Generate Selected]  │
├──────────────────────────────────────────────────┤
│  2. Transfer QA Files                            │
│     [Transfer QA Files]                          │
├──────────────────────────────────────────────────┤
│  3. Build Master Files                           │
│     [Build Master Files]                         │
├──────────────────────────────────────────────────┤
│  4. Coverage Analysis                            │
│     [Run Coverage Analysis]                      │
└──────────────────────────────────────────────────┘
{code}
{panel}

----

h2. 8. CLI Usage

h3. Basic Commands

{code:language=bash|title=CLI Commands}
# Show help
python main.py --help

# Show version
python main.py --version

# List available categories
python main.py --list
{code}

h3. Generate Datasheets

{code:language=bash}
# Generate specific categories
python main.py --generate quest knowledge item

# Generate all categories
python main.py --generate all

# Multiple -g flags
python main.py -g quest -g item -g region
{code}

h3. Transfer Files

{code:language=bash}
python main.py --transfer
python main.py -t
{code}

h3. Build Master Files

{code:language=bash}
python main.py --build
python main.py -b
{code}

h3. Full Pipeline

{code:language=bash}
# Transfer + Build in one command
python main.py --all
python main.py -a
{code}

----

h2. 9. Tester Mapping

h3. File Format

{code:title=languageTOtester_list.txt}
ENG
TesterName1
TesterName2
TesterName3

ZHO-CN
TesterName4
TesterName5
{code}

h3. Rules

* Section headers: {{ENG}} or {{ZHO-CN}}
* One tester name per line (exact match with folder names)
* Empty lines are ignored
* *Testers NOT in the mapping default to EN*

h3. Routing Effect

||Tester||Language||Output Folder||
|John|EN|Masterfolder_EN/|
|Mary|EN|Masterfolder_EN/|
|Chen|CN|Masterfolder_CN/|
|Unknown|EN (default)|Masterfolder_EN/|

----

h2. 10. Categories & Generators

h3. Category Overview

||#||Category||Description||
|1|Quest|Main/Faction/Daily/Challenge/Minigame quests|
|2|Knowledge|Knowledge entries with hierarchical groups|
|3|Item|Items with descriptions and group organization|
|4|Region|Faction/Region exploration data|
|5|System|Skill + Help combined|
|6|Character|NPC/Monster character info|
|7|Skill|Player skills with knowledge linking|
|8|Help|GameAdvice/Help system entries|
|9|Gimmick|Interactive gimmick objects|

h3. Quest Tab Organization

{code}
Quest_LQA_ENG.xlsx
├── Main Quest           (scenario-based)
├── Faction 1           (OrderByString from factioninfo)
├── Faction 2
├── Region Quest         (*_Request StrKey)
├── Daily                (*_Daily + Group="daily")
├── Politics             (*_Situation StrKey)
├── Challenge Quest
├── Minigame Quest
└── Others               (leftover factions)
{code}

----

h2. 11. Output Files

h3. Generated Datasheet Columns

||Column||Description||
|Original|Korean source text|
|ENG|English translation|
|\{Language\}|Target language (hidden for ENG)|
|StringKey|Identifier for /complete commands|
|Command|Cheat commands (see Quest Command Structure)|
|STATUS|Dropdown: ISSUE, NO ISSUE, BLOCKED, KOREAN|
|COMMENT|Tester notes|
|STRINGID|Unique string identifier|
|SCREENSHOT|Image filename|

h3. Quest Command Structure (Daily/Politics/Region Quest tabs)

The Command column contains cheat commands in this order:

{code:title=Example Command}
/complete mission Mission_A && Mission_B    ← Prerequisites first
/complete prevmission Mission_X             ← Progress command
/teleport 1234 567 89                       ← Teleport last
{code}

*Auto-generated from:*
* Factioninfo {{<Quest Condition="...">}} attributes
* Quest XML {{<Branch Condition="..." Execute="...">}} elements

h3. Progress Tracker Sheets

||Sheet||Description||
|DAILY|EN/CN sections with daily deltas per user|
|TOTAL|Cumulative totals, category breakdown, rankings|
|_DAILY_DATA|Hidden raw data storage|

h3. TOTAL Sheet - Column Structure

||Section||Color||Columns||
|Tester Stats|Blue|User, Done, Issues, No Issue, Blocked, Korean|
|Manager Stats|Green|Fixed, Reported, NonIssue, Checking, Pending|
|Workload Analysis|Orange|Actual Done, Days Worked, Daily Avg, Type, Comment|

h4. Workload Analysis Columns

||Column||Source||Description||
|Actual Done|Auto|Done - Blocked - Korean|
|Days Worked|Manual|Manager fills in (PRESERVED)|
|Daily Avg|Auto|Actual Done ÷ Days Worked|
|Type|TesterType.txt|"Text" or "Gameplay"|
|Comment|Manual|Manager's notes (PRESERVED)|

{tip:title=Preserved Data}
*Days Worked* and *Comment* columns are automatically preserved when rebuilding the TOTAL sheet.
{tip}

h3. Ranking Formula

{note}
*Score = 80% Done + 20% Actual Issues*
(Higher is better - rewards both productivity and issue finding)
{note}

----

h2. 12. Workflow Examples

h3. Workflow A: New Project Setup

{code:language=bash}
# 1. Generate all datasheets
python main.py --generate all

# 2. Distribute datasheets to testers
# Copy from GeneratedDatasheets/ to testers

# 3. Wait for testers to complete work...

# 4. Collect tester work into QAfolder/

# 5. Build master files
python main.py --build
{code}

h3. Workflow B: Update Existing Project

{code:language=bash}
# 1. Testers' current work -> QAfolderOLD/
mv QAfolder/* QAfolderOLD/

# 2. Generate new datasheets -> QAfolderNEW/
python main.py --generate quest

# 3. Transfer work to preserve STATUS/COMMENT
python main.py --transfer

# 4. Build updated masters
python main.py --build
{code}

h3. Workflow C: Daily Compilation

{code:language=bash}
# One command for daily updates
python main.py --all
{code}

----

h2. 13. Best Practices

h3. Folder Naming

||Do||Don't||
|John_Quest|John Quest (spaces)|
|Mary_Item|Mary-Item (hyphens)|
|Chen_Knowledge|chen_knowledge (inconsistent)|

h3. Before Transfer

{warning}
# *Backup QAfolderOLD* - Transfer modifies files
# *Verify folder names match* - OLD and NEW must have same names
# *Check duplicate report* - Review if multiple comments exist
{warning}

h3. Manager Status Values

||Status||Meaning||
|FIXED|Issue has been fixed|
|REPORTED|Issue reported to devs|
|CHECKING|Under investigation|
|NON-ISSUE|Marked as not an issue|

----

h2. 14. Troubleshooting

h3. Common Issues

{expand:title="No valid QA folders found"}
*Cause:* Folder naming incorrect
*Solution:* Ensure format is \{TesterName\}_\{Category\}

{code}
# Check your folders
ls QAfolder/

# Should see:
# John_Quest/
# Mary_Item/
{code}
{expand}

{expand:title="Language folder not found"}
*Cause:* Path in config.py incorrect or not accessible
*Solution:*
# Check Perforce workspace is synced
# Verify path in config.py
# Ensure network drive is connected
{expand}

{expand:title="No matching NEW folder for transfer"}
*Cause:* OLD folder has no corresponding NEW folder
*Solution:* Ensure both folders exist with same name

{code}
QAfolderOLD/John_Quest/
QAfolderNEW/John_Quest/  <- Must exist!
{code}
{expand}

{expand:title="Images not appearing"}
*Cause:* Hyperlinks broken or images not copied
*Solution:*
# Check Images/ folder in Master output
# Verify image filenames match SCREENSHOT values
# Check for special characters in filenames
{expand}

----

h2. 15. Appendix

h3. Status Values Reference

h4. Tester Status (STATUS column)

||Value||Description||
|ISSUE|Translation issue found|
|NO ISSUE|Checked, no issue|
|BLOCKED|Cannot test|
|KOREAN|Korean text remaining|

h4. Manager Status (STATUS_\{User\} column)

||Value||Description||
|FIXED|Issue resolved|
|REPORTED|Sent to development|
|CHECKING|Under review|
|NON-ISSUE|Not a real issue|

h3. Supported Languages

ENG, FRE, DEU, SPA, ITA, JPN, ZHO, KOR, and more...

h3. File Size Limits

||Limit||Value||
|Maximum rows per sheet|1,048,576 (Excel limit)|
|Recommended max images|1,000 per folder|
|Progress tracker entries|Unlimited|

----

{panel:title=Document End|borderStyle=solid|borderColor=#ccc|bgColor=#f0f0f0}
*QA Compiler Suite v2.0 - User Guide*
Last updated: 2025-01-15
{panel}
