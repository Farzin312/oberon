use anyhow::Result;
use serde_json::json;

/// Deliver a webhook alert when a portfolio run produces material findings.
///
/// The payload contains the portfolio name, finding count, and a link to
/// the dashboard. Delivery is best-effort with one retry. Failures are
/// logged but never block the pipeline.
pub async fn send_alert(
    webhook_url: &str,
    portfolio_name: &str,
    job_id: &str,
    findings_count: usize,
) -> Result<()> {
    let payload = json!({
        "portfolio": portfolio_name,
        "job_id": job_id,
        "findings_count": findings_count,
        "dashboard_url": format!("/#/portfolio/{job_id}"),
        "message": format!(
            "{findings_count} new change finding(s) detected for portfolio '{portfolio_name}'"
        ),
    });

    // Best-effort delivery with one retry.
    for attempt in 0..2u8 {
        match try_post(webhook_url, &payload).await {
            Ok(_) => {
                tracing::info!(
                    webhook_url,
                    job_id,
                    findings_count,
                    attempt,
                    "alert.delivered"
                );
                return Ok(());
            }
            Err(e) if attempt == 0 => {
                tracing::warn!(webhook_url, error = %e, "alert.retry");
                tokio::time::sleep(std::time::Duration::from_secs(2)).await;
            }
            Err(e) => {
                tracing::error!(webhook_url, error = %e, "alert.delivery_failed");
                return Err(e);
            }
        }
    }
    Ok(())
}

async fn try_post(url: &str, payload: &serde_json::Value) -> Result<()> {
    let client = reqwest::Client::new();
    let resp = client
        .post(url)
        .header("content-type", "application/json")
        .json(payload)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await?;

    if !resp.status().is_success() {
        anyhow::bail!("webhook returned HTTP {}", resp.status());
    }
    Ok(())
}
