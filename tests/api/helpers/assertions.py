"""Reusable assertion helpers for API response validation.

Every function raises ``AssertionError`` with a descriptive message
so that test failures are immediately understandable.
"""
from __future__ import annotations

import re
from typing import Any


# ------------------------------------------------------------------
# Status code assertions
# ------------------------------------------------------------------


def assert_status(response: Any, expected: int, msg: str = "") -> None:
    """Assert HTTP response status code matches *expected*.

    ``response`` is any object with a ``.status_code`` attribute
    (``httpx.Response``, FastAPI ``TestClient`` response, etc.).
    """
    actual = response.status_code
    detail = ""
    try:
        detail = response.text[:300]
    except Exception:
        pass
    prefix = f"{msg} — " if msg else ""
    assert actual == expected, (
        f"{prefix}Expected status {expected}, got {actual}. "
        f"Body: {detail}"
    )


def assert_status_ok(response: Any, msg: str = "") -> None:
    """Assert response has a 2xx status code."""
    actual = response.status_code
    detail = ""
    try:
        detail = response.text[:300]
    except Exception:
        pass
    prefix = f"{msg} — " if msg else ""
    assert 200 <= actual < 300, (
        f"{prefix}Expected 2xx, got {actual}. Body: {detail}"
    )


def assert_error_response(response: Any, expected_status: int, msg: str = "") -> None:
    """Assert response has the expected error status AND contains a ``detail`` field."""
    assert_status(response, expected_status, msg)
    data = response.json()
    assert "detail" in data, f"Error response missing 'detail' field. Body: {data}"


# ------------------------------------------------------------------
# JSON field assertions
# ------------------------------------------------------------------


def assert_json_fields(data: dict, required_fields: list[str], msg: str = "") -> None:
    """Assert that *data* contains all *required_fields*."""
    missing = [f for f in required_fields if f not in data]
    prefix = f"{msg} — " if msg else ""
    assert not missing, (
        f"{prefix}Missing required fields: {missing}. "
        f"Present keys: {sorted(data.keys())}"
    )


def assert_list_response(data: Any, min_count: int = 0) -> None:
    """Assert *data* is a list with at least *min_count* items."""
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    assert len(data) >= min_count, (
        f"Expected >= {min_count} items, got {len(data)}"
    )


def assert_pagination(data: dict) -> None:
    """Assert *data* has standard pagination fields (rows, total, page, limit, total_pages)."""
    required = ["rows", "total", "page", "limit", "total_pages"]
    assert_json_fields(data, required, "Pagination")
    assert isinstance(data["rows"], list), f"Expected 'rows' to be list, got {type(data['rows']).__name__}"
    assert isinstance(data["total"], int), "Expected 'total' to be int"
    assert isinstance(data["page"], int), "Expected 'page' to be int"
    assert isinstance(data["total_pages"], int), "Expected 'total_pages' to be int"


# ------------------------------------------------------------------
# Entity-specific assertions
# ------------------------------------------------------------------


def assert_project_response(data: dict) -> None:
    """Assert *data* matches ProjectResponse schema."""
    assert_json_fields(data, ["id", "name", "owner_id"], "ProjectResponse")
    assert isinstance(data["id"], int), f"project.id should be int, got {type(data['id']).__name__}"


def assert_file_response(data: dict) -> None:
    """Assert *data* matches FileResponse schema."""
    assert_json_fields(
        data,
        ["id", "name", "original_filename", "format", "row_count"],
        "FileResponse",
    )
    assert isinstance(data["id"], int), f"file.id should be int, got {type(data['id']).__name__}"


def assert_row_response(data: dict) -> None:
    """Assert *data* matches RowResponse schema."""
    assert_json_fields(
        data,
        ["id", "file_id", "row_num", "status"],
        "RowResponse",
    )


def assert_tm_response(data: dict) -> None:
    """Assert *data* matches TMResponse schema."""
    assert_json_fields(
        data,
        ["id", "name", "source_lang", "target_lang", "entry_count", "status"],
        "TMResponse",
    )


def assert_codex_entity(data: dict) -> None:
    """Assert *data* matches CodexEntity schema."""
    assert_json_fields(
        data,
        ["entity_type", "strkey", "name", "source_file"],
        "CodexEntity",
    )


def assert_qa_issue(data: dict) -> None:
    """Assert *data* matches QAIssue schema."""
    assert_json_fields(
        data,
        ["id", "check_type", "severity", "message"],
        "QAIssue",
    )


def assert_worldmap_data(data: dict) -> None:
    """Assert *data* matches WorldMapData schema."""
    assert_json_fields(data, ["nodes", "routes", "bounds"], "WorldMapData")
    assert isinstance(data["nodes"], list), "nodes should be a list"
    assert isinstance(data["routes"], list), "routes should be a list"


# ------------------------------------------------------------------
# Content integrity assertions
# ------------------------------------------------------------------


def assert_brtag_preserved(original: str, result: str) -> None:
    """Assert that ``<br/>`` tags in *original* are present in *result*.

    Counts occurrences to ensure none are dropped or duplicated.
    """
    orig_count = original.count("<br/>")
    result_count = result.count("<br/>")
    assert orig_count == result_count, (
        f"br-tag count mismatch: original has {orig_count}, result has {result_count}. "
        f"Original: {original!r}, Result: {result!r}"
    )


def assert_korean_preserved(original: str, result: str) -> None:
    """Assert Korean characters in *original* are present in *result*.

    Uses the full Korean regex: syllables + Jamo + Compat Jamo.
    """
    korean_re = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
    orig_korean = set(korean_re.findall(original))
    result_korean = set(korean_re.findall(result))
    missing = orig_korean - result_korean
    assert not missing, (
        f"Korean characters lost in round-trip: {missing}. "
        f"Original Korean chars: {len(orig_korean)}, Result: {len(result_korean)}"
    )


def assert_no_html_entities(text: str) -> None:
    """Assert *text* does not contain HTML entities like ``&#10;`` or ``&lt;``.

    br-tags should be literal ``<br/>``, not ``&lt;br/&gt;``.
    """
    entity_re = re.compile(r"&(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]+);")
    matches = entity_re.findall(text)
    # Allow &amp; &lt; &gt; only if they're NOT encoding br-tags
    if matches:
        # Filter out false positives that are NOT br-tag mangling
        brtag_entities = [m for m in matches if m in ("&lt;", "&gt;")]
        if brtag_entities:
            assert False, (
                f"Found HTML entities that may be mangled br-tags: {brtag_entities}. "
                f"Text: {text!r}"
            )
