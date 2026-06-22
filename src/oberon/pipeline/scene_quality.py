"""Scene quality assessment — local valid-pixel fraction over AOI."""

from __future__ import annotations

from oberon.core import CandidateScene, SelectedScene


def compute_local_valid_fraction(
    candidate: CandidateScene,
    aoi_geometry: dict,
) -> float:
    """Compute fraction of valid (non-cloud/shadow/snow) pixels within the AOI.

    Reads the SCL band over the AOI window, classifies each pixel as
    valid or invalid per the SCL bitmask constants, and returns the
    fraction of valid pixels.

    ponytail: full-resolution SCL read; consider SCL thumbnail or cached
    quality layer for speed when monitoring many AOIs.
    """
    raise NotImplementedError("requires SCL band reading + AOI intersection")
