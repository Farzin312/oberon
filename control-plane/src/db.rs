use anyhow::{Result, anyhow};
use rusqlite::Connection;
use std::sync::{Arc, Mutex};

/// SQLite connection wrapped for thread-safe sharing.
pub type Db = Arc<Mutex<Connection>>;

pub fn open(path: &std::path::Path) -> Result<Db> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let conn = Connection::open(path)?;
    conn.execute_batch("PRAGMA journal_mode=WAL;")?;
    conn.execute_batch("PRAGMA foreign_keys=ON;")?;
    init_schema(&conn)?;
    Ok(Arc::new(Mutex::new(conn)))
}

fn init_schema(conn: &Connection) -> Result<()> {
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            task TEXT NOT NULL DEFAULT 'vegetation_disturbance',
            max_cloud_fraction REAL NOT NULL DEFAULT 0.15,
            before_from TEXT NOT NULL DEFAULT '2026-01-01',
            before_to TEXT NOT NULL DEFAULT '2026-01-31',
            after_from TEXT NOT NULL DEFAULT '2026-06-01',
            after_to TEXT NOT NULL DEFAULT '2026-06-30',
            use_ai INTEGER NOT NULL DEFAULT 0,
            alert_webhook_url TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_polygons (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            geometry_json TEXT NOT NULL,
            label TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT REFERENCES portfolios(id),
            polygon_id TEXT REFERENCES portfolio_polygons(id),
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','completed','failed','abstained')),
            output_dir TEXT,
            findings_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES runs(id),
            finding_idx INTEGER NOT NULL,
            portfolio_id TEXT REFERENCES portfolios(id),
            state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','approved','rejected','uncertain')),
            reviewer_notes TEXT,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, finding_idx)
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash TEXT PRIMARY KEY,
            user_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            method TEXT NOT NULL,
            path TEXT NOT NULL,
            user_name TEXT,
            status_code INTEGER NOT NULL,
            duration_ms INTEGER NOT NULL
        );
        ",
    )?;

    // Safe schema migrations for existing databases
    let _ = conn.execute(
        "ALTER TABLE portfolios ADD COLUMN before_from TEXT NOT NULL DEFAULT '2026-01-01'",
        [],
    );
    let _ = conn.execute(
        "ALTER TABLE portfolios ADD COLUMN before_to TEXT NOT NULL DEFAULT '2026-01-31'",
        [],
    );
    let _ = conn.execute(
        "ALTER TABLE portfolios ADD COLUMN after_from TEXT NOT NULL DEFAULT '2026-06-01'",
        [],
    );
    let _ = conn.execute(
        "ALTER TABLE portfolios ADD COLUMN after_to TEXT NOT NULL DEFAULT '2026-06-30'",
        [],
    );
    let _ = conn.execute(
        "ALTER TABLE portfolios ADD COLUMN use_ai INTEGER NOT NULL DEFAULT 0",
        [],
    );

    Ok(())
}

// ---- Portfolio CRUD ----

use crate::models::Portfolio;

pub fn create_portfolio(db: &Db, p: &Portfolio) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT INTO portfolios (id, name, task, max_cloud_fraction, before_from, before_to, after_from, after_to, use_ai, alert_webhook_url, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        rusqlite::params![p.id, p.name, p.task, p.max_cloud_fraction, p.before_from, p.before_to, p.after_from, p.after_to, p.use_ai as i32, p.alert_webhook_url, p.created_at],
    )?;
    Ok(())
}

/// Update an existing portfolio's editable config (everything except id and
/// created_at). Returns false if no row matched the id.
pub fn update_portfolio(db: &Db, id: &str, p: &Portfolio) -> Result<bool> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let n = conn.execute(
        "UPDATE portfolios SET name = ?1, task = ?2, max_cloud_fraction = ?3, before_from = ?4, before_to = ?5, after_from = ?6, after_to = ?7, use_ai = ?8, alert_webhook_url = ?9 WHERE id = ?10",
        rusqlite::params![p.name, p.task, p.max_cloud_fraction, p.before_from, p.before_to, p.after_from, p.after_to, p.use_ai as i32, p.alert_webhook_url, id],
    )?;
    Ok(n > 0)
}

pub fn get_portfolio(db: &Db, id: &str) -> Result<Option<Portfolio>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT id, name, task, max_cloud_fraction, before_from, before_to, after_from, after_to, use_ai, alert_webhook_url, created_at FROM portfolios WHERE id = ?1",
    )?;
    let row = stmt.query_row(rusqlite::params![id], |row| {
        let use_ai_int: i32 = row.get(8)?;
        Ok(Portfolio {
            id: row.get(0)?,
            name: row.get(1)?,
            task: row.get(2)?,
            max_cloud_fraction: row.get(3)?,
            before_from: row.get(4)?,
            before_to: row.get(5)?,
            after_from: row.get(6)?,
            after_to: row.get(7)?,
            use_ai: use_ai_int != 0,
            alert_webhook_url: row.get(9)?,
            created_at: row.get(10)?,
        })
    });
    match row {
        Ok(p) => Ok(Some(p)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.into()),
    }
}

pub fn list_portfolios(db: &Db) -> Result<Vec<Portfolio>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT id, name, task, max_cloud_fraction, before_from, before_to, after_from, after_to, use_ai, alert_webhook_url, created_at FROM portfolios ORDER BY created_at DESC",
    )?;
    let items = stmt.query_map([], |row| {
        let use_ai_int: i32 = row.get(8)?;
        Ok(Portfolio {
            id: row.get(0)?,
            name: row.get(1)?,
            task: row.get(2)?,
            max_cloud_fraction: row.get(3)?,
            before_from: row.get(4)?,
            before_to: row.get(5)?,
            after_from: row.get(6)?,
            after_to: row.get(7)?,
            use_ai: use_ai_int != 0,
            alert_webhook_url: row.get(9)?,
            created_at: row.get(10)?,
        })
    })?;
    let mut out = Vec::new();
    for item in items {
        out.push(item?);
    }
    Ok(out)
}

pub fn delete_portfolio(db: &Db, id: &str) -> Result<bool> {
    let mut conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let tx = conn.transaction()?;
    tx.execute(
        "DELETE FROM reviews WHERE portfolio_id = ?1",
        rusqlite::params![id],
    )?;
    tx.execute(
        "DELETE FROM runs WHERE portfolio_id = ?1",
        rusqlite::params![id],
    )?;
    tx.execute(
        "DELETE FROM portfolio_polygons WHERE portfolio_id = ?1",
        rusqlite::params![id],
    )?;
    let n = tx.execute(
        "DELETE FROM portfolios WHERE id = ?1",
        rusqlite::params![id],
    )?;
    tx.commit()?;
    Ok(n > 0)
}

// ---- Polygon CRUD ----

use crate::models::Polygon;

pub fn add_polygon(db: &Db, poly: &Polygon) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT INTO portfolio_polygons (id, portfolio_id, geometry_json, label, created_at) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params![poly.id, poly.portfolio_id, poly.geometry_json, poly.label, poly.created_at],
    )?;
    Ok(())
}

pub fn list_polygons(db: &Db, portfolio_id: &str) -> Result<Vec<Polygon>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT id, portfolio_id, geometry_json, label, created_at FROM portfolio_polygons WHERE portfolio_id = ?1 ORDER BY created_at",
    )?;
    let items = stmt.query_map(rusqlite::params![portfolio_id], |row| {
        Ok(Polygon {
            id: row.get(0)?,
            portfolio_id: row.get(1)?,
            geometry_json: row.get(2)?,
            label: row.get(3)?,
            created_at: row.get(4)?,
        })
    })?;
    let mut out = Vec::new();
    for item in items {
        out.push(item?);
    }
    Ok(out)
}

pub fn delete_polygon(db: &Db, id: &str) -> Result<bool> {
    let mut conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let tx = conn.transaction()?;
    tx.execute(
        "DELETE FROM reviews WHERE run_id IN (SELECT id FROM runs WHERE polygon_id = ?1)",
        rusqlite::params![id],
    )?;
    tx.execute(
        "DELETE FROM runs WHERE polygon_id = ?1",
        rusqlite::params![id],
    )?;
    let n = tx.execute(
        "DELETE FROM portfolio_polygons WHERE id = ?1",
        rusqlite::params![id],
    )?;
    tx.commit()?;
    Ok(n > 0)
}

pub fn update_polygon(db: &Db, id: &str, geometry_json: &str, label: &str) -> Result<bool> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let n = conn.execute(
        "UPDATE portfolio_polygons SET geometry_json = ?1, label = ?2 WHERE id = ?3",
        rusqlite::params![geometry_json, label, id],
    )?;
    Ok(n > 0)
}

// ---- Run CRUD ----

use crate::models::Run;

pub fn create_run(db: &Db, r: &Run) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT INTO runs (id, portfolio_id, polygon_id, status, output_dir, findings_count, error_message, created_at, completed_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        rusqlite::params![r.id, r.portfolio_id, r.polygon_id, r.status, r.output_dir, r.findings_count, r.error_message, r.created_at, r.completed_at],
    )?;
    Ok(())
}

pub fn get_run(db: &Db, id: &str) -> Result<Option<Run>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT id, portfolio_id, polygon_id, status, output_dir, findings_count, error_message, created_at, completed_at FROM runs WHERE id = ?1",
    )?;
    let row = stmt.query_row(rusqlite::params![id], |row| {
        Ok(Run {
            id: row.get(0)?,
            portfolio_id: row.get(1)?,
            polygon_id: row.get(2)?,
            status: row.get(3)?,
            output_dir: row.get(4)?,
            findings_count: row.get(5)?,
            error_message: row.get(6)?,
            created_at: row.get(7)?,
            completed_at: row.get(8)?,
        })
    });
    match row {
        Ok(r) => Ok(Some(r)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.into()),
    }
}

pub fn update_run_output_dir(db: &Db, id: &str, output_dir: &str) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "UPDATE runs SET output_dir = ?1 WHERE id = ?2",
        rusqlite::params![output_dir, id],
    )?;
    Ok(())
}

pub fn update_run_status(
    db: &Db,
    id: &str,
    status: &str,
    findings_count: i64,
    error_message: Option<&str>,
    completed_at: Option<&str>,
) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "UPDATE runs SET status = ?1, findings_count = ?2, error_message = ?3, completed_at = ?4 WHERE id = ?5",
        rusqlite::params![status, findings_count, error_message, completed_at, id],
    )?;
    Ok(())
}

/// Mark any `pending`/`running` runs as failed. Job execution lives in
/// in-memory tokio tasks, so a process restart orphans those rows — they would
/// otherwise display "running" forever. Call once on startup. Returns the count.
pub fn reconcile_stale_runs(db: &Db, now: &str) -> Result<usize> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let n = conn.execute(
        "UPDATE runs SET status = 'failed', error_message = 'Interrupted by server restart', completed_at = ?1 WHERE status IN ('pending', 'running')",
        rusqlite::params![now],
    )?;
    Ok(n)
}

pub fn list_runs(db: &Db, portfolio_id: &str) -> Result<Vec<Run>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT id, portfolio_id, polygon_id, status, output_dir, findings_count, error_message, created_at, completed_at FROM runs WHERE portfolio_id = ?1 ORDER BY created_at DESC",
    )?;
    let items = stmt.query_map(rusqlite::params![portfolio_id], |row| {
        Ok(Run {
            id: row.get(0)?,
            portfolio_id: row.get(1)?,
            polygon_id: row.get(2)?,
            status: row.get(3)?,
            output_dir: row.get(4)?,
            findings_count: row.get(5)?,
            error_message: row.get(6)?,
            created_at: row.get(7)?,
            completed_at: row.get(8)?,
        })
    })?;
    let mut out = Vec::new();
    for item in items {
        out.push(item?);
    }
    Ok(out)
}

// ---- Review CRUD ----

use crate::models::Review;

pub fn create_review(db: &Db, r: &Review) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT OR REPLACE INTO reviews (id, run_id, finding_idx, portfolio_id, state, reviewer_notes, reviewed_at, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        rusqlite::params![r.id, r.run_id, r.finding_idx, r.portfolio_id, r.state, r.reviewer_notes, r.reviewed_at, r.created_at],
    )?;
    Ok(())
}

pub fn list_reviews(
    db: &Db,
    portfolio_id: &str,
    state_filter: Option<&str>,
) -> Result<Vec<Review>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = if let Some(sf) = state_filter {
        let mut rows = conn.prepare(
            "SELECT id, run_id, finding_idx, portfolio_id, state, reviewer_notes, reviewed_at, created_at FROM reviews WHERE portfolio_id = ?1 AND state = ?2 ORDER BY created_at DESC",
        )?;
        let items = rows.query_map(rusqlite::params![portfolio_id, sf], map_review)?;
        let mut out = Vec::new();
        for item in items {
            out.push(item?);
        }
        return Ok(out);
    } else {
        conn.prepare(
            "SELECT id, run_id, finding_idx, portfolio_id, state, reviewer_notes, reviewed_at, created_at FROM reviews WHERE portfolio_id = ?1 ORDER BY created_at DESC",
        )?
    };
    let items = stmt.query_map(rusqlite::params![portfolio_id], map_review)?;
    let mut out = Vec::new();
    for item in items {
        out.push(item?);
    }
    Ok(out)
}

fn map_review(row: &rusqlite::Row) -> rusqlite::Result<Review> {
    Ok(Review {
        id: row.get(0)?,
        run_id: row.get(1)?,
        finding_idx: row.get(2)?,
        portfolio_id: row.get(3)?,
        state: row.get(4)?,
        reviewer_notes: row.get(5)?,
        reviewed_at: row.get(6)?,
        created_at: row.get(7)?,
    })
}

// ---- API key operations ----

pub fn store_api_key(db: &Db, key_hash: &str, user_name: &str, created_at: &str) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT INTO api_keys (key_hash, user_name, created_at) VALUES (?1, ?2, ?3)",
        rusqlite::params![key_hash, user_name, created_at],
    )?;
    Ok(())
}

pub fn validate_api_key(db: &Db, key_hash: &str) -> Result<Option<String>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let row = conn.query_row(
        "SELECT user_name FROM api_keys WHERE key_hash = ?1",
        rusqlite::params![key_hash],
        |row| row.get::<_, String>(0),
    );
    match row {
        Ok(name) => {
            // Update last_used timestamp.
            let now = chrono::Utc::now().to_rfc3339();
            let _ = conn.execute(
                "UPDATE api_keys SET last_used = ?1 WHERE key_hash = ?2",
                rusqlite::params![now, key_hash],
            );
            Ok(Some(name))
        }
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e.into()),
    }
}

// ---- Audit log ----

use crate::models::AuditEntry;

pub fn insert_audit(db: &Db, entry: &AuditEntry) -> Result<()> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    conn.execute(
        "INSERT INTO audit_log (timestamp, method, path, user_name, status_code, duration_ms) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        rusqlite::params![entry.timestamp, entry.method, entry.path, entry.user_name, entry.status_code, entry.duration_ms],
    )?;
    Ok(())
}

pub fn list_audit(db: &Db, limit: i64) -> Result<Vec<AuditEntry>> {
    let conn = db.lock().map_err(|e| anyhow!("db lock: {e}"))?;
    let mut stmt = conn.prepare(
        "SELECT timestamp, method, path, user_name, status_code, duration_ms FROM audit_log ORDER BY id DESC LIMIT ?1",
    )?;
    let items = stmt.query_map(rusqlite::params![limit], |row| {
        Ok(AuditEntry {
            timestamp: row.get(0)?,
            method: row.get(1)?,
            path: row.get(2)?,
            user_name: row.get(3)?,
            status_code: row.get(4)?,
            duration_ms: row.get(5)?,
        })
    })?;
    let mut out = Vec::new();
    for item in items {
        out.push(item?);
    }
    Ok(out)
}
