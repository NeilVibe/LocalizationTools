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
DDS_FIXTURE = FIXTURES_DIR / "texture" / "image" / "character_kira.dds"
WEM_FIXTURE = FIXTURES_DIR / "sound" / "windows" / "English(US)" / "play_kira_taunt_01.wem"

# Check if Pillow can read DDS (not available on all platforms)
_CAN_READ_DDS = False
try:
    from PIL import Image
    import io
    if DDS_FIXTURE.exists():
        with open(DDS_FIXTURE, 'rb') as f:
            try:
                Image.open(io.BytesIO(f.read()))
                _CAN_READ_DDS = True
            except Exception:
                pass
except ImportError:
    pass


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

@pytest.mark.skipif(not _CAN_READ_DDS, reason="Pillow cannot read DDS on this platform (needs pillow-dds plugin)")
class TestDdsConversion:
    """Tests for DDS-to-PNG conversion."""

    def test_valid_dds_returns_png_bytes(self):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter()
        result = converter.convert_dds_to_png(DDS_FIXTURE)
        assert result is not None
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
        other_dds = FIXTURES_DIR / "texture" / "image" / "character_varon.dds"
        converter.convert_dds_to_png(other_dds)
        assert len(converter._png_cache) == 2
        # Add a third -- should evict oldest
        third_dds = FIXTURES_DIR / "texture" / "image" / "character_drakmar.dds"
        converter.convert_dds_to_png(third_dds)
        assert len(converter._png_cache) <= 2


# ===========================================================================
# TestWemConversion
# ===========================================================================

class TestWemConversion:
    """Tests for WEM-to-WAV conversion."""

    def test_wem_with_riff_header_still_needs_vgmstream(self, tmp_path):
        """WEM files with RIFF header must still go through vgmstream (Wwise uses RIFF containers).
        Without vgmstream available, conversion returns None."""
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        # WEM_FIXTURE has RIFF header but is .wem extension — must NOT be copied as-is
        # Without vgmstream-cli in CI, this correctly returns None
        result = converter.convert_wem_to_wav(WEM_FIXTURE)
        assert result is None

    def test_successful_conversion_returns_path(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        with patch("server.tools.ldm.services.media_converter.shutil.which", return_value=None):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                # Pre-create the output file so the converter finds it
                expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]
                wav_out = tmp_path / f"{expected_hash}.wav"
                wav_out.write_bytes(b"RIFF" + b"\x24\x00\x00\x00" + b"WAVEfmt " + b"\x10\x00\x00\x00" + b"\x01\x00" + b"\x01\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x02\x00\x10\x00" + b"data" + b"\x00\x00\x00\x00")

                # Provide a fake vgmstream path
                with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
                    result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is not None
        assert isinstance(result, Path)

    def test_failed_conversion_returns_none(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        # Use a non-RIFF WEM file (actual Wwise format) to test vgmstream failure path
        fake_wem = tmp_path / "fake.wem"
        fake_wem.write_bytes(b"BKHD" + b"\x00" * 40)  # Wwise header, not RIFF

        with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="error decoding")
                result = converter.convert_wem_to_wav(fake_wem)

        assert result is None

    def test_path_hashed_filename(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)
        expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]

        with patch.object(converter, "_find_vgmstream", return_value=Path("/usr/bin/vgmstream-cli")):
            with patch("server.tools.ldm.services.media_converter.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                wav_out = tmp_path / f"{expected_hash}.wav"
                wav_out.write_bytes(b"RIFF" + b"\x24\x00\x00\x00" + b"WAVEfmt " + b"\x10\x00\x00\x00" + b"\x01\x00" + b"\x01\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x02\x00\x10\x00" + b"data" + b"\x00\x00\x00\x00")
                result = converter.convert_wem_to_wav(WEM_FIXTURE)

        assert result is not None
        assert expected_hash in result.name

    def test_cached_wav_skips_subprocess(self, tmp_path):
        from server.tools.ldm.services.media_converter import MediaConverter
        converter = MediaConverter(wav_cache_dir=tmp_path)

        # Pre-create cached WAV file with recent mtime
        expected_hash = hashlib.md5(str(WEM_FIXTURE).encode()).hexdigest()[:8]
        wav_out = tmp_path / f"{expected_hash}.wav"
        wav_out.write_bytes(b"RIFF" + b"\x24\x00\x00\x00" + b"WAVEfmt " + b"\x10\x00\x00\x00" + b"\x01\x00" + b"\x01\x00" + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x02\x00\x10\x00" + b"data" + b"\x00\x00\x00\x00")

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

        # Use a non-RIFF WEM file to test vgmstream-missing path
        fake_wem = tmp_path / "fake.wem"
        fake_wem.write_bytes(b"BKHD" + b"\x00" * 40)  # Wwise header, not RIFF

        with patch("server.tools.ldm.services.media_converter.shutil.which", return_value=None):
            result = converter.convert_wem_to_wav(fake_wem)

        assert result is None

    def test_get_media_converter_singleton(self):
        from server.tools.ldm.services.media_converter import get_media_converter
        a = get_media_converter()
        b = get_media_converter()
        assert a is b
