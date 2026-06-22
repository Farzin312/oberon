"""Tests for geometry validation and transformation utilities.

Module: oberon/core/geometry.py

Each test class covers one public function. Every test method has a
docstring explaining what behaviour it validates. Edge cases and
failure modes are tested explicitly.
"""

from __future__ import annotations

from oberon.core.geometry import polygon_area_approx_ha, polygon_to_bbox, validate_geojson_polygon

# ---------------------------------------------------------------------------
# validate_geojson_polygon
# ---------------------------------------------------------------------------

class TestValidateGeojsonPolygon:
    """validate_geojson_polygon(): verify a GeoJSON dict is a valid Polygon or MultiPolygon."""

    def test_valid_polygon_returns_true(self, sample_polygon_geometry: dict) -> None:
        """A well-formed Polygon geometry with closed ring should return True."""
        assert validate_geojson_polygon(sample_polygon_geometry) is True

    def test_valid_multipolygon_returns_true(self) -> None:
        """A well-formed MultiPolygon geometry with one part should return True."""
        geom = {
            "type": "MultiPolygon",
            "coordinates": [[
                [[-84.0, 10.0], [-83.9, 10.0], [-83.9, 10.1], [-84.0, 10.1], [-84.0, 10.0]],
            ]],
        }
        assert validate_geojson_polygon(geom) is True

    def test_point_geometry_returns_false(self) -> None:
        """Point geometries are not polygons and should return False."""
        assert validate_geojson_polygon({"type": "Point", "coordinates": [0, 0]}) is False

    def test_linestring_geometry_returns_false(self) -> None:
        """LineString geometries are not polygons and should return False."""
        assert validate_geojson_polygon({"type": "LineString", "coordinates": [[0, 0], [1, 1]]}) is False

    def test_missing_type_returns_false(self) -> None:
        """A dict without a 'type' key is not valid GeoJSON and should return False."""
        assert validate_geojson_polygon({"coordinates": []}) is False

    def test_self_intersecting_polygon_returns_false(self) -> None:
        """A self-intersecting (bowtie) polygon is invalid geometry and should return False."""
        bowtie = {
            "type": "Polygon",
            "coordinates": [[
                [0, 0], [1, 1], [0, 1], [1, 0], [0, 0],
            ]],
        }
        assert validate_geojson_polygon(bowtie) is False

    def test_empty_coordinates_returns_false(self) -> None:
        """Polygon with an empty coordinate list should return False (cannot form a valid shape)."""
        geom = {"type": "Polygon", "coordinates": []}
        assert validate_geojson_polygon(geom) is False

    def test_missing_coordinates_returns_false(self) -> None:
        """Polygon with no coordinates key should return False (malformed)."""
        geom = {"type": "Polygon"}
        assert validate_geojson_polygon(geom) is False

    def test_three_point_polygon_returns_false(self) -> None:
        """A polygon ring must have at least 4 coordinates (closed). Fewer is degenerate."""
        geom = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [0, 0]]],
        }
        assert validate_geojson_polygon(geom) is False


# ---------------------------------------------------------------------------
# polygon_to_bbox
# ---------------------------------------------------------------------------

class TestPolygonToBbox:
    """polygon_to_bbox(): compute (west, south, east, north) bounding box from GeoJSON."""

    def test_returns_minimum_bounding_box(self, sample_polygon_geometry: dict) -> None:
        """Bbox should return (min_lon, min_lat, max_lon, max_lat) matching the polygon extent."""
        bbox = polygon_to_bbox(sample_polygon_geometry)
        assert bbox == (-55.2, -7.5, -55.15, -7.45)

    def test_multipolygon_returns_unified_envelope(self) -> None:
        """For MultiPolygon, the bbox should cover the envelope of all parts combined."""
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[-84.0, 10.0], [-83.95, 10.0], [-83.95, 10.05], [-84.0, 10.05], [-84.0, 10.0]]],
                [[[-83.9, 10.05], [-83.85, 10.05], [-83.85, 10.1], [-83.9, 10.1], [-83.9, 10.05]]],
            ],
        }
        bbox = polygon_to_bbox(geom)
        # Leftmost: -84.0, lowest: 10.0, rightmost: -83.85, highest: 10.1
        assert bbox == (-84.0, 10.0, -83.85, 10.1)


# ---------------------------------------------------------------------------
# polygon_area_approx_ha
# ---------------------------------------------------------------------------

class TestPolygonAreaApproxHa:
    """polygon_area_approx_ha(): approximate planar area of a polygon in hectares."""

    def test_returns_approx_area_for_small_polygon(self) -> None:
        """A ~0.01 deg² polygon at the equator should return ~12,321 ha (planar approximation)."""
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [-84.0, 10.0],
                [-83.9, 10.0],
                [-83.9, 10.1],
                [-84.0, 10.1],
                [-84.0, 10.0],
            ]],
        }
        # 0.1 deg x 0.1 deg = 0.01 deg² x (111 km/deg)² x 100 ha/km² = ~12,321 ha
        area = polygon_area_approx_ha(geom)
        assert 12000 < area < 12500

    def test_returns_approx_area_for_large_polygon(self) -> None:
        """A ~1 deg² polygon at the equator should return ~1,232,100 ha (planar approximation)."""
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [-85.0, 9.0],
                [-84.0, 9.0],
                [-84.0, 10.0],
                [-85.0, 10.0],
                [-85.0, 9.0],
            ]],
        }
        # 1 deg x 1 deg = 1 deg² x (111 km/deg)² x 100 ha/km² = ~1,232,100 ha
        area = polygon_area_approx_ha(geom)
        assert 1_200_000 < area < 1_250_000

    def test_degenerate_zero_width_polygon_returns_zero(self) -> None:
        """A polygon with no width (duplicate coordinates) should return 0.0 ha."""
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [-84.0, 10.0],
                [-84.0, 10.0],
                [-84.0, 10.0],
            ]],
        }
        area = polygon_area_approx_ha(geom)
        assert area == 0.0

    def test_negative_longitude_is_handled(self) -> None:
        """Western hemisphere (negative longitude) should compute the same as positive."""
        geom = {
            "type": "Polygon",
            "coordinates": [[
                [10.0, -5.0],
                [10.1, -5.0],
                [10.1, -4.9],
                [10.0, -4.9],
                [10.0, -5.0],
            ]],
        }
        area = polygon_area_approx_ha(geom)
        assert 12000 < area < 12500  # same 0.01 deg² approximation
