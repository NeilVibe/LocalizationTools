"""
Linkage Module - SIMPLIFIED (Following DatasheetGenerator Pattern)

Data Collection Strategy:
1. Build knowledge lookup table FIRST (StrKey -> Name, UITextureName)
2. Collect ALL entries, don't filter by DDS existence
3. Mark entries that have verified images for prioritization
4. Support 3 modes: MAP (Region), CHARACTER, ITEM

Key difference from before: We DON'T filter out entries without images.
We collect everything, prioritize those with images.
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
# KNOWLEDGE LOOKUP (Built First - Like DatasheetGenerator)
# =============================================================================

@dataclass
class KnowledgeLookup:
    """Knowledge entry from KnowledgeInfo XML."""
    strkey: str
    name: str  # Korean display name
    desc: str  # Description
    ui_texture_name: str  # UITextureName attribute
    group_key: str = ""
    source_file: str = ""


# =============================================================================
# DATA STRUCTURES (Unified - All Modes)
# =============================================================================

@dataclass
class DataEntry:
    """
    Unified data entry for all modes.

    Used for MAP (Region), CHARACTER, and ITEM modes.
    Image is OPTIONAL - entries without images are still collected.
    """
    strkey: str
    name_kr: str  # Korean name (from Knowledge lookup)
    desc_kr: str  # Description
    ui_texture_name: str  # May be empty
    dds_path: Optional[Path]  # None if no DDS found
    has_image: bool  # True if DDS exists

    # Mode-specific fields
    position: Optional[Tuple[float, float, float]] = None  # MAP mode: WorldPosition
    group: str = ""  # Group/Category name
    knowledge_key: str = ""  # Key used for Knowledge lookup
    source_file: str = ""
    entry_type: str = ""  # Type of entry (for sorting)

    @property
    def position_2d(self) -> Optional[Tuple[float, float]]:
        """Get 2D position (x, z) for map display."""
        if self.position:
            return (self.position[0], self.position[2])
        return None


# =============================================================================
# DDS INDEX (Texture Lookup)
# =============================================================================

class DDSIndex:
    """Index of available DDS files for texture lookup."""

    def __init__(self):
        self._texture_folder: Optional[Path] = None
        self._dds_files: Dict[str, Path] = {}  # lowercase name -> full path
        self._scanned = False

    def scan_folder(self, texture_folder: Path, progress_callback=None) -> int:
        """Scan texture folder for DDS files."""
        self._texture_folder = texture_folder
        self._dds_files.clear()

        if not texture_folder or not texture_folder.exists():
            log.warning("Texture folder not found: %s", texture_folder)
            return 0

        if progress_callback:
            progress_callback(f"Scanning {texture_folder}...")

        count = 0
        for dds_path in texture_folder.rglob("*.dds"):
            name_lower = dds_path.stem.lower()
            self._dds_files[name_lower] = dds_path
            self._dds_files[dds_path.name.lower()] = dds_path
            count += 1

        self._scanned = True
        log.info("Indexed %d DDS files from %s", count, texture_folder)
        return count

    def find(self, ui_texture_name: str) -> Optional[Path]:
        """Find DDS file for texture name."""
        if not ui_texture_name:
            return None

        original_name = ui_texture_name
        name = ui_texture_name.lower().strip()

        # Remove path components
        if '/' in name or '\\' in name:
            name = name.replace('\\', '/').split('/')[-1]

        # Remove .dds extension if present for lookup
        lookup_name = name
        if lookup_name.endswith('.dds'):
            lookup_name = lookup_name[:-4]

        # Try without extension
        if lookup_name in self._dds_files:
            return self._dds_files[lookup_name]

        # Try with .dds extension
        if name in self._dds_files:
            return self._dds_files[name]

        # Try adding .dds
        name_with_ext = lookup_name + '.dds'
        if name_with_ext in self._dds_files:
            return self._dds_files[name_with_ext]

        # Log first few misses for debugging
        if not hasattr(self, '_miss_count'):
            self._miss_count = 0
        if self._miss_count < 10:
            log.debug("DDS not found: '%s' (tried: %s, %s)", original_name, lookup_name, name_with_ext)
            self._miss_count += 1

        return None

    @property
    def is_scanned(self) -> bool:
        return self._scanned

    @property
    def file_count(self) -> int:
        return len(self._dds_files) // 2  # Each file indexed twice


# =============================================================================
# LINKAGE RESOLVER (SIMPLIFIED)
# =============================================================================

class LinkageResolver:
    """
    Resolves and collects data following DatasheetGenerator pattern.

    Pattern:
    1. Build knowledge lookup table FIRST
    2. Collect all entries (don't filter by image)
    3. Mark entries with verified images for prioritization
    """

    def __init__(self):
        self._dds_index = DDSIndex()

        # Knowledge lookup (built first!)
        self._knowledge_lookup: Dict[str, KnowledgeLookup] = {}

        # Unified data collection (all modes use DataEntry)
        self._entries: Dict[str, DataEntry] = {}

        # Track which mode's data is currently loaded
        self._current_mode: Optional[DataMode] = None

        # Stats
        self._stats = {
            'knowledge_loaded': 0,
            'entries_total': 0,
            'entries_with_image': 0,
            'entries_without_image': 0,
        }

    @property
    def current_mode(self) -> Optional[DataMode]:
        """Return which mode's data is currently loaded."""
        return self._current_mode

    # =========================================================================
    # DDS INDEX
    # =========================================================================

    def scan_textures(self, texture_folder: Path, progress_callback=None) -> int:
        """Scan texture folder for DDS files."""
        return self._dds_index.scan_folder(texture_folder, progress_callback)

    @property
    def dds_index(self) -> DDSIndex:
        return self._dds_index

    # =========================================================================
    # STEP 1: BUILD KNOWLEDGE LOOKUP (Like DatasheetGenerator)
    # =========================================================================

    def build_knowledge_lookup(
        self,
        knowledge_folder: Path,
        progress_callback=None
    ) -> int:
        """
        Build knowledge lookup table from KnowledgeInfo XML files.

        This MUST be called first before loading other data!
        Maps: StrKey -> (Name, UITextureName, Desc)
        """
        self._knowledge_lookup.clear()

        if not knowledge_folder or not knowledge_folder.exists():
            log.error("Knowledge folder not found: %s", knowledge_folder)
            return 0

        log.info("Building knowledge lookup from: %s", knowledge_folder)
        count = 0

        for path in iter_xml_files(knowledge_folder):
            if progress_callback:
                progress_callback(f"Reading {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            # Parse ALL KnowledgeInfo elements
            for ki in root.iter("KnowledgeInfo"):
                strkey = (ki.get("StrKey") or "").strip()
                if not strkey:
                    continue

                name = (ki.get("Name") or "").strip()
                desc = (ki.get("Desc") or "").replace("<br/>", "\n").strip()
                ui_texture = (ki.get("UITextureName") or "").strip()
                group_key = (ki.get("KnowledgeGroupKey") or "").strip()

                lookup = KnowledgeLookup(
                    strkey=strkey,
                    name=name,
                    desc=desc,
                    ui_texture_name=ui_texture,
                    group_key=group_key,
                    source_file=path.name
                )

                self._knowledge_lookup[strkey] = lookup
                count += 1

        self._stats['knowledge_loaded'] = count
        log.info("Knowledge lookup: %d entries", count)

        # Log sample entries with textures
        with_texture = sum(1 for k in self._knowledge_lookup.values() if k.ui_texture_name)
        log.info("  - With UITextureName: %d", with_texture)

        return count

    def get_knowledge(self, strkey: str) -> Optional[KnowledgeLookup]:
        """Get knowledge entry by StrKey."""
        return self._knowledge_lookup.get(strkey)

    # =========================================================================
    # STEP 2: LOAD ENTRIES (All Modes)
    # =========================================================================

    def load_map_data(
        self,
        faction_folder: Path,
        progress_callback=None
    ) -> int:
        """
        Load MAP (Region) data from FactionNode XML files.

        Uses knowledge lookup to get display names and UITextureName.
        Does NOT filter by image existence - collects everything.
        """
        self._entries.clear()
        self._current_mode = DataMode.MAP
        count = 0
        with_image = 0

        if not faction_folder or not faction_folder.exists():
            log.error("Faction folder not found: %s", faction_folder)
            return 0

        log.info("Loading MAP data from: %s", faction_folder)

        for path in iter_xml_files(faction_folder):
            if progress_callback:
                progress_callback(f"Loading {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for fn in root.iter("FactionNode"):
                strkey = (fn.get("StrKey") or "").strip()
                if not strkey:
                    continue

                # Skip duplicates
                if strkey in self._entries:
                    continue

                # Get attributes
                name_kr = (fn.get("Name") or "").strip()
                desc_kr = (fn.get("Desc") or "").replace("<br/>", "\n").strip()
                knowledge_key = (fn.get("KnowledgeKey") or "").strip()
                node_type = (fn.get("Type") or "").strip()

                # Lookup from Knowledge table
                ui_texture = ""
                if knowledge_key:
                    knowledge = self._knowledge_lookup.get(knowledge_key)
                    if knowledge:
                        if not name_kr:
                            name_kr = knowledge.name
                        if not desc_kr:
                            desc_kr = knowledge.desc
                        ui_texture = knowledge.ui_texture_name

                # Parse position
                position = None
                pos_str = (fn.get("WorldPosition") or "").strip()
                if pos_str:
                    parts = re.split(r"[,\s]+", pos_str)
                    if len(parts) >= 3:
                        try:
                            position = (float(parts[0]), float(parts[1]), float(parts[2]))
                        except ValueError:
                            pass

                # Check if DDS exists (but don't filter!)
                dds_path = self._dds_index.find(ui_texture) if ui_texture else None
                has_image = dds_path is not None

                if has_image:
                    with_image += 1

                entry = DataEntry(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    ui_texture_name=ui_texture,
                    dds_path=dds_path,
                    has_image=has_image,
                    position=position,
                    knowledge_key=knowledge_key,
                    source_file=path.name,
                    entry_type=node_type,
                )

                self._entries[strkey] = entry
                count += 1

        # ALSO add KnowledgeInfo entries with images (for direct Knowledge search)
        for strkey, knowledge in self._knowledge_lookup.items():
            if strkey in self._entries:
                continue  # Already added via FactionNode

            if not knowledge.name:
                continue  # Skip entries without name

            ui_texture = knowledge.ui_texture_name
            dds_path = self._dds_index.find(ui_texture) if ui_texture else None
            has_image = dds_path is not None

            if has_image:
                with_image += 1

            entry = DataEntry(
                strkey=strkey,
                name_kr=knowledge.name,
                desc_kr=knowledge.desc,
                ui_texture_name=ui_texture,
                dds_path=dds_path,
                has_image=has_image,
                position=None,
                knowledge_key=strkey,
                source_file=knowledge.source_file,
                entry_type="Knowledge",
            )

            self._entries[strkey] = entry
            count += 1

        self._stats['entries_total'] = count
        self._stats['entries_with_image'] = with_image
        self._stats['entries_without_image'] = count - with_image
        # Mode-specific stats for app.py compatibility
        self._stats['faction_nodes_verified'] = with_image
        self._stats['faction_nodes_skipped'] = count - with_image

        log.info("Loaded %d MAP entries: %d with image, %d without",
                 count, with_image, count - with_image)

        return count

    def load_character_data(
        self,
        character_folder: Path,
        progress_callback=None
    ) -> int:
        """Load CHARACTER data from CharacterInfo XML files."""
        self._entries.clear()
        self._current_mode = DataMode.CHARACTER
        count = 0
        with_image = 0

        if not character_folder or not character_folder.exists():
            log.error("Character folder not found: %s", character_folder)
            return 0

        log.info("Loading CHARACTER data from: %s", character_folder)

        for path in iter_xml_files(character_folder):
            if progress_callback:
                progress_callback(f"Loading {path.name}...")

            root = parse_xml(path)
            if root is None:
                continue

            for char in root.iter("CharacterInfo"):
                strkey = (char.get("StrKey") or "").strip()
                if not strkey:
                    continue

                if strkey in self._entries:
                    continue

                name_kr = (char.get("CharacterName") or "").strip()
                group = (char.get("CharacterGroup") or "").strip()

                # Get UITextureName from nested Knowledge or UIIconPath
                ui_texture = ""
                desc_kr = ""

                for knowledge in char.iter("Knowledge"):
                    ui_texture = (knowledge.get("UITextureName") or "").strip()
                    desc_kr = (knowledge.get("Desc") or "").replace("<br/>", "\n").strip()
                    knowledge_name = (knowledge.get("Name") or "").strip()
                    if knowledge_name:
                        name_kr = knowledge_name
                    if ui_texture:
                        break

                if not ui_texture:
                    ui_texture = (char.get("UIIconPath") or "").strip()

                # Check DDS
                dds_path = self._dds_index.find(ui_texture) if ui_texture else None
                has_image = dds_path is not None

                if has_image:
                    with_image += 1

                entry = DataEntry(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    ui_texture_name=ui_texture,
                    dds_path=dds_path,
                    has_image=has_image,
                    group=group,
                    source_file=path.name,
                    entry_type="Character",
                )

                self._entries[strkey] = entry
                count += 1

        self._stats['entries_total'] = count
        self._stats['entries_with_image'] = with_image
        self._stats['entries_without_image'] = count - with_image
        # Mode-specific stats for app.py compatibility
        self._stats['characters_verified'] = with_image
        self._stats['characters_skipped'] = count - with_image

        log.info("Loaded %d CHARACTER entries: %d with image, %d without",
                 count, with_image, count - with_image)

        return count

    def load_item_data(
        self,
        knowledge_folder: Path,
        progress_callback=None
    ) -> int:
        """Load ITEM data directly from KnowledgeInfo (already in lookup)."""
        self._entries.clear()
        self._current_mode = DataMode.ITEM
        count = 0
        with_image = 0

        log.info("Loading ITEM data from knowledge lookup...")

        # Track current group
        current_group = ""

        # Re-parse to get group info
        if knowledge_folder and knowledge_folder.exists():
            for path in iter_xml_files(knowledge_folder):
                if progress_callback:
                    progress_callback(f"Loading {path.name}...")

                root = parse_xml(path)
                if root is None:
                    continue

                # Reset group for each file to avoid leaking across files
                current_group = ""

                for elem in root.iter():
                    if elem.tag == "KnowledgeGroupInfo":
                        current_group = (elem.get("GroupName") or "").strip()

                    elif elem.tag == "KnowledgeInfo":
                        strkey = (elem.get("StrKey") or "").strip()
                        if not strkey or strkey in self._entries:
                            continue

                        name_kr = (elem.get("Name") or "").strip()
                        desc_kr = (elem.get("Desc") or "").replace("<br/>", "\n").strip()
                        ui_texture = (elem.get("UITextureName") or "").strip()

                        if not name_kr:
                            continue

                        dds_path = self._dds_index.find(ui_texture) if ui_texture else None
                        has_image = dds_path is not None

                        if has_image:
                            with_image += 1

                        entry = DataEntry(
                            strkey=strkey,
                            name_kr=name_kr,
                            desc_kr=desc_kr,
                            ui_texture_name=ui_texture,
                            dds_path=dds_path,
                            has_image=has_image,
                            group=current_group,
                            source_file=path.name,
                            entry_type="Item",
                        )

                        self._entries[strkey] = entry
                        count += 1

        self._stats['entries_total'] = count
        self._stats['entries_with_image'] = with_image
        self._stats['entries_without_image'] = count - with_image
        # Mode-specific stats for app.py compatibility
        self._stats['items_verified'] = with_image
        self._stats['items_skipped'] = count - with_image

        log.info("Loaded %d ITEM entries: %d with image, %d without",
                 count, with_image, count - with_image)

        return count

    # =========================================================================
    # ACCESSORS
    # =========================================================================

    @property
    def entries(self) -> Dict[str, DataEntry]:
        """Get all entries."""
        return self._entries

    @property
    def knowledge_lookup(self) -> Dict[str, KnowledgeLookup]:
        """Get knowledge lookup table."""
        return self._knowledge_lookup

    @property
    def stats(self) -> dict:
        return self._stats.copy()

    def get_entry(self, strkey: str) -> Optional[DataEntry]:
        """Get entry by StrKey."""
        return self._entries.get(strkey)

    # Legacy compatibility (mode-aware - returns empty if wrong mode)
    @property
    def faction_nodes(self) -> Dict[str, DataEntry]:
        """Legacy: Get MAP entries (only valid if current_mode == MAP)."""
        if self._current_mode != DataMode.MAP:
            return {}
        return self._entries

    @property
    def characters(self) -> Dict[str, DataEntry]:
        """Legacy: Get CHARACTER entries (only valid if current_mode == CHARACTER)."""
        if self._current_mode != DataMode.CHARACTER:
            return {}
        return self._entries

    @property
    def items(self) -> Dict[str, DataEntry]:
        """Legacy: Get ITEM entries (only valid if current_mode == ITEM)."""
        if self._current_mode != DataMode.ITEM:
            return {}
        return self._entries

    def get_node(self, strkey: str) -> Optional[DataEntry]:
        """Legacy: Get node by strkey."""
        return self._entries.get(strkey)

    def get_character(self, strkey: str) -> Optional[DataEntry]:
        """Legacy: Get character by strkey."""
        return self._entries.get(strkey)

    def get_item(self, strkey: str) -> Optional[DataEntry]:
        """Legacy: Get item by strkey."""
        return self._entries.get(strkey)
