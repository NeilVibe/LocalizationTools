---
paths:
  - "RessourcesForCodingTheProject/NewScripts/**/*.py"
---

# openpyxl read_only Mode: Never ws.cell()

NEVER use `ws.cell(row, col)` in openpyxl `read_only=True` mode. Use `iter_rows(values_only=True)` instead.

ws.cell() in read_only mode seeks through XML for each call. With max_row potentially 1,048,576, this causes a 10-minute freeze on a single sheet. iter_rows processes 10K rows in 439ms.

```python
# WRONG — freezes for 10 minutes
for row in range(1, ws.max_row + 1):
    val = ws.cell(row, col).value

# CORRECT — instant
for row in ws.iter_rows(values_only=True):
    val = row[col_idx]
```
