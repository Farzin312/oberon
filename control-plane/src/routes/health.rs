use axum::extract::State;
use axum::response::Json;
use serde_json::json;

use super::AppState;
use oberon_control_plane::telemetry;

pub async fn get_health(State(state): State<AppState>) -> Json<serde_json::Value> {
    let python_available = std::process::Command::new("python")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    let resources = telemetry::snapshot_resources(&state.dashboard_dir);

    Json(json!({
        "status": "healthy",
        "version": env!("CARGO_PKG_VERSION"),
        "python_available": python_available,
        "active_jobs": state.job_metrics.active_count(),
        "total_jobs": state.job_metrics.total_count(),
        "mem_total_mb": resources.mem_total_mb,
        "mem_available_mb": resources.mem_available_mb,
        "disk_total_gb": resources.disk_total_gb,
        "disk_free_gb": resources.disk_free_gb,
    }))
}
