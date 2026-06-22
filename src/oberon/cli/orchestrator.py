"""Pipeline orchestration — runs stages in order, handles abstention."""

from __future__ import annotations

from pathlib import Path

from oberon.core import BaselineResult, ChangeRequest, EvidenceBundle, Finding


def run_analysis(request: ChangeRequest, output_dir: Path) -> EvidenceBundle:
    """Run the full analysis pipeline for a change request.

    Calls each pipeline stage in order. If any stage returns abstention,
    the pipeline stops early and returns an abstention result containing
    the reason and any partial provenance.
    """
    raise NotImplementedError("requires full pipeline wiring")
