---
paths:
  - "RessourcesForCodingTheProject/NewScripts/**/*.py"
---

# StringID Columns = Text Format

StringID values are 19+ digit integers. Excel auto-converts them to scientific notation (1.23456E+19), destroying the data.

ALWAYS:
- Set `num_format: '@'` (text format) on StringID columns
- Write values as `str(stringid)`, never as int
- Pattern reference: QACompiler `submit_datasheet.py`

```python
# xlsxwriter
worksheet.write_string(row, col, str(stringid), text_format)

# openpyxl
cell.number_format = '@'
cell.value = str(stringid)
```
