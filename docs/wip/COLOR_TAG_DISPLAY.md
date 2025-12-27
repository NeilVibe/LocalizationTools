# Color Tag Display Feature

**Created:** 2025-12-27 | **Status:** PLANNING | **Priority:** NEXT

---

## Goal

Parse color codes in translation strings and display the text in actual colors.

**Example:**
```
Input:  <PAColor0xffe9bd23>100 %<PAOldColor>
Output: "100 %" displayed in gold/yellow (#e9bd23)
```

---

## Color Patterns Found

| Pattern | Example | Color Format |
|---------|---------|--------------|
| `<PAColor0xAABBCCDD>text<PAOldColor>` | `<PAColor0xffe9bd23>100 %<PAOldColor>` | ARGB hex |
| `<color=XXX>text</color>` | `<color=red>Warning</color>` | Named or hex |
| `{PAColor(#HEX)}text{PAOldColor}` | `{PAColor(#FF0000)}Red{PAOldColor}` | RGB hex |

---

## Hex Color Parsing

### Format: `0xAABBCCDD` (ARGB)

```
0xffe9bd23
   ││└───┴── Blue:  0x23 = 35
   │└────── Green: 0xbd = 189
   └─────── Red:   0xe9 = 233
            Alpha: 0xff = 255 (opaque)

CSS: #e9bd23 (RGB, ignore alpha for display)
```

### Parsing Logic

```javascript
function parseHexColor(code) {
  // "0xffe9bd23" or "0xe9bd23"
  const hex = code.replace('0x', '');

  if (hex.length === 8) {
    // ARGB format
    const r = parseInt(hex.substr(2, 2), 16);
    const g = parseInt(hex.substr(4, 2), 16);
    const b = parseInt(hex.substr(6, 2), 16);
    return `#${hex.substr(2)}`;  // "#e9bd23"
  } else if (hex.length === 6) {
    // RGB format
    return `#${hex}`;
  }
  return null;
}
```

---

## Implementation Plan

### WIP-1: Create color parser utility

**File:** `locaNext/src/lib/utils/colorParser.js`

```javascript
// Parse all color patterns
export function parseColorTags(text) {
  const segments = [];
  // ... regex matching
  return segments; // [{text, color}, {text, color}, ...]
}

// Convert hex to CSS
export function hexToCSS(hex) {
  // Handle 0xAABBCCDD, #RRGGBB, named colors
}
```

### WIP-2: Create ColorText component

**File:** `locaNext/src/lib/components/ldm/ColorText.svelte`

```svelte
<script>
  export let text;
  const segments = parseColorTags(text);
</script>

{#each segments as segment}
  {#if segment.color}
    <span style="color: {segment.color}">{segment.text}</span>
  {:else}
    {segment.text}
  {/if}
{/each}
```

### WIP-3: Integrate into VirtualGrid

**File:** `locaNext/src/lib/components/ldm/VirtualGrid.svelte`

Replace raw text display with `<ColorText>` component in cells.

### WIP-4: Update sample data

Add 10K sample strings with various color patterns for testing.

### WIP-5: Test and verify

- Visual test with different color codes
- Performance test with 10K colored rows

---

## Sample Strings (Real Examples)

```
<PAColor0xffe9bd23>100 %<PAOldColor>
<PAColor0xffe9bd23>{TextBind:CLICK_ON_RMB} à nouveau pour ajouter le colorant à la palette.<PAOldColor>
<PAColor0xffe9bd23>Un colorant de Valencia. Il préserve l'aspect étincelant du métal.<PAOldColor>
<PAColor0xFFf3d900>※ 선박 등록증 사용 방법<PAOldColor>
<PAColor0xffff0000>ERROR<PAOldColor>
<PAColor0xff00ff00>SUCCESS<PAOldColor>
Normal text with <PAColor0xffe9bd23>colored part<PAOldColor> and more text
```

**Note:** Colors apply to BOTH source and target columns.

---

## Test Cases

| Input | Expected Display |
|-------|------------------|
| `<PAColor0xffe9bd23>100 %<PAOldColor>` | "100 %" in gold (#e9bd23) |
| `<PAColor0xffff0000>ERROR<PAOldColor>` | "ERROR" in red (#ff0000) |
| `<PAColor0xff00ff00>OK<PAOldColor>` | "OK" in green (#00ff00) |
| `Text <PAColor0xff0000ff>blue<PAOldColor> more` | "Text " normal, "blue" in blue, " more" normal |

---

## Questions to Resolve

1. **Alpha channel** - Display with opacity or ignore?
2. **Hover behavior** - Show color code on hover?
3. **Edit mode** - How to edit text with color tags?
4. **Copy/paste** - Preserve tags when copying?

---

## Dependencies

- VirtualGrid.svelte (existing)
- Cell rendering system (existing)
- No external libraries needed

---

*Ready for implementation after plan approval*
