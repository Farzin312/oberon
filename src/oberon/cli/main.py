"""CLI entry point for Oberon."""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
def cli() -> None:
    """Oberon — Earth observation change monitoring engine."""


@cli.command()
@click.option("--aoi", required=True, type=click.Path(exists=True, dir_okay=False),
              help="Path to GeoJSON file with AOI polygon")
@click.option("--before", required=True, help="Before date window start (YYYY-MM-DD)")
@click.option("--after", required=True, help="After date window end (YYYY-MM-DD)")
@click.option("--task", default="vegetation_disturbance",
              help="Task type (default: vegetation_disturbance)")
@click.option("--output", "-o", default="./oberon-output",
              type=click.Path(file_okay=False),
              help="Output directory for artifacts")
def analyze(aoi: str, before: str, after: str, task: str, output: str) -> None:
    """Analyze a land area for vegetation change between two date windows.

    This is the primary entry point for the Oberon pipeline. It runs the
    full walking-vertical-slice: STAC discovery → scene quality → COG read
    → preparation → baseline analytics → evidence bundles.
    """
    click.echo(f"Oberon analyze: {aoi}")
    click.echo(f"  Before: {before}")
    click.echo(f"  After:  {after}")
    click.echo(f"  Task:   {task}")
    click.echo(f"  Output: {output}")
    click.echo("(Implementation in progress — see docs/mini-sdd/001-data-plane-pipeline/)")
