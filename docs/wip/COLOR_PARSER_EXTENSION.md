# Color Parser Extension Guide

**Status:** Current implementation works for PAColor format. This doc explains how to add more formats.

---

## Current Implementation

**Location:** `locaNext/src/lib/utils/colorParser.js`

**Supported Format:**
```
<PAColor0xHEXCODE>text<PAOldColor>
```

**Examples:**
- `<PAColor0xffe9bd23>gold text<PAOldColor>` → gold text
- `<PAColor0xff0000>red<PAOldColor>` → red text

---

## How to Add New Formats

### Step 1: Identify the Pattern

Common game color formats:
```
{Color(#ff0000)}text{/Color}
<color=red>text</color>
[color=#ff0000]text[/color]
{{rgb(255,0,0)}}text{{/rgb}}
```

### Step 2: Add Pattern to Parser

Edit `colorParser.js`:

```javascript
// Add new pattern constant
const PATTERNS = {
  // Existing PAColor pattern
  paColor: /<PAColor(0x[0-9a-fA-F]{6,8})>([\s\S]*?)<PAOldColor>/g,

  // Example: {Color(#hex)}text{/Color}
  curlyColor: /\{Color\(#([0-9a-fA-F]{6})\)\}([\s\S]*?)\{\/Color\}/g,

  // Example: <color=name>text</color>
  htmlColor: /<color=([a-zA-Z]+)>([\s\S]*?)<\/color>/g
};

// Add color name mapping for HTML-style
const COLOR_NAMES = {
  red: '#ff0000',
  green: '#00ff00',
  blue: '#0000ff',
  gold: '#ffd700',
  // ... add more as needed
};
```

### Step 3: Update parseColorTags Function

```javascript
export function parseColorTags(text) {
  // Try each pattern in order
  for (const [name, pattern] of Object.entries(PATTERNS)) {
    if (pattern.test(text)) {
      return parseWithPattern(text, pattern, name);
    }
  }
  return [{ text, color: null }];
}
```

### Step 4: Add Detection Function

```javascript
export function detectColorFormat(text) {
  if (/<PAColor0x/.test(text)) return 'paColor';
  if (/\{Color\(#/.test(text)) return 'curlyColor';
  if (/<color=/.test(text)) return 'htmlColor';
  return null;
}
```

---

## Testing New Formats

Add to test fixtures in `tests/fixtures/`:
```
Sample text with {Color(#ff0000)}red{/Color} and {Color(#00ff00)}green{/Color}.
```

Run tests:
```bash
npm test -- --grep "colorParser"
```

---

## Future Considerations

1. **Auto-detection:** Parser could auto-detect format per-file
2. **User preference:** Settings to choose which format to use for export
3. **Format conversion:** Convert between formats when needed

---

*Document created: 2025-12-28 | For future extension only*
