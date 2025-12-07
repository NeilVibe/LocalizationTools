# Test Files Manifest

**Location:** `D:\TestFilesForLocaNext\`

This document lists all test files required for autonomous testing of LocaNext.

---

## Required Test Files

### XLSTransfer

| File | Purpose | Structure | Size |
|------|---------|-----------|------|
| `GlossaryUploadTestFile.xlsx` | Create Dictionary (fast) | Col A: Korean, Col B: Translation | ~100 rows |
| `translationTEST.xlsx` | Translate Excel | Col A: Korean text | ~150 rows |
| `closetotest.txt` | Transfer to Close | Plain text, Korean lines | Small |
| `TESTSMALL.xlsx` | Large dictionary test (optional) | Col A: Korean, Col B: Translation | ~22,917 rows |

### QuickSearch

QuickSearch uses **backend dictionaries** (BDO_EN, etc.) stored in `server/data/dictionaries/`.
No external test files needed - it loads from the database.

### KR Similar

KR Similar uses **backend embeddings** stored in `server/data/embeddings/`.
No external test files needed - it loads from the database.

---

## File Specifications

### GlossaryUploadTestFile.xlsx

**Purpose:** Fast dictionary creation test (~20 seconds)

**Structure:**
```
| A (Korean)      | B (Translation) |
|-----------------|-----------------|
| 안녕하세요       | Hello           |
| 감사합니다       | Thank you       |
| 전투            | Combat          |
| 아이템          | Item            |
| ... (100 rows)  | ...             |
```

**Requirements:**
- Sheet name: `Sheet1`
- No empty rows in data range
- UTF-8 encoding

### translationTEST.xlsx

**Purpose:** Test translation with loaded dictionary

**Structure:**
```
| A (Korean to translate) | B (Will be filled) |
|-------------------------|-------------------|
| 전투 시작               |                   |
| 아이템 획득             |                   |
| ... (150 rows)          |                   |
```

### closetotest.txt

**Purpose:** Test Transfer to Close feature

**Structure:**
```
Korean text line 1
Korean text line 2
...
```

Plain text file with Korean text, one entry per line.

---

## Creating Test Files

If you need to recreate the test environment:

### Option 1: From existing BDO data

```python
# Extract sample from existing dictionaries
import pandas as pd

# Read large dictionary
df = pd.read_excel('path/to/BDO_full.xlsx')

# Take first 100 rows
sample = df.head(100)
sample.to_excel('GlossaryUploadTestFile.xlsx', index=False)
```

### Option 2: Manual creation

Create Excel files with the structure above. Ensure:
- Column A contains Korean text
- Column B contains translations
- No empty cells in the data range

---

## Verification

Run the prerequisites check to verify test files:

```bash
cd testing_toolkit/setup
bash check_prerequisites.sh
```

Expected output:
```
[CHECK] Test files (D:\TestFilesForLocaNext\): OK (4 files)
Test Files:
  [CHECK] GlossaryUploadTestFile.xlsx: OK (15KB)
  [CHECK] translationTEST.xlsx: OK (8KB)
```

---

## Backup Location

Test files should be backed up to:
- `testing_toolkit/test_files/samples/` (committed to repo)
- Or cloud storage for larger files

---

*Last updated: 2025-12-07*
