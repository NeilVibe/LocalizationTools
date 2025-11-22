# Claude Instructions: NewScripts Framework

**CRITICAL REFERENCE FOR HANDLING NEWSCRIPTS REQUESTS**

---

## 🎯 Purpose

This document provides **systematic instructions** for Claude Code when the user requests a new localization script within the NewScripts framework.

---

## 🚨 When to Use This Framework

**Activate NewScripts workflow when user says**:
- "I need a script that..."
- "Can you build a tool to..."
- "Create a Python script for..."
- "I need to convert [format A] to [format B]"
- "Build me a quick script for..."
- Any request for standalone Python scripts for localization tasks

**Context clues**:
- User mentions XML, Excel, TMX, translation, localization
- User requests file format conversion
- User needs data processing/validation
- User wants a quick automation tool

---

## 📋 Systematic Workflow (ALWAYS Follow)

### Phase 1: Requirement Gathering (MANDATORY)

**DO THIS FIRST - Never skip!**

Ask clarifying questions:
```
I'll help you build that script! First, let me clarify a few things:

1. Input format: [What format? XML/Excel/TXT/TMX?]
2. Output format: [What should the output look like?]
3. Languages: [Which languages are involved?]
4. Sample data: [Do you have a sample file I can look at?]
5. Special requirements: [GUI needed? Batch processing? Validation?]
```

**Wait for user response before proceeding.**

---

### Phase 2: Reference Script Identification (MANDATORY)

**DO THIS SECOND - Critical for pattern reuse!**

#### Step 2a: Search for Reference Scripts

**Search locations**:
1. `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/` (9 major scripts)
2. `RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/` (74 utility scripts)

**Search strategies**:
```bash
# Search by file type
grep -l "xml" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py
grep -l "openpyxl" RessourcesForCodingTheProject/MAIN\ PYTHON\ SCRIPTS/*.py
grep -l "tmx" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py

# Or use Glob/Grep tools
Glob: "RessourcesForCodingTheProject/**/*.py"
Grep: pattern="openpyxl|xml.etree|pandas"
```

#### Step 2b: Ask User for Reference Guidance

**Always ask**:
```
I found several scripts that might have relevant patterns:
- [script1.py] - [relevant feature]
- [script2.py] - [relevant feature]

Which one should I use as the main reference? Or would you like me to check a different script?
```

**Common references by task type**:
| Task Type | Recommended Reference |
|-----------|----------------------|
| XML parsing | `translatexmlstable2.py`, `xmlatt13.py` |
| Excel processing | `XLSTransfer0225.py`, `xlscompare5.py` |
| TMX handling | `tmxconvert33.py` |
| Text processing | `extractchinese.py`, `quickregex3.py` |
| Korean text | `KRSIMILAR0124.py`, `stackKR.py` |
| GUI (Tkinter) | `QS0305.py`, `TFMLITE0307.py` |

---

### Phase 3: Read Reference Script (MANDATORY)

**DO THIS THIRD - Absorb patterns!**

```python
# Read the reference script
Read("RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/[reference_script].py")
```

**Extract these patterns**:
- [ ] Import statements
- [ ] File I/O approach (file picker, paths)
- [ ] XML/Excel/text parsing method
- [ ] Data structures used
- [ ] Error handling pattern
- [ ] Output file generation
- [ ] GUI patterns (if applicable)

**Inform user**:
```
I've reviewed [reference_script.py]. I'll use these patterns:
- [Pattern 1: e.g., XML parsing with ElementTree]
- [Pattern 2: e.g., Excel writing with openpyxl]
- [Pattern 3: e.g., File picker with tkinter]

Ready to proceed?
```

---

### Phase 4: Plan & Create Structure (MANDATORY)

**DO THIS FOURTH - Create folder and roadmap!**

#### Step 4a: Create Folder Structure

```python
# Determine script name (PascalCase for folder)
folder_name = "ScriptName"  # e.g., XmlToExcel, KoreanValidator

# Create folder
Bash: mkdir -p RessourcesForCodingTheProject/NewScripts/{folder_name}
```

#### Step 4b: Create ROADMAP.md

**Always create ROADMAP.md first!**

```python
Write("RessourcesForCodingTheProject/NewScripts/{folder_name}/ROADMAP.md")
```

**ROADMAP.md template**:
```markdown
# [ScriptName] Roadmap

## Purpose
[One sentence: What does this script do?]

## Input Format
[Describe input structure with example]

## Output Format
[Describe output structure with example]

## Reference Script
[Which script from RessourcesForCodingTheProject was used?]

## Development Phases

### Phase 1: File I/O Setup
- [ ] Implement file picker (tkinter)
- [ ] Set up input file reading
- [ ] Set up output file writing

### Phase 2: Parsing Logic
- [ ] Parse input format (XML/Excel/TXT)
- [ ] Extract required data
- [ ] Handle edge cases

### Phase 3: Processing/Transformation
- [ ] Implement core logic
- [ ] Data transformation
- [ ] Validation

### Phase 4: Output Generation
- [ ] Format output data
- [ ] Write to output file
- [ ] Proper file naming

### Phase 5: Error Handling
- [ ] Add try/except blocks
- [ ] Helpful error messages
- [ ] Edge case handling

### Phase 6: Testing
- [ ] Test with sample data
- [ ] Test edge cases
- [ ] Verify output correctness

## Dependencies
```
pip install openpyxl
[other dependencies]
```

## Status
- **Created**: 2025-11-[DD]
- **Status**: In Development
- **Last Updated**: 2025-11-[DD]

## Testing Notes
[Document test cases and results]

## Known Issues
[Any limitations or edge cases]
```

---

### Phase 5: Build the Script (MANDATORY)

**DO THIS FIFTH - Write the actual code!**

#### File naming convention:
```
[descriptive_name]_[MMDD].py

Examples:
- xml_to_excel_1118.py
- korean_validator_1118.py
- tmx_converter_1118.py
```

#### Script structure (ALWAYS use this template):

```python
"""
Script Name: [name].py
Created: 2025-11-[DD]
Purpose: [One sentence description]
Input: [Format and structure description]
Output: [Format and structure description]
Reference: [Reference script path]

Usage:
    python [script_name].py

    1. Run the script
    2. Select input file using file picker
    3. Process and generate output
    4. Output saved in same directory as input

Dependencies:
    pip install openpyxl pandas
    [List all required packages]

Author: Generated with Claude Code
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# [Add other imports based on reference script]
# Common: openpyxl, xml.etree.ElementTree, pandas, re

def main():
    """Main execution function"""

    print("="*60)
    print("[SCRIPT NAME]")
    print("="*60)

    # File picker setup
    root = tk.Tk()
    root.withdraw()

    # Get input file
    input_file = filedialog.askopenfilename(
        title="Select input file",
        filetypes=[
            ("Excel files", "*.xlsx"),
            ("XML files", "*.xml"),
            ("All files", "*.*")
        ]
    )

    if not input_file:
        print("❌ No file selected. Exiting.")
        return

    print(f"📁 Input file: {input_file}")

    # Process
    try:
        print("\n🔄 Processing...")
        result = process_file(input_file)

        print("💾 Saving output...")
        output_file = generate_output_path(input_file)
        save_output(result, output_file)

        print(f"\n✅ Done! Output saved to:")
        print(f"   {output_file}")
        print("\n" + "="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)

def process_file(input_file):
    """
    Process the input file

    Args:
        input_file: Path to input file

    Returns:
        Processed data structure
    """
    # TODO: Implement based on reference script pattern
    pass

def save_output(data, output_file):
    """
    Save the output file

    Args:
        data: Processed data
        output_file: Path to output file
    """
    # TODO: Implement based on reference script pattern
    pass

def generate_output_path(input_file):
    """
    Generate output file path

    Args:
        input_file: Path to input file

    Returns:
        Path to output file
    """
    input_path = Path(input_file)
    output_name = f"{input_path.stem}_output{input_path.suffix}"
    return input_path.parent / output_name

if __name__ == "__main__":
    main()
```

#### Best practices (ALWAYS follow):
- ✅ Standalone single .py file
- ✅ File picker GUI (tkinter)
- ✅ Try/except error handling
- ✅ Progress messages with emojis (✓, ✗, 🔄, 📁, 💾)
- ✅ Clear output file naming
- ✅ Proper header documentation
- ✅ Helpful comments for complex logic
- ❌ NO hardcoded paths
- ❌ NO over-engineering
- ❌ NO unnecessary dependencies

---

### Phase 6: Test the Script (MANDATORY)

**DO THIS SIXTH - Verify it works!**

#### Testing process:

1. **Prepare test data**:
```bash
# Check for test data
ls RessourcesForCodingTheProject/datausedfortesting/
```

2. **Run the script**:
```bash
python RessourcesForCodingTheProject/NewScripts/ScriptName/script_name_1118.py
```

3. **Verify output**:
- [ ] Output file created successfully
- [ ] Output format matches requirements
- [ ] Data transformation is correct
- [ ] Edge cases handled properly

4. **Test error cases**:
- [ ] Empty input file
- [ ] Missing required data
- [ ] Invalid format
- [ ] Large files

5. **Document test results**:
Update ROADMAP.md with test results:
```markdown
## Testing Notes
- ✅ Tested with sample_file.xlsx - Success
- ✅ Tested empty file - Proper error message
- ✅ Tested 1000-row file - Completed in 2.3s
- ⚠️  Special characters in Korean text handled correctly
```

---

### Phase 7: Deliver & Document (MANDATORY)

**DO THIS SEVENTH - Hand off to user!**

#### Delivery message template:

```
✅ Script complete!

**Location**:
RessourcesForCodingTheProject/NewScripts/ScriptName/script_name_1118.py

**How to use**:
1. Navigate to the folder
2. Run: `python script_name_1118.py`
3. Select your input file using the file picker
4. Output will be saved in the same directory as your input file

**Dependencies**:
```bash
pip install openpyxl pandas
```

**Tested with**:
- Sample XML file with 500 entries ✓
- Edge case: empty file ✓
- Edge case: missing language columns ✓

**Documentation**:
- ROADMAP.md: Complete development plan
- Script header: Full usage instructions

Let me know if you need any adjustments!
```

---

## 🔍 Pattern Reference Guide

### Common Patterns to Copy from Reference Scripts

#### 1. File Picker Pattern
```python
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()

input_file = filedialog.askopenfilename(
    title="Select input file",
    filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
)
```

#### 2. XML Parsing Pattern
```python
import xml.etree.ElementTree as ET

tree = ET.parse(input_file)
root = tree.getroot()

for text_elem in root.findall('.//Text'):
    korean = text_elem.find('Korean').text
    english = text_elem.find('English').text
```

#### 3. Excel Reading Pattern (openpyxl)
```python
import openpyxl

wb = openpyxl.load_workbook(input_file)
ws = wb.active

for row in ws.iter_rows(min_row=2, values_only=True):
    col1, col2 = row[0], row[1]
```

#### 4. Excel Writing Pattern (openpyxl)
```python
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Output"

# Headers
ws.append(["Korean", "English"])

# Data
for item in data:
    ws.append([item['korean'], item['english']])

wb.save(output_file)
```

#### 5. Error Handling Pattern
```python
try:
    result = risky_operation()
except FileNotFoundError:
    print(f"❌ Error: File not found")
    return
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
```

---

## 📊 Quick Reference: Reference Scripts by Task

### XML Processing
**Use**: `translatexmlstable2.py`, `xmlatt13.py`, `XMLCHECKER1.py`
**For**: XML parsing, attribute handling, validation

### Excel Processing
**Use**: `XLSTransfer0225.py`, `xlscompare5.py`, `xlsconcat.py`
**For**: Excel reading/writing, comparison, concatenation

### TMX Processing
**Use**: `tmxconvert33.py`
**For**: TMX format handling

### Korean Text
**Use**: `KRSIMILAR0124.py`, `stackKR.py`, `KRtermcheck.py`
**For**: Korean language processing, similarity checking

### Text Processing
**Use**: `extractchinese.py`, `quickregex3.py`, `wordparser0424.py`
**For**: Text extraction, regex operations, parsing

### GUI (Tkinter)
**Use**: `QS0305.py`, `TFMLITE0307.py`
**For**: Complex GUI patterns, user interaction

---

## ⚠️ Common Mistakes to AVOID

### ❌ DON'T:
1. **Skip reference script reading** - Always read reference first!
2. **Hardcode file paths** - Always use file picker
3. **Over-engineer** - Keep it simple and standalone
4. **Forget error handling** - Always include try/except
5. **Skip testing** - Always test before delivering
6. **Omit documentation** - Always include header comment and ROADMAP
7. **Use unfamiliar libraries** - Stick to reference patterns
8. **Create without folder** - Always use folder structure

### ✅ DO:
1. **Follow the 7-phase workflow** - Every single time
2. **Use reference script patterns** - Copy liberally
3. **Ask clarifying questions** - Understand before building
4. **Create ROADMAP.md first** - Plan before coding
5. **Test thoroughly** - Multiple test cases
6. **Document clearly** - Header + ROADMAP
7. **Keep it standalone** - Single .py file with minimal deps
8. **Use file picker** - User-friendly input selection

---

## 🎯 Success Criteria Checklist

Before marking a script as "complete", verify ALL of these:

### Functionality
- [ ] Solves the requested problem completely
- [ ] Handles expected input formats correctly
- [ ] Produces correct output format
- [ ] Works with test data successfully

### Code Quality
- [ ] Has proper header documentation (all fields filled)
- [ ] Includes comprehensive error handling
- [ ] Follows reference script patterns exactly
- [ ] Uses appropriate libraries from reference
- [ ] Has clear, descriptive function names
- [ ] Includes helpful comments for complex logic
- [ ] Code is clean and readable

### User Experience
- [ ] File picker GUI (not hardcoded paths)
- [ ] Clear progress messages with emojis
- [ ] Helpful error messages (not just stack traces)
- [ ] Output file naming makes sense
- [ ] Instructions are crystal clear

### Documentation
- [ ] ROADMAP.md exists and is complete
- [ ] Script header has all required information
- [ ] Dependencies are clearly listed
- [ ] Usage instructions are step-by-step
- [ ] Test results are documented

### Testing
- [ ] Tested with valid sample data
- [ ] Tested with edge cases (empty, missing data, etc.)
- [ ] Tested with large files (performance)
- [ ] All tests documented in ROADMAP.md

### Organization
- [ ] Script is in proper folder: `NewScripts/ScriptName/`
- [ ] File naming follows convention: `name_MMDD.py`
- [ ] ROADMAP.md is in same folder
- [ ] No unnecessary files in folder

---

## 🚀 Speed Optimization

**Target: 15-30 minutes per script**

**Time allocation**:
- Phase 1 (Requirements): 2-3 min
- Phase 2 (Reference): 2-3 min
- Phase 3 (Read): 5 min
- Phase 4 (Plan/ROADMAP): 3 min
- Phase 5 (Build): 10-15 min
- Phase 6 (Test): 5 min
- Phase 7 (Document): 2 min

**Speed tips**:
1. Use reference scripts - don't reinvent
2. Copy patterns exactly - modify minimally
3. Start with template - fill in the blanks
4. Test as you build - don't wait until end
5. Keep it simple - no fancy features

---

## 📝 Example Conversation Flow

**User**: "I need a script to convert XML translations to Excel"

**Claude**:
```
I'll help you build that script! First, let me clarify:

1. What's the XML structure? (Sample would help)
2. Which languages should be in the Excel? (e.g., Korean + English)
3. Should it be all languages or specific ones?
4. Any specific Excel format requirements?
```

**User**: "XML has <Korean> and <English> tags. Just those two in the Excel."

**Claude**:
```
Got it! Let me search for reference scripts with XML and Excel patterns...

[Searches reference scripts]

I found these relevant scripts:
- translatexmlstable2.py (XML parsing)
- xlscompare5.py (Excel writing)

I'll use translatexmlstable2.py as the main reference. Let me read it...

[Reads reference]

Perfect! I'll use these patterns:
- XML parsing with ElementTree
- Excel writing with openpyxl
- File picker with tkinter

Creating folder structure and ROADMAP...

[Creates folder and ROADMAP]

Now building the script...

[Builds script]

Testing with sample data...

[Tests]

✅ Done! Script ready at:
NewScripts/XmlToExcel/xml_to_excel_1118.py

[Provides usage instructions]
```

---

## 🔄 Iteration & Feedback

**If user requests changes**:

1. **Understand the change**:
   - "What specifically needs to be different?"

2. **Locate the change**:
   - Read the existing script
   - Identify affected function

3. **Make the change**:
   - Edit the script
   - Update ROADMAP if needed

4. **Test the change**:
   - Verify it works
   - Check no regressions

5. **Deliver updated version**:
   - Explain what changed
   - Provide new instructions if needed

---

## 🎓 Learning & Improvement

**After each script**:
- Note any new patterns discovered
- Update reference script knowledge
- Consider: Could this be a LocaNext app?

**Pattern library**:
- Keep mental note of successful patterns
- Reuse across multiple scripts
- Build expertise over time

---

**Last Updated**: 2025-11-18
**Version**: 1.0

---

**REMEMBER**: This is a SYSTEMATIC workflow. Follow ALL phases EVERY time. No shortcuts!
