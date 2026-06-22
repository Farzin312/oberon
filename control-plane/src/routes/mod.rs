pub mod health;
pub mod change;
pub mod portfolio;
pub mod review;
pub mod audit;
pub mod dashboard;

use axum::{
    Router,
    routing::{get, post},
    middleware::from_fn_with_state,
};
use std::path::PathBuf;
use tower_http::cors::CorsLayer;
use tower_http::compression::CompressionLayer;

use oberon_control_plane::db::Db;
use crate::middleware::auth;

#[derive(Clone)]
pub struct AppState {
    pub db: Db,
    pub auth_disabled: bool,
    pub python_path: String,
    pub dashboard_dir: PathBuf,
}

pub fn build_app(
    db: Db,
    auth_disabled: bool,
    python_path: String,
    dashboard_dir: PathBuf,
) -> Router {
    let state = AppState {
        db: db.clone(),
        auth_disabled,
        python_path,
        dashboard_dir,
    };

    // Routes that require auth.
    let protected = Router::new()
        .route("/v1/change", post(change::post_change))
        .route("/v1/jobs/{id}", get(change::get_job))
        .route("/v1/jobs/{id}/artifacts/{name}", get(change::get_artifact))
        .route("/v1/portfolios", post(portfolio::create_portfolio).get(portfolio::list_portfolios))
        .route("/v1/portfolios/{id}", get(portfolio::get_portfolio).delete(portfolio::delete_portfolio))
        .route("/v1/portfolios/{id}/polygons", post(portfolio::add_polygon).get(portfolio::list_polygons))
        .route("/v1/portfolios/{id}/run", post(portfolio::run_portfolio))
        .route("/v1/portfolios/{id}/findings", get(portfolio::get_findings))
        .route("/v1/reviews", get(review::list_reviews).post(review::create_review))
        .route("/v1/audit/export", get(audit::export_audit))
        .layer(from_fn_with_state(
            state.clone(),
            auth::auth_middleware,
        ));

    // Public routes.
    let public = Router::new()
        .route("/v1/health", get(health::get_health));

    // Dashboard (static files, no auth for local dev).
    let dashboard = Router::new()
        .route("/", get(dashboard::serve_index))
        .route("/{file}", get(dashboard::serve_static));

    Router::new()
        .merge(protected)
        .merge(public)
        .merge(dashboard)
        .layer(CorsLayer::permissive())
        .layer(CompressionLayer::new())
        .with_state(state)
}
