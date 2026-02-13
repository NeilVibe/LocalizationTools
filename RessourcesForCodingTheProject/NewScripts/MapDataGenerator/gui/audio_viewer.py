"""
Audio Viewer Module

Display panel for audio playback in AUDIO mode:
- Event name header
- KOR script (primary, larger area)
- ENG script (reference, smaller area)
- Play/Stop controls with unicode icons and progress bar
- Auto-play toggle, Prev/Next navigation
- Async duration fetching (never blocks main thread)
- Clean empty state
"""

import logging
import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable, Optional

# Ensure parent directory is in sys.path for PyInstaller compatibility
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_ui_text
from core.audio_handler import AudioHandler


log = logging.getLogger(__name__)


class AudioViewer(ttk.Frame):
    """
    Audio viewer panel for AUDIO mode.

    Layout:
    +---------------------------------------------+
    | Event: narrator_quest_001          Dur: 3.2s |
    +---------------------------------------------+
    | KOR Script (primary, 60% height):            |
    | +------------------------------------------+ |
    | | 안녕하세요. 이 퀘스트를 시작하려면...        | |
    | +------------------------------------------+ |
    +---------------------------------------------+
    | ENG Script (reference, 40% height):          |
    | +------------------------------------------+ |
    | | Hello. To start this quest...             | |
    | +------------------------------------------+ |
    +---------------------------------------------+
    | [< Prev] [> Play] [# Stop] [Next >]  [Loop] |
    | [=========>          ] 1.2s / 3.2s  AutoPlay |
    +---------------------------------------------+
    """

    def __init__(
        self,
        parent: tk.Widget,
        audio_handler: Optional[AudioHandler] = None,
        on_play: Optional[Callable[[Path], None]] = None,
        on_prev: Optional[Callable[[], None]] = None,
        on_next: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)

        self._audio_handler = audio_handler or AudioHandler()
        self._on_play = on_play
        self._on_prev = on_prev
        self._on_next = on_next

        self._current_wem: Optional[Path] = None
        self._current_event: str = ""
        self._current_script_kor: str = ""
        self._current_script_eng: str = ""
        self._duration: Optional[float] = None
        self._generation = 0  # Prevents stale async duration updates
        self._progress_after_id: Optional[str] = None
        self._play_start_time: Optional[float] = None
        self._auto_play = False

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create viewer widgets."""
        self.columnconfigure(0, weight=1)
        # KOR gets more space (primary), ENG less (reference)
        self.rowconfigure(2, weight=3)  # KOR Script
        self.rowconfigure(3, weight=2)  # ENG Script

        # === Header with event name and duration ===
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        header_frame.columnconfigure(1, weight=1)

        self._header_label = ttk.Label(
            header_frame,
            text=get_ui_text('audio_player'),
            font=('TkDefaultFont', 12, 'bold')
        )
        self._header_label.grid(row=0, column=0, sticky="w")

        # Availability warning
        if not self._audio_handler.is_available:
            warn_label = ttk.Label(
                header_frame,
                text="(vgmstream-cli not found — place in tools/ folder)",
                foreground="red",
                font=('TkDefaultFont', 9)
            )
            warn_label.grid(row=0, column=1, sticky="e")

        # === Event name section ===
        event_frame = ttk.LabelFrame(self, text=get_ui_text('event_name'))
        event_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(6, 4))

        event_inner = ttk.Frame(event_frame)
        event_inner.pack(fill="x", padx=10, pady=8)
        event_inner.columnconfigure(0, weight=1)

        self._event_label = ttk.Label(
            event_inner,
            text="",
            font=('Malgun Gothic', 12, 'bold'),
            foreground="#555"
        )
        self._event_label.grid(row=0, column=0, sticky="w")

        self._duration_label = ttk.Label(
            event_inner,
            text="",
            foreground="#888",
            font=('TkDefaultFont', 10)
        )
        self._duration_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # === KOR Script section (primary — warm cream background) ===
        kor_frame = ttk.LabelFrame(self, text=get_ui_text('script_line') + " (KOR)")
        kor_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 3))
        kor_frame.columnconfigure(0, weight=1)
        kor_frame.rowconfigure(0, weight=1)

        kor_text_frame = ttk.Frame(kor_frame)
        kor_text_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        kor_text_frame.columnconfigure(0, weight=1)
        kor_text_frame.rowconfigure(0, weight=1)

        self._kor_text = tk.Text(
            kor_text_frame,
            wrap="word",
            font=('Malgun Gothic', 12),
            height=6,
            state="disabled",
            relief="flat",
            padx=12,
            pady=10,
            background="#FFF8F0",  # Warm ivory — primary content
            foreground="#1a1a1a",
            highlightthickness=1,
            highlightbackground="#e0d8d0",
            highlightcolor="#c8bfb5",
            spacing1=3,
            spacing2=1,
            spacing3=3,
        )
        self._kor_text.grid(row=0, column=0, sticky="nsew")

        kor_scroll = ttk.Scrollbar(kor_text_frame, orient="vertical", command=self._kor_text.yview)
        kor_scroll.grid(row=0, column=1, sticky="ns")
        self._kor_text.configure(yscrollcommand=kor_scroll.set)

        # === ENG Script section (reference — cool blue-gray background) ===
        eng_frame = ttk.LabelFrame(self, text=get_ui_text('script_line') + " (ENG)")
        eng_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(3, 4))
        eng_frame.columnconfigure(0, weight=1)
        eng_frame.rowconfigure(0, weight=1)

        eng_text_frame = ttk.Frame(eng_frame)
        eng_text_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        eng_text_frame.columnconfigure(0, weight=1)
        eng_text_frame.rowconfigure(0, weight=1)

        self._eng_text = tk.Text(
            eng_text_frame,
            wrap="word",
            font=('Malgun Gothic', 11),
            height=4,
            state="disabled",
            relief="flat",
            padx=12,
            pady=10,
            background="#F0F5FF",  # Cool blue-gray — reference content
            foreground="#333333",
            highlightthickness=1,
            highlightbackground="#d0d8e0",
            highlightcolor="#b5bfc8",
            spacing1=2,
            spacing2=1,
            spacing3=2,
        )
        self._eng_text.grid(row=0, column=0, sticky="nsew")

        eng_scroll = ttk.Scrollbar(eng_text_frame, orient="vertical", command=self._eng_text.yview)
        eng_scroll.grid(row=0, column=1, sticky="ns")
        self._eng_text.configure(yscrollcommand=eng_scroll.set)

        # === Separator ===
        ttk.Separator(self, orient="horizontal").grid(
            row=4, column=0, sticky="ew", padx=12, pady=(6, 0)
        )

        # === Control section (row 1: buttons, row 2: progress) ===
        control_frame = ttk.Frame(self)
        control_frame.grid(row=5, column=0, sticky="ew", padx=12, pady=(8, 4))

        # Prev button
        self._prev_btn = ttk.Button(
            control_frame,
            text="\u25C0  Prev",
            command=self._on_prev_click,
            width=8,
        )
        self._prev_btn.pack(side="left", padx=(0, 4))

        # Play button (prominent)
        self._play_btn = ttk.Button(
            control_frame,
            text="\u25B6  Play",
            command=self._on_play_click,
            state="disabled",
            width=8,
        )
        self._play_btn.pack(side="left", padx=4)

        # Stop button
        self._stop_btn = ttk.Button(
            control_frame,
            text="\u25A0  Stop",
            command=self._on_stop_click,
            state="disabled",
            width=8,
        )
        self._stop_btn.pack(side="left", padx=4)

        # Next button
        self._next_btn = ttk.Button(
            control_frame,
            text="Next  \u25B6",
            command=self._on_next_click,
            width=8,
        )
        self._next_btn.pack(side="left", padx=(4, 0))

        # Separator between nav/play and utility controls
        ttk.Separator(control_frame, orient="vertical").pack(
            side="left", fill="y", padx=12, pady=2
        )

        # Auto-play toggle
        self._auto_play_var = tk.BooleanVar(value=False)
        self._auto_play_check = ttk.Checkbutton(
            control_frame,
            text="Auto-play",
            variable=self._auto_play_var,
            command=self._on_auto_play_toggle,
        )
        self._auto_play_check.pack(side="left", padx=6)

        # Cleanup button
        self._cleanup_btn = ttk.Button(
            control_frame,
            text="Cleanup cache",
            command=self._on_cleanup_click,
        )
        self._cleanup_btn.pack(side="right", padx=4)

        # === Progress bar row ===
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=6, column=0, sticky="ew", padx=12, pady=(2, 4))
        progress_frame.columnconfigure(0, weight=1)

        self._playback_progress = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100,
        )
        self._playback_progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Status / elapsed label
        self._status_label = ttk.Label(
            progress_frame,
            text="",
            foreground="#888",
            font=('TkDefaultFont', 9),
            width=20,
            anchor="e",
        )
        self._status_label.grid(row=0, column=1, sticky="e")

        # === File info row ===
        self._path_label = ttk.Label(
            self,
            text="",
            foreground="#aaa",
            font=('TkDefaultFont', 9),
        )
        self._path_label.grid(row=7, column=0, sticky="w", padx=14, pady=(0, 6))

        # === Empty state overlay ===
        self._empty_frame = ttk.Frame(self)
        self._empty_label = ttk.Label(
            self._empty_frame,
            text="Select an audio entry from the list\nto view scripts and play audio",
            foreground="#999",
            font=('TkDefaultFont', 11),
            justify="center",
        )
        self._empty_label.pack(expand=True)
        # Show empty state initially
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        """Show the empty state overlay."""
        self._empty_frame.grid(row=0, column=0, rowspan=8, sticky="nsew")
        self._empty_frame.lift()

    def _hide_empty_state(self) -> None:
        """Hide the empty state overlay."""
        self._empty_frame.grid_forget()

    def set_audio(
        self,
        wem_path: Optional[Path],
        event_name: str = "",
        script_line: str = "",
        script_kor: str = "",
        script_eng: str = ""
    ) -> None:
        """
        Set the audio to display/play. Duration is fetched asynchronously.
        """
        self._current_wem = wem_path
        self._current_event = event_name
        self._current_script_kor = script_kor if script_kor else script_line
        self._current_script_eng = script_eng

        # Increment generation to invalidate any pending async operations
        self._generation += 1
        gen = self._generation

        if not wem_path and not event_name:
            self._show_empty_state()
            return

        self._hide_empty_state()

        # Update event label
        if event_name:
            self._event_label.config(text=event_name, foreground="#222")
        else:
            self._event_label.config(text="(No event)", foreground="#999")

        # Update KOR script text
        self._kor_text.config(state="normal")
        self._kor_text.delete("1.0", "end")
        if self._current_script_kor:
            self._kor_text.insert("1.0", self._current_script_kor)
        self._kor_text.config(state="disabled")

        # Update ENG script text
        self._eng_text.config(state="normal")
        self._eng_text.delete("1.0", "end")
        if self._current_script_eng:
            self._eng_text.insert("1.0", self._current_script_eng)
        self._eng_text.config(state="disabled")

        # File info — just the filename, not the full path
        if wem_path:
            self._path_label.config(text=f"File: {wem_path.name}")
        else:
            self._path_label.config(text="")

        # Update controls
        can_play = wem_path is not None and wem_path.exists() and self._audio_handler.is_available
        self._play_btn.config(state="normal" if can_play else "disabled")
        self._stop_btn.config(state="disabled")

        # Reset progress
        self._playback_progress['value'] = 0
        self._status_label.config(text="")
        self._stop_progress_updates()

        # Fetch duration asynchronously (never block main thread)
        self._duration = None
        self._duration_label.config(text="")
        if wem_path and wem_path.exists():
            self._duration_label.config(text="...")
            def _fetch_duration(path=wem_path, expected_gen=gen):
                dur = self._audio_handler.get_duration(path)
                if expected_gen != self._generation:
                    return  # Stale — user already selected another row
                if dur is not None:
                    self._duration = dur
                    self.after(0, lambda: self._duration_label.config(
                        text=f"{dur:.1f}s") if self._generation == expected_gen else None)
                else:
                    self.after(0, lambda: self._duration_label.config(
                        text="") if self._generation == expected_gen else None)
            threading.Thread(target=_fetch_duration, daemon=True).start()

        # Auto-play if enabled
        if self._auto_play and can_play:
            self.after(50, self._on_play_click)

    def clear(self) -> None:
        """Clear the display and stop playback."""
        self._stop_progress_updates()
        self.set_audio(None, "", "")

    def _on_play_click(self) -> None:
        """Handle play button click."""
        if not self._current_wem or not self._current_wem.exists():
            return

        if not self._audio_handler.is_available:
            self._status_label.config(text="vgmstream not found", foreground="red")
            return

        # Update button states
        self._play_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status_label.config(text="Converting...", foreground="#4a9")

        # Callback
        if self._on_play:
            self._on_play(self._current_wem)

        # Track playback start for progress
        import time
        self._play_start_time = time.time()

        def on_complete():
            self.after(0, self._on_playback_complete)

        success = self._audio_handler.play(self._current_wem, on_complete)
        if success:
            # Start progress updates
            self._start_progress_updates()
        else:
            self._play_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
            self._status_label.config(text="Playback failed", foreground="red")
            self.after(3000, self._auto_clear_status)

    def _on_playback_complete(self) -> None:
        """Handle playback completion (called from main thread)."""
        self._play_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._stop_progress_updates()
        self._playback_progress['value'] = 100
        self._status_label.config(text="", foreground="#888")

    def _on_stop_click(self) -> None:
        """Handle stop button click."""
        self._audio_handler.stop()
        self._play_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._stop_progress_updates()
        self._playback_progress['value'] = 0
        self._status_label.config(text="Stopped", foreground="#888")
        self.after(2000, self._auto_clear_status)

    def _on_prev_click(self) -> None:
        """Handle prev button click."""
        if self._on_prev:
            self._on_prev()

    def _on_next_click(self) -> None:
        """Handle next button click."""
        if self._on_next:
            self._on_next()

    def _on_auto_play_toggle(self) -> None:
        """Handle auto-play toggle."""
        self._auto_play = self._auto_play_var.get()

    def _on_cleanup_click(self) -> None:
        """Handle cleanup button click — show result in status, not modal."""
        count = self._audio_handler.cleanup_temp_files()
        self._status_label.config(
            text=f"Cleaned {count} cached files",
            foreground="#666"
        )
        self.after(3000, self._auto_clear_status)

    def _auto_clear_status(self) -> None:
        """Auto-clear stale status messages."""
        text = self._status_label.cget("text")
        if text in ("Stopped", "Playback failed", "") or text.startswith("Cleaned"):
            self._status_label.config(text="", foreground="#888")

    # === Progress bar updates ===

    def _start_progress_updates(self) -> None:
        """Start periodic progress bar updates during playback."""
        self._stop_progress_updates()
        self._update_playback_progress()

    def _stop_progress_updates(self) -> None:
        """Stop periodic progress bar updates."""
        if self._progress_after_id:
            self.after_cancel(self._progress_after_id)
            self._progress_after_id = None

    def _update_playback_progress(self) -> None:
        """Update progress bar based on elapsed time."""
        import time
        if not self._audio_handler.is_playing or not self._play_start_time:
            return

        elapsed = time.time() - self._play_start_time

        if self._duration and self._duration > 0:
            pct = min(100, (elapsed / self._duration) * 100)
            self._playback_progress['value'] = pct
            self._status_label.config(
                text=f"{elapsed:.1f}s / {self._duration:.1f}s",
                foreground="#4a9"
            )
        else:
            # No duration known — show elapsed only with indeterminate feel
            self._status_label.config(
                text=f"Playing... {elapsed:.1f}s",
                foreground="#4a9"
            )

        self._progress_after_id = self.after(100, self._update_playback_progress)

    # === Public API ===

    def set_audio_handler(self, handler: AudioHandler) -> None:
        """Set the audio handler."""
        self._audio_handler = handler

    def set_navigation_callbacks(
        self,
        on_prev: Optional[Callable[[], None]] = None,
        on_next: Optional[Callable[[], None]] = None
    ) -> None:
        """Set prev/next navigation callbacks."""
        self._on_prev = on_prev
        self._on_next = on_next

    def play(self) -> bool:
        """Start playback. Returns True if playback started."""
        if not self._current_wem or not self._audio_handler.is_available:
            return False
        self._on_play_click()
        return True

    def toggle_playback(self) -> None:
        """Toggle between play and stop (for keyboard shortcut)."""
        if self._audio_handler.is_playing:
            self._on_stop_click()
        elif self._current_wem and self._audio_handler.is_available:
            self._on_play_click()

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._audio_handler.is_playing
