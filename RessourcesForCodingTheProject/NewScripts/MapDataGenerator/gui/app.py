"""
Main Application Module (REDESIGNED)

Four-mode MapDataGenerator:
- MAP mode: FactionNodes with map canvas
- CHARACTER mode: Characters with large image display
- ITEM mode: Items/Knowledge with large image display
- AUDIO mode: WEM audio files with script line display

Features:
- Mode selector toolbar
- Large image display (512×512+)
- Audio playback with script display
- Lazy language loading
- Image-first architecture (all results have images)
"""

import logging
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional

# Ensure parent directory is in sys.path for PyInstaller compatibility
# This is the QACompiler pattern - add parent BEFORE imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    APP_NAME, VERSION, get_settings, save_settings, load_settings,
    get_ui_text, Settings, LANGUAGES, LANGUAGE_NAMES,
    DATA_MODES, DEFAULT_MODE, KNOWN_BRANCHES, update_branch,
)
import config
from core.linkage import LinkageResolver, DataMode
from core.language import LanguageManager
from core.search import SearchEngine, SearchResult
from core.audio_handler import AudioHandler
from gui.search_panel import SearchPanel
from gui.result_panel import ResultPanel
from gui.image_viewer import ImageViewer
from gui.audio_viewer import AudioViewer
from gui.map_canvas import MapCanvas


log = logging.getLogger(__name__)


# =============================================================================
# KOREAN FONT INSTALLATION
# =============================================================================

def install_korean_font(root: tk.Tk) -> None:
    """Force Tk and Matplotlib to use a Hangul-capable font."""
    import tkinter.font as tkfont

    try:
        from matplotlib import font_manager, rcParams
        has_matplotlib = True
    except ImportError:
        has_matplotlib = False

    font_candidates = [
        "Malgun Gothic",
        "맑은 고딕",
        "NanumGothic",
        "Noto Sans CJK KR",
        "AppleGothic",
    ]

    available_tk = set(tkfont.families(root))
    chosen_font: Optional[str] = None

    for f in font_candidates:
        if f in available_tk:
            chosen_font = f
            break

    if not chosen_font:
        log.warning("No Hangul-capable font found. Korean glyphs may be missing.")
        return

    log.info("Using '%s' for Korean text.", chosen_font)

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            tkfont.nametofont(name).configure(family=chosen_font)
        except tk.TclError:
            pass

    if has_matplotlib:
        for f in font_candidates:
            if any(f in fm.name for fm in font_manager.fontManager.ttflist):
                rcParams["font.family"] = f
                break
        rcParams["axes.unicode_minus"] = False


# =============================================================================
# MAIN APPLICATION
# =============================================================================

class MapDataGeneratorApp:
    """
    Main MapDataGenerator application with three modes.

    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [MAP] [CHARACTER] [ITEM]  ← Mode selector toolbar           │
    ├─────────────────────────────────────────────────────────────┤
    │  Left (35%)            │    Right (65%)                     │
    ├────────────────────────┼────────────────────────────────────┤
    │ Search Panel           │  IMAGE VIEWER (large!)             │
    │ Result Panel           │  [Map Canvas - MAP mode only]      │
    ├────────────────────────┴────────────────────────────────────┤
    │ Status bar                                                  │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(self, root: Optional[tk.Tk] = None):
        self.root = root or tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")

        # Load settings
        self.settings = load_settings()
        self.root.geometry(self.settings.window_geometry)
        self.root.minsize(900, 600)

        # Install Korean font
        install_korean_font(self.root)

        # Core components
        self._resolver = LinkageResolver()
        self._lang_manager = LanguageManager()
        self._search_engine: Optional[SearchEngine] = None
        self._audio_handler = AudioHandler()

        # Current mode
        self._current_mode = DataMode(self.settings.current_mode)

        # State
        self._data_loaded = False
        self._loading = False  # Loading lock - prevents rapid mode switching
        self._load_generation = 0  # Generation counter for stale callback detection
        self._current_results = []
        self._current_search_index = 0
        self._texture_folder: Optional[Path] = None

        # Variables
        self._progress_var = tk.StringVar(value=get_ui_text('ready'))
        self._mode_var = tk.StringVar(value=self._current_mode.value)

        self._create_menu()
        self._create_widgets()

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Auto-load data on startup (after window is shown)
        self.root.after(100, self._auto_load_data)

    def _create_menu(self) -> None:
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=get_ui_text('file'), menu=file_menu)

        file_menu.add_command(
            label=get_ui_text('load_data'),
            command=self._load_data,
            accelerator="Ctrl+O"
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=get_ui_text('settings'),
            command=self._open_settings
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=get_ui_text('exit'),
            command=self._on_close
        )

        # Keyboard bindings
        self.root.bind("<Control-o>", lambda e: self._load_data())

    def _create_widgets(self) -> None:
        """Create main window widgets."""
        # Branch selector at top
        self._create_branch_selector()

        # Mode selector toolbar
        self._create_mode_toolbar()

        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Horizontal paned window
        self._main_paned = ttk.PanedWindow(main_frame, orient="horizontal")
        self._main_paned.pack(fill="both", expand=True)

        # Left panel (search + results) - 35%
        left_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(left_frame, weight=1)

        # Search panel
        self._search_panel = SearchPanel(
            left_frame,
            on_search=self._on_search,
            on_language_change=self._on_language_change
        )
        self._search_panel.pack(fill="x", padx=5, pady=5)

        # Result panel
        self._result_panel = ResultPanel(
            left_frame,
            on_select=self._on_result_select,
            on_double_click=self._on_result_double_click
        )
        self._result_panel.pack(fill="both", expand=True, padx=5, pady=5)
        self._result_panel.set_load_more_callback(self._load_more_results)

        # Right panel - 65% - IMAGE VIEWER or AUDIO VIEWER
        self._right_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(self._right_frame, weight=2)

        # Image viewer - takes full right panel (default)
        self._image_viewer = ImageViewer(self._right_frame)
        self._image_viewer.pack(fill="both", expand=True)

        # Audio viewer - hidden by default, shown in AUDIO mode
        self._audio_viewer = AudioViewer(
            self._right_frame,
            audio_handler=self._audio_handler
        )
        # Don't pack yet - will be shown when AUDIO mode is active

        # Map is OFF by default - opens in separate window when toggled
        self._map_window: Optional[tk.Toplevel] = None
        self._map_canvas: Optional[MapCanvas] = None
        self._map_visible = False

        # Status bar
        self._create_status_bar()

        # Sync result panel and viewer with saved mode (ResultPanel defaults to 'map')
        if self._current_mode.value != 'map':
            self._result_panel.set_mode(self._current_mode.value)
        self._update_mode_visibility()

        # Initially disable search
        self._search_panel.enable(False)

    def _create_branch_selector(self) -> None:
        """Create branch selector (QACompiler style)."""
        branch_frame = ttk.Frame(self.root)
        branch_frame.pack(fill="x", padx=15, pady=(5, 0))

        ttk.Label(branch_frame, text="Branch:", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))

        self._branch_var = tk.StringVar(value=self.settings.branch)
        branch_combo = ttk.Combobox(
            branch_frame, textvariable=self._branch_var,
            values=KNOWN_BRANCHES, width=25
        )
        branch_combo.pack(side="left", padx=5)
        branch_combo.bind("<<ComboboxSelected>>", self._on_branch_change)
        branch_combo.bind("<Return>", self._on_branch_change)

        self._branch_status = ttk.Label(branch_frame, text="", font=("Arial", 9))
        self._branch_status.pack(side="left", padx=10)

    def _on_branch_change(self, _event=None) -> None:
        """Handle branch selection change."""
        new_branch = self._branch_var.get().strip()
        if not new_branch:
            return

        update_branch(new_branch)
        self._branch_status.config(text=f"Branch set to: {new_branch}")
        self._progress_var.set(f"Branch changed to: {new_branch}")

        # Reload data if data was previously loaded
        if self._data_loaded:
            self._auto_load_data()

    def _create_mode_toolbar(self) -> None:
        """Create mode selector toolbar."""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=5, pady=(5, 0))

        # Mode label
        ttk.Label(toolbar, text=get_ui_text('select_mode') + ":", font=('TkDefaultFont', 9)).pack(side="left", padx=(0, 10))

        # Mode buttons (radio-style)
        self._mode_buttons = {}

        for mode in DATA_MODES:
            btn = ttk.Radiobutton(
                toolbar,
                text=get_ui_text(f'mode_{mode}'),
                value=mode,
                variable=self._mode_var,
                command=self._on_mode_change,
                style='Toolbutton'
            )
            btn.pack(side="left", padx=2)
            self._mode_buttons[mode] = btn

        # Map toggle button (MAP mode only)
        self._map_toggle_var = tk.BooleanVar(value=False)
        self._map_toggle_btn = ttk.Checkbutton(
            toolbar,
            text="Show Map",
            variable=self._map_toggle_var,
            command=self._toggle_map
        )
        self._map_toggle_btn.pack(side="left", padx=20)

        # Stats display (right side)
        self._stats_label = ttk.Label(toolbar, text="", foreground="gray")
        self._stats_label.pack(side="right", padx=10)

    def _create_status_bar(self) -> None:
        """Create status bar at bottom."""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")

        self._progress_bar = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=200
        )
        self._progress_bar.pack(side="left", padx=5, pady=2)

        self._status_label = ttk.Label(
            status_frame,
            textvariable=self._progress_var
        )
        self._status_label.pack(side="left", padx=5, pady=2, fill="x", expand=True)

    def _on_mode_change(self) -> None:
        """Handle mode change - reload data for new mode if needed."""
        # Ignore clicks while loading (prevents race conditions)
        if self._loading:
            # Reset radio button to current mode since we're ignoring the click
            self._mode_var.set(self._current_mode.value)
            return

        new_mode = DataMode(self._mode_var.get())

        if new_mode == self._current_mode:
            return

        self._current_mode = new_mode
        self.settings.current_mode = new_mode.value
        save_settings(self.settings)

        log.info("Mode changed to: %s", new_mode.value)

        # Update visibility
        self._update_mode_visibility()

        # Update result panel mode (headers + column defaults)
        self._result_panel.set_mode(new_mode.value)

        # Check if data for new mode is loaded using current_mode tracking
        needs_reload = (self._resolver.current_mode != new_mode)

        if needs_reload:
            settings = get_settings()
            if new_mode == DataMode.AUDIO:
                # AUDIO mode needs different data loading
                self._start_audio_data_load(
                    audio_folder=Path(settings.audio_folder),
                    export_folder=Path(settings.export_folder),
                    loc_folder=Path(settings.loc_folder),
                    mode=new_mode,
                )
            else:
                # Other modes use texture folder from settings (or cached value)
                texture_folder = self._texture_folder or Path(settings.texture_folder)
                if texture_folder.exists():
                    self._start_data_load(
                        texture_folder=texture_folder,
                        loc_folder=Path(settings.loc_folder),
                        faction_folder=Path(settings.faction_folder),
                        knowledge_folder=Path(settings.knowledge_folder),
                        waypoint_folder=Path(settings.waypoint_folder),
                        character_folder=Path(settings.character_folder),
                        mode=new_mode,
                    )
                else:
                    log.warning("Texture folder not found: %s", texture_folder)
                    self._progress_var.set("Texture folder not found - use File > Load Data")
        elif self._search_engine:
            # Data already loaded, just update search engine mode
            self._search_engine.set_mode(new_mode)

            # Re-run search or show all entries
            query = self._search_panel.get_search_text()
            match_type = self._search_panel.get_match_type()
            lang_code = self._search_panel.get_language()
            self._on_search(query, match_type, lang_code)

        # Update stats
        self._update_stats()

    def _update_mode_visibility(self) -> None:
        """Update widget visibility based on current mode."""
        # Map toggle button only visible in MAP mode
        if self._current_mode == DataMode.MAP:
            self._map_toggle_btn.pack(side="left", padx=20)
        else:
            self._map_toggle_btn.pack_forget()
            # Close map window if open
            if self._map_window:
                self._map_window.destroy()
                self._map_window = None
                self._map_canvas = None
                self._map_visible = False
                self._map_toggle_var.set(False)

        # Swap between ImageViewer and AudioViewer based on mode
        if self._current_mode == DataMode.AUDIO:
            # Hide ImageViewer, show AudioViewer
            self._image_viewer.pack_forget()
            self._audio_viewer.pack(fill="both", expand=True)
        else:
            # Stop audio playback and clear audio viewer when leaving AUDIO mode
            self._audio_handler.stop()
            self._audio_viewer.clear()
            self._audio_viewer.pack_forget()
            # Clear stale image from previous mode, show ImageViewer
            self._image_viewer.clear()
            self._image_viewer.pack(fill="both", expand=True)

    def _toggle_map(self) -> None:
        """Toggle map window visibility."""
        if self._map_toggle_var.get():
            self._show_map_window()
        else:
            self._hide_map_window()

    def _show_map_window(self) -> None:
        """Show map in separate window."""
        if self._map_window is not None:
            self._map_window.focus_set()
            return

        # Create map window
        self._map_window = tk.Toplevel(self.root)
        self._map_window.title("Map View")
        self._map_window.geometry("800x600")
        self._map_window.protocol("WM_DELETE_WINDOW", self._hide_map_window)

        # Position next to main window
        x = self.root.winfo_x() + self.root.winfo_width() + 10
        y = self.root.winfo_y()
        self._map_window.geometry(f"+{x}+{y}")

        # Create map canvas
        self._map_canvas = MapCanvas(
            self._map_window,
            on_node_click=self._on_map_node_click
        )
        self._map_canvas.pack(fill="both", expand=True)

        # Set data if available
        if self._resolver and self._data_loaded and self._map_canvas:
            lang_code = self._search_panel.get_language()
            lang_table = self._lang_manager.get_table(lang_code)
            self._map_canvas.set_data(self._resolver, lang_table)

        self._map_visible = True

    def _hide_map_window(self) -> None:
        """Hide map window."""
        if self._map_window:
            self._map_window.destroy()
            self._map_window = None
            self._map_canvas = None
        self._map_visible = False
        self._map_toggle_var.set(False)

    def _update_stats(self) -> None:
        """Update stats display."""
        if not self._search_engine:
            self._stats_label.config(text="")
            return

        stats = self._resolver.stats
        total = stats.get('entries_total', 0)

        if self._current_mode == DataMode.AUDIO:
            # Audio-specific stats
            with_script = stats.get('audio_with_script', 0)
            self._stats_label.config(
                text=f"Total: {total} | With Script: {with_script}"
            )
        else:
            # Image mode stats
            with_image = stats.get('entries_with_image', 0)
            dds_count = self._resolver.dds_index.file_count
            self._stats_label.config(
                text=f"Total: {total} | With Image: {with_image} | DDS Files: {dds_count}"
            )

    def _auto_load_data(self) -> None:
        """Auto-load data on startup using saved paths."""
        settings = get_settings()

        if self._current_mode == DataMode.AUDIO:
            # AUDIO mode: check audio and export folders
            audio_path = Path(settings.audio_folder)
            export_path = Path(settings.export_folder)

            if not audio_path.exists():
                log.warning("Audio folder not found: %s", audio_path)
                self._progress_var.set("Audio folder not found - use File > Load Data")
                return

            if not export_path.exists():
                log.warning("Export folder not found: %s", export_path)
                self._progress_var.set("Export folder not found - use File > Load Data")
                return

            log.info("Auto-loading audio data from saved paths...")
            self._progress_var.set("Auto-loading audio data...")

            self._start_audio_data_load(
                audio_folder=audio_path,
                export_folder=export_path,
                loc_folder=Path(settings.loc_folder),
                mode=self._current_mode,
            )
        else:
            # Other modes: check texture and knowledge folders
            texture_path = Path(settings.texture_folder)
            knowledge_path = Path(settings.knowledge_folder)

            if not texture_path.exists():
                log.warning("Texture folder not found: %s", texture_path)
                self._progress_var.set("Texture folder not found - use File > Load Data")
                return

            if not knowledge_path.exists():
                log.warning("Knowledge folder not found: %s", knowledge_path)
                self._progress_var.set("Knowledge folder not found - use File > Load Data")
                return

            log.info("Auto-loading data from saved paths...")
            self._progress_var.set("Auto-loading data...")

            # Start loading with saved paths
            self._start_data_load(
                texture_folder=texture_path,
                loc_folder=Path(settings.loc_folder),
                faction_folder=Path(settings.faction_folder),
                knowledge_folder=knowledge_path,
                waypoint_folder=Path(settings.waypoint_folder),
                character_folder=Path(settings.character_folder),
                mode=self._current_mode,
            )

    def _load_data(self) -> None:
        """Open simplified load data dialog — branch is set via top bar."""
        settings = get_settings()

        dialog = tk.Toplevel(self.root)
        dialog.title("Load Data")
        dialog.geometry("450x280")
        dialog.transient(self.root)
        dialog.grab_set()

        # Mode selection
        mode_frame = ttk.LabelFrame(dialog, text=get_ui_text('select_mode'))
        mode_frame.pack(fill="x", padx=10, pady=10)

        mode_var = tk.StringVar(value=self._current_mode.value)
        for mode in DATA_MODES:
            ttk.Radiobutton(
                mode_frame,
                text=get_ui_text(f'mode_{mode}'),
                value=mode,
                variable=mode_var
            ).pack(side="left", padx=10, pady=5)

        # Info section
        info_frame = ttk.LabelFrame(dialog, text="Info")
        info_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            info_frame,
            text=f"Branch: {settings.branch}  |  Drive: {config._DRIVE_LETTER}:",
            font=("Arial", 10)
        ).pack(anchor="w", padx=10, pady=(5, 2))

        ttk.Label(
            info_frame,
            text="Paths are derived from Branch + Drive settings.",
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).pack(anchor="w", padx=10, pady=(0, 2))

        ttk.Label(
            info_frame,
            text="Use the Branch selector in the top bar to change branch.",
            font=("Arial", 9, "italic"),
            foreground="gray"
        ).pack(anchor="w", padx=10, pady=(0, 5))

        def on_load():
            # Update mode
            new_mode = DataMode(mode_var.get())
            self._current_mode = new_mode
            self._mode_var.set(new_mode.value)
            settings.current_mode = new_mode.value
            save_settings(settings)
            dialog.destroy()

            # Update mode visibility
            self._update_mode_visibility()
            self._result_panel.set_mode(new_mode.value)

            # Start loading based on mode with current settings
            if new_mode == DataMode.AUDIO:
                self._start_audio_data_load(
                    audio_folder=Path(settings.audio_folder),
                    export_folder=Path(settings.export_folder),
                    loc_folder=Path(settings.loc_folder),
                    mode=new_mode,
                )
            else:
                self._start_data_load(
                    texture_folder=Path(settings.texture_folder),
                    loc_folder=Path(settings.loc_folder),
                    faction_folder=Path(settings.faction_folder),
                    knowledge_folder=Path(settings.knowledge_folder),
                    waypoint_folder=Path(settings.waypoint_folder),
                    character_folder=Path(settings.character_folder),
                    mode=new_mode,
                )

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Load Data", command=on_load, width=15).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=15).pack(side="left", padx=10)

    def _start_data_load(
        self,
        texture_folder: Path,
        loc_folder: Path,
        faction_folder: Path,
        knowledge_folder: Path,
        waypoint_folder: Path,
        character_folder: Path,
        mode: DataMode,
    ) -> None:
        """Start background data loading."""
        # Set loading lock and disable mode buttons
        self._loading = True
        for btn in self._mode_buttons.values():
            btn.configure(state='disabled')

        # Increment generation to invalidate any pending callbacks
        self._load_generation += 1
        current_gen = self._load_generation

        self._progress_bar.start()
        self._search_panel.enable(False)

        # Capture UI state before thread (tkinter is not thread-safe)
        lang_code = self._search_panel.get_language()

        def task():
            try:
                # 1. FIRST: Scan DDS files for texture lookup
                self._update_progress("Scanning texture folder for DDS files...")
                dds_count = self._resolver.scan_textures(
                    texture_folder,
                    lambda msg: self._update_progress(msg)
                )
                self._update_progress(f"Found {dds_count} DDS files")

                if dds_count == 0:
                    log.warning("No DDS files found in texture folder!")
                    self._update_progress("WARNING: No DDS files found - check texture path")

                # 2. Build knowledge lookup table FIRST (like DatasheetGenerator)
                # KnowledgeInfo has: Names, UITextureName, Descriptions
                self._update_progress("Building Knowledge lookup table...")
                knowledge_count = self._resolver.build_knowledge_lookup(
                    knowledge_folder,
                    lambda msg: self._update_progress(msg)
                )
                self._update_progress(f"Indexed {knowledge_count} Knowledge entries")

                # 3. Load mode-specific data
                if mode == DataMode.MAP:
                    # MAP mode: Load FactionNodes for positions + merge with Knowledge
                    self._update_progress("Loading MAP data (FactionNodes + Knowledge)...")
                    self._resolver.load_map_data(
                        faction_folder,
                        lambda msg: self._update_progress(msg)
                    )

                elif mode == DataMode.CHARACTER:
                    self._update_progress("Loading CHARACTER data...")
                    self._resolver.load_character_data(
                        character_folder,
                        lambda msg: self._update_progress(msg)
                    )

                elif mode == DataMode.ITEM:
                    self._update_progress("Loading ITEM data...")
                    self._resolver.load_item_data(
                        knowledge_folder,
                        lambda msg: self._update_progress(msg)
                    )

                # 4. Load language tables (lazy - only English and Korean)
                self._update_progress("Loading language tables (English, Korean)...")
                self._lang_manager.set_folder(loc_folder)
                self._lang_manager.preload_essential(
                    lambda msg: self._update_progress(msg)
                )

                # 5. Create search engine
                self._update_progress("Building search index...")
                self._search_engine = SearchEngine(
                    self._resolver,
                    fuzzy_threshold=self.settings.fuzzy_threshold
                )
                self._search_engine.set_mode(mode)

                # Set initial language (using pre-captured lang_code)
                lang_table = self._lang_manager.get_table(lang_code)
                self._search_engine.set_language_table(lang_table)

                # Update UI on main thread (with generation check)
                self.root.after(0, lambda gen=current_gen: self._on_data_loaded(texture_folder, gen))

            except Exception as e:
                log.exception("Error loading data")
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg, gen=current_gen: self._on_load_error(msg, gen))

        threading.Thread(target=task, daemon=True).start()

    def _start_audio_data_load(
        self,
        audio_folder: Path,
        export_folder: Path,
        loc_folder: Path,
        mode: DataMode,
    ) -> None:
        """Start background audio data loading."""
        # Set loading lock and disable mode buttons
        self._loading = True
        for btn in self._mode_buttons.values():
            btn.configure(state='disabled')

        # Increment generation to invalidate any pending callbacks
        self._load_generation += 1
        current_gen = self._load_generation

        self._progress_bar.start()
        self._search_panel.enable(False)

        # Capture UI state before thread (tkinter is not thread-safe)
        lang_code = self._search_panel.get_language()

        def task():
            try:
                # Load audio data (WEM files + event mappings + script lines)
                self._update_progress("Loading AUDIO data...")
                count = self._resolver.load_audio_data(
                    audio_folder,
                    export_folder,
                    loc_folder,
                    lambda msg: self._update_progress(msg)
                )
                self._update_progress(f"Loaded {count} audio entries")

                # Load language tables for script lines
                self._update_progress("Loading language tables...")
                self._lang_manager.set_folder(loc_folder)
                self._lang_manager.preload_essential(
                    lambda msg: self._update_progress(msg)
                )

                # Create search engine
                self._update_progress("Building search index...")
                self._search_engine = SearchEngine(
                    self._resolver,
                    fuzzy_threshold=self.settings.fuzzy_threshold
                )
                self._search_engine.set_mode(mode)

                # Set initial language (using pre-captured lang_code)
                lang_table = self._lang_manager.get_table(lang_code)
                self._search_engine.set_language_table(lang_table)

                # Update UI on main thread (with generation check)
                self.root.after(0, lambda gen=current_gen: self._on_audio_data_loaded(gen))

            except Exception as e:
                log.exception("Error loading audio data")
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg, gen=current_gen: self._on_load_error(msg, gen))

        threading.Thread(target=task, daemon=True).start()

    def _on_audio_data_loaded(self, generation: int) -> None:
        """Handle audio data load completion."""
        # Ignore stale callbacks from previous loads
        if generation != self._load_generation:
            log.debug("Ignoring stale audio callback (gen %d, current %d)", generation, self._load_generation)
            return

        self._progress_bar.stop()
        self._data_loaded = True

        # Clear loading lock and re-enable mode buttons
        self._loading = False
        for btn in self._mode_buttons.values():
            btn.configure(state='normal')

        # Update mode visibility
        self._update_mode_visibility()

        # Sync result panel columns with audio mode
        self._result_panel.set_mode(self._current_mode.value)

        # Enable search
        self._search_panel.enable(True)
        self._search_panel.focus_search()

        # Update stats
        self._update_stats()

        # Auto-search to populate grid (show all entries)
        query = self._search_panel.get_search_text()
        match_type = self._search_panel.get_match_type()
        lang_code = self._search_panel.get_language()
        self._on_search(query, match_type, lang_code)

        # Update status
        total = self._search_engine.total_entries if self._search_engine else 0
        stats = self._resolver.stats
        with_script = stats.get('audio_with_script', 0)
        self._progress_var.set(f"Loaded {total} audio entries ({with_script} with script). Ready to search.")

        log.info("Audio data loaded: %d entries", total)

    def _update_progress(self, msg: str) -> None:
        """Update progress message (thread-safe)."""
        self.root.after(0, lambda: self._progress_var.set(msg))

    def _on_data_loaded(self, texture_folder: Path, generation: int) -> None:
        """Handle data load completion."""
        # Ignore stale callbacks from previous loads
        if generation != self._load_generation:
            log.debug("Ignoring stale data callback (gen %d, current %d)", generation, self._load_generation)
            return

        self._progress_bar.stop()
        self._data_loaded = True
        self._texture_folder = texture_folder

        # Clear loading lock and re-enable mode buttons
        self._loading = False
        for btn in self._mode_buttons.values():
            btn.configure(state='normal')

        # Update mode visibility
        self._update_mode_visibility()

        # Update map (if MAP mode)
        # Update map if visible
        if self._current_mode == DataMode.MAP and self._map_canvas:
            lang_code = self._search_panel.get_language()
            lang_table = self._lang_manager.get_table(lang_code)
            self._map_canvas.set_data(self._resolver, lang_table)

        # Sync result panel columns with current mode
        self._result_panel.set_mode(self._current_mode.value)

        # Enable search
        self._search_panel.enable(True)
        self._search_panel.focus_search()

        # Update stats
        self._update_stats()

        # Auto-search to populate grid (show all entries)
        query = self._search_panel.get_search_text()
        match_type = self._search_panel.get_match_type()
        lang_code = self._search_panel.get_language()
        self._on_search(query, match_type, lang_code)

        # Update status
        total = self._search_engine.total_entries if self._search_engine else 0
        self._progress_var.set(f"Loaded {total} verified entries. Ready to search.")

        log.info("Data loaded: %d entries in %s mode", total, self._current_mode.value)

    def _on_load_error(self, error: str, generation: int) -> None:
        """Handle data load error."""
        # Ignore stale callbacks from previous loads
        if generation != self._load_generation:
            log.debug("Ignoring stale error callback (gen %d, current %d)", generation, self._load_generation)
            return

        self._progress_bar.stop()

        # Clear loading lock and re-enable mode buttons
        self._loading = False
        for btn in self._mode_buttons.values():
            btn.configure(state='normal')

        self._progress_var.set("Load failed")
        messagebox.showerror("Error", f"Failed to load data:\n{error}")

    def _on_search(self, query: str, match_type: str, language: str) -> None:
        """Handle search request."""
        if not self._search_engine:
            return

        self._current_search_index = 0

        if not query:
            # Show all entries
            results = self._search_engine.get_all_entries(
                limit=self.settings.search_limit
            )
            has_more = len(results) >= self.settings.search_limit
        else:
            # Perform search
            results = self._search_engine.search(
                query,
                match_type=match_type,
                limit=self.settings.search_limit
            )
            has_more = len(results) >= self.settings.search_limit

        self._current_results = results
        self._current_search_index = len(results)

        self._result_panel.set_results(
            results,
            total_count=self._search_engine.total_entries if not query else len(results),
            has_more=has_more
        )

        if results:
            self._progress_var.set(f"Found {len(results)} results")
        else:
            self._progress_var.set(get_ui_text('no_results'))

    def _load_more_results(self) -> None:
        """Load more search results."""
        if not self._search_engine:
            return

        query = self._search_panel.get_search_text()
        match_type = self._search_panel.get_match_type()

        if not query:
            results = self._search_engine.get_all_entries(
                limit=self.settings.search_limit,
                start_index=self._current_search_index
            )
        else:
            results = self._search_engine.search(
                query,
                match_type=match_type,
                limit=self.settings.search_limit,
                start_index=self._current_search_index
            )

        has_more = len(results) >= self.settings.search_limit
        self._current_search_index += len(results)

        self._result_panel.append_results(results, has_more)

    def _on_language_change(self, lang_code: str) -> None:
        """Handle language change (with lazy loading)."""
        if not self._search_engine:
            return

        # Check if language needs to be loaded
        if not self._lang_manager.is_language_loaded(lang_code):
            self._progress_var.set(f"{get_ui_text('loading_language')}")
            self.root.update_idletasks()

            # Load in background
            def load_and_update():
                self._lang_manager.load_language(lang_code)
                self.root.after(0, lambda: self._apply_language_change(lang_code))

            threading.Thread(target=load_and_update, daemon=True).start()
        else:
            self._apply_language_change(lang_code)

    def _apply_language_change(self, lang_code: str) -> None:
        """Apply language change after loading."""
        lang_table = self._lang_manager.get_table(lang_code)
        self._search_engine.set_language_table(lang_table)

        # Update map if visible
        if self._current_mode == DataMode.MAP and self._map_canvas:
            self._map_canvas.set_data(self._resolver, lang_table)

        # Re-run search if there are results
        if self._current_results:
            query = self._search_panel.get_search_text()
            match_type = self._search_panel.get_match_type()
            self._on_search(query, match_type, lang_code)

        # Save preference
        self.settings.selected_language = lang_code
        save_settings(self.settings)

        self._progress_var.set(get_ui_text('ready'))

    def _on_result_select(self, result: SearchResult) -> None:
        """Handle result selection."""
        if self._current_mode == DataMode.AUDIO:
            # AUDIO mode: update audio viewer
            # In audio mode, dds_path is actually the WEM path
            # desc_kr = KOR script, desc_translated = ENG script (from knowledge_key)
            self._audio_viewer.set_audio(
                wem_path=result.dds_path,
                event_name=result.strkey,
                script_kor=result.desc_kr,
                script_eng=result.desc_translated
            )
        else:
            # Other modes: update image (GUARANTEED to exist due to image-first architecture)
            self._image_viewer.set_image(result.dds_path, result.ui_texture_name)

            # Highlight on map if visible
            if self._current_mode == DataMode.MAP and result.position and self._map_canvas:
                self._map_canvas.select_node(result.strkey)

    def _on_result_double_click(self, result: SearchResult) -> None:
        """Handle result double-click."""
        self._on_result_select(result)

        # In AUDIO mode, double-click plays the audio
        if self._current_mode == DataMode.AUDIO and result.dds_path:
            self._audio_viewer.play()

    def _on_map_node_click(self, strkey: str) -> None:
        """Handle map node click."""
        # Select in result list
        self._result_panel.select_by_strkey(strkey)

        # Update image
        if self._search_engine:
            result = self._search_engine.get_entry_by_strkey(strkey)
            if result:
                self._image_viewer.set_image(result.dds_path, result.ui_texture_name)

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title(get_ui_text('settings'))
        dialog.geometry("450x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # UI Language
        lang_frame = ttk.LabelFrame(dialog, text="UI Language")
        lang_frame.pack(fill="x", padx=10, pady=10)

        lang_var = tk.StringVar(value=self.settings.ui_language)
        for lang in ["English", "한국어"]:
            ttk.Radiobutton(lang_frame, text=lang, variable=lang_var, value=lang).pack(anchor="w", padx=5)

        # Search settings
        search_frame = ttk.LabelFrame(dialog, text="Search Settings")
        search_frame.pack(fill="x", padx=10, pady=10)

        limit_frame = ttk.Frame(search_frame)
        limit_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(limit_frame, text="Results per page:").pack(side="left")
        limit_var = tk.IntVar(value=self.settings.search_limit)
        ttk.Spinbox(limit_frame, from_=10, to=500, textvariable=limit_var, width=10).pack(side="left", padx=5)

        fuzzy_frame = ttk.Frame(search_frame)
        fuzzy_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(fuzzy_frame, text="Fuzzy threshold:").pack(side="left")
        fuzzy_var = tk.DoubleVar(value=self.settings.fuzzy_threshold)
        ttk.Spinbox(fuzzy_frame, from_=0.1, to=1.0, increment=0.1, textvariable=fuzzy_var, width=10).pack(side="left", padx=5)

        # Default mode
        mode_frame = ttk.LabelFrame(dialog, text="Default Mode")
        mode_frame.pack(fill="x", padx=10, pady=10)

        mode_var = tk.StringVar(value=self.settings.current_mode)
        for mode in DATA_MODES:
            ttk.Radiobutton(
                mode_frame,
                text=get_ui_text(f'mode_{mode}'),
                variable=mode_var,
                value=mode
            ).pack(side="left", padx=10, pady=5)

        def on_save():
            self.settings.ui_language = lang_var.get()
            self.settings.search_limit = limit_var.get()
            self.settings.fuzzy_threshold = fuzzy_var.get()
            self.settings.current_mode = mode_var.get()
            save_settings(self.settings)
            dialog.destroy()
            messagebox.showinfo("Settings", "Settings saved. Some changes may require restart.")

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=on_save).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=10)

    def _on_close(self) -> None:
        """Handle window close."""
        # Stop audio playback if active
        self._audio_handler.stop()

        # Save window geometry
        self.settings.window_geometry = self.root.geometry()
        save_settings(self.settings)
        self.root.destroy()

    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()
