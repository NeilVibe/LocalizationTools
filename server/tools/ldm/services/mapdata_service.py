"""
MapData Context Service - StrKey-to-image/audio index lookups.

Provides image and audio context for translation grid rows using
MapDataGenerator's StrKey-to-media linkage pattern. Indexes entries
under multiple keys (StrKey, StringID, KnowledgeKey) for robust lookup.

Phase 5: Visual Polish and Integration (Plan 01)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
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


@dataclass
class KnowledgeLookup:
    """Knowledge entry from KnowledgeInfo XML -- maps StrKey to entity metadata."""
    strkey: str
    name: str
    desc: str
    ui_texture_name: str
    group_key: str
    source_file: str


# =============================================================================
# Knowledge Table & DDS Index Builders
# =============================================================================


def build_knowledge_table(knowledge_folder: Path, parser: "XMLParsingEngine") -> Dict[str, KnowledgeLookup]:
    """Build StrKey -> KnowledgeLookup mapping from KnowledgeInfo XML files.

    Parses all .xml files in knowledge_folder, extracts KnowledgeInfo elements,
    and builds a lookup dict keyed by StrKey.

    Args:
        knowledge_folder: Path to folder containing knowledgeinfo XML files.
        parser: XMLParsingEngine instance for parsing.

    Returns:
        Dict mapping StrKey -> KnowledgeLookup.
    """
    from server.tools.ldm.services.xml_parsing import get_xml_parsing_engine

    table: Dict[str, KnowledgeLookup] = {}

    if not knowledge_folder.is_dir():
        logger.warning(f"[MAPDATA] Knowledge folder does not exist: {knowledge_folder}")
        return table

    xml_files = sorted(knowledge_folder.rglob("*.xml"))
    if not xml_files:
        logger.debug(f"[MAPDATA] No XML files found in {knowledge_folder}")
        return table

    for xml_path in xml_files:
        root = parser.parse_file(xml_path)
        if root is None:
            continue

        count = 0
        for elem in root.iter("KnowledgeInfo"):
            strkey = elem.get("StrKey") or ""
            if not strkey:
                continue

            entry = KnowledgeLookup(
                strkey=strkey,
                name=elem.get("Name") or "",
                desc=elem.get("Desc") or "",
                ui_texture_name=elem.get("UITextureName") or "",
                group_key=elem.get("GroupKey") or "",
                source_file=xml_path.name,
            )
            table[strkey] = entry
            count += 1

        if count > 0:
            logger.debug(f"[MAPDATA] Extracted {count} KnowledgeInfo entries from {xml_path.name}")

    logger.info(f"[MAPDATA] Knowledge table built: {len(table)} entries from {len(xml_files)} files")
    return table


def build_dds_index(texture_folder: Path) -> Dict[str, Path]:
    """Build lowercase-stem -> Path mapping for DDS texture files.

    Args:
        texture_folder: Path to folder containing DDS files.

    Returns:
        Dict mapping lowercase stem (no extension) to file Path.
    """
    index: Dict[str, Path] = {}

    if not texture_folder.is_dir():
        logger.warning(f"[MAPDATA] Texture folder does not exist: {texture_folder}")
        return index

    for dds_path in texture_folder.rglob("*.dds"):
        stem_lower = dds_path.stem.lower()
        index[stem_lower] = dds_path

    logger.info(f"[MAPDATA] DDS index built: {len(index)} textures")
    return index


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
        self._knowledge_table: Dict[str, KnowledgeLookup] = {}
        self._dds_index: Dict[str, Path] = {}
        self._loaded: bool = False
        self._branch: str = "mainline"
        self._drive: str = "F"

    def initialize(self, branch: str = "mainline", drive: str = "F") -> bool:
        """Initialize the service by building indexes from real XML data.

        Parses KnowledgeInfo XMLs via XMLParsingEngine and builds:
        1. Knowledge table (StrKey -> KnowledgeLookup)
        2. DDS index (lowercase stem -> Path)
        3. Image chains (StrKey -> UITextureName -> DDS -> ImageContext)

        Gracefully degrades: if paths don't exist, logs warnings and still
        marks as loaded with empty indexes.

        Args:
            branch: Perforce branch name
            drive: Drive letter

        Returns:
            True if initialization succeeded.
        """
        from server.tools.ldm.services.xml_parsing import get_xml_parsing_engine

        self._branch = branch
        self._drive = drive

        paths = generate_paths(drive, branch)
        logger.info(
            f"[MAPDATA] Initializing MapDataService: branch={branch}, drive={drive}, "
            f"texture_folder={paths.get('texture_folder', 'N/A')}"
        )

        parser = get_xml_parsing_engine()

        # Build knowledge table from KnowledgeInfo XMLs
        knowledge_path_str = paths.get("knowledge_folder", "")
        knowledge_wsl = convert_to_wsl_path(knowledge_path_str)
        knowledge_folder = Path(knowledge_wsl) if knowledge_wsl else Path(".")

        self._knowledge_table = build_knowledge_table(knowledge_folder, parser)

        # Build DDS texture index
        texture_path_str = paths.get("texture_folder", "")
        texture_wsl = convert_to_wsl_path(texture_path_str)
        texture_folder = Path(texture_wsl) if texture_wsl else Path(".")

        self._dds_index = build_dds_index(texture_folder)

        # Resolve image chains: StrKey -> Knowledge -> UITextureName -> DDS
        self._resolve_image_chains()

        self._loaded = True
        logger.info(
            f"[MAPDATA] Initialized: {len(self._knowledge_table)} knowledge entries, "
            f"{len(self._dds_index)} DDS textures, "
            f"{len(self._strkey_to_image)} image chains resolved"
        )
        return True

    def _resolve_image_chains(self) -> None:
        """Resolve StrKey -> KnowledgeLookup -> UITextureName -> DDS -> ImageContext.

        For each knowledge table entry, looks up UITextureName in DDS index.
        If found, creates ImageContext and indexes under StrKey.
        """
        resolved = 0
        missing_texture = 0

        for strkey, knowledge in self._knowledge_table.items():
            texture_name = knowledge.ui_texture_name
            if not texture_name:
                continue

            texture_lower = texture_name.lower()
            dds_path = self._dds_index.get(texture_lower)

            if dds_path is not None:
                img = ImageContext(
                    texture_name=texture_name,
                    dds_path=str(dds_path),
                    thumbnail_url=f"/api/ldm/mapdata/thumbnail/{texture_name}",
                    has_image=True,
                )
                self._strkey_to_image[strkey] = img
                resolved += 1
            else:
                logger.debug(
                    f"[MAPDATA] Missing DDS for StrKey={strkey}, "
                    f"UITextureName={texture_name}"
                )
                missing_texture += 1

        logger.info(
            f"[MAPDATA] Image chains: {resolved} resolved, "
            f"{missing_texture} missing textures"
        )

    def get_image_context(self, string_id: str) -> Optional[ImageContext]:
        """Look up image context by StrKey, StringID, or KnowledgeKey.

        Returns None if service is not loaded or key is unknown.
        """
        if not self._loaded:
            return None
        return self._strkey_to_image.get(string_id)

    def get_knowledge_lookup(self, strkey: str) -> Optional[KnowledgeLookup]:
        """Look up raw KnowledgeLookup entry by StrKey.

        Used by ContextService.resolve_chain() to access UITextureName
        and other metadata for step-by-step chain resolution.

        Args:
            strkey: The StrKey to look up.

        Returns:
            KnowledgeLookup or None if not found.
        """
        return self._knowledge_table.get(strkey)

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
