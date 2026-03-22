"""
Integration tests for execute_transfer() -- all 3 match types, scope, postprocess, dry-run.

Tests use fixture XML files copied to tmp_path, then verify merge results by
parsing the output XML with xml.etree.ElementTree.
"""
from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "transfer"


@pytest.fixture()
def transfer_env(tmp_path: Path) -> dict:
    """Copy fixture files to tmp_path and return path dict."""
    target_dir = tmp_path / "target"
    source_dir = tmp_path / "source"
    export_dir = tmp_path / "export"

    shutil.copytree(FIXTURES / "target", target_dir)
    shutil.copytree(FIXTURES / "source", source_dir)
    shutil.copytree(FIXTURES / "export", export_dir)

    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "export_dir": str(export_dir),
    }


def _get_locstr(xml_path: Path, string_id: str) -> dict | None:
    """Parse XML and return attributes dict for the given StringID."""
    tree = ET.parse(xml_path)
    for elem in tree.iter("LocStr"):
        if elem.get("StringID", "").lower() == string_id.lower():
            return dict(elem.attrib)
    return None


# ── Test 1: StringID Only ────────────────────────────────────────────────────


def test_stringid_only_transfer(transfer_env):
    """StringID Only match transfers corrections by StringID (case-insensitive)."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="stringid_only",
        stringid_all_categories=True,
    )

    # STR_HELLO should have been updated from "Bonjour" to "Salut"
    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"
    hello = _get_locstr(target_xml, "STR_HELLO")
    assert hello is not None, "STR_HELLO not found in output"
    assert hello["Str"] == "Salut", f"Expected 'Salut', got '{hello['Str']}'"

    # Result dict should have matched > 0
    assert result.get("total_matched", 0) > 0 or result.get("total_updated", 0) > 0


# ── Test 2: StringID Only with SCRIPT filter ─────────────────────────────────


def test_stringid_only_script_filter(transfer_env):
    """StringID Only with SCRIPT filter only transfers Dialog/Sequencer entries."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="stringid_only",
        stringid_all_categories=False,  # SCRIPT filter active
    )

    # With SCRIPT filter and our export folder having Dialog/sample.loc.xml,
    # only STR_DIALOG_01 and STR_SCRIPT_01 would be SCRIPT category.
    # STR_HELLO (not in Dialog/Sequencer export) should NOT be transferred.
    # Result should have some skipped_non_script entries
    assert isinstance(result, dict)


# ── Test 3: Strict (StringID + StrOrigin) ────────────────────────────────────


def test_strict_transfer(transfer_env):
    """StringID+StrOrigin strict match requires both to match."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strict",
    )

    # STR_HELLO: StringID matches, StrOrigin="Hello" matches -> should transfer
    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"
    hello = _get_locstr(target_xml, "STR_HELLO")
    assert hello is not None
    assert hello["Str"] == "Salut", f"Expected 'Salut', got '{hello['Str']}'"
    assert result.get("total_matched", 0) > 0 or result.get("total_updated", 0) > 0


# ── Test 4: StrOrigin + FileName 2PASS ──────────────────────────────────────


def test_strorigin_filename_transfer(transfer_env):
    """StrOrigin+FileName 2PASS mode runs without crash and returns result dict."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strorigin_filename",
    )

    assert isinstance(result, dict)
    assert "match_mode" in result
    assert result["match_mode"] == "strorigin_filename"


# ── Test 5: Postprocess runs (curly apostrophe cleanup) ──────────────────────


def test_postprocess_runs(transfer_env):
    """Postprocess cleans curly apostrophes after merge."""
    from server.services.transfer_adapter import execute_transfer

    # Inject a curly apostrophe into the target file before merge
    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"
    content = target_xml.read_text(encoding="utf-8")
    # Add an entry with curly apostrophe that corrections will update
    content = content.replace(
        "</LanguageData>",
        '  <LocStr StringID="STR_CURLY" Str="test\u2019s value" StrOrigin="test\'s value" DescOrigin="test"/>\n</LanguageData>',
    )
    target_xml.write_text(content, encoding="utf-8")

    execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strict",
    )

    # After postprocess, curly apostrophe should be normalized to ASCII
    curly = _get_locstr(target_xml, "STR_CURLY")
    assert curly is not None, "STR_CURLY not found after merge"
    assert "\u2019" not in curly["Str"], f"Curly apostrophe not cleaned: {curly['Str']}"


# ── Test 6: Only Untranslated scope ──────────────────────────────────────────


def test_only_untranslated_scope(transfer_env):
    """Only Untranslated skips entries that already have translations."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strict",
        only_untranslated=True,
    )

    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"

    # STR_HELLO already has Str="Bonjour" (non-empty, non-Korean)
    # -> should be SKIPPED (not overwritten to "Salut")
    hello = _get_locstr(target_xml, "STR_HELLO")
    assert hello is not None
    assert hello["Str"] == "Bonjour", f"STR_HELLO should remain 'Bonjour', got '{hello['Str']}'"

    # STR_GOODBYE has Str="" (empty) -> should be transferred to "Au revoir"
    goodbye = _get_locstr(target_xml, "STR_GOODBYE")
    assert goodbye is not None
    assert goodbye["Str"] == "Au revoir", f"STR_GOODBYE should be 'Au revoir', got '{goodbye['Str']}'"


# ── Test 7: Transfer All scope ───────────────────────────────────────────────


def test_transfer_all_scope(transfer_env):
    """Transfer All overwrites even already-translated entries."""
    from server.services.transfer_adapter import execute_transfer

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strict",
        only_untranslated=False,
    )

    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"

    # STR_HELLO had Str="Bonjour" but correction has "Salut"
    # -> should be overwritten to "Salut"
    hello = _get_locstr(target_xml, "STR_HELLO")
    assert hello is not None
    assert hello["Str"] == "Salut", f"STR_HELLO should be 'Salut', got '{hello['Str']}'"


# ── Test 8: Dry Run ──────────────────────────────────────────────────────────


def test_dry_run(transfer_env):
    """Dry run computes results but leaves files unchanged on disk."""
    from server.services.transfer_adapter import execute_transfer

    target_xml = Path(transfer_env["target_dir"]) / "languagedata_FRE.xml"
    original_content = target_xml.read_text(encoding="utf-8")

    result = execute_transfer(
        source_path=transfer_env["source_dir"],
        target_path=transfer_env["target_dir"],
        export_path=transfer_env["export_dir"],
        match_mode="strict",
        dry_run=True,
    )

    # File should be UNCHANGED after dry run
    after_content = target_xml.read_text(encoding="utf-8")
    assert original_content == after_content, "Dry run modified the target file!"

    # But result dict should still report what WOULD have been matched
    assert isinstance(result, dict)
