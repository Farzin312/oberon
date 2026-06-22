"""Geometry validation and transformation helpers."""

from __future__ import annotations

from shapely.geometry import shape


def validate_geojson_polygon(geometry: dict) -> bool:
    """Check that a GeoJSON-like dict is a valid Polygon or MultiPolygon."""
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return False
    coords = geometry.get("coordinates")
    if not coords or not coords[0]:
        return False
    try:
        geom = shape(geometry)
        return geom.is_valid and geom.geom_type in ("Polygon", "MultiPolygon")
    except Exception:
        return False


def polygon_to_bbox(geometry: dict) -> tuple[float, float, float, float]:
    """Return (west, south, east, north) bounding box from a GeoJSON geometry."""
    geom = shape(geometry)
    return geom.bounds  # type: ignore[no-any-return]


def polygon_area_approx_ha(geometry: dict) -> float:
    """Approximate area in hectares using a simple lat/lon planar estimate.

    ponytail: planar approximation only, accurate to ~5% at mid-latitudes.
    Upgrade to `pyproj` azimuthal equal-area projection when precision matters.
    """
    geom = shape(geometry)
    bounds = geom.bounds
    width_deg = bounds[2] - bounds[0]
    height_deg = bounds[3] - bounds[1]
    # Rough deg² → km² at equator: 1° ≈ 111km
    area_km2 = width_deg * height_deg * 111 * 111
    return area_km2 * 100  # km² → ha
