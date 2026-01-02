/**
 * Color Tag Parser
 *
 * Parses color tags like <PAColor0xffe9bd23>text<PAOldColor>
 * and returns segments with text and color information.
 */

/**
 * Convert hex color code to CSS color
 * Handles formats: 0xAABBCCDD (ARGB), 0xBBCCDD (RGB)
 *
 * @param {string} hexCode - e.g., "0xffe9bd23" or "0xFFf3d900"
 * @returns {string|null} - CSS color like "#e9bd23" or null if invalid
 */
export function hexToCSS(hexCode) {
  if (!hexCode) return null;

  // Remove 0x prefix and convert to lowercase
  const hex = hexCode.replace(/^0x/i, '').toLowerCase();

  if (hex.length === 8) {
    // ARGB format: first 2 chars are alpha, ignore them
    // Extract RGB (last 6 chars)
    return `#${hex.slice(2)}`;
  } else if (hex.length === 6) {
    // RGB format
    return `#${hex}`;
  }

  return null;
}

/**
 * Unescape HTML entities in color tags
 * Handles: &lt; -> <, &gt; -> >
 */
function unescapeColorTags(text) {
  if (!text) return text;
  // Only unescape angle brackets around PAColor tags to avoid breaking other content
  return text
    .replace(/&lt;(PAColor0x[0-9a-fA-F]{6,8})&gt;/gi, '<$1>')
    .replace(/&lt;(PAOldColor)&gt;/gi, '<$1>');
}

/**
 * Parse text with color tags into segments
 *
 * @param {string} text - Text with color tags
 * @returns {Array<{text: string, color: string|null}>} - Segments
 *
 * Example:
 *   Input: "Normal <PAColor0xffe9bd23>colored<PAOldColor> text"
 *   Output: [
 *     { text: "Normal ", color: null },
 *     { text: "colored", color: "#e9bd23" },
 *     { text: " text", color: null }
 *   ]
 */
export function parseColorTags(text) {
  if (!text || typeof text !== 'string') {
    return [{ text: text || '', color: null }];
  }

  // First unescape HTML entities in color tags (handles &lt;PAColor...&gt;)
  const unescapedText = unescapeColorTags(text);

  const segments = [];

  // Pattern 1: <PAColor0xHEX>text<PAOldColor> (properly closed)
  // Pattern 2: <PAColor0xHEX>text (unclosed - color extends to end or next tag)
  // We process both patterns in order

  let remainingText = unescapedText;
  let currentColor = null;

  // First, try to match properly closed tags
  const closedTagPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>([\s\S]*?)<PAOldColor>/g;

  let lastIndex = 0;
  let match;

  while ((match = closedTagPattern.exec(unescapedText)) !== null) {
    // Add text before the color tag (if any)
    if (match.index > lastIndex) {
      segments.push({
        text: unescapedText.slice(lastIndex, match.index),
        color: null
      });
    }

    // Add the colored segment
    const colorHex = match[1];
    const coloredText = match[2];
    const cssColor = hexToCSS(colorHex);

    segments.push({
      text: coloredText,
      color: cssColor
    });

    lastIndex = match.index + match[0].length;
  }

  // Check remaining text for unclosed color tags
  if (lastIndex < unescapedText.length) {
    const remaining = unescapedText.slice(lastIndex);

    // Check for unclosed color tag at the start of remaining text
    const unclosedMatch = remaining.match(/^<PAColor(0x[0-9a-fA-F]{6,8})>([\s\S]*)$/);
    if (unclosedMatch) {
      const colorHex = unclosedMatch[1];
      const coloredText = unclosedMatch[2];
      const cssColor = hexToCSS(colorHex);

      segments.push({
        text: coloredText,
        color: cssColor
      });
    } else {
      // No unclosed tag, just add remaining as plain text
      segments.push({
        text: remaining,
        color: null
      });
    }
  }

  // If no color tags found, return original text
  if (segments.length === 0) {
    segments.push({ text: unescapedText, color: null });
  }

  return segments;
}

/**
 * Check if text contains any color tags (raw or HTML-escaped)
 *
 * @param {string} text
 * @returns {boolean}
 */
export function hasColorTags(text) {
  if (!text || typeof text !== 'string') return false;
  // Check for both raw tags and HTML-escaped tags
  return /<PAColor0x[0-9a-fA-F]{6,8}>/.test(text) ||
         /&lt;PAColor0x[0-9a-fA-F]{6,8}&gt;/i.test(text);
}

/**
 * Strip all color tags from text (for plain text operations)
 * Handles both raw and HTML-escaped tags
 *
 * @param {string} text
 * @returns {string} - Text without color tags
 */
export function stripColorTags(text) {
  if (!text || typeof text !== 'string') return text || '';
  return text
    // Raw tags
    .replace(/<PAColor0x[0-9a-fA-F]{6,8}>/g, '')
    .replace(/<PAOldColor>/g, '')
    // HTML-escaped tags
    .replace(/&lt;PAColor0x[0-9a-fA-F]{6,8}&gt;/gi, '')
    .replace(/&lt;PAOldColor&gt;/gi, '');
}

/**
 * Convert PAColor tags to HTML for WYSIWYG editing
 * <PAColor0xffe9bd23>text<PAOldColor> → <span style="color:#e9bd23" data-pacolor="0xffe9bd23">text</span>
 *
 * @param {string} text - Text with PAColor tags
 * @returns {string} - HTML with colored spans
 */
export function paColorToHtml(text) {
  if (!text || typeof text !== 'string') return text || '';

  // First unescape any HTML-escaped color tags
  let result = text
    .replace(/&lt;(PAColor0x[0-9a-fA-F]{6,8})&gt;/gi, '<$1>')
    .replace(/&lt;(PAOldColor)&gt;/gi, '<$1>');

  // Convert closed tags: <PAColor0xHEX>text<PAOldColor> → <span>text</span>
  result = result.replace(
    /<PAColor(0x[0-9a-fA-F]{6,8})>([\s\S]*?)<PAOldColor>/gi,
    (match, hex, content) => {
      const cssColor = hexToCSS(hex);
      // Escape HTML entities in content to prevent XSS
      const safeContent = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      return `<span style="color:${cssColor}" data-pacolor="${hex}">${safeContent}</span>`;
    }
  );

  // Handle unclosed tags: <PAColor0xHEX>text → <span>text</span>
  result = result.replace(
    /<PAColor(0x[0-9a-fA-F]{6,8})>([^<]*?)$/gi,
    (match, hex, content) => {
      const cssColor = hexToCSS(hex);
      const safeContent = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      return `<span style="color:${cssColor}" data-pacolor="${hex}">${safeContent}</span>`;
    }
  );

  // Escape remaining text (not in spans) - but preserve the spans we just created
  // Split by our spans, escape the rest, rejoin
  const parts = result.split(/(<span[^>]*>[\s\S]*?<\/span>)/g);
  result = parts.map(part => {
    if (part.startsWith('<span')) {
      return part; // Keep spans as-is
    }
    // Escape any remaining < > that aren't our spans
    return part
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }).join('');

  // Convert newlines to <br> for contenteditable
  result = result.replace(/\n/g, '<br>');

  return result;
}

/**
 * Convert HTML from contenteditable back to PAColor format
 * <span style="color:#e9bd23" data-pacolor="0xffe9bd23">text</span> → <PAColor0xffe9bd23>text<PAOldColor>
 *
 * @param {string} html - HTML from contenteditable
 * @returns {string} - Text with PAColor tags
 */
export function htmlToPaColor(html) {
  if (!html || typeof html !== 'string') return html || '';

  let result = html;

  // Convert <br> back to newlines
  result = result.replace(/<br\s*\/?>/gi, '\n');

  // Convert colored spans back to PAColor tags
  // Match spans with data-pacolor attribute
  result = result.replace(
    /<span[^>]*data-pacolor="(0x[0-9a-fA-F]{6,8})"[^>]*>([\s\S]*?)<\/span>/gi,
    (match, hex, content) => {
      // Unescape HTML entities in content
      const unescaped = content
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>');
      return `<PAColor${hex}>${unescaped}<PAOldColor>`;
    }
  );

  // Also handle spans without data-pacolor but with color style (from manual color picker)
  result = result.replace(
    /<span[^>]*style="[^"]*color:\s*#([0-9a-fA-F]{6})[^"]*"[^>]*>([\s\S]*?)<\/span>/gi,
    (match, hex, content) => {
      // Unescape HTML entities in content
      const unescaped = content
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>');
      return `<PAColor0xff${hex}>${unescaped}<PAOldColor>`;
    }
  );

  // Unescape remaining HTML entities
  result = result
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');

  // Remove any remaining HTML tags (divs from contenteditable, etc)
  // BUT preserve PAColor/PAOldColor tags using negative lookahead
  result = result.replace(/<\/?div>/gi, '\n');
  result = result.replace(/<(?!\/?PA(?:Color|OldColor))[^>]+>/g, '');

  // Clean up multiple newlines
  result = result.replace(/\n{3,}/g, '\n\n');

  return result.trim();
}
