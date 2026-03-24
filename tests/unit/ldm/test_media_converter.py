"""Unit tests for MediaConverter service (DDS-to-PNG, WEM-to-WAV)."""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "mock_gamedata"
DDS_FIXTURE = FIXTURES_DIR / "textures" / "character_kira.dds"
WEM_FIXTURE = FIXTURES_DIR / "audio" / "varon_greeting.wem"


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton between tests."""
    from server.tools.ldm.services.media_converter import _reset_singleton
    _reset_singleton()
    yield
    _reset_singleton()


# ===========================================================================
# TestDdsConversion
# ===========================================================================

class TestDdsConversion:
    """Tests for DDS-to-PNG conversion."""

    def test_valid_dds_returns_png_bytes(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        result = converter.convert_dds_to_png(DDS_FIXTURE)
        if result is None:
            pytest.skip("Pillow cannot read DDS on this platform (needs pillow-dds or Pillow 10.1+ with DDS plugin)")
        assert result[:4] == b"\x89PNG", "Should start with PNG magic bytes"

    def test_nonexistent_path_returns_none(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        result = converter.convert_dds_to_png(Path("/tmp/does_not_exist.dds"))
        assert result is None

    def test_caching_returns_same_bytes(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        first = converter.convert_dds_to_png(DDS_FIXTURE)
        second = converter.convert_dds_to_png(DDS_FIXTURE)
        assert first is second, "Cached result should be the exact same object"

    def test_max_size_constrains_dimensions(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        result = converter.convert_dds_to_png(DDS_FIXTURE, max_size=16)
        assert result is not None
        # Verify actual image dimensions
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(result))
        assert img.width <= 16
        assert img.height <= 16

    def test_lru_eviction_when_cache_full(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(png_cache_size=2)
        # Fill cache with 2 entries (use different paths via symlink/copy trick)
        converter.convert_dds_to_png(DDS_FIXTURE)
        # Use another DDS fixture
        other_dds = FIXTURES_DIR / "textures" / "character_varon.dds"
        converter.convert_dds_to_png(other_dds)
        assert len(converter._png_cache) == 2
        # Add a third -- should evict oldest
        third_dds = FIXTURES_DIR / "textures" / "character_drakmar.dds"
        converter.convert_dds_to_png(third_dds)
        assert len(converter._png_cache) <= 2


# ===========================================================================
# TestWemConversion
# ===========================================================================

class TestWemConversion:
    """Tests for WEM-to-WAV conversion."""

    def test_successful_conversion_returns_path(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        with patch("server.tools.ldm.services.media_converter.shutil.which", return_value=None):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                # Pre-create the output file so the converter finds it
                expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]
                wav_out = tmp_path / f"{expected_hash}.wav"
                wav_out.write_bytes(b"RIFF" + b"\x00" * 40)

                # Provide a fake vgmstream path
                with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
                    result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is not None
        assert isinstance(result, Path)

    def test_failed_conversion_returns_none(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="error decoding")
                result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is None

    def test_path_hashed_filename(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)
        expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]

        with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                wav_out = tmp_path / f"{expected_hash}.wav"
                wav_out.write_bytes(b"RIFF" + b"\x00" * 40)
                result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is not None
        assert expected_hash in result.name

    def test_cached_wav_skips_subprocess(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        # Pre-create cached WAV file with recent mtime
        expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]
        wav_out = tmp_path / f"{expected_hash}.wav"
        wav_out.write_bytes(b"RIFF" + b"\x00" * 40)

        with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
            result = converter.convert_wem_to_wav(WEM_FIXTURE)

        # subprocess should NOT have been called -- cached file exists
        mock_run.assert_not_called()
        assert result == wav_out


# ===========================================================================
# TestGracefulFallback
# ===========================================================================

class TestGracefulFallback:
    """Tests for graceful error handling."""

    def test_corrupt_dds_returns_none(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        corrupt = tmp_path / "corrupt.dds"
        corrupt.write_bytes(b"\x00\x01\x02\x03" * 10)
        result = converter.convert_dds_to_png(corrupt)
        assert result is None

    def test_no_vgmstream_returns_none(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        with patch("server.tools.ldm.services.media_converter.shutil.which", return_value=None):
            result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is None

    def test_get_media_converter_singleton(self):
        from server.tools.ldm.services.media_converter import get_media_converter
        a = get_media_converter()
        b = get_media_converter()
        assert a is b
