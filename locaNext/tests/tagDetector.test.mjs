/**
 * Tag Detector Tests
 *
 * Standalone Node.js test script for tagDetector.js.
 * Run: node --test tests/tagDetector.test.mjs
 */

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { detectTags, hasTags } from '../src/lib/utils/tagDetector.js';

// ---- detectTags: individual tag types ----

describe('detectTags', () => {
  describe('braced tags', () => {
    it('detects {0} as braced tag', () => {
      const result = detectTags('{0}');
      assert.strictEqual(result.length, 1);
      assert.deepStrictEqual(result[0].tag, {
        label: '0', type: 'braced', color: 'blue', raw: '{0}'
      });
    });

    it('detects {PlayerName} as braced tag', () => {
      const result = detectTags('{PlayerName}');
      assert.strictEqual(result.length, 1);
      assert.strictEqual(result[0].tag.label, 'PlayerName');
      assert.strictEqual(result[0].tag.type, 'braced');
    });
  });

  describe('param tags', () => {
    it('detects %1# as param tag', () => {
      const result = detectTags('%1#');
      assert.strictEqual(result.length, 1);
      assert.deepStrictEqual(result[0].tag, {
        label: 'Param1', type: 'param', color: 'purple', raw: '%1#'
      });
    });

    it('detects %2# as param tag', () => {
      const result = detectTags('%2#');
      assert.strictEqual(result[0].tag.label, 'Param2');
    });
  });

  describe('escape tags', () => {
    it('detects \\n as escape tag', () => {
      const result = detectTags('\\n');
      assert.strictEqual(result.length, 1);
      assert.deepStrictEqual(result[0].tag, {
        label: '\\n', type: 'escape', color: 'grey', raw: '\\n'
      });
    });

    it('detects \\t as escape tag', () => {
      const result = detectTags('\\t');
      assert.strictEqual(result[0].tag.label, '\\t');
      assert.strictEqual(result[0].tag.type, 'escape');
    });

    it('detects \\1 as escape tag (digit is \\w)', () => {
      const result = detectTags('\\1');
      assert.strictEqual(result[0].tag.label, '\\1');
      assert.strictEqual(result[0].tag.type, 'escape');
    });

    it('detects \\_ as escape tag (underscore is \\w)', () => {
      const result = detectTags('\\_');
      assert.strictEqual(result[0].tag.label, '\\_');
      assert.strictEqual(result[0].tag.type, 'escape');
    });
  });

  describe('desc tags', () => {
    it('detects &desc; as desc tag', () => {
      const result = detectTags('&desc;');
      assert.strictEqual(result.length, 1);
      assert.deepStrictEqual(result[0].tag, {
        label: 'desc', type: 'desc', color: 'orange', raw: '&desc;'
      });
    });

    it('detects &amp;desc; as desc tag', () => {
      const result = detectTags('&amp;desc;');
      assert.strictEqual(result.length, 1);
      assert.deepStrictEqual(result[0].tag, {
        label: 'desc', type: 'desc', color: 'orange', raw: '&amp;desc;'
      });
    });
  });

  describe('staticinfo tags', () => {
    it('detects StaticInfo paired tag with all fields', () => {
      const result = detectTags('{StaticInfo:Knowledge:Elixir#Potion of Healing}');
      assert.strictEqual(result.length, 1);
      const tag = result[0].tag;
      assert.strictEqual(tag.label, 'Elixir');
      assert.strictEqual(tag.inner, 'Potion of Healing');
      assert.strictEqual(tag.type, 'staticinfo');
      assert.strictEqual(tag.color, 'green');
      assert.strictEqual(tag.raw, '{StaticInfo:Knowledge:Elixir#Potion of Healing}');
    });

    it('handles case-insensitive StaticInfo/Staticinfo', () => {
      const result = detectTags('{Staticinfo:Quest:Dragon#Slay the dragon}');
      assert.strictEqual(result[0].tag.type, 'staticinfo');
      assert.strictEqual(result[0].tag.label, 'Dragon');
    });
  });

  // ---- Priority / overlap tests ----

  describe('priority ordering', () => {
    it('StaticInfo takes priority over braced', () => {
      const result = detectTags('{StaticInfo:Knowledge:Elixir#text}');
      assert.strictEqual(result.length, 1);
      assert.strictEqual(result[0].tag.type, 'staticinfo');
      // Must NOT be detected as braced
      assert.notStrictEqual(result[0].tag.type, 'braced');
    });

    it('braced does not match StaticInfo range', () => {
      const result = detectTags('before {StaticInfo:Knowledge:ID#inner} after');
      // Should be: text("before "), staticinfo tag, text(" after")
      assert.strictEqual(result.length, 3);
      assert.strictEqual(result[0].text, 'before ');
      assert.strictEqual(result[1].tag.type, 'staticinfo');
      assert.strictEqual(result[2].text, ' after');
    });
  });

  // ---- Mixed text tests ----

  describe('mixed text', () => {
    it('detects multiple tags in mixed text', () => {
      const result = detectTags('Hello {0} world %1# end');
      assert.strictEqual(result.length, 5);
      assert.strictEqual(result[0].text, 'Hello ');
      assert.strictEqual(result[1].tag.label, '0');
      assert.strictEqual(result[1].tag.type, 'braced');
      assert.strictEqual(result[2].text, ' world ');
      assert.strictEqual(result[3].tag.label, 'Param1');
      assert.strictEqual(result[3].tag.type, 'param');
      assert.strictEqual(result[4].text, ' end');
    });

    it('handles all 5 tag types in one string', () => {
      const input = '{StaticInfo:Knowledge:A#B} then {0} and %1# with \\n plus &desc;';
      const result = detectTags(input);
      const tagTypes = result.filter(s => s.tag).map(s => s.tag.type);
      assert.deepStrictEqual(tagTypes, ['staticinfo', 'braced', 'param', 'escape', 'desc']);
    });
  });

  // ---- Edge cases ----

  describe('edge cases', () => {
    it('returns plain text segment for non-tag text', () => {
      const result = detectTags('Hello world');
      assert.deepStrictEqual(result, [{ text: 'Hello world' }]);
    });

    it('returns empty text segment for empty string', () => {
      const result = detectTags('');
      assert.deepStrictEqual(result, [{ text: '' }]);
    });

    it('returns empty text segment for null', () => {
      const result = detectTags(null);
      assert.deepStrictEqual(result, [{ text: '' }]);
    });

    it('returns empty text segment for undefined', () => {
      const result = detectTags(undefined);
      assert.deepStrictEqual(result, [{ text: '' }]);
    });

    it('handles consecutive tags without gap', () => {
      const result = detectTags('{0}{1}');
      assert.strictEqual(result.length, 2);
      assert.strictEqual(result[0].tag.label, '0');
      assert.strictEqual(result[1].tag.label, '1');
    });
  });
});

// ---- Round-trip integrity (CRITICAL for merge safety) ----

describe('round-trip integrity', () => {
  // The tag detector is DISPLAY ONLY. When data is saved/merged back,
  // the raw text must be perfectly reconstructable from segments.
  // This proves no data is lost or modified during detection.

  function reconstructRaw(segments) {
    return segments.map(seg => seg.tag ? seg.tag.raw : seg.text).join('');
  }

  const MOCK_GAME_DATA = [
    // Real-world game localization strings with tags
    '{0}이(가) {1}을(를) 사용했습니다.',
    '%1#님이 %2#을(를) 획득하였습니다.',
    '첫 번째 줄\\n두 번째 줄\\n세 번째 줄',
    '{StaticInfo:Knowledge:Elixir#회복의 물약}을 발견했습니다!',
    '아이템 설명&desc;',
    // Complex mixed: all 5 tag types in realistic context
    '{StaticInfo:Quest:Dragon#용을 처치하라} 보상: {0} 골드 (%1# 배율)\\n&desc;',
    // Edge: tags adjacent to Korean text with no spaces
    '{PlayerName}의 공격력이{0}만큼 증가했습니다.',
    // Edge: multiple escapes in a row
    '\\n\\t\\n',
    // Edge: empty braced (should still round-trip)
    'before {} after',
    // Plain text (no tags — must also round-trip)
    '태그가 없는 일반 텍스트입니다.',
    // Real XML-style data with br tags (display converts these, but raw stays)
    '첫 번째&lt;br/&gt;두 번째',
  ];

  for (const input of MOCK_GAME_DATA) {
    it(`round-trips: "${input.slice(0, 50)}${input.length > 50 ? '...' : ''}"`, () => {
      const segments = detectTags(input);
      const reconstructed = reconstructRaw(segments);
      assert.strictEqual(reconstructed, input,
        `Round-trip FAILED.\nInput:  ${input}\nOutput: ${reconstructed}`);
    });
  }

  it('round-trips every segment has either .text or .tag.raw', () => {
    const input = '{StaticInfo:Quest:A#B} hello {0} %1# \\n &desc;';
    const segments = detectTags(input);
    for (const seg of segments) {
      assert.ok(seg.text !== undefined || (seg.tag && seg.tag.raw !== undefined),
        `Segment missing both .text and .tag.raw: ${JSON.stringify(seg)}`);
    }
  });
});

// ---- hasTags ----

describe('hasTags', () => {
  it('returns true for braced tag', () => {
    assert.strictEqual(hasTags('{0}'), true);
  });

  it('returns true for param tag', () => {
    assert.strictEqual(hasTags('%1#'), true);
  });

  it('returns true for escape tag', () => {
    assert.strictEqual(hasTags('\\n'), true);
  });

  it('returns true for desc tag', () => {
    assert.strictEqual(hasTags('&desc;'), true);
  });

  it('returns true for amp desc tag', () => {
    assert.strictEqual(hasTags('&amp;desc;'), true);
  });

  it('returns true for StaticInfo tag', () => {
    assert.strictEqual(hasTags('{StaticInfo:Knowledge:Elixir#text}'), true);
  });

  it('returns false for plain text', () => {
    assert.strictEqual(hasTags('Hello world'), false);
  });

  it('returns false for empty string', () => {
    assert.strictEqual(hasTags(''), false);
  });

  it('returns false for null', () => {
    assert.strictEqual(hasTags(null), false);
  });

  it('returns false for non-string', () => {
    assert.strictEqual(hasTags(42), false);
  });
});

// ---- br-tag exclusion (TAG-04) ----

describe('br-tag exclusion (TAG-04)', () => {
  it('br-tag only text returns pure text segment, no pills', () => {
    const result = detectTags('Hello&lt;br/&gt;World');
    assert.deepStrictEqual(result, [{ text: 'Hello&lt;br/&gt;World' }]);
  });

  it('multiple br-tags return pure text, no pills', () => {
    const result = detectTags('Text&lt;br/&gt;More&lt;br/&gt;End');
    assert.deepStrictEqual(result, [{ text: 'Text&lt;br/&gt;More&lt;br/&gt;End' }]);
  });

  it('real tag + br-tag: Code pill preserved, br-tag is plain text', () => {
    const result = detectTags('{Code}&lt;br/&gt;More');
    assert.strictEqual(result.length, 2);
    assert.strictEqual(result[0].tag.label, 'Code');
    assert.strictEqual(result[0].tag.type, 'braced');
    assert.strictEqual(result[1].text, '&lt;br/&gt;More');
  });

  it('hasTags returns false for br-tags only', () => {
    assert.strictEqual(hasTags('Hello&lt;br/&gt;World'), false);
  });

  it('hasTags returns true when br-tags mixed with real tags', () => {
    assert.strictEqual(hasTags('Hello&lt;br/&gt;{Code}'), true);
  });
});

// ---- combined color+code (TAG-05) ----

describe('combined color+code (TAG-05)', () => {
  it('PAColor wrapping braced code returns single combinedcolor pill', () => {
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;');
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].tag.label, 'ItemName');
    assert.strictEqual(result[0].tag.type, 'combinedcolor');
    assert.strictEqual(result[0].tag.color, 'combined');
    assert.strictEqual(result[0].tag.cssColor, '#e9bd23');
    assert.strictEqual(result[0].tag.raw, '&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;');
  });

  it('PAColor wrapping braced code with trailing text', () => {
    const result = detectTags('&lt;PAColor0xffff0000&gt;{HP}&lt;PAOldColor&gt; remaining');
    assert.strictEqual(result.length, 2);
    assert.strictEqual(result[0].tag.label, 'HP');
    assert.strictEqual(result[0].tag.type, 'combinedcolor');
    assert.strictEqual(result[0].tag.cssColor, '#ff0000');
    assert.strictEqual(result[1].text, ' remaining');
  });

  it('PAColor wrapping param returns combinedcolor pill', () => {
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;%1#&lt;PAOldColor&gt;');
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].tag.label, 'Param1');
    assert.strictEqual(result[0].tag.type, 'combinedcolor');
    assert.strictEqual(result[0].tag.cssColor, '#e9bd23');
  });

  it('plain braced tag still works without PAColor', () => {
    const result = detectTags('Plain {Code} text');
    assert.strictEqual(result.length, 3);
    assert.strictEqual(result[1].tag.type, 'braced');
    assert.strictEqual(result[1].tag.color, 'blue');
  });

  it('PAColor wrapping plain text does NOT create combined pill', () => {
    // When PAColor wraps non-code text, ColorText handles it -- not tagDetector
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;just text&lt;PAOldColor&gt;');
    // Should return as plain text segments (no tag pills)
    assert.ok(result.every(seg => !seg.tag || seg.tag.type !== 'combinedcolor'),
      'Should not create combinedcolor pill for plain text inside PAColor');
  });

  it('round-trips combined color+code', () => {
    const input = '&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;';
    const segments = detectTags(input);
    const reconstructed = segments.map(seg => seg.tag ? seg.tag.raw : seg.text).join('');
    assert.strictEqual(reconstructed, input);
  });

  it('combined pill with 6-char hex (no alpha)', () => {
    const result = detectTags('&lt;PAColor0xe9bd23&gt;{Code}&lt;PAOldColor&gt;');
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].tag.type, 'combinedcolor');
    assert.strictEqual(result[0].tag.cssColor, '#e9bd23');
  });

  it('hasTags detects PAColor-wrapped code', () => {
    assert.strictEqual(hasTags('&lt;PAColor0xffe9bd23&gt;{Code}&lt;PAOldColor&gt;'), true);
  });
});
