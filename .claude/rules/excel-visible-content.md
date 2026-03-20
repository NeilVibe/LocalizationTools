---
paths:
  - "RessourcesForCodingTheProject/NewScripts/**/*.py"
---

# Excel Column Hiding: Check Visible Content Only

When hiding columns in Excel output, use a 3-layer system:

1. **Row hiding** — hide rows by tester/manager status (FIXED, resolved)
2. **Column hiding** — hide entire user column blocks when zero data
3. **Final column sweep** — checks VISIBLE (non-hidden) rows only, catches resolved users

`final_column_sweep()` MUST run as ABSOLUTE LAST step before `wb.save()`. A user's column can have data but ALL rows are hidden (all FIXED/resolved) — the column appears empty to users but old logic kept it visible.
