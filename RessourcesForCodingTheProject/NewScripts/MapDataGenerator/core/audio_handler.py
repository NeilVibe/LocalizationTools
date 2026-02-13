"""
Audio Handler Module

Handles WEM audio file playback:
- Converts WEM to WAV using vgmstream-cli
- Plays WAV audio using platform-appropriate method
- Manages temporary files and playback state
- Thread-safe with generation counters to prevent stale callbacks
"""

import hashlib
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

# Suppress console window popup on Windows for subprocess calls
# Use kwargs dict because creationflags parameter only exists on Windows
_SUBPROCESS_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)

# Try to import platform-specific audio libraries
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False
    log.info("winsound not available (not Windows)")


# =============================================================================
# AUDIO HANDLER
# =============================================================================

class AudioHandler:
    """
    Handles WEM audio file conversion and playback.

    Uses vgmstream-cli for WEM to WAV conversion.
    Uses winsound (Windows) for synchronous playback in a background thread.
    Thread-safe with generation counters to prevent stale state clobbering.
    """

    def __init__(self, vgmstream_path: Optional[Path] = None):
        self._vgmstream_path = vgmstream_path
        self._current_wav: Optional[Path] = None
        self._is_playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._play_generation = 0  # Prevents stale thread callbacks
        self._duration_cache: dict = {}

        # Create temp directory safely
        try:
            self._temp_dir = Path(tempfile.gettempdir()) / "mapdatagenerator_audio"
            self._temp_dir.mkdir(exist_ok=True)
        except OSError as e:
            log.error("Cannot create temp directory: %s", e)
            self._temp_dir = Path(tempfile.gettempdir())

        # Try to find vgmstream-cli if not specified
        if not self._vgmstream_path:
            self._vgmstream_path = self._find_vgmstream()

        if self._vgmstream_path and self._vgmstream_path.exists():
            log.info("vgmstream-cli found: %s", self._vgmstream_path)
        else:
            log.warning(
                "vgmstream-cli not found. Place vgmstream-cli.exe in the tools/ "
                "folder to enable audio playback."
            )

    def _find_vgmstream(self) -> Optional[Path]:
        """Find vgmstream-cli executable."""
        module_dir = Path(__file__).parent.parent
        candidates = [
            module_dir / "tools" / "vgmstream-cli.exe",
            module_dir / "tools" / "vgmstream-cli",
            module_dir / "vgmstream-cli.exe",
            module_dir / "vgmstream-cli",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        import shutil
        system_path = shutil.which("vgmstream-cli") or shutil.which("vgmstream-cli.exe")
        if system_path:
            return Path(system_path)

        return None

    @property
    def is_available(self) -> bool:
        """Check if audio playback is available."""
        return (
            self._vgmstream_path is not None
            and self._vgmstream_path.exists()
            and HAS_WINSOUND
        )

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_playing

    def convert_wem_to_wav(self, wem_path: Path, force: bool = False) -> Optional[Path]:
        """
        Convert WEM file to temporary WAV file.
        Uses path-hashed filenames to avoid collisions between different
        source directories with same-named files.
        """
        if not self._vgmstream_path or not self._vgmstream_path.exists():
            log.error("vgmstream-cli not available")
            return None

        if not wem_path.exists():
            log.error("WEM file not found: %s", wem_path)
            return None

        # Hash the full path to avoid filename collisions across directories
        path_hash = hashlib.md5(str(wem_path).encode()).hexdigest()[:8]
        wav_name = f"{wem_path.stem}_{path_hash}.wav"
        wav_path = self._temp_dir / wav_name

        # Check if already converted (cache hit)
        if not force and wav_path.exists():
            try:
                if wav_path.stat().st_mtime >= wem_path.stat().st_mtime:
                    log.debug("Using cached WAV: %s", wav_path)
                    return wav_path
            except OSError:
                pass  # File disappeared between check and stat

        # Convert using vgmstream-cli
        try:
            cmd = [
                str(self._vgmstream_path),
                "-o", str(wav_path),
                str(wem_path)
            ]

            log.debug("Running: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                **_SUBPROCESS_KWARGS,
            )

            if result.returncode != 0:
                log.error("vgmstream-cli failed: %s", result.stderr)
                return None

            if wav_path.exists():
                log.info("Converted: %s -> %s", wem_path.name, wav_path.name)
                return wav_path
            else:
                log.error("WAV not created: %s", wav_path)
                return None

        except subprocess.TimeoutExpired:
            log.error("vgmstream-cli timed out (file may be too large)")
            return None
        except Exception as e:
            log.exception("Conversion failed: %s", e)
            return None

    def play(
        self,
        wem_path: Path,
        on_complete: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Play WEM audio file in a background thread.
        Conversion and playback both happen off the main thread.
        Uses synchronous winsound in the thread for accurate completion detection.
        """
        if not HAS_WINSOUND:
            log.error("winsound not available")
            return False

        # Stop any current playback and wait for thread to finish
        self.stop()

        with self._lock:
            self._play_generation += 1
            gen = self._play_generation
            self._is_playing = True
            self._stop_event.clear()

        def play_thread():
            try:
                # Convert WEM to WAV (off main thread!)
                wav_path = self.convert_wem_to_wav(wem_path)
                if not wav_path:
                    return

                # Check if we were stopped during conversion
                if self._stop_event.is_set():
                    return

                self._current_wav = wav_path

                # Synchronous playback - blocks until audio finishes
                # This gives us accurate completion without duration guessing
                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)

            except Exception as e:
                if not self._stop_event.is_set():
                    log.exception("Playback error: %s", e)
            finally:
                with self._lock:
                    # Only update state if this is still the current generation
                    if gen == self._play_generation:
                        self._is_playing = False
                        self._current_wav = None
                if on_complete and not self._stop_event.is_set() and gen == self._play_generation:
                    on_complete()

        self._play_thread = threading.Thread(target=play_thread, daemon=True)
        self._play_thread.start()

        log.info("Playing: %s", wem_path.name)
        return True

    def stop(self) -> None:
        """Stop current audio playback and wait for thread cleanup."""
        self._stop_event.set()

        if HAS_WINSOUND and self._is_playing:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception as e:
                log.debug("Stop error: %s", e)

        # Wait for play thread to finish to prevent stale callbacks
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2.0)

        with self._lock:
            self._is_playing = False
            self._current_wav = None

    def get_duration(self, wem_path: Path) -> Optional[float]:
        """
        Get audio duration in seconds. Results are cached by file path.
        Thread-safe — can be called from any thread.
        """
        if not self._vgmstream_path or not self._vgmstream_path.exists():
            return None

        cache_key = str(wem_path)
        if cache_key in self._duration_cache:
            return self._duration_cache[cache_key]

        try:
            cmd = [
                str(self._vgmstream_path),
                "-m",
                str(wem_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                **_SUBPROCESS_KWARGS,
            )

            if result.returncode != 0:
                return None

            output = result.stdout
            samples = None
            sample_rate = None

            for line in output.split('\n'):
                line_lower = line.lower()
                if 'sample rate' in line_lower:
                    match = re.search(r'(\d+)', line)
                    if match:
                        sample_rate = int(match.group(1))
                elif 'total samples' in line_lower or 'stream total' in line_lower:
                    match = re.search(r'(\d+)', line)
                    if match:
                        samples = int(match.group(1))

            if samples and sample_rate:
                duration = samples / sample_rate
                self._duration_cache[cache_key] = duration
                return duration

            return None

        except Exception as e:
            log.debug("Duration check failed: %s", e)
            return None

    def cleanup_temp_files(self) -> int:
        """Clean up temporary WAV files."""
        self.stop()  # Stop playback before cleanup
        count = 0
        try:
            for wav_file in self._temp_dir.glob("*.wav"):
                try:
                    wav_file.unlink()
                    count += 1
                except Exception:
                    pass
        except Exception as e:
            log.debug("Cleanup error: %s", e)
        return count

    def shutdown(self) -> None:
        """Clean shutdown — stop playback and clean temp files."""
        self.stop()
        self.cleanup_temp_files()

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
