"""
Perforce Path Service - Centralized path resolution for all Codex data modes.

Extracts PATH_TEMPLATES, KNOWN_BRANCHES, drive/branch substitution, and WSL
conversion from MapDataService into a shared singleton. All services that need
Perforce paths import from here instead of maintaining duplicate templates.

Phase 45: MegaIndex Foundation Infrastructure (Plan 01)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from loguru import logger


# =============================================================================
# Constants (extracted from MapDataGenerator/config.py + QACompiler/config.py)
# =============================================================================

KNOWN_BRANCHES = ["mainline", "cd_beta", "cd_alpha", "cd_lambda", "cd_delta"]

KNOWN_DRIVES = ["C", "D", "E", "F", "G"]

PATH_TEMPLATES = {
    "faction_folder": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo",
    "loc_folder": r"F:\perforce\cd\mainline\resource\GameData\stringtable\loc",
    "knowledge_folder": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\knowledgeinfo",
    "waypoint_folder": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo\NodeWaypointInfo",
    "texture_folder": r"F:\perforce\common\mainline\commonresource\ui\texture\image",
    "character_folder": r"F:\perforce\cd\mainline\resource\GameData\StaticInfo\characterinfo",
    "audio_folder": r"F:\perforce\cd\mainline\resource\sound\windows\English(US)",
    "audio_folder_kr": r"F:\perforce\cd\mainline\resource\sound\windows\Korean",
    "audio_folder_zh": r"F:\perforce\cd\mainline\resource\sound\windows\Chinese(PRC)",
    "export_folder": r"F:\perforce\cd\mainline\resource\GameData\stringtable\export__",
    "vrs_folder": r"F:\perforce\cd\mainline\resource\editordata\VoiceRecordingSheet__",
}

LANG_TO_AUDIO_FOLDER = {
    "eng": "audio_folder",
    "kor": "audio_folder_kr",
    "zho-cn": "audio_folder_zh",
}


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
# PerforcePathService
# =============================================================================


class PerforcePathService:
    """Centralized Perforce path resolution with 11 templates.

    Resolves drive/branch substitution and WSL conversion for all path
    templates used by MapDataService, Codex services, and Audio services.
    """

    def __init__(self) -> None:
        self._drive: str = "F"
        self._branch: str = "mainline"
        self._resolved_paths: Dict[str, Path] = {}
        self._regenerate_paths()

    def configure(self, drive: str, branch: str) -> None:
        """Configure drive letter and branch, regenerate all resolved paths.

        Args:
            drive: Single alpha character (e.g. "F", "D")
            branch: Branch name from KNOWN_BRANCHES

        Raises:
            ValueError: If drive is not a single alpha char or branch is unknown.
        """
        drive = drive.upper().strip()
        if not drive.isalpha() or len(drive) != 1:
            raise ValueError(f"Drive must be a single alpha character, got '{drive}'")

        branch = branch.strip()
        if branch not in KNOWN_BRANCHES:
            raise ValueError(
                f"Unknown branch '{branch}'. Must be one of: {KNOWN_BRANCHES}"
            )

        self._drive = drive
        self._branch = branch
        self._regenerate_paths()
        logger.info(f"[PERFORCE] Configured: drive={drive}, branch={branch}")

    def resolve(self, key: str) -> Path:
        """Return resolved WSL Path for a template key.

        Args:
            key: Template key from PATH_TEMPLATES (e.g. 'knowledge_folder')

        Returns:
            Resolved Path object (WSL-converted).

        Raises:
            KeyError: If key is not in PATH_TEMPLATES.
        """
        if key not in self._resolved_paths:
            raise KeyError(
                f"Unknown path template key '{key}'. "
                f"Valid keys: {list(PATH_TEMPLATES.keys())}"
            )
        return self._resolved_paths[key]

    def resolve_audio_folder(self, language: str = "eng") -> Path:
        """Resolve the audio folder path for a given language.

        Args:
            language: Language code ('eng', 'kor', 'zho-cn')

        Returns:
            Resolved WSL Path for the language-specific audio folder.

        Raises:
            KeyError: If language code is not in LANG_TO_AUDIO_FOLDER.
        """
        audio_key = LANG_TO_AUDIO_FOLDER.get(language)
        if audio_key is None:
            raise KeyError(
                f"Unknown audio language '{language}'. "
                f"Valid languages: {list(LANG_TO_AUDIO_FOLDER.keys())}"
            )
        return self.resolve(audio_key)

    def get_all_resolved(self) -> Dict[str, Path]:
        """Return all 11 resolved paths as a dict."""
        return dict(self._resolved_paths)

    def get_status(self) -> dict:
        """Return service status information."""
        return {
            "drive": self._drive,
            "branch": self._branch,
            "paths_resolved": len(self._resolved_paths),
            "known_branches": KNOWN_BRANCHES,
            "known_drives": KNOWN_DRIVES,
        }

    def _regenerate_paths(self) -> None:
        """Regenerate all resolved paths from templates with current drive/branch."""
        raw_paths = generate_paths(self._drive, self._branch)
        self._resolved_paths = {}
        for key, windows_path in raw_paths.items():
            wsl_path = convert_to_wsl_path(windows_path)
            self._resolved_paths[key] = Path(wsl_path)


# =============================================================================
# Singleton
# =============================================================================

_service_instance: Optional[PerforcePathService] = None


def get_perforce_path_service() -> PerforcePathService:
    """Get or create the singleton PerforcePathService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = PerforcePathService()
    return _service_instance
