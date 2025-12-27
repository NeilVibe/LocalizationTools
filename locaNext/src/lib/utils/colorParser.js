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

  const segments = [];

  // Pattern: <PAColor0xHEX>text<PAOldColor>
  // Captures: (color hex), (text between tags)
  const colorTagPattern = /<PAColor(0x[0-9a-fA-F]{6,8})>([\s\S]*?)<PAOldColor>/g;

  let lastIndex = 0;
  let match;

  while ((match = colorTagPattern.exec(text)) !== null) {
    // Add text before the color tag (if any)
    if (match.index > lastIndex) {
      segments.push({
        text: text.slice(lastIndex, match.index),
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

  // Add remaining text after last color tag
  if (lastIndex < text.length) {
    segments.push({
      text: text.slice(lastIndex),
      color: null
    });
  }

  // If no color tags found, return original text
  if (segments.length === 0) {
    segments.push({ text, color: null });
  }

  return segments;
}

/**
 * Check if text contains any color tags
 *
 * @param {string} text
 * @returns {boolean}
 */
export function hasColorTags(text) {
  if (!text || typeof text !== 'string') return false;
  return /<PAColor0x[0-9a-fA-F]{6,8}>/.test(text);
}

/**
 * Strip all color tags from text (for plain text operations)
 *
 * @param {string} text
 * @returns {string} - Text without color tags
 */
export function stripColorTags(text) {
  if (!text || typeof text !== 'string') return text || '';
  return text
    .replace(/<PAColor0x[0-9a-fA-F]{6,8}>/g, '')
    .replace(/<PAOldColor>/g, '');
}
