//! Per-IP token-bucket rate limiting.
//!
//! Two buckets per client IP: a general request budget, and a much tighter
//! budget for `/run` (which spawns a subprocess per AOI — the expensive,
//! abusable path). In-process and dependency-free.
//!
//! ponytail: in-memory HashMap keyed by IP, opportunistically pruned. Fine for a
//! self-hosted control plane; swap for a shared store (Redis) only if you run
//! multiple replicas behind a load balancer.

use std::collections::HashMap;
use std::net::{IpAddr, Ipv4Addr, SocketAddr};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use axum::extract::{ConnectInfo, Request, State};
use axum::http::StatusCode;
use axum::middleware::Next;
use axum::response::{IntoResponse, Response};

use crate::routes::AppState;

/// Stop pruning the IP table from unbounded growth.
const MAX_TRACKED_IPS: usize = 10_000;
const PRUNE_AFTER: Duration = Duration::from_secs(600);

#[derive(Clone, Copy)]
struct Limit {
    capacity: f64,       // burst size
    refill_per_sec: f64, // sustained rate
}

struct Bucket {
    tokens: f64,
    last: Instant,
}

impl Bucket {
    fn new(cap: f64) -> Self {
        Bucket {
            tokens: cap,
            last: Instant::now(),
        }
    }

    /// Try to consume one token. Returns Err(retry_after) if empty.
    fn take(&mut self, limit: Limit, now: Instant) -> Result<(), Duration> {
        let elapsed = now.duration_since(self.last).as_secs_f64();
        self.tokens = (self.tokens + elapsed * limit.refill_per_sec).min(limit.capacity);
        self.last = now;
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            Ok(())
        } else {
            let needed = 1.0 - self.tokens;
            // Guard against a zero refill rate (would divide to infinity and
            // panic in Duration::from_secs_f64).
            let secs = if limit.refill_per_sec > 0.0 {
                (needed / limit.refill_per_sec).ceil()
            } else {
                60.0
            };
            Err(Duration::from_secs_f64(secs))
        }
    }
}

struct Entry {
    general: Bucket,
    run: Bucket,
    last_seen: Instant,
}

#[derive(Clone)]
pub struct RateLimiter {
    inner: Arc<Mutex<HashMap<IpAddr, Entry>>>,
    general: Limit,
    run: Limit,
}

impl Default for RateLimiter {
    fn default() -> Self {
        RateLimiter {
            inner: Arc::new(Mutex::new(HashMap::new())),
            // ~120 req/min burst, sustained 2/s.
            general: Limit {
                capacity: 120.0,
                refill_per_sec: 2.0,
            },
            // ~12 runs/min burst, sustained 0.2/s — runs are expensive.
            run: Limit {
                capacity: 12.0,
                refill_per_sec: 0.2,
            },
        }
    }
}

impl RateLimiter {
    /// Returns Ok or the suggested Retry-After duration.
    pub fn check(&self, ip: IpAddr, is_run: bool) -> Result<(), Duration> {
        let now = Instant::now();
        let mut map = self.inner.lock().unwrap_or_else(|e| e.into_inner());

        if map.len() > MAX_TRACKED_IPS {
            map.retain(|_, e| now.duration_since(e.last_seen) < PRUNE_AFTER);
        }

        let entry = map.entry(ip).or_insert_with(|| Entry {
            general: Bucket::new(self.general.capacity),
            run: Bucket::new(self.run.capacity),
            last_seen: now,
        });
        entry.last_seen = now;

        entry.general.take(self.general, now)?;
        if is_run {
            entry.run.take(self.run, now)?;
        }
        Ok(())
    }
}

/// Axum middleware. IP comes from ConnectInfo (or X-Forwarded-For if proxied).
pub async fn rate_limit(
    State(state): State<AppState>,
    req: Request,
    next: Next,
) -> Response {
    let ip = client_ip(&req);
    let is_run = req.uri().path().ends_with("/run") || req.uri().path() == "/v1/change";

    match state.rate_limiter.check(ip, is_run) {
        Ok(()) => next.run(req).await,
        Err(retry) => (
            StatusCode::TOO_MANY_REQUESTS,
            [("retry-after", retry.as_secs().max(1).to_string())],
            "Rate limit exceeded. Slow down and retry.",
        )
            .into_response(),
    }
}

fn client_ip(req: &Request) -> IpAddr {
    if let Some(fwd) = req
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.split(',').next())
        .and_then(|s| s.trim().parse::<IpAddr>().ok())
    {
        return fwd;
    }
    req.extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|ci| ci.0.ip())
        .unwrap_or(IpAddr::V4(Ipv4Addr::UNSPECIFIED))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn general_budget_exhausts_then_refills() {
        let rl = RateLimiter {
            inner: Arc::new(Mutex::new(HashMap::new())),
            general: Limit { capacity: 3.0, refill_per_sec: 100.0 },
            run: Limit { capacity: 100.0, refill_per_sec: 100.0 },
        };
        let ip = IpAddr::V4(Ipv4Addr::LOCALHOST);
        assert!(rl.check(ip, false).is_ok());
        assert!(rl.check(ip, false).is_ok());
        assert!(rl.check(ip, false).is_ok());
        assert!(rl.check(ip, false).is_err()); // 4th over a 3-burst
    }

    #[test]
    fn run_budget_is_separate_and_tighter() {
        let rl = RateLimiter {
            inner: Arc::new(Mutex::new(HashMap::new())),
            general: Limit { capacity: 1000.0, refill_per_sec: 1000.0 },
            run: Limit { capacity: 2.0, refill_per_sec: 0.0 },
        };
        let ip = IpAddr::V4(Ipv4Addr::LOCALHOST);
        assert!(rl.check(ip, true).is_ok());
        assert!(rl.check(ip, true).is_ok());
        assert!(rl.check(ip, true).is_err()); // run budget spent
        // non-run still fine (separate bucket)
        assert!(rl.check(ip, false).is_ok());
    }
}
