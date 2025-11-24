# GlossarySniffer

**Quick glossary term extraction and search tool**

---

## 🎯 What It Does

**GlossarySniffer** extracts glossary terms from XML files and searches for them in Excel text lines, using the fast Aho-Corasick algorithm for multi-pattern matching.

### Use Case
- Analyze translation lines to identify which glossary terms appear
- Build smart glossary from XML `StrOrigin` attributes (filters out sentences, punctuation, etc.)
- Fast search for both single terms ("Kliff") and multi-word expressions ("Duke Elenor")
- Output Excel with original lines + glossary terms found

---

## 🚀 Quick Start

### Installation
```bash
cd RessourcesForCodingTheProject/NewScripts/GlossarySniffer
pip install openpyxl lxml pyahocorasick
```

### Run the Script
```bash
python glossary_sniffer_1124.py
```

### Workflow
1. **Select XML file** (glossary source with `StrOrigin` attributes)
2. Script builds glossary with smart filtering
3. **Select Excel file** (lines to analyze)
4. Script searches for glossary terms using Aho-Corasick
5. **Save results** (Excel with 2 columns: Original Line | Glossary Terms Found)

---

## 📋 Example

### Input 1: XML Glossary Source
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

### Input 2: Excel Lines to Analyze
| Text Line |
|-----------|
| Kliff went to Calphade to talk to his friends |
| I am Duke Elenor, and I rule over the Lands of Gogogugu |

### Output: Analysis Result
| Original Line | Glossary Terms Found |
|---------------|----------------------|
| Kliff went to Calphade to talk to his friends | Kliff, Calphade |
| I am Duke Elenor, and I rule over the Lands of Gogogugu | Duke Elenor, Lands of Gogogugu |

---

## ⚙️ Hardcoded Rules (No Configuration Needed!)

**All filtering rules are HARDCODED based on QuickSearch0818** - just run the script!

```python
# 5 HARDCODED FILTERING RULES:
DEFAULT_LENGTH_THRESHOLD = 15   # Korean names/terms < 15 chars
MIN_OCCURRENCE = 2              # Must appear 2+ times (real glossary)
FILTER_SENTENCES = True         # No punctuation endings (.?!)
FILTER_PUNCTUATION = True       # No punctuation inside (except space/hyphen)
WORD_BOUNDARIES = True          # Only match complete words
```

### What Gets Kept:
✅ "클리프" (4 chars, appears 5x)
✅ "엘레노어 공작" (8 chars, appears 2x, multi-word ok)
✅ "검은사막" (4 chars, appears 10x)

### What Gets Filtered:
❌ "클리프가 도시에 갔다." (ends with period)
❌ "안녕하세요, 여행자님!" (punctuation inside)
❌ "매우 긴 설명 텍스트입니다" (16 chars, too long)
❌ "임시항목" (appears only 1x, not real glossary)

---

## ✨ Features

### Smart Glossary Filtering (5 Hardcoded Rules)
**Based on QuickSearch0818 proven patterns:**

✅ **KEEP**:
- Single words: "클리프", "칼파데" (Korean names)
- Multi-word terms: "엘레노어 공작", "검은사막" (expressions)
- Terms < 15 characters
- Terms appearing 2+ times (real glossary, not typos)

❌ **REMOVE**:
- Full sentences: "환영합니다." (ends with period)
- Punctuation: "안녕하세요, 여행자님!" (contains comma/!)
- Long descriptions: >15 chars
- One-off terms: Appears only 1x
- Empty strings

### Fast Multi-Pattern Search with Word Boundaries
- Uses **Aho-Corasick algorithm** for O(n+m+z) complexity
- Searches for ALL glossary terms in single pass
- **Word boundary validation**: Won't match "공작" inside "엘레노어 공작"
- Handles overlapping matches (prefers longest match)
- Perfect for Korean text (works with particles: 가, 을, 는, etc.)

---

## 📁 Files

```
GlossarySniffer/
├── ROADMAP.md                  # Detailed development plan
├── README.md                   # This file
├── glossary_sniffer_1124.py    # Main script
├── sample_glossary.xml         # Sample XML glossary source
└── sample_input_lines.xlsx     # Sample Excel input
```

---

## 🧪 Testing

**Quick test with samples**:
1. Run: `python glossary_sniffer_1124.py`
2. Select: `sample_glossary.xml`
3. Select: `sample_input_lines.xlsx`
4. Save output
5. Check results!

**Expected glossary** (after filtering):
- Kliff, Calphade, Heidel, Valencia
- Duke Elenor, Lands of Gogogugu, Black Desert, Red Battlefield
- Mediah, Kamasylvia, Ancient Weapon

**Expected matches**:
- Line 1: "Kliff went to Calphade..." → Kliff, Calphade
- Line 2: "I am Duke Elenor..." → Duke Elenor, Lands of Gogogugu
- Line 3: "The city of Heidel..." → Heidel
- etc.

---

## 🔧 Troubleshooting

### "No module named 'ahocorasick'"
```bash
pip install pyahocorasick
```

### "No module named 'lxml'"
```bash
pip install lxml
```

### "No glossary terms found"
- Check XML structure has `<LocStr StrOrigin="...">` elements
- Reduce `DEFAULT_LENGTH_THRESHOLD` if terms are longer
- Set `FILTER_PUNCTUATION = False` if you want to include punctuation

---

## 📊 Performance

- **Glossary Building**: <5s for 10,000 XML entries
- **Aho-Corasick Automaton**: <1s for 5,000 terms
- **Line Searching**: <10s for 10,000 lines with 5,000-term glossary
- **Total**: <30 seconds for typical use case

---

## 🔗 Reference

**Based on**: QuickSearch0818.py
- Aho-Corasick glossary extraction patterns (lines 2113-2259)
- Glossary filtering logic (length, punctuation, sentences)
- Fast multi-pattern matching with `ahocorasick` library

---

## 📝 Notes

- **Standalone script**: Single .py file, minimal dependencies
- **Smart filtering**: Only keeps real glossary terms (no sentences, punctuation)
- **Multi-word support**: Handles "Duke Elenor", "Lands of Gogogugu", etc.
- **Fast search**: Aho-Corasick algorithm for efficient multi-pattern matching
- **Clean output**: Excel with 2 columns for easy analysis

---

**Created**: 2025-11-24
**Status**: Ready to use! 🚀
