"""WorldMap Service -- FactionNode positions, waypoint routes, Codex enrichment.

Phase 20: Interactive World Map -- parses FactionNode XML for map node positions,
NodeWaypointInfo for route connections, and enriches with Codex entity data.
"""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from lxml import etree

from server.tools.ldm.schemas.worldmap import MapNode, MapRoute, WorldMapData


class WorldMapService:
    """Parses world map data from StaticInfo XML and enriches with Codex."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self._nodes: Dict[str, MapNode] = {}
        self._routes: List[MapRoute] = []
        self._initialized = False

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize(self) -> None:
        """Full initialization: parse nodes, waypoints, enrich with Codex."""
        if self._initialized:
            return

        logger.info("[WorldMap] Initializing world map service...")
        t0 = time.time()

        self._parse_faction_nodes()
        self._parse_waypoints()
        self._enrich_with_codex()

        elapsed = time.time() - t0
        logger.info(
            f"[WorldMap] Initialized: {len(self._nodes)} nodes, "
            f"{len(self._routes)} routes in {elapsed:.2f}s"
        )
        self._initialized = True

    # =========================================================================
    # FactionNode parsing
    # =========================================================================

    def _parse_faction_nodes(self) -> None:
        """Parse FactionInfo.staticinfo.xml for FactionNode positions."""
        xml_path = (
            self.base_dir / "StaticInfo" / "factioninfo"
            / "FactionInfo.staticinfo.xml"
        )

        if not xml_path.is_file():
            logger.warning(f"[WorldMap] FactionInfo XML not found: {xml_path}")
            return

        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        for node_el in root.iter("FactionNode"):
            strkey = node_el.get("StrKey")
            if not strkey:
                continue

            knowledge_key = node_el.get("KnowledgeKey", "")
            region_type = node_el.get("Type", "Unknown")

            # Parse WorldPosition "X,0,Z" format
            world_pos = node_el.get("WorldPosition", "0,0,0")
            parts = world_pos.split(",")
            try:
                x = float(parts[0]) if len(parts) >= 1 else 0.0
            except ValueError:
                logger.warning(f"[WorldMap] Malformed X coordinate in WorldPosition '{world_pos}' for {strkey}, defaulting to 0.0")
                x = 0.0
            try:
                z = float(parts[2]) if len(parts) >= 3 else 0.0
            except (ValueError, IndexError):
                logger.warning(f"[WorldMap] Malformed Z coordinate in WorldPosition '{world_pos}' for {strkey}, defaulting to 0.0")
                z = 0.0

            self._nodes[strkey] = MapNode(
                strkey=strkey,
                knowledge_key=knowledge_key,
                name=strkey,  # fallback; enriched by Codex later
                region_type=region_type,
                x=x,
                z=z,
            )

        logger.debug(f"[WorldMap] Parsed {len(self._nodes)} FactionNode positions")

    # =========================================================================
    # Waypoint route parsing
    # =========================================================================

    def _parse_waypoints(self) -> None:
        """Parse NodeWaypointInfo.staticinfo.xml for route connections."""
        xml_path = (
            self.base_dir / "StaticInfo" / "factioninfo"
            / "NodeWaypointInfo" / "NodeWaypointInfo.staticinfo.xml"
        )

        if not xml_path.is_file():
            logger.warning(f"[WorldMap] NodeWaypointInfo XML not found: {xml_path}")
            return

        tree = etree.parse(str(xml_path))
        root = tree.getroot()

        for waypoint_el in root.iter("NodeWaypointInfo"):
            from_node = waypoint_el.get("FromNodeKey", "")
            to_node = waypoint_el.get("ToNodeKey", "")

            if not from_node or not to_node:
                continue

            # Parse child WorldPosition elements
            waypoints: List[Dict[str, float]] = []
            for wp_el in waypoint_el.findall("WorldPosition"):
                x = float(wp_el.get("X", "0"))
                z = float(wp_el.get("Z", "0"))
                waypoints.append({"x": x, "z": z})

            self._routes.append(MapRoute(
                from_node=from_node,
                to_node=to_node,
                waypoints=waypoints,
            ))

        logger.debug(f"[WorldMap] Parsed {len(self._routes)} waypoint routes")

    # =========================================================================
    # Codex enrichment
    # =========================================================================

    def _enrich_with_codex(self) -> None:
        """Enrich nodes with Codex entity data (names, descriptions, NPCs)."""
        # Lazy import to avoid circular dependencies and ensure service is available
        svc = codex_service
        if svc is None:
            try:
                from server.tools.ldm.services.codex_service import CodexService
                svc = CodexService(base_dir=self.base_dir)
                logger.debug("[WorldMap] Created CodexService instance for enrichment")
            except Exception as exc:
                logger.debug(f"[WorldMap] CodexService unavailable ({exc}), using fallback names")
                return

        try:
            if not getattr(svc, "_initialized", False):
                svc.initialize()

            response = svc.list_entities("region")

            # Build lookup: knowledge_key -> CodexEntity
            by_knowledge_key = {}
            for entity in response.entities:
                if entity.knowledge_key:
                    by_knowledge_key[entity.knowledge_key] = entity

            for strkey, node in self._nodes.items():
                entity = by_knowledge_key.get(node.knowledge_key)
                if entity is None:
                    continue

                # Enrich name and description
                if entity.name:
                    node.name = entity.name
                if entity.description:
                    node.description = entity.description

                # Parse related_entities for NPCs and type counts
                type_counts: Counter = Counter()
                npcs: List[str] = []
                for ref in entity.related_entities:
                    if "/" in ref:
                        ref_type, ref_key = ref.split("/", 1)
                        type_counts[ref_type] += 1
                        if ref_type == "character":
                            npcs.append(ref_key)

                node.npcs = npcs
                node.entity_type_counts = dict(type_counts)

        except Exception as e:
            logger.warning(f"[WorldMap] Codex enrichment failed (using fallbacks): {e}")

    # =========================================================================
    # Public API
    # =========================================================================

    def get_map_data(self) -> WorldMapData:
        """Return complete world map dataset. Lazy-initializes on first call."""
        if not self._initialized:
            self.initialize()

        nodes = list(self._nodes.values())

        # Compute bounds
        bounds: Dict[str, float] = {}
        if nodes:
            xs = [n.x for n in nodes]
            zs = [n.z for n in nodes]
            bounds = {
                "min_x": min(xs),
                "max_x": max(xs),
                "min_z": min(zs),
                "max_z": max(zs),
            }

        return WorldMapData(
            nodes=nodes,
            routes=self._routes,
            bounds=bounds,
        )


# =============================================================================
# Module-level singleton (same pattern as CodexService)
# =============================================================================

# Will be set by route layer or manually in tests
codex_service = None
