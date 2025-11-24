# GlossarySniffer Roadmap

**Created**: 2025-11-24
**Status**: In Development
**Reference Script**: QuickSearch0818.py (Aho-Corasick glossary extraction)

---

## 🎯 Purpose

**GlossarySniffer** extracts glossary terms from XML files and searches for them in Excel text lines, outputting which glossary terms appear in each line.

### Use Case
- Analyze translation lines to identify glossary terms automatically
- Build glossary from XML `StrOrigin` attributes with smart filtering
- Fast multi-pattern matching using Aho-Corasick algorithm
- Output Excel with original lines + glossary terms found

---

## 📋 Input/Output

### Input 1: XML Glossary Source
**Format**: XML file with `StrOrigin` (Korean) and `Str` (English) attributes
```xml
<Texts>
  <Text>
    <LocStr StrOrigin="클리프" Str="Kliff"/>
    <LocStr StrOrigin="칼파데" Str="Calphade"/>
    <LocStr StrOrigin="엘레노어 공작" Str="Duke Elenor"/>
    <LocStr StrOrigin="고고구구 땅" Str="Lands of Gogogugu"/>
  </Text>
</Texts>
```

### Input 2: Lines to Analyze
**Format**: Excel file (`.xlsx`) with Korean lines to check
```
| Line (Korean)                                |
|----------------------------------------------|
| 클리프가 칼파데에 가서 친구들과 이야기했다        |
| 나는 엘레노어 공작이고, 고고구구 땅을 다스린다   |
```

### Output: Analysis Result
**Format**: Excel file with original lines + glossary terms found + mapped translations
```
| Original Line (Korean)                                     | Glossary Terms Found (StrOrigin=Korean) | Mapped Translations (Str=English) |
|------------------------------------------------------------|----------------------------------------|-----------------------------------|
| 클리프가 칼파데에 가서 친구들과 이야기했다                      | 클리프, 칼파데                          | Kliff, Calphade                   |
| 나는 엘레노어 공작이고, 고고구구 땅을 다스린다                 | 엘레노어 공작, 고고구구 땅                | Duke Elenor, Lands of Gogogugu    |
```

**NEW ENHANCEMENT (2025-11-24)**:
- **Column 3 added**: Maps each StrOrigin match to its corresponding Str value from XML
- **Example**: If "클리프" (Korean) is found, show both "클리프" (StrOrigin) and "Kliff" (Str=English)
- **Use case**: See Korean glossary term AND its English translation side-by-side
- **Direction**: Korean (StrOrigin) → English (Str)

---

## 🔧 Glossary Building Logic - HARDCODED RULES

### ⚙️ All Rules Hardcoded (No User Input Needed!)

**Based on QuickSearch0818.py glossary_filter() lines 2113-2149**

### 5 HARDCODED FILTERING RULES:

**Rule 1: Length Threshold**
```python
DEFAULT_LENGTH_THRESHOLD = 15  # Korean names/terms are usually short
```
- ✅ KEEP: Terms < 15 characters
- ❌ SKIP: Anything >= 15 characters (too long, likely a phrase/sentence)

**Rule 2: Minimum Occurrence**
```python
MIN_OCCURRENCE = 2  # Must appear at least 2 times
```
- ✅ KEEP: Terms that appear 2+ times in XML
- ❌ SKIP: One-off terms (likely typos or descriptions, not real glossary)

**Rule 3: No Punctuation Endings**
```python
FILTER_SENTENCES = True
Pattern: r'[.?!]\s*$'  # Ends with .?!
```
- ✅ KEEP: "Kliff", "Duke Elenor"
- ❌ SKIP: "Welcome.", "How are you?", "Hello!"

**Rule 4: No Punctuation Inside**
```python
FILTER_PUNCTUATION = True
Checks: string.punctuation (except spaces/hyphens) + special ellipsis …
```
- ✅ KEEP: "Duke Elenor" (space ok), "Black-Desert" (hyphen ok)
- ❌ SKIP: "Hello, world", "Wait—what", "Well..."

**Rule 5: Non-Empty Only**
- ✅ KEEP: Any non-empty string
- ❌ SKIP: Empty strings, None values

### Two-Pass Filtering (Like QuickSearch0818)
```python
# Pass 1: Basic filtering + count occurrences
for term in all_terms:
    if passes_basic_filters(term):
        count_map[term] += 1

# Pass 2: Apply min_occurrence filter
glossary = [term for term, count in count_map.items() if count >= MIN_OCCURRENCE]

# Sort by frequency (most common first)
glossary.sort(key=count, reverse=True)
```

### Example Filtering
```
INPUT: 1000 StrOrigin entries from XML

✅ KEEP (111 terms after filtering):
- "클리프" (4 chars, appears 5 times)
- "칼파데" (4 chars, appears 3 times)
- "엘레노어 공작" (8 chars, appears 2 times)
- "고고구구 땅" (7 chars, appears 2 times)
- "검은사막" (4 chars, appears 10 times)

❌ SKIP:
- "클리프가 도시에 갔다." (ends with ., sentence)
- "안녕하세요, 여행자님!" (contains comma and !, punctuation)
- "이것은 매우 긴 설명입니다" (16 chars, too long)
- "임시항목" (1 occurrence only, not recurring glossary)
- "..." (only punctuation)
```

### Word Boundary Matching
```python
WORD_BOUNDARIES = True  # Only match complete words
```
- ✅ MATCH: "Duke" in "The Duke arrived"
- ❌ SKIP: "Duke" inside "Archduke" (not at word boundary)

---

## ⚡ Search Algorithm: Aho-Corasick + Word Boundaries

### Why Aho-Corasick?
- **Fast multi-pattern matching**: Search for ALL glossary terms in single pass
- **Efficient**: O(n + m + z) where n=text length, m=total pattern length, z=matches
- **Perfect for glossary**: Can find overlapping patterns
- **Proven in QuickSearch0818**: Already successfully used in production

### Implementation Steps (Enhanced)
1. **Build Automaton**: Add all glossary terms to Aho-Corasick automaton
2. **Make Automaton**: Finalize state machine for fast searching
3. **Scan Each Line**: Use automaton to find all glossary term candidates
4. **Word Boundary Check**: Validate each match is at word boundaries (not inside other words)
5. **Aggregate Results**: Collect all valid unique terms found per line

### Word Boundary Logic (NEW!)
```python
# For each Aho-Corasick match, check:
start_pos = match_end - len(term) + 1

# Character before match (if exists)
if start_pos > 0:
    char_before = line[start_pos - 1]
    if char_before.isalnum():
        skip  # Inside a word!

# Character after match (if exists)
if match_end + 1 < len(line):
    char_after = line[match_end + 1]
    if char_after.isalnum():
        skip  # Inside a word!
```

### Example Search with Word Boundaries
```python
# Glossary terms: ["클리프", "공작", "엘레노어 공작"]
# Line: "클리프가 엘레노어 공작을 만났다"

# Aho-Corasick finds: ["클리프", "공작", "엘레노어 공작"]
# Word boundary check:
#   - "클리프" ✅ (가 is not alnum in this context)
#   - "공작" inside "엘레노어 공작" ❌ (prefer longest)
#   - "엘레노어 공작" ✅ (을 is not alnum)

# Final output: "클리프, 엘레노어 공작"
```

### Korean Language Considerations
- Korean doesn't have case sensitivity (no uppercase/lowercase)
- Word boundaries work with particles (가, 을, 는, etc.)
- Multi-word Korean terms work fine ("엘레노어 공작")

---

## 🔄 Development Plan

### Phase 1: XML Glossary Extraction ✅ (Target: Complete)
- [ ] Parse XML files using `lxml` or `xml.etree.ElementTree`
- [ ] Extract all `StrOrigin` attributes
- [ ] Apply length threshold filter (default: 30 chars)
- [ ] Remove entries with punctuation
- [ ] Remove full sentences
- [ ] Deduplicate terms
- [ ] Save glossary to internal list

**Reference**: QuickSearch0818.py lines 2113-2149 (glossary_filter function)

### Phase 2: Excel Input Handling ✅ (Target: Complete)
- [ ] Read Excel file with `openpyxl`
- [ ] Extract lines from first column (or user-specified column)
- [ ] Store lines in list for processing

**Reference**: Standard openpyxl patterns from XLSTransfer, QuickSearch

### Phase 3: Aho-Corasick Search Implementation ✅ (Target: Complete)
- [ ] Import `ahocorasick` library
- [ ] Build automaton with all glossary terms
- [ ] For each Excel line:
  - [ ] Run Aho-Corasick search
  - [ ] Collect all matched glossary terms
  - [ ] Handle overlapping matches (e.g., "Duke" vs "Duke Elenor")
- [ ] Prefer longest matches for overlapping terms

**Reference**: QuickSearch0818.py lines 2211-2259 (Aho-Corasick implementation)

### Phase 4: Excel Output Generation ✅ (Target: Complete)
- [ ] Create new Excel workbook
- [ ] Column 1: Original lines
- [ ] Column 2: Glossary terms found (comma-separated)
- [ ] Format: Clean, readable
- [ ] Save to output file

**Reference**: openpyxl workbook creation patterns

### Phase 5: GUI & File Pickers ✅ (Target: Complete)
- [ ] Tkinter file picker for XML glossary source
- [ ] Tkinter file picker for Excel input lines
- [ ] Tkinter save dialog for Excel output
- [ ] Progress messages
- [ ] Error handling

**Reference**: Standard Tkinter patterns from all NewScripts

### Phase 6: Advanced Features (Optional)
- [ ] Configurable length threshold (GUI input)
- [ ] Option to include/exclude punctuation
- [ ] Case-sensitive vs case-insensitive matching
- [ ] Multiple XML source files
- [ ] Column selection for Excel input
- [ ] Statistics (total lines, terms found, coverage %)

---

## 📦 Dependencies

```bash
pip install openpyxl lxml pyahocorasick
```

### Libraries Used
- **openpyxl**: Excel file handling (read/write .xlsx)
- **lxml**: Fast XML parsing (preferred) or xml.etree.ElementTree (fallback)
- **pyahocorasick**: Aho-Corasick algorithm for fast multi-pattern matching
- **tkinter**: GUI file pickers (built-in Python)
- **re**: Regular expressions for text cleaning/filtering
- **string**: Punctuation detection for filtering

### Why These Libraries?
- **Aho-Corasick**: 10-100x faster than regex for multi-pattern matching
- **lxml**: Faster than ElementTree for large XML files
- **openpyxl**: Standard Excel library, reliable for .xlsx
- All proven in QuickSearch0818 production use

---

## 🎨 Script Structure

### File Name
`glossary_sniffer_1124.py`

### Main Functions
```python
def extract_glossary_from_xml(xml_path, length_threshold=30):
    """
    Extract glossary terms from XML StrOrigin attributes
    Returns: list of glossary terms
    """

def filter_glossary_terms(terms, length_threshold):
    """
    Filter out non-glossary entries (punctuation, long phrases, etc.)
    Returns: filtered list of terms
    """

def build_ahocorasick_automaton(glossary_terms):
    """
    Build Aho-Corasick automaton from glossary terms
    Returns: automaton object
    """

def search_line_for_glossary(line, automaton):
    """
    Search a single line for glossary terms using Aho-Corasick
    Returns: list of matched terms
    """

def process_excel_lines(excel_path, automaton):
    """
    Read Excel, search each line, return results
    Returns: list of (original_line, glossary_terms_found) tuples
    """

def write_results_to_excel(results, output_path):
    """
    Write results to Excel with 2 columns:
    - Column 1: Original Line
    - Column 2: Glossary Terms Found (comma-separated)
    """

def main():
    """
    Main execution:
    1. Pick XML glossary source
    2. Build glossary
    3. Pick Excel input file
    4. Search for glossary terms
    5. Save results to Excel
    """
```

---

## ✅ Testing Plan

### Test Case 1: Basic Glossary Extraction
**Input XML**:
```xml
<LocStr StrOrigin="Kliff" Str="Kliff"/>
<LocStr StrOrigin="Calphade" Str="Calphade"/>
<LocStr StrOrigin="This is a long sentence that should be filtered." Str="..."/>
<LocStr StrOrigin="Hello, world!" Str="..."/>
```

**Expected Glossary**: `["Kliff", "Calphade"]`

### Test Case 2: Multi-Word Terms
**Input XML**:
```xml
<LocStr StrOrigin="Duke Elenor" Str="Duke Elenor"/>
<LocStr StrOrigin="Lands of Gogogugu" Str="Lands of Gogogugu"/>
```

**Expected Glossary**: `["Duke Elenor", "Lands of Gogogugu"]`

### Test Case 3: Line Search
**Glossary**: `["Kliff", "Calphade", "Duke Elenor"]`
**Excel Line**: `"Kliff went to Calphade to meet Duke Elenor"`
**Expected Match**: `"Kliff, Calphade, Duke Elenor"`

### Test Case 4: Overlapping Terms
**Glossary**: `["Duke", "Duke Elenor"]`
**Excel Line**: `"I am Duke Elenor"`
**Expected Match**: `"Duke Elenor"` (prefer longest match)

### Test Case 5: No Matches
**Glossary**: `["Kliff", "Calphade"]`
**Excel Line**: `"Hello world"`
**Expected Match**: `""` (empty)

---

## 🚀 Performance Goals

- **Glossary Building**: <5 seconds for 10,000 XML entries
- **Aho-Corasick Automaton**: <1 second for 5,000 terms
- **Line Searching**: <10 seconds for 10,000 lines with 5,000-term glossary
- **Excel Output**: <5 seconds for 10,000 rows

**Total**: <30 seconds for typical use case

---

## 📊 Success Criteria

✅ **Functional**:
- Correctly extracts glossary from XML StrOrigin
- **5 HARDCODED RULES** applied automatically (no user config needed):
  1. Length < 15 chars ✅
  2. Min 2 occurrences ✅
  3. No punctuation endings ✅
  4. No punctuation inside (except space/hyphen) ✅
  5. Non-empty only ✅
- **Word boundaries** enforced (no matching inside other words) ✅
- Finds single-word Korean terms ("클리프") ✅
- Finds multi-word Korean expressions ("엘레노어 공작") ✅
- Handles overlapping matches correctly (prefers longest) ✅
- Outputs clean Excel results ✅

✅ **Performance**:
- Fast enough for 10,000+ lines
- Uses Aho-Corasick for O(n+m+z) efficiency
- Two-pass filtering (like QuickSearch0818)

✅ **User Experience**:
- Simple file picker GUI (no configuration needed!)
- Clear progress messages
- Helpful error messages
- Clean Excel output format
- Shows sample glossary terms after extraction

✅ **Code Quality**:
- Clean, commented code
- Hardcoded rules well-documented
- Error handling
- Follows NewScripts patterns
- Based on proven QuickSearch0818 logic (lines 2113-2259)

---

## 🔗 References

### Pattern Source
**QuickSearch0818.py** (`RessourcesForCodingTheProject/SECONDARY PYTHON SCRIPTS/`)
- Lines 2113-2149: `glossary_filter()` function (filtering logic)
- Lines 2211-2259: Aho-Corasick automaton building and searching
- Line 24: `import ahocorasick`
- Line 890, 1775, 1803, 1879: `StrOrigin` extraction patterns

### Key Patterns Reused
1. **XML Parsing**: `tree.xpath('//LocStr')` with `locstr.get('StrOrigin', '')`
2. **Glossary Filtering**: Length threshold, punctuation removal, sentence detection
3. **Aho-Corasick**: Build automaton → make_automaton() → scan text for matches
4. **Excel I/O**: openpyxl patterns from multiple scripts

---

## 🔄 ENHANCEMENT: Add Translation Mapping (Column 3)

**Status**: 📋 PLANNED (2025-11-24)
**Complexity**: LOW (straightforward mapping)
**Estimated Time**: 30-45 minutes

### What Changes

**Current Output** (2 columns):
```
| Original Line | Glossary Terms Found |
```

**New Output** (3 columns):
```
| Original Line | Glossary Terms Found (StrOrigin) | Mapped Translations (Str) |
```

### Implementation Plan

#### Step 1: Update Glossary Extraction (extract_glossary_from_xml)
**Current**: Returns `list` of StrOrigin values only
```python
glossary = ['클리프', '칼파데', '엘레노어 공작']  # Korean only
```

**New**: Return BOTH list (for Aho-Corasick) AND mapping dict
```python
glossary_terms = ['클리프', '칼파데', '엘레노어 공작']  # Korean (for Aho-Corasick)
glossary_map = {
    '클리프': 'Kliff',              # Korean → English
    '칼파데': 'Calphade',           # Korean → English
    '엘레노어 공작': 'Duke Elenor'   # Korean → English
}
```

**Code changes**:
```python
def extract_glossary_from_xml(xml_path, length_threshold, min_occurrence):
    """
    Returns:
        tuple: (glossary_terms: list, glossary_map: dict)
        - glossary_terms: List of StrOrigin values for Aho-Corasick
        - glossary_map: Dict mapping StrOrigin → Str values
    """
    # Extract BOTH StrOrigin and Str
    all_terms = []
    term_to_str_map = {}  # NEW: Store mapping

    for locstr in tree.xpath('//LocStr'):
        str_origin = locstr.get('StrOrigin', '').strip()
        str_value = locstr.get('Str', '').strip()

        if str_origin:
            all_terms.append(str_origin)
            term_to_str_map[str_origin] = str_value  # NEW: Map StrOrigin → Str

    # Filter glossary (same as before)
    glossary_terms = filter_glossary_terms(all_terms, length_threshold, min_occurrence)

    # Build final mapping (only for terms that passed filtering)
    glossary_map = {term: term_to_str_map[term] for term in glossary_terms}

    return glossary_terms, glossary_map  # NEW: Return both
```

#### Step 2: Update Main Function
**Pass glossary_map through the pipeline**:
```python
def main():
    # Step 1: Extract glossary + mapping
    glossary_terms, glossary_map = extract_glossary_from_xml(xml_path)  # NEW: unpack tuple

    # Step 2: Build Aho-Corasick (uses glossary_terms only)
    automaton = build_ahocorasick_automaton(glossary_terms)

    # Step 3: Process Excel (pass glossary_map)
    results = process_excel_lines(excel_path, automaton, glossary_map)  # NEW: pass map

    # Step 4: Write results (now includes translations)
    write_results_to_excel(results, output_path)
```

#### Step 3: Update Excel Processing (process_excel_lines)
**Add glossary_map parameter**:
```python
def process_excel_lines(excel_path, automaton, glossary_map):  # NEW: glossary_map param
    """
    Returns:
        list: Tuples of (original_line, glossary_terms_found, mapped_translations)
    """
    for row in ws.iter_rows(...):
        line = str(row[0])
        matches = search_line_for_glossary(line, automaton)
        matches = resolve_overlapping_matches(matches, line)

        # NEW: Map each match to its Str value
        mapped_translations = [glossary_map.get(term, '') for term in matches]

        results.append((line, matches, mapped_translations))  # NEW: 3-tuple

    return results
```

#### Step 4: Update Excel Output (write_results_to_excel)
**Add third column**:
```python
def write_results_to_excel(results, output_path):
    # Header row (3 columns now)
    ws.append(["Original Line", "Glossary Terms Found (StrOrigin)", "Mapped Translations (Str)"])

    # Data rows
    for line, matches, translations in results:  # NEW: unpack 3-tuple
        glossary_str = ", ".join(matches) if matches else ""
        translation_str = ", ".join(translations) if translations else ""  # NEW

        ws.append([line, glossary_str, translation_str])  # NEW: 3 columns

    # Auto-size columns
    ws.column_dimensions['A'].width = 80
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 50  # NEW
```

### Testing Plan

**Test Case 1**: Basic mapping (Korean → English)
- Input XML: `<LocStr StrOrigin="클리프" Str="Kliff"/>`
- Input line: "클리프가 도시에 갔다" (Korean)
- Expected output:
  - Column 2: "클리프"
  - Column 3: "Kliff"

**Test Case 2**: Multi-word expressions (Korean → English)
- Input XML: `<LocStr StrOrigin="엘레노어 공작" Str="Duke Elenor"/>`
- Input line: "나는 엘레노어 공작이다" (Korean)
- Expected output:
  - Column 2: "엘레노어 공작"
  - Column 3: "Duke Elenor"

**Test Case 3**: Multiple matches (Korean → English)
- Input line: "클리프가 칼파데에 갔다" (Korean)
- Expected output:
  - Column 2: "클리프, 칼파데"
  - Column 3: "Kliff, Calphade"

**Test Case 4**: No matches
- Input line: "안녕하세요 세계" (Korean, no glossary terms)
- Expected output:
  - Column 2: ""
  - Column 3: ""

### Files to Modify

✅ **glossary_sniffer_1124.py** (4 functions):
1. `extract_glossary_from_xml()` - Return tuple (list, dict)
2. `process_excel_lines()` - Add glossary_map param, return 3-tuple
3. `write_results_to_excel()` - Add 3rd column
4. `main()` - Update to pass glossary_map

✅ **ROADMAP.md** (this file) - Document enhancement

✅ **README.md** - Update example output (3 columns)

✅ **SUMMARY.md** - Update example output (3 columns)

### Summary

**Changes**: Minimal, straightforward mapping
**Complexity**: LOW (just passing data through)
**Backward compatibility**: Output format changes (2 cols → 3 cols)
**Testing**: 4 test cases to validate mapping
**Status**: ✅ COMPLETE (2025-11-24)

---

## 🌍 ENHANCEMENT: Multi-Language Support (13 Languages)

**Status**: 📋 PLANNED (2025-11-24)
**Complexity**: MEDIUM (folder walking, multiple file parsing)
**Estimated Time**: 2-3 hours
**Reference**: wordcount1.py (lines 43-47, 134-148)

### Current Limitation

**Current**: Single XML file → Single language mapping (Korean → English)
```
Input: One XML file with StrOrigin + Str
Output: 3 columns (Original Line | Korean | English)
```

**Problem**: Need to check translations across **13 languages**, not just one!

### New Approach: Language Data Folder

**Input**: LANGUAGE DATA FOLDER containing multiple XML files
```
languagedata_folder/
├── languagedata_KOR.xml  ← StrOrigin (Korean source)
├── languagedata_ENG.xml  ← English translation
├── languagedata_FRA.xml  ← French translation
├── languagedata_GER.xml  ← German translation
├── languagedata_SPA.xml  ← Spanish translation
├── languagedata_ITA.xml  ← Italian translation
├── languagedata_POR.xml  ← Portuguese translation
├── languagedata_RUS.xml  ← Russian translation
├── languagedata_POL.xml  ← Polish translation
├── languagedata_TUR.xml  ← Turkish translation
├── languagedata_THA.xml  ← Thai translation
├── languagedata_JPN.xml  ← Japanese translation
├── languagedata_CHS.xml  ← Chinese Simplified translation
└── languagedata_CHT.xml  ← Chinese Traditional translation
```

**Key Insight from wordcount1.py**:
- All language files have the **SAME StrOrigin** values
- Each file has **different Str translations**
- Extract StrOrigin from KOR file (reference)
- Map to all 13 language translations

### New Output Format

**Output**: Excel with **15 columns** (Original Line + StrOrigin + 13 languages)

```
| Original Line (Korean) | Glossary (StrOrigin=KOR) | ENG | FRA | GER | SPA | ITA | POR | RUS | POL | TUR | THA | JPN | CHS | CHT |
|------------------------|--------------------------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| 클리프가 칼파데에 갔다   | 클리프, 칼파데            | Kliff, Calphade | Kliff, Calphade | Kliff, Calphade | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

### Implementation Plan

#### Step 1: Update XML Selection (UI)
**Change**: Select FOLDER instead of single XML file
```python
def main():
    # BEFORE: Select single XML file
    xml_path = filedialog.askopenfilename(title="Select XML Glossary Source", ...)

    # AFTER: Select LANGUAGE DATA FOLDER
    folder_path = filedialog.askdirectory(title="Select Language Data Folder")
```

#### Step 2: Folder Walking (from wordcount1.py pattern)
**New function**: Walk folder and find all `languagedata_*.xml` files
```python
def iter_language_files(folder: Path):
    """
    Walk folder and yield all languagedata_*.xml files.
    Pattern from wordcount1.py lines 43-47.
    """
    for dirpath, _, filenames in os.walk(folder):
        for fn in filenames:
            if fn.lower().startswith("languagedata_") and fn.lower().endswith(".xml"):
                yield Path(dirpath) / fn

def extract_language_code(xml_path: Path) -> str:
    """
    Extract language code from filename.
    Example: "languagedata_ENG.xml" → "ENG"
    Pattern from wordcount1.py lines 135-139.
    """
    stem = xml_path.stem
    parts = stem.split("_", 1)
    if len(parts) == 2:
        return parts[1].upper()
    return "UNKNOWN"
```

#### Step 3: Multi-Language Glossary Extraction
**New function**: Extract StrOrigin + all language translations
```python
def extract_multilanguage_glossary(folder_path, length_threshold, min_occurrence):
    """
    Extract glossary from LANGUAGE DATA FOLDER.

    Returns:
        tuple: (glossary_terms: list, multi_lang_map: dict)
        - glossary_terms: List of StrOrigin values (from KOR)
        - multi_lang_map: Dict mapping StrOrigin → {lang_code: translation}

    Example multi_lang_map:
    {
        '클리프': {
            'ENG': 'Kliff',
            'FRA': 'Kliff',
            'GER': 'Kliff',
            'SPA': 'Kliff',
            ...
        },
        '칼파데': {
            'ENG': 'Calphade',
            'FRA': 'Calphade',
            ...
        }
    }
    """
    # 1. Find all languagedata_*.xml files
    xml_files = list(iter_language_files(Path(folder_path)))
    print(f"   Found {len(xml_files)} language files")

    # 2. Group by language code
    files_by_lang = {}
    for xml_path in xml_files:
        lang_code = extract_language_code(xml_path)
        files_by_lang[lang_code] = xml_path

    # 3. Extract StrOrigin from KOR file (reference)
    if 'KOR' not in files_by_lang:
        raise ValueError("No Korean (KOR) language file found!")

    kor_path = files_by_lang['KOR']
    tree = etree.parse(kor_path)

    # Build StrOrigin list (for filtering)
    all_terms = []
    for locstr in tree.xpath('//LocStr'):
        str_origin = locstr.get('StrOrigin', '').strip()
        if str_origin:
            all_terms.append(str_origin)

    # Filter glossary (same rules as before)
    glossary_terms = filter_glossary_terms(all_terms, length_threshold, min_occurrence)

    # 4. Build multi-language mapping
    multi_lang_map = {term: {} for term in glossary_terms}

    for lang_code, xml_path in files_by_lang.items():
        print(f"   Processing {lang_code}...")
        tree = etree.parse(xml_path)

        for locstr in tree.xpath('//LocStr'):
            str_origin = locstr.get('StrOrigin', '').strip()
            str_value = locstr.get('Str', '').strip()

            # Only include terms that passed filtering
            if str_origin in multi_lang_map:
                multi_lang_map[str_origin][lang_code] = str_value

    return glossary_terms, multi_lang_map
```

#### Step 4: Update Excel Processing
**Modify**: Store translations for all languages
```python
def process_excel_lines(excel_path, automaton, multi_lang_map, language_codes):
    """
    Returns:
        list: Tuples of (original_line, glossary_terms_found, translations_by_lang)
        - translations_by_lang: Dict mapping lang_code → comma-separated translations
    """
    results = []

    for row in ws.iter_rows(...):
        line = str(row[0])
        matches = search_line_for_glossary(line, automaton)
        matches = resolve_overlapping_matches(matches, line)

        # NEW: Build translations for ALL languages
        translations_by_lang = {}
        for lang_code in language_codes:
            lang_translations = [
                multi_lang_map.get(term, {}).get(lang_code, '')
                for term in matches
            ]
            translations_by_lang[lang_code] = lang_translations

        results.append((line, matches, translations_by_lang))

    return results
```

#### Step 5: Update Excel Output (15 Columns)
**New**: Write 15 columns instead of 3
```python
def write_results_to_excel(results, output_path, language_codes):
    """
    Write results with 15 columns:
    - Column 1: Original Line
    - Column 2: Glossary Terms Found (StrOrigin)
    - Columns 3-15: Translations for each language
    """
    # Header row
    headers = ["Original Line", "Glossary Terms (StrOrigin)"] + language_codes
    ws.append(headers)

    # Data rows
    for line, matches, translations_by_lang in results:
        glossary_str = ", ".join(matches) if matches else ""

        row_data = [line, glossary_str]

        # Add translation columns for each language
        for lang_code in language_codes:
            lang_translations = translations_by_lang.get(lang_code, [])
            translation_str = ", ".join(lang_translations) if lang_translations else ""
            row_data.append(translation_str)

        ws.append(row_data)

    # Auto-size columns
    ws.column_dimensions['A'].width = 80  # Original Line
    ws.column_dimensions['B'].width = 50  # Glossary Terms
    for i, lang_code in enumerate(language_codes, start=3):
        col_letter = chr(64 + i)  # C, D, E, F, ...
        ws.column_dimensions[col_letter].width = 40
```

### Testing Plan

**Test Case 1**: Folder with 13 language files
- Input: Folder with languagedata_KOR.xml, languagedata_ENG.xml, etc.
- Expected: Extracts glossary from KOR, maps to all 13 languages

**Test Case 2**: Multi-language mapping
- Input line: "클리프가 칼파데에 갔다"
- Expected output: 15 columns with translations in all languages

**Test Case 3**: Missing language file
- Input: Folder missing one language (e.g., no FRA file)
- Expected: Empty column for missing language, others work fine

**Test Case 4**: Same StrOrigin across files
- Verify: All language files have the same StrOrigin values
- Verify: Only Str values differ per language

### Files to Modify

✅ **glossary_sniffer_1124.py** (major refactor):
1. Add `iter_language_files()` - Folder walking
2. Add `extract_language_code()` - Extract lang code from filename
3. Modify `extract_glossary_from_xml()` → `extract_multilanguage_glossary()` - Multi-file parsing
4. Modify `process_excel_lines()` - Handle multi-language translations
5. Modify `write_results_to_excel()` - Write 15 columns

✅ **ROADMAP.md** (this file) - Document enhancement

✅ **README.md** - Update examples (15 columns)

✅ **SUMMARY.md** - Update examples (15 columns)

### Summary

**Changes**: SIGNIFICANT refactor for multi-language support
**Complexity**: MEDIUM (folder walking, multiple file parsing, 15-column output)
**Backward compatibility**: BREAKS (output format changes 3 cols → 15 cols)
**Testing**: 4 test cases + validation with real language data
**Benefits**:
- Check ALL 13 language translations at once ✅
- Single run covers entire translation coverage ✅
- No need to run 13 times for each language ✅

---

## 📝 Notes

- **Keep it standalone**: Single .py file, minimal dependencies
- **Speed matters**: Use Aho-Corasick for fast searching (proven in QuickSearch0818)
- **Smart filtering**: Don't include everything as glossary - filter intelligently
- **Multi-word support**: Must handle "Duke Elenor", "Lands of Gogogugu", etc.
- **User-friendly**: File pickers, progress messages, clear output

---

**Next Step**: Begin Phase 1 (XML Glossary Extraction) 🚀

---

*Last Updated: 2025-11-24*
*Status: Ready to build!*
