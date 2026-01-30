"""
Audio Handler Module

Handles WEM audio file playback:
- Converts WEM to WAV using vgmstream-cli
- Plays WAV audio using platform-appropriate method
- Manages temporary files and playback state
"""

import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

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
    Uses winsound (Windows) for playback.
    """

    def __init__(self, vgmstream_path: Optional[Path] = None):
        """
        Initialize audio handler.

        Args:
            vgmstream_path: Path to vgmstream-cli.exe. If not provided,
                           looks in tools/ folder next to this module.
        """
        self._vgmstream_path = vgmstream_path
        self._temp_dir = Path(tempfile.gettempdir()) / "mapdatagenerator_audio"
        self._temp_dir.mkdir(exist_ok=True)

        self._current_wav: Optional[Path] = None
        self._is_playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._duration_cache: dict = {}  # Cache durations

        # Try to find vgmstream-cli if not specified
        if not self._vgmstream_path:
            self._vgmstream_path = self._find_vgmstream()

        if self._vgmstream_path and self._vgmstream_path.exists():
            log.info("vgmstream-cli found: %s", self._vgmstream_path)
        else:
            log.warning("vgmstream-cli not found. Audio playback will not work.")

    def _find_vgmstream(self) -> Optional[Path]:
        """Find vgmstream-cli executable."""
        # Look in tools/ folder relative to this module
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

        # Try system PATH
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

        Args:
            wem_path: Path to WEM file
            force: Force reconversion even if WAV exists

        Returns:
            Path to temporary WAV file, or None on failure
        """
        if not self._vgmstream_path or not self._vgmstream_path.exists():
            log.error("vgmstream-cli not available")
            return None

        if not wem_path.exists():
            log.error("WEM file not found: %s", wem_path)
            return None

        # Create output path in temp directory
        wav_name = wem_path.stem + ".wav"
        wav_path = self._temp_dir / wav_name

        # Check if already converted (cache hit)
        if not force and wav_path.exists():
            # Verify the cached file is newer than source
            if wav_path.stat().st_mtime >= wem_path.stat().st_mtime:
                log.debug("Using cached WAV: %s", wav_path)
                return wav_path

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
                timeout=30
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
            log.error("vgmstream-cli timed out")
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
        Play WEM audio file.

        Args:
            wem_path: Path to WEM file
            on_complete: Optional callback when playback finishes

        Returns:
            True if playback started, False on failure
        """
        if not HAS_WINSOUND:
            log.error("winsound not available")
            return False

        # Stop any current playback
        self.stop()

        # Convert WEM to WAV
        wav_path = self.convert_wem_to_wav(wem_path)
        if not wav_path:
            return False

        self._current_wav = wav_path
        self._is_playing = True
        self._stop_event.clear()

        # Play in background thread to avoid blocking
        def play_thread():
            stopped_early = False
            try:
                winsound.PlaySound(
                    str(wav_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                # Wait for duration OR stop signal
                duration = self.get_duration(wem_path)
                stopped_early = self._stop_event.wait(timeout=duration if duration else 5.0)

            except Exception as e:
                log.exception("Playback error: %s", e)
            finally:
                self._is_playing = False
                # Only call on_complete if not stopped early
                if on_complete and not stopped_early:
                    on_complete()

        self._play_thread = threading.Thread(target=play_thread, daemon=True)
        self._play_thread.start()

        log.info("Playing: %s", wem_path.name)
        return True

    def play_sync(self, wem_path: Path) -> bool:
        """
        Play WEM audio file synchronously (blocking).

        Args:
            wem_path: Path to WEM file

        Returns:
            True if playback completed, False on failure
        """
        if not HAS_WINSOUND:
            log.error("winsound not available")
            return False

        # Convert WEM to WAV
        wav_path = self.convert_wem_to_wav(wem_path)
        if not wav_path:
            return False

        try:
            self._is_playing = True
            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
            return True
        except Exception as e:
            log.exception("Playback error: %s", e)
            return False
        finally:
            self._is_playing = False

    def stop(self) -> None:
        """Stop current audio playback."""
        # Signal the play thread to exit early
        self._stop_event.set()

        if HAS_WINSOUND and self._is_playing:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception as e:
                log.debug("Stop error: %s", e)

        self._is_playing = False
        self._current_wav = None

    def get_duration(self, wem_path: Path) -> Optional[float]:
        """
        Get audio duration in seconds.

        Args:
            wem_path: Path to WEM file

        Returns:
            Duration in seconds, or None if unknown
        """
        if not self._vgmstream_path or not self._vgmstream_path.exists():
            return None

        try:
            # Use vgmstream-cli -m (metadata) to get duration
            cmd = [
                str(self._vgmstream_path),
                "-m",
                str(wem_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            # Parse output for duration
            # Format varies, look for "stream total samples" and "sample rate"
            output = result.stdout
            samples = None
            sample_rate = None

            for line in output.split('\n'):
                line_lower = line.lower()
                if 'sample rate' in line_lower:
                    # Extract number
                    match = re.search(r'(\d+)', line)
                    if match:
                        sample_rate = int(match.group(1))
                elif 'total samples' in line_lower or 'stream total' in line_lower:
                    match = re.search(r'(\d+)', line)
                    if match:
                        samples = int(match.group(1))

            if samples and sample_rate:
                return samples / sample_rate

            return None

        except Exception as e:
            log.debug("Duration check failed: %s", e)
            return None

    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary WAV files.

        Returns:
            Number of files deleted
        """
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

    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
        # Don't auto-cleanup temp files - might still be playing
