# NewScripts Creation Workflow

**Quick Reference Guide for Creating Scripts in the NewScripts Framework**

---

## 📋 Overview

This document outlines the **systematic workflow** for creating new localization scripts within the NewScripts framework. Follow these steps every time you need to build a new script.

---

## 🔀 Two Types of Tasks

Before starting work, determine which type of task you're doing:

### Type 1: Guide Creation for Existing Scripts
**Purpose**: Document how to use an existing script from RessourcesForCodingTheProject

**When**:
- User asks for a guide/documentation for an existing script
- User wants simple usage instructions for scripts in MAIN/SECONDARY PYTHON SCRIPTS
- No new code needs to be written

**Output Location**: `/RessourcesForCodingTheProject/guides/` folder

**Structure**:
```
RessourcesForCodingTheProject/
├── MAIN PYTHON SCRIPTS/
├── SECONDARY PYTHON SCRIPTS/
│   └── tmxtransfer8.py
└── guides/                          # Guides for existing scripts
    ├── tmxtransfer_guide_en.md
    ├── tmxtransfer_guide_kr.md
    └── [other_script]_guide_en.md
```

**Process**:
1. Read the existing script to understand functionality
2. Create clean, simple markdown guide(s)
3. Include step-by-step instructions with screenshots if needed
4. Place in `/RessourcesForCodingTheProject/guides/` folder
5. Naming convention: `[scriptname]_guide_[language].md`

---

### Type 2: New Mini-Project Based on Existing Script
**Purpose**: Build a new, enhanced version of an existing script

**When**:
- User wants to create a new script based on existing one
- User wants to expand/improve functionality
- New code development is required

**Output Location**: `/RessourcesForCodingTheProject/NewScripts/[ProjectName]/` folder

**Structure**:
```
NewScripts/
├── README.md
├── WORKFLOW.md
├── guides/                         # General NewScripts guides (optional)
└── ProjectName/                    # Your mini-project
    ├── ROADMAP.md                  # Development plan
    ├── project_script_MMDD.py      # Main script
    ├── tests/                      # Optional: test files
    ├── data/                       # Optional: sample data
    └── docs/                       # Project-specific guides
        ├── guide_en.md
        └── guide_kr.md
```

**Process**:
1. Create new folder: `NewScripts/[ProjectName]/`
2. Create ROADMAP.md with development plan
3. Build the new script using reference script as base
4. Follow the 7-step workflow below
5. Optionally create guides in project's `docs/` subfolder for project-specific documentation

---

## 🎯 Quick Decision Guide

**Ask yourself**: Am I writing new code?

- **NO** → Type 1: Guide Creation
  - Just documenting existing script from RessourcesForCodingTheProject
  - Goes in `/RessourcesForCodingTheProject/guides/`

- **YES** → Type 2: Mini-Project
  - Building/enhancing a script as new development
  - Gets its own folder in `/NewScripts/[ProjectName]/`
  - Can have project-specific docs in `/NewScripts/[ProjectName]/docs/`

---

## 🔄 The 7-Step Workflow

### Step 1: Understand the Request

**Goal**: Get crystal clear on what needs to be built

**Actions**:
- [ ] What is the input format? (XML, Excel, TXT, TMX, etc.)
- [ ] What is the output format?
- [ ] What processing/transformation is needed?
- [ ] Which languages are involved?
- [ ] Are there any special requirements? (GUI, batch processing, validation, etc.)

**Example Questions to Ask**:
- "Can you provide a sample of the input file?"
- "What should the output look like?"
- "Which languages need to be processed?"
- "Do you need a GUI or command-line tool?"

---

### Step 2: Find Reference Script(s)

**Goal**: Identify existing scripts with similar patterns

**Where to Look**:
1. **Main Scripts** (`RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/`)
   - Start here for complex, high-value patterns
2. **Secondary Scripts** (`RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/`)
   - 74 utility scripts with specific patterns

**Search Strategies**:
```bash
# Search by file type
grep -l "xml" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py
grep -l "excel" RessourcesForCodingTheProject/MAIN\ PYTHON\ SCRIPTS/*.py

# Search by language
grep -l "Korean" RessourcesForCodingTheProject/MAIN\ PYTHON\ SCRIPTS/*.py

# Search by operation
grep -l "conversion" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py
```

**Common Reference Scripts**:
| Need | Reference Script |
|------|-----------------|
| XML parsing | `translatexmlstable2.py`, `xmlatt13.py` |
| Excel handling | `XLSTransfer0225.py`, `xlscompare5.py` |
| TMX processing | `tmxconvert33.py` |
| Text processing | `extractchinese.py`, `quickregex3.py` |
| GUI (Tkinter) | `QS0305.py`, `TFMLITE0307.py` |
| File I/O patterns | Any of the main scripts |

---

### Step 3: Read & Absorb Patterns

**Goal**: Understand how the reference script works

**What to Extract**:
- [ ] Import statements (which libraries are used?)
- [ ] XML/Excel/text parsing approach
- [ ] Data structure patterns
- [ ] File I/O patterns (how do they read/write?)
- [ ] Error handling approach
- [ ] GUI patterns (if Tkinter is used)
- [ ] Naming conventions
- [ ] Code organization

**Key Patterns to Copy**:
```python
# File picker pattern
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
input_file = filedialog.askopenfilename(...)

# XML parsing pattern
import xml.etree.ElementTree as ET
tree = ET.parse(file)
root = tree.getroot()

# Excel pattern
import openpyxl
wb = openpyxl.load_workbook(file)
ws = wb.active
```

---

### Step 4: Plan the New Script

**Goal**: Create a roadmap before coding

**Create Script Folder**:
```bash
# Naming: Use descriptive name
NewScripts/ScriptName/
```

**Create ROADMAP.md**:
```markdown
# ScriptName Roadmap

## Purpose
[What does this script do?]

## Input
[Format and structure]

## Output
[Format and structure]

## Reference Script
[Which script did you base this on?]

## Development Plan
- [ ] Phase 1: Basic file I/O
- [ ] Phase 2: Parsing logic
- [ ] Phase 3: Processing/transformation
- [ ] Phase 4: Output generation
- [ ] Phase 5: Error handling
- [ ] Phase 6: Testing

## Dependencies
- openpyxl
- [others]

## Status
In Development
```

---

### Step 5: Build the Script

**Goal**: Write the code using reference patterns

**File Naming Convention**:
```
[descriptive_name]_[MMDD].py

Examples:
- xml_to_excel_1118.py
- tmx_converter_1118.py
- korean_validator_1118.py
```

**Script Structure** (always include this):

```python
"""
Script Name: [name].py
Created: 2025-11-[DD]
Purpose: [One sentence description]
Input: [Format and structure]
Output: [Format and structure]
Reference: [Reference script from RessourcesForCodingTheProject]

Usage:
    python [script_name].py

    1. Run the script
    2. Select input file using file picker
    3. Process and generate output
    4. Output saved in same directory

Dependencies:
    pip install openpyxl pandas
    [other dependencies]

Author: [Your name or "Generated with Claude Code"]
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import openpyxl
# [other imports based on reference script]

def main():
    """Main execution function"""

    # File picker setup
    root = tk.Tk()
    root.withdraw()

    # Get input file
    input_file = filedialog.askopenfilename(
        title="Select input file",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    if not input_file:
        print("No file selected. Exiting.")
        return

    print(f"Processing: {input_file}")

    # Process
    try:
        result = process_file(input_file)
        output_file = generate_output_path(input_file)
        save_output(result, output_file)
        print(f"✓ Done! Output saved to: {output_file}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def process_file(input_file):
    """Process the input file"""
    # Your processing logic here
    pass

def save_output(data, output_file):
    """Save the output file"""
    # Your save logic here
    pass

def generate_output_path(input_file):
    """Generate output file path"""
    input_path = Path(input_file)
    return input_path.parent / f"{input_path.stem}_output{input_path.suffix}"

if __name__ == "__main__":
    main()
```

**Best Practices**:
- ✅ Keep it standalone (single .py file)
- ✅ Use file picker (Tkinter) for user-friendliness
- ✅ Include error handling with try/except
- ✅ Print progress messages
- ✅ Save output with clear naming
- ✅ Add comments for complex logic
- ❌ Don't over-engineer - keep it simple
- ❌ Don't add unnecessary dependencies

---

### Step 6: Test the Script

**Goal**: Verify it works with real data

**Testing Process**:
1. **Use test data**: Check `/RessourcesForCodingTheProject/datausedfortesting/`
2. **Run the script**: `python script_name.py`
3. **Verify output**:
   - Does it match expected format?
   - Are transformations correct?
   - Does it handle edge cases?
4. **Test error cases**:
   - Empty files
   - Missing columns/elements
   - Invalid formats

**Common Test Cases**:
- [ ] Valid input file → Correct output
- [ ] Empty input file → Clear error message
- [ ] Missing required data → Helpful error
- [ ] Large file → Performance check
- [ ] Special characters → Proper handling

---

### Step 7: Deliver & Document

**Goal**: Hand off working script with documentation

**Delivery Checklist**:
- [ ] Script is in `NewScripts/ScriptName/` folder
- [ ] ROADMAP.md is complete
- [ ] Script has proper header documentation
- [ ] Script has been tested successfully
- [ ] Dependencies are documented
- [ ] Usage instructions are clear

**Tell the User**:
```
✓ Script complete: NewScripts/ScriptName/script_name_1118.py

How to use:
1. Navigate to NewScripts/ScriptName/
2. Run: python script_name_1118.py
3. Select your input file
4. Output will be saved in same directory as input

Dependencies:
pip install openpyxl pandas

Tested with: [describe test case]
```

---

## 📁 Folder Organization

**Structure**:
```
NewScripts/
├── README.md                          # Overview and reference guide
├── WORKFLOW.md                        # This file - step-by-step workflow
│
├── WordCountMaster/                   # Example: Script folder
│   ├── ROADMAP.md                    # Development roadmap
│   ├── wordcount_diff_master.py      # Main script
│   └── wordcount_history.json        # Auto-generated data
│
├── ScriptName2/                       # Your next script
│   ├── ROADMAP.md                    # Development roadmap
│   └── script_name2_1118.py          # Main script
│
├── 2025-11/                          # Monthly scripts (optional)
│   └── [quick one-off scripts]
│
└── archive/                           # Deprecated scripts
    └── [old versions]
```

**Naming Rules**:
- **Folder name**: Descriptive, PascalCase (e.g., `XmlToExcel`, `KoreanValidator`)
- **Script file**: lowercase_with_underscores_MMDD.py
- **ROADMAP**: Always `ROADMAP.md`

---

## 🎯 Quality Checklist

Before considering a script "done", verify:

### Functionality
- [ ] Solves the requested problem completely
- [ ] Handles expected input formats
- [ ] Produces correct output format
- [ ] Works with test data

### Code Quality
- [ ] Has proper header documentation
- [ ] Includes error handling
- [ ] Follows reference script patterns
- [ ] Uses appropriate libraries
- [ ] Has clear function names
- [ ] Includes helpful comments

### User Experience
- [ ] File picker GUI (not hardcoded paths)
- [ ] Clear progress messages
- [ ] Helpful error messages
- [ ] Output file naming makes sense
- [ ] Instructions are clear

### Documentation
- [ ] ROADMAP.md exists and is complete
- [ ] Script header has all required info
- [ ] Dependencies are listed
- [ ] Usage instructions are clear

---

## 🚀 Speed Tips

**How to Build Scripts Fast (15-30 minutes)**:

1. **Don't reinvent the wheel** - Always use reference scripts
2. **Copy patterns liberally** - That's what they're for
3. **Start simple** - Get basic I/O working first
4. **Test early, test often** - Don't wait until the end
5. **Use familiar libraries** - openpyxl, xml.etree, pandas
6. **Keep it standalone** - No complex dependency chains
7. **Document as you go** - Write header comment first

**Time Budget**:
- Understand request: 2-3 minutes
- Find reference: 2-3 minutes
- Read reference: 5 minutes
- Plan (ROADMAP): 3 minutes
- Build script: 10-15 minutes
- Test: 5 minutes
- Document & deliver: 2 minutes

**Total: 15-30 minutes per script**

---

## 🔗 Related Resources

### Reference Scripts
- **Location**: `/RessourcesForCodingTheProject/`
  - `MAIN PYTHON SCRIPTS/` (9 major tools)
  - `SECONDARY PYTHON SCRIPTS/` (74 utilities)

### Test Data
- **Location**: `/RessourcesForCodingTheProject/datausedfortesting/`
- Use this for testing your scripts

### Main Project
- **LocaNext Platform**: Successful scripts may become LocaNext apps
- See: `docs/ADD_NEW_APP_GUIDE.md` for migration guide

---

## 📝 Example Workflow (Real Case)

**Request**: "I need to convert XML game translations to Excel with Korean and English columns"

**Step 1 - Understand**:
- Input: XML files with `<Korean>` and `<English>` tags
- Output: Excel with 2 columns: Korean | English
- No GUI needed, just file picker

**Step 2 - Find Reference**:
- Found: `translatexmlstable2.py` (has XML parsing)
- Found: `xlscompare5.py` (has Excel writing)

**Step 3 - Read Patterns**:
- XML: Uses `xml.etree.ElementTree`
- Excel: Uses `openpyxl`
- File picker: Uses `tkinter.filedialog`

**Step 4 - Plan**:
- Create: `NewScripts/XmlToExcel/`
- Create: `ROADMAP.md` with 6-phase plan
- Script name: `xml_to_excel_1118.py`

**Step 5 - Build**:
- Copied XML parsing pattern from reference
- Copied Excel writing pattern from reference
- Added file picker
- Added error handling

**Step 6 - Test**:
- Used sample XML from `datausedfortesting/`
- Verified Excel output has correct columns
- Tested empty file → good error message

**Step 7 - Deliver**:
```
✓ Script complete: NewScripts/XmlToExcel/xml_to_excel_1118.py

Usage: python xml_to_excel_1118.py
Dependencies: openpyxl
Status: Tested and working
```

**Time taken**: 23 minutes ✓

---

## 🤝 Working with Claude

When requesting a new script from Claude:

**Good Request**:
```
I need a script that converts XML translation files to Excel.
The XML has <Korean> and <English> tags inside <Text> elements.
I want an Excel with two columns: Korean | English.
Check translatexmlstable2.py for the XML pattern.
```

**Claude will**:
1. Create the folder structure
2. Write ROADMAP.md
3. Build the script using reference patterns
4. Test with sample data
5. Deliver with documentation

**You should**:
1. Provide sample input if possible
2. Point to relevant reference scripts
3. Test the delivered script
4. Provide feedback if adjustments needed

---

**Last Updated**: 2025-11-18
**Version**: 1.0

---

*Follow this workflow for consistent, fast, high-quality script development!*
