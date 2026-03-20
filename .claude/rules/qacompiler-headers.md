---
paths:
  - "RessourcesForCodingTheProject/NewScripts/QACompilerNEW/**"
---

# QACompiler Header Sync Rule

If you change a translation column header in ANY generator, you MUST update detection in matching.py.

Detection uses pattern matching (prefix, exact), NOT imports from generators. A mismatch means `find_translation_col_in_headers()` returns `None` and masterfile compilation silently produces empty output. No error logged.

When changing headers, update ALL 4:
1. `core/matching.py` → `find_translation_col_in_headers()`
2. `core/matching.py` → `find_translation_col_in_ws()`
3. `generators/wordcount_report.py` → `_find_translation_col()`
4. `docs/MASTERFILE_COMPILATION_GUIDE.md`
