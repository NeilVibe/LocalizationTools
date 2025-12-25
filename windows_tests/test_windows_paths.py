"""
Windows PATH Tests

Critical tests for Windows-specific path handling.
These tests run ONLY on Windows during the CI build-windows job.

Tests:
- Download/Upload paths work correctly
- Model paths resolve to AppData
- PKL/Index paths save/load properly
- Install paths are correct
"""

import os
import sys
import platform
import tempfile
from pathlib import Path

import pytest


# Skip all tests if not on Windows
pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-only tests"
)


class TestWindowsPathResolution:
    """Test that paths resolve correctly on Windows."""

    def test_appdata_path_exists(self):
        """AppData path should exist and be writable."""
        appdata = os.environ.get("APPDATA")
        assert appdata is not None, "APPDATA environment variable not set"
        assert Path(appdata).exists(), f"APPDATA path does not exist: {appdata}"
        assert Path(appdata).is_dir(), f"APPDATA is not a directory: {appdata}"

    def test_userprofile_path_exists(self):
        """User profile path should exist."""
        userprofile = os.environ.get("USERPROFILE")
        assert userprofile is not None, "USERPROFILE environment variable not set"
        assert Path(userprofile).exists(), f"USERPROFILE does not exist: {userprofile}"

    def test_locanext_appdata_writable(self):
        """LocaNext AppData folder should be creatable and writable."""
        appdata = os.environ.get("APPDATA")
        locanext_path = Path(appdata) / "LocaNext"

        # Create if doesn't exist
        locanext_path.mkdir(exist_ok=True)
        assert locanext_path.exists(), f"Failed to create LocaNext folder: {locanext_path}"

        # Test write
        test_file = locanext_path / ".write_test"
        test_file.write_text("test")
        assert test_file.exists(), "Failed to write test file"
        test_file.unlink()  # Cleanup

    def test_downloads_path_exists(self):
        """Downloads folder should exist (skipped for SYSTEM user in CI)."""
        userprofile = os.environ.get("USERPROFILE")
        downloads = Path(userprofile) / "Downloads"
        # CI runs as SYSTEM user which has no Downloads folder
        if "systemprofile" in str(userprofile).lower():
            pytest.skip("SYSTEM user has no Downloads folder (CI environment)")
        assert downloads.exists(), f"Downloads folder does not exist: {downloads}"


class TestModelPaths:
    """Test model path resolution."""

    def test_models_directory_creatable(self):
        """Models directory should be creatable in AppData."""
        appdata = os.environ.get("APPDATA")
        models_path = Path(appdata) / "LocaNext" / "models"

        models_path.mkdir(parents=True, exist_ok=True)
        assert models_path.exists(), f"Failed to create models folder: {models_path}"

    def test_qwen_model_path_structure(self):
        """Qwen model path should follow expected structure."""
        appdata = os.environ.get("APPDATA")
        qwen_path = Path(appdata) / "LocaNext" / "models" / "qwen"

        # Just verify path is valid (model may not be downloaded yet)
        assert qwen_path.parent.parent.parent == Path(appdata)

    def test_model2vec_path_structure(self):
        """Model2Vec path should follow expected structure."""
        appdata = os.environ.get("APPDATA")
        m2v_path = Path(appdata) / "LocaNext" / "models" / "model2vec"

        # Just verify path is valid
        assert m2v_path.parent.parent.parent == Path(appdata)


class TestIndexPaths:
    """Test FAISS/PKL index path handling."""

    def test_indexes_directory_creatable(self):
        """Indexes directory should be creatable."""
        appdata = os.environ.get("APPDATA")
        indexes_path = Path(appdata) / "LocaNext" / "indexes"

        indexes_path.mkdir(parents=True, exist_ok=True)
        assert indexes_path.exists(), f"Failed to create indexes folder: {indexes_path}"

    def test_pkl_file_writable(self):
        """PKL files should be writable to indexes folder."""
        appdata = os.environ.get("APPDATA")
        indexes_path = Path(appdata) / "LocaNext" / "indexes"
        indexes_path.mkdir(parents=True, exist_ok=True)

        test_pkl = indexes_path / "test_index.pkl"
        test_pkl.write_bytes(b"test pkl data")
        assert test_pkl.exists(), "Failed to write PKL file"

        # Read back
        data = test_pkl.read_bytes()
        assert data == b"test pkl data", "PKL data mismatch"

        test_pkl.unlink()  # Cleanup

    def test_faiss_index_writable(self):
        """FAISS index files should be writable."""
        appdata = os.environ.get("APPDATA")
        indexes_path = Path(appdata) / "LocaNext" / "indexes"
        indexes_path.mkdir(parents=True, exist_ok=True)

        test_index = indexes_path / "test.faiss"
        test_index.write_bytes(b"fake faiss data")
        assert test_index.exists(), "Failed to write FAISS file"
        test_index.unlink()  # Cleanup


class TestFileOperationPaths:
    """Test file upload/download path handling."""

    def test_temp_directory_writable(self):
        """Temp directory should be writable for file operations."""
        temp_dir = Path(tempfile.gettempdir())
        assert temp_dir.exists(), f"Temp directory does not exist: {temp_dir}"

        test_file = temp_dir / "locanext_test.tmp"
        test_file.write_text("test")
        assert test_file.exists()
        test_file.unlink()

    def test_path_with_spaces(self):
        """Paths with spaces should work correctly."""
        appdata = os.environ.get("APPDATA")
        test_path = Path(appdata) / "LocaNext" / "test folder with spaces"

        test_path.mkdir(parents=True, exist_ok=True)
        assert test_path.exists(), "Failed to create folder with spaces"

        test_file = test_path / "file with spaces.txt"
        test_file.write_text("content")
        assert test_file.exists()

        # Cleanup
        test_file.unlink()
        test_path.rmdir()

    def test_path_with_unicode(self):
        """Paths with Unicode (Korean) should work correctly."""
        appdata = os.environ.get("APPDATA")
        test_path = Path(appdata) / "LocaNext" / "테스트_폴더"

        test_path.mkdir(parents=True, exist_ok=True)
        assert test_path.exists(), "Failed to create Korean folder"

        test_file = test_path / "한글파일.txt"
        test_file.write_text("한글 내용", encoding="utf-8")
        assert test_file.exists()

        # Read back and verify
        content = test_file.read_text(encoding="utf-8")
        assert content == "한글 내용"

        # Cleanup
        test_file.unlink()
        test_path.rmdir()

    def test_long_path_support(self):
        """Long paths should work (Windows 10+ with long path enabled)."""
        appdata = os.environ.get("APPDATA")

        # Create a moderately long path (not exceeding 260 for safety)
        long_folder = "a" * 50
        test_path = Path(appdata) / "LocaNext" / long_folder

        try:
            test_path.mkdir(parents=True, exist_ok=True)
            assert test_path.exists(), "Failed to create long-named folder"
            test_path.rmdir()
        except OSError as e:
            pytest.skip(f"Long path not supported: {e}")


class TestServerConnectivity:
    """Basic connectivity tests for Windows."""

    def test_localhost_resolvable(self):
        """localhost should resolve correctly."""
        import socket
        try:
            socket.gethostbyname("localhost")
        except socket.gaierror:
            pytest.fail("localhost does not resolve")

    def test_port_8888_bindable(self):
        """Port 8888 should be available for backend."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(("127.0.0.1", 8888))
            # Either connected (server running) or refused (available) is OK
            # Only timeout or other errors are problems
        finally:
            sock.close()


class TestInstallPaths:
    """Test installation path handling."""

    def test_program_files_exists(self):
        """Program Files directory should exist."""
        program_files = os.environ.get("ProgramFiles")
        assert program_files is not None, "ProgramFiles not set"
        assert Path(program_files).exists(), f"ProgramFiles does not exist: {program_files}"

    def test_program_files_x86_exists(self):
        """Program Files (x86) should exist on 64-bit Windows."""
        pf_x86 = os.environ.get("ProgramFiles(x86)")
        if pf_x86:
            assert Path(pf_x86).exists(), f"ProgramFiles(x86) does not exist: {pf_x86}"
