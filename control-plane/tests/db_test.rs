use oberon_control_plane::db;
use oberon_control_plane::models::{Polygon, Portfolio, Review, Run, is_supported_task};

fn tmp_db() -> db::Db {
    let path = std::env::temp_dir().join(format!(
        "oberon-test-{}-{}.db",
        std::process::id(),
        uuid::Uuid::new_v4()
    ));
    db::open(&path).expect("open db")
}

#[test]
fn test_supported_task_scope() {
    assert!(is_supported_task("vegetation_disturbance"));
    assert!(!is_supported_task("burn_severity"));
}

#[test]
fn test_create_and_get_portfolio() {
    let db = tmp_db();
    let p = Portfolio {
        id: "test-portfolio-1".into(),
        name: "Test Portfolio".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();

    let got = db::get_portfolio(&db, "test-portfolio-1").unwrap();
    assert!(got.is_some());
    let got = got.unwrap();
    assert_eq!(got.name, "Test Portfolio");
    assert_eq!(got.task, "vegetation_disturbance");
}

#[test]
fn test_get_nonexistent_portfolio() {
    let db = tmp_db();
    let got = db::get_portfolio(&db, "does-not-exist").unwrap();
    assert!(got.is_none());
}

#[test]
fn test_list_portfolios() {
    let db = tmp_db();
    for i in 0..3 {
        let p = Portfolio {
            id: format!("p-{i}"),
            name: format!("Portfolio {i}"),
            task: "vegetation_disturbance".into(),
            max_cloud_fraction: 0.15,
            before_from: "2026-01-01".into(),
            before_to: "2026-01-31".into(),
            after_from: "2026-06-01".into(),
            after_to: "2026-06-30".into(),
            use_ai: false,
            alert_webhook_url: None,
            created_at: format!("2026-06-22T00:0{i}:00Z"),
        };
        db::create_portfolio(&db, &p).unwrap();
    }
    let list = db::list_portfolios(&db).unwrap();
    assert_eq!(list.len(), 3);
}

#[test]
fn test_update_portfolio() {
    let db = tmp_db();
    let p = Portfolio {
        id: "to-edit".into(),
        name: "Original".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();

    let edited = Portfolio {
        name: "Renamed".into(),
        max_cloud_fraction: 0.40,
        after_to: "2026-07-15".into(),
        use_ai: true,
        ..p.clone()
    };
    assert!(db::update_portfolio(&db, "to-edit", &edited).unwrap());

    let got = db::get_portfolio(&db, "to-edit").unwrap().unwrap();
    assert_eq!(got.name, "Renamed");
    assert_eq!(got.max_cloud_fraction, 0.40);
    assert_eq!(got.after_to, "2026-07-15");
    assert!(got.use_ai);
    // id + created_at preserved
    assert_eq!(got.id, "to-edit");
    assert_eq!(got.created_at, "2026-06-22T00:00:00Z");

    // Updating a missing id returns false.
    assert!(!db::update_portfolio(&db, "nope", &edited).unwrap());
}

#[test]
fn test_delete_portfolio() {
    let db = tmp_db();
    let p = Portfolio {
        id: "to-delete".into(),
        name: "Delete Me".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();
    assert!(db::delete_portfolio(&db, "to-delete").unwrap());
    assert!(db::get_portfolio(&db, "to-delete").unwrap().is_none());
}

#[test]
fn test_add_and_list_polygons() {
    let db = tmp_db();
    let p = Portfolio {
        id: "pf-poly".into(),
        name: "PF".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();

    let poly = Polygon {
        id: "poly-1".into(),
        portfolio_id: "pf-poly".into(),
        geometry_json: r#"{"type":"Polygon","coordinates":[]}"#.into(),
        label: Some("Plot A".into()),
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::add_polygon(&db, &poly).unwrap();

    let list = db::list_polygons(&db, "pf-poly").unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].label.as_deref(), Some("Plot A"));
}

#[test]
fn test_create_and_get_run() {
    let db = tmp_db();
    // FK: need a portfolio and polygon first.
    let p = Portfolio {
        id: "pf-run".into(),
        name: "PF".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();
    let poly = Polygon {
        id: "poly-run".into(),
        portfolio_id: "pf-run".into(),
        geometry_json: "{}".into(),
        label: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::add_polygon(&db, &poly).unwrap();

    let run = Run {
        id: "run-1".into(),
        portfolio_id: Some("pf-run".into()),
        polygon_id: Some("poly-run".into()),
        status: "pending".into(),
        output_dir: None,
        findings_count: 0,
        error_message: None,
        created_at: "2026-06-22T00:00:00Z".into(),
        completed_at: None,
    };
    db::create_run(&db, &run).unwrap();

    let got = db::get_run(&db, "run-1").unwrap().unwrap();
    assert_eq!(got.status, "pending");
    assert_eq!(got.findings_count, 0);

    // Update status.
    db::update_run_status(
        &db,
        "run-1",
        "completed",
        3,
        None,
        Some("2026-06-22T01:00:00Z"),
    )
    .unwrap();
    let got = db::get_run(&db, "run-1").unwrap().unwrap();
    assert_eq!(got.status, "completed");
    assert_eq!(got.findings_count, 3);
}

#[test]
fn test_reconcile_stale_runs() {
    let db = tmp_db();
    let p = Portfolio {
        id: "pf-stale".into(),
        name: "PF".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();

    let mk = |id: &str, status: &str| Run {
        id: id.into(),
        portfolio_id: Some("pf-stale".into()),
        polygon_id: None,
        status: status.into(),
        output_dir: None,
        findings_count: 0,
        error_message: None,
        created_at: "2026-06-22T00:00:00Z".into(),
        completed_at: None,
    };
    db::create_run(&db, &mk("r-running", "running")).unwrap();
    db::create_run(&db, &mk("r-pending", "pending")).unwrap();
    db::create_run(&db, &mk("r-done", "completed")).unwrap();

    let n = db::reconcile_stale_runs(&db, "2026-06-24T00:00:00Z").unwrap();
    assert_eq!(n, 2); // only running + pending flipped

    assert_eq!(db::get_run(&db, "r-running").unwrap().unwrap().status, "failed");
    assert_eq!(db::get_run(&db, "r-pending").unwrap().unwrap().status, "failed");
    // a finished run is untouched
    assert_eq!(db::get_run(&db, "r-done").unwrap().unwrap().status, "completed");
}

#[test]
fn test_review_lifecycle() {
    let db = tmp_db();
    // FK: need portfolio + run first.
    let p = Portfolio {
        id: "pf-rev".into(),
        name: "PF".into(),
        task: "vegetation_disturbance".into(),
        max_cloud_fraction: 0.15,
        before_from: "2026-01-01".into(),
        before_to: "2026-01-31".into(),
        after_from: "2026-06-01".into(),
        after_to: "2026-06-30".into(),
        use_ai: false,
        alert_webhook_url: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_portfolio(&db, &p).unwrap();
    let run = Run {
        id: "run-rev".into(),
        portfolio_id: Some("pf-rev".into()),
        polygon_id: None,
        status: "completed".into(),
        output_dir: None,
        findings_count: 1,
        error_message: None,
        created_at: "2026-06-22T00:00:00Z".into(),
        completed_at: Some("2026-06-22T01:00:00Z".into()),
    };
    db::create_run(&db, &run).unwrap();

    let review = Review {
        id: "rev-1".into(),
        run_id: "run-rev".into(),
        finding_idx: 0,
        portfolio_id: Some("pf-rev".into()),
        state: "pending".into(),
        reviewer_notes: None,
        reviewed_at: None,
        created_at: "2026-06-22T00:00:00Z".into(),
    };
    db::create_review(&db, &review).unwrap();

    let list = db::list_reviews(&db, "pf-rev", None).unwrap();
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].state, "pending");

    // Filter by state.
    let list = db::list_reviews(&db, "pf-rev", Some("approved")).unwrap();
    assert_eq!(list.len(), 0);
}

#[test]
fn test_api_key_create_and_validate() {
    let db = tmp_db();
    let key_hash = "abc123hash";
    db::store_api_key(&db, key_hash, "test-user", "2026-06-22T00:00:00Z").unwrap();

    let user = db::validate_api_key(&db, key_hash).unwrap();
    assert_eq!(user.as_deref(), Some("test-user"));

    let invalid = db::validate_api_key(&db, "wrong-hash").unwrap();
    assert!(invalid.is_none());
}
