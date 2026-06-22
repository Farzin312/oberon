use std::env;
use std::path::PathBuf;

#[derive(Clone, Debug)]
pub struct Config {
    pub bind_addr: String,
    pub db_path: PathBuf,
    pub python_path: String,
    pub auth_disabled: bool,
    pub dashboard_dir: PathBuf,
}

impl Default for Config {
    fn default() -> Self {
        let db_path = env::var("OBERON_DB_PATH")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                dirs_home().join(".oberon").join("oberon.db")
            });

        let dashboard_dir = env::var("OBERON_DASHBOARD_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .parent()
                    .unwrap()
                    .join("dashboard")
            });

        Self {
            bind_addr: env::var("OBERON_BIND_ADDR").unwrap_or_else(|_| "0.0.0.0:8000".into()),
            db_path,
            python_path: env::var("OBERON_PYTHON_PATH").unwrap_or_else(|_| "python".into()),
            auth_disabled: env::var("OBERON_AUTH_DISABLED").as_deref() == Ok("1"),
            dashboard_dir,
        }
    }
}

fn dirs_home() -> PathBuf {
    env::var("HOME").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from("."))
}
