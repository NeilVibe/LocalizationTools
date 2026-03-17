"""WorldMap schemas for Interactive World Map.

Phase 20: Interactive World Map -- node positions, route connections,
coordinate bounds for SVG visualization.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class MapNode(BaseModel):
    """A single node on the world map (parsed from FactionNode)."""

    strkey: str
    knowledge_key: str
    name: str
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    region_type: str
    x: float
    z: float
    center_x: float = 0.0
    center_y: float = 0.0
    polygon_points: List[List[float]] = []
    danger_level: int = 1
    npcs: List[str] = []
    entity_type_counts: Dict[str, int] = {}


class MapRoute(BaseModel):
    """A route connecting two map nodes (parsed from NodeWaypointInfo)."""

    from_node: str
    to_node: str
    waypoints: List[Dict[str, float]] = []  # [{"x": float, "z": float}, ...]
    danger_level: int = 1
    travel_time: Optional[str] = None


class MegaRegion(BaseModel):
    """A large biome zone that tessellates the full map area."""

    id: str
    name_kr: str
    name_en: str
    biome: str  # forest, ruins, wasteland, lake, highlands, volcanic
    color: str  # accent color for overlay
    polygon: List[List[float]]  # world-coordinate polygon [[x,z], ...]
    node_strkeys: List[str] = []  # nodes contained in this region


class WorldMapData(BaseModel):
    """Complete world map dataset returned by the API."""

    nodes: List[MapNode]
    routes: List[MapRoute]
    bounds: Dict[str, float] = {}  # {"min_x", "max_x", "min_z", "max_z"}
    mega_regions: List[MegaRegion] = []
    background_image: Optional[str] = None  # URL path to background image
