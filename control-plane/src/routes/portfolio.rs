use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Json};
use chrono::Utc;
use serde_json::json;
use uuid::Uuid;

use super::AppState;
use oberon_control_plane::db;
use oberon_control_plane::models::{
    AddPolygonRequest, CreatePortfolioRequest, Polygon, Portfolio, Run,
};

pub async fn create_portfolio(
    State(state): State<AppState>,
    Json(req): Json<CreatePortfolioRequest>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let p = Portfolio {
        id,
        name: req.name,
        task: req.task,
        max_cloud_fraction: req.max_cloud_fraction,
        before_from: req.before_from,
        before_to: req.before_to,
        after_from: req.after_from,
        after_to: req.after_to,
        use_ai: req.use_ai,
        alert_webhook_url: req.alert_webhook_url,
        created_at: now,
    };
    db::create_portfolio(&state.db, &p)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok((StatusCode::CREATED, Json(json!(p))))
}

pub async fn list_portfolios(
    State(state): State<AppState>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let list = db::list_portfolios(&state.db)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(json!(list)))
}

pub async fn get_portfolio(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let p = db::get_portfolio(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    match p {
        Some(p) => Ok((StatusCode::OK, Json(json!(p)))),
        None => Err((StatusCode::NOT_FOUND, format!("Portfolio {id} not found"))),
    }
}

pub async fn delete_portfolio(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let deleted = db::delete_portfolio(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    if deleted {
        Ok((StatusCode::NO_CONTENT, Json(json!({}))))
    } else {
        Err((StatusCode::NOT_FOUND, format!("Portfolio {id} not found")))
    }
}

pub async fn add_polygon(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(req): Json<AddPolygonRequest>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let poly_id = Uuid::new_v4().to_string();
    let now = Utc::now().to_rfc3339();
    let poly = Polygon {
        id: poly_id,
        portfolio_id: id,
        geometry_json: serde_json::to_string(&req.geometry)
            .map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?,
        label: req.label,
        created_at: now,
    };
    db::add_polygon(&state.db, &poly)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok((StatusCode::CREATED, Json(json!(poly))))
}

pub async fn list_polygons(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let list = db::list_polygons(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(json!(list)))
}

pub async fn run_portfolio(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    // Verify portfolio exists.
    let portfolio = db::get_portfolio(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?
        .ok_or((StatusCode::NOT_FOUND, format!("Portfolio {id} not found")))?;

    let polygons = db::list_polygons(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let mut job_ids = Vec::new();
    let now = Utc::now().to_rfc3339();

    for poly in polygons {
        let job_id = Uuid::new_v4().to_string();
        let run = Run {
            id: job_id.clone(),
            portfolio_id: Some(id.clone()),
            polygon_id: Some(poly.id.clone()),
            status: "pending".into(),
            output_dir: None,
            findings_count: 0,
            error_message: None,
            created_at: now.clone(),
            completed_at: None,
        };
        db::create_run(&state.db, &run)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        // Spawn pipeline for this polygon.
        let db_clone = state.db.clone();
        let python_path = state.python_path.clone();
        let output_dir = state.output_dir.clone();
        let jid = job_id.clone();
        let geometry: serde_json::Value = serde_json::from_str(&poly.geometry_json)
            .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

        // Build a ChangeRequestAPI from the polygon geometry using portfolio config.
        let req = oberon_control_plane::models::ChangeRequestAPI {
            geometry,
            before: oberon_control_plane::models::TimeWindow {
                from: portfolio.before_from.clone(),
                to: portfolio.before_to.clone(),
            },
            after: oberon_control_plane::models::TimeWindow {
                from: portfolio.after_from.clone(),
                to: portfolio.after_to.clone(),
            },
            task: portfolio.task.clone(),
            max_cloud_fraction: portfolio.max_cloud_fraction,
            use_ai: portfolio.use_ai,
        };

        tokio::spawn(async move {
            let _ = db::update_run_status(&db_clone, &jid, "running", 0, None, None);
            match oberon_control_plane::pipeline::run_pipeline(
                &python_path,
                &req,
                &jid,
                &output_dir,
            )
            .await
            {
                Ok(result) => {
                    let now = Utc::now().to_rfc3339();
                    let _ = db::update_run_status(
                        &db_clone,
                        &jid,
                        &result.status,
                        result.findings_count as i64,
                        result.error_message.as_deref(),
                        Some(&now),
                    );
                    let _ = db::update_run_output_dir(
                        &db_clone,
                        &jid,
                        &result.output_dir.to_string_lossy(),
                    );
                }
                Err(e) => {
                    let now = Utc::now().to_rfc3339();
                    let _ = db::update_run_status(
                        &db_clone,
                        &jid,
                        "failed",
                        0,
                        Some(&e.to_string()),
                        Some(&now),
                    );
                }
            }
        });

        job_ids.push(job_id);
    }

    Ok((
        StatusCode::ACCEPTED,
        Json(json!({ "jobs": job_ids, "count": job_ids.len() })),
    ))
}

pub async fn get_findings(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let runs = db::list_runs(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let mut features = Vec::new();
    for run in &runs {
        if run.status != "completed" {
            continue;
        }
        if let Some(output_dir) = &run.output_dir {
            let path = std::path::Path::new(output_dir).join("findings.geojson");
            if let Ok(data) = std::fs::read_to_string(&path)
                && let Ok(geojson) = serde_json::from_str::<serde_json::Value>(&data)
                && let Some(feat_array) = geojson.get("features").and_then(|f| f.as_array())
            {
                for feat in feat_array {
                    let mut feat_clone = feat.clone();
                    if let Some(obj) = feat_clone.as_object_mut()
                        && let Some(props) =
                            obj.get_mut("properties").and_then(|p| p.as_object_mut())
                    {
                        props.insert("run_id".to_string(), serde_json::json!(run.id));
                    }
                    features.push(feat_clone);
                }
            }
        }
    }

    Ok(Json(json!({
        "type": "FeatureCollection",
        "features": features,
    })))
}

pub async fn list_runs(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, (StatusCode, String)> {
    let list = db::list_runs(&state.db, &id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(json!(list)))
}
