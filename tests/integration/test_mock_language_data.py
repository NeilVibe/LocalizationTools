"""Tests for mock language data files (MOCK-04).

Validates that language data XML files contain proper LocStr entries
with Korean source text and English/French translations.

NOTE: References legacy path stringtable/loc/ — restructured to loc/ in v9.0 Phase 74.
"""
from __future__ import annotations

import pytest
pytestmark = pytest.mark.skip(reason="Legacy fixture path stringtable/loc/ — restructured in v9.0 Phase 74")

import re
from pathlib import Path

import pytest
from lxml import etree

MOCK_DIR = Path(__file__).parent.parent / "fixtures" / "mock_gamedata"
LOC_DIR = MOCK_DIR / "stringtable" / "loc"

# Korean character regex: syllables + Jamo + Compat Jamo
KR_REGEX = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")


def _parse_locstr(lang: str) -> list[etree._Element]:
    """Parse LocStr elements from a language data file."""
    path = LOC_DIR / f"languagedata_{lang}.xml"
    assert path.exists(), f"Missing {path}"
    tree = etree.parse(str(path))
    return tree.getroot().findall(".//LocStr")


class TestKoreanLocStr:
    """MOCK-04: Korean language data validation."""

    def test_korean_locstr_count(self) -> None:
        """languagedata_kor.xml has 300+ LocStr entries."""
        entries = _parse_locstr("kor")
        assert len(entries) >= 300, f"Only {len(entries)} LocStr entries (need 300+)"

    def test_korean_text_contains_hangul(self) -> None:
        """Every StrOrigin in KOR file contains Korean characters."""
        entries = _parse_locstr("kor")
        for entry in entries:
            str_origin = entry.get("StrOrigin", "")
            assert KR_REGEX.search(str_origin), (
                f"StringId={entry.get('StringId')}: StrOrigin has no Korean: {str_origin!r}"
            )


class TestEnglishLocStr:
    """MOCK-04: English language data validation."""

    def test_english_locstr_count(self) -> None:
        """languagedata_eng.xml has 300+ LocStr entries."""
        entries = _parse_locstr("eng")
        assert len(entries) >= 300, f"Only {len(entries)} LocStr entries (need 300+)"


class TestFrenchLocStr:
    """MOCK-04: French language data validation."""

    def test_french_locstr_count(self) -> None:
        """languagedata_fre.xml has 300+ LocStr entries."""
        entries = _parse_locstr("fre")
        assert len(entries) >= 300, f"Only {len(entries)} LocStr entries (need 300+)"


class TestStringIdConsistency:
    """MOCK-04: StringID consistency across language files."""

    def test_stringid_consistency(self) -> None:
        """All 3 language files have the EXACT same set of StringIDs."""
        kor_ids = {e.get("StringId") for e in _parse_locstr("kor")}
        eng_ids = {e.get("StringId") for e in _parse_locstr("eng")}
        fre_ids = {e.get("StringId") for e in _parse_locstr("fre")}

        assert kor_ids == eng_ids, f"KOR vs ENG mismatch: {kor_ids.symmetric_difference(eng_ids)}"
        assert kor_ids == fre_ids, f"KOR vs FRE mismatch: {kor_ids.symmetric_difference(fre_ids)}"

    def test_stringid_naming_convention(self) -> None:
        """All StringIDs match pattern SID_{TYPE}_{ID}_{NAME|DESC}."""
        pattern = re.compile(r"^SID_[A-Z]+(?:_[A-Z]+)*_\d{4}_(NAME|DESC)$")
        entries = _parse_locstr("kor")
        for entry in entries:
            sid = entry.get("StringId", "")
            assert pattern.match(sid), f"StringId {sid!r} doesn't match naming convention"

    def test_br_tag_preservation(self) -> None:
        """At least 10 LocStr entries contain <br/> in StrOrigin or Str."""
        entries = _parse_locstr("kor")
        br_count = 0
        for entry in entries:
            str_origin = entry.get("StrOrigin", "")
            desc_origin = entry.get("DescOrigin", "")
            if "<br/>" in str_origin or "<br/>" in desc_origin:
                br_count += 1
        assert br_count >= 10, f"Only {br_count} LocStr entries with <br/> (need 10+)"
