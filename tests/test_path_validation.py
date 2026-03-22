"""
Tests for path validation endpoint (Phase 56, Plan 02, Task 1).

Tests the /api/settings/validate-path endpoint including:
- Valid paths with languagedata XML files
- Valid paths with languagedata TXT files (MOCK-04: test123 uses .txt)
- Nonexistent paths
- Non-directory paths
- Empty directories (no languagedata files)
- WSL path translation in DEV_MODE
- Round-trip stability
"""

from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch

# Import the module under test (will be created in GREEN phase)
from server.api.settings import (
    PathValidationRequest,
    PathValidationResponse,
    translate_wsl_path,
    validate_path_logic,
)


def test_validate_valid_xml_path(tmp_path: Path):
    """POST with path containing languagedata XML returns valid=True."""
    (tmp_path / "languagedata_fre.xml").write_text("<root/>")
    result = validate_path_logic(str(tmp_path))
    assert result.valid is True
    assert result.files_found == 1
    assert "languagedata_fre.xml" in result.file_types
    assert result.error is None


def test_validate_valid_txt_path(tmp_path: Path):
    """POST with path containing languagedata .txt returns valid=True (MOCK-04)."""
    (tmp_path / "languagedata_fr PC 0904 1847.txt").write_text("data")
    result = validate_path_logic(str(tmp_path))
    assert result.valid is True
    assert result.files_found == 1
    assert "languagedata_fr PC 0904 1847.txt" in result.file_types


def test_validate_nonexistent_path():
    """POST with nonexistent path returns valid=False."""
    result = validate_path_logic("/nonexistent/path/that/does/not/exist")
    assert result.valid is False
    assert result.error == "Path does not exist"


def test_validate_not_directory(tmp_path: Path):
    """POST with path to a regular file returns valid=False."""
    file_path = tmp_path / "somefile.txt"
    file_path.write_text("hello")
    result = validate_path_logic(str(file_path))
    assert result.valid is False
    assert result.error == "Path is not a directory"


def test_validate_no_langdata(tmp_path: Path):
    """POST with empty directory (no languagedata files) returns valid=False."""
    result = validate_path_logic(str(tmp_path))
    assert result.valid is False
    assert result.error == "No languagedata files found"
    assert result.hint is not None


@patch("server.api.settings.config")
def test_wsl_path_translation(mock_config):
    """When DEV_MODE=true, Windows paths are translated to WSL paths."""
    mock_config.DEV_MODE = True
    translated = translate_wsl_path("C:\\Users\\MYCOM\\test")
    assert translated == "/mnt/c/Users/MYCOM/test"

    # Non-Windows paths pass through unchanged
    translated2 = translate_wsl_path("/mnt/c/already/linux")
    assert translated2 == "/mnt/c/already/linux"


@patch("server.api.settings.config")
def test_wsl_path_translation_disabled(mock_config):
    """When DEV_MODE=false, Windows paths are NOT translated."""
    mock_config.DEV_MODE = False
    result = translate_wsl_path("C:\\Users\\MYCOM\\test")
    assert result == "C:\\Users\\MYCOM\\test"


def test_validate_path_roundtrip(tmp_path: Path):
    """Two consecutive calls return the same result (stability smoke test)."""
    (tmp_path / "languagedata_kor.xml").write_text("<data/>")
    (tmp_path / "languagedata_eng.xml").write_text("<data/>")
    r1 = validate_path_logic(str(tmp_path))
    r2 = validate_path_logic(str(tmp_path))
    assert r1.valid == r2.valid
    assert r1.files_found == r2.files_found
    assert sorted(r1.file_types) == sorted(r2.file_types)


def test_validate_multiple_file_types(tmp_path: Path):
    """Path with mixed .xml and .txt languagedata files finds all."""
    (tmp_path / "languagedata_fre.xml").write_text("<root/>")
    (tmp_path / "languagedata_fr PC 0904 1847.txt").write_text("data")
    (tmp_path / "other_file.xml").write_text("<other/>")  # should NOT match
    result = validate_path_logic(str(tmp_path))
    assert result.valid is True
    assert result.files_found == 2
    assert "other_file.xml" not in result.file_types
