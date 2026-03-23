# Phase 73: Regex Tag Visualizer - Research

**Researched:** 2026-03-23
**Domain:** Svelte 5 frontend, regex-based tag detection, inline pill rendering
**Confidence:** HIGH

## Summary

Phase 73 adds MemoQ-style inline tag pills to the VirtualGrid translation editor. The feature detects 5 tag types (`{N}`, `%N#`, `\X`, `{StaticInfo:...}`, `&desc;`) using regex patterns from `tmx_tools.py` and renders them as colored inline pills instead of raw text.

The existing codebase already has a near-identical pattern: `colorParser.js` + `ColorText.svelte` parses `<PAColor>` tags and renders colored text segments. The tag visualizer follows the same architecture: `tagDetector.js` (parser) + `TagText.svelte` (renderer), composed with `ColorText` in VirtualGrid display mode.

**Primary recommendation:** Create `tagDetector.js` that splits text into `{text, tag}` segments, create `TagText.svelte` that wraps `ColorText` and adds tag pills, and replace the two `<ColorText>` calls in VirtualGrid (lines 2844 and 2894) with `<TagText>`. Tags are display-only pills; edit mode continues to show raw text via the existing `contenteditable` WYSIWYG editor.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TAG-01 | tagDetector.js detects all 5 tag types using tmx_tools.py regexes | Exact regexes extracted from tmx_tools.py lines 248-314; priority ordering documented |
| TAG-02 | TagText.svelte renders detected tags as colored inline pills in VirtualGrid display mode | ColorText.svelte pattern documented as template; VirtualGrid insertion points identified at lines 2844, 2894 |
| TAG-03 | Tags preserved exactly during editing (pills to raw text in edit mode, raw text to pills on save) | Edit mode already uses raw text via `contenteditable` + `paColorToHtml`/`htmlToPaColor`; no tag-specific edit changes needed |
</phase_requirements>

## Architecture Patterns

### Existing Pattern to Follow: ColorText Pipeline

The codebase already has a text-parsing-to-visual-rendering pipeline:

```
Data flow (display mode):
  row.source/target
    -> formatGridText(text)     // converts &lt;br/&gt; and \n to actual newlines
    -> <ColorText text={...}>   // parses PAColor tags, renders colored spans
    -> DOM

Data flow (edit mode):
  row.target
    -> formatTextForDisplay()   // converts line breaks for textarea
    -> paColorToHtml()          // converts PAColor to <span style="color:...">
    -> contenteditable.innerHTML

  contenteditable.innerHTML
    -> htmlToPaColor()          // converts spans back to PAColor
    -> formatTextForSave()      // converts newlines back to file format
    -> API save
```

### New Pattern: TagText wraps ColorText

```
Data flow (display mode - NEW):
  row.source/target
    -> <TagText text={...}>
        -> tagDetector.detectTags(text)  // returns [{text, tag}] segments
        -> for non-tag segments: formatGridText() + <ColorText>
        -> for tag segments: <span class="tag-pill {color}">
    -> DOM

Data flow (edit mode - UNCHANGED):
  Same as before. Tags appear as raw text in contenteditable.
  No tag-to-HTML or HTML-to-tag conversion needed.
```

### CRITICAL: formatGridText and \n Conflict

**Current behavior (line 2186):** `formatGridText` converts literal `\n` to actual newlines for display.

**Problem:** `\n` is also a tag pattern that should render as a grey pill.

**Solution:** Tag detection MUST run BEFORE `formatGridText`. The `TagText` component should:
1. Run `detectTags(rawText)` on the raw text
2. For non-tag segments, apply `formatGridText()` logic (br + newline conversion)
3. For tag segments, render as pills (no text conversion)

This means `formatGridText` moves INSIDE `TagText` and only applies to plain-text segments.

### Recommended Project Structure

```
locaNext/src/lib/
  utils/
    tagDetector.js           # NEW: regex detection, returns segments
    colorParser.js           # EXISTING: PAColor detection (unchanged)
  components/ldm/
    TagText.svelte           # NEW: renders tag pills + delegates to ColorText
    ColorText.svelte         # EXISTING: renders colored text (unchanged)
    VirtualGrid.svelte       # MODIFIED: swap ColorText -> TagText at 2 locations
```

### Anti-Patterns to Avoid
- **Modifying ColorText.svelte:** Keep it focused on color rendering. Tag pills are a separate concern composed on top.
- **Doing tag detection inside VirtualGrid:** VirtualGrid is already 4299 lines. All detection logic goes in `tagDetector.js`.
- **Converting tags to HTML in edit mode:** Tags are NOT colors. They should simply show as raw text when editing. No `paColorToHtml`-equivalent needed for tags.
- **Modifying formatGridText globally:** The `\n` conversion must be preserved for non-tag text. Move the logic into TagText where it applies only to plain segments.

## Standard Stack

### Core

No new libraries needed. This is pure Svelte 5 + regex work.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | existing | Component rendering with Runes | Already in use |
| JavaScript RegExp | built-in | Tag pattern matching | No external regex library needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw regex in JS | Parser combinator (Nearley, PEG.js) | Overkill -- 5 simple patterns, regex is sufficient |
| Custom pill CSS | Carbon Design badges | Carbon badges are too large for inline text; custom pills needed |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color tag rendering | Custom color parser | Existing `colorParser.js` + `ColorText.svelte` | Already handles PAColor tags perfectly |
| Text editing with tags | Custom contenteditable tag editor | Existing WYSIWYG contenteditable | Edit mode shows raw text; no tag editing UX needed |

## Common Pitfalls

### Pitfall 1: Regex Priority / Overlap
**What goes wrong:** `{StaticInfo:Knowledge:ID#text}` matches both the StaticInfo pattern AND the generic `{braced}` pattern, causing double-detection or wrong pill type.
**Why it happens:** The generic braced pattern `\{([^}]+)\}` matches StaticInfo if not excluded.
**How to avoid:** Use the EXACT negative lookahead from tmx_tools.py: `\{(?!Static[Ii]nfo:\w+:)([^}]+)\}`. Process patterns in priority order: StaticInfo FIRST, then `%N#`, then braced, then `\X`, then `&desc;`.
**Warning signs:** StaticInfo text appearing in blue pills instead of green.

### Pitfall 2: formatGridText Eating Tags
**What goes wrong:** `\n` and `\t` are converted to whitespace by `formatGridText` BEFORE tag detection, so they never get pill treatment.
**Why it happens:** Current pipeline: `formatGridText(text)` runs first, then `<ColorText>` renders.
**How to avoid:** Run tag detection on RAW text. Apply `formatGridText` logic only to non-tag plain-text segments inside `TagText`.
**Warning signs:** `\n` showing as line breaks instead of grey pills.

### Pitfall 3: HTML Entity Confusion
**What goes wrong:** `&desc;` in the data might be stored as `&amp;desc;` (HTML-escaped) or `&desc;` (raw). Missing one form causes tags to not be detected.
**Why it happens:** VirtualGrid receives data that may or may not be HTML-escaped depending on the source.
**How to avoid:** Match BOTH forms in tagDetector: `&amp;desc;` and `&desc;`, exactly as tmx_tools.py does (line 309-314).
**Warning signs:** `&desc;` pills not appearing in some files.

### Pitfall 4: Performance with Large Grids
**What goes wrong:** Running 5 regex patterns on every cell of a 10,000-row grid causes jank.
**Why it happens:** VirtualGrid is virtualized (only visible rows render), but each visible cell runs the detector.
**How to avoid:** Use a single combined regex pass (one `matchAll` with alternation) instead of 5 separate passes. Cache results with `$derived` in TagText. The virtual scroll already limits rendered rows to ~30-50.
**Warning signs:** Scroll lag when tag-heavy files are loaded.

### Pitfall 5: StaticInfo Paired Tags
**What goes wrong:** `{StaticInfo:Knowledge:Elixir#Potion of Healing}` should show `[Elixir]` as a green pill with "Potion of Healing" as wrapped inner text, but naive implementation shows the entire match as one pill.
**Why it happens:** StaticInfo is a PAIRED tag (bpt/ept equivalent) that wraps inner text.
**How to avoid:** The StaticInfo regex has 3 capture groups: category, ID, inner text. Render as: `[ID]` pill + inner text plain + closing indicator, OR simplify to a single `[ID]` pill around the inner text with a green background.
**Warning signs:** Inner text of StaticInfo tags not visible to translators.

## Code Examples

### tagDetector.js - Core Detection Pattern

Source: tmx_tools.py lines 248-314

```javascript
// Tag types with their regex, display format, and color
const TAG_PATTERNS = [
  {
    name: 'staticinfo',
    // Priority 1: Must match BEFORE generic braced
    regex: /\{Static[Ii]nfo:(\w+):([^#}]+)#([^}]+)\}/g,
    format: (m) => ({ label: m[2], inner: m[3], type: 'staticinfo' }),
    color: 'green'
  },
  {
    name: 'param',
    // Priority 2: %N# parameters
    regex: /%(\d)#/g,
    format: (m) => ({ label: `Param${m[1]}`, type: 'param' }),
    color: 'purple'
  },
  {
    name: 'braced',
    // Priority 3: {placeholder} - excludes StaticInfo via negative lookahead
    regex: /\{(?!Static[Ii]nfo:\w+:)([^}]+)\}/g,
    format: (m) => ({ label: m[1], type: 'braced' }),
    color: 'blue'
  },
  {
    name: 'escape',
    // Priority 4: \n, \t, etc.
    regex: /\\(\w)/g,
    format: (m) => ({ label: `\\${m[1]}`, type: 'escape' }),
    color: 'grey'
  },
  {
    name: 'desc',
    // Priority 5: &desc; or &amp;desc;
    regex: /&(?:amp;)?desc;/g,
    format: () => ({ label: 'desc', type: 'desc' }),
    color: 'orange'
  }
];

/**
 * Detect all tags in text, return ordered segments.
 * Each segment is either { text } (plain) or { tag: { label, type, color, raw } }.
 *
 * Uses single-pass approach: find all matches across all patterns,
 * sort by position, split text into segments.
 */
export function detectTags(text) {
  if (!text || typeof text !== 'string') return [{ text: text || '' }];

  const matches = [];
  for (const pattern of TAG_PATTERNS) {
    const re = new RegExp(pattern.regex.source, pattern.regex.flags);
    let m;
    while ((m = re.exec(text)) !== null) {
      // Skip if this position already claimed by a higher-priority pattern
      const overlaps = matches.some(
        existing => m.index >= existing.start && m.index < existing.end
      );
      if (!overlaps) {
        const info = pattern.format(m);
        matches.push({
          start: m.index,
          end: m.index + m[0].length,
          raw: m[0],
          ...info,
          color: pattern.color
        });
      }
    }
  }

  // Sort by position
  matches.sort((a, b) => a.start - b.start);

  // Build segments
  const segments = [];
  let lastEnd = 0;
  for (const match of matches) {
    if (match.start > lastEnd) {
      segments.push({ text: text.slice(lastEnd, match.start) });
    }
    segments.push({ tag: match });
    lastEnd = match.end;
  }
  if (lastEnd < text.length) {
    segments.push({ text: text.slice(lastEnd) });
  }

  return segments;
}

/**
 * Quick check if text contains any detectable tags.
 */
export function hasTags(text) {
  if (!text || typeof text !== 'string') return false;
  return /%\d#/.test(text) ||
         /\{[^}]+\}/.test(text) ||
         /\\[a-zA-Z]/.test(text) ||
         /&(?:amp;)?desc;/.test(text);
}
```

### TagText.svelte - Rendering Pattern

```svelte
<script>
  import { detectTags, hasTags } from '$lib/utils/tagDetector.js';
  import ColorText from './ColorText.svelte';

  let { text = '' } = $props();

  let segments = $derived(hasTags(text) ? detectTags(text) : null);

  // Apply formatGridText only to plain text segments
  function formatPlainText(t) {
    if (!t) return '';
    return t.replace(/&lt;br\/&gt;/g, '\n');
    // NOTE: Do NOT convert \n here -- \n is handled as a tag pill
  }
</script>

{#if segments}
  <span class="tag-text">
    {#each segments as seg, i (i)}
      {#if seg.tag}
        <span class="tag-pill tag-{seg.tag.color}" title={seg.tag.raw}>
          {seg.tag.label}
        </span>
        {#if seg.tag.inner}
          <ColorText text={formatPlainText(seg.tag.inner)} />
        {/if}
      {:else}
        <ColorText text={formatPlainText(seg.text)} />
      {/if}
    {/each}
  </span>
{:else}
  <ColorText text={formatPlainText(text)} />
{/if}
```

### VirtualGrid.svelte - Insertion Points

Two lines need changing:

```svelte
<!-- Line 2844: Source cell (display-only) -->
<!-- BEFORE: -->
<span class="cell-content"><ColorText text={formatGridText(row.source) || ""} /></span>
<!-- AFTER: -->
<span class="cell-content"><TagText text={row.source || ""} /></span>

<!-- Line 2894: Target cell (display mode) -->
<!-- BEFORE: -->
<span class="cell-content"><ColorText text={formatGridText(row.target) || ""} /></span>
<!-- AFTER: -->
<span class="cell-content"><TagText text={row.target || ""} /></span>
```

**Key change:** `formatGridText` is NO LONGER called at the VirtualGrid level. It moves inside TagText where it applies only to non-tag plain text segments.

### Tag Pill CSS

```css
.tag-pill {
  display: inline;
  padding: 0 4px;
  border-radius: 3px;
  font-size: 0.85em;
  font-family: monospace;
  vertical-align: baseline;
  white-space: nowrap;
  cursor: default;
  user-select: none;
}

.tag-blue    { background: #1e3a5f; color: #7ec8f0; }  /* {placeholder} */
.tag-purple  { background: #3d1f5c; color: #c4a0e8; }  /* %N# param */
.tag-grey    { background: #3a3a3a; color: #b0b0b0; }  /* \n \t escapes */
.tag-green   { background: #1a4a2e; color: #7ed4a0; }  /* StaticInfo */
.tag-orange  { background: #5c3a1a; color: #e8b070; }  /* &desc; */
```

Dark-theme colors chosen to match the existing VirtualGrid dark theme with grey/dark cells.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw regex text in grid | Colored PAColor tags via ColorText | v4.0 (Phase ~35) | Translators see colored text |
| No tag visualization | MemoQ-style inline pills (this phase) | v8.0 (Phase 73) | Translators see tag meaning |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Playwright (no vitest configured for unit tests) |
| Config file | `locaNext/playwright.config.js` |
| Quick run command | `cd locaNext && npx playwright test --grep "tag"` |
| Full suite command | `cd locaNext && npx playwright test` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TAG-01 | tagDetector detects all 5 tag types | unit | Needs vitest or manual validation in browser | No - Wave 0 |
| TAG-02 | TagText renders pills in display mode | smoke/visual | Playwright screenshot comparison | No - Wave 0 |
| TAG-03 | Edit mode shows raw text, save preserves tags | smoke | Playwright: double-click cell, verify raw text, save, verify pills return | No - Wave 0 |

### Sampling Rate
- **Per task commit:** Manual browser check (DEV mode) + Playwright screenshot
- **Per wave merge:** Full Playwright suite
- **Phase gate:** All 5 tag types visible as pills in both source and target columns

### Wave 0 Gaps
- [ ] `locaNext/src/lib/utils/tagDetector.test.js` -- unit tests for detection (needs vitest setup OR can be a simple Node.js script)
- [ ] Playwright test for tag pill rendering (screenshot comparison)
- [ ] Test data: need at least one row with each of the 5 tag types loaded into the dev environment

**Recommendation:** Since there is no vitest setup, validate TAG-01 with a standalone Node.js test script that imports tagDetector.js and runs assertions. TAG-02 and TAG-03 validated visually via Playwright screenshots + DEV mode manual check.

## Open Questions

1. **StaticInfo paired tag UX**
   - What we know: StaticInfo wraps inner text (e.g., `{StaticInfo:Knowledge:Elixir#Potion of Healing}`). tmx_tools.py converts this to `<bpt>...<ept>` pairs.
   - What's unclear: Should the pill show just `[Elixir]` with inner text flowing normally, or should the entire construct be a single highlighted block?
   - Recommendation: Render as `[Elixir]` green pill followed by inner text in normal font, then a closing `[/]` green pill. This matches MemoQ's bpt/ept visual style.

2. **\n in formatGridText conflict**
   - What we know: Line 2186 converts `\n` to actual newlines. But `\n` is also a tag that should show as a grey pill.
   - What's unclear: Is there data where `\n` means "literal backslash-n tag" vs "actual newline"? In game localization, `\n` is always a tag (escape sequence), not a human newline.
   - Recommendation: Tag detection runs first. All `\n` patterns become pills. Only `&lt;br/&gt;` is converted to actual newlines in non-tag text.

3. **Reference column**
   - What we know: Line 2926 renders reference text WITHOUT ColorText (plain `{formatGridText(refText)}`).
   - What's unclear: Should tag pills also appear in the reference column?
   - Recommendation: YES, for consistency. Wire `<TagText>` into the reference cell too.

## Sources

### Primary (HIGH confidence)
- `server/services/merge/tmx_tools.py` lines 248-314 -- exact regex patterns and priority ordering
- `locaNext/src/lib/utils/colorParser.js` -- existing parser pattern (full file reviewed)
- `locaNext/src/lib/components/ldm/ColorText.svelte` -- existing renderer pattern (full file reviewed)
- `locaNext/src/lib/components/ldm/VirtualGrid.svelte` -- cell rendering at lines 2844, 2894, 2926; edit mode at lines 1264-1340; formatGridText at line 2181
- `~/.claude/projects/-home-neil1988-LocalizationTools/memory/reference_tag_regex_patterns.md` -- pre-documented tag patterns

### Secondary (MEDIUM confidence)
- MemoQ tag visualization concept -- industry-standard CAT tool pattern for tag pills

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pure Svelte 5 + regex, no external dependencies needed
- Architecture: HIGH - follows existing ColorText pattern exactly, insertion points clearly identified
- Pitfalls: HIGH - regex priority and formatGridText conflict identified from source code analysis

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependencies to become stale)
