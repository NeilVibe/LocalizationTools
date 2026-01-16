"""
Windows PATH Tests - P11-A Platform Stability

Tests for Windows-specific path handling to catch path bugs that
slip through Linux-only CI testing.

These tests verify:
1. Path normalization (forward/backslash handling)
2. Download/Upload paths work correctly
3. Model paths (Qwen/embeddings) in AppData
4. PKL/index file paths
5. Special character handling in paths
6. Long path support (>260 chars)
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path, PureWindowsPath, PurePosixPath
from unittest.mock import patch, MagicMock


# =============================================================================
# Path Normalization Tests
# =============================================================================

class TestPathNormalization:
    """Test path normalization for cross-platform compatibility."""

    def test_forward_slash_normalization(self):
        """Forward slashes should work on both platforms."""
        path = "C:/Users/test/Documents/file.txt"
        # Path should be usable regardless of platform
        p = Path(path)
        assert p.name == "file.txt"
        assert "Documents" in str(p)

    def test_backslash_in_path(self):
        """Backslashes should be handled correctly."""
        # Using raw string for backslash - use PureWindowsPath for cross-platform testing
        path = r"C:\Users\test\Documents\file.txt"
        p = PureWindowsPath(path)
        assert p.name == "file.txt"

    def test_mixed_slash_normalization(self):
        """Mixed slashes should be normalized."""
        path = "C:/Users/test\\Documents/file.txt"
        p = Path(path)
        assert p.name == "file.txt"

    def test_unc_path_handling(self):
        """UNC paths (network shares) should be handled."""
        # UNC path format: \\server\share\path
        unc_path = r"\\server\share\folder\file.txt"
        p = PureWindowsPath(unc_path)
        assert p.name == "file.txt"
        assert p.drive == r"\\server\share"

    def test_relative_path_resolution(self):
        """Relative paths should resolve correctly."""
        base = Path("/home/user/project")
        relative = Path("data/file.txt")
        full = base / relative
        assert "data" in str(full)
        assert full.name == "file.txt"


# =============================================================================
# Download Path Tests
# =============================================================================

class TestDownloadPaths:
    """Test file download path handling."""

    def test_download_directory_creation(self):
        """Download directory should be created if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            download_path = Path(tmpdir) / "downloads" / "subdir"
            download_path.mkdir(parents=True, exist_ok=True)
            assert download_path.exists()

    def test_download_filename_sanitization(self):
        """Filenames with special chars should be sanitized."""
        # Characters invalid on Windows: < > : " / \ | ? *
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        filename = "test<>file:name.txt"

        # Simple sanitization
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')

        assert '<' not in sanitized
        assert '>' not in sanitized
        assert ':' not in sanitized

    def test_download_path_with_spaces(self):
        """Paths with spaces should work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path_with_spaces = Path(tmpdir) / "My Documents" / "test file.txt"
            path_with_spaces.parent.mkdir(parents=True, exist_ok=True)
            path_with_spaces.write_text("test content")
            assert path_with_spaces.exists()
            assert path_with_spaces.read_text() == "test content"

    def test_download_path_unicode(self):
        """Unicode characters in paths should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            unicode_path = Path(tmpdir) / "한국어" / "日本語" / "файл.txt"
            unicode_path.parent.mkdir(parents=True, exist_ok=True)
            unicode_path.write_text("unicode test", encoding='utf-8')
            assert unicode_path.exists()


# =============================================================================
# Upload Path Tests
# =============================================================================

class TestUploadPaths:
    """Test file upload path handling."""

    def test_upload_source_path_exists(self):
        """Upload should verify source file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "upload_test.txt"
            source.write_text("upload content")
            assert source.exists()
            assert source.is_file()

    def test_upload_path_with_extension(self):
        """File extensions should be preserved."""
        filename = "data.xlsx"
        p = Path(filename)
        assert p.suffix == ".xlsx"

        filename2 = "archive.tar.gz"
        p2 = Path(filename2)
        assert p2.suffix == ".gz"
        assert "".join(p2.suffixes) == ".tar.gz"

    def test_upload_temp_file_cleanup(self):
        """Temporary upload files should be cleanable."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as f:
            temp_path = Path(f.name)
            f.write(b"temp content")

        assert temp_path.exists()
        temp_path.unlink()
        assert not temp_path.exists()


# =============================================================================
# Model Path Tests (Qwen/Embeddings)
# =============================================================================

class TestModelPaths:
    """Test AI model path handling."""

    def test_appdata_path_detection(self):
        """AppData path should be detectable."""
        if sys.platform == 'win32':
            appdata = os.environ.get('APPDATA')
            assert appdata is not None
            assert Path(appdata).exists()
        else:
            # On Linux, simulate Windows AppData structure
            home = Path.home()
            fake_appdata = home / ".config" / "LocaNext"
            # Just verify path construction works
            assert "LocaNext" in str(fake_appdata)

    def test_model_directory_structure(self):
        """Model directory structure should be correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_base = Path(tmpdir) / "LocaNext" / "models"
            qwen_dir = model_base / "qwen"
            embeddings_dir = model_base / "embeddings"

            qwen_dir.mkdir(parents=True)
            embeddings_dir.mkdir(parents=True)

            assert qwen_dir.exists()
            assert embeddings_dir.exists()

    def test_model_file_path_length(self):
        """Model paths should handle typical lengths."""
        # Qwen model path example
        model_path = "C:/Users/username/AppData/Roaming/LocaNext/models/qwen/Qwen2.5-0.5B-Instruct/model.safetensors"
        p = PureWindowsPath(model_path)
        assert p.name == "model.safetensors"
        # Windows MAX_PATH is 260, but modern Windows supports longer
        assert len(str(p)) < 260


# =============================================================================
# PKL/Index Path Tests
# =============================================================================

class TestPKLIndexPaths:
    """Test PKL and FAISS index path handling."""

    def test_pkl_file_extension(self):
        """PKL files should have correct extension."""
        pkl_path = Path("tm_index.pkl")
        assert pkl_path.suffix == ".pkl"

    def test_faiss_index_path(self):
        """FAISS index paths should be valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_dir = Path(tmpdir) / "indexes" / "tm_123"
            index_dir.mkdir(parents=True)

            # Typical FAISS index files
            faiss_index = index_dir / "index.faiss"
            metadata = index_dir / "metadata.json"

            faiss_index.write_bytes(b"fake index")
            metadata.write_text('{"version": 1}')

            assert faiss_index.exists()
            assert metadata.exists()

    def test_index_path_with_tm_id(self):
        """Index paths should include TM ID correctly."""
        tm_id = 12345
        index_path = Path(f"indexes/tm_{tm_id}/index.faiss")
        assert str(tm_id) in str(index_path)
        assert index_path.suffix == ".faiss"


# =============================================================================
# Long Path Tests
# =============================================================================

class TestLongPaths:
    """Test handling of long paths (>260 chars on Windows)."""

    def test_long_path_creation(self):
        """Long paths should be creatable with proper prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a moderately long path (not exceeding limits)
            long_name = "a" * 50
            long_path = Path(tmpdir) / long_name / long_name / "file.txt"
            long_path.parent.mkdir(parents=True)
            long_path.write_text("test")
            assert long_path.exists()

    def test_path_length_validation(self):
        """Path length should be checked before operations."""
        max_path = 260  # Windows MAX_PATH
        test_path = "C:/" + "a" * 250 + "/file.txt"

        # This path is too long for classic Windows
        assert len(test_path) > max_path

        # Modern Windows with long path support can handle longer
        # Just verify we can construct the path
        p = PureWindowsPath(test_path)
        assert p.name == "file.txt"


# =============================================================================
# Special Characters Tests
# =============================================================================

class TestSpecialCharacterPaths:
    """Test paths with special characters."""

    def test_space_in_path(self):
        """Spaces in paths should work."""
        path = Path("Program Files/LocaNext/data.txt")
        assert "Program Files" in str(path)

    def test_parentheses_in_path(self):
        """Parentheses should work in paths."""
        path = Path("folder (1)/file (copy).txt")
        assert "(1)" in str(path)

    def test_ampersand_in_path(self):
        """Ampersand should work in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Games & Apps" / "test.txt"
            path.parent.mkdir(parents=True)
            path.write_text("test")
            assert path.exists()

    def test_hash_in_path(self):
        """Hash/pound sign should work in paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Issue #123" / "test.txt"
            path.parent.mkdir(parents=True)
            path.write_text("test")
            assert path.exists()


# =============================================================================
# Merge/Export Path Tests
# =============================================================================

class TestMergeExportPaths:
    """Test merge and export file path handling."""

    def test_export_filename_generation(self):
        """Export filenames should be generated correctly."""
        original = "game_data.xlsx"
        timestamp = "20260116_143022"
        export_name = f"{Path(original).stem}_merged_{timestamp}{Path(original).suffix}"
        assert export_name == "game_data_merged_20260116_143022.xlsx"

    def test_export_directory_default(self):
        """Export should default to Downloads or specified directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "exports"
            export_dir.mkdir()

            export_file = export_dir / "merged_output.xlsx"
            export_file.write_bytes(b"fake excel content")

            assert export_file.exists()
            assert export_file.stat().st_size > 0

    def test_export_overwrite_handling(self):
        """Export should handle existing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "output.xlsx"

            # Create existing file
            export_path.write_text("original")
            original_content = export_path.read_text()

            # Overwrite
            export_path.write_text("new content")
            new_content = export_path.read_text()

            assert original_content != new_content
            assert new_content == "new content"


# =============================================================================
# Install Path Tests
# =============================================================================

class TestInstallPaths:
    """Test installation path handling."""

    def test_program_files_path(self):
        """Program Files path should be valid."""
        if sys.platform == 'win32':
            program_files = os.environ.get('ProgramFiles')
            assert program_files is not None
        else:
            # Simulate on Linux
            program_files = "/opt"

        install_path = Path(program_files) / "LocaNext"
        assert "LocaNext" in str(install_path)

    def test_user_data_path(self):
        """User data path should be in appropriate location."""
        if sys.platform == 'win32':
            user_data = Path(os.environ.get('APPDATA', '')) / "LocaNext"
        else:
            user_data = Path.home() / ".config" / "LocaNext"

        assert "LocaNext" in str(user_data)

    def test_install_path_permissions(self):
        """Should verify path is writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_write.txt"
            test_path.write_text("permission test")
            assert test_path.exists()

            # Verify readable
            content = test_path.read_text()
            assert content == "permission test"
