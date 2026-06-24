use std::env;
use std::path::PathBuf;

#[derive(Clone, Debug)]
pub struct Config {
    pub bind_addr: String,
    pub db_path: PathBuf,
    pub python_path: String,
    pub auth_disabled: bool,
    pub dashboard_dir: PathBuf,
    pub output_dir: PathBuf,
    /// Max analysis subprocesses allowed to run at once; excess jobs queue.
    pub max_concurrent_runs: usize,
    /// Cross-origin origin to allow (e.g. https://app.example.com). When unset,
    /// cross-origin browser calls are refused; the same-origin dashboard is
    /// unaffected (CORS does not apply to same-origin requests).
    pub cors_allow_origin: Option<String>,
}

impl Default for Config {
    fn default() -> Self {
        let db_path = env::var("OBERON_DB_PATH")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs_home().join(".oberon").join("oberon.db"));

        let dashboard_dir = env::var("OBERON_DASHBOARD_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .parent()
                    .unwrap()
                    .join("dashboard")
            });

        let output_dir = env::var("OBERON_OUTPUT_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs_home().join(".oberon").join("output"));

        Self {
            bind_addr: env::var("OBERON_BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8000".into()),
            db_path,
            python_path: env::var("OBERON_PYTHON_PATH").unwrap_or_else(|_| "python".into()),
            auth_disabled: env::var("OBERON_AUTH_DISABLED").as_deref() == Ok("1"),
            dashboard_dir,
            output_dir,
            max_concurrent_runs: env::var("OBERON_MAX_CONCURRENT_RUNS")
                .ok()
                .and_then(|v| v.parse::<usize>().ok())
                .filter(|n| *n >= 1)
                .unwrap_or(2),
            cors_allow_origin: env::var("OBERON_CORS_ALLOW_ORIGIN")
                .ok()
                .filter(|s| !s.is_empty()),
        }
    }
}

fn dirs_home() -> PathBuf {
    env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}
