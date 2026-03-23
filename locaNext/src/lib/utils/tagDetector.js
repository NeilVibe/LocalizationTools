/**
 * Tag Detector
 *
 * Detects 5 inline tag types used in game localization data and returns
 * ordered segments for pill rendering. Patterns sourced from
 * server/services/merge/tmx_tools.py lines 248-314.
 *
 * Tag types (priority order):
 *   1. staticinfo  {StaticInfo:Category:ID#inner}  -> green pill
 *   2. param       %N#                              -> purple pill
 *   3. braced      {placeholder}                    -> blue pill
 *   4. escape      \n \t \1 etc.                    -> grey pill
 *   5. desc        &desc; or &amp;desc;             -> orange pill
 */

// Tag patterns in priority order — higher priority patterns are checked first
// to prevent lower-priority patterns from claiming the same text range.
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
    // Priority 3: {placeholder} — excludes StaticInfo via negative lookahead
    regex: /\{(?!Static[Ii]nfo:\w+:)([^}]+)\}/g,
    format: (m) => ({ label: m[1], type: 'braced' }),
    color: 'blue'
  },
  {
    name: 'escape',
    // Priority 4: \n, \t, \1, \_, etc. — uses \w to match tmx_tools.py exactly
    regex: /\\(\w)/g,
    format: (m) => ({ label: `\\${m[1]}`, type: 'escape' }),
    color: 'grey'
  },
  {
    name: 'desc',
    // Priority 5: &desc; or &amp;desc; (dual-form entity matching)
    regex: /&(?:amp;)?desc;/g,
    format: () => ({ label: 'desc', type: 'desc' }),
    color: 'orange'
  }
];

/**
 * Detect all tags in text, return ordered segments.
 * Each segment is either { text } (plain) or { tag: { label, type, color, raw, inner? } }.
 *
 * Uses single-pass approach: find all matches across all patterns,
 * sort by position, split text into segments.
 *
 * @param {string} text - Raw text to scan for tags
 * @returns {Array<{text: string} | {tag: {label: string, type: string, color: string, raw: string, inner?: string}}>}
 */
export function detectTags(text) {
  if (!text || typeof text !== 'string') return [{ text: text || '' }];

  const matches = [];

  for (const pattern of TAG_PATTERNS) {
    // Create a fresh RegExp to reset lastIndex
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
    segments.push({
      tag: {
        label: match.label,
        type: match.type,
        color: match.color,
        raw: match.raw,
        ...(match.inner !== undefined ? { inner: match.inner } : {})
      }
    });
    lastEnd = match.end;
  }
  if (lastEnd < text.length) {
    segments.push({ text: text.slice(lastEnd) });
  }

  return segments.length > 0 ? segments : [{ text }];
}

/**
 * Quick check if text contains any detectable tags.
 * Uses simple patterns without capture groups for speed.
 *
 * @param {string} text
 * @returns {boolean}
 */
export function hasTags(text) {
  if (!text || typeof text !== 'string') return false;
  return /%\d#/.test(text) ||
         /\{[^}]+\}/.test(text) ||
         /\\[\w]/.test(text) ||
         /&(?:amp;)?desc;/.test(text);
}
