"""Fixture data generators for API tests.

Provides factory functions that return dicts / strings matching the
expected request body shapes for each API subsystem.
"""
from __future__ import annotations

from typing import Any, Optional


# ------------------------------------------------------------------
# Project
# ------------------------------------------------------------------


def sample_project_data(
    name: str = "Test Project",
    description: Optional[str] = "Automated test project",
    platform_id: Optional[int] = None,
) -> dict[str, Any]:
    """Return a dict suitable for ``POST /api/ldm/projects``."""
    data: dict[str, Any] = {"name": name}
    if description is not None:
        data["description"] = description
    if platform_id is not None:
        data["platform_id"] = platform_id
    return data


# ------------------------------------------------------------------
# File
# ------------------------------------------------------------------


def sample_locstr_xml(num_rows: int = 5) -> str:
    """Return a minimal LocStr XML string with *num_rows* entries."""
    rows = "\n".join(
        f'  <String StrKey="KEY_{i:03d}" KR="한국어 텍스트 {i}" EN="English text {i}" />'
        for i in range(1, num_rows + 1)
    )
    return f'<?xml version="1.0" encoding="utf-8"?>\n<LanguageData>\n{rows}\n</LanguageData>\n'


def sample_locstr_xml_with_brtags() -> str:
    """Return a LocStr XML string with br-tags (multiline text)."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<LanguageData>\n"
        '  <String StrKey="BR_001" KR="첫 줄<br/>둘째 줄" EN="Line 1<br/>Line 2" />\n'
        '  <String StrKey="BR_002" KR="A<br/>B<br/>C" EN="A<br/>B<br/>C" />\n'
        "</LanguageData>\n"
    )


def sample_file_data(
    filename: str = "test_file.xml",
    content: Optional[bytes] = None,
    content_type: str = "text/xml",
) -> dict[str, Any]:
    """Return dict with file upload parameters."""
    if content is None:
        content = sample_locstr_xml().encode()
    return {
        "filename": filename,
        "content": content,
        "content_type": content_type,
    }


# ------------------------------------------------------------------
# TM
# ------------------------------------------------------------------


def sample_tm_data(
    name: str = "Test TM",
    source_lang: str = "ko",
    target_lang: str = "en",
    num_entries: int = 5,
) -> dict[str, Any]:
    """Return dict with TM upload parameters.

    The ``content`` key holds a tab-separated byte string.
    """
    lines = ["Source\tTarget"]
    for i in range(num_entries):
        lines.append(f"한국어 소스 {i}\tEnglish target {i}")
    content = "\n".join(lines).encode()
    return {
        "name": name,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "content": content,
        "filename": "test_tm.txt",
    }


def sample_tm_entry(
    source_text: str = "테스트 소스",
    target_text: str = "Test target",
    string_id: Optional[str] = None,
) -> dict[str, Any]:
    """Return a dict suitable for ``POST /api/ldm/tm/{tm_id}/entries``."""
    entry: dict[str, Any] = {
        "source_text": source_text,
        "target_text": target_text,
    }
    if string_id is not None:
        entry["string_id"] = string_id
    return entry


# ------------------------------------------------------------------
# Row
# ------------------------------------------------------------------


def sample_row_update(
    target: str = "Updated translation",
    status: Optional[str] = None,
) -> dict[str, Any]:
    """Return a dict suitable for ``PUT /api/ldm/rows/{row_id}``."""
    data: dict[str, Any] = {"target": target}
    if status is not None:
        data["status"] = status
    return data


# ------------------------------------------------------------------
# Korean / br-tag text samples
# ------------------------------------------------------------------


def sample_korean_text() -> str:
    """Return Korean text with br-tags for round-trip testing."""
    return "첫 번째 줄<br/>두 번째 줄<br/>세 번째 줄"


def sample_brtag_text() -> str:
    """Return text with various br-tag scenarios."""
    return "Line A<br/>Line B<br/>Line C"


def sample_korean_sentences() -> list[str]:
    """Return a list of Korean sentences for batch testing."""
    return [
        "안녕하세요",
        "감사합니다",
        "검은 칼날의 전사",
        "마법<br/>스킬",
        "지역 이름: 봄의 숲",
    ]


# ------------------------------------------------------------------
# GameData
# ------------------------------------------------------------------


def sample_gamedata_browse_request(path: str = "", max_depth: int = 1) -> dict[str, Any]:
    """Return a dict for ``POST /api/ldm/gamedata/browse``."""
    return {"path": path, "max_depth": max_depth}


def sample_gamedata_save_request(
    xml_path: str = "iteminfo/iteminfo_weapon.staticinfo.xml",
    entity_index: int = 0,
    attr_name: str = "Str",
    new_value: str = "Updated value",
) -> dict[str, Any]:
    """Return a dict for ``PUT /api/ldm/gamedata/save``."""
    return {
        "xml_path": xml_path,
        "entity_index": entity_index,
        "attr_name": attr_name,
        "new_value": new_value,
    }


# ------------------------------------------------------------------
# QA
# ------------------------------------------------------------------


def sample_qa_check_request(
    checks: Optional[list[str]] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return a dict for ``POST /api/ldm/rows/{id}/check-qa``."""
    return {
        "checks": checks or ["line", "pattern", "term"],
        "force": force,
    }


# ------------------------------------------------------------------
# Platform
# ------------------------------------------------------------------


def sample_platform_data(
    name: str = "Test Platform",
    description: Optional[str] = "Automated test platform",
) -> dict[str, Any]:
    """Return a dict suitable for ``POST /api/ldm/platforms``."""
    data: dict[str, Any] = {"name": name}
    if description is not None:
        data["description"] = description
    return data
