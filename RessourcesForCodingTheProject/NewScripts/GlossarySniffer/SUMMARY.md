# GlossarySniffer - Quick Summary

**Created**: 2025-11-24
**Status**: ✅ COMPLETE & READY TO USE

---

## 🎯 What It Does

Extracts Korean glossary terms from **LANGUAGE DATA FOLDER** (13 languages) and finds them in Excel lines using **Aho-Corasick** + **5 hardcoded filtering rules**. Maps to **ALL 13 language translations** at once.

---

## ⚡ ZERO CONFIGURATION NEEDED!

**All rules are hardcoded** (based on QuickSearch0818):

### 5 Hardcoded Rules:
1. **Length < 15 chars** (Korean names/terms are short)
2. **Min 2 occurrences** (real glossary, not typos)
3. **No punctuation endings** (.?!)
4. **No punctuation inside** (except space/hyphen)
5. **Word boundaries** (won't match inside other words)

---

## 🚀 Usage

```bash
# Install
pip install openpyxl lxml pyahocorasick

# Run
python glossary_sniffer_1124.py

# 1. Select LANGUAGE DATA FOLDER (with languagedata_*.xml files)
# 2. Select Excel (lines to analyze)
# 3. Save results
# Done! (Output has 2 + N language columns)
```

---

## 📊 Example

**Input XML**: 1000 StrOrigin entries (Korean → English mapping)
**After filtering**: 111 glossary terms (passed all 5 rules)

**Keep**:
- "클리프" → "Kliff" (4 chars, 5 occurrences) ✅
- "엘레노어 공작" → "Duke Elenor" (8 chars, 2 occurrences) ✅
- "검은사막" → "Shadow Realm" (4 chars, 10 occurrences) ✅

**Remove**:
- "클리프가 도시에 갔다." (ends with period) ❌
- "안녕하세요, 여행자님!" (punctuation) ❌
- "매우 긴 설명입니다" (16 chars) ❌
- "임시항목" (1 occurrence only) ❌

**Output** (3 columns):
| Original Line (Korean) | Glossary Found (Korean) | Translation (English) |
|------------------------|-------------------------|-----------------------|
| 클리프가 검은사막에 갔다 | 클리프, 검은사막 | Kliff, Shadow Realm |

---

## ✨ Features

✅ Aho-Corasick multi-pattern matching (FAST!)  
✅ Word boundary validation (no false positives)  
✅ Korean language optimized  
✅ Multi-word expressions supported  
✅ Sorted by frequency (most common first)  
✅ Clean Excel output  

---

## 📁 Files

- `glossary_sniffer_1124.py` - Main script (450 lines)
- `ROADMAP.md` - Detailed development plan
- `README.md` - Full guide
- `SUMMARY.md` - This file (quick reference)
- `sample_glossary.xml` - Test data
- `sample_input_lines.xlsx` - Test data

---

**Just run it! No configuration needed.** 🚀
