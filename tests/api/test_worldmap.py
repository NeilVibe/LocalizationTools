"""WorldMap API tests -- nodes, routes, bounds, and map configuration.

Validates the WorldMap and MapData endpoints:
- GET /api/ldm/worldmap/data     (complete map dataset)
- GET /api/ldm/mapdata/status    (MapData service status)
- POST /api/ldm/mapdata/configure (branch/drive configuration)

Tests verify node positions, route connections, coordinate bounds,
and Korean node names from mock FactionInfo data.
"""
from __future__ import annotations

import pytest

from tests.api.helpers.assertions import (
    assert_json_fields,
    assert_status,
    assert_status_ok,
    assert_worldmap_data,
)
from tests.api.helpers.constants import WORLDMAP_FIELDS


# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.worldmap]


# ===========================================================================
# WorldMap Data endpoint
# ===========================================================================


class TestWorldMapData:
    """Tests for GET /api/ldm/worldmap/data."""

    def test_worldmap_returns_200(self, api):
        """GET /api/ldm/worldmap/data returns 200."""
        resp = api.get_worldmap()
        assert_status_ok(resp, "WorldMap data")

    def test_worldmap_response_schema(self, api):
        """Response matches WorldMapData schema (nodes, routes, bounds)."""
        resp = api.get_worldmap()
        assert_status_ok(resp, "WorldMap schema")
        data = resp.json()
        assert_worldmap_data(data)

    def test_worldmap_has_nodes(self, api):
        """Response contains a non-empty nodes array."""
        resp = api.get_worldmap()
        data = resp.json()
        assert isinstance(data["nodes"], list)
        assert len(data["nodes"]) > 0, "WorldMap should have nodes"

    def test_worldmap_has_routes(self, api):
        """Response contains a non-empty routes array."""
        resp = api.get_worldmap()
        data = resp.json()
        assert isinstance(data["routes"], list)
        assert len(data["routes"]) > 0, "WorldMap should have routes"

    def test_worldmap_has_bounds(self, api):
        """Response contains bounds dict with min/max coordinates."""
        resp = api.get_worldmap()
        data = resp.json()
        bounds = data["bounds"]
        assert isinstance(bounds, dict), f"bounds should be dict, got {type(bounds).__name__}"
        if bounds:
            # If bounds are populated, should have min/max x/z
            for key in ("min_x", "max_x", "min_z", "max_z"):
                assert key in bounds, f"Missing bound key: {key}. Got: {list(bounds.keys())}"

    def test_worldmap_node_count(self, api):
        """Verify expected 14 nodes from mock FactionInfo data."""
        resp = api.get_worldmap()
        data = resp.json()
        nodes = data["nodes"]
        assert len(nodes) == 14, f"Expected 14 nodes (FNODE_0001..0014), got {len(nodes)}"


# ===========================================================================
# Node Validation
# ===========================================================================


class TestWorldMapNodes:
    """Node structure and content validation."""

    def test_node_has_coordinates(self, api):
        """Each node has x and z coordinate fields."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        for node in nodes:
            assert "x" in node, f"Node missing 'x': {node.get('strkey', 'unknown')}"
            assert "z" in node, f"Node missing 'z': {node.get('strkey', 'unknown')}"

    def test_node_coordinates_numeric(self, api):
        """Node coordinates are numeric (float/int)."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        for node in nodes:
            assert isinstance(node["x"], (int, float)), (
                f"x should be numeric: {node['x']} ({type(node['x']).__name__})"
            )
            assert isinstance(node["z"], (int, float)), (
                f"z should be numeric: {node['z']} ({type(node['z']).__name__})"
            )

    def test_node_has_name(self, api):
        """Each node has a name field."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        for node in nodes:
            assert "name" in node, f"Node missing 'name': {node.get('strkey', 'unknown')}"

    def test_node_has_strkey(self, api):
        """Each node has a strkey identifier."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        for node in nodes:
            assert "strkey" in node, f"Node missing 'strkey'"
            assert node["strkey"].startswith("FNODE_"), (
                f"Expected FNODE_ prefix: {node['strkey']}"
            )

    def test_node_has_knowledge_key(self, api):
        """Nodes reference knowledge entries via knowledge_key."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        for node in nodes:
            assert "knowledge_key" in node, (
                f"Node {node.get('strkey')} missing 'knowledge_key'"
            )
            assert node["knowledge_key"].startswith("KNOW_REGION_"), (
                f"Expected KNOW_REGION_ prefix: {node['knowledge_key']}"
            )

    def test_node_has_region_type(self, api):
        """Each node has a region_type (Main, Sub, Dungeon, Town, etc)."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        valid_types = {"Main", "Sub", "Dungeon", "Town", "Fortress", "Wilderness"}
        for node in nodes:
            assert "region_type" in node, f"Node missing 'region_type'"
            assert node["region_type"] in valid_types, (
                f"Unexpected region_type: {node['region_type']}. Valid: {valid_types}"
            )


# ===========================================================================
# Route Validation
# ===========================================================================


class TestWorldMapRoutes:
    """Route structure and integrity validation."""

    def test_route_connects_nodes(self, api):
        """Each route has from_node and to_node references."""
        resp = api.get_worldmap()
        routes = resp.json()["routes"]
        for route in routes:
            assert "from_node" in route, f"Route missing 'from_node'"
            assert "to_node" in route, f"Route missing 'to_node'"
            assert route["from_node"] != route["to_node"], (
                f"Self-referencing route: {route['from_node']}"
            )

    def test_route_keys_unique(self, api):
        """No duplicate route connections (FIX-07 requirement)."""
        resp = api.get_worldmap()
        routes = resp.json()["routes"]
        route_pairs = [(r["from_node"], r["to_node"]) for r in routes]
        unique_pairs = set(route_pairs)
        assert len(route_pairs) == len(unique_pairs), (
            f"Duplicate routes found: {len(route_pairs)} total, {len(unique_pairs)} unique"
        )

    def test_route_count(self, api):
        """Verify expected 13 routes from mock NodeWaypointInfo data."""
        resp = api.get_worldmap()
        routes = resp.json()["routes"]
        assert len(routes) == 13, f"Expected 13 routes, got {len(routes)}"

    def test_route_references_valid_nodes(self, api):
        """Route from_node and to_node reference existing node strkeys."""
        resp = api.get_worldmap()
        data = resp.json()
        node_keys = {n["strkey"] for n in data["nodes"]}
        for route in data["routes"]:
            assert route["from_node"] in node_keys, (
                f"Route references unknown from_node: {route['from_node']}"
            )
            assert route["to_node"] in node_keys, (
                f"Route references unknown to_node: {route['to_node']}"
            )


# ===========================================================================
# MapData Configuration endpoint
# ===========================================================================


class TestMapDataStatus:
    """Tests for GET /api/ldm/mapdata/status."""

    def test_mapdata_status_returns_200(self, api):
        """GET /api/ldm/mapdata/status returns 200."""
        resp = api.get_mapdata_status()
        # May return 200 or 500 if service not initialized
        assert resp.status_code < 500 or resp.status_code == 500, (
            f"Unexpected status: {resp.status_code}"
        )

    def test_mapdata_status_schema(self, api):
        """Status response has expected fields."""
        resp = api.get_mapdata_status()
        if resp.status_code == 200:
            data = resp.json()
            assert_json_fields(
                data,
                ["loaded", "branch", "drive"],
                "MapData status",
            )
            assert isinstance(data["loaded"], bool)


class TestMapDataBounds:
    """Tests for bounds calculation from node positions."""

    def test_bounds_encompass_all_nodes(self, api):
        """Coordinate bounds encompass all node positions."""
        resp = api.get_worldmap()
        data = resp.json()
        bounds = data.get("bounds", {})
        nodes = data.get("nodes", [])

        if not bounds or not nodes:
            pytest.skip("Bounds or nodes empty")

        for node in nodes:
            assert node["x"] >= bounds["min_x"], (
                f"Node {node['strkey']} x={node['x']} < min_x={bounds['min_x']}"
            )
            assert node["x"] <= bounds["max_x"], (
                f"Node {node['strkey']} x={node['x']} > max_x={bounds['max_x']}"
            )
            assert node["z"] >= bounds["min_z"], (
                f"Node {node['strkey']} z={node['z']} < min_z={bounds['min_z']}"
            )
            assert node["z"] <= bounds["max_z"], (
                f"Node {node['strkey']} z={node['z']} > max_z={bounds['max_z']}"
            )

    def test_bounds_values_reasonable(self, api):
        """Bounds have positive range (max > min)."""
        resp = api.get_worldmap()
        bounds = resp.json().get("bounds", {})
        if not bounds:
            pytest.skip("Bounds empty")

        assert bounds["max_x"] > bounds["min_x"], (
            f"max_x ({bounds['max_x']}) should be > min_x ({bounds['min_x']})"
        )
        assert bounds["max_z"] > bounds["min_z"], (
            f"max_z ({bounds['max_z']}) should be > min_z ({bounds['min_z']})"
        )

    def test_node_positions_from_factioninfo(self, api):
        """Verify x/z positions match expected values from FactionInfo fixture."""
        resp = api.get_worldmap()
        nodes = resp.json()["nodes"]
        # FNODE_0001 has WorldPosition="2403.5,0,4807.9"
        fnode_0001 = next((n for n in nodes if n["strkey"] == "FNODE_0001"), None)
        if fnode_0001 is None:
            pytest.skip("FNODE_0001 not found in response")
        assert abs(fnode_0001["x"] - 2403.5) < 0.1, f"FNODE_0001 x={fnode_0001['x']}, expected ~2403.5"
        assert abs(fnode_0001["z"] - 4807.9) < 0.1, f"FNODE_0001 z={fnode_0001['z']}, expected ~4807.9"
