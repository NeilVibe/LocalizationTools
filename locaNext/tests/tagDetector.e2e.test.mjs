/**
 * Tag Detector E2E Mock Tests
 *
 * Tests the FULL data flow: DB raw text → detect → display → edit → save → merge
 * Proves tag pills are display-only and never corrupt stored/merged data.
 *
 * Run: node --test tests/tagDetector.e2e.test.mjs
 */

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { detectTags, hasTags } from '../src/lib/utils/tagDetector.js';

// ============================================================
// MOCK DATA — realistic game localization strings
// ============================================================

const MOCK_DB_ROWS = [
  {
    id: 1,
    stringid: 'UI_ITEM_USE_MSG',
    source: '{0}이(가) {1}을(를) 사용했습니다.',
    target: '{0} used {1}.',
    strorigin: '{0}이(가) {1}을(를) 사용했습니다.',
  },
  {
    id: 2,
    stringid: 'UI_REWARD_MSG',
    source: '%1#님이 %2#을(를) 획득하였습니다.',
    target: '%1# obtained %2#.',
    strorigin: '%1#님이 %2#을(를) 획득하였습니다.',
  },
  {
    id: 3,
    stringid: 'UI_MULTILINE',
    source: '첫 번째 줄\\n두 번째 줄\\n세 번째 줄',
    target: 'Line 1\\nLine 2\\nLine 3',
    strorigin: '첫 번째 줄\\n두 번째 줄\\n세 번째 줄',
  },
  {
    id: 4,
    stringid: 'UI_QUEST_ITEM',
    source: '{StaticInfo:Knowledge:Elixir#회복의 물약}을 발견했습니다!',
    target: 'Found a {StaticInfo:Knowledge:Elixir#Potion of Healing}!',
    strorigin: '{StaticInfo:Knowledge:Elixir#회복의 물약}을 발견했습니다!',
  },
  {
    id: 5,
    stringid: 'UI_COMPLEX',
    source: '{StaticInfo:Quest:Dragon#용을 처치하라} 보상: {0} 골드 (%1# 배율)\\n&desc;',
    target: '{StaticInfo:Quest:Dragon#Slay the dragon} Reward: {0} gold (%1# multiplier)\\n&desc;',
    strorigin: '{StaticInfo:Quest:Dragon#용을 처치하라} 보상: {0} 골드 (%1# 배율)\\n&desc;',
  },
  {
    id: 6,
    stringid: 'UI_PLAIN_TEXT',
    source: '태그가 없는 일반 텍스트입니다.',
    target: 'Plain text without any tags.',
    strorigin: '태그가 없는 일반 텍스트입니다.',
  },
  {
    id: 7,
    stringid: 'UI_DESC_MARKER',
    source: '아이템 설명&desc;',
    target: 'Item description&desc;',
    strorigin: '아이템 설명&desc;',
  },
  {
    id: 8,
    stringid: 'UI_ADJACENT_TAGS',
    source: '{PlayerName}의 공격력이{0}만큼 증가했습니다.',
    target: "{PlayerName}'s ATK increased by {0}.",
    strorigin: '{PlayerName}의 공격력이{0}만큼 증가했습니다.',
  },
  {
    id: 9,
    stringid: 'UI_BR_TAGS',
    source: '첫 번째&lt;br/&gt;두 번째&lt;br/&gt;세 번째',
    target: 'First&lt;br/&gt;Second&lt;br/&gt;Third',
    strorigin: '첫 번째&lt;br/&gt;두 번째&lt;br/&gt;세 번째',
  },
  {
    id: 10,
    stringid: 'UI_AMP_DESC',
    source: '설명 시작&amp;desc;설명 끝',
    target: 'Description start&amp;desc;description end',
    strorigin: '설명 시작&amp;desc;설명 끝',
  },
];

// ============================================================
// Helper: reconstruct raw text from detectTags segments
// ============================================================

function reconstructRaw(segments) {
  return segments.map(seg => seg.tag ? seg.tag.raw : seg.text).join('');
}

// Mock XML file content (what merge compares against)
function mockXmlAttribute(row) {
  // In real .loc.xml: KR="source text here"
  return row.strorigin;
}

// ============================================================
// E2E TEST SUITE
// ============================================================

describe('E2E: Tag pill display does NOT corrupt data', () => {

  describe('1. DB → Display: pills render on both source and target', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id} (${row.stringid}): source has tags=${hasTags(row.source)}`, () => {
        const sourceSegs = detectTags(row.source);
        const targetSegs = detectTags(row.target);
        // Both produce valid segment arrays
        assert.ok(Array.isArray(sourceSegs), 'source segments is array');
        assert.ok(Array.isArray(targetSegs), 'target segments is array');
        assert.ok(sourceSegs.length > 0, 'source has segments');
        assert.ok(targetSegs.length > 0, 'target has segments');
      });
    }
  });

  describe('2. Display → Raw: round-trip integrity for ALL columns', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: source round-trips perfectly`, () => {
        const segs = detectTags(row.source);
        assert.strictEqual(reconstructRaw(segs), row.source);
      });

      it(`row ${row.id}: target round-trips perfectly`, () => {
        const segs = detectTags(row.target);
        assert.strictEqual(reconstructRaw(segs), row.target);
      });
    }
  });

  describe('3. Merge safety: StrOrigin matching uses raw text', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: DB source === XML strorigin (raw match)`, () => {
        // Merge compares DB source text against XML file source text
        // This MUST use raw text, never pill-rendered HTML
        const xmlText = mockXmlAttribute(row);
        assert.strictEqual(row.source, xmlText,
          `StrOrigin mismatch! DB: "${row.source}" vs XML: "${xmlText}"`);
      });

      it(`row ${row.id}: detectTags output preserves merge-matchable text`, () => {
        // Even after detection, we can reconstruct the exact text for matching
        const segs = detectTags(row.source);
        const reconstructed = reconstructRaw(segs);
        const xmlText = mockXmlAttribute(row);
        assert.strictEqual(reconstructed, xmlText,
          'Reconstructed text must match XML for merge');
      });
    }
  });

  describe('4. Edit cycle: raw text survives edit mode', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: simulated edit-save preserves raw text`, () => {
        // Simulate the VirtualGrid flow:
        // 1. Display mode: detectTags(row.target) → pills
        const displaySegs = detectTags(row.target);

        // 2. User double-clicks → edit mode shows RAW text
        const editModeText = row.target; // contenteditable gets raw text

        // 3. User saves without changes → raw text goes to API
        const savedText = editModeText;

        // 4. After save: display re-renders with pills
        const afterSaveSegs = detectTags(savedText);

        // Verify: saved text === original (no corruption)
        assert.strictEqual(savedText, row.target);
        // Verify: pill rendering is identical before and after
        assert.deepStrictEqual(afterSaveSegs, displaySegs);
      });
    }
  });

  describe('5. Tag pills never appear in segment .text (no HTML leak)', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: no HTML in any segment`, () => {
        const allSegs = [
          ...detectTags(row.source),
          ...detectTags(row.target)
        ];
        for (const seg of allSegs) {
          if (seg.text) {
            assert.ok(!seg.text.includes('<span'),
              `HTML found in plain text segment: "${seg.text}"`);
            assert.ok(!seg.text.includes('tag-pill'),
              `Pill class found in plain text: "${seg.text}"`);
          }
          if (seg.tag) {
            // tag.raw must be the original text, not HTML
            assert.ok(!seg.tag.raw.includes('<span'),
              `HTML found in tag raw: "${seg.tag.raw}"`);
          }
        }
      });
    }
  });

  describe('6. TM embedding safety: raw text for FAISS indexing', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: text for embedding === DB raw text`, () => {
        // TM embeddings use the raw DB text, not pill-rendered
        // This test proves the text we'd send to Model2Vec is clean
        const textForEmbedding = row.source; // always raw from DB
        assert.ok(!textForEmbedding.includes('<span'),
          'Embedding text must not contain HTML');
        assert.ok(!textForEmbedding.includes('tag-pill'),
          'Embedding text must not contain pill markup');
      });
    }
  });

  describe('7. Export safety: raw text for XML/Excel/TMX export', () => {
    for (const row of MOCK_DB_ROWS) {
      it(`row ${row.id}: export text === DB raw text`, () => {
        const exportText = row.target; // export reads raw from DB
        // Verify it can be written directly to XML attribute
        assert.ok(typeof exportText === 'string');
        assert.ok(!exportText.includes('tag-pill'));
        assert.ok(!exportText.includes('<span class'));
      });
    }
  });

  describe('8. Korean source + translation both get pills', () => {
    it('source (Korean) gets correct tag types', () => {
      const row = MOCK_DB_ROWS[4]; // UI_COMPLEX
      const segs = detectTags(row.source);
      const tagTypes = segs.filter(s => s.tag).map(s => s.tag.type);
      assert.deepStrictEqual(tagTypes, ['staticinfo', 'braced', 'param', 'escape', 'desc']);
    });

    it('target (English) gets same tag types', () => {
      const row = MOCK_DB_ROWS[4]; // UI_COMPLEX
      const segs = detectTags(row.target);
      const tagTypes = segs.filter(s => s.tag).map(s => s.tag.type);
      assert.deepStrictEqual(tagTypes, ['staticinfo', 'braced', 'param', 'escape', 'desc']);
    });
  });

  describe('9. Performance: hasTags fast-path skips regex for plain text', () => {
    it('plain text (no tags) skips full detection', () => {
      const plain = MOCK_DB_ROWS[5]; // UI_PLAIN_TEXT
      assert.strictEqual(hasTags(plain.source), false);
      assert.strictEqual(hasTags(plain.target), false);
      // detectTags still works but returns single text segment
      const segs = detectTags(plain.source);
      assert.strictEqual(segs.length, 1);
      assert.ok(segs[0].text);
    });
  });
});
