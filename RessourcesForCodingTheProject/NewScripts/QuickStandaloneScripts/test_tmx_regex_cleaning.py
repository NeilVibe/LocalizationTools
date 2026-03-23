#!/usr/bin/env python3
"""
Test script for TMX regex cleaning patterns.
Tests clean_tmx_folder_data's _clean_segment function against
various MemoQ <ph> patterns — both currently handled and failing ones.
"""
import re
import html
import sys

# ===================================================================
# Reproduce the EXACT regex logic from tmxconvert41.py clean_tmx_folder_data
# ===================================================================

SEG_RE = re.compile(r'(<seg[^>]*>)(.*?)(</seg>)', re.DOTALL | re.IGNORECASE)
ZERO_WIDTH_RE = re.compile(r'[\u200B\u200C\u200D]')
BPT_EPT_RE = re.compile(
    r'<bpt\b[^>]*>'
    r'&lt;mq:rxt\s+displaytext=&quot;(.*?)&quot;\s+val=&quot;\{Staticinfo:Knowledge:[^#}]+#&quot;&gt;</bpt>'
    r'(.*?)'
    r'<ept\b[^>]*>.*?</ept>',
    flags=re.DOTALL | re.IGNORECASE
)
PH_RE = re.compile(
    r'<ph\b(?![^>]*\btype=[\'"]fmt[\'"])[^>]*>(.*?)</ph>',
    flags=re.DOTALL | re.IGNORECASE
)
PH_SELFCLOSE_RE = re.compile(
    r'<ph\b[^>]*/\s*>',
    flags=re.IGNORECASE
)
GENERIC_BPT_EPT_RE = re.compile(
    r'<bpt\b[^>]*>[^<]*</bpt>(.*?)<ept\b[^>]*>[^<]*</ept>',
    flags=re.DOTALL | re.IGNORECASE
)
FORMATTING_CONTENT_RE = re.compile(
    r'^<(?:cf\b|/cf|b>|/b>|i>|/i>|u>|/u>|sub>|/sub>|sup>|/sup>)',
    flags=re.IGNORECASE
)


def _clean_segment_ORIGINAL(seg_content):
    """Original _clean_segment logic from tmxconvert41.py (BEFORE fix)"""
    content = seg_content
    content = ZERO_WIDTH_RE.sub('', content)
    def _bpt_repl(m):
        ident, inner = m.group(1), m.group(2)
        return f'{{Staticinfo:Knowledge:{ident}#{inner}}}'
    content = BPT_EPT_RE.sub(_bpt_repl, content)
    def _ph_repl(m):
        ph_inner = m.group(1)
        decoded = html.unescape(ph_inner)
        vm = re.search(r'val="([^"]+)"', decoded)
        return vm.group(1) if vm else ''
    content = PH_RE.sub(_ph_repl, content)
    content = re.sub(
        r'<ph\b[^>]*\btype=[\'"]fmt[\'"][^>]*>.*?</ph>',
        '', content, flags=re.DOTALL | re.IGNORECASE
    )
    content = re.sub(r'\r\n|\r|\n', '&lt;br/&gt;', content)
    content = content.replace('\\n', '&lt;br/&gt;')
    content = re.sub(r'&amp;lt;br\s*/&amp;gt;', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    content = re.sub(r'<\s*br\s*/?\s*>', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    content = content.replace('<br/', '&lt;br/&gt;')
    content = re.sub(r'\bbr/\b', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    return content


def _clean_segment_NEW(seg_content):
    """NEW _clean_segment logic with smart fallback (AFTER fix)"""
    content = seg_content
    # 1) strip zero-width
    content = ZERO_WIDTH_RE.sub('', content)
    # 2) reverse Staticinfo bpt/ept
    def _bpt_repl(m):
        ident, inner = m.group(1), m.group(2)
        return f'{{Staticinfo:Knowledge:{ident}#{inner}}}'
    content = BPT_EPT_RE.sub(_bpt_repl, content)
    # 3) generic <bpt>...<ept> pairs — keep inner text only
    content = GENERIC_BPT_EPT_RE.sub(r'\1', content)
    # 4) reverse non-fmt <ph> → smart extraction
    def _ph_repl(m):
        ph_inner = m.group(1)
        if not ph_inner or ph_inner.isspace():
            return ''
        decoded = html.unescape(ph_inner)
        # Priority 1: extract val="..." (re-encode & to preserve entities)
        vm = re.search(r'val="([^"]+)"', decoded)
        if vm:
            val = vm.group(1)
            val = val.replace('&', '&amp;')
            return val
        # Priority 2: if it's formatting content → remove
        if FORMATTING_CONTENT_RE.search(decoded):
            return ''
        # Priority 3: displaytext but no val → extract displaytext
        dm = re.search(r'displaytext="([^"]+)"', decoded)
        if dm:
            return dm.group(1)
        # Priority 4: structural XML tag but NOT <br/> → remove
        stripped = decoded.strip()
        if (stripped.startswith('<') and stripped.endswith('>')
                and not re.match(r'<\s*br\s*/?\s*>', stripped, re.IGNORECASE)):
            return ''
        # Priority 5: raw inner text as-is
        return ph_inner
    content = PH_RE.sub(_ph_repl, content)
    # 5) remove self-closing <ph .../> tags
    content = PH_SELFCLOSE_RE.sub('', content)
    # 6) drop fmt placeholders
    content = re.sub(
        r'<ph\b[^>]*\btype=[\'"]fmt[\'"][^>]*>.*?</ph>',
        '', content, flags=re.DOTALL | re.IGNORECASE
    )
    # 7) normalize newlines
    content = re.sub(r'\r\n|\r|\n', '&lt;br/&gt;', content)
    content = content.replace('\\n', '&lt;br/&gt;')
    # 8) normalize <br> variants
    content = re.sub(r'&amp;lt;br\s*/&amp;gt;', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    content = re.sub(r'<\s*br\s*/?\s*>', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    content = content.replace('<br/', '&lt;br/&gt;')
    content = re.sub(r'\bbr/\b', '&lt;br/&gt;', content, flags=re.IGNORECASE)
    return content


def run_test(test_name, seg_content, expected, clean_func):
    """Run a single test and report results."""
    result = clean_func(seg_content)
    passed = result == expected
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_name}")
    if not passed:
        print(f"    INPUT:    {seg_content!r}")
        print(f"    EXPECTED: {expected!r}")
        print(f"    GOT:      {result!r}")
        print()
    return passed


def run_all_tests(label, clean_func):
    print(f"\n{'=' * 80}")
    print(f"  {label}")
    print(f"{'=' * 80}")

    tests_passed = 0
    tests_failed = 0

    # GROUP A: MemoQ <ph> with val= (should work)
    print("\n  --- GROUP A: MemoQ <ph> with val= ---")
    test_cases = [
        ("A1: MemoQ ph with val (Name)", '<ph>&lt;mq:rxt-req displaytext="Name" val="{Name}" /&gt;</ph>', '{Name}'),
        ("A2: MemoQ ph with val (br)", '<ph>&lt;mq:rxt displaytext="br" val="&lt;br/&gt;" /&gt;</ph>', '&lt;br/&gt;'),
        ("A3: MemoQ ph with val (param)", '<ph>&lt;mq:rxt-req displaytext="Param1" val="%1#" /&gt;</ph>', '%1#'),
        ("A4: MemoQ ph with val (desc)", '<ph>&lt;mq:rxt-req displaytext="desc" val="&amp;desc;" /&gt;</ph>', '&amp;desc;'),
        ("A5: MemoQ fmt ph (removed)", '<ph type="fmt">   </ph>', ''),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    # GROUP B: Escaped quotes (&quot;)
    print("\n  --- GROUP B: &quot; escaped quotes ---")
    test_cases = [
        ("B1: &quot; escaped val (Name)", '<ph>&lt;mq:rxt-req displaytext=&quot;Name&quot; val=&quot;{Name}&quot; /&gt;</ph>', '{Name}'),
        ("B2: &quot; escaped val (br)", '<ph>&lt;mq:rxt displaytext=&quot;br&quot; val=&quot;&lt;br/&gt;&quot; /&gt;</ph>', '&lt;br/&gt;'),
        ("B3: &quot; escaped val (param)", '<ph>&lt;mq:rxt-req displaytext=&quot;Param1&quot; val=&quot;%1#&quot; /&gt;</ph>', '%1#'),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    # GROUP C: <ph> WITHOUT val= (the critical fix)
    print("\n  --- GROUP C: <ph> WITHOUT val= (critical!) ---")
    test_cases = [
        ("C1: Plain {Name} in ph", '<ph>{Name}</ph>', '{Name}'),
        ("C2: Plain %1# in ph", '<ph>%1#</ph>', '%1#'),
        ("C3: Plain &lt;br/&gt; in ph", '<ph>&lt;br/&gt;</ph>', '&lt;br/&gt;'),
        ("C4: Plain {1} in ph", '<ph>{1}</ph>', '{1}'),
        ("C5: Plain text in ph", '<ph>some placeholder</ph>', 'some placeholder'),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    # GROUP D: Real MemoQ complex cases
    print("\n  --- GROUP D: Complex MemoQ patterns ---")
    test_cases = [
        ("D1: mq:tag id only (no val) → displaytext", '<ph>&lt;mq:tag id="1" /&gt;</ph>', ''),
        ("D2: mq:rxt with ONLY displaytext", '<ph>&lt;mq:rxt displaytext="SomeTag" /&gt;</ph>', 'SomeTag'),
        ("D3: Self-closing ph with x attribute", '<ph x="1"/>', ''),
        ("D4: ph with xlf:g formatting", '<ph type="xlf:g" x="1">&lt;b&gt;</ph>', ''),
        ("D5: bpt/ept bold pair → keep inner", '<bpt i="1">&lt;b&gt;</bpt>bold text<ept i="1">&lt;/b&gt;</ept>', 'bold text'),
        ("D6: Mixed text + ph + text", 'Hello <ph>&lt;mq:rxt-req displaytext="Name" val="{Name}" /&gt;</ph> World', 'Hello {Name} World'),
        ("D7: Multiple ph tags", '<ph>&lt;mq:rxt-req displaytext="A" val="{A}" /&gt;</ph> and <ph>&lt;mq:rxt-req displaytext="B" val="{B}" /&gt;</ph>', '{A} and {B}'),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    # GROUP E: Export-specific formats
    print("\n  --- GROUP E: Export-specific formats ---")
    test_cases = [
        ("E1: val with no space before />", '<ph>&lt;mq:rxt-req displaytext=&quot;ItemName&quot; val=&quot;{ItemName}&quot;/&gt;</ph>', '{ItemName}'),
        ("E2: val no space before /> (unescaped)", '<ph>&lt;mq:rxt-req displaytext="ItemName" val="{ItemName}"/&gt;</ph>', '{ItemName}'),
        ("E3: Extra whitespace", '<ph>&lt;mq:rxt-req  displaytext="Name"  val="{Name}"  /&gt;</ph>', '{Name}'),
        ("E4: Just a number in ph", '<ph>1</ph>', '1'),
        ("E5: Word formatting (cf tag)", '<ph>&lt;cf size=&quot;12&quot; complexscript-size=&quot;12&quot;&gt;</ph>', ''),
        ("E6: Double-encoded &amp;amp;desc;", '<ph>&lt;mq:rxt-req displaytext="desc" val="&amp;amp;desc;" /&gt;</ph>', '&amp;amp;desc;'),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    # GROUP F: Edge cases
    print("\n  --- GROUP F: Edge cases ---")
    test_cases = [
        ("F1: Empty ph", '<ph></ph>', ''),
        ("F2: Whitespace-only ph", '<ph>   </ph>', ''),
        ("F3: Nested angle brackets (formatting)", '<ph>&lt;cf bold=&quot;on&quot;&gt;</ph>', ''),
        ("F4: Zero-width chars", 'Hello\u200BWorld', 'HelloWorld'),
        ("F5: Literal newline", 'Line1\nLine2', 'Line1&lt;br/&gt;Line2'),
        ("F6: Closing tag formatting", '<ph>&lt;/cf&gt;</ph>', ''),
        ("F7: Bold tag formatting", '<ph>&lt;b&gt;</ph>', ''),
    ]
    for name, inp, exp in test_cases:
        if run_test(name, inp, exp, clean_func): tests_passed += 1
        else: tests_failed += 1

    total = tests_passed + tests_failed
    print(f"\n  RESULTS: {tests_passed}/{total} passed, {tests_failed}/{total} failed")
    return tests_passed, tests_failed


def main():
    # Run ORIGINAL logic
    p1, f1 = run_all_tests("ORIGINAL logic (BEFORE fix)", _clean_segment_ORIGINAL)

    # Run NEW logic
    p2, f2 = run_all_tests("NEW logic (AFTER fix)", _clean_segment_NEW)

    # Summary
    print(f"\n{'=' * 80}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'=' * 80}")
    print(f"  ORIGINAL: {p1}/{p1+f1} passed ({f1} failures)")
    print(f"  NEW:      {p2}/{p2+f2} passed ({f2} failures)")
    improvement = p2 - p1
    if improvement > 0:
        print(f"  IMPROVEMENT: +{improvement} tests now passing!")
    elif improvement < 0:
        print(f"  REGRESSION: {-improvement} tests now failing!")
    else:
        print(f"  NO CHANGE")
    print(f"{'=' * 80}")

    return 0 if f2 == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
