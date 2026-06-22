"""Pipeline orchestration — STAC discovery and scene selection."""

from __future__ import annotations

from oberon.core import CandidateScene, ChangeRequest, SelectedScene


STAC_URL = "https://earth-search.aws.element84.com/v1"


async def search_catalog(request: ChangeRequest, limit: int = 50) -> list[CandidateScene]:
    """Search STAC catalog for Sentinel-2 L2A items intersecting the AOI.

    Requires network access to the Earth Search STAC API.
    Returns candidate scenes ordered by datetime descending.
    """
    raise NotImplementedError("requires real STAC implementation")


def rank_by_local_quality(
    candidates: list[CandidateScene],
    request: ChangeRequest,
    target_period: str,
    max_selected: int = 3,
) -> list[SelectedScene]:
    """Rank candidates by local valid-pixel fraction over the AOI.

    Computes the fraction of non-cloud/shadow/snow pixels within the AOI
    for each candidate using its SCL band. Returns the top N selections.
    """
    raise NotImplementedError("requires real quality assessment implementation")
