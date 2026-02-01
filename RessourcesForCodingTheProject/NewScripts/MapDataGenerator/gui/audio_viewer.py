"""
Audio Viewer Module

Display panel for audio playback in AUDIO mode:
- Shows event name
- Shows KOR script line (original)
- Shows ENG script line (translation)
- Play/Stop/Cleanup buttons with status
- Duration display
"""

import logging
import sys
import tkinter as tk
from tkinter import ttk, messagebox
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
    ┌─────────────────────────────────────────┐
    │ Event: narrator_quest_001               │
    ├─────────────────────────────────────────┤
    │ KOR Script:                             │
    │ ┌─────────────────────────────────────┐ │
    │ │ 안녕하세요. 이 퀘스트를 시작하려면... │ │
    │ └─────────────────────────────────────┘ │
    ├─────────────────────────────────────────┤
    │ ENG Script:                             │
    │ ┌─────────────────────────────────────┐ │
    │ │ Hello. To start this quest...       │ │
    │ └─────────────────────────────────────┘ │
    ├─────────────────────────────────────────┤
    │ [▶ Play] [⏹ Stop] [Cleanup]   Dur: 3.2s│
    └─────────────────────────────────────────┘
    """

    def __init__(
        self,
        parent: tk.Widget,
        audio_handler: Optional[AudioHandler] = None,
        on_play: Optional[Callable[[Path], None]] = None,
        **kwargs
    ):
        """
        Initialize audio viewer.

        Args:
            parent: Parent widget
            audio_handler: AudioHandler instance for playback
            on_play: Optional callback when play is clicked
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._audio_handler = audio_handler or AudioHandler()
        self._on_play = on_play

        self._current_wem: Optional[Path] = None
        self._current_event: str = ""
        self._current_script_kor: str = ""
        self._current_script_eng: str = ""
        self._duration: Optional[float] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create viewer widgets."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # KOR Script area expands
        self.rowconfigure(3, weight=1)  # ENG Script area expands

        # Header
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self._header_label = ttk.Label(
            header_frame,
            text=get_ui_text('audio_player'),
            font=('TkDefaultFont', 12, 'bold')
        )
        self._header_label.pack(side="left")

        # Availability status
        if not self._audio_handler.is_available:
            status_label = ttk.Label(
                header_frame,
                text="(vgmstream-cli not found)",
                foreground="red",
                font=('TkDefaultFont', 9)
            )
            status_label.pack(side="right")

        # Event name section
        event_frame = ttk.LabelFrame(self, text=get_ui_text('event_name'))
        event_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        self._event_label = ttk.Label(
            event_frame,
            text="(No audio selected)",
            font=('TkDefaultFont', 11),
            foreground="gray"
        )
        self._event_label.pack(anchor="w", padx=10, pady=8)

        # KOR Script section
        kor_frame = ttk.LabelFrame(self, text=get_ui_text('script_line') + " (KOR)")
        kor_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        kor_frame.columnconfigure(0, weight=1)
        kor_frame.rowconfigure(0, weight=1)

        kor_text_frame = ttk.Frame(kor_frame)
        kor_text_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        kor_text_frame.columnconfigure(0, weight=1)
        kor_text_frame.rowconfigure(0, weight=1)

        self._kor_text = tk.Text(
            kor_text_frame,
            wrap="word",
            font=('Malgun Gothic', 11),
            height=4,
            state="disabled",
            relief="flat",
            padx=10,
            pady=8,
            background="#f5f5f5"
        )
        self._kor_text.grid(row=0, column=0, sticky="nsew")

        kor_scroll = ttk.Scrollbar(kor_text_frame, orient="vertical", command=self._kor_text.yview)
        kor_scroll.grid(row=0, column=1, sticky="ns")
        self._kor_text.configure(yscrollcommand=kor_scroll.set)

        # ENG Script section
        eng_frame = ttk.LabelFrame(self, text=get_ui_text('script_line') + " (ENG)")
        eng_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)
        eng_frame.columnconfigure(0, weight=1)
        eng_frame.rowconfigure(0, weight=1)

        eng_text_frame = ttk.Frame(eng_frame)
        eng_text_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        eng_text_frame.columnconfigure(0, weight=1)
        eng_text_frame.rowconfigure(0, weight=1)

        self._eng_text = tk.Text(
            eng_text_frame,
            wrap="word",
            font=('TkDefaultFont', 11),
            height=4,
            state="disabled",
            relief="flat",
            padx=10,
            pady=8,
            background="#f0f0f0"
        )
        self._eng_text.grid(row=0, column=0, sticky="nsew")

        eng_scroll = ttk.Scrollbar(eng_text_frame, orient="vertical", command=self._eng_text.yview)
        eng_scroll.grid(row=0, column=1, sticky="ns")
        self._eng_text.configure(yscrollcommand=eng_scroll.set)

        # Control section
        control_frame = ttk.Frame(self)
        control_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)

        # Play button
        self._play_btn = ttk.Button(
            control_frame,
            text=f"  {get_ui_text('play')}  ",
            command=self._on_play_click,
            state="disabled"
        )
        self._play_btn.pack(side="left", padx=5)

        # Stop button
        self._stop_btn = ttk.Button(
            control_frame,
            text=f"  {get_ui_text('stop')}  ",
            command=self._on_stop_click,
            state="disabled"
        )
        self._stop_btn.pack(side="left", padx=5)

        # Cleanup button
        self._cleanup_btn = ttk.Button(
            control_frame,
            text=f"  {get_ui_text('cleanup')}  ",
            command=self._on_cleanup_click
        )
        self._cleanup_btn.pack(side="left", padx=15)

        # Status label
        self._status_label = ttk.Label(
            control_frame,
            text="",
            foreground="gray"
        )
        self._status_label.pack(side="left", padx=10)

        # Duration label
        self._duration_label = ttk.Label(
            control_frame,
            text="",
            foreground="gray"
        )
        self._duration_label.pack(side="right", padx=10)

        # File path label
        path_frame = ttk.Frame(self)
        path_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 10))

        self._path_label = ttk.Label(
            path_frame,
            text="",
            foreground="gray",
            font=('TkDefaultFont', 8)
        )
        self._path_label.pack(anchor="w")

    def set_audio(
        self,
        wem_path: Optional[Path],
        event_name: str = "",
        script_line: str = "",
        script_kor: str = "",
        script_eng: str = ""
    ) -> None:
        """
        Set the audio to display/play.

        Args:
            wem_path: Path to WEM file
            event_name: Event name to display
            script_line: Script line text (legacy, uses as KOR if script_kor not provided)
            script_kor: Korean script text
            script_eng: English script text
        """
        self._current_wem = wem_path
        self._current_event = event_name
        self._current_script_kor = script_kor if script_kor else script_line
        self._current_script_eng = script_eng

        # Update event label
        if event_name:
            self._event_label.config(text=event_name, foreground="black")
        else:
            self._event_label.config(text="(No audio selected)", foreground="gray")

        # Update KOR script text
        self._kor_text.config(state="normal")
        self._kor_text.delete("1.0", "end")
        if self._current_script_kor:
            self._kor_text.insert("1.0", self._current_script_kor)
        else:
            self._kor_text.insert("1.0", "(No KOR script)")
        self._kor_text.config(state="disabled")

        # Update ENG script text
        self._eng_text.config(state="normal")
        self._eng_text.delete("1.0", "end")
        if self._current_script_eng:
            self._eng_text.insert("1.0", self._current_script_eng)
        else:
            self._eng_text.insert("1.0", "(No ENG script)")
        self._eng_text.config(state="disabled")

        # Update path
        if wem_path:
            self._path_label.config(text=str(wem_path))
        else:
            self._path_label.config(text="")

        # Update controls
        can_play = wem_path is not None and wem_path.exists() and self._audio_handler.is_available
        self._play_btn.config(state="normal" if can_play else "disabled")
        self._stop_btn.config(state="disabled")

        # Get duration (async would be better, but sync for now)
        if wem_path and wem_path.exists():
            self._duration = self._audio_handler.get_duration(wem_path)
            if self._duration:
                self._duration_label.config(text=f"{get_ui_text('duration')}: {self._duration:.1f}s")
            else:
                self._duration_label.config(text="")
        else:
            self._duration = None
            self._duration_label.config(text="")

        self._status_label.config(text="")

    def clear(self) -> None:
        """Clear the display."""
        self.set_audio(None, "", "")

    def _on_play_click(self) -> None:
        """Handle play button click."""
        if not self._current_wem or not self._current_wem.exists():
            return

        if not self._audio_handler.is_available:
            self._status_label.config(text="vgmstream-cli not found", foreground="red")
            return

        # Disable play, enable stop
        self._play_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status_label.config(text="Playing...", foreground="green")

        # Callback
        if self._on_play:
            self._on_play(self._current_wem)

        # Play audio
        def on_complete():
            # Re-enable play button
            self.after(0, lambda: self._play_btn.config(state="normal"))
            self.after(0, lambda: self._stop_btn.config(state="disabled"))
            self.after(0, lambda: self._status_label.config(text="", foreground="gray"))

        success = self._audio_handler.play(self._current_wem, on_complete)
        if not success:
            self._play_btn.config(state="normal")
            self._stop_btn.config(state="disabled")
            self._status_label.config(text="Playback failed", foreground="red")

    def _on_stop_click(self) -> None:
        """Handle stop button click."""
        self._audio_handler.stop()
        self._play_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._status_label.config(text="Stopped", foreground="gray")

    def _on_cleanup_click(self) -> None:
        """Handle cleanup button click - remove cached WAV files."""
        count = self._audio_handler.cleanup_temp_files()
        messagebox.showinfo("Cleanup", f"Removed {count} cached WAV files.")

    def set_audio_handler(self, handler: AudioHandler) -> None:
        """Set the audio handler."""
        self._audio_handler = handler

    def play(self) -> bool:
        """Start playback. Returns True if playback started."""
        if not self._current_wem or not self._audio_handler.is_available:
            return False
        self._on_play_click()
        return True

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._audio_handler.is_playing
