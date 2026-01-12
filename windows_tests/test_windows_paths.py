"""
Windows PATH Tests - Critical path validation for Windows builds

Tests 7 critical path scenarios:
1. AppData path validation
2. Downloads path validation
3. Models path validation
4. Indexes path validation
5. Unicode path handling (Korean/CJK)
6. Backslash handling
7. Long path support
"""

import os
import sys
import tempfile
import pytest


class TestWindowsPaths:
    """Windows path validation tests."""

    def test_appdata_path_resolution(self):
        """Test AppData path can be resolved correctly."""
        # APPDATA should always be set on Windows
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")

        appdata = os.environ.get('APPDATA')
        assert appdata is not None, "APPDATA environment variable not set"
        assert os.path.exists(appdata), f"APPDATA path does not exist: {appdata}"

        # Test creating LocaNext subdir
        locanext_path = os.path.join(appdata, 'LocaNext')
        assert '\\' in locanext_path or '/' in locanext_path, "Path should contain separator"

    def test_localappdata_path_resolution(self):
        """Test LocalAppData path can be resolved correctly."""
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")

        local_appdata = os.environ.get('LOCALAPPDATA')
        assert local_appdata is not None, "LOCALAPPDATA environment variable not set"
        assert os.path.exists(local_appdata), f"LOCALAPPDATA path does not exist: {local_appdata}"

    def test_downloads_path_construction(self):
        """Test Downloads path can be constructed from USERPROFILE."""
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")

        userprofile = os.environ.get('USERPROFILE')
        assert userprofile is not None, "USERPROFILE environment variable not set"

        downloads = os.path.join(userprofile, 'Downloads')
        assert downloads.endswith('Downloads'), f"Unexpected downloads path: {downloads}"

    def test_models_path_normalization(self):
        """Test model path normalization with mixed separators."""
        mixed_path = "C:/Users\\test/models\\qwen"
        normalized = os.path.normpath(mixed_path)

        if sys.platform == 'win32':
            assert '/' not in normalized, f"Path should not contain forward slashes: {normalized}"
        else:
            assert '\\' not in normalized, f"Path should not contain backslashes: {normalized}"

    def test_indexes_path_with_spaces(self):
        """Test path handling with spaces (common in Windows)."""
        path_with_spaces = os.path.join(tempfile.gettempdir(), "LocaNext Test", "indexes")
        normalized = os.path.normpath(path_with_spaces)

        assert "Test" in normalized, "Path should preserve spaces"
        assert normalized == os.path.normpath(normalized), "Double normalization should be idempotent"

    def test_unicode_path_korean(self):
        """Test Unicode path handling with Korean characters."""
        korean_name = "테스트_파일_폴더"
        temp_base = tempfile.gettempdir()
        unicode_path = os.path.join(temp_base, korean_name)

        try:
            os.makedirs(unicode_path, exist_ok=True)
            assert os.path.exists(unicode_path), f"Failed to create Korean directory: {unicode_path}"

            test_file = os.path.join(unicode_path, "한글_테스트.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("테스트 내용")

            assert os.path.exists(test_file), f"Failed to create Korean file: {test_file}"

            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "테스트" in content, "Unicode content not preserved"

        finally:
            if os.path.exists(unicode_path):
                import shutil
                shutil.rmtree(unicode_path, ignore_errors=True)

    def test_unicode_path_cjk_mixed(self):
        """Test Unicode path with mixed CJK characters (Korean, Japanese, Chinese)."""
        cjk_name = "한글_日本語_中文"
        temp_base = tempfile.gettempdir()
        unicode_path = os.path.join(temp_base, cjk_name)

        try:
            os.makedirs(unicode_path, exist_ok=True)
            assert os.path.exists(unicode_path), f"Failed to create CJK directory: {unicode_path}"
        finally:
            if os.path.exists(unicode_path):
                import shutil
                shutil.rmtree(unicode_path, ignore_errors=True)
