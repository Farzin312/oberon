"""CLI entry point for Oberon."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

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


# Max GeoJSON file size: 10 MB. Prevents memory exhaustion from huge polygons.
_MAX_GEOJSON_BYTES = 10 * 1024 * 1024


def _validate_file_size(path: str) -> None:
    """Reject input files larger than _MAX_GEOJSON_BYTES.

    Protects against accidental or malicious resource exhaustion from
    processing country-sized polygons with millions of vertices.
    """
    import os

    size = os.path.getsize(path)
    if size > _MAX_GEOJSON_BYTES:
        click.echo(
            f"Error: Input file '{path}' is {size / 1024 / 1024:.1f} MB. "
            f"Maximum is {_MAX_GEOJSON_BYTES / 1024 / 1024:.0f} MB. "
            "Simplify the geometry (reduce vertex count or area).",
            err=True,
        )
        sys.exit(1)


def _build_request(
    request_file: str | None,
    aoi: str | None,
    before: str | None,
    after: str | None,
    before_start: str | None,
    after_start: str | None,
    task: str,
    max_cloud: float,
    min_valid: float,
) -> ChangeRequest:
    """Build a ChangeRequest from either --request JSON or --aoi/--before/--after flags.

    Validates mutual exclusion: --request cannot be used with --aoi.
    At least one input mode must be provided.
    """
    if request_file:
        if aoi:
            raise click.UsageError(
                "--request cannot be used with --aoi/--before/--after. Choose one input mode."
            )
        return _request_from_file(request_file)

    if not aoi or not before or not after:
        raise click.UsageError(
            "Provide either --request <path> or --aoi <path> --before <date> --after <date>. "
            "Run 'oberon analyze --help' for examples."
        )
    return _request_from_flags(aoi, before, after, before_start, after_start, task, max_cloud, min_valid)


def _request_from_file(path: str) -> ChangeRequest:
    """Parse a ChangeRequestAPI JSON file into a ChangeRequest."""
    _validate_file_size(path)
    try:
        with open(path) as f:
            raw: dict[str, Any] = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: Invalid request file '{path}': {exc}", err=True)
        sys.exit(1)

    # Validate with the Pydantic model (catches bad geometry, dates, etc.).
    from pydantic import ValidationError

    from oberon.api.contracts import ChangeRequestAPI

    try:
        api_req = ChangeRequestAPI(**raw)
    except ValidationError as exc:
        click.echo(f"Error: Invalid request schema: {exc}", err=True)
        sys.exit(1)

    return ChangeRequest(
        geometry=api_req.geometry,
        before=(api_req.before.from_, api_req.before.to),
        after=(api_req.after.from_, api_req.after.to),
        task=api_req.task,
        max_cloud_fraction=api_req.max_cloud_fraction,
        min_valid_pixels=0.30,
    )


def _request_from_flags(
    aoi: str,
    before: str,
    after: str,
    before_start: str | None,
    after_start: str | None,
    task: str,
    max_cloud: float,
    min_valid: float,
) -> ChangeRequest:
    """Build a ChangeRequest from CLI flags (the original --aoi mode)."""
    before_dt = date.fromisoformat(before)
    after_dt = date.fromisoformat(after)

    before_start_dt = date.fromisoformat(before_start) if before_start else before_dt.replace(
        month=before_dt.month - 1 if before_dt.month > 1 else 12,
        year=before_dt.year - 1 if before_dt.month <= 1 else before_dt.year,
    )
    after_start_dt = date.fromisoformat(after_start) if after_start else after_dt.replace(
        month=after_dt.month - 1 if after_dt.month > 1 else 12,
        year=after_dt.year - 1 if after_dt.month <= 1 else after_dt.year,
    )

    _validate_file_size(aoi)
    try:
        with open(aoi) as f:
            geojson = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        click.echo(f"Error: Invalid AOI file '{aoi}': {exc}", err=True)
        sys.exit(1)

    geometry = geojson.get("geometry") or geojson
    if geojson.get("type") == "FeatureCollection" and geojson.get("features"):
        feat = geojson["features"][0]
        geometry = feat.get("geometry") or feat
    if not isinstance(geometry, dict) or "type" not in geometry:
        click.echo("Error: AOI file must contain a GeoJSON Feature or Geometry with a 'type' field",
                   err=True)
        sys.exit(1)

    return ChangeRequest(
        geometry=geometry,
        before=(before_start_dt, before_dt),
        after=(after_start_dt, after_dt),
        task=task,
        max_cloud_fraction=max_cloud / 100.0,
        min_valid_pixels=min_valid,
    )


@click.group()
@click.version_option(version=__version__, prog_name="oberon")
def cli() -> None:
    """Oberon — Earth observation change monitoring engine."""


@cli.command()
@click.option("--aoi", default=None, type=click.Path(exists=True, dir_okay=False),
              help="Path to GeoJSON file with AOI polygon")
@click.option("--before", default=None, callback=_parse_date,
              help="Before date window end (YYYY-MM-DD)")
@click.option("--after", default=None, callback=_parse_date,
              help="After date window end (YYYY-MM-DD)")
@click.option("--before-start", "before_start", default=None, callback=_parse_date,
              help="Before date window start (YYYY-MM-DD). Defaults to 30 days before --before.")
@click.option("--after-start", "after_start", default=None, callback=_parse_date,
              help="After date window start (YYYY-MM-DD). Defaults to 30 days before --after.")
@click.option("--request", "request_file", default=None,
              type=click.Path(exists=True, dir_okay=False),
              help="Path to JSON request file (ChangeRequestAPI schema). "
                   "Alternative to --aoi/--before/--after.")
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
@click.option("--use-ai", "use_ai", is_flag=True, default=False,
              help="Run Clay v1.5 feature extraction alongside deterministic baseline")
@click.option("--cache", "use_cache", is_flag=True, default=False,
              help="Enable session-level COG window cache (reduces repeat reads)")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output results as JSON (for programmatic use)")
def analyze(
    aoi: str | None,
    before: str | None,
    after: str | None,
    before_start: str | None,
    after_start: str | None,
    request_file: str | None,
    task: str,
    output: str,
    max_cloud: float,
    min_valid: float,
    force_composite: bool,
    use_ai: bool,
    use_cache: bool,
    as_json: bool,
) -> None:
    """Analyze a land area for vegetation change between two date windows.

    Finds the best before/after Sentinel-2 image pair for the given AOI,
    computes spectral indices and change detection, and writes evidence
    artifacts (PNG images, GeoJSON findings, provenance manifest) to
    the output directory.

    Two input modes:
    - Flag mode: --aoi polygon.geojson --before 2026-01-01 --after 2026-06-01
    - Request mode: --request request.json (reads ChangeRequestAPI JSON)

    Examples:

      oberon analyze --aoi aoi.geojson --before 2026-01-01 --after 2026-06-01

      oberon analyze --aoi aoi.geojson --before 2026-01-01 --after 2026-06-01 --json

      oberon analyze --request request.json --composite --use-ai -o output/
    """
    request = _build_request(
        request_file, aoi, before, after, before_start, after_start,
        task, max_cloud, min_valid,
    )

    output_dir = Path(output)

    logger = get_logger("oberon.analyze")
    logger.info("job.started", extra={
        "task": request.task, "aoi": str(aoi or request_file),
        "before": str(request.before), "after": str(request.after),
        "max_cloud": max_cloud, "min_valid": min_valid,
        "composite": force_composite,
    })

    if not as_json:
        click.echo(f"Oberon analyze — {request.task}")
        click.echo(f"  AOI:       {aoi or request_file}")
        click.echo(f"  Before:    {request.before[0]} to {request.before[1]}")
        click.echo(f"  After:     {request.after[0]} to {request.after[1]}")
        click.echo(f"  Max cloud: {max_cloud:.0f}%")
        click.echo(f"  Min valid: {min_valid:.0%}")
        click.echo(f"  Output:    {output_dir}")
        click.echo("")

    # Enable cache if requested.
    if use_cache:
        from oberon.pipeline.cog_reader import enable_cache

        enable_cache()

    # Run the pipeline.
    from oberon.cli.orchestrator import run_analysis

    # Progress callback prints stage status to stderr (keeps stdout clean for --json).
    def _progress(msg: str) -> None:
        if not as_json:
            click.echo(msg, err=True)

    bundle = run_analysis(
        request, output_dir,
        force_composite=force_composite,
        use_ai=use_ai,
        progress=_progress,
    )

    # Report result using the API serialization layer for --json.
    provenance = bundle.provenance
    abstention = provenance.get("abstention")
    is_abstained = bool(abstention and abstention.get("reason"))
    reason = abstention["reason"] if (abstention and isinstance(abstention, dict)) else ""

    if is_abstained:
        logger.info("job.abstained", extra={"outcome": "abstained", "reason": reason})

    if as_json:
        from oberon.api.serialization import serialize_bundle_to_response

        response = serialize_bundle_to_response(bundle)
        click.echo(response.model_dump_json(indent=2))
    elif is_abstained:
        click.echo(f"Abstained: {reason}")
    else:
        num_findings = len(provenance.get("findings", []))
        logger.info("job.completed", extra={"outcome": "complete", "findings": num_findings})
        click.echo(f"Analysis complete: {num_findings} finding(s)")
        click.echo(f"  Before image:  {bundle.before_image}")
        click.echo(f"  After image:   {bundle.after_image}")
        click.echo(f"  Overlay:       {bundle.overlay_image}")
        click.echo(f"  Findings:      {bundle.findings_geojson}")
        click.echo(f"  Provenance:    {bundle.provenance_manifest}")

    sys.exit(0)


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

        from oberon.pipeline.stac_discovery import STAC_URL

        urllib.request.urlopen(STAC_URL, timeout=5)
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

    # STAC is a core dependency — degraded when unreachable.
    if not status.get("stac_reachable"):
        status["status"] = "degraded"

    if as_json:
        click.echo(json.dumps(status, indent=2))
    else:
        click.echo(f"Oberon v{status['version']} — {status['status']}")
        click.echo(f"  Torch:     {'available' if status['torch_available'] else 'not installed'}")
        click.echo(f"  STAC API:  {'reachable' if status['stac_reachable'] else 'unreachable'}")
        click.echo(f"  Cache:     {status['cache_size_mb']} MB at {status['cache_dir']}")

    if status["status"] == "degraded":
        sys.exit(1)
    sys.exit(0)


@cli.command()
def init() -> None:
    """Check prerequisites and create the ~/.oberon/ config directory.

    Verifies Python, GDAL, and STAC reachability. Prints setup guidance
    if anything is missing. Useful as a first-run sanity check.
    """
    import subprocess

    click.echo(f"Oberon v{__version__} — setup check")
    click.echo("")

    # Python version.
    click.echo(f"  Python:    {sys.version.split()[0]}")

    # GDAL/rasterio check.
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import rasterio; print(rasterio.__gdal_version__)"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            click.echo(f"  GDAL:      {result.stdout.strip()}")
        else:
            click.echo("  GDAL:      MISSING — install: brew install gdal (macOS) or sudo apt install libgdal-dev (Linux)")
    except Exception:
        click.echo("  GDAL:      check failed")

    # STAC reachability.
    try:
        import urllib.request

        from oberon.pipeline.stac_discovery import STAC_URL

        urllib.request.urlopen(STAC_URL, timeout=5)
        click.echo("  STAC API:  reachable")
        stac_ok = True
    except Exception:
        click.echo("  STAC API:  unreachable")
        stac_ok = False

    # Create config dir.
    config_dir = Path.home() / ".oberon"
    config_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"  Config:    {config_dir} (created)")
    click.echo("")

    if stac_ok:
        click.echo("All set. Try: oberon analyze --aoi sample-aoi.geojson --before-start 2024-01-01 --before 2024-03-01 --after-start 2024-07-01 --after 2024-09-01")
    else:
        click.echo("STAC API unreachable — check your network or set OBERON_STAC_URL.")
        click.echo("You can still run offline tests: pytest tests/ -q")

    sys.exit(0)


@cli.command()
@click.option("--lat", required=True, type=click.FloatRange(-90, 90),
              help="Latitude of the AOI center (decimal degrees)")
@click.option("--lon", required=True, type=click.FloatRange(-180, 180),
              help="Longitude of the AOI center (decimal degrees)")
@click.option("--buffer", "buffer_km", default=2.5, type=click.FloatRange(0.1, 20),
              help="Half-width of the bounding box in km (default: 2.5 = ~5km box)")
@click.option("--output", "-o", default=None,
              help="Output file path. If omitted, prints GeoJSON to stdout.")
def aoi(lat: float, lon: float, buffer_km: float, output: str | None) -> None:
    """Generate a bounding-box AOI polygon from a lat/lon coordinate.

    Creates a square GeoJSON polygon centered on the given coordinate.
    Useful when you don't have a ready-made GeoJSON polygon.

    \b
    Examples:
      oberon aoi --lat -7.475 --lon -55.175 -o amazon.geojson
      oberon aoi --lat 41.82 --lon -93.62 --buffer 1.0 > iowa.geojson
      oberon aoi --lat -7.475 --lon -55.175 --buffer 2.5 | oberon analyze --request /dev/stdin
    """
    import math

    # Convert km buffer to degrees. 1 degree latitude ~111 km.
    # Longitude degrees shrink with cos(lat).
    lat_offset = buffer_km / 111.0
    lon_offset = buffer_km / (111.0 * math.cos(math.radians(lat)))

    min_lon = round(lon - lon_offset, 6)
    max_lon = round(lon + lon_offset, 6)
    min_lat = round(lat - lat_offset, 6)
    max_lat = round(lat + lat_offset, 6)

    geojson = {
        "type": "Feature",
        "properties": {
            "name": f"aoi-{lat:.4f}-{lon:.4f}",
            "center": [lon, lat],
            "buffer_km": buffer_km,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]],
        },
    }

    text = json.dumps(geojson, indent=2)
    if output:
        Path(output).write_text(text)
        click.echo(f"AOI written to {output}")
        click.echo(f"  Center:    {lat}, {lon}")
        click.echo(f"  Buffer:    {buffer_km} km")
        click.echo(f"  Bounds:    {min_lon}, {min_lat} to {max_lon}, {max_lat}")
    else:
        click.echo(text)


def main() -> None:
    """Entry point for `oberon` CLI (console_scripts)."""
    configure_logging()
    cli()
