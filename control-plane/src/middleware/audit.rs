use axum::extract::{Request, State};
use axum::http::StatusCode;
use axum::middleware::Next;
use axum::response::Response;
use chrono::Utc;
use std::time::Instant;

use crate::routes::AppState;
use oberon_control_plane::db;
use oberon_control_plane::models::AuditEntry;

/// Audit middleware: logs every request to the audit_log table.
/// Records method, path, authenticated user (if any), status code, duration.
pub async fn audit_middleware(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Result<Response, StatusCode> {
    let method = req.method().to_string();
    let path = req.uri().path().to_string();
    let start = Instant::now();

    // Run the request handler.
    let response = next.run(req).await;

    let status = response.status().as_u16() as i64;
    let duration_ms = start.elapsed().as_millis() as i64;
    let timestamp = Utc::now().to_rfc3339();

    let entry = AuditEntry {
        timestamp,
        method,
        path,
        user_name: None, // Set by auth middleware via request extensions in future.
        status_code: status,
        duration_ms,
    };

    // Fire and forget — audit logging must never break a request.
    if let Err(e) = db::insert_audit(&state.db, &entry) {
        tracing::warn!(error = %e, path = %entry.path, "audit.log_failed");
    }

    Ok(response)
}
