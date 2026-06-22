use axum::extract::State;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Json};

use super::AppState;
use oberon_control_plane::db;

pub async fn export_audit(
    State(state): State<AppState>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let entries = db::list_audit(&state.db, 1000)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(serde_json::json!(entries)))
}
