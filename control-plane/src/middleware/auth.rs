use axum::extract::{Request, State};
use axum::http::StatusCode;
use axum::middleware::Next;
use axum::response::Response;
use sha2::{Sha256, Digest};

use crate::routes::AppState;
use oberon_control_plane::db;

/// Auth middleware: extract X-API-Key header, validate against SQLite.
/// If OBERON_AUTH_DISABLED=1, all requests pass through.
pub async fn auth_middleware(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Skip auth in local dev mode.
    if state.auth_disabled {
        return Ok(next.run(req).await);
    }

    let key = req
        .headers()
        .get("x-api-key")
        .and_then(|v| v.to_str().ok())
        .ok_or(StatusCode::UNAUTHORIZED)?;

    // Hash the key and look it up.
    let mut hasher = Sha256::new();
    hasher.update(key.as_bytes());
    let key_hash = hex::encode(hasher.finalize());

    match db::validate_api_key(&state.db, &key_hash) {
        Ok(Some(_user)) => Ok(next.run(req).await),
        Ok(None) => Err(StatusCode::UNAUTHORIZED),
        Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
    }
}
