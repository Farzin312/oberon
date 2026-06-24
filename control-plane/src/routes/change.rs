use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Json as AxumJson};
use chrono::Utc;
use serde_json::json;
use tracing::{error, info};
use uuid::Uuid;

use super::AppState;
use oberon_control_plane::db;
use oberon_control_plane::models::{ChangeRequestAPI, Run};
use oberon_control_plane::telemetry::{self, Timer};

pub async fn post_change(
    State(state): State<AppState>,
    AxumJson(req): AxumJson<ChangeRequestAPI>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let job_id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();

    // Create run record as pending.
    let run = Run {
        id: job_id.clone(),
        portfolio_id: None,
        polygon_id: None,
        status: "pending".into(),
        output_dir: None,
        findings_count: 0,
        error_message: None,
        created_at: now,
        completed_at: None,
    };
    db::create_run(&state.db, &run).map_err(|e| {
        error!(operation = "create_run", error = %e, "db.error");
        (StatusCode::INTERNAL_SERVER_ERROR, e.to_string())
    })?;

    info!(job_id = %job_id, "job.created");

    // Spawn the pipeline in background.
    let db = state.db.clone();
    let python_path = state.python_path.clone();
    let jid = job_id.clone();
    let metrics = state.job_metrics.clone();
    let output_dir = state.output_dir.clone();
    let sem = state.run_semaphore.clone();

    tokio::spawn(async move {
        // Wait for a run permit; bounds concurrent analysis subprocesses.
        let _permit = match sem.acquire_owned().await {
            Ok(p) => p,
            Err(_) => return,
        };
        let _guard = metrics.start();
        let timer = Timer::start();

        // Update status to running.
        let _ = db::update_run_status(&db, &jid, "running", 0, None, None);

        match oberon_control_plane::pipeline::run_pipeline(&python_path, &req, &jid, &output_dir)
            .await
        {
            Ok(result) => {
                let now = Utc::now().to_rfc3339();
                let _ = db::update_run_status(
                    &db,
                    &jid,
                    &result.status,
                    result.findings_count as i64,
                    result.error_message.as_deref(),
                    Some(&now),
                );
                // Store output_dir for artifact serving.
                let _ = db::update_run_output_dir(&db, &jid, &result.output_dir.to_string_lossy());

                let output_mb = telemetry::dir_size_mb(&result.output_dir);
                let peak_rss_mb = telemetry::child_peak_rss_mb();
                let duration_ms = timer.elapsed_ms();

                if result.status == "completed" {
                    info!(
                        job_id = %jid,
                        findings_count = result.findings_count,
                        duration_ms,
                        output_mb = format!("{output_mb:.1}"),
                        peak_rss_mb,
                        "job.completed"
                    );
                } else if result.status == "abstained" {
                    info!(
                        job_id = %jid,
                        duration_ms,
                        output_mb = format!("{output_mb:.1}"),
                        peak_rss_mb,
                        "job.abstained"
                    );
                }
            }
            Err(e) => {
                let now = Utc::now().to_rfc3339();
                let duration_ms = timer.elapsed_ms();
                let _ =
                    db::update_run_status(&db, &jid, "failed", 0, Some(&e.to_string()), Some(&now));
                error!(
                    job_id = %jid,
                    error = %e,
                    duration_ms,
                    "job.failed"
                );
            }
        }
    });

    Ok((
        StatusCode::ACCEPTED,
        AxumJson(json!({ "job_id": job_id, "status": "pending" })),
    ))
}

pub async fn get_job(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let run = db::get_run(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    match run {
        Some(r) => Ok((
            StatusCode::OK,
            AxumJson(json!({
                "id": r.id,
                "status": r.status,
                "findings_count": r.findings_count,
                "error": r.error_message,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
            })),
        )),
        None => Err((StatusCode::NOT_FOUND, format!("Job {id} not found"))),
    }
}

pub async fn get_artifact(
    State(state): State<AppState>,
    Path((id, name)): Path<(String, String)>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let run = db::get_run(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let run = run.ok_or((StatusCode::NOT_FOUND, "Job not found".to_string()))?;

    let output_dir = run.output_dir.ok_or((
        StatusCode::NOT_FOUND,
        "No artifacts for this job".to_string(),
    ))?;

    // Only allow known artifact names (prevent path traversal).
    let allowed = [
        "before.png",
        "after.png",
        "overlay.png",
        "findings.geojson",
        "provenance.json",
    ];
    if !allowed.contains(&name.as_str()) {
        return Err((StatusCode::BAD_REQUEST, format!("Unknown artifact: {name}")));
    }

    let path = std::path::Path::new(&output_dir).join(&name);
    if !path.exists() {
        return Err((StatusCode::NOT_FOUND, format!("Artifact {name} not found")));
    }

    let data = tokio::fs::read(&path)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    // Determine content type.
    let content_type = if name.ends_with(".png") {
        "image/png"
    } else if name.ends_with(".geojson") || name.ends_with(".json") {
        "application/json"
    } else {
        "application/octet-stream"
    };

    Ok((
        StatusCode::OK,
        [
            ("content-type", content_type.to_string()),
            ("cache-control", "public, max-age=3600".to_string()),
        ],
        data,
    ))
}
