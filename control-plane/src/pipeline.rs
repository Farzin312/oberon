use anyhow::{Result, anyhow, bail};
use std::path::{Path, PathBuf};
use std::process::Command;
use tokio::fs;
use tracing::{error, info};

use crate::models::ChangeRequestAPI;

/// State machine for a pipeline job.
#[derive(Debug, Clone)]
pub struct JobResult {
    pub status: String,       // "completed" | "failed" | "abstained"
    pub findings_count: usize,
    pub error_message: Option<String>,
    pub output_dir: PathBuf,
}

/// Spawn the Python pipeline as a subprocess and wait for it to complete.
///
/// Communication contract:
///   python -m oberon.cli analyze --request /tmp/job-<id>.json -o /tmp/output-<id>/ --json
/// Python exits 0 on success (including abstention). Non-zero on error.
/// Output dir contains: findings.geojson, provenance.json, before.png, after.png, overlay.png
pub async fn run_pipeline(
    python_path: &str,
    request: &ChangeRequestAPI,
    job_id: &str,
) -> Result<JobResult> {
    let tmp_dir = std::env::temp_dir();
    let request_path = tmp_dir.join(format!("oberon-job-{job_id}.json"));
    let output_dir = tmp_dir.join(format!("oberon-output-{job_id}"));

    // Write request JSON.
    let request_json = serde_json::to_string_pretty(request)?;
    fs::write(&request_path, &request_json).await?;

    // Spawn Python subprocess (blocking, so use spawn_blocking).
    let output_dir_str = output_dir.to_string_lossy().to_string();
    let request_path_str = request_path.to_string_lossy().to_string();
    let py = python_path.to_string();

    let result = tokio::task::spawn_blocking(move || {
        Command::new(&py)
            .args([
                "-m", "oberon.cli", "analyze",
                "--request", &request_path_str,
                "-o", &output_dir_str,
                "--json",
            ])
            .output()
    })
    .await
    .map_err(|e| {
        error!(job_id = %job_id, error = %e, "pipeline.spawn_error");
        anyhow!("subprocess task failed: {e}")
    })?
    .map_err(|e| {
        error!(job_id = %job_id, error = %e, "pipeline.spawn_error");
        anyhow!("failed to spawn python: {e}")
    })?;

    // Clean up request file.
    let _ = std::fs::remove_file(&request_path);

    if !result.status.success() {
        let stderr = String::from_utf8_lossy(&result.stderr);
        let stdout = String::from_utf8_lossy(&result.stdout);
        error!(
            job_id = %job_id,
            exit_code = ?result.status.code(),
            stderr = %stderr.chars().take(500).collect::<String>(),
            "pipeline.spawn_error"
        );
        bail!(
            "pipeline failed (exit {:?}): stderr={stderr}; stdout={stdout}",
            result.status.code()
        );
    }

    // Parse the --json stdout for status.
    let stdout = String::from_utf8_lossy(&result.stdout);
    let response: serde_json::Value = serde_json::from_str(&stdout)
        .map_err(|e| {
            error!(job_id = %job_id, error = %e, "pipeline.spawn_error");
            anyhow!("failed to parse pipeline JSON output: {e}")
        })?;

    let status = response
        .get("status")
        .and_then(|v| v.as_str())
        .unwrap_or("failed")
        .to_string();

    let findings_count = response
        .get("findings")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    if status == "abstained" {
        info!(job_id = %job_id, "job.abstained");
        return Ok(JobResult {
            status: "abstained".into(),
            findings_count: 0,
            error_message: None,
            output_dir,
        });
    }

    info!(job_id = %job_id, status = %status, findings_count, "job.completed");
    Ok(JobResult {
        status: "completed".into(),
        findings_count,
        error_message: None,
        output_dir,
    })
}

/// Read findings.geojson from an output directory.
pub async fn read_findings_geojson(output_dir: &Path) -> Result<serde_json::Value> {
    let path = output_dir.join("findings.geojson");
    let data = fs::read_to_string(&path).await?;
    Ok(serde_json::from_str(&data)?)
}

/// Read provenance.json from an output directory.
pub async fn read_provenance(output_dir: &Path) -> Result<serde_json::Value> {
    let path = output_dir.join("provenance.json");
    let data = fs::read_to_string(&path).await?;
    Ok(serde_json::from_str(&data)?)
}
