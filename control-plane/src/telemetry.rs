use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;
use std::env;
use tracing_subscriber::fmt;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

// ---------------------------------------------------------------------------
// Logging initialization
// ---------------------------------------------------------------------------

/// Initialize structured logging. Call once at startup.
///
/// Format is controlled by OBERON_LOG_FORMAT, matching the Python pipeline:
///   - "console" (default): ANSI-colored human-readable for local dev/CLI
///   - "json": single-line JSON records for containers/log aggregation
///
/// Verbosity via RUST_LOG (standard tracing convention):
///   - Default: "oberon_control_plane=info,tower_http=info"
///   - Set RUST_LOG=debug for pipeline internals
///   - Set RUST_LOG=trace for everything
///
/// See docs/LOGGING_STANDARD.md for the full event vocabulary.
///
/// Security: never log API keys (raw or hashed), full request bodies,
/// or geometry payloads. Log only method, path, status, duration.
pub fn init() {
    let fmt_env = env::var("OBERON_LOG_FORMAT").unwrap_or_else(|_| "console".into());
    let default_filter = "oberon_control_plane=info,tower_http=info";

    let filter = tracing_subscriber::EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new(default_filter));

    match fmt_env.as_str() {
        "json" => {
            tracing_subscriber::registry()
                .with(filter)
                .with(fmt::layer().json())
                .init();
        }
        _ => {
            tracing_subscriber::registry()
                .with(filter)
                .with(fmt::layer().with_target(true).with_ansi(true))
                .init();
        }
    }
}

// ---------------------------------------------------------------------------
// Resource tracking
// ---------------------------------------------------------------------------

/// Tracks active background jobs to prevent runaway concurrency.
/// Cloned into AppState, shared across all handlers.
#[derive(Clone)]
pub struct JobMetrics {
    active: std::sync::Arc<AtomicU64>,
    total: std::sync::Arc<AtomicU64>,
}

impl Default for JobMetrics {
    fn default() -> Self {
        Self {
            active: std::sync::Arc::new(AtomicU64::new(0)),
            total: std::sync::Arc::new(AtomicU64::new(0)),
        }
    }
}

impl JobMetrics {
    /// Call when a pipeline job starts. Returns a guard that decrements on drop.
    pub fn start(&self) -> JobGuard {
        let active = self.active.fetch_add(1, Ordering::Relaxed) + 1;
        let total = self.total.fetch_add(1, Ordering::Relaxed) + 1;
        tracing::info!(active_jobs = active, total_jobs = total, "job.started");
        JobGuard {
            counter: self.active.clone(),
        }
    }

    pub fn active_count(&self) -> u64 {
        self.active.load(Ordering::Relaxed)
    }

    pub fn total_count(&self) -> u64 {
        self.total.load(Ordering::Relaxed)
    }
}

/// RAII guard that decrements the active job count when dropped.
pub struct JobGuard {
    counter: std::sync::Arc<AtomicU64>,
}

impl Drop for JobGuard {
    fn drop(&mut self) {
        self.counter.fetch_sub(1, Ordering::Relaxed);
    }
}

/// Snapshot of system resources at a point in time.
#[derive(Debug)]
pub struct ResourceSnapshot {
    pub mem_total_mb: u64,
    pub mem_available_mb: u64,
    pub disk_total_gb: f64,
    pub disk_free_gb: f64,
}

/// Read current system memory + disk space on the volume holding `path`.
pub fn snapshot_resources(path: &std::path::Path) -> ResourceSnapshot {
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();

    let mem_total_mb = sys.total_memory() / 1024 / 1024;
    let mem_available_mb = sys.available_memory() / 1024 / 1024;

    // Disk: use statvfs on Unix, fall back to 0 on others.
    let (disk_total_gb, disk_free_gb) = disk_space(path);

    ResourceSnapshot {
        mem_total_mb,
        mem_available_mb,
        disk_total_gb,
        disk_free_gb,
    }
}

#[cfg(unix)]
fn disk_space(path: &std::path::Path) -> (f64, f64) {
    use std::ffi::CString;
    let c_path = match path.to_str().and_then(|s| CString::new(s).ok()) {
        Some(p) => p,
        None => return (0.0, 0.0),
    };
    // SAFETY: statvfs is a standard POSIX call. c_path is a valid C string.
    let mut statv: libc::statvfs = unsafe { std::mem::zeroed() };
    let rc = unsafe { libc::statvfs(c_path.as_ptr(), &mut statv) };
    if rc != 0 {
        return (0.0, 0.0);
    }
    let block_size = statv.f_bsize as f64;
    let total = statv.f_blocks as f64 * block_size / 1e9;
    let free = statv.f_bavail as f64 * block_size / 1e9;
    (total, free)
}

#[cfg(not(unix))]
fn disk_space(_path: &std::path::Path) -> (f64, f64) {
    (0.0, 0.0)
}

/// Calculate total size of a directory in MB.
pub fn dir_size_mb(path: &std::path::Path) -> f64 {
    fn walk(p: &std::path::Path) -> u64 {
        let mut total = 0;
        if let Ok(entries) = std::fs::read_dir(p) {
            for entry in entries.flatten() {
                let ft = match entry.file_type() {
                    Ok(ft) => ft,
                    Err(_) => continue,
                };
                if ft.is_file() {
                    total += entry.metadata().map(|m| m.len()).unwrap_or(0);
                } else if ft.is_dir() {
                    total += walk(&entry.path());
                }
            }
        }
        total
    }
    walk(path) as f64 / 1e6
}

/// Get peak RSS of child processes via getrusage (Unix only).
pub fn child_peak_rss_mb() -> u64 {
    #[cfg(unix)]
    {
        // SAFETY: getrusage with RUSAGE_CHILDREN is a standard POSIX call.
        let mut usage: libc::rusage = unsafe { std::mem::zeroed() };
        let rc = unsafe { libc::getrusage(libc::RUSAGE_CHILDREN, &mut usage) };
        if rc == 0 {
            // ru_maxrss is in KB on Linux, bytes on macOS.
            #[cfg(target_os = "linux")]
            { return usage.ru_maxrss as u64 / 1024; }
            #[cfg(not(target_os = "linux"))]
            { return usage.ru_maxrss as u64 / 1024 / 1024; }
        }
        0
    }
    #[cfg(not(unix))]
    { 0 }
}

/// Timing helper for instrumenting pipeline jobs with wall-clock duration.
pub struct Timer {
    start: Instant,
}

impl Timer {
    pub fn start() -> Self {
        Self { start: Instant::now() }
    }

    pub fn elapsed_ms(&self) -> u128 {
        self.start.elapsed().as_millis()
    }
}
