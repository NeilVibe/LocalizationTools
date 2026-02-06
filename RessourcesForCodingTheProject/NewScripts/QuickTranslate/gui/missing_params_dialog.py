"""
Missing Translation Parameters Dialog.

Tkinter Toplevel popup for selecting match type and fuzzy threshold
before running Find Missing Translations.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict

import config


class MissingParamsDialog(tk.Toplevel):
    """
    Parameter selection dialog for Find Missing Translations.

    Returns dict with match_mode and threshold, or None if cancelled.
    """

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Find Missing Translations - Parameters")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result: Optional[Dict] = None

        # Variables
        self.match_mode = tk.StringVar(value="stringid_kr_strict")
        self.threshold = tk.DoubleVar(value=config.FUZZY_THRESHOLD_DEFAULT)

        self._build_ui()

        # Center on parent
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    def _build_ui(self):
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Match Type section
        ttk.Label(main, text="Match Type:", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        modes = [
            ("stringid_kr_strict", "StringID + KR (Strict)",
             "Exact (StrOrigin, StringID) composite key. Current behavior."),
            ("stringid_kr_fuzzy", "StringID + KR (Fuzzy)",
             "StringID must match; KR text compared by semantic similarity."),
            ("kr_strict", "KR only (Strict)",
             "Exact StrOrigin text match, ignores StringID differences."),
            ("kr_fuzzy", "KR only (Fuzzy)",
             "Semantic similarity on KR text only. Broadest matching."),
        ]

        for value, label, tooltip in modes:
            rb = ttk.Radiobutton(
                main, text=label, variable=self.match_mode, value=value,
                command=self._on_mode_change,
            )
            rb.pack(anchor=tk.W, padx=(10, 0), pady=1)

        # Separator
        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Threshold section
        self.threshold_frame = ttk.Frame(main)
        self.threshold_frame.pack(fill=tk.X)

        ttk.Label(self.threshold_frame, text="Fuzzy Threshold:").pack(
            anchor=tk.W
        )

        slider_frame = ttk.Frame(self.threshold_frame)
        slider_frame.pack(fill=tk.X, pady=(2, 0))

        self.threshold_scale = ttk.Scale(
            slider_frame, from_=config.FUZZY_THRESHOLD_MIN,
            to=config.FUZZY_THRESHOLD_MAX,
            variable=self.threshold, orient=tk.HORIZONTAL,
            command=self._on_threshold_change,
        )
        self.threshold_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.threshold_label = ttk.Label(
            slider_frame, text=f"{self.threshold.get():.2f}", width=5
        )
        self.threshold_label.pack(side=tk.LEFT, padx=(5, 0))

        # Disable threshold for strict modes initially
        self._on_mode_change()

        # Separator
        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Run", command=self._on_run, width=12).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel, width=12).pack(
            side=tk.LEFT
        )

    def _on_mode_change(self, *_):
        mode = self.match_mode.get()
        is_fuzzy = mode.endswith("_fuzzy")
        state = "normal" if is_fuzzy else "disabled"
        self.threshold_scale.configure(state=state)

    def _on_threshold_change(self, val):
        # Snap to 0.01 increments
        snapped = round(float(val), 2)
        self.threshold.set(snapped)
        self.threshold_label.configure(text=f"{snapped:.2f}")

    def _on_run(self):
        self.result = {
            "match_mode": self.match_mode.get(),
            "threshold": round(self.threshold.get(), 2),
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
