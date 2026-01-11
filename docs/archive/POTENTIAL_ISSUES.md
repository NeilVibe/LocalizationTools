# Potential Issues - Future Reference

**Created:** 2025-12-17 | **Status:** For future consideration only

These are observations that may or may not be issues. Only fix if specific user feedback received.

---

## XLS Transfer: `<PAOldColor>` Edge Case

**Location:** `server/tools/xlstransfer/core.py:320-322`

**Scenario:** When `<PAColor>` is at position 0 of the original text.

**What happens:**
```python
# Input:  "<PAColor>경고!<PAOldColor>" + translation "Warning!"
# Output: "<PAColor>Warning!"  (missing <PAOldColor>)
```

**Why:**
```python
# Line 322 returns early, skipping <PAOldColor> check at lines 345-346
if codes:
    return ''.join(codes) + translated  # Early return
```

**Potential fix (if ever needed):**
```python
if codes:
    result = ''.join(codes) + translated
    if original.endswith("<PAOldColor>"):
        result += "<PAOldColor>"
    return result
```

**Status:** NOT A BUG - Same code exists in original monolith. Team has not reported issues. Only fix if user feedback received.

**Test Confirmation (2025-12-17):**
```
# Position 0 - loses <PAOldColor>
Input:  <PAColor0xffe9bd23>2시간 동안...<PAOldColor>
Output: <PAColor0xffe9bd23>Chance +1 pendant 2 heures  ← Missing

# Text before color - preserves <PAOldColor>
Input:  짐칸 : <PAColor0xffe9bd23>11칸<PAOldColor>...
Output: Emplacements : 11...<PAOldColor>  ← Present
```

---

## KR Similar: `adapt_structure()` Uses Literal `\\n`

**Location:** `server/tools/kr_similar/core.py:30`

**Note:** The function splits on `\\n` (literal backslash-n string), NOT actual newline characters. This is correct behavior because language data files store newlines as literal `\n` strings.

**Status:** NOT A BUG - Working as designed.

---

*Add future observations here.*
