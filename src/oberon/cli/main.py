"""CLI entry point for Oberon."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import click

from oberon.core import ChangeRequest


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

    bundle = run_analysis(request, output_dir)

    # Report result.
    provenance = bundle.provenance
    if provenance.get("abstention"):
        click.echo(f"Abstained: {provenance['abstention']['reason']}")
        sys.exit(0)

    num_findings = len(provenance.get("findings", []))
    click.echo(f"Analysis complete: {num_findings} finding(s)")
    click.echo(f"  Before image:  {bundle.before_image}")
    click.echo(f"  After image:   {bundle.after_image}")
    click.echo(f"  Overlay:       {bundle.overlay_image}")
    click.echo(f"  Findings:      {bundle.findings_geojson}")
    click.echo(f"  Provenance:    {bundle.provenance_manifest}")


def main() -> None:
    """Entry point for `oberon` CLI (console_scripts)."""
    cli()
