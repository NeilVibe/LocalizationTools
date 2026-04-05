"""Integration tests for merge internalization (Phase 61).

Verifies that the internalized merge package (server.services.merge) works
identically to the old sys.path adapter approach. Tests all 4 MARCH requirements.
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path


class TestMARCH01_NoSysPathInjection:
    """MARCH-01: No sys.path injection or importlib hacks."""

    def test_no_qt_in_sys_path(self):
        """QuickTranslate source tree must NOT be in sys.path after import."""
        from server.services.transfer_adapter import MATCH_MODES
        for p in sys.path:
            assert "QuickTranslate" not in p, f"QT still in sys.path: {p}"

    def test_no_importlib_in_adapter(self):
        """transfer_adapter.py must not use importlib as an import."""
        import inspect
        from server.services import transfer_adapter
        source = inspect.getsource(transfer_adapter)
        # Check that importlib is not used as an actual import statement
        for line in source.split("\n"):
            stripped = line.strip()
            # Skip comments and docstrings
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            # Check for actual import usage (not mentions in string literals)
            if "import importlib" in stripped or "importlib.util" in stripped:
                pytest.fail(f"importlib found in code: {stripped}")

    def test_no_sys_modules_config_injection(self):
        """sys.modules['config'] must not be a synthetic config shim."""
        from server.services.transfer_adapter import MATCH_MODES
        import types
        config_mod = sys.modules.get("config")
        if config_mod is not None:
            # If config exists, it should NOT be our old shim
            assert hasattr(config_mod, "__file__") or not isinstance(config_mod, types.ModuleType), \
                "sys.modules['config'] is still a synthetic shim"

    def test_merge_package_importable(self):
        """server.services.merge must be importable as a normal package."""
        from server.services.merge import transfer_folder_to_folder
        from server.services.merge import run_all_postprocess
        from server.services.merge import scan_source_for_languages
        assert callable(transfer_folder_to_folder)
        assert callable(run_all_postprocess)
        assert callable(scan_source_for_languages)


class TestMARCH02_MatchTypes:
    """MARCH-02: All 3 match types importable and callable."""

    def test_match_modes_constant(self):
        """MATCH_MODES must contain all 3 match types."""
        from server.services.transfer_adapter import MATCH_MODES
        assert "stringid_only" in MATCH_MODES
        assert "strict" in MATCH_MODES
        assert "strorigin_filename" in MATCH_MODES

    def test_merge_functions_exist(self):
        """All merge functions must be importable from the package."""
        from server.services.merge import (
            transfer_folder_to_folder,
            merge_corrections_to_xml,
            merge_corrections_stringid_only,
        )
        assert callable(transfer_folder_to_folder)
        assert callable(merge_corrections_to_xml)
        assert callable(merge_corrections_stringid_only)

    def test_lookup_builders_exist(self):
        """Lookup map builders must be importable."""
        from server.services.merge import (
            build_stringid_to_category,
            build_stringid_to_subfolder,
            build_stringid_to_filepath,
        )
        assert callable(build_stringid_to_category)
        assert callable(build_stringid_to_subfolder)
        assert callable(build_stringid_to_filepath)


class TestMARCH03_Postprocess:
    """MARCH-03: Postprocess 8-step pipeline importable."""

    def test_run_all_postprocess_importable(self):
        """run_all_postprocess must be importable from merge package."""
        from server.services.merge import run_all_postprocess
        assert callable(run_all_postprocess)

    def test_postprocess_no_core_import(self):
        """postprocess.py must not contain 'from core.' imports."""
        import inspect
        from server.services.merge import postprocess
        source = inspect.getsource(postprocess)
        assert "from core." not in source
        assert "import config" not in source

    def test_preprocess_excel_importable(self):
        """run_preprocess_excel must also be importable."""
        from server.services.merge import run_preprocess_excel
        assert callable(run_preprocess_excel)


class TestMARCH04_SSEImportChain:
    """MARCH-04: SSE endpoint import chain works."""

    def test_merge_api_imports(self):
        """server.api.merge must still import from transfer_adapter."""
        from server.api.merge import router
        assert router is not None

    def test_execute_transfer_callable(self):
        """execute_transfer must be callable from adapter."""
        from server.services.transfer_adapter import execute_transfer
        assert callable(execute_transfer)

    def test_execute_multi_language_transfer_callable(self):
        """execute_multi_language_transfer must be callable from adapter."""
        from server.services.transfer_adapter import execute_multi_language_transfer
        assert callable(execute_multi_language_transfer)

    def test_transfer_adapter_class(self):
        """TransferAdapter class must still be importable."""
        from server.services.transfer_adapter import TransferAdapter
        assert TransferAdapter is not None


class TestConfigModule:
    """Verify _config.py works correctly."""

    def test_configure_creates_config(self):
        from server.services.merge._config import configure, get_config
        cfg = configure("/tmp/test_loc", "/tmp/test_export")
        assert cfg.LOC_FOLDER == Path("/tmp/test_loc")
        assert cfg.EXPORT_FOLDER == Path("/tmp/test_export")
        assert cfg.SCRIPT_CATEGORIES == {"Sequencer", "Dialog"}
        assert cfg.FUZZY_THRESHOLD_DEFAULT == 0.85

    def test_reconfigure_updates_paths(self):
        from server.services.merge._config import configure, reconfigure, get_config
        configure("/tmp/a", "/tmp/b")
        reconfigure("/tmp/c", "/tmp/d")
        cfg = get_config()
        assert cfg.LOC_FOLDER == Path("/tmp/c")
        assert cfg.EXPORT_FOLDER == Path("/tmp/d")

    def test_get_config_raises_without_configure(self):
        from server.services.merge import _config
        _config._instance = None  # Reset
        with pytest.raises(RuntimeError):
            _config.get_config()
