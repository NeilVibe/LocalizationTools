# Development Paradigms

> Battle-tested patterns and library choices. Follow these to avoid pain.

---

## Excel Libraries

### xlsxwriter > openpyxl (for writing)

**Always use xlsxwriter for generating Excel files:**

| | xlsxwriter | openpyxl |
|--|------------|----------|
| Writing | Excellent - just works | Buggy, unreliable |
| Install | `pip install` and done | Dependency issues |
| Sheet protection | Works perfectly | Hit or miss |
| Reading files | Cannot (write-only) | Can read |

**Decision tree:**
- Need to WRITE Excel? → **xlsxwriter**
- Need to READ Excel? → openpyxl (only option)
- Need both read AND write? → openpyxl for read, xlsxwriter for write

### Sheet Protection Pattern

Excel protection works as "lock everything, unlock specific cells":

```python
import xlsxwriter

wb = xlsxwriter.Workbook('output.xlsx')
ws = wb.add_worksheet()

# 1. Create locked format (default for all cells)
locked = wb.add_format({'locked': True})

# 2. Create unlocked format for editable cells
unlocked = wb.add_format({'locked': False})

# 3. Write cells with appropriate format
ws.write(0, 0, "Read-only", locked)
ws.write(0, 1, "Editable", unlocked)

# 4. Activate protection (makes locked property effective)
ws.protect('')  # Empty password = prevent accidents, not security

wb.close()
```

**Used in:** LanguageDataExporter (`exporter/excel_writer.py`)

---

## More paradigms to be added...

---

*Last updated: 2026-02-05*
