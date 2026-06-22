# Logging Standard

**Parent**: [README.md](../README.md)

Oberon has two runtimes (Python pipeline, Rust control plane) that share one
logging contract. This document is the authoritative spec — both sides follow it.

---

## Principles

1. **Fail fast, log the why.** Every error path logs the cause before returning.
   A user who sees "job failed" in the dashboard should find the reason in the
   server log without guessing.

2. **Structured fields, not interpolated strings.** All logs carry key=value
   fields (job_id, duration_ms, status, error). This makes logs greppable and
   machine-parseable. The message is a stable event name, not prose.

3. **No secrets in logs.** API keys (raw or hashed), geometry payloads, file
   contents, and reviewer notes are never logged. Log only identifiers
   (job_id, portfolio_id, user_name).

4. **Two formats, one env var.** `OBERON_LOG_FORMAT` controls both sides:
   - `console` (default): ANSI-colored, human-readable for terminal/CLI
   - `json`: single-line JSON for containers and log aggregation

5. **Quiet by default, loud on failure.** INFO logs startup and completions.
   WARN logs degraded states (STAC unreachable, retried requests). ERROR logs
   failures with full error chains. DEBUG is opt-in for pipeline internals.

---

## Event vocabulary

These event names appear in the `msg` / event field. Both sides use them.

| Event | Level | When | Fields |
|-------|-------|------|--------|
| `startup` | INFO | Server/CLI starts | bind_addr, db_path, auth_mode, python_path |
| `shutdown` | INFO | Server stops cleanly | |
| `request.start` | DEBUG | HTTP request received (tower-http) | method, path |
| `request.complete` | INFO | HTTP request completed (tower-http) | method, path, status, duration_ms |
| `auth.rejected` | WARN | API key missing or invalid | reason, path |
| `job.created` | INFO | Pipeline job created | job_id, portfolio_id |
| `job.started` | INFO | Python subprocess spawned | job_id, active_jobs, total_jobs |
| `job.completed` | INFO | Pipeline finished successfully | job_id, status, findings_count, duration_ms, output_mb, peak_rss_mb |
| `job.abstained` | INFO | Pipeline abstained (valid result) | job_id, duration_ms, output_mb, peak_rss_mb |
| `job.failed` | ERROR | Pipeline crashed or returned error | job_id, error, duration_ms |
| `db.error` | ERROR | SQLite operation failed | operation, error |
| `pipeline.spawn_error` | ERROR | Could not spawn Python subprocess | job_id, exit_code, error |

### Resource fields (logged at job completion)

Every `job.completed`, `job.abstained`, and `job.failed` event includes:

| Field | Description | Source |
|-------|-------------|--------|
| `duration_ms` | Wall-clock time from spawn to completion | `Instant::now()` delta |
| `output_mb` | Total size of the job output directory | `walk() + metadata().len()` |
| `peak_rss_mb` | Peak RSS of all child (Python) processes | `getrusage(RUSAGE_CHILDREN)` |
| `active_jobs` | How many jobs are running concurrently | `AtomicU64` counter |

The health endpoint (`GET /v1/health`) additionally returns system-level
resources for monitoring dashboards:

| Field | Description |
|-------|-------------|
| `mem_total_mb` | System total RAM |
| `mem_available_mb` | System available RAM |
| `disk_total_gb` | Disk total on the volume holding the DB/temp |
| `disk_free_gb` | Disk free on that volume |

---

## Python side

Location: `src/oberon/telemetry/logging.py`

Uses stdlib `logging` with `extra={}` for structured fields. Already wired into
all pipeline stages and CLI commands.

```python
from oberon.telemetry.logging import get_logger

logger = get_logger("oberon.analyze")
logger.info("job.started", extra={"job_id": "abc123"})
logger.error("pipeline.spawn_error", extra={"job_id": "abc123", "error": str(e)})
```

Third-party loggers (boto3, rasterio, GDAL) are suppressed to WARNING.

## Rust side

Location: `control-plane/src/telemetry.rs`

Uses `tracing` + `tracing-subscriber`. Initialized once at startup.

```rust
use tracing::{info, warn, error};

info!(job_id = %jid, "job.started");
error!(job_id = %jid, error = %e, "job.failed");
```

Verbosity via `RUST_LOG` (standard tracing convention):
- Default: `oberon_control_plane=info,tower_http=info`
- Debug: `RUST_LOG=debug`
- Trace everything: `RUST_LOG=trace`

`tower-http` TraceLayer provides automatic request/response logging with
method, path, status, and latency — no manual wiring needed per route.
