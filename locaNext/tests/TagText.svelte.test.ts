import { render } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TagText from '../src/lib/components/ldm/TagText.svelte';

// Mock tagDetector per D-12: do NOT test regex logic from component tests
vi.mock('$lib/utils/tagDetector.js', () => ({
  detectTags: vi.fn(),
  hasTags: vi.fn(),
}));

// Mock colorParser so ColorText renders plain text without needing real color parsing
vi.mock('$lib/utils/colorParser.js', () => ({
  parseColorTags: vi.fn(() => []),
  hasColorTags: vi.fn(() => false),
  hexToCSS: vi.fn((hex: string) => hex),
  stripColorTags: vi.fn((t: string) => t),
  paColorToHtml: vi.fn((t: string) => t),
  htmlToPaColor: vi.fn((t: string) => t),
}));

import { detectTags, hasTags } from '$lib/utils/tagDetector.js';

const mockedHasTags = vi.mocked(hasTags);
const mockedDetectTags = vi.mocked(detectTags);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TagText', () => {
  it('renders plain text without tag pills when no tags detected', () => {
    mockedHasTags.mockReturnValue(false);

    const { container } = render(TagText, { props: { text: 'Hello world' } });

    // No tag pills should be rendered
    expect(container.querySelectorAll('.tag-pill').length).toBe(0);
    // Text should be present in the DOM
    expect(container.textContent).toContain('Hello world');
  });

  it('renders braced tag pill with correct CSS class', () => {
    mockedHasTags.mockReturnValue(true);
    mockedDetectTags.mockReturnValue([
      { tag: { label: '0', type: 'braced', color: 'blue', raw: '{0}' } },
    ]);

    const { container } = render(TagText, { props: { text: '{0}' } });

    const pill = container.querySelector('.tag-pill.tag-blue');
    expect(pill).not.toBeNull();
    expect(pill!.textContent!.trim()).toBe('0');
  });

  it('renders combinedcolor pill with combinedcolor class', () => {
    mockedHasTags.mockReturnValue(true);
    mockedDetectTags.mockReturnValue([
      {
        tag: {
          label: 'code',
          type: 'combinedcolor',
          color: 'combinedcolor',
          raw: '&lt;PAColor0xffe9bd23&gt;{code}&lt;PAOldColor&gt;',
          cssColor: '#FF0000',
        },
      },
    ]);

    const { container } = render(TagText, { props: { text: 'test' } });

    const pill = container.querySelector('.tag-pill.tag-combinedcolor');
    expect(pill).not.toBeNull();
  });

  it('combinedcolor pill receives title with raw tag and renders label', () => {
    // Verifies cssColor data flows through the combinedcolor branch
    // NOTE: Svelte 5 template style expressions (style="background: {expr}")
    // are not applied by jsdom. Per D-13, we assert on class names and
    // element attributes, not computed CSS values.
    mockedHasTags.mockReturnValue(true);
    mockedDetectTags.mockReturnValue([
      {
        tag: {
          label: 'code',
          type: 'combinedcolor',
          color: 'combinedcolor',
          raw: '&lt;PAColor0xffe9bd23&gt;{code}&lt;PAOldColor&gt;',
          cssColor: '#FF0000',
        },
      },
    ]);

    const { container } = render(TagText, { props: { text: 'test' } });

    const pill = container.querySelector('.tag-pill.tag-combinedcolor');
    expect(pill).not.toBeNull();
    // Title attribute carries the raw tag (tooltip)
    expect(pill!.getAttribute('title')).toContain('PAColor');
    // Label renders inside the pill
    expect(pill!.textContent!.trim()).toBe('code');
  });

  it('renders mixed text + tag + text in correct DOM order', () => {
    mockedHasTags.mockReturnValue(true);
    mockedDetectTags.mockReturnValue([
      { text: 'before ' },
      { tag: { label: '0', type: 'braced', color: 'blue', raw: '{0}' } },
      { text: ' after' },
    ]);

    const { container } = render(TagText, { props: { text: 'before {0} after' } });

    // Should have exactly one pill
    const pills = container.querySelectorAll('.tag-pill');
    expect(pills.length).toBe(1);
    expect(pills[0].textContent!.trim()).toBe('0');

    // Full text content should contain all segments in order
    const fullText = container.textContent || '';
    const beforeIdx = fullText.indexOf('before');
    const pillIdx = fullText.indexOf('0', fullText.indexOf('before') + 6);
    const afterIdx = fullText.indexOf('after');
    expect(beforeIdx).toBeLessThan(pillIdx);
    expect(pillIdx).toBeLessThan(afterIdx);
  });

  it('renders without crash for empty and undefined input', () => {
    mockedHasTags.mockReturnValue(false);

    // Empty string should not throw
    expect(() => render(TagText, { props: { text: '' } })).not.toThrow();

    // Undefined (uses default empty string from $props)
    expect(() => render(TagText, { props: { text: undefined as any } })).not.toThrow();
  });
});
