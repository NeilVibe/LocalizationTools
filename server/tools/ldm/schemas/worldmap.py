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
    description: Optional[str] = None
    region_type: str
    x: float
    z: float
    npcs: List[str] = []
    entity_type_counts: Dict[str, int] = {}


class MapRoute(BaseModel):
    """A route connecting two map nodes (parsed from NodeWaypointInfo)."""

    from_node: str
    to_node: str
    waypoints: List[Dict[str, float]] = []  # [{"x": float, "z": float}, ...]


class WorldMapData(BaseModel):
    """Complete world map dataset returned by the API."""

    nodes: List[MapNode]
    routes: List[MapRoute]
    bounds: Dict[str, float] = {}  # {"min_x", "max_x", "min_z", "max_z"}
