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

from server.tools.ldm.schemas.worldmap import MapNode, MapRoute, MegaRegion, WorldMapData

# Bounds expansion padding so mega-region polygons extend past outermost nodes
_BOUNDS_PADDING = 60


def _safe_float(parts: List[str], index: int, label: str) -> float:
    """Extract a float from a split coordinate list, defaulting to 0.0 on error."""
    if index >= len(parts):
        return 0.0
    try:
        return float(parts[index])
    except ValueError:
        logger.warning(f"[WorldMap] Malformed coordinate {label}, defaulting to 0.0")
        return 0.0


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
            x = _safe_float(parts, 0, f"X in '{world_pos}' for {strkey}")
            z = _safe_float(parts, 2, f"Z in '{world_pos}' for {strkey}")

            # Parse new showcase fields
            danger_level = int(node_el.get("DangerLevel", "1"))
            name_kr = node_el.get("NameKR", "")
            name_en = node_el.get("NameEN", "")
            description_kr = node_el.get("DescriptionKR", "")

            # Parse polygon child element
            polygon_points: List[List[float]] = []
            polygon_el = node_el.find("Polygon")
            if polygon_el is not None:
                pts_str = polygon_el.get("Points", "")
                if pts_str:
                    for pt in pts_str.split(";"):
                        coords = pt.strip().split(",")
                        if len(coords) >= 2:
                            try:
                                polygon_points.append([float(coords[0]), float(coords[1])])
                            except ValueError:
                                pass

            # Name priority: name_kr > name_en > strkey
            display_name = name_kr or name_en or strkey

            self._nodes[strkey] = MapNode(
                strkey=strkey,
                knowledge_key=knowledge_key,
                name=display_name,
                name_kr=name_kr or None,
                name_en=name_en or None,
                description=description_kr or None,
                region_type=region_type,
                x=x,
                z=z,
                center_x=x,
                center_y=z,
                polygon_points=polygon_points,
                danger_level=danger_level,
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

            # Parse new showcase fields
            danger_level = int(waypoint_el.get("DangerLevel", "1"))
            travel_time = waypoint_el.get("TravelTime", None)

            self._routes.append(MapRoute(
                from_node=from_node,
                to_node=to_node,
                waypoints=waypoints,
                danger_level=danger_level,
                travel_time=travel_time,
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

    def _build_mega_regions(self, bounds: Dict[str, float]) -> List[MegaRegion]:
        """Build 6 tessellating mega-region polygons covering the full map.

        Layout matches the AI-generated background image:
        ┌────────────┬─────────────┬────────────┐
        │  Mist Forest │ Sealed Ruins │ Dark Lands │
        ├──────┬──────┴──────┬──────┴────────────┤
        │ Moon │  Highlands  │    Volcanic        │
        │ Lake │   (center)  │     Zone           │
        └──────┴─────────────┴────────────────────┘
        """
        if not bounds:
            return []

        # Expand bounds slightly for full coverage
        x0 = bounds.get("min_x", 100) - _BOUNDS_PADDING
        x1 = bounds.get("max_x", 750) + _BOUNDS_PADDING
        z0 = bounds.get("min_z", 150) - _BOUNDS_PADDING
        z1 = bounds.get("max_z", 650) + _BOUNDS_PADDING

        # Dividing lines
        mid_x = (x0 + x1) / 2  # ~425
        left_x = x0 + (x1 - x0) * 0.33  # ~307
        right_x = x0 + (x1 - x0) * 0.66  # ~614
        mid_z = (z0 + z1) / 2  # ~395

        # Organic offsets to avoid grid-look
        jog = 30

        regions = [
            MegaRegion(
                id="mega_mist_forest",
                name_kr="안개의 숲",
                name_en="Mist Forest",
                biome="forest",
                color="#1a6b3a",
                polygon=[
                    [x0, z0], [left_x + jog, z0],
                    [left_x - jog, mid_z - jog],
                    [x0, mid_z + jog],
                ],
                node_strkeys=["mist_forest", "moonlight_lake"],
            ),
            MegaRegion(
                id="mega_sealed_ruins",
                name_kr="봉인된 유적",
                name_en="Sealed Ruins",
                biome="ruins",
                color="#8b6914",
                polygon=[
                    [left_x + jog, z0], [right_x - jog, z0],
                    [right_x + jog, mid_z - jog],
                    [mid_x, mid_z + jog],
                    [left_x - jog, mid_z - jog],
                ],
                node_strkeys=["sealed_library", "sage_tower"],
            ),
            MegaRegion(
                id="mega_dark_lands",
                name_kr="어둠의 땅",
                name_en="Dark Lands",
                biome="wasteland",
                color="#6b1a6b",
                polygon=[
                    [right_x - jog, z0], [x1, z0],
                    [x1, mid_z + jog],
                    [right_x + jog, mid_z - jog],
                ],
                node_strkeys=["dark_cult_hq", "blackstar_village"],
            ),
            MegaRegion(
                id="mega_moonlight_valley",
                name_kr="달빛 골짜기",
                name_en="Moonlight Valley",
                biome="lake",
                color="#1a4b6b",
                polygon=[
                    [x0, mid_z + jog],
                    [left_x - jog, mid_z - jog],
                    [mid_x - jog, mid_z + jog],
                    [left_x, z1],
                    [x0, z1],
                ],
                node_strkeys=["dragon_tomb"],
            ),
            MegaRegion(
                id="mega_central_highlands",
                name_kr="중앙 고원",
                name_en="Central Highlands",
                biome="highlands",
                color="#6b5a1a",
                polygon=[
                    [mid_x - jog, mid_z + jog],
                    [mid_x, mid_z + jog],
                    [right_x + jog, mid_z - jog],
                    [right_x, mid_z + jog],
                    [right_x - jog, z1],
                    [left_x, z1],
                ],
                node_strkeys=["wind_canyon", "forgotten_fortress"],
            ),
            MegaRegion(
                id="mega_volcanic_zone",
                name_kr="화산 지대",
                name_en="Volcanic Zone",
                biome="volcanic",
                color="#8b2a0a",
                polygon=[
                    [right_x + jog, mid_z - jog],
                    [x1, mid_z + jog],
                    [x1, z1],
                    [right_x - jog, z1],
                    [right_x, mid_z + jog],
                ],
                node_strkeys=["volcanic_zone"],
            ),
        ]

        return regions

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

        # Build mega-regions (6 tessellating biome zones)
        mega_regions = self._build_mega_regions(bounds)

        return WorldMapData(
            nodes=nodes,
            routes=self._routes,
            bounds=bounds,
            mega_regions=mega_regions,
            background_image="/map_background.png",
        )


# =============================================================================
# Module-level singleton (same pattern as CodexService)
# =============================================================================

# Will be set by route layer or manually in tests
codex_service = None
