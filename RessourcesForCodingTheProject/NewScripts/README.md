# NewScripts - Rapid Localization Script Development

**Purpose**: Quick standalone Python scripts for ad-hoc localization tasks requested by coworkers

**Created**: 2025-11-13
**Status**: Active Development

---

## 📖 Documentation

**New to NewScripts? Start here:**

1. **[WORKFLOW.md](WORKFLOW.md)** ⭐ **START HERE**
   - Step-by-step guide for creating new scripts
   - Systematic 7-phase workflow
   - Quality checklists and speed tips
   - **Use this when building scripts!**

2. **README.md** (this file)
   - Reference script catalog
   - Common patterns and templates
   - Libraries and conventions
   - **Use this for reference and context**

3. **`.claude/newscript_instructions.md`** (for Claude Code)
   - Systematic instructions for AI assistance
   - Mandatory workflow for Claude
   - Pattern reference guide

**Quick Start**: Read [WORKFLOW.md](WORKFLOW.md) for the complete process!

---

## 🎯 Purpose & Workflow

### The Mission
Build standalone Python scripts quickly to solve various localization tasks that coworkers request. These scripts:
1. Solve immediate business needs
2. May evolve into LocaNext platform apps later
3. Build a library of reusable patterns and solutions

### Why This Exists
- **Immediate Value**: Coworkers need quick automated solutions for Excel/XML/text processing
- **Knowledge Base**: All existing scripts contain the company's data structures and patterns
- **Future Apps**: Successful scripts become candidates for LocaNext platform
- **Context for Claude**: Having reference scripts helps Claude understand the company's environment

### Typical Requests
- XML ↔ Excel conversions
- TMX ↔ XML conversions
- Text file processing and transformations
- Translation data extraction/injection
- Language data validation
- File format conversions
- Batch processing tasks
- Data cleaning and normalization

---

## 📚 Reference Script Library

All existing scripts are in `/RessourcesForCodingTheProject/`

### Main Scripts (High-value tools)
Located in: `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/`

| Script | Purpose | Key Patterns |
|--------|---------|-------------|
| `XLSTransfer0225.py` | AI-powered Excel translation transfer | Excel handling, embeddings, similarity matching |
| `QS0305.py` | QuickSearch dictionary tool | XML parsing, text normalization, dictionary structures |
| `KRSIMILAR0124.py` | Korean similarity checker | Korean text processing, similarity algorithms |
| `TFMFULL0116.py` | TFM Full (Translation File Manager) | Complex XML/TMX handling, translation workflows |
| `TFMLITE0307.py` | TFM Lite (lightweight version) | Simplified translation management |
| `bdmglossary1224.py` | BDM glossary tool | Glossary management, term extraction |
| `stackKR.py` | Korean stacking tool | Korean language processing |
| `trianglelen.py` | Triangle length calculator | Text length calculations |
| `removeduplicate.py` | Duplicate remover | Deduplication logic |

### Secondary Scripts (Utility scripts - 74 total)
Located in: `RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/`

**Categories:**

**XML Processing:**
- `xmlatt13.py` - XML attribute handling
- `xmlscan.py` - XML scanning
- `XMLCHECKER1.py` - XML validation
- `translatexmlstable2.py` - XML translation tables
- `prettyprint.py` - XML pretty printing

**TMX Processing:**
- `tmxconvert33.py` - TMX conversion

**Excel Processing:**
- `xlsconcat.py` - Excel concatenation
- `xlsconcatmap.py` - Excel concat with mapping
- `xlscompare5.py` - Excel comparison
- `XLSTransfer0225.py` - Excel translation transfer

**Text Processing:**
- `extractchinese.py` - Chinese text extraction
- `extractfile.py` - File extraction
- `chineseinjection2.py` - Chinese text injection
- `KRtermcheck.py` - Korean term checking
- `quickregex3.py` - Quick regex operations
- `wordparser0424.py` - Word parsing

**File Operations:**
- `filesync19.py` - File synchronization
- `findseq3.py` - Sequence finding
- `checkifnotcontained.py` - Containment checking

**Quest/Mission Processing:**
- `fullquest2.py` - Full quest processing
- `missionkey2.py` - Mission key handling

**Data Validation:**
- `matchid2.py` - ID matching
- `transfercheck.py` - Transfer validation
- `langmissfix.py` - Missing language fixes

**Multi-function Tools:**
- `multifunction.py` - Multiple utilities
- `multifunction6.py` - Enhanced utilities

**PAAT Tools:**
- `paatreportclean.py` - PAAT report cleaning
- `cleanpaatgloss.py` - PAAT glossary cleaning

**Other:**
- `compilertest.py` - Compiler testing
- `QuickSearch0818.py` - QuickSearch (newer version)

---

## 🔧 Common Patterns & Structures

### XML Structure Patterns

**Game Localization XML (BDO, BDM, BDC, CD):**
```xml
<Texts>
  <Text>
    <Korean>한국어 텍스트</Korean>
    <English>English text</English>
    <French>Texte français</French>
    <StringID>123456</StringID>
  </Text>
</Texts>
```

**TMX Format:**
```xml
<tmx>
  <tu>
    <tuv xml:lang="ko">
      <seg>한국어</seg>
    </tuv>
    <tuv xml:lang="en">
      <seg>English</seg>
    </tuv>
  </tu>
</tmx>
```

### Excel Structure Patterns

**Translation Dictionary:**
| Korean | English | French | German | StringID |
|--------|---------|--------|--------|----------|
| 안녕 | Hello | Bonjour | Hallo | 12345 |

**Bilingual Translation:**
| Source (Korean) | Target (English) |
|-----------------|------------------|
| 안녕하세요 | Hello |

### Text File Patterns

**Tab-Delimited Translation:**
```
Korean\tEnglish\tStringID
안녕\tHello\t12345
```

**Language Codes Used:**
- DE (German), IT (Italian), PL (Polish)
- EN (English), ES (Spanish), SP (Spanish)
- FR (French), ID (Indonesian), JP (Japanese)
- PT (Portuguese), RU (Russian), TR (Turkish)
- TH (Thai), TW (Traditional Chinese), CH (Simplified Chinese)
- KR (Korean)

### Common Libraries Used
```python
import openpyxl  # Excel handling
import xml.etree.ElementTree as ET  # XML parsing
import re  # Regex operations
import pandas as pd  # Data manipulation
import tkinter  # GUI (Tkinter)
from pathlib import Path  # File paths
```

---

## 🤖 Instructions for Claude

### When User Requests a New Script

**Step 1: Understand the Task**
- What input format? (XML, Excel, TXT, TMX)
- What output format?
- What processing is needed?
- Which languages are involved?

**Step 2: Find Reference Scripts**
- Look in `RessourcesForCodingTheProject/MAIN PYTHON SCRIPTS/` first
- Check `RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/` for similar tasks
- User will often point you to specific reference scripts

**Step 3: Absorb Patterns**
From the reference script, extract:
- How they parse XML/Excel/text
- How they handle language data
- How they structure file I/O
- What libraries they use
- Error handling patterns
- UI patterns (if Tkinter GUI needed)

**Step 4: Build the New Script**
- Follow the reference script's style
- Use the same libraries and patterns
- Adapt to the new task requirements
- Keep it standalone (single .py file)
- Add clear comments
- Include error handling

**Step 5: Naming Convention**
```
[task_name][date].py
Examples:
- xmltoexcel1113.py
- tmxconverter1113.py
- textcleaner1113.py
```

**Step 6: Documentation**
At the top of each script, include:
```python
"""
Script Name: [name]
Created: [date]
Purpose: [brief description]
Input: [format]
Output: [format]
Reference: [which script was used as reference]

Usage:
    python script_name.py

Dependencies:
    - openpyxl
    - [other libraries]
"""
```

---

## 🎨 Script Template

### Basic Standalone Script Template
```python
"""
Script Name: example_script.py
Created: 2025-11-13
Purpose: [Description of what this script does]
Input: [Input file format and structure]
Output: [Output file format and structure]
Reference: [Reference script from RessourcesForCodingTheProject]

Usage:
    python example_script.py

    1. Run the script
    2. Select input file using file picker
    3. Process and generate output
    4. Output saved in same directory

Dependencies:
    pip install openpyxl pandas
"""

import os
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import openpyxl
# Add other imports as needed

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

    # Your processing logic here
    try:
        # Process the file
        result = process_file(input_file)

        # Save output
        output_file = Path(input_file).stem + "_output.xlsx"
        save_output(result, output_file)

        print(f"✓ Done! Output saved to: {output_file}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def process_file(input_file):
    """Process the input file"""
    # Your processing logic
    pass

def save_output(data, output_file):
    """Save the output file"""
    # Your save logic
    pass

if __name__ == "__main__":
    main()
```

### Tkinter GUI Template (if needed)
```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class ScriptGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Script Name")
        self.root.geometry("600x400")

        # Create UI elements
        self.create_widgets()

    def create_widgets(self):
        # File selection
        ttk.Button(self.root, text="Select File",
                  command=self.select_file).pack(pady=10)

        # Process button
        ttk.Button(self.root, text="Process",
                  command=self.process).pack(pady=10)

    def select_file(self):
        self.file_path = filedialog.askopenfilename()
        if self.file_path:
            messagebox.showinfo("File Selected", f"File: {self.file_path}")

    def process(self):
        # Your processing logic
        try:
            # Process here
            messagebox.showinfo("Success", "Processing complete!")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScriptGUI(root)
    root.mainloop()
```

---

## 📁 Organization

### Folder Structure
```
RessourcesForCodingTheProject/
├── MAIN PYTHON SCRIPTS/
├── SECONDARY PYTHON SCRIPTS/
│   └── tmxtransfer8.py
├── guides/                           # Guides for existing scripts
│   ├── tmxtransfer_guide_en.md
│   └── tmxtransfer_guide_kr.md
└── NewScripts/
    ├── README.md (this file)
    ├── WORKFLOW.md
    ├── guides/                       # General NewScripts guides (optional)
    ├── WordCountMaster/              # Example mini-project
    │   ├── ROADMAP.md
    │   ├── wordcount_diff_master.py
    │   ├── wordcount_history.json
    │   └── docs/                     # Project-specific guides
    │       ├── guide_en.md
    │       └── guide_kr.md
    ├── ScriptName2/
    │   ├── ROADMAP.md
    │   ├── script_name2.py
    │   └── docs/
    └── archive/
        └── [old or deprecated scripts]
```

**Organization Pattern:**

**For Existing Scripts (Type 1)**:
- Guides for scripts in MAIN/SECONDARY PYTHON SCRIPTS
- Go in: `/RessourcesForCodingTheProject/guides/`
- Naming: `[scriptname]_guide_[language].md`

**For New Mini-Projects (Type 2)**:
- Each new script gets its own folder in NewScripts
- Each folder contains:
  - `ROADMAP.md` - Development plan
  - Main script file(s)
  - Optional `docs/` subfolder for project-specific guides
  - Any auto-generated data files
- This keeps each script project self-contained and organized

---

## 🚀 Quick Start for New Script Request

### Example Workflow:

**User says:** "I need to convert XML translation files to Excel with Korean and English columns"

**Claude does:**

1. **Ask clarifying questions:**
   - What's the XML structure? (Ask for sample or reference script)
   - Which languages? (Korean + English confirmed)
   - Output Excel format? (2 columns: Korean | English)

2. **Find reference:**
   ```bash
   # Look for similar scripts
   grep -l "xml" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py
   grep -l "excel" RessourcesForCodingTheProject/SECONDARY\ PYTHON\ SCRIPTS/*.py
   ```

3. **User points to reference:**
   "Check `translatexmlstable2.py` for XML parsing pattern"

4. **Read reference script:**
   ```python
   # Read and understand the pattern
   Read(translatexmlstable2.py)
   ```

5. **Build new script:**
   - Use same XML parsing approach
   - Use same Excel writing approach
   - Adapt to specific requirements
   - Save as `NewScripts/2025-11/xmltoexcel1113.py`

6. **Test:**
   - Use test data from `/RessourcesForCodingTheProject/datausedfortesting/`
   - Verify output

7. **Deliver:**
   - Give user the script path
   - Explain how to run it
   - Document any dependencies

---

## 🎯 Success Criteria for New Scripts

✅ **Standalone** - Single .py file, no complex dependencies
✅ **User-friendly** - File picker GUI (Tkinter)
✅ **Error handling** - Clear error messages
✅ **Documented** - Header comment with usage
✅ **Tested** - Works with sample data
✅ **Fast** - Builds in 15-30 minutes using references

---

## 📊 Script Categories

Track scripts by category for easy reference:

### Conversion Scripts
- XML → Excel
- TMX → XML
- Excel → XML
- Text → Excel
- etc.

### Validation Scripts
- XML validation
- Translation completeness check
- Duplicate detection
- Language code validation

### Processing Scripts
- Text normalization
- Character replacement
- Data cleaning
- Batch processing

### Analysis Scripts
- Translation comparison
- Missing translation finder
- Statistics generation
- Quality checks

---

## 🔗 Related Projects

**Main Project**: LocaNext Platform (FastAPI + SvelteKit)
- Successful scripts here may become LocaNext apps
- Use BaseToolAPI pattern when migrating
- See: `docs/ADD_NEW_APP_GUIDE.md`

**Reference Library**: RessourcesForCodingTheProject/
- 9 main scripts (major tools)
- 74 secondary scripts (utilities)
- Test data available in `datausedfortesting/`

---

## 📝 Notes

- **Speed matters**: These are quick solutions, not production apps
- **Reference is key**: Always use existing scripts as templates
- **Keep it simple**: Standalone scripts, minimal dependencies
- **Document lightly**: Header comment is enough
- **Test quickly**: Use existing test data
- **Iterate fast**: Build, test, deliver, improve if needed

---

## 🤝 Collaboration Pattern

**User → Claude workflow:**

1. **User**: "I need a script that does X"
2. **Claude**: "Got it! Which reference script should I look at?"
3. **User**: "Check script Y, it has the pattern you need"
4. **Claude**: Reads script Y, understands pattern
5. **Claude**: Builds new script using that pattern
6. **User**: Tests it, provides feedback
7. **Claude**: Adjusts if needed
8. **Done**: Script delivered in NewScripts/

**Fast, efficient, pattern-based development!**

---

**Last Updated**: 2026-01-27
**Total Reference Scripts**: ~83 (9 main + 74 secondary)

---

## 🚀 CI/CD BUILD GUIDE (CRITICAL!)

### Build Map - Which CI For Which Project?

| Project | CI System | Trigger File (at ROOT) | Workflow File | Check Status |
|---------|-----------|------------------------|---------------|--------------|
| **LocaNext** (main app) | Gitea Actions | `GITEA_TRIGGER.txt` | `.gitea/workflows/build.yml` | `./scripts/gitea_control.sh status` |
| **QuickSearch** | GitHub Actions | `QUICKSEARCH_BUILD.txt` | `quicksearch-build.yml` | `gh run list --workflow=quicksearch-build.yml` |
| **QACompilerNEW** | GitHub Actions | `QACOMPILER_BUILD.txt` | `qacompiler-build.yml` | `gh run list --workflow=qacompiler-build.yml` |
| **LanguageDataExporter** | GitHub Actions | `LANGUAGEDATAEXPORTER_BUILD.txt` | `languagedataexporter-build.yml` | `gh run list --workflow=languagedataexporter-build.yml` |
| **DataListGenerator** | GitHub Actions | `DATALISTGENERATOR_BUILD.txt` | `datalistgenerator-build.yml` | `gh run list --workflow=datalistgenerator-build.yml` |
| **Other NewScripts** | None | N/A | N/A | No build needed |

**⚠️ ALL trigger files are at the REPO ROOT, not in project folders!**

### Quick Reference Commands

**QuickSearch:**
```bash
echo "Build NNN: <description>" >> QUICKSEARCH_BUILD.txt
git add -A && git commit -m "Build NNN: <description>" && git push origin main
gh run list --workflow=quicksearch-build.yml --limit 3
```

**QACompilerNEW:**
```bash
echo "Build NNN: <description>" >> QACOMPILER_BUILD.txt
git add -A && git commit -m "Build NNN: <description>" && git push origin main
gh run list --workflow=qacompiler-build.yml --limit 3
```

**LanguageDataExporter:**
```bash
echo "Build NNN: <description>" >> LANGUAGEDATAEXPORTER_BUILD.txt
git add -A && git commit -m "Build NNN: <description>" && git push origin main
gh run list --workflow=languagedataexporter-build.yml --limit 3
```

**DataListGenerator:**
```bash
echo "Build NNN: <description>" >> DATALISTGENERATOR_BUILD.txt
git add -A && git commit -m "Build NNN: <description>" && git push origin main
gh run list --workflow=datalistgenerator-build.yml --limit 3
```

**LocaNext (main app - NOT NewScripts!):**
```bash
echo "Build NNN: <description>" >> GITEA_TRIGGER.txt
git add -A && git commit -m "Build NNN: <description>" && git push origin main && git push gitea main
```

**Standalone scripts (no CI):**
```bash
git add -A && git commit -m "<description>" && git push origin main
# Done - no build required, just use directly with Python
```

### Decision Tree: Do I Need a Build?

```
What did I modify?
│
├─ locaNext/ or server/ (main app)
│  └─ YES → Use Gitea CI (GITEA_TRIGGER.txt + push to both remotes)
│
├─ NewScripts/QuickSearch/
│  └─ YES → Use GitHub Actions (QUICKSEARCH_BUILD.txt)
│
├─ NewScripts/QACompilerNEW/
│  └─ YES → Use GitHub Actions (QACOMPILER_BUILD.txt)
│
├─ NewScripts/LanguageDataExporter/
│  └─ YES → Use GitHub Actions (LANGUAGEDATAEXPORTER_BUILD.txt)
│
├─ NewScripts/DataListGenerator/
│  └─ YES → Use GitHub Actions (DATALISTGENERATOR_BUILD.txt)
│
├─ NewScripts/<anything else>/
│  └─ NO → Just push to GitHub, run directly with Python
│
└─ RessourcesForCodingTheProject/ (reference scripts)
   └─ NO → Just push to GitHub, these are reference only
```

### Common Mistakes to Avoid

| ❌ WRONG | ✅ CORRECT |
|----------|-----------|
| Trigger Gitea build for NewScripts | Use GitHub Actions for NewScripts projects |
| Push only to GitHub for LocaNext | Push to BOTH GitHub AND Gitea for LocaNext |
| Investigate Gitea failures for NewScripts | Gitea is only for LocaNext main app |
| Look for trigger files in project folders | ALL trigger files are at REPO ROOT |

---

*This is a living document. Update it as patterns emerge and the script library grows!*
