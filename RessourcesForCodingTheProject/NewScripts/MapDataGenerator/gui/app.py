"""
Main Application Module

Main window with:
- Menu bar (File -> Load Data, Settings, Exit)
- PanedWindow layout (left: search+results, right: image+map)
- Progress bar during data loading
- Threading for non-blocking loads
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

try:
    from config import (
        APP_NAME, VERSION, get_settings, save_settings, load_settings,
        get_ui_text, Settings, LANGUAGES, LANGUAGE_NAMES
    )
    from core.linkage import LinkageResolver
    from core.language import LanguageManager
    from core.search import SearchEngine, SearchResult
    from gui.search_panel import SearchPanel
    from gui.result_panel import ResultPanel
    from gui.image_viewer import ImageViewer
    from gui.map_canvas import MapCanvas
except ImportError:
    from ..config import (
        APP_NAME, VERSION, get_settings, save_settings, load_settings,
        get_ui_text, Settings, LANGUAGES, LANGUAGE_NAMES
    )
    from ..core.linkage import LinkageResolver
    from ..core.language import LanguageManager
    from ..core.search import SearchEngine, SearchResult
    from .search_panel import SearchPanel
    from .result_panel import ResultPanel
    from .image_viewer import ImageViewer
    from .map_canvas import MapCanvas


log = logging.getLogger(__name__)


# =============================================================================
# KOREAN FONT INSTALLATION
# =============================================================================

def install_korean_font(root: tk.Tk) -> None:
    """
    Force Tk and Matplotlib to use a Hangul-capable font.
    """
    import tkinter.font as tkfont

    try:
        from matplotlib import font_manager, rcParams
        has_matplotlib = True
    except ImportError:
        has_matplotlib = False

    # Font candidates (order matters)
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

    # Apply to Tkinter
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            tkfont.nametofont(name).configure(family=chosen_font)
        except tk.TclError:
            pass

    # Apply to Matplotlib
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
    """Main MapDataGenerator application."""

    def __init__(self, root: Optional[tk.Tk] = None):
        """
        Initialize application.

        Args:
            root: Tkinter root window (created if None)
        """
        self.root = root or tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")

        # Load settings
        self.settings = load_settings()
        self.root.geometry(self.settings.window_geometry)

        # Install Korean font
        install_korean_font(self.root)

        # Core components
        self._resolver = LinkageResolver()
        self._lang_manager = LanguageManager()
        self._search_engine: Optional[SearchEngine] = None

        # State
        self._data_loaded = False
        self._current_results = []
        self._current_search_index = 0

        # Variables
        self._progress_var = tk.StringVar(value=get_ui_text('ready'))

        self._create_menu()
        self._create_widgets()

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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
        # Main paned window (horizontal split)
        self._main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        self._main_paned.pack(fill="both", expand=True, padx=5, pady=5)

        # Left panel (search + results)
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

        # Right panel (image + map)
        right_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(right_frame, weight=2)

        # Right paned (vertical split: image on top, map on bottom)
        right_paned = ttk.PanedWindow(right_frame, orient="vertical")
        right_paned.pack(fill="both", expand=True)

        # Image viewer
        self._image_viewer = ImageViewer(right_paned)
        right_paned.add(self._image_viewer, weight=1)

        # Map canvas
        self._map_canvas = MapCanvas(
            right_paned,
            on_node_click=self._on_map_node_click
        )
        right_paned.add(self._map_canvas, weight=3)

        # Status bar
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

        # Initially disable search
        self._search_panel.enable(False)

    def _load_data(self) -> None:
        """Open folder selection and load data."""
        # Show folder selection dialog
        settings = get_settings()

        dialog = tk.Toplevel(self.root)
        dialog.title("Load Data - Select Folders")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Faction folder
        faction_var = tk.StringVar(value=settings.faction_folder)
        ttk.Label(dialog, text="Faction Info Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        faction_frame = ttk.Frame(dialog)
        faction_frame.pack(fill="x", padx=10, pady=2)
        faction_entry = ttk.Entry(faction_frame, textvariable=faction_var, width=50)
        faction_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            faction_frame,
            text="Browse",
            command=lambda: faction_var.set(
                filedialog.askdirectory(title="Select Faction Info Folder") or faction_var.get()
            )
        ).pack(side="left", padx=5)

        # LOC folder
        loc_var = tk.StringVar(value=settings.loc_folder)
        ttk.Label(dialog, text="Language Data Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        loc_frame = ttk.Frame(dialog)
        loc_frame.pack(fill="x", padx=10, pady=2)
        loc_entry = ttk.Entry(loc_frame, textvariable=loc_var, width=50)
        loc_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            loc_frame,
            text="Browse",
            command=lambda: loc_var.set(
                filedialog.askdirectory(title="Select Language Data Folder") or loc_var.get()
            )
        ).pack(side="left", padx=5)

        # Knowledge folder
        knowledge_var = tk.StringVar(value=settings.knowledge_folder)
        ttk.Label(dialog, text="Knowledge Info Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        knowledge_frame = ttk.Frame(dialog)
        knowledge_frame.pack(fill="x", padx=10, pady=2)
        knowledge_entry = ttk.Entry(knowledge_frame, textvariable=knowledge_var, width=50)
        knowledge_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            knowledge_frame,
            text="Browse",
            command=lambda: knowledge_var.set(
                filedialog.askdirectory(title="Select Knowledge Info Folder") or knowledge_var.get()
            )
        ).pack(side="left", padx=5)

        # Waypoint folder
        waypoint_var = tk.StringVar(value=settings.waypoint_folder)
        ttk.Label(dialog, text="Waypoint Info Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        waypoint_frame = ttk.Frame(dialog)
        waypoint_frame.pack(fill="x", padx=10, pady=2)
        waypoint_entry = ttk.Entry(waypoint_frame, textvariable=waypoint_var, width=50)
        waypoint_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            waypoint_frame,
            text="Browse",
            command=lambda: waypoint_var.set(
                filedialog.askdirectory(title="Select Waypoint Info Folder") or waypoint_var.get()
            )
        ).pack(side="left", padx=5)

        # Texture folder
        texture_var = tk.StringVar(value=settings.texture_folder)
        ttk.Label(dialog, text="Texture Folder:").pack(anchor="w", padx=10, pady=(10, 0))
        texture_frame = ttk.Frame(dialog)
        texture_frame.pack(fill="x", padx=10, pady=2)
        texture_entry = ttk.Entry(texture_frame, textvariable=texture_var, width=50)
        texture_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(
            texture_frame,
            text="Browse",
            command=lambda: texture_var.set(
                filedialog.askdirectory(title="Select Texture Folder") or texture_var.get()
            )
        ).pack(side="left", padx=5)

        def on_load():
            # Save paths to settings
            settings.faction_folder = faction_var.get()
            settings.loc_folder = loc_var.get()
            settings.knowledge_folder = knowledge_var.get()
            settings.waypoint_folder = waypoint_var.get()
            settings.texture_folder = texture_var.get()
            save_settings(settings)

            dialog.destroy()

            # Start loading in background
            self._start_data_load(
                faction_folder=Path(faction_var.get()),
                loc_folder=Path(loc_var.get()),
                knowledge_folder=Path(knowledge_var.get()),
                waypoint_folder=Path(waypoint_var.get()),
                texture_folder=Path(texture_var.get())
            )

        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="Load", command=on_load, width=15).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=15).pack(side="left", padx=10)

    def _start_data_load(
        self,
        faction_folder: Path,
        loc_folder: Path,
        knowledge_folder: Path,
        waypoint_folder: Path,
        texture_folder: Path
    ) -> None:
        """Start background data loading."""
        self._progress_bar.start()
        self._search_panel.enable(False)

        def task():
            try:
                # Load faction nodes
                self._update_progress("Loading FactionNodes...")
                self._resolver.load_faction_nodes(
                    faction_folder,
                    lambda msg: self._update_progress(msg)
                )

                # Load knowledge info
                self._update_progress("Loading KnowledgeInfo...")
                self._resolver.load_knowledge_info(
                    knowledge_folder,
                    lambda msg: self._update_progress(msg)
                )

                # Load routes
                self._update_progress("Loading routes...")
                self._resolver.load_routes(
                    waypoint_folder,
                    lambda msg: self._update_progress(msg)
                )

                # Load language tables
                self._update_progress("Loading language tables...")
                self._lang_manager.set_folder(loc_folder)
                self._lang_manager.load_all(
                    lambda msg: self._update_progress(msg)
                )

                # Create search engine
                self._update_progress("Building search index...")
                self._search_engine = SearchEngine(
                    self._resolver,
                    fuzzy_threshold=self.settings.fuzzy_threshold
                )

                # Set initial language
                lang_code = self._search_panel.get_language()
                lang_table = self._lang_manager.get_table(lang_code)
                self._search_engine.set_language_table(lang_table)

                # Update UI on main thread
                self.root.after(0, lambda: self._on_data_loaded(texture_folder))

            except Exception as e:
                log.exception("Error loading data")
                error_msg = str(e)
                self.root.after(0, lambda msg=error_msg: self._on_load_error(msg))

        threading.Thread(target=task, daemon=True).start()

    def _update_progress(self, msg: str) -> None:
        """Update progress message (thread-safe)."""
        self.root.after(0, lambda: self._progress_var.set(msg))

    def _on_data_loaded(self, texture_folder: Path) -> None:
        """Handle data load completion."""
        self._progress_bar.stop()
        self._data_loaded = True
        self._texture_folder = texture_folder

        # Update map
        lang_code = self._search_panel.get_language()
        lang_table = self._lang_manager.get_table(lang_code)
        self._map_canvas.set_data(self._resolver, lang_table)

        # Enable search
        self._search_panel.enable(True)
        self._search_panel.focus_search()

        # Update status
        node_count = len(self._resolver.faction_nodes)
        self._progress_var.set(f"Loaded {node_count} nodes. Ready to search.")

        log.info("Data loaded: %d nodes", node_count)

    def _on_load_error(self, error: str) -> None:
        """Handle data load error."""
        self._progress_bar.stop()
        self._progress_var.set("Load failed")
        messagebox.showerror("Error", f"Failed to load data:\n{error}")

    def _on_search(self, query: str, match_type: str, language: str) -> None:
        """Handle search request."""
        if not self._search_engine:
            return

        self._current_search_index = 0

        if not query:
            # Show all nodes
            results = self._search_engine.get_all_nodes(
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
            total_count=self._search_engine.total_nodes if not query else len(results),
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
            results = self._search_engine.get_all_nodes(
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
        """Handle language change."""
        if not self._search_engine:
            return

        # Update language table
        lang_table = self._lang_manager.get_table(lang_code)
        self._search_engine.set_language_table(lang_table)

        # Update map
        self._map_canvas.set_data(self._resolver, lang_table)

        # Re-run search if there are results
        if self._current_results:
            query = self._search_panel.get_search_text()
            match_type = self._search_panel.get_match_type()
            self._on_search(query, match_type, lang_code)

        # Save preference
        self.settings.selected_language = lang_code
        save_settings(self.settings)

    def _on_result_select(self, result: SearchResult) -> None:
        """Handle result selection."""
        # Update image
        if result.ui_texture_name:
            texture_path = self._resolver.get_texture_path(
                result.strkey,
                self._texture_folder
            )
            self._image_viewer.set_image(texture_path, result.ui_texture_name)
        else:
            self._image_viewer.clear()

        # Highlight on map
        self._map_canvas.select_node(result.strkey)

    def _on_result_double_click(self, result: SearchResult) -> None:
        """Handle result double-click."""
        # Same as select for now
        self._on_result_select(result)

    def _on_map_node_click(self, strkey: str) -> None:
        """Handle map node click."""
        # Select in result list
        self._result_panel.select_by_strkey(strkey)

        # Update image if not already selected
        result = self._search_engine.get_node_by_strkey(strkey)
        if result:
            if result.ui_texture_name:
                texture_path = self._resolver.get_texture_path(
                    strkey,
                    self._texture_folder
                )
                self._image_viewer.set_image(texture_path, result.ui_texture_name)
            else:
                self._image_viewer.clear()

    def _open_settings(self) -> None:
        """Open settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title(get_ui_text('settings'))
        dialog.geometry("400x300")
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

        def on_save():
            self.settings.ui_language = lang_var.get()
            self.settings.search_limit = limit_var.get()
            self.settings.fuzzy_threshold = fuzzy_var.get()
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
        # Save window geometry
        self.settings.window_geometry = self.root.geometry()
        save_settings(self.settings)
        self.root.destroy()

    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()
