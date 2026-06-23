use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Json};
use chrono::Utc;
use serde::Deserialize;
use serde_json::json;
use uuid::Uuid;

use super::AppState;
use oberon_control_plane::db;
use oberon_control_plane::models::{CreateReviewRequest, Review};

#[derive(Deserialize)]
pub struct ReviewQuery {
    pub portfolio: Option<String>,
    pub state: Option<String>,
}

pub async fn list_reviews(
    State(state): State<AppState>,
    Query(q): Query<ReviewQuery>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let portfolio_id = q.portfolio.as_deref().unwrap_or("");
    let list = db::list_reviews(&state.db, portfolio_id, q.state.as_deref())
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(json!(list)))
}

pub async fn create_review(
    State(state): State<AppState>,
    Json(req): Json<CreateReviewRequest>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let review = Review {
        id,
        run_id: req.run_id,
        finding_idx: req.finding_idx,
        portfolio_id: req.portfolio_id,
        state: req.state,
        reviewer_notes: req.reviewer_notes,
        reviewed_at: Some(now.clone()),
        created_at: now,
    };
    db::create_review(&state.db, &review)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok((StatusCode::CREATED, Json(json!(review))))
}

/// Export all review decisions as JSON (for model calibration feedback loop).
/// GET /v1/reviews/export?portfolio=<id>
pub async fn export_feedback(
    State(state): State<AppState>,
    Query(q): Query<ReviewQuery>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let portfolio_id = q.portfolio.as_deref().unwrap_or("");
    let list = db::list_reviews(&state.db, portfolio_id, None)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    // Filter to only reviewed (non-pending) decisions.
    let reviewed: Vec<&Review> = list.iter().filter(|r| r.state != "pending").collect();

    Ok(Json(json!({
        "portfolio_id": portfolio_id,
        "total_decisions": reviewed.len(),
        "reviews": reviewed,
    })))
}
