"""
Windows Model and Index Tests

Tests for ML model paths and FAISS index handling on Windows.
"""

import os
import platform
import pickle
import struct
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Windows-only tests"
)


class TestModelPaths:
    """Test model directory structure."""

    def test_models_directory_structure(self):
        """Models directory should have correct structure."""
        appdata = os.environ.get("APPDATA")
        models_root = Path(appdata) / "LocaNext" / "models"

        # Create expected structure
        subdirs = ["qwen", "model2vec", "cache"]
        for subdir in subdirs:
            (models_root / subdir).mkdir(parents=True, exist_ok=True)

        # Verify
        for subdir in subdirs:
            assert (models_root / subdir).exists()
            assert (models_root / subdir).is_dir()

    def test_model_file_writable(self):
        """Should be able to write model files."""
        appdata = os.environ.get("APPDATA")
        model_path = Path(appdata) / "LocaNext" / "models" / "test"
        model_path.mkdir(parents=True, exist_ok=True)

        # Simulate writing a model file (binary)
        model_file = model_path / "test_model.bin"
        model_file.write_bytes(b"\x00" * 1024)  # 1KB dummy

        assert model_file.exists()
        assert model_file.stat().st_size == 1024

        model_file.unlink()
        model_path.rmdir()

    def test_large_model_file(self):
        """Should handle larger model files (10MB)."""
        appdata = os.environ.get("APPDATA")
        model_path = Path(appdata) / "LocaNext" / "models" / "test"
        model_path.mkdir(parents=True, exist_ok=True)

        # Write 10MB file
        model_file = model_path / "large_model.bin"
        chunk = b"\x00" * (1024 * 1024)  # 1MB
        with open(model_file, 'wb') as f:
            for _ in range(10):
                f.write(chunk)

        assert model_file.exists()
        assert model_file.stat().st_size == 10 * 1024 * 1024

        model_file.unlink()
        model_path.rmdir()


class TestPickleFiles:
    """Test pickle file handling for indexes."""

    def test_pickle_save_load(self):
        """Pickle files should save and load correctly."""
        appdata = os.environ.get("APPDATA")
        index_path = Path(appdata) / "LocaNext" / "indexes"
        index_path.mkdir(parents=True, exist_ok=True)

        test_data = {
            "string_ids": ["STR_001", "STR_002", "STR_003"],
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
            "metadata": {"version": "1.0", "count": 3}
        }

        pkl_file = index_path / "test_index.pkl"
        with open(pkl_file, 'wb') as f:
            pickle.dump(test_data, f)

        # Load and verify
        with open(pkl_file, 'rb') as f:
            loaded_data = pickle.load(f)

        assert loaded_data == test_data
        pkl_file.unlink()

    def test_pickle_with_korean(self):
        """Pickle with Korean content should work."""
        appdata = os.environ.get("APPDATA")
        index_path = Path(appdata) / "LocaNext" / "indexes"
        index_path.mkdir(parents=True, exist_ok=True)

        test_data = {
            "strings": ["안녕하세요", "게임 번역", "로컬라이제이션"],
            "translations": {"hello": "안녕", "world": "세계"}
        }

        pkl_file = index_path / "korean_index.pkl"
        with open(pkl_file, 'wb') as f:
            pickle.dump(test_data, f)

        with open(pkl_file, 'rb') as f:
            loaded_data = pickle.load(f)

        assert loaded_data["strings"][0] == "안녕하세요"
        assert loaded_data["translations"]["hello"] == "안녕"
        pkl_file.unlink()

    def test_large_pickle_file(self):
        """Large pickle files should work."""
        appdata = os.environ.get("APPDATA")
        index_path = Path(appdata) / "LocaNext" / "indexes"
        index_path.mkdir(parents=True, exist_ok=True)

        # Create large data (10000 entries)
        test_data = {
            "ids": [f"STR_{i:05d}" for i in range(10000)],
            "vectors": [[float(j) for j in range(256)] for _ in range(100)]  # 100 vectors
        }

        pkl_file = index_path / "large_index.pkl"
        with open(pkl_file, 'wb') as f:
            pickle.dump(test_data, f)

        assert pkl_file.exists()
        assert pkl_file.stat().st_size > 100000  # Should be > 100KB

        with open(pkl_file, 'rb') as f:
            loaded_data = pickle.load(f)

        assert len(loaded_data["ids"]) == 10000
        pkl_file.unlink()


class TestFAISSIndex:
    """Test FAISS index file handling."""

    def test_faiss_importable(self):
        """FAISS should be importable (if installed)."""
        try:
            import faiss
        except ImportError:
            pytest.skip("faiss not installed")

    def test_faiss_index_path_writable(self):
        """FAISS index path should be writable."""
        appdata = os.environ.get("APPDATA")
        index_path = Path(appdata) / "LocaNext" / "indexes" / "faiss"
        index_path.mkdir(parents=True, exist_ok=True)

        # Write dummy FAISS-like file
        index_file = index_path / "test.faiss"
        index_file.write_bytes(b"FAISS_INDEX_DUMMY_DATA" * 100)

        assert index_file.exists()
        index_file.unlink()
        index_path.rmdir()

    def test_numpy_arrays_saveable(self):
        """NumPy arrays should be saveable (for embeddings)."""
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy not installed")

        appdata = os.environ.get("APPDATA")
        index_path = Path(appdata) / "LocaNext" / "indexes"
        index_path.mkdir(parents=True, exist_ok=True)

        # Create embeddings array
        embeddings = np.random.rand(1000, 256).astype(np.float32)

        npy_file = index_path / "embeddings.npy"
        np.save(str(npy_file), embeddings)

        assert npy_file.exists()

        # Load and verify
        loaded = np.load(str(npy_file))
        assert loaded.shape == (1000, 256)

        npy_file.unlink()


class TestCachePaths:
    """Test cache directory handling."""

    def test_cache_directory_writable(self):
        """Cache directory should be writable."""
        appdata = os.environ.get("APPDATA")
        cache_path = Path(appdata) / "LocaNext" / "cache"
        cache_path.mkdir(parents=True, exist_ok=True)

        test_file = cache_path / "test_cache.tmp"
        test_file.write_text("cache test")
        assert test_file.exists()
        test_file.unlink()

    def test_huggingface_cache_path(self):
        """HuggingFace cache path should be settable."""
        appdata = os.environ.get("APPDATA")
        hf_cache = Path(appdata) / "LocaNext" / "models" / "huggingface"
        hf_cache.mkdir(parents=True, exist_ok=True)

        # Set environment variable (for HuggingFace)
        os.environ["HF_HOME"] = str(hf_cache)
        assert os.environ["HF_HOME"] == str(hf_cache)
        assert hf_cache.exists()

    def test_temp_cache_cleanup(self):
        """Temp cache files should be cleanable."""
        appdata = os.environ.get("APPDATA")
        cache_path = Path(appdata) / "LocaNext" / "cache" / "temp"
        cache_path.mkdir(parents=True, exist_ok=True)

        # Create some temp files
        for i in range(5):
            (cache_path / f"temp_{i}.tmp").write_text(f"temp {i}")

        # Cleanup
        for f in cache_path.glob("*.tmp"):
            f.unlink()

        assert len(list(cache_path.glob("*.tmp"))) == 0
        cache_path.rmdir()
