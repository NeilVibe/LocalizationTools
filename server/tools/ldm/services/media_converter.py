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
import os
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from typing import Optional

import sys

from loguru import logger
from PIL import Image

# Suppress console window popup on Windows for subprocess calls
_SUBPROCESS_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)


# =============================================================================
# MediaConverter
# =============================================================================

class MediaConverter:
    """Converts DDS textures to PNG and WEM audio to WAV with caching."""

    def __init__(
        self,
        png_cache_size: int = 500,
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

        # Check disk cache — must exist, be valid PCM WAV, and be newer than source
        if wav_path.exists():
            try:
                if wav_path.stat().st_mtime >= wem_path.stat().st_mtime and self._is_valid_pcm_wav(wav_path):
                    logger.debug("WAV cache hit: {} ({}B)", wav_path.name, wav_path.stat().st_size)
                    return wav_path
                else:
                    logger.info("WAV cache invalid or stale, re-converting: {}", wav_path.name)
                    wav_path.unlink()
            except OSError:
                pass

        # NOTE: Do NOT shortcut on RIFF header — WEM files use RIFF containers too
        # (Wwise wraps audio in RIFF). Must ALWAYS run vgmstream to get proper PCM WAV.
        # Only skip conversion if the file is already a .wav extension (not .wem).
        if wem_path.suffix.lower() == ".wav":
            try:
                shutil.copy2(wem_path, wav_path)
                logger.debug("Source is already WAV, copied: {}", wem_path.name)
                return wav_path
            except OSError:
                pass

        # Find vgmstream-cli
        vgmstream = self._find_vgmstream()
        if vgmstream is None:
            logger.warning("vgmstream-cli not found -- cannot convert WEM files")
            return None

        try:
            logger.info("[vgmstream] Converting: {} → {}", wem_path, wav_path)
            result = subprocess.run(
                [str(vgmstream), "-o", str(wav_path), str(wem_path)],
                capture_output=True,
                text=True,
                timeout=60,
                **_SUBPROCESS_KWARGS,
            )

            if result.returncode != 0:
                logger.warning(
                    "vgmstream-cli failed for {} (rc={}): stdout={}, stderr={}",
                    wem_path.name,
                    result.returncode,
                    result.stdout.strip()[:200],
                    result.stderr.strip()[:200],
                )
                # Clean up partial output
                if wav_path.exists():
                    wav_path.unlink()
                return None

            # Log vgmstream output for diagnostics
            if result.stdout.strip():
                logger.debug("[vgmstream] stdout: {}", result.stdout.strip()[:300])

            if not wav_path.exists():
                logger.warning("vgmstream-cli produced no output for {}", wem_path.name)
                return None

            wav_size = wav_path.stat().st_size
            if wav_size <= 44 or not self._is_valid_pcm_wav(wav_path):
                logger.error(
                    "vgmstream-cli produced invalid WAV ({}B, valid_pcm={}) for {}",
                    wav_size, self._is_valid_pcm_wav(wav_path), wem_path.name,
                )
                wav_path.unlink(missing_ok=True)
                return None

            logger.info("Converted WEM to WAV: {} → {} ({}B)", wem_path.name, wav_path.name, wav_size)
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

    @staticmethod
    def _is_valid_pcm_wav(path: Path) -> bool:
        """Check if a file is a valid PCM WAV (not a WEM with RIFF header).

        Reads first 20 bytes: RIFF + size + WAVE + fmt + chunk_size + audio_format.
        PCM WAV has audio_format == 1. WEM/Vorbis/etc. have other values.
        """
        try:
            with open(path, "rb") as f:
                header = f.read(20)
            if len(header) < 20:
                return False
            # RIFF....WAVEfmt
            if header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                return False
            # Audio format at byte 20: 1 = PCM, 3 = IEEE float (both playable)
            audio_format = int.from_bytes(header[20:22], "little") if len(header) >= 22 else 0
            # Actually need to read 22 bytes for audio_format
            with open(path, "rb") as f:
                data = f.read(22)
            if len(data) < 22:
                return False
            audio_format = int.from_bytes(data[20:22], "little")
            return audio_format in (1, 3)  # PCM or IEEE float
        except Exception:
            return False

    def _find_vgmstream(self) -> Optional[Path]:
        """Locate the vgmstream-cli binary.

        Search order (grafted from MDG audio_handler pattern):
        1. System PATH
        2. LOCANEXT_RESOURCES_PATH env var (Electron packaged app)
        3. Co-located with python.exe (packaged app: resources/bin/vgmstream/)
        4. Project root bin/vgmstream/ (dev mode after bundle_vgmstream.py)
        5. Sibling to server dir (legacy server/bin/)
        """
        if self._vgmstream_checked:
            return self._vgmstream_path

        self._vgmstream_checked = True
        exe_name = "vgmstream-cli.exe" if os.name == "nt" else "vgmstream-cli"

        logger.info("[vgmstream] Starting search for {} (os.name={})", exe_name, os.name)

        # 1. Check PATH first
        which_result = shutil.which("vgmstream-cli")
        if which_result:
            self._vgmstream_path = Path(which_result)
            logger.info("[vgmstream] Found in PATH: {}", self._vgmstream_path)
            return self._vgmstream_path
        logger.debug("[vgmstream] Not in PATH")

        # 2. Check LOCANEXT_RESOURCES_PATH env var (Electron packaged app)
        electron_resources = os.environ.get("LOCANEXT_RESOURCES_PATH", "")
        if electron_resources:
            electron_vgm = Path(electron_resources) / "bin" / "vgmstream" / exe_name
            logger.debug("[vgmstream] Checking LOCANEXT_RESOURCES_PATH: {}", electron_vgm)
            if electron_vgm.exists():
                self._vgmstream_path = electron_vgm
                logger.info("[vgmstream] Found via LOCANEXT_RESOURCES_PATH: {}", self._vgmstream_path)
                return self._vgmstream_path
            logger.debug("[vgmstream] Not at LOCANEXT_RESOURCES_PATH ({})", electron_vgm)
        else:
            logger.debug("[vgmstream] LOCANEXT_RESOURCES_PATH not set")

        # 3. Co-located with python.exe (packaged app structure):
        #    resources/tools/python/python.exe  <-- sys.executable
        #    resources/bin/vgmstream/vgmstream-cli.exe
        import sys
        python_exe = Path(sys.executable).resolve()
        resources_dir = python_exe.parent.parent.parent  # tools/python/python.exe -> resources/
        packaged_vgm = resources_dir / "bin" / "vgmstream" / exe_name
        logger.debug("[vgmstream] Checking co-located (sys.executable={}): {}", python_exe, packaged_vgm)
        if packaged_vgm.exists():
            self._vgmstream_path = packaged_vgm
            logger.info("[vgmstream] Found co-located with python: {}", self._vgmstream_path)
            return self._vgmstream_path

        # 3b. Fallback: walk up from python.exe looking for bin/vgmstream/
        #     Handles cases where sys.executable depth varies
        for i in range(1, 6):
            ancestor = python_exe.parents[i] if i < len(python_exe.parents) else None
            if ancestor is None:
                break
            candidate = ancestor / "bin" / "vgmstream" / exe_name
            if candidate.exists():
                self._vgmstream_path = candidate
                logger.info("[vgmstream] Found by walking up from python.exe (depth {}): {}", i, self._vgmstream_path)
                return self._vgmstream_path

        # 4. Project root bin/vgmstream/ (dev mode after running bundle_vgmstream.py)
        project_bin = Path(__file__).resolve().parents[4] / "bin" / "vgmstream" / exe_name
        logger.debug("[vgmstream] Checking project bin: {}", project_bin)
        if project_bin.exists():
            self._vgmstream_path = project_bin
            logger.info("[vgmstream] Found in project bin: {}", self._vgmstream_path)
            return self._vgmstream_path

        # 5. Legacy server/bin/
        bundled = Path(__file__).resolve().parents[2] / "bin" / exe_name
        logger.debug("[vgmstream] Checking legacy server/bin: {}", bundled)
        if bundled.exists():
            self._vgmstream_path = bundled
            logger.info("[vgmstream] Found bundled: {}", self._vgmstream_path)
            return self._vgmstream_path

        logger.warning(
            "[vgmstream] NOT FOUND in any search path -- audio playback disabled. "
            "Searched: PATH, LOCANEXT_RESOURCES_PATH={}, co-located={}, project={}, legacy={}",
            electron_resources or "(not set)",
            packaged_vgm,
            project_bin,
            bundled,
        )
        return None

    def cleanup_wav_cache(self) -> int:
        """Delete all cached WAV files from disk. Returns count deleted.

        MDG-exact: audio_handler.cleanup_temp_files() equivalent.
        """
        count = 0
        if self._wav_cache_dir.exists():
            for f in self._wav_cache_dir.glob("*.wav"):
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    pass
        logger.info("Cleaned {} cached WAV files from {}", count, self._wav_cache_dir)
        return count

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
