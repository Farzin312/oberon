"""CLI entry point for Oberon."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import click

from oberon import __version__
from oberon.core import ChangeRequest
from oberon.telemetry.logging import configure_logging, get_logger


def _parse_date(ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Validate date format is YYYY-MM-DD (don't parse yet — need two for window)."""
    if not value:
        return value
    try:
        date.fromisoformat(value)
    except (ValueError, TypeError):
        raise click.BadParameter(f"Invalid date format '{value}'. Use YYYY-MM-DD.") from None
    return value


@click.group()
def cli() -> None:
    """Oberon — Earth observation change monitoring engine."""


@cli.command()
@click.option("--aoi", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Path to GeoJSON file with AOI polygon")
@click.option("--before", required=True, callback=_parse_date,
              help="Before date window end (YYYY-MM-DD)")
@click.option("--after", required=True, callback=_parse_date,
              help="After date window end (YYYY-MM-DD)")
@click.option("--before-start", "before_start", default=None, callback=_parse_date,
              help="Before date window start (YYYY-MM-DD). Defaults to 30 days before --before.")
@click.option("--after-start", "after_start", default=None, callback=_parse_date,
              help="After date window start (YYYY-MM-DD). Defaults to --after.")
@click.option("--task", default="vegetation_disturbance",
              help="Task type (default: vegetation_disturbance)")
@click.option("--output", "-o", default="./oberon-output",
              type=click.Path(file_okay=False),
              help="Output directory for artifacts")
@click.option("--max-cloud", default=15.0, type=click.FloatRange(0, 100),
              help="Maximum scene cloud cover %% (default: 15)")
@click.option("--min-valid", default=0.30, type=click.FloatRange(0, 1),
              help="Minimum valid pixel fraction (default: 0.30)")
@click.option("--composite", "force_composite", is_flag=True, default=False,
              help="Force cloud-masked composite mode (merge up to 3 scenes per period)")
def analyze(
    aoi: str,
    before: str,
    after: str,
    before_start: str | None,
    after_start: str | None,
    task: str,
    output: str,
    max_cloud: float,
    min_valid: float,
    force_composite: bool,
) -> None:
    """Analyze a land area for vegetation change between two date windows.

    Finds the best before/after Sentinel-2 image pair for the given AOI,
    computes spectral indices and change detection, and writes evidence
    artifacts (PNG images, GeoJSON findings, provenance manifest) to
    the output directory.
    """
    # Parse dates into windows.
    before_dt = date.fromisoformat(before)
    after_dt = date.fromisoformat(after)

    # Default windows: 30-day lookback for before, 30-day for after.
    before_start_dt = date.fromisoformat(before_start) if before_start else before_dt.replace(
        month=before_dt.month - 1 if before_dt.month > 1 else 12,
        year=before_dt.year - 1 if before_dt.month <= 1 else before_dt.year,
    )
    after_start_dt = date.fromisoformat(after_start) if after_start else after_dt

    # Load AOI GeoJSON
    try:
        with open(aoi) as f:
            geojson = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: Invalid AOI file '{aoi}': {exc}", err=True)
        sys.exit(1)

    geometry = geojson.get("geometry") or geojson
    # Handle FeatureCollection: extract the first feature's geometry.
    if geojson.get("type") == "FeatureCollection" and geojson.get("features"):
        feat = geojson["features"][0]
        geometry = feat.get("geometry") or feat
    if not isinstance(geometry, dict) or "type" not in geometry:
        click.echo("Error: AOI file must contain a GeoJSON Feature or Geometry with a 'type' field",
                   err=True)
        sys.exit(1)

    # Build the change request.
    request = ChangeRequest(
        geometry=geometry,
        before=(before_start_dt, before_dt),
        after=(after_start_dt, after_dt),
        task=task,
        max_cloud_fraction=max_cloud / 100.0,
        min_valid_pixels=min_valid,
    )

    output_dir = Path(output)

    logger = get_logger("oberon.analyze")
    logger.info("analyze.start", extra={
        "task": task, "aoi": str(aoi),
        "before": str(request.before), "after": str(request.after),
        "max_cloud": max_cloud, "min_valid": min_valid,
        "composite": force_composite,
    })

    click.echo(f"Oberon analyze — {task}")
    click.echo(f"  AOI:       {aoi}")
    click.echo(f"  Before:    {request.before[0]} to {request.before[1]}")
    click.echo(f"  After:     {request.after[0]} to {request.after[1]}")
    click.echo(f"  Max cloud: {max_cloud:.0f}%")
    click.echo(f"  Min valid: {min_valid:.0%}")
    click.echo(f"  Output:    {output_dir}")
    click.echo("")

    # Run the pipeline.
    from oberon.cli.orchestrator import run_analysis

    bundle = run_analysis(request, output_dir, force_composite=force_composite)

    # Report result.
    provenance = bundle.provenance
    if provenance.get("abstention"):
        reason = provenance["abstention"]["reason"]
        logger.info("analyze.result", extra={"outcome": "abstained", "reason": reason})
        click.echo(f"Abstained: {reason}")
        sys.exit(0)

    num_findings = len(provenance.get("findings", []))
    logger.info("analyze.result", extra={"outcome": "complete", "findings": num_findings})
    click.echo(f"Analysis complete: {num_findings} finding(s)")
    click.echo(f"  Before image:  {bundle.before_image}")
    click.echo(f"  After image:   {bundle.after_image}")
    click.echo(f"  Overlay:       {bundle.overlay_image}")
    click.echo(f"  Findings:      {bundle.findings_geojson}")
    click.echo(f"  Provenance:    {bundle.provenance_manifest}")


@cli.command()
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output as JSON (for programmatic use)")
def health(as_json: bool) -> None:
    """Check system health: version, torch availability, cache status.

    Verifies the container is correctly configured before running analysis.
    """
    import os

    status: dict[str, object] = {
        "status": "healthy",
        "version": __version__,
    }

    # Check torch availability (optional).
    try:
        import torch  # noqa: F401

        status["torch_available"] = True
    except ImportError:
        status["torch_available"] = False

    # Check STAC reachability (non-blocking, 5s timeout).
    try:
        import urllib.request

        urllib.request.urlopen(
            "https://earth-search.aws.element84.com/v1",
            timeout=5,
        )
        status["stac_reachable"] = True
    except Exception:
        status["stac_reachable"] = False

    # Cache directory size.
    cache_dir = os.environ.get("OBERON_CACHE_DIR", os.path.expanduser("~/.cache/oberon"))
    cache_size = 0
    if os.path.isdir(cache_dir):
        for dirpath, _dirs, files in os.walk(cache_dir):
            for f in files:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    cache_size += os.path.getsize(fp)
    status["cache_dir"] = cache_dir
    status["cache_size_mb"] = round(cache_size / (1024 * 1024), 1)

    if as_json:
        click.echo(json.dumps(status, indent=2))
    else:
        click.echo(f"Oberon v{status['version']} — {status['status']}")
        click.echo(f"  Torch:     {'available' if status['torch_available'] else 'not installed'}")
        click.echo(f"  STAC API:  {'reachable' if status['stac_reachable'] else 'unreachable'}")
        click.echo(f"  Cache:     {status['cache_size_mb']} MB at {status['cache_dir']}")

    sys.exit(0)


def main() -> None:
    """Entry point for `oberon` CLI (console_scripts)."""
    configure_logging()
    cli()
