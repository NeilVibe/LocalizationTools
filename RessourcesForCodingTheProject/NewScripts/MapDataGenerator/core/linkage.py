"""
Linkage Module (REWRITTEN)

Image-First Architecture:
- Only collects entries that have BOTH UITextureName AND existing DDS file
- Supports 3 modes: MAP, CHARACTER, ITEM
- DDSIndex scans texture folder first for fast lookups

Resolution Chain for MAP mode:
    FactionNode.StrKey
    → FactionNode.KnowledgeKey
    → KnowledgeInfo.UITextureName
    → (or KnowledgeGroupInfo.UITextureName)
    → Verified .dds file path
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from .xml_parser import parse_xml, iter_xml_files

log = logging.getLogger(__name__)


# =============================================================================
# DATA MODE ENUM
# =============================================================================

class DataMode(Enum):
    """Application data modes."""
    MAP = "map"
    CHARACTER = "character"
    ITEM = "item"


# =============================================================================
# DDS INDEX (Scans texture folder for fast lookup)
# =============================================================================

class DDSIndex:
    """
    Pre-scans texture folder to build index of available DDS files.

    This is the KEY to image-first architecture:
    - Scans all .dds files once at startup
    - Provides O(1) lookup by texture name
    - If DDS not in index, entry is skipped (no image = no entry)
    """

    def __init__(self, texture_folder: Optional[Path] = None):
        self._texture_folder: Optional[Path] = texture_folder
        self._dds_files: Dict[str, Path] = {}  # lowercase name -> full path
        self._scanned = False

    def scan_folder(self, texture_folder: Optional[Path] = None, progress_callback=None) -> int:
        """
        Scan texture folder recursively for all .dds files.

        Args:
            texture_folder: Path to texture folder (uses stored if None)
            progress_callback: Optional progress callback

        Returns:
            Number of DDS files found
        """
        if texture_folder:
            self._texture_folder = texture_folder

        if self._texture_folder is None:
            log.error("Texture folder not set!")
            return 0

        if not self._texture_folder.exists():
            log.error("Texture folder does not exist: %s", self._texture_folder)
            return 0

        self._dds_files.clear()

        if progress_callback:
            progress_callback(f"Scanning {self._texture_folder} for DDS files...")

        log.info("Scanning texture folder: %s", self._texture_folder)

        count = 0
        knowledgeimage_count = 0

        for dds_path in self._texture_folder.rglob("*.dds"):
            # Index by lowercase filename (without extension)
            name_lower = dds_path.stem.lower()
            self._dds_files[name_lower] = dds_path

            # Also index with extension
            self._dds_files[dds_path.name.lower()] = dds_path

            # Track knowledgeimage files specifically
            if "knowledgeimage" in str(dds_path).lower():
                knowledgeimage_count += 1

            count += 1

        self._scanned = True
        log.info("Scanned %d DDS files (%d in Knowledgeimage folders)", count, knowledgeimage_count)

        # Log sample entries for debugging
        if count > 0:
            samples = list(self._dds_files.keys())[:5]
            log.debug("Sample indexed textures: %s", samples)

        return count

    def find(self, ui_texture_name: str) -> Optional[Path]:
        """
        Find DDS file for UITextureName.

        Args:
            ui_texture_name: Texture name from XML

        Returns:
            Path to DDS file or None if not found
        """
        if not ui_texture_name:
            return None

        name = ui_texture_name.lower().strip()

        # Remove any path components (just use filename)
        if '/' in name or '\\' in name:
            name = name.replace('\\', '/').split('/')[-1]

        if not name.endswith('.dds'):
            # Try without extension first
            if name in self._dds_files:
                return self._dds_files[name]
            # Try with extension
            name_with_ext = name + '.dds'
            return self._dds_files.get(name_with_ext)

        return self._dds_files.get(name)

    def exists(self, ui_texture_name: str) -> bool:
        """Check if DDS file exists for texture name."""
        return self.find(ui_texture_name) is not None

    @property
    def is_scanned(self) -> bool:
        return self._scanned

    @property
    def file_count(self) -> int:
        # Divide by 2 because we index each file twice (with and without extension)
        return len(self._dds_files) // 2


# =============================================================================
# IMAGE-VERIFIED DATA STRUCTURES
# =============================================================================

@dataclass
class FactionNodeVerified:
    """
    FactionNode with VERIFIED image.

    IMPORTANT: dds_path is REQUIRED - if no DDS exists, node is NOT created.
    This ensures every search result has a guaranteed image.
    """
    strkey: str
    name_kr: str
    desc_kr: str
    position: Tuple[float, float, float]  # (x, y, z)
    ui_texture_name: str  # REQUIRED
    dds_path: Path  # VERIFIED (REQUIRED)
    knowledge_key: str = ""
    source_file: str = ""

    @property
    def position_2d(self) -> Tuple[float, float]:
        """Get 2D position (x, z) for map display."""
        return (self.position[0], self.position[2])


@dataclass
class CharacterItem:
    """
    Character with VERIFIED image.

    Extracted from CharacterInfo XML files.
    """
    strkey: str  # CharacterInfo.StrKey
    name_kr: str  # CharacterName or Knowledge.Name
    desc_kr: str  # Knowledge.Desc
    ui_texture_name: str  # REQUIRED
    dds_path: Path  # VERIFIED (REQUIRED)
    group: str = ""  # Category (e.g., "Dogs and Cats", "NPC")
    source_file: str = ""


@dataclass
class ItemEntry:
    """
    Item/Knowledge with VERIFIED image.

    Extracted from KnowledgeInfo XML files.
    """
    strkey: str  # KnowledgeInfo.StrKey
    name_kr: str  # Name
    desc_kr: str  # Desc
    ui_texture_name: str  # REQUIRED
    dds_path: Path  # VERIFIED (REQUIRED)
    group_name: str = ""  # KnowledgeGroupInfo.GroupName
    source_file: str = ""


# Legacy dataclasses (for backward compatibility during transition)
@dataclass
class FactionNode:
    """Legacy FactionNode (without verified image)."""
    strkey: str
    name_kr: str
    desc_kr: str
    position: Tuple[float, float, float]
    knowledge_key: str = ""
    source_file: str = ""

    @property
    def position_2d(self) -> Tuple[float, float]:
        return (self.position[0], self.position[2])


@dataclass
class KnowledgeInfo:
    """Represents a KnowledgeInfo entry."""
    strkey: str
    name_kr: str
    desc_kr: str
    ui_texture_name: str = ""
    knowledge_group_key: str = ""
    source_file: str = ""


@dataclass
class KnowledgeGroupInfo:
    """Represents a KnowledgeGroupInfo entry."""
    strkey: str
    group_name_kr: str
    desc_kr: str
    ui_texture_name: str = ""
    knowledge_group_icon: str = ""
    source_file: str = ""


@dataclass
class Route:
    """Represents a waypoint route between nodes."""
    key: str
    from_key: str
    to_key: str
    points: List[Tuple[float, float]]  # 2D points (x, z)


# =============================================================================
# LINKAGE RESOLVER (REWRITTEN FOR IMAGE-FIRST)
# =============================================================================

class LinkageResolver:
    """
    Resolves linkage between data nodes and UITextureName.

    IMAGE-FIRST ARCHITECTURE:
    - DDSIndex must be scanned FIRST
    - Only entries with verified images are collected
    - Every entry in collections has guaranteed image
    """

    def __init__(self):
        # DDS Index (scan first!)
        self._dds_index: DDSIndex = DDSIndex()

        # Verified collections (all entries have images)
        self._faction_nodes_verified: Dict[str, FactionNodeVerified] = {}
        self._characters: Dict[str, CharacterItem] = {}
        self._items: Dict[str, ItemEntry] = {}

        # Knowledge lookups (for resolution chain)
        self._knowledge_info: Dict[str, KnowledgeInfo] = {}
        self._knowledge_groups: Dict[str, KnowledgeGroupInfo] = {}

        # Routes (for map)
        self._routes: List[Route] = []
        self._adjacency: Dict[str, set] = {}

        # Stats
        self._stats = {
            'faction_nodes_verified': 0,
            'faction_nodes_skipped': 0,
            'characters_verified': 0,
            'characters_skipped': 0,
            'items_verified': 0,
            'items_skipped': 0,
        }

    # =========================================================================
    # DDS INDEX
    # =========================================================================

    def scan_textures(self, texture_folder: Path, progress_callback=None) -> int:
        """
        MUST be called first! Scans texture folder for DDS files.

        Args:
            texture_folder: Path to texture folder
            progress_callback: Optional callback

        Returns:
            Number of DDS files found
        """
        return self._dds_index.scan_folder(texture_folder, progress_callback)

    @property
    def dds_index(self) -> DDSIndex:
        """Get DDS index for direct access."""
        return self._dds_index

    # =========================================================================
    # KNOWLEDGE INFO LOADING (Needed for resolution chain)
    # =========================================================================

    def load_knowledge_info(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load KnowledgeInfo data from XML files.

        This is needed for the resolution chain (FactionNode → KnowledgeInfo → UITextureName).

        Args:
            folder: Path to knowledge info folder
            progress_callback: Optional progress callback

        Returns:
            Number of knowledge entries loaded
        """
        if not folder.exists():
            log.error("Knowledge folder does not exist: %s", folder)
            return 0

        log.info("Loading KnowledgeInfo from: %s", folder)

        count = 0
        with_texture = 0
        sample_textures = []

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading KnowledgeInfo from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            # Parse KnowledgeInfo elements
            for ki in root.iter("KnowledgeInfo"):
                strkey = ki.get("StrKey")
                if not strkey:
                    continue

                name_kr = (ki.get("Name") or "").strip()
                desc_kr = (ki.get("Desc") or "").replace("<br/>", "\n").strip()
                ui_texture = (ki.get("UITextureName") or "").strip()
                group_key = (ki.get("KnowledgeGroupKey") or "").strip()

                info = KnowledgeInfo(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    ui_texture_name=ui_texture,
                    knowledge_group_key=group_key,
                    source_file=path.name,
                )

                self._knowledge_info[strkey] = info
                count += 1

                if ui_texture:
                    with_texture += 1
                    if len(sample_textures) < 5:
                        sample_textures.append(f"{strkey}:{ui_texture}")

            # Also parse KnowledgeGroupInfo elements
            for kgi in root.iter("KnowledgeGroupInfo"):
                strkey = kgi.get("StrKey")
                if not strkey:
                    continue

                group_name = (kgi.get("GroupName") or "").strip()
                desc_kr = (kgi.get("Desc") or "").replace("<br/>", "\n").strip()
                ui_texture = (kgi.get("UITextureName") or "").strip()
                icon = (kgi.get("KnowledgeGroupIcon") or "").strip()

                group = KnowledgeGroupInfo(
                    strkey=strkey,
                    group_name_kr=group_name,
                    desc_kr=desc_kr,
                    ui_texture_name=ui_texture,
                    knowledge_group_icon=icon,
                    source_file=path.name,
                )

                self._knowledge_groups[strkey] = group

        log.info("Loaded %d KnowledgeInfo (%d with UITextureName), %d KnowledgeGroupInfo",
                 count, with_texture, len(self._knowledge_groups))

        if sample_textures:
            log.debug("Sample KnowledgeInfo with textures: %s", sample_textures)

        return count

    def _resolve_texture_for_knowledge_key(self, knowledge_key: str) -> Optional[str]:
        """
        Resolve UITextureName from KnowledgeKey.

        Resolution chain:
        1. KnowledgeInfo.UITextureName (if present)
        2. KnowledgeInfo.KnowledgeGroupKey → KnowledgeGroupInfo.UITextureName
        """
        if not knowledge_key:
            return None

        knowledge = self._knowledge_info.get(knowledge_key)
        if not knowledge:
            return None

        # Check for UITextureName on KnowledgeInfo
        if knowledge.ui_texture_name:
            return knowledge.ui_texture_name

        # Fallback: check KnowledgeGroupInfo
        group_key = knowledge.knowledge_group_key
        if group_key:
            group = self._knowledge_groups.get(group_key)
            if group and group.ui_texture_name:
                return group.ui_texture_name

        return None

    # =========================================================================
    # MAP MODE: FACTION NODES + KNOWLEDGE INFO (IMAGE-VERIFIED)
    # =========================================================================

    def load_faction_nodes_verified(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load FactionNodes - ONLY those with verified images.

        Args:
            folder: Path to faction info folder
            progress_callback: Optional callback

        Returns:
            Number of verified nodes loaded
        """
        if not self._dds_index.is_scanned:
            log.error("DDS index not scanned! Call scan_textures() first.")
            return 0

        self._faction_nodes_verified.clear()
        count = 0
        skipped = 0

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading FactionNodes from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for fn in root.iter("FactionNode"):
                strkey = fn.get("StrKey")
                if not strkey:
                    continue

                # Parse position
                pos_str = fn.get("WorldPosition") or ""
                parts = re.split(r"[,\s]+", pos_str.strip())
                if len(parts) < 3:
                    skipped += 1
                    continue

                try:
                    position = (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    skipped += 1
                    continue

                # Get attributes
                name_kr = (fn.get("Name") or "").strip()
                desc_kr = (fn.get("Desc") or "").replace("<br/>", "\n").strip()
                knowledge_key = (fn.get("KnowledgeKey") or "").strip()

                # RESOLVE UITextureName from KnowledgeKey
                ui_texture = self._resolve_texture_for_knowledge_key(knowledge_key)
                if not ui_texture:
                    skipped += 1
                    log.debug("FactionNode %s has no UITextureName via KnowledgeKey %s", strkey, knowledge_key)
                    continue  # No UITextureName - skip

                # VERIFY DDS exists
                dds_path = self._dds_index.find(ui_texture)
                if not dds_path:
                    skipped += 1
                    log.debug("FactionNode %s: DDS not found for %s", strkey, ui_texture)
                    continue  # DDS not found - skip

                # ONLY NOW create the verified node
                node = FactionNodeVerified(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    position=position,
                    ui_texture_name=ui_texture,
                    dds_path=dds_path,
                    knowledge_key=knowledge_key,
                    source_file=path.name,
                )

                self._faction_nodes_verified[strkey] = node
                count += 1

        self._stats['faction_nodes_verified'] = count
        self._stats['faction_nodes_skipped'] = skipped
        log.info("Loaded %d verified FactionNodes, skipped %d without images", count, skipped)
        return count

    def load_map_data_from_knowledge(
        self,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Add KnowledgeInfo entries with images to MAP mode as items.

        This allows searching KnowledgeInfo directly in MAP mode.
        KnowledgeInfo entries are added to _items collection.

        Args:
            progress_callback: Optional callback

        Returns:
            Number of knowledge entries with images added
        """
        if not self._dds_index.is_scanned:
            log.warning("DDS index not scanned - skipping knowledge data for MAP")
            return 0

        count = 0
        skipped = 0

        for strkey, ki in self._knowledge_info.items():
            ui_texture = ki.ui_texture_name
            if not ui_texture:
                skipped += 1
                continue

            # Verify DDS exists
            dds_path = self._dds_index.find(ui_texture)
            if not dds_path:
                skipped += 1
                continue

            # Add as ItemEntry to _items (can be searched in MAP mode)
            item = ItemEntry(
                strkey=strkey,
                name_kr=ki.name_kr,
                desc_kr=ki.desc_kr,
                ui_texture_name=ui_texture,
                dds_path=dds_path,
                group_name="",  # From KnowledgeInfo
                source_file=ki.source_file,
            )
            self._items[strkey] = item
            count += 1

        log.info("Added %d KnowledgeInfo entries with images for MAP mode, skipped %d", count, skipped)
        return count

    # =========================================================================
    # CHARACTER MODE: CHARACTERS (IMAGE-VERIFIED)
    # =========================================================================

    def load_characters_verified(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load CharacterInfo - ONLY those with verified images.

        Args:
            folder: Path to character info folder
            progress_callback: Optional callback

        Returns:
            Number of verified characters loaded
        """
        if not self._dds_index.is_scanned:
            log.error("DDS index not scanned! Call scan_textures() first.")
            return 0

        self._characters.clear()
        count = 0
        skipped = 0

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading Characters from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for char in root.iter("CharacterInfo"):
                strkey = char.get("StrKey")
                if not strkey:
                    continue

                name_kr = (char.get("CharacterName") or "").strip()
                group = (char.get("CharacterGroup") or "").strip()

                # Try to get UITextureName from nested Knowledge node
                ui_texture = None
                desc_kr = ""

                for knowledge in char.iter("Knowledge"):
                    ui_texture = (knowledge.get("UITextureName") or "").strip()
                    desc_kr = (knowledge.get("Desc") or "").replace("<br/>", "\n").strip()
                    # Prefer Knowledge.Name if available
                    knowledge_name = (knowledge.get("Name") or "").strip()
                    if knowledge_name:
                        name_kr = knowledge_name
                    if ui_texture:
                        break

                # Fallback to CharacterInfo.UIIconPath
                if not ui_texture:
                    ui_texture = (char.get("UIIconPath") or "").strip()

                if not ui_texture:
                    skipped += 1
                    continue  # No texture name

                # VERIFY DDS exists
                dds_path = self._dds_index.find(ui_texture)
                if not dds_path:
                    skipped += 1
                    continue  # DDS not found

                character = CharacterItem(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    ui_texture_name=ui_texture,
                    dds_path=dds_path,
                    group=group,
                    source_file=path.name,
                )

                self._characters[strkey] = character
                count += 1

        self._stats['characters_verified'] = count
        self._stats['characters_skipped'] = skipped
        log.info("Loaded %d verified Characters, skipped %d without images", count, skipped)
        return count

    # =========================================================================
    # ITEM MODE: ITEMS (IMAGE-VERIFIED)
    # =========================================================================

    def _find_ui_texture_in_element(self, elem) -> Optional[str]:
        """
        Find UITextureName from element or its children.

        Checks:
        1. Direct attribute on element
        2. Nested UIMapTextureInfo elements
        3. Nested LevelData/UIMapTextureInfo
        """
        # First check direct attribute
        ui_texture = (elem.get("UITextureName") or "").strip()
        if ui_texture:
            return ui_texture

        # Check nested UIMapTextureInfo
        for child in elem.iter("UIMapTextureInfo"):
            ui_texture = (child.get("UITextureName") or "").strip()
            if ui_texture:
                return ui_texture

        # Check nested Knowledge elements (for CharacterInfo)
        for child in elem.iter("Knowledge"):
            ui_texture = (child.get("UITextureName") or "").strip()
            if ui_texture:
                return ui_texture

        return None

    def load_items_verified(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None,
        require_image: bool = True
    ) -> int:
        """
        Load KnowledgeInfo items - with or without image verification.

        Args:
            folder: Path to knowledge info folder
            progress_callback: Optional callback
            require_image: If True, skip entries without valid DDS file

        Returns:
            Number of items loaded
        """
        if require_image and not self._dds_index.is_scanned:
            log.warning("DDS index not scanned - loading without image verification")
            require_image = False

        self._items.clear()
        count = 0
        skipped_no_texture = 0
        skipped_no_dds = 0

        # Debug: track texture names that weren't found
        missing_textures: List[str] = []

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading Items from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            # Track current group for items
            current_group = ""

            for elem in root.iter():
                if elem.tag == "KnowledgeGroupInfo":
                    current_group = (elem.get("GroupName") or "").strip()

                elif elem.tag == "KnowledgeInfo":
                    strkey = elem.get("StrKey")
                    if not strkey:
                        continue

                    # Try to find UITextureName (check element and children)
                    ui_texture = self._find_ui_texture_in_element(elem)

                    if not ui_texture:
                        skipped_no_texture += 1
                        continue  # No texture anywhere

                    # VERIFY DDS exists (if required)
                    dds_path = None
                    if require_image:
                        dds_path = self._dds_index.find(ui_texture)
                        if not dds_path:
                            skipped_no_dds += 1
                            if len(missing_textures) < 10:  # Log first 10
                                missing_textures.append(ui_texture)
                            continue  # DDS not found
                    else:
                        # No image verification - use placeholder path
                        dds_path = Path(f"placeholder/{ui_texture}.dds")

                    name_kr = (elem.get("Name") or "").strip()
                    desc_kr = (elem.get("Desc") or "").replace("<br/>", "\n").strip()

                    item = ItemEntry(
                        strkey=strkey,
                        name_kr=name_kr,
                        desc_kr=desc_kr,
                        ui_texture_name=ui_texture,
                        dds_path=dds_path,
                        group_name=current_group,
                        source_file=path.name,
                    )

                    self._items[strkey] = item
                    count += 1

        self._stats['items_verified'] = count
        self._stats['items_skipped'] = skipped_no_texture + skipped_no_dds
        self._stats['items_no_texture'] = skipped_no_texture
        self._stats['items_no_dds'] = skipped_no_dds

        log.info("Loaded %d Items: %d no texture, %d no DDS file",
                 count, skipped_no_texture, skipped_no_dds)

        if missing_textures:
            log.warning("Sample missing textures: %s", missing_textures[:5])

        return count

    # =========================================================================
    # ROUTES (FOR MAP)
    # =========================================================================

    def load_routes(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load route/waypoint data from XML files.

        Args:
            folder: Path to waypoint info folder
            progress_callback: Optional progress callback

        Returns:
            Number of routes loaded
        """
        count = 0

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading routes from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for wp in root.iter("NodeWayPointInfo"):
                key = wp.get("Key") or path.stem
                from_key = (wp.get("FromNodeKey") or "").strip()
                to_key = (wp.get("ToNodeKey") or "").strip()

                points: List[Tuple[float, float]] = []
                for wpos in wp.iter("WorldPosition"):
                    pos_str = wpos.get("Position") or ""
                    parts = re.split(r"[,\s]+", pos_str.strip())
                    if len(parts) >= 3:
                        try:
                            x, z = float(parts[0]), float(parts[2])
                            points.append((x, z))
                        except ValueError:
                            pass

                if points:
                    route = Route(
                        key=key,
                        from_key=from_key,
                        to_key=to_key,
                        points=points,
                    )
                    self._routes.append(route)
                    count += 1

        # Build adjacency map
        self._build_adjacency()

        log.info("Loaded %d routes", count)
        return count

    def _build_adjacency(self) -> None:
        """Build adjacency map from routes."""
        self._adjacency.clear()
        for route in self._routes:
            if route.from_key and route.to_key:
                if route.from_key not in self._adjacency:
                    self._adjacency[route.from_key] = set()
                if route.to_key not in self._adjacency:
                    self._adjacency[route.to_key] = set()
                self._adjacency[route.from_key].add(route.to_key)
                self._adjacency[route.to_key].add(route.from_key)

    # =========================================================================
    # ACCESSORS
    # =========================================================================

    @property
    def faction_nodes(self) -> Dict[str, FactionNodeVerified]:
        """Get all verified FactionNodes."""
        return self._faction_nodes_verified

    @property
    def characters(self) -> Dict[str, CharacterItem]:
        """Get all verified Characters."""
        return self._characters

    @property
    def items(self) -> Dict[str, ItemEntry]:
        """Get all verified Items."""
        return self._items

    @property
    def knowledge_info(self) -> Dict[str, KnowledgeInfo]:
        """Get all KnowledgeInfo entries."""
        return self._knowledge_info

    @property
    def knowledge_groups(self) -> Dict[str, KnowledgeGroupInfo]:
        """Get all KnowledgeGroupInfo entries."""
        return self._knowledge_groups

    @property
    def routes(self) -> List[Route]:
        """Get all routes."""
        return self._routes

    @property
    def adjacency(self) -> Dict[str, set]:
        """Get adjacency map for nodes."""
        return self._adjacency

    @property
    def stats(self) -> dict:
        """Get loading statistics."""
        return self._stats.copy()

    def get_node(self, strkey: str) -> Optional[FactionNodeVerified]:
        """Get verified FactionNode by StrKey."""
        return self._faction_nodes_verified.get(strkey)

    def get_character(self, strkey: str) -> Optional[CharacterItem]:
        """Get verified Character by StrKey."""
        return self._characters.get(strkey)

    def get_item(self, strkey: str) -> Optional[ItemEntry]:
        """Get verified Item by StrKey."""
        return self._items.get(strkey)

    def get_connected_nodes(self, strkey: str) -> List[str]:
        """Get list of StrKeys for nodes connected to given node."""
        return list(self._adjacency.get(strkey, set()))

    def get_routes_for_node(self, strkey: str) -> List[Route]:
        """Get routes that include the given node."""
        return [r for r in self._routes
                if r.from_key == strkey or r.to_key == strkey]

    # =========================================================================
    # LEGACY COMPATIBILITY
    # =========================================================================

    def resolve_ui_texture(self, strkey: str) -> Optional[str]:
        """
        Legacy method: Resolve UITextureName for a FactionNode StrKey.

        With image-first architecture, all verified nodes already have ui_texture_name.
        """
        node = self._faction_nodes_verified.get(strkey)
        if node:
            return node.ui_texture_name
        return None

    def get_texture_path(self, strkey: str, texture_folder: Path = None) -> Optional[Path]:
        """
        Legacy method: Get texture path for a FactionNode.

        With image-first architecture, verified nodes already have dds_path.
        """
        node = self._faction_nodes_verified.get(strkey)
        if node:
            return node.dds_path
        return None

    # Legacy loader (backward compatibility)
    def load_faction_nodes(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Legacy method: Load faction nodes.

        Redirects to load_faction_nodes_verified if DDS index is ready.
        """
        if self._dds_index.is_scanned:
            return self.load_faction_nodes_verified(folder, progress_callback)

        # Fallback to old behavior (without image verification)
        log.warning("Loading faction nodes without image verification (DDS not scanned)")
        return self._load_faction_nodes_legacy(folder, progress_callback)

    def _load_faction_nodes_legacy(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """Legacy faction node loading (without image verification)."""
        count = 0

        for path in iter_xml_files(folder):
            if progress_callback:
                progress_callback(f"Loading FactionNodes from {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for fn in root.iter("FactionNode"):
                strkey = fn.get("StrKey")
                if not strkey:
                    continue

                pos_str = fn.get("WorldPosition") or ""
                parts = re.split(r"[,\s]+", pos_str.strip())
                if len(parts) < 3:
                    continue

                try:
                    position = (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    continue

                name_kr = (fn.get("Name") or "").strip()
                desc_kr = (fn.get("Desc") or "").replace("<br/>", "\n").strip()
                knowledge_key = (fn.get("KnowledgeKey") or "").strip()

                # Resolve texture
                ui_texture = self._resolve_texture_for_knowledge_key(knowledge_key)
                dds_path = self._dds_index.find(ui_texture) if ui_texture else None

                # Create node (may not have image)
                if ui_texture and dds_path:
                    node = FactionNodeVerified(
                        strkey=strkey,
                        name_kr=name_kr,
                        desc_kr=desc_kr,
                        position=position,
                        ui_texture_name=ui_texture,
                        dds_path=dds_path,
                        knowledge_key=knowledge_key,
                        source_file=path.name,
                    )
                    self._faction_nodes_verified[strkey] = node
                    count += 1

        log.info("Loaded %d FactionNodes (legacy mode)", count)
        return count
