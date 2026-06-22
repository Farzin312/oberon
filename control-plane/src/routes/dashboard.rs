use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};

use super::AppState;

pub async fn serve_index(
    State(state): State<AppState>,
) -> Response {
    let path = state.dashboard_dir.join("index.html");
    match tokio::fs::read_to_string(&path).await {
        Ok(html) => (
            StatusCode::OK,
            [("content-type", "text/html; charset=utf-8")],
            html,
        ).into_response(),
        Err(_) => (
            StatusCode::NOT_FOUND,
            "Dashboard not built. Create dashboard/index.html",
        ).into_response(),
    }
}

pub async fn serve_static(
    State(state): State<AppState>,
    Path(file): Path<String>,
) -> Response {
    // Prevent path traversal.
    if file.contains("..") || file.contains('/') {
        return (StatusCode::BAD_REQUEST, "Invalid file path").into_response();
    }

    let path = state.dashboard_dir.join(&file);
    match tokio::fs::read(&path).await {
        Ok(data) => {
            let content_type = if file.ends_with(".js") {
                "application/javascript"
            } else if file.ends_with(".css") {
                "text/css"
            } else if file.ends_with(".png") {
                "image/png"
            } else {
                "application/octet-stream"
            };
            (
                StatusCode::OK,
                [("content-type", content_type.to_string())],
                data,
            ).into_response()
        }
        Err(_) => (StatusCode::NOT_FOUND, "File not found").into_response(),
    }
}
