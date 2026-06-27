"""Findings come out of change detection in pixel space — this reprojects them
to lon/lat so the dashboard GeoJSON renders at the AOI, not near (0, 0)."""

from __future__ import annotations

from oberon.core import Finding
from oberon.pipeline.preparation import reproject_findings_to_wgs84


def _finding(coords: list[list[float]]) -> Finding:
    return Finding(
        geometry={"type": "Polygon", "coordinates": [coords]},
        score=0.9,
        area_ha=1.0,
        ndvi_delta_mean=-0.3,
        nbr_delta_mean=0.0,
        valid_pixels_in_finding=42,
    )


def test_wgs84_affine_maps_pixels_exactly() -> None:
    # crs already lon/lat -> no warp, pure affine. Pixel (col,row) -> (lon,lat).
    # lon = 5 + 0.001*col, lat = 50 - 0.001*row.
    transform = (0.001, 0.0, 5.0, 0.0, -0.001, 50.0)
    f = _finding([[0, 0], [10, 0], [10, 20], [0, 20], [0, 0]])

    reproject_findings_to_wgs84([f], transform, "EPSG:4326")

    ring = f.geometry["coordinates"][0]
    assert ring[0] == [5.0, 50.0]
    assert ring[1] == [5.01, 50.0]
    assert ring[2] == [5.01, 49.98]


def test_utm_findings_become_valid_lonlat() -> None:
    # UTM 33N grid near the central meridian: pixel coords must land in
    # plausible lon/lat, never the raw pixel indices.
    transform = (10.0, 0.0, 500000.0, 0.0, -10.0, 5000000.0)
    f = _finding([[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]])

    reproject_findings_to_wgs84([f], transform, "EPSG:32633")

    for lon, lat in f.geometry["coordinates"][0]:
        assert 10.0 < lon < 20.0, lon
        assert 40.0 < lat < 50.0, lat


def test_empty_transform_is_noop() -> None:
    # Abstention path carries no real grid — leave geometry untouched.
    f = _finding([[1, 2], [3, 4], [5, 6], [1, 2]])
    reproject_findings_to_wgs84([f], (), "")
    assert f.geometry["coordinates"][0] == [[1, 2], [3, 4], [5, 6], [1, 2]]


if __name__ == "__main__":
    test_wgs84_affine_maps_pixels_exactly()
    test_utm_findings_become_valid_lonlat()
    test_empty_transform_is_noop()
    print("ok")
