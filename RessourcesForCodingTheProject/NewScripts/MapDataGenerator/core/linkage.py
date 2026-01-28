"""
Linkage Module

Resolves the multi-step linkage chain:
    FactionNode.StrKey
    → FactionNode.KnowledgeKey
    → KnowledgeInfo.UITextureName
    → (or KnowledgeGroupInfo.UITextureName)
    → .dds file path

This module handles:
- FactionNode parsing (location nodes on the map)
- KnowledgeInfo parsing (for UITextureName resolution)
- KnowledgeGroupInfo parsing (fallback for UITextureName)
- Route/waypoint parsing for map visualization
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .xml_parser import parse_xml, iter_xml_files

log = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FactionNode:
    """Represents a FactionNode (map location)."""
    strkey: str
    name_kr: str
    desc_kr: str
    position: Tuple[float, float, float]  # (x, y, z)
    knowledge_key: str = ""
    source_file: str = ""

    @property
    def position_2d(self) -> Tuple[float, float]:
        """Get 2D position (x, z) for map display."""
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
# LINKAGE RESOLVER
# =============================================================================

class LinkageResolver:
    """
    Resolves linkage between FactionNode and UITextureName.

    The resolution chain is:
    1. FactionNode.KnowledgeKey → KnowledgeInfo.StrKey
    2. KnowledgeInfo.UITextureName (if present)
    3. OR: KnowledgeInfo.KnowledgeGroupKey → KnowledgeGroupInfo.StrKey
    4. KnowledgeGroupInfo.UITextureName (fallback)
    """

    def __init__(self):
        self._faction_nodes: Dict[str, FactionNode] = {}
        self._knowledge_info: Dict[str, KnowledgeInfo] = {}
        self._knowledge_groups: Dict[str, KnowledgeGroupInfo] = {}
        self._routes: List[Route] = []
        self._adjacency: Dict[str, set] = {}

    def load_faction_nodes(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load FactionNode data from XML files.

        Args:
            folder: Path to faction info folder
            progress_callback: Optional progress callback

        Returns:
            Number of nodes loaded
        """
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

                name_kr = (fn.get("Name") or "").strip()
                desc_kr = (fn.get("Desc") or "").replace("<br/>", "\n").strip()
                knowledge_key = (fn.get("KnowledgeKey") or "").strip()

                # Parse WorldPosition
                pos_str = fn.get("WorldPosition") or ""
                parts = re.split(r"[,\s]+", pos_str.strip())
                if len(parts) >= 3:
                    try:
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        position = (x, y, z)
                    except ValueError:
                        continue
                else:
                    continue

                node = FactionNode(
                    strkey=strkey,
                    name_kr=name_kr,
                    desc_kr=desc_kr,
                    position=position,
                    knowledge_key=knowledge_key,
                    source_file=path.name,
                )

                self._faction_nodes[strkey] = node
                count += 1

        log.info("Loaded %d FactionNodes", count)
        return count

    def load_knowledge_info(
        self,
        folder: Path,
        progress_callback: Optional[callable] = None
    ) -> int:
        """
        Load KnowledgeInfo data from XML files.

        Args:
            folder: Path to knowledge info folder
            progress_callback: Optional progress callback

        Returns:
            Number of knowledge entries loaded
        """
        count = 0

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

            # Also parse KnowledgeGroupInfo elements for UITextureName fallback
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

        log.info("Loaded %d KnowledgeInfo entries, %d KnowledgeGroupInfo entries",
                 count, len(self._knowledge_groups))
        return count

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

    def resolve_ui_texture(self, strkey: str) -> Optional[str]:
        """
        Resolve UITextureName for a FactionNode StrKey.

        Resolution chain:
        1. FactionNode.KnowledgeKey → KnowledgeInfo.StrKey
        2. KnowledgeInfo.UITextureName (if present)
        3. OR: KnowledgeInfo.KnowledgeGroupKey → KnowledgeGroupInfo.StrKey
        4. KnowledgeGroupInfo.UITextureName (fallback)

        Args:
            strkey: FactionNode StrKey

        Returns:
            UITextureName or None if not found
        """
        # Get FactionNode
        node = self._faction_nodes.get(strkey)
        if not node:
            return None

        # Get KnowledgeInfo via KnowledgeKey
        knowledge_key = node.knowledge_key
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

    def get_texture_path(self, strkey: str, texture_folder: Path) -> Optional[Path]:
        """
        Get full path to texture file for a FactionNode.

        Args:
            strkey: FactionNode StrKey
            texture_folder: Base folder for textures

        Returns:
            Path to .dds file or None if not found
        """
        ui_texture = self.resolve_ui_texture(strkey)
        if not ui_texture:
            return None

        # UITextureName might be just the name or include path
        # Try to find the file
        if not ui_texture.lower().endswith('.dds'):
            ui_texture += '.dds'

        # Try direct path
        direct_path = texture_folder / ui_texture
        if direct_path.exists():
            return direct_path

        # Try searching in subfolders
        for dds_path in texture_folder.rglob(ui_texture):
            return dds_path

        return None

    # =============================================================================
    # ACCESSORS
    # =============================================================================

    @property
    def faction_nodes(self) -> Dict[str, FactionNode]:
        """Get all FactionNodes."""
        return self._faction_nodes

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

    def get_node(self, strkey: str) -> Optional[FactionNode]:
        """Get FactionNode by StrKey."""
        return self._faction_nodes.get(strkey)

    def get_connected_nodes(self, strkey: str) -> List[str]:
        """Get list of StrKeys for nodes connected to given node."""
        return list(self._adjacency.get(strkey, set()))

    def get_routes_for_node(self, strkey: str) -> List[Route]:
        """Get routes that include the given node."""
        return [r for r in self._routes
                if r.from_key == strkey or r.to_key == strkey]
