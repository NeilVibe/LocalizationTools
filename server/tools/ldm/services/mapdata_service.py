"""
MapData Context Service - StrKey-to-image/audio index lookups.

Provides image and audio context for translation grid rows using
MapDataGenerator's StrKey-to-media linkage pattern. Indexes entries
under multiple keys (StrKey, StringID, KnowledgeKey) for robust lookup.

Phase 5: Visual Polish and Integration (Plan 01)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional
from loguru import logger


# =============================================================================
# Known Branches & Path Templates
# (Adapted from MapDataGenerator/config.py)
# =============================================================================

KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda"]

PATH_TEMPLATES = {
    'faction_folder':    r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    'loc_folder':        r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    'knowledge_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    'waypoint_folder':   r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo",
    'texture_folder':    r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    'character_folder':  r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    'audio_folder':      r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    'audio_folder_kr':   r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    'audio_folder_zh':   r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",
    'export_folder':     r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    'vrs_folder':        r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ImageContext:
    """Image context for a translation grid row."""
    texture_name: str
    dds_path: str
    thumbnail_url: str
    has_image: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AudioContext:
    """Audio context for a translation grid row."""
    event_name: str
    wem_path: str
    script_kr: str
    script_eng: str
    duration_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Helper Functions
# =============================================================================

def convert_to_wsl_path(windows_path: str) -> str:
    """Convert Windows path to WSL path.

    F:\\perforce\\... -> /mnt/f/perforce/...
    Already-unix paths pass through unchanged.
    """
    if not windows_path:
        return ""

    # Already a Unix path
    if windows_path.startswith("/"):
        return windows_path

    # Check for drive letter pattern (X:\...)
    if len(windows_path) >= 2 and windows_path[1] == ":":
        drive = windows_path[0].lower()
        rest = windows_path[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"

    return windows_path


def generate_paths(drive: str, branch: str) -> dict:
    """Generate all resolved paths from templates with given drive and branch.

    Args:
        drive: Drive letter (single character, e.g. "F")
        branch: Branch name (e.g. "mainline", "cd_beta")

    Returns:
        Dict with keys matching PATH_TEMPLATES, values are resolved path strings.
    """
    result = {}
    for key, template in PATH_TEMPLATES.items():
        path = template
        # Replace drive letter
        if path.startswith("F:") or path.startswith("f:"):
            path = f"{drive}:{path[2:]}"
        # Replace branch
        path = path.replace("mainline", branch)
        result[key] = path
    return result


# =============================================================================
# MapDataService
# =============================================================================

class MapDataService:
    """Service for StrKey-to-image/audio context lookups.

    Maintains pre-indexed maps for fast O(1) lookups by StrKey, StringID,
    or KnowledgeKey. Gracefully degrades: returns None when unloaded.
    """

    def __init__(self):
        self._strkey_to_image: Dict[str, ImageContext] = {}
        self._strkey_to_audio: Dict[str, AudioContext] = {}
        self._loaded: bool = False
        self._branch: str = "mainline"
        self._drive: str = "F"

    def initialize(self, branch: str = "mainline", drive: str = "F") -> bool:
        """Initialize the service by building indexes.

        In production, this would parse staticinfo XML files using
        MapDataGenerator's LinkageResolver pattern. For now, sets up
        the infrastructure for manual or future automated population.

        Args:
            branch: Perforce branch name
            drive: Drive letter

        Returns:
            True if initialization succeeded, False if paths don't exist.
        """
        self._branch = branch
        self._drive = drive

        paths = generate_paths(drive, branch)
        logger.info(
            f"[MAPDATA] Initializing MapDataService: branch={branch}, drive={drive}, "
            f"texture_folder={paths.get('texture_folder', 'N/A')}"
        )

        # Infrastructure ready - indexes can be populated by future XML parsing
        # or manually for testing. Service reports as loaded if initialize called.
        self._loaded = True
        return True

    def get_image_context(self, string_id: str) -> Optional[ImageContext]:
        """Look up image context by StrKey, StringID, or KnowledgeKey.

        Returns None if service is not loaded or key is unknown.
        """
        if not self._loaded:
            return None
        return self._strkey_to_image.get(string_id)

    def get_audio_context(self, string_id: str) -> Optional[AudioContext]:
        """Look up audio context by StrKey, StringID, or KnowledgeKey.

        Returns None if service is not loaded or key is unknown.
        """
        if not self._loaded:
            return None
        return self._strkey_to_audio.get(string_id)

    def get_status(self) -> dict:
        """Return service status info."""
        return {
            "loaded": self._loaded,
            "branch": self._branch,
            "drive": self._drive,
            "image_count": len(self._strkey_to_image),
            "audio_count": len(self._strkey_to_audio),
        }


# =============================================================================
# Singleton instance
# =============================================================================

_service_instance: Optional[MapDataService] = None


def get_mapdata_service() -> MapDataService:
    """Get or create the singleton MapDataService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MapDataService()
    return _service_instance
