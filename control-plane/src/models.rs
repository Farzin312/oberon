use serde::{Deserialize, Serialize};

// ---- Portfolio ----

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Portfolio {
    pub id: String,
    pub name: String,
    pub task: String,
    pub max_cloud_fraction: f64,
    pub before_from: String,
    pub before_to: String,
    pub after_from: String,
    pub after_to: String,
    pub use_ai: bool,
    pub alert_webhook_url: Option<String>,
    pub created_at: String,
}

#[derive(Deserialize)]
pub struct CreatePortfolioRequest {
    pub name: String,
    #[serde(default = "default_task")]
    pub task: String,
    #[serde(default = "default_cloud")]
    pub max_cloud_fraction: f64,
    #[serde(default = "default_before_from")]
    pub before_from: String,
    #[serde(default = "default_before_to")]
    pub before_to: String,
    #[serde(default = "default_after_from")]
    pub after_from: String,
    #[serde(default = "default_after_to")]
    pub after_to: String,
    #[serde(default = "default_use_ai")]
    pub use_ai: bool,
    pub alert_webhook_url: Option<String>,
}

fn default_task() -> String {
    "vegetation_disturbance".into()
}
fn default_cloud() -> f64 {
    0.15
}
fn default_before_from() -> String {
    "2026-01-01".into()
}
fn default_before_to() -> String {
    "2026-01-31".into()
}
fn default_after_from() -> String {
    "2026-06-01".into()
}
fn default_after_to() -> String {
    "2026-06-30".into()
}
fn default_use_ai() -> bool {
    false
}

// ---- Polygon ----

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Polygon {
    pub id: String,
    pub portfolio_id: String,
    pub geometry_json: String,
    pub label: Option<String>,
    pub created_at: String,
}

#[derive(Deserialize)]
pub struct AddPolygonRequest {
    pub geometry: serde_json::Value,
    pub label: Option<String>,
}

// ---- Run ----

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Run {
    pub id: String,
    pub portfolio_id: Option<String>,
    pub polygon_id: Option<String>,
    pub status: String,
    pub output_dir: Option<String>,
    pub findings_count: i64,
    pub error_message: Option<String>,
    pub created_at: String,
    pub completed_at: Option<String>,
}

// ---- Review ----

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Review {
    pub id: String,
    pub run_id: String,
    pub finding_idx: i64,
    pub portfolio_id: Option<String>,
    pub state: String,
    pub reviewer_notes: Option<String>,
    pub reviewed_at: Option<String>,
    pub created_at: String,
}

#[derive(Deserialize)]
pub struct CreateReviewRequest {
    pub run_id: String,
    pub finding_idx: i64,
    pub portfolio_id: Option<String>,
    #[serde(default = "default_review_state")]
    pub state: String,
    pub reviewer_notes: Option<String>,
}

fn default_review_state() -> String {
    "pending".into()
}

// ---- Audit ----

#[derive(Clone, Debug, Serialize)]
pub struct AuditEntry {
    pub timestamp: String,
    pub method: String,
    pub path: String,
    pub user_name: Option<String>,
    pub status_code: i64,
    pub duration_ms: i64,
}

// ---- API response shapes matching Python Pydantic contracts ----

#[derive(Serialize)]
pub struct ChangeResponse {
    pub status: String,
    pub findings: Vec<serde_json::Value>,
    pub artifacts: Option<ArtifactPaths>,
}

#[derive(Serialize)]
pub struct ArtifactPaths {
    pub before: String,
    pub after: String,
    pub overlay: String,
}

#[derive(Deserialize, Serialize)]
pub struct ChangeRequestAPI {
    pub geometry: serde_json::Value,
    pub before: TimeWindow,
    pub after: TimeWindow,
    #[serde(default = "default_task")]
    pub task: String,
    #[serde(default = "default_cloud")]
    pub max_cloud_fraction: f64,
    #[serde(default = "default_use_ai")]
    pub use_ai: bool,
}

#[derive(Deserialize, Serialize)]
pub struct TimeWindow {
    pub from: String,
    pub to: String,
}
