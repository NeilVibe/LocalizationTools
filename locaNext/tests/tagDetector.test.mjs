/**
 * Tag Detector Tests
 *
 * Standalone test script for tagDetector.js.
 * Run: npx vitest run tests/tagDetector.test.mjs
 */

import { describe, it, expect } from 'vitest';
import { detectTags, hasTags } from '../src/lib/utils/tagDetector.js';

// ---- detectTags: individual tag types ----

describe('detectTags', () => {
  describe('braced tags', () => {
    it('detects {0} as braced tag', () => {
      const result = detectTags('{0}');
      expect(result).toHaveLength(1);
      expect(result[0].tag).toEqual({
        label: '0', type: 'braced', color: 'blue', raw: '{0}'
      });
    });

    it('detects {PlayerName} as braced tag', () => {
      const result = detectTags('{PlayerName}');
      expect(result).toHaveLength(1);
      expect(result[0].tag.label).toBe('PlayerName');
      expect(result[0].tag.type).toBe('braced');
    });
  });

  describe('param tags', () => {
    it('detects %1# as param tag', () => {
      const result = detectTags('%1#');
      expect(result).toHaveLength(1);
      expect(result[0].tag).toEqual({
        label: 'Param1', type: 'param', color: 'purple', raw: '%1#'
      });
    });

    it('detects %2# as param tag', () => {
      const result = detectTags('%2#');
      expect(result[0].tag.label).toBe('Param2');
    });
  });

  describe('escape tags', () => {
    it('detects \\n as escape tag', () => {
      const result = detectTags('\\n');
      expect(result).toHaveLength(1);
      expect(result[0].tag).toEqual({
        label: '\\n', type: 'escape', color: 'grey', raw: '\\n'
      });
    });

    it('detects \\t as escape tag', () => {
      const result = detectTags('\\t');
      expect(result[0].tag.label).toBe('\\t');
      expect(result[0].tag.type).toBe('escape');
    });

    it('detects \\1 as escape tag (digit is \\w)', () => {
      const result = detectTags('\\1');
      expect(result[0].tag.label).toBe('\\1');
      expect(result[0].tag.type).toBe('escape');
    });

    it('detects \\_ as escape tag (underscore is \\w)', () => {
      const result = detectTags('\\_');
      expect(result[0].tag.label).toBe('\\_');
      expect(result[0].tag.type).toBe('escape');
    });
  });

  describe('desc tags', () => {
    it('detects &desc; as desc tag', () => {
      const result = detectTags('&desc;');
      expect(result).toHaveLength(1);
      expect(result[0].tag).toEqual({
        label: 'desc', type: 'desc', color: 'orange', raw: '&desc;'
      });
    });

    it('detects &amp;desc; as desc tag', () => {
      const result = detectTags('&amp;desc;');
      expect(result).toHaveLength(1);
      expect(result[0].tag).toEqual({
        label: 'desc', type: 'desc', color: 'orange', raw: '&amp;desc;'
      });
    });
  });

  describe('staticinfo tags', () => {
    it('detects StaticInfo paired tag with all fields', () => {
      const result = detectTags('{StaticInfo:Knowledge:Elixir#Potion of Healing}');
      expect(result).toHaveLength(1);
      const tag = result[0].tag;
      expect(tag.label).toBe('Elixir');
      expect(tag.inner).toBe('Potion of Healing');
      expect(tag.type).toBe('staticinfo');
      expect(tag.color).toBe('green');
      expect(tag.raw).toBe('{StaticInfo:Knowledge:Elixir#Potion of Healing}');
    });

    it('handles case-insensitive StaticInfo/Staticinfo', () => {
      const result = detectTags('{Staticinfo:Quest:Dragon#Slay the dragon}');
      expect(result[0].tag.type).toBe('staticinfo');
      expect(result[0].tag.label).toBe('Dragon');
    });
  });

  // ---- Priority / overlap tests ----

  describe('priority ordering', () => {
    it('StaticInfo takes priority over braced', () => {
      const result = detectTags('{StaticInfo:Knowledge:Elixir#text}');
      expect(result).toHaveLength(1);
      expect(result[0].tag.type).toBe('staticinfo');
      // Must NOT be detected as braced
      expect(result[0].tag.type).not.toBe('braced');
    });

    it('braced does not match StaticInfo range', () => {
      const result = detectTags('before {StaticInfo:Knowledge:ID#inner} after');
      // Should be: text("before "), staticinfo tag, text(" after")
      expect(result).toHaveLength(3);
      expect(result[0].text).toBe('before ');
      expect(result[1].tag.type).toBe('staticinfo');
      expect(result[2].text).toBe(' after');
    });
  });

  // ---- Mixed text tests ----

  describe('mixed text', () => {
    it('detects multiple tags in mixed text', () => {
      const result = detectTags('Hello {0} world %1# end');
      expect(result).toHaveLength(5);
      expect(result[0].text).toBe('Hello ');
      expect(result[1].tag.label).toBe('0');
      expect(result[1].tag.type).toBe('braced');
      expect(result[2].text).toBe(' world ');
      expect(result[3].tag.label).toBe('Param1');
      expect(result[3].tag.type).toBe('param');
      expect(result[4].text).toBe(' end');
    });

    it('handles all 5 tag types in one string', () => {
      const input = '{StaticInfo:Knowledge:A#B} then {0} and %1# with \\n plus &desc;';
      const result = detectTags(input);
      const tagTypes = result.filter(s => s.tag).map(s => s.tag.type);
      expect(tagTypes).toEqual(['staticinfo', 'braced', 'param', 'escape', 'desc']);
    });
  });

  // ---- Edge cases ----

  describe('edge cases', () => {
    it('returns plain text segment for non-tag text', () => {
      const result = detectTags('Hello world');
      expect(result).toEqual([{ text: 'Hello world' }]);
    });

    it('returns empty text segment for empty string', () => {
      const result = detectTags('');
      expect(result).toEqual([{ text: '' }]);
    });

    it('returns empty text segment for null', () => {
      const result = detectTags(null);
      expect(result).toEqual([{ text: '' }]);
    });

    it('returns empty text segment for undefined', () => {
      const result = detectTags(undefined);
      expect(result).toEqual([{ text: '' }]);
    });

    it('handles consecutive tags without gap', () => {
      const result = detectTags('{0}{1}');
      expect(result).toHaveLength(2);
      expect(result[0].tag.label).toBe('0');
      expect(result[1].tag.label).toBe('1');
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
      expect(reconstructed).toBe(input);
    });
  }

  it('round-trips every segment has either .text or .tag.raw', () => {
    const input = '{StaticInfo:Quest:A#B} hello {0} %1# \\n &desc;';
    const segments = detectTags(input);
    for (const seg of segments) {
      expect(seg.text !== undefined || (seg.tag && seg.tag.raw !== undefined)).toBeTruthy();
    }
  });
});

// ---- hasTags ----

describe('hasTags', () => {
  it('returns true for braced tag', () => {
    expect(hasTags('{0}')).toBe(true);
  });

  it('returns true for param tag', () => {
    expect(hasTags('%1#')).toBe(true);
  });

  it('returns true for escape tag', () => {
    expect(hasTags('\\n')).toBe(true);
  });

  it('returns true for desc tag', () => {
    expect(hasTags('&desc;')).toBe(true);
  });

  it('returns true for amp desc tag', () => {
    expect(hasTags('&amp;desc;')).toBe(true);
  });

  it('returns true for StaticInfo tag', () => {
    expect(hasTags('{StaticInfo:Knowledge:Elixir#text}')).toBe(true);
  });

  it('returns false for plain text', () => {
    expect(hasTags('Hello world')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(hasTags('')).toBe(false);
  });

  it('returns false for null', () => {
    expect(hasTags(null)).toBe(false);
  });

  it('returns false for non-string', () => {
    expect(hasTags(42)).toBe(false);
  });
});

// ---- br-tag exclusion (TAG-04) ----

describe('br-tag exclusion (TAG-04)', () => {
  it('br-tag only text returns pure text segment, no pills', () => {
    const result = detectTags('Hello&lt;br/&gt;World');
    expect(result).toEqual([{ text: 'Hello&lt;br/&gt;World' }]);
  });

  it('multiple br-tags return pure text, no pills', () => {
    const result = detectTags('Text&lt;br/&gt;More&lt;br/&gt;End');
    expect(result).toEqual([{ text: 'Text&lt;br/&gt;More&lt;br/&gt;End' }]);
  });

  it('real tag + br-tag: Code pill preserved, br-tag is plain text', () => {
    const result = detectTags('{Code}&lt;br/&gt;More');
    expect(result).toHaveLength(2);
    expect(result[0].tag.label).toBe('Code');
    expect(result[0].tag.type).toBe('braced');
    expect(result[1].text).toBe('&lt;br/&gt;More');
  });

  it('hasTags returns false for br-tags only', () => {
    expect(hasTags('Hello&lt;br/&gt;World')).toBe(false);
  });

  it('hasTags returns true when br-tags mixed with real tags', () => {
    expect(hasTags('Hello&lt;br/&gt;{Code}')).toBe(true);
  });
});

// ---- combined color+code (TAG-05) ----

describe('combined color+code (TAG-05)', () => {
  it('PAColor wrapping braced code returns single combinedcolor pill', () => {
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;');
    expect(result).toHaveLength(1);
    expect(result[0].tag.label).toBe('ItemName');
    expect(result[0].tag.type).toBe('combinedcolor');
    expect(result[0].tag.color).toBe('combined');
    expect(result[0].tag.cssColor).toBe('#e9bd23');
    expect(result[0].tag.raw).toBe('&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;');
  });

  it('PAColor wrapping braced code with trailing text', () => {
    const result = detectTags('&lt;PAColor0xffff0000&gt;{HP}&lt;PAOldColor&gt; remaining');
    expect(result).toHaveLength(2);
    expect(result[0].tag.label).toBe('HP');
    expect(result[0].tag.type).toBe('combinedcolor');
    expect(result[0].tag.cssColor).toBe('#ff0000');
    expect(result[1].text).toBe(' remaining');
  });

  it('PAColor wrapping param returns combinedcolor pill', () => {
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;%1#&lt;PAOldColor&gt;');
    expect(result).toHaveLength(1);
    expect(result[0].tag.label).toBe('Param1');
    expect(result[0].tag.type).toBe('combinedcolor');
    expect(result[0].tag.cssColor).toBe('#e9bd23');
  });

  it('plain braced tag still works without PAColor', () => {
    const result = detectTags('Plain {Code} text');
    expect(result).toHaveLength(3);
    expect(result[1].tag.type).toBe('braced');
    expect(result[1].tag.color).toBe('blue');
  });

  it('PAColor wrapping plain text does NOT create combined pill', () => {
    // When PAColor wraps non-code text, ColorText handles it -- not tagDetector
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;just text&lt;PAOldColor&gt;');
    // Should return as plain text segments (no tag pills)
    expect(result.every(seg => !seg.tag || seg.tag.type !== 'combinedcolor')).toBeTruthy();
  });

  it('round-trips combined color+code', () => {
    const input = '&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;';
    const segments = detectTags(input);
    const reconstructed = segments.map(seg => seg.tag ? seg.tag.raw : seg.text).join('');
    expect(reconstructed).toBe(input);
  });

  it('combined pill with 6-char hex (no alpha)', () => {
    const result = detectTags('&lt;PAColor0xe9bd23&gt;{Code}&lt;PAOldColor&gt;');
    expect(result).toHaveLength(1);
    expect(result[0].tag.type).toBe('combinedcolor');
    expect(result[0].tag.cssColor).toBe('#e9bd23');
  });

  it('hasTags detects PAColor-wrapped code', () => {
    expect(hasTags('&lt;PAColor0xffe9bd23&gt;{Code}&lt;PAOldColor&gt;')).toBe(true);
  });
});

// ---- Mutation-killing assertions (D-10) ----
// Each test verifies a specific pattern's tag.type, which can ONLY be true
// if that pattern's regex exists in TAG_PATTERNS. Removing the regex would
// cause the test to fail.

describe('mutation-killing: combinedcolor pattern is essential', () => {
  it('detects PAColor-wrapped code only because combinedcolor regex exists', () => {
    const result = detectTags('&lt;PAColor0xffe9bd23&gt;{ItemName}&lt;PAOldColor&gt;');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('combinedcolor');
  });
});

describe('mutation-killing: staticinfo pattern is essential', () => {
  it('detects {StaticInfo:...} only because staticinfo regex exists', () => {
    const result = detectTags('{StaticInfo:Knowledge:Elixir#Potion}');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('staticinfo');
  });
});

describe('mutation-killing: param pattern is essential', () => {
  it('detects %1# only because param regex exists', () => {
    const result = detectTags('%1#');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('param');
  });
});

describe('mutation-killing: braced pattern is essential', () => {
  it('detects {PlayerName} only because braced regex exists', () => {
    const result = detectTags('{PlayerName}');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('braced');
  });
});

describe('mutation-killing: escape pattern is essential', () => {
  it('detects \\n only because escape regex exists', () => {
    const result = detectTags('\\n');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('escape');
  });
});

describe('mutation-killing: desc pattern is essential', () => {
  it('detects &desc; only because desc regex exists', () => {
    const result = detectTags('&desc;');
    expect(result).toHaveLength(1);
    expect(result[0].tag).toBeDefined();
    expect(result[0].tag.type).toBe('desc');
  });
});
