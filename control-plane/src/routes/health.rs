use axum::extract::State;
use axum::response::Json;
use serde_json::json;

use super::AppState;

pub async fn get_health(State(_state): State<AppState>) -> Json<serde_json::Value> {
    let python_available = std::process::Command::new("python")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);

    Json(json!({
        "status": "healthy",
        "version": env!("CARGO_PKG_VERSION"),
        "python_available": python_available,
    }))
}
