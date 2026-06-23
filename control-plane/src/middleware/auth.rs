use axum::extract::{Request, State};
use axum::http::StatusCode;
use axum::middleware::Next;
use axum::response::Response;
use sha2::{Digest, Sha256};
use tracing::warn;

use crate::routes::AppState;
use oberon_control_plane::db;

/// Auth middleware: extract X-API-Key header, validate against SQLite.
/// If OBERON_AUTH_DISABLED=1, all requests pass through.
///
/// Security: logs the rejection reason and path, never the key value.
pub async fn auth_middleware(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    // Skip auth in local dev mode.
    if state.auth_disabled {
        return Ok(next.run(req).await);
    }

    let path = req.uri().path().to_string();

    let key = req.headers().get("x-api-key").and_then(|v| v.to_str().ok());

    if key.is_none() {
        warn!(reason = "missing_key", path = %path, "auth.rejected");
        return Err(StatusCode::UNAUTHORIZED);
    }

    // Hash the key and look it up.
    let mut hasher = Sha256::new();
    hasher.update(key.unwrap().as_bytes());
    let key_hash = hex::encode(hasher.finalize());

    match db::validate_api_key(&state.db, &key_hash) {
        Ok(Some(_user)) => Ok(next.run(req).await),
        Ok(None) => {
            warn!(reason = "invalid_key", path = %path, "auth.rejected");
            Err(StatusCode::UNAUTHORIZED)
        }
        Err(e) => {
            tracing::error!(error = %e, path = %path, "db.error");
            Err(StatusCode::INTERNAL_SERVER_ERROR)
        }
    }
}
