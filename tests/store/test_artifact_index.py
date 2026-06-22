"""Tests for the artifact index (006 Phase 1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from oberon.core import EvidenceBundle
from oberon.store.artifact_index import build_run_artifact_index, compute_sha256


def _make_bundle(output_dir: Path) -> EvidenceBundle:
    """Create an EvidenceBundle with real files on disk for testing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    before = output_dir / "before.png"
    after = output_dir / "after.png"
    overlay = output_dir / "overlay.png"
    findings = output_dir / "findings.geojson"
    provenance = output_dir / "provenance.json"

    # Write some content to each file.
    before.write_bytes(b"\x89PNG fake")
    after.write_bytes(b"\x89PNG fake")
    overlay.write_bytes(b"\x89PNG fake")
    findings.write_text('{"type":"FeatureCollection","features":[]}')
    provenance_path = output_dir / "provenance.json"
    provenance.write_text('{"oberon_version":"0.1.0"}')

    return EvidenceBundle(
        output_dir=output_dir,
        before_image=before,
        after_image=after,
        overlay_image=overlay,
        findings_geojson=findings,
        provenance_manifest=provenance_path,
        provenance={},
    )


class TestComputeSha256:
    def test_known_content(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert compute_sha256(f) == expected

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.json"
        f.write_text("")
        expected = hashlib.sha256(b"").hexdigest()
        assert compute_sha256(f) == expected


class TestBuildRunArtifactIndex:
    """build_run_artifact_index: produces complete run index."""

    def test_has_required_fields(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-001"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        assert "run_id" in index
        assert "created_at" in index
        assert "artifacts" in index
        assert "checksums" in index
        assert "file_sizes" in index

    def test_run_id_starts_with_oberon(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-002"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        assert index["run_id"].startswith("oberon-")

    def test_custom_run_id(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-003"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir, run_id="custom-123")

        assert index["run_id"] == "custom-123"

    def test_checksums_for_json_geojson_only(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-004"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        # JSON/GeoJSON should have checksums.
        assert "findings_geojson" in index["checksums"]
        assert "provenance" in index["checksums"]

        # PNG files should NOT have checksums (too large).
        assert "before_image" not in index["checksums"]
        assert "after_image" not in index["checksums"]

    def test_checksums_match_actual_sha256(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-005"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        # Verify findings.geojson checksum.
        actual = compute_sha256(output_dir / "findings.geojson")
        assert index["checksums"]["findings_geojson"] == f"sha256:{actual}"

    def test_file_sizes_recorded(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-006"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        assert index["file_sizes"]["findings_geojson"] > 0
        assert index["file_sizes"]["before_image"] > 0

    def test_writes_index_json_to_disk(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-007"
        bundle = _make_bundle(output_dir)
        build_run_artifact_index(bundle, output_dir)

        index_path = output_dir / "artifact_index.json"
        assert index_path.exists()

        with open(index_path) as f:
            loaded = json.load(f)
        assert loaded["run_id"].startswith("oberon-")

    def test_artifact_paths_are_relative(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "run-008"
        bundle = _make_bundle(output_dir)
        index = build_run_artifact_index(bundle, output_dir)

        # Paths should be just filenames, not absolute paths.
        for name, path_str in index["artifacts"].items():
            if path_str:
                assert "/" not in path_str, f"{name} should be relative: {path_str}"
