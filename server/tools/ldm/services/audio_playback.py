"""
Audio Playback Service — MDG AudioHandler port for LocaNext.

Exact port of MapDataGenerator/core/audio_handler.py:
- WEM → WAV conversion via vgmstream-cli (reuses MediaConverter)
- winsound.PlaySound() for synchronous playback in background thread
- Generation counter prevents stale thread callbacks
- Thread-safe stop via SND_PURGE + thread join

On Linux (DEV mode): winsound unavailable, play() returns False.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from server.tools.ldm.services.media_converter import get_media_converter
from server.tools.ldm.services.perforce_path_service import convert_to_wsl_path

# Suppress console window popup on Windows for subprocess calls
_SUBPROCESS_KWARGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
)

# Platform-specific audio — MDG: try import winsound
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False
    logger.info("[AudioPlayback] winsound not available (not Windows / DEV mode)")


class AudioPlaybackService:
    """
    MDG AudioHandler port — plays WAV audio via winsound on Windows.

    Thread-safe. Generation counter prevents stale callbacks.
    """

    def __init__(self) -> None:
        self._is_playing = False
        self._current_event: Optional[str] = None
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._play_generation = 0
        self._play_start_time: Optional[float] = None
        self._duration: Optional[float] = None
        self._duration_cache: dict = {}

    @property
    def is_available(self) -> bool:
        """Check if audio playback is available (Windows + vgmstream)."""
        converter = get_media_converter()
        return HAS_WINSOUND and converter._find_vgmstream() is not None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_event(self) -> Optional[str]:
        return self._current_event

    def get_status(self) -> dict:
        """Get current playback status for frontend polling."""
        elapsed = 0.0
        if self._is_playing and self._play_start_time:
            elapsed = time.time() - self._play_start_time
        return {
            "is_playing": self._is_playing,
            "current_event": self._current_event,
            "elapsed": round(elapsed, 1),
            "duration": self._duration,
        }

    def play(self, event_name: str, language: str = "eng") -> dict:
        """
        Play audio for an event. MDG-exact: convert WEM→WAV, winsound in thread.

        Returns status dict: {success, message, event_name}
        """
        if not HAS_WINSOUND:
            return {"success": False, "message": "winsound not available (not Windows)", "event_name": event_name}

        # Look up WEM path from MegaIndex
        from server.tools.ldm.services.mega_index import get_mega_index
        mega = get_mega_index()
        wem_path = mega.get_audio_path_by_event_for_lang(event_name, language)

        if wem_path is None:
            return {"success": False, "message": f"No audio file for '{event_name}' in '{language}'", "event_name": event_name}

        logger.info("[AudioPlayback] WEM lookup: event={}, lang={}, path={}", event_name, language, wem_path)

        # Convert Windows path to WSL path if needed
        if sys.platform != "win32":
            wem_path_str = convert_to_wsl_path(str(wem_path))
            wem_path = Path(wem_path_str)

        # Verify WEM file exists before attempting conversion
        if not wem_path.exists():
            logger.error("[AudioPlayback] WEM file NOT FOUND: {}", wem_path)
            return {"success": False, "message": f"WEM file not found: {wem_path}", "event_name": event_name}

        # Stop any current playback first (MDG: self.stop() at start of play())
        self.stop()

        with self._lock:
            self._play_generation += 1
            gen = self._play_generation
            self._is_playing = True
            self._current_event = event_name
            self._stop_event.clear()
            self._play_start_time = None
            self._duration = None

        def play_thread():
            try:
                # Convert WEM → WAV (MDG: off main thread)
                converter = get_media_converter()
                wav_path = converter.convert_wem_to_wav(wem_path)
                if not wav_path:
                    logger.error("[AudioPlayback] WEM→WAV conversion failed: {}", wem_path)
                    return

                # Validate WAV file exists and is non-empty
                if not wav_path.exists():
                    logger.error("[AudioPlayback] WAV file does not exist after conversion: {}", wav_path)
                    return

                wav_size = wav_path.stat().st_size
                if wav_size < 44:  # WAV header is 44 bytes minimum
                    logger.error("[AudioPlayback] WAV file too small ({}B), likely corrupt: {}", wav_size, wav_path)
                    # Delete corrupt cache entry so next attempt re-converts
                    try:
                        wav_path.unlink()
                    except OSError:
                        pass
                    return

                # Check if stopped during conversion (MDG: self._stop_event.is_set())
                if self._stop_event.is_set():
                    return

                # Get duration for status (MDG: async duration fetch)
                self._duration = self._get_duration_from_wav(wav_path)
                self._play_start_time = time.time()

                logger.info(
                    "[AudioPlayback] Playing: {} → {} ({}B, {:.1f}s)",
                    event_name, wav_path.name, wav_size,
                    self._duration or 0.0,
                )

                # MDG-exact: synchronous winsound.PlaySound — blocks until audio finishes
                # SND_NODEFAULT prevents Windows from playing the system default sound
                # when the WAV file can't be read/decoded
                winsound.PlaySound(
                    str(wav_path),
                    winsound.SND_FILENAME | winsound.SND_NODEFAULT,
                )

            except Exception as e:
                if not self._stop_event.is_set():
                    logger.exception("[AudioPlayback] Playback error: {}", e)
            finally:
                with self._lock:
                    # MDG: only update if still current generation
                    if gen == self._play_generation:
                        self._is_playing = False
                        self._current_event = None
                        self._play_start_time = None

        self._play_thread = threading.Thread(target=play_thread, daemon=True)
        self._play_thread.start()

        return {"success": True, "message": "Playing", "event_name": event_name}

    def stop(self) -> dict:
        """Stop playback. MDG-exact: SND_PURGE + thread join."""
        self._stop_event.set()

        if HAS_WINSOUND and self._is_playing:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception as e:
                logger.debug("[AudioPlayback] Stop error: {}", e)

        # MDG: wait for thread to finish
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2.0)

        with self._lock:
            self._is_playing = False
            self._current_event = None
            self._play_start_time = None

        return {"success": True, "message": "Stopped"}

    def _get_duration_from_wav(self, wav_path: Path) -> Optional[float]:
        """Get WAV duration by reading headers. Fast, no subprocess needed."""
        cache_key = str(wav_path)
        if cache_key in self._duration_cache:
            return self._duration_cache[cache_key]

        try:
            import wave
            with wave.open(str(wav_path), 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                if rate > 0:
                    dur = frames / rate
                    self._duration_cache[cache_key] = dur
                    return dur
        except Exception:
            pass
        return None

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.stop()


# Singleton
_instance: Optional[AudioPlaybackService] = None


def get_audio_playback() -> AudioPlaybackService:
    global _instance
    if _instance is None:
        _instance = AudioPlaybackService()
    return _instance
