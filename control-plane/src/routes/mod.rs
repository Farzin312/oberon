pub mod audit;
pub mod change;
pub mod dashboard;
pub mod health;
pub mod portfolio;
pub mod review;

use axum::{
    Router,
    extract::{DefaultBodyLimit, Request},
    http::{HeaderName, HeaderValue, Method, header},
    middleware::{Next, from_fn, from_fn_with_state},
    response::Response,
    routing::{get, post},
};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Semaphore;
use tower_http::compression::CompressionLayer;
use tower_http::cors::CorsLayer;

use crate::middleware::audit::audit_middleware;
use crate::middleware::auth;
use crate::middleware::ratelimit::{self, RateLimiter};
use oberon_control_plane::db::Db;

/// Largest request body accepted (geometry payloads are the biggest legit case).
const MAX_BODY_BYTES: usize = 4 * 1024 * 1024;

#[derive(Clone)]
pub struct AppState {
    pub db: Db,
    pub auth_disabled: bool,
    pub python_path: String,
    pub dashboard_dir: PathBuf,
    pub output_dir: PathBuf,
    pub job_metrics: oberon_control_plane::telemetry::JobMetrics,
    /// Caps concurrent analysis subprocesses; excess runs queue on a permit.
    pub run_semaphore: Arc<Semaphore>,
    pub rate_limiter: RateLimiter,
}

pub fn build_app(
    db: Db,
    auth_disabled: bool,
    python_path: String,
    dashboard_dir: PathBuf,
    output_dir: PathBuf,
    max_concurrent_runs: usize,
    cors_allow_origin: Option<String>,
) -> Router {
    let state = AppState {
        db: db.clone(),
        auth_disabled,
        python_path,
        dashboard_dir,
        output_dir,
        job_metrics: oberon_control_plane::telemetry::JobMetrics::default(),
        run_semaphore: Arc::new(Semaphore::new(max_concurrent_runs.max(1))),
        rate_limiter: RateLimiter::default(),
    };

    // Routes that require auth.
    let protected = Router::new()
        .route("/v1/change", post(change::post_change))
        .route("/v1/jobs/{id}", get(change::get_job))
        .route("/v1/jobs/{id}/artifacts/{name}", get(change::get_artifact))
        .route(
            "/v1/portfolios",
            post(portfolio::create_portfolio).get(portfolio::list_portfolios),
        )
        .route(
            "/v1/portfolios/{id}",
            get(portfolio::get_portfolio)
                .patch(portfolio::update_portfolio)
                .delete(portfolio::delete_portfolio),
        )
        .route(
            "/v1/portfolios/{id}/polygons",
            post(portfolio::add_polygon).get(portfolio::list_polygons),
        )
        .route(
            "/v1/polygons/{id}",
            axum::routing::patch(portfolio::update_polygon).delete(portfolio::delete_polygon),
        )
        .route("/v1/portfolios/{id}/run", post(portfolio::run_portfolio))
        .route("/v1/portfolios/{id}/runs", get(portfolio::list_runs))
        .route("/v1/portfolios/{id}/findings", get(portfolio::get_findings))
        .route(
            "/v1/reviews",
            get(review::list_reviews).post(review::create_review),
        )
        .route("/v1/reviews/export", get(review::export_feedback))
        .route("/v1/audit/export", get(audit::export_audit))
        .layer(from_fn_with_state(state.clone(), auth::auth_middleware));

    // Public routes.
    let public = Router::new().route("/v1/health", get(health::get_health));

    // Dashboard (static files, no auth for local dev).
    let dashboard = Router::new()
        .route("/", get(dashboard::serve_index))
        .route("/{file}", get(dashboard::serve_static));

    // Restrictive CORS: only the methods/headers we use, and cross-origin only
    // for an explicitly configured origin. Same-origin dashboard is unaffected.
    let mut cors = CorsLayer::new()
        .allow_methods([
            Method::GET,
            Method::POST,
            Method::PATCH,
            Method::DELETE,
            Method::OPTIONS,
        ])
        .allow_headers([header::CONTENT_TYPE, HeaderName::from_static("x-api-key")]);
    if let Some(origin) = cors_allow_origin.as_deref().and_then(|o| o.parse::<HeaderValue>().ok()) {
        cors = cors.allow_origin(origin);
    }

    Router::new()
        .merge(protected)
        .merge(public)
        .merge(dashboard)
        .layer(from_fn_with_state(state.clone(), audit_middleware))
        .layer(from_fn(security_headers))
        .layer(DefaultBodyLimit::max(MAX_BODY_BYTES))
        // Rate limit is outermost so abusive clients are rejected before any work.
        .layer(from_fn_with_state(state.clone(), ratelimit::rate_limit))
        .layer(cors)
        .layer(CompressionLayer::new())
        .with_state(state)
}

/// Baseline security response headers applied to every response.
async fn security_headers(req: Request, next: Next) -> Response {
    let mut res = next.run(req).await;
    let h = res.headers_mut();
    h.insert("x-content-type-options", HeaderValue::from_static("nosniff"));
    h.insert("x-frame-options", HeaderValue::from_static("DENY"));
    h.insert("referrer-policy", HeaderValue::from_static("no-referrer"));
    res
}
