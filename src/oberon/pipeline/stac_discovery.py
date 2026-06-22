"""STAC catalog discovery and scene selection.

Discovers Sentinel-2 L2A observations from a STAC catalog intersecting
the AOI and date windows. Scene selection uses scene-level metadata
for preliminary ranking; Phase 2 adds AOI-local quality assessment.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pystac_client import Client

from oberon.core import CandidateScene, ChangeRequest, SelectedScene

STAC_URL = "https://earth-search.aws.element84.com/v1"

# Sentinel-2 L2A band names to COG asset keys.
_BAND_NAMES = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]


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
) -> list[SelectedScene]:
    """Rank candidate scenes by scene-level cloud cover, grouped by period.

    Filters candidates above the cloud threshold, sorts by cloud cover
    (ascending), and returns the top N per period as SelectedScene items.

    When ``before_window`` and ``after_window`` are provided, the function
    splits candidates into periods automatically. Otherwise all candidates
    are ranked together with period="unknown".

    ponytail: scene-level cloud % only. Phase 2 adds AOI-local valid-pixel
    fraction via SCL for more accurate ranking.
    """
    filtered = [c for c in candidates if c.scene_cloud_pct <= max_cloud_pct]
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

        selected: list[SelectedScene] = []
        for period in ("before", "after"):
            period_candidates = [c for c in filtered if _assign_period(c.datetime) == period]
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


def _parse_stac_item(item) -> CandidateScene | None:
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

    # Extract per-band COG URLs and find the SCL URL
    assets_map: dict[str, str] = {}
    scl_url: str | None = None
    for band_name in _BAND_NAMES:
        asset = item.assets.get(band_name)
        if asset is not None:
            assets_map[band_name] = str(asset.href)

    scl_asset = item.assets.get("SCL")
    if scl_asset is not None:
        scl_url = str(scl_asset.href)

    cloud_pct = float(item.properties.get("eo:cloud_cover", 0.0))

    return CandidateScene(
        stac_item_id=item.id,
        datetime=item_dt,
        geometry=geometry,
        bbox=tuple(bbox),  # type: ignore[arg-type]
        assets=assets_map,
        scl_url=scl_url,
        scene_cloud_pct=cloud_pct,
    )
