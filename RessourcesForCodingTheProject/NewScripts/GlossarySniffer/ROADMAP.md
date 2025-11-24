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
**Format**: XML file with `StrOrigin` attributes
```xml
<Texts>
  <Text>
    <LocStr StrOrigin="Kliff" Str="Kliff"/>
    <LocStr StrOrigin="Calphade" Str="Calphade"/>
    <LocStr StrOrigin="Duke Elenor" Str="Duke Elenor"/>
    <LocStr StrOrigin="Lands of Gogogugu" Str="Lands of Gogogugu"/>
  </Text>
</Texts>
```

### Input 2: Lines to Analyze
**Format**: Excel file (`.xlsx`) with lines to check
```
| Line                                              |
|---------------------------------------------------|
| Kliff went to Calphade to talk to his friends    |
| I am Duke Elenor, and I rule over the Lands of Gogogugu |
```

### Output: Analysis Result
**Format**: Excel file with original lines + glossary terms found
```
| Original Line                                              | Glossary Terms Found      |
|------------------------------------------------------------|---------------------------|
| Kliff went to Calphade to talk to his friends             | Kliff, Calphade           |
| I am Duke Elenor, and I rule over the Lands of Gogogugu   | Duke Elenor, Lands of Gogogugu |
```

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
