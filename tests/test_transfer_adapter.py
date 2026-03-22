"""
Tests for transfer adapter and config shim.

Validates that QuickTranslate Sacred Script modules can be imported via
sys.path injection with a synthetic config shim, without copying any code.
"""
from __future__ import annotations

import glob
import sys
import types
from pathlib import Path
from xml.etree import ElementTree

import pytest

# Fixture paths
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "transfer"
TARGET_XML = FIXTURE_DIR / "target" / "languagedata_FRE.xml"
SOURCE_XML = FIXTURE_DIR / "source" / "corrections_FRE.xml"
EXPORT_XML = FIXTURE_DIR / "export" / "Dialog" / "sample.loc.xml"


class TestConfigShim:
    """Test config shim creation and injection."""

    def test_config_shim_creates_module(self, tmp_path):
        """create_config_shim returns a ModuleType with correct attributes."""
        from server.services.transfer_config_shim import create_config_shim

        loc = str(tmp_path / "loc")
        export = str(tmp_path / "export")
        shim = create_config_shim(loc, export)

        assert isinstance(shim, types.ModuleType)
        assert shim.LOC_FOLDER == Path(loc)
        assert shim.EXPORT_FOLDER == Path(export)
        assert shim.SCRIPT_CATEGORIES == {"Sequencer", "Dialog"}

    def test_inject_config_shim(self, tmp_path):
        """After inject_config_shim, sys.modules['config'] has LOC_FOLDER."""
        from server.services.transfer_config_shim import inject_config_shim

        loc = str(tmp_path / "loc")
        export = str(tmp_path / "export")

        # Save and restore original config module
        original = sys.modules.get("config")
        try:
            inject_config_shim(loc, export)
            assert hasattr(sys.modules["config"], "LOC_FOLDER")
            assert sys.modules["config"].LOC_FOLDER == Path(loc)
        finally:
            if original is not None:
                sys.modules["config"] = original
            else:
                sys.modules.pop("config", None)

    def test_reconfigure_paths(self, tmp_path):
        """After reconfigure_paths, sys.modules['config'].LOC_FOLDER updates."""
        from server.services.transfer_config_shim import (
            inject_config_shim,
            reconfigure_paths,
        )

        loc1 = str(tmp_path / "loc1")
        loc2 = str(tmp_path / "loc2")
        export = str(tmp_path / "export")

        original = sys.modules.get("config")
        try:
            inject_config_shim(loc1, export)
            reconfigure_paths(loc2, export)
            assert sys.modules["config"].LOC_FOLDER == Path(loc2)
        finally:
            if original is not None:
                sys.modules["config"] = original
            else:
                sys.modules.pop("config", None)


class TestTransferAdapter:
    """Test adapter import layer."""

    def test_init_quicktranslate(self):
        """init_quicktranslate returns dict with all expected function keys."""
        from server.services.transfer_adapter import init_quicktranslate

        original_config = sys.modules.get("config")
        original_path = list(sys.path)
        try:
            modules = init_quicktranslate(
                str(FIXTURE_DIR / "target"),
                str(FIXTURE_DIR / "export"),
            )
            expected_keys = {
                "transfer_folder_to_folder",
                "merge_corrections_to_xml",
                "merge_corrections_stringid_only",
                "run_all_postprocess",
                "scan_source_for_languages",
            }
            assert expected_keys.issubset(set(modules.keys()))
        finally:
            if original_config is not None:
                sys.modules["config"] = original_config
            else:
                sys.modules.pop("config", None)
            sys.path[:] = original_path

    def test_no_sacred_script_copied(self):
        """No file in server/services/ contains Sacred Script function defs."""
        services_dir = Path(__file__).parent.parent / "server" / "services"
        forbidden_patterns = [
            "def merge_corrections_to_xml",
            "def merge_corrections_stringid_only",
            "def run_all_postprocess",
            "def transfer_folder_to_folder",
        ]

        for py_file in services_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                assert pattern not in content, (
                    f"Sacred Script function definition '{pattern}' found in {py_file.name}"
                )


class TestFixtures:
    """Test that XML fixtures exist and are valid."""

    @pytest.mark.parametrize(
        "xml_path",
        [TARGET_XML, SOURCE_XML, EXPORT_XML],
        ids=["target", "source", "export"],
    )
    def test_fixtures_exist(self, xml_path):
        """All 3 fixture XML files exist and contain at least one LocStr element."""
        assert xml_path.exists(), f"Fixture missing: {xml_path}"
        tree = ElementTree.parse(str(xml_path))
        root = tree.getroot()
        locstr_elements = root.findall(".//LocStr")
        assert len(locstr_elements) >= 1, f"No LocStr elements in {xml_path.name}"
