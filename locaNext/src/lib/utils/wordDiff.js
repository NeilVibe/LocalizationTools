/**
 * wordDiff.js - CJK-aware word-level diff utility
 *
 * Splits text into tokens (whitespace-delimited words + individual CJK characters)
 * and uses LCS algorithm to find minimal diff between two strings.
 *
 * Used by TMTab.svelte for fuzzy match diff highlighting.
 */

/**
 * Tokenize text into words and individual CJK characters.
 * CJK characters (U+3000-U+9FFF, U+AC00-U+D7AF Korean syllables) are each a separate token.
 * Latin/other text is split on whitespace boundaries.
 *
 * @param {string} text
 * @returns {string[]}
 */
export function tokenize(text) {
  if (!text) return [];

  // Match: individual CJK char OR sequence of non-whitespace non-CJK chars
  const regex = /[\u3000-\u9fff\uac00-\ud7af]|[^\s\u3000-\u9fff\uac00-\ud7af]+/g;
  const tokens = text.match(regex);
  return tokens || [];
}

/**
 * Compute word-level diff between original and match text using LCS.
 *
 * @param {string} original - The current source text
 * @param {string} match - The TM source text
 * @returns {{ original: Array<{text: string, type: 'same'|'removed'}>, match: Array<{text: string, type: 'same'|'added'}> }}
 */
export function computeWordDiff(original, match) {
  const tokensA = tokenize(original);
  const tokensB = tokenize(match);

  // Edge cases
  if (tokensA.length === 0 && tokensB.length === 0) {
    return { original: [], match: [] };
  }
  if (tokensA.length === 0) {
    return {
      original: [],
      match: tokensB.map(t => ({ text: t, type: 'added' }))
    };
  }
  if (tokensB.length === 0) {
    return {
      original: tokensA.map(t => ({ text: t, type: 'removed' })),
      match: []
    };
  }

  // Build LCS table
  const m = tokensA.length;
  const n = tokensB.length;
  const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (tokensA[i - 1] === tokensB[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find LCS
  const lcs = [];
  let i = m, j = n;
  while (i > 0 && j > 0) {
    if (tokensA[i - 1] === tokensB[j - 1]) {
      lcs.unshift({ aIdx: i - 1, bIdx: j - 1 });
      i--;
      j--;
    } else if (dp[i - 1][j] >= dp[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  // Build result arrays from LCS
  const resultA = [];
  const resultB = [];

  let aPos = 0, bPos = 0;
  for (const { aIdx, bIdx } of lcs) {
    // Tokens before this LCS match are removed/added
    while (aPos < aIdx) {
      resultA.push({ text: tokensA[aPos], type: 'removed' });
      aPos++;
    }
    while (bPos < bIdx) {
      resultB.push({ text: tokensB[bPos], type: 'added' });
      bPos++;
    }
    // The matching token
    resultA.push({ text: tokensA[aPos], type: 'same' });
    resultB.push({ text: tokensB[bPos], type: 'same' });
    aPos++;
    bPos++;
  }

  // Remaining tokens after last LCS match
  while (aPos < m) {
    resultA.push({ text: tokensA[aPos], type: 'removed' });
    aPos++;
  }
  while (bPos < n) {
    resultB.push({ text: tokensB[bPos], type: 'added' });
    bPos++;
  }

  return { original: resultA, match: resultB };
}
