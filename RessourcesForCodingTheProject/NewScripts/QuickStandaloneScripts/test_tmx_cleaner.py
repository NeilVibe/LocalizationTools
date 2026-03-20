#!/usr/bin/env python3
"""
Test suite for tmx_cleaner.py — standalone TMX regex cleaning.
Tests against both synthetic patterns and real data from TM NO WORK.xlsx.
"""
from __future__ import annotations

import sys
import re
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tmx_cleaner import clean_segment


def run_test(name, inp, expected):
    result = clean_segment(inp)
    ok = result == expected
    status = 'PASS' if ok else 'FAIL'
    print(f'  [{status}] {name}')
    if not ok:
        print(f'    INPUT:    {inp[:150]}')
        print(f'    EXPECTED: {expected[:150]}')
        print(f'    GOT:      {result[:150]}')
        print()
    # Check no leftover markup tags
    leftovers = re.findall(r'<(?:bpt|ept|ph|it|g)\b[^>]*>', result)
    if leftovers and ok:
        print(f'    *** WARNING: leftover tags in output: {leftovers}')
    return ok


def main():
    passed = 0
    failed = 0

    def check(name, inp, expected):
        nonlocal passed, failed
        if run_test(name, inp, expected):
            passed += 1
        else:
            failed += 1

    # =================================================================
    # GROUP A: MemoQ bpt/ept StaticInfo (real data patterns from Excel)
    # =================================================================
    print('\n--- A: MemoQ bpt/ept StaticInfo (real Excel data) ---')

    # Plain quotes (Excel/MemoQ export format)
    check('A1: Knowledge (plain quotes)',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Knowledge_Node_Kwe_DreamTree" val="{StaticInfo:Knowledge:Knowledge_Node_Kwe_DreamTree#"&gt;</bpt>꿈의 나무<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>',
          '{StaticInfo:Knowledge:Knowledge_Node_Kwe_DreamTree#꿈의 나무}')

    check('A2: Item (plain quotes)',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Miner_PlateArmor_Helm" val="{StaticInfo:Item:Miner_PlateArmor_Helm#"&gt;</bpt>광부의 랜턴 모자<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>',
          '{StaticInfo:Item:Miner_PlateArmor_Helm#광부의 랜턴 모자}')

    check('A3: Character (plain quotes)',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Riding_WarMachine_Unique_1" val="{StaticInfo:Character:Riding_WarMachine_Unique_1#"&gt;</bpt>A.T.A.G.<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>',
          '{StaticInfo:Character:Riding_WarMachine_Unique_1#A.T.A.G.}')

    check('A4: lowercase Staticinfo (plain quotes)',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Knowledge_BlackWolf" val="{Staticinfo:Knowledge:Knowledge_BlackWolf#"&gt;</bpt>섭리의 힘<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>',
          '{StaticInfo:Knowledge:Knowledge_BlackWolf#섭리의 힘}')

    # &quot; escaped quotes (TMX file format)
    check('A5: Knowledge (&quot; escaped)',
          '<bpt i="1">&lt;mq:rxt-req displaytext=&quot;{Knowledge_Node_Kwe_DreamTree&quot; val=&quot;{StaticInfo:Knowledge:Knowledge_Node_Kwe_DreamTree#&quot;&gt;</bpt>꿈의 나무<ept i="1">&lt;/mq:rxt-req displaytext=&quot;}&quot; val=&quot;}&quot;&gt;</ept>',
          '{StaticInfo:Knowledge:Knowledge_Node_Kwe_DreamTree#꿈의 나무}')

    # mq:rxt (without -req)
    check('A6: Knowledge mq:rxt (no -req)',
          '<bpt i="1">&lt;mq:rxt displaytext=&quot;{SomeID&quot; val=&quot;{StaticInfo:Knowledge:SomeID#&quot;&gt;</bpt>text<ept i="1">&lt;/mq:rxt displaytext=&quot;}&quot; val=&quot;}&quot;&gt;</ept>',
          '{StaticInfo:Knowledge:SomeID#text}')

    # =================================================================
    # GROUP B: bpt/ept mid-sentence (text before/after)
    # =================================================================
    print('\n--- B: bpt/ept mid-sentence ---')

    check('B1: trailing Korean text',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Knowledge_BlackWolf" val="{Staticinfo:Knowledge:Knowledge_BlackWolf#"&gt;</bpt>섭리의 힘<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>을 이용해 차원 간의 이동이 가능해진다.',
          '{StaticInfo:Knowledge:Knowledge_BlackWolf#섭리의 힘}을 이용해 차원 간의 이동이 가능해진다.')

    check('B2: leading + trailing text',
          'Skill: <bpt i="1">&lt;mq:rxt-req displaytext="{Knowledge_Light_Reflection" val="{StaticInfo:Knowledge:Knowledge_Light_Reflection#"&gt;</bpt>Blinding Flash<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>!',
          'Skill: {StaticInfo:Knowledge:Knowledge_Light_Reflection#Blinding Flash}!')

    check('B3: English mid-sentence',
          'Move across dimensions by using the <bpt i="1">&lt;mq:rxt-req displaytext="{Knowledge_BlackWolf" val="{Staticinfo:Knowledge:Knowledge_BlackWolf#"&gt;</bpt>Axiom Force<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>.',
          'Move across dimensions by using the {StaticInfo:Knowledge:Knowledge_BlackWolf#Axiom Force}.')

    check('B4: trailing space + text',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{Riding_WarMachine_Unique_1" val="{StaticInfo:Character:Riding_WarMachine_Unique_1#"&gt;</bpt>A.T.A.G.<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept> 지급',
          '{StaticInfo:Character:Riding_WarMachine_Unique_1#A.T.A.G.} 지급')

    # =================================================================
    # GROUP C: MemoQ <ph> with val= (from tmxconvert41 tests)
    # =================================================================
    print('\n--- C: MemoQ <ph> with val= ---')

    check('C1: ph val Name', '<ph>&lt;mq:rxt-req displaytext="Name" val="{Name}" /&gt;</ph>', '{Name}')
    check('C2: ph val br', '<ph>&lt;mq:rxt displaytext="br" val="&lt;br/&gt;" /&gt;</ph>', '&lt;br/&gt;')
    check('C3: ph val param', '<ph>&lt;mq:rxt-req displaytext="Param1" val="%1#" /&gt;</ph>', '%1#')
    check('C4: ph val desc', '<ph>&lt;mq:rxt-req displaytext="desc" val="&amp;desc;" /&gt;</ph>', '&amp;desc;')
    check('C5: ph fmt (removed)', '<ph type="fmt">   </ph>', '')

    # =================================================================
    # GROUP D: <ph> WITHOUT val= (the critical fix)
    # =================================================================
    print('\n--- D: <ph> without val= ---')

    check('D1: Plain {Name}', '<ph>{Name}</ph>', '{Name}')
    check('D2: Plain %1#', '<ph>%1#</ph>', '%1#')
    check('D3: Plain &lt;br/&gt;', '<ph>&lt;br/&gt;</ph>', '&lt;br/&gt;')
    check('D4: Plain {1}', '<ph>{1}</ph>', '{1}')
    check('D5: Plain text', '<ph>some placeholder</ph>', 'some placeholder')
    check('D6: Just a number', '<ph>1</ph>', '1')

    # =================================================================
    # GROUP E: Generic bpt/ept (Trados bold/italic/etc.)
    # =================================================================
    print('\n--- E: Generic bpt/ept ---')

    check('E1: Trados bold', '<bpt i="1">&lt;b&gt;</bpt>bold text<ept i="1">&lt;/b&gt;</ept>', 'bold text')
    check('E2: Empty bpt/ept pair', '<bpt i="1">&lt;b&gt;</bpt><ept i="1">&lt;/b&gt;</ept>', '')

    # =================================================================
    # GROUP F: Other tag types
    # =================================================================
    print('\n--- F: Other tags ---')

    check('F1: Self-closing ph', '<ph x="1"/>', '')
    check('F2: it tag', '<it pos="begin">&lt;b&gt;</it>', '')
    check('F3: x tag', '<x id="1"/>', '')
    check('F4: g tag (keep inner)', '<g id="1">inner text</g>', 'inner text')

    # =================================================================
    # GROUP G: Formatting and normalization
    # =================================================================
    print('\n--- G: Formatting and normalization ---')

    check('G1: Zero-width chars', 'Hello\u200BWorld', 'HelloWorld')
    check('G2: Literal newline', 'Line1\nLine2', 'Line1&lt;br/&gt;Line2')
    check('G3: Formatting cf tag', '<ph>&lt;cf bold=&quot;on&quot;&gt;</ph>', '')
    check('G4: Closing cf tag', '<ph>&lt;/cf&gt;</ph>', '')
    check('G5: Bold tag', '<ph>&lt;b&gt;</ph>', '')
    check('G6: displaytext only', '<ph>&lt;mq:rxt displaytext="SomeTag" /&gt;</ph>', 'SomeTag')
    check('G7: Structural mq:tag', '<ph>&lt;mq:tag id="1" /&gt;</ph>', '')

    # =================================================================
    # GROUP H: Mixed content (multiple patterns in one segment)
    # =================================================================
    print('\n--- H: Mixed content ---')

    check('H1: text + ph + text',
          'Hello <ph>&lt;mq:rxt-req displaytext="Name" val="{Name}" /&gt;</ph> World',
          'Hello {Name} World')

    check('H2: multiple ph tags',
          '<ph>&lt;mq:rxt-req displaytext="A" val="{A}" /&gt;</ph> and <ph>&lt;mq:rxt-req displaytext="B" val="{B}" /&gt;</ph>',
          '{A} and {B}')

    check('H3: bpt/ept + br + bpt/ept',
          '<bpt i="1">&lt;mq:rxt-req displaytext="{ID1" val="{StaticInfo:Knowledge:ID1#"&gt;</bpt>Text1<ept i="1">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>&lt;br/&gt;<bpt i="2">&lt;mq:rxt-req displaytext="{ID2" val="{StaticInfo:Knowledge:ID2#"&gt;</bpt>Text2<ept i="2">&lt;/mq:rxt-req displaytext="}" val="}"&gt;</ept>',
          '{StaticInfo:Knowledge:ID1#Text1}&lt;br/&gt;{StaticInfo:Knowledge:ID2#Text2}')

    # =================================================================
    # SUMMARY
    # =================================================================
    total = passed + failed
    print(f'\n{"=" * 60}')
    print(f'RESULTS: {passed}/{total} passed, {failed}/{total} failed')
    print(f'{"=" * 60}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
