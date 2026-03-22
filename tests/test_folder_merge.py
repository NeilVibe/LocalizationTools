"""
Integration tests for multi-language folder merge.

Tests scan_source_languages() and execute_multi_language_transfer() from
the transfer adapter -- Phase 57 Plan 03 (XFER-07).
"""
from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "transfer"
MULTI_SOURCE = FIXTURES / "multi_source"
MULTI_TARGET = FIXTURES / "multi_target"
EXPORT_DIR = FIXTURES / "export"


@pytest.fixture(autouse=True)
def _clear_qt_caches():
    """Clear QT module-level caches between tests to avoid stale state."""
    yield
    # Reset cached language codes after each test
    try:
        from core.source_scanner import clear_language_code_cache
        clear_language_code_cache()
    except ImportError:
        pass
    # Reset adapter module cache so reconfigure_paths runs fresh
    import server.services.transfer_adapter as _mod
    _mod._qt_modules = None


@pytest.fixture()
def multi_env(tmp_path: Path) -> dict:
    """Copy multi-language fixtures into tmp_path and return paths."""
    src = tmp_path / "source"
    tgt = tmp_path / "target"
    exp = tmp_path / "export"

    shutil.copytree(MULTI_SOURCE, src)
    shutil.copytree(MULTI_TARGET, tgt)
    # Export dir may or may not exist -- create empty for config shim
    if EXPORT_DIR.exists():
        shutil.copytree(EXPORT_DIR, exp)
    else:
        exp.mkdir()

    return {"source_dir": src, "target_dir": tgt, "export_dir": exp}


# ---------------------------------------------------------------------------
# Tests for scan_source_languages
# ---------------------------------------------------------------------------

def test_scan_source_languages(multi_env: dict) -> None:
    """scan_source_languages detects FRE and ENG from subfolder names."""
    from server.services.transfer_adapter import scan_source_languages

    result = scan_source_languages(
        str(multi_env["source_dir"]),
        target_path=str(multi_env["target_dir"]),
    )

    assert "FRE" in result["languages"]
    assert "ENG" in result["languages"]
    assert result["total_files"] >= 2
    assert isinstance(result["unrecognized"], list)


def test_scan_empty_folder(tmp_path: Path) -> None:
    """scan_source_languages on empty folder returns zero-count result."""
    from server.services.transfer_adapter import scan_source_languages

    empty = tmp_path / "empty"
    empty.mkdir()

    result = scan_source_languages(str(empty))

    assert result["languages"] == {}
    assert result["total_files"] == 0


# ---------------------------------------------------------------------------
# Tests for execute_multi_language_transfer
# ---------------------------------------------------------------------------

def test_multi_language_merge(multi_env: dict) -> None:
    """execute_multi_language_transfer merges FRE and ENG corrections."""
    from server.services.transfer_adapter import execute_multi_language_transfer

    result = execute_multi_language_transfer(
        source_path=str(multi_env["source_dir"]),
        target_path=str(multi_env["target_dir"]),
        export_path=str(multi_env["export_dir"]),
        match_mode="strict",
    )

    # Both target files should have been updated
    fre_tree = ET.parse(multi_env["target_dir"] / "languagedata_FRE.xml")
    eng_tree = ET.parse(multi_env["target_dir"] / "languagedata_ENG.xml")

    fre_strs = {e.get("StringID"): e.get("Str") for e in fre_tree.iter("LocStr")}
    eng_strs = {e.get("StringID"): e.get("Str") for e in eng_tree.iter("LocStr")}

    # FRE corrections: STR_HELLO -> "Salut", STR_GOODBYE -> "Au revoir"
    assert fre_strs["STR_HELLO"] == "Salut"
    assert fre_strs["STR_GOODBYE"] == "Au revoir"

    # ENG corrections: STR_HELLO -> "Hi there", STR_YES -> "Yeah"
    assert eng_strs["STR_HELLO"] == "Hi there"
    assert eng_strs["STR_YES"] == "Yeah"


def test_multi_language_per_language_results(multi_env: dict) -> None:
    """Result has per-language breakdown with matched counts."""
    from server.services.transfer_adapter import execute_multi_language_transfer

    result = execute_multi_language_transfer(
        source_path=str(multi_env["source_dir"]),
        target_path=str(multi_env["target_dir"]),
        export_path=str(multi_env["export_dir"]),
        match_mode="strict",
    )

    assert "per_language" in result
    assert "FRE" in result["per_language"]
    assert "ENG" in result["per_language"]
    assert result["per_language"]["FRE"]["matched"] > 0
    assert result["per_language"]["ENG"]["matched"] > 0


def test_multi_language_dry_run(multi_env: dict) -> None:
    """dry_run=True returns scan + match data but does not modify targets."""
    from server.services.transfer_adapter import execute_multi_language_transfer

    # Record original content
    fre_before = (multi_env["target_dir"] / "languagedata_FRE.xml").read_text()
    eng_before = (multi_env["target_dir"] / "languagedata_ENG.xml").read_text()

    result = execute_multi_language_transfer(
        source_path=str(multi_env["source_dir"]),
        target_path=str(multi_env["target_dir"]),
        export_path=str(multi_env["export_dir"]),
        match_mode="strict",
        dry_run=True,
    )

    # Scan data should be present
    assert "scan" in result
    assert result["scan"]["total_files"] >= 2

    # Files should NOT be modified
    fre_after = (multi_env["target_dir"] / "languagedata_FRE.xml").read_text()
    eng_after = (multi_env["target_dir"] / "languagedata_ENG.xml").read_text()
    assert fre_before == fre_after
    assert eng_before == eng_after
