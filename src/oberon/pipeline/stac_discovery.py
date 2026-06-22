"""STAC catalog discovery and scene selection.

Discovers Sentinel-2 L2A observations from a STAC catalog intersecting
the AOI and date windows. Scene selection uses scene-level metadata
for preliminary ranking; Phase 2 adds AOI-local quality assessment.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pystac_client import Client
from shapely.geometry import shape

from oberon.core import CandidateScene, ChangeRequest, SelectedScene

STAC_URL = "https://earth-search.aws.element84.com/v1"

# Sentinel-2 L2A band names to COG asset keys.
_BAND_NAMES = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]

# Earth Search STAC uses descriptive asset keys; map them to internal band names.
# See https://earth-search.aws.element84.com/ for the canonical asset key list.
_STAC_TO_INTERNAL: dict[str, str] = {
    "coastal": "B01",
    "blue": "B02",
    "green": "B03",
    "red": "B04",
    "rededge1": "B05",
    "rededge2": "B06",
    "rededge3": "B07",
    "nir": "B08",
    "nir08": "B8A",
    "swir16": "B11",
    "swir22": "B12",
}


def search_catalog(request: ChangeRequest, limit: int = 50) -> list[CandidateScene]:
    """Search the STAC catalog for Sentinel-2 L2A items intersecting the AOI.

    Queries the Earth Search STAC API for both the before and after date
    windows, combines results, and returns CandidateScene objects ordered
    by datetime descending.

    Raises ConnectionError if the STAC API is unreachable.
    """
    try:
        client = Client.open(STAC_URL)
    except Exception as exc:
        raise ConnectionError(f"Failed to connect to STAC catalog at {STAC_URL}: {exc}") from exc

    candidates: list[CandidateScene] = []

    for window in (request.before, request.after):
        date_str = f"{window[0].isoformat()}/{window[1].isoformat()}"
        search = client.search(
            intersects=request.geometry,
            datetime=date_str,
            collections=["sentinel-2-l2a"],
            max_items=limit,
        )

        for item in search.items():
            scene = _parse_stac_item(item)
            if scene is not None:
                candidates.append(scene)

    # Sort by datetime descending (newest first)
    candidates.sort(key=lambda c: c.datetime, reverse=True)
    return candidates


def rank_by_scene_quality(
    candidates: list[CandidateScene],
    before_window: tuple[date, date] | None = None,
    after_window: tuple[date, date] | None = None,
    max_cloud_pct: float = 15.0,
    max_selected: int = 3,
    aoi_geometry: dict[str, Any] | None = None,
) -> list[SelectedScene]:
    """Rank candidate scenes by scene-level cloud cover, grouped by period.

    Filters candidates above the cloud threshold, sorts by cloud cover
    (ascending), and returns the top N per period as SelectedScene items.

    When ``before_window`` and ``after_window`` are provided, the function
    splits candidates into periods automatically. Otherwise all candidates
    are ranked together with period="unknown".

    When ``aoi_geometry`` is provided, drops STAC items whose footprint does
    not actually intersect the AOI polygon. This prevents bbox/tile leakage
    from selecting a clean scene that cannot produce overlapping pixels.

    ponytail: cloud % ranking after exact footprint filter. Add SCL reads here
    only if catalog-level ranking still picks obstructed scenes in practice.
    """
    eligible = list(candidates)
    if aoi_geometry is not None:
        aoi_shape = shape(aoi_geometry)
        eligible = [c for c in eligible if _scene_intersects_aoi(c, aoi_shape)]

    eligible.sort(key=lambda c: c.scene_cloud_pct)
    filtered = [c for c in eligible if c.scene_cloud_pct <= max_cloud_pct]
    filtered.sort(key=lambda c: c.scene_cloud_pct)

    # Group by period if windows are provided
    if before_window and after_window:
        before_start, before_end = before_window
        after_start, after_end = after_window

        def _assign_period(dt: datetime) -> str:
            dt_naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
            if before_start <= dt_naive.date() <= before_end:
                return "before"
            if after_start <= dt_naive.date() <= after_end:
                return "after"
            return "unknown"

        period_pool = {
            period: [c for c in eligible if _assign_period(c.datetime) == period]
            for period in ("before", "after")
        }
        candidates_by_period = {
            period: [c for c in filtered if _assign_period(c.datetime) == period] or period_pool[period]
            for period in ("before", "after")
        }

        common_tiles = (
            {_mgrs_tile(c) for c in period_pool["before"]}
            & {_mgrs_tile(c) for c in period_pool["after"]}
        )
        common_tiles.discard(None)

        if common_tiles:
            tile = min(
                common_tiles,
                key=lambda t: (
                    min(c.scene_cloud_pct for c in period_pool["before"] if _mgrs_tile(c) == t)
                    + min(c.scene_cloud_pct for c in period_pool["after"] if _mgrs_tile(c) == t)
                ),
            )
            candidates_by_period = {
                period: (
                    [c for c in period_candidates if _mgrs_tile(c) == tile and c.scene_cloud_pct <= max_cloud_pct]
                    or [c for c in period_candidates if _mgrs_tile(c) == tile]
                )
                for period, period_candidates in period_pool.items()
            }

        selected: list[SelectedScene] = []
        for period in ("before", "after"):
            period_candidates = candidates_by_period[period]
            for c in period_candidates[:max_selected]:
                selected.append(
                    SelectedScene(
                        candidate=c,
                        local_valid_fraction=(100.0 - c.scene_cloud_pct) / 100.0,
                        period=period,
                    )
                )
        return selected

    # Fallback: no window info, all candidates together
    return [
        SelectedScene(
            candidate=c,
            local_valid_fraction=(100.0 - c.scene_cloud_pct) / 100.0,
            period="unknown",
        )
        for c in filtered[:max_selected]
    ]


def _scene_intersects_aoi(scene: CandidateScene, aoi_shape: Any) -> bool:
    """Return True when a candidate's STAC footprint intersects the AOI."""
    try:
        return bool(shape(scene.geometry).intersects(aoi_shape))
    except Exception:
        return False


def _mgrs_tile(scene: CandidateScene) -> str | None:
    """Extract the Sentinel-2 MGRS tile from Earth Search item IDs."""
    parts = scene.stac_item_id.split("_")
    return parts[1] if len(parts) >= 2 and len(parts[1]) == 5 else None


def _parse_stac_item(item: Any) -> CandidateScene | None:
    """Parse a pystac.Item into a CandidateScene.

    Returns None if required fields are missing.
    """
    item_dt: datetime | None = item.datetime
    if item_dt is None:
        return None

    # Ensure timezone-aware
    if item_dt.tzinfo is None:
        item_dt = item_dt.replace(tzinfo=UTC)

    bbox = item.bbox
    if bbox is None:
        return None

    geometry = item.geometry
    if geometry is None:
        return None

    # Extract per-band COG URLs using the descriptive-key mapping.
    assets_map: dict[str, str] = {}
    scl_url: str | None = None
    for stac_key, internal_name in _STAC_TO_INTERNAL.items():
        asset = item.assets.get(stac_key)
        if asset is not None:
            assets_map[internal_name] = str(asset.href)

    scl_asset = item.assets.get("scl")
    if scl_asset is not None:
        scl_url = str(scl_asset.href)

    cloud_pct = float(item.properties.get("eo:cloud_cover", 0.0))

    return CandidateScene(
        stac_item_id=item.id,
        datetime=item_dt,
        geometry=geometry,
        bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
        assets=assets_map,
        scl_url=scl_url,
        scene_cloud_pct=cloud_pct,
    )
