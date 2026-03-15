"""
MediaConverter service - DDS-to-PNG and WEM-to-WAV conversion with caching.

Converts raw game assets (DDS textures, WEM audio) into browser-consumable
formats (PNG images, WAV audio). Used by streaming endpoints to serve
media to the LocaNext frontend.

Phase 11: Image/Audio Pipeline (Plan 01)
"""
from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from loguru import logger
from PIL import Image


# =============================================================================
# MediaConverter
# =============================================================================

class MediaConverter:
    """Converts DDS textures to PNG and WEM audio to WAV with caching."""

    def __init__(
        self,
        png_cache_size: int = 100,
        wav_cache_dir: Optional[Path] = None,
    ) -> None:
        self._png_cache: OrderedDict[str, bytes] = OrderedDict()
        self._png_cache_size = png_cache_size
        self._wav_cache_dir = wav_cache_dir or Path(tempfile.gettempdir()) / "locanext_audio"
        self._wav_cache_dir.mkdir(parents=True, exist_ok=True)
        self._vgmstream_path: Optional[Path] = None
        self._vgmstream_checked = False

    # -------------------------------------------------------------------------
    # DDS -> PNG
    # -------------------------------------------------------------------------

    def convert_dds_to_png(
        self,
        dds_path: Path,
        max_size: int = 256,
    ) -> Optional[bytes]:
        """Convert a DDS texture to PNG bytes.

        Args:
            dds_path: Path to the .dds file.
            max_size: Maximum dimension (width or height) for the thumbnail.

        Returns:
            PNG bytes or None if conversion fails.
        """
        cache_key = f"{dds_path}:{max_size}"

        # Check cache
        if cache_key in self._png_cache:
            self._png_cache.move_to_end(cache_key)
            return self._png_cache[cache_key]

        try:
            if not dds_path.exists():
                logger.warning("DDS file not found: {}", dds_path)
                return None

            img = Image.open(dds_path)
            img = img.convert("RGBA")
            img.thumbnail((max_size, max_size))

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

            # Store in LRU cache
            self._png_cache[cache_key] = png_bytes
            if len(self._png_cache) > self._png_cache_size:
                self._png_cache.popitem(last=False)

            logger.debug("Converted DDS to PNG: {} ({}B)", dds_path.name, len(png_bytes))
            return png_bytes

        except Exception as exc:
            logger.warning("Failed to convert DDS {}: {}", dds_path, exc)
            return None

    # -------------------------------------------------------------------------
    # WEM -> WAV
    # -------------------------------------------------------------------------

    def convert_wem_to_wav(self, wem_path: Path) -> Optional[Path]:
        """Convert a WEM audio file to WAV using vgmstream-cli.

        Args:
            wem_path: Path to the .wem file.

        Returns:
            Path to the converted WAV file, or None if conversion fails.
        """
        path_hash = hashlib.md5(str(wem_path).encode()).hexdigest()[:8]
        wav_path = self._wav_cache_dir / f"{path_hash}.wav"

        # Check disk cache
        if wav_path.exists():
            try:
                if wav_path.stat().st_mtime >= wem_path.stat().st_mtime:
                    logger.debug("WAV cache hit: {}", wav_path.name)
                    return wav_path
            except OSError:
                pass

        # Find vgmstream-cli
        vgmstream = self._find_vgmstream()
        if vgmstream is None:
            logger.warning("vgmstream-cli not found -- cannot convert WEM files")
            return None

        try:
            result = subprocess.run(
                [str(vgmstream), "-o", str(wav_path), str(wem_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                logger.warning(
                    "vgmstream-cli failed for {}: {}",
                    wem_path.name,
                    result.stderr.strip(),
                )
                # Clean up partial output
                if wav_path.exists():
                    wav_path.unlink()
                return None

            if not wav_path.exists():
                logger.warning("vgmstream-cli produced no output for {}", wem_path.name)
                return None

            logger.debug("Converted WEM to WAV: {}", wem_path.name)
            return wav_path

        except subprocess.TimeoutExpired:
            logger.warning("vgmstream-cli timed out for {}", wem_path.name)
            return None
        except Exception as exc:
            logger.warning("Failed to convert WEM {}: {}", wem_path, exc)
            return None

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _find_vgmstream(self) -> Optional[Path]:
        """Locate the vgmstream-cli binary."""
        if self._vgmstream_checked:
            return self._vgmstream_path

        self._vgmstream_checked = True

        # Check PATH first
        which_result = shutil.which("vgmstream-cli")
        if which_result:
            self._vgmstream_path = Path(which_result)
            logger.info("Found vgmstream-cli in PATH: {}", self._vgmstream_path)
            return self._vgmstream_path

        # Check bundled location
        bundled = Path(__file__).resolve().parents[2] / "bin" / "vgmstream-cli"
        if bundled.exists():
            self._vgmstream_path = bundled
            logger.info("Found bundled vgmstream-cli: {}", self._vgmstream_path)
            return self._vgmstream_path

        logger.debug("vgmstream-cli not found in PATH or bundled location")
        return None

    def clear_caches(self) -> None:
        """Clear all in-memory and disk caches."""
        self._png_cache.clear()
        self._vgmstream_checked = False
        self._vgmstream_path = None
        logger.info("MediaConverter caches cleared")


# =============================================================================
# Singleton
# =============================================================================

_service_instance: Optional[MediaConverter] = None


def get_media_converter() -> MediaConverter:
    """Get or create the singleton MediaConverter instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MediaConverter()
    return _service_instance


def _reset_singleton() -> None:
    """Reset the singleton (for testing)."""
    global _service_instance
    _service_instance = None
