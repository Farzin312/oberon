mod routes;
mod middleware;

use anyhow::Result;
use clap::{Parser, Subcommand};
use oberon_control_plane::{config, db, telemetry};
use tower_http::trace::TraceLayer;
use tracing::info;

#[derive(Parser)]
#[command(name = "oberon", version, about = "Oberon control plane server")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the HTTP API server
    Serve {
        #[arg(long, default_value = "0.0.0.0:8000")]
        host: String,
    },
    /// API key management
    Auth {
        #[command(subcommand)]
        action: AuthAction,
    },
}

#[derive(Subcommand)]
enum AuthAction {
    /// Create a new API key
    CreateKey {
        #[arg(long)]
        user: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    telemetry::init();

    let cli = Cli::parse();
    let config = config::Config::default();

    match cli.command {
        Commands::Serve { host } => {
            let db = db::open(&config.db_path)?;

            info!(
                bind_addr = %host,
                db_path = %config.db_path.display(),
                auth_mode = if config.auth_disabled { "disabled" } else { "enabled" },
                python_path = %config.python_path,
                "startup"
            );

            let app = routes::build_app(
                db,
                config.auth_disabled,
                config.python_path.clone(),
                config.dashboard_dir.clone(),
            )
            .layer(TraceLayer::new_for_http());

            let addr = host
                .parse::<std::net::SocketAddr>()
                .unwrap_or("0.0.0.0:8000".parse().unwrap());
            let listener = tokio::net::TcpListener::bind(addr).await?;
            axum::serve(listener, app).await?;
        }
        Commands::Auth { action } => {
            let db = db::open(&config.db_path)?;
            match action {
                AuthAction::CreateKey { user } => {
                    let key = create_api_key(&db, &user)?;
                    println!("API key created for '{user}':");
                    println!("  {key}");
                    println!();
                    println!("Store this key securely. It will not be shown again.");
                    println!("Use it in the X-API-Key header for API requests.");
                }
            }
        }
    }

    Ok(())
}

fn create_api_key(db: &db::Db, user_name: &str) -> Result<String> {
    use sha2::{Digest, Sha256};

    // Generate a random key (oberon_<32 hex chars>).
    let raw = uuid::Uuid::new_v4().to_string();
    let key = format!("oberon_{}", &raw.replace('-', ""));
    let now = chrono::Utc::now().to_rfc3339();

    // Hash with SHA-256.
    let mut hasher = Sha256::new();
    hasher.update(key.as_bytes());
    let hash = hex::encode(hasher.finalize());

    db::store_api_key(db, &hash, user_name, &now)?;

    Ok(key)
}
