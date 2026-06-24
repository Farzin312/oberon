//! Trust-boundary input validation for API requests. Keeps malformed or
//! abusive payloads (bad dates, out-of-range cloud, enormous polygons) out of
//! the job pipeline, where they would otherwise burn STAC/COG work or fail late.

use chrono::NaiveDate;
use serde_json::Value;

/// Hard cap on polygon vertices. A single AOI with millions of points would make
/// every windowed COG read pathological; real monitoring AOIs are far smaller.
pub const MAX_POLYGON_VERTICES: usize = 50_000;

/// Validate a portfolio's analysis window + cloud threshold.
pub fn validate_portfolio_config(
    before_from: &str,
    before_to: &str,
    after_from: &str,
    after_to: &str,
    max_cloud_fraction: f64,
) -> Result<(), String> {
    let bf = parse_date(before_from, "before_from")?;
    let bt = parse_date(before_to, "before_to")?;
    let af = parse_date(after_from, "after_from")?;
    let at = parse_date(after_to, "after_to")?;

    if bf > bt {
        return Err("before_from must be on or before before_to".into());
    }
    if af > at {
        return Err("after_from must be on or before after_to".into());
    }
    if bt > af {
        return Err("the before window must end on or before the after window begins".into());
    }
    if !(max_cloud_fraction > 0.0 && max_cloud_fraction <= 1.0) {
        return Err("max_cloud_fraction must be between 0 and 1 (exclusive of 0)".into());
    }
    Ok(())
}

fn parse_date(s: &str, field: &str) -> Result<NaiveDate, String> {
    NaiveDate::parse_from_str(s, "%Y-%m-%d")
        .map_err(|_| format!("{field} must be a YYYY-MM-DD date (got '{s}')"))
}

/// Validate an AOI geometry: GeoJSON Polygon/MultiPolygon, in-range coordinates,
/// and a bounded vertex count.
pub fn validate_geometry(geometry: &Value) -> Result<(), String> {
    let t = geometry
        .get("type")
        .and_then(|v| v.as_str())
        .ok_or("geometry must have a string 'type'")?;
    if t != "Polygon" && t != "MultiPolygon" {
        return Err(format!(
            "geometry type must be Polygon or MultiPolygon (got '{t}')"
        ));
    }
    let coords = geometry
        .get("coordinates")
        .ok_or("geometry must have 'coordinates'")?;

    let mut count = 0usize;
    walk_coords(coords, &mut count)?;
    if count == 0 {
        return Err("geometry has no coordinates".into());
    }
    Ok(())
}

/// Recursively walk nested coordinate arrays. A `[lon, lat]` pair (two leading
/// numbers) is a vertex; anything else is a container to descend into.
fn walk_coords(v: &Value, count: &mut usize) -> Result<(), String> {
    let arr = v.as_array().ok_or("coordinates must be arrays")?;
    if arr.len() >= 2 && arr[0].is_number() && arr[1].is_number() {
        let lon = arr[0].as_f64().unwrap_or(f64::NAN);
        let lat = arr[1].as_f64().unwrap_or(f64::NAN);
        if !(-180.0..=180.0).contains(&lon) || !(-90.0..=90.0).contains(&lat) {
            return Err(format!("coordinate out of range: [{lon}, {lat}]"));
        }
        *count += 1;
        if *count > MAX_POLYGON_VERTICES {
            return Err(format!(
                "geometry has too many vertices (> {MAX_POLYGON_VERTICES})"
            ));
        }
        return Ok(());
    }
    for item in arr {
        walk_coords(item, count)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn accepts_valid_config() {
        assert!(validate_portfolio_config(
            "2026-01-01", "2026-01-31", "2026-06-01", "2026-06-30", 0.3
        )
        .is_ok());
    }

    #[test]
    fn rejects_reversed_window() {
        assert!(validate_portfolio_config(
            "2026-02-01", "2026-01-01", "2026-06-01", "2026-06-30", 0.3
        )
        .is_err());
    }

    #[test]
    fn rejects_before_after_overlap() {
        // before window ends AFTER the after window begins
        assert!(validate_portfolio_config(
            "2026-01-01", "2026-07-01", "2026-06-01", "2026-06-30", 0.3
        )
        .is_err());
    }

    #[test]
    fn rejects_bad_cloud() {
        assert!(validate_portfolio_config("2026-01-01", "2026-01-31", "2026-06-01", "2026-06-30", 0.0).is_err());
        assert!(validate_portfolio_config("2026-01-01", "2026-01-31", "2026-06-01", "2026-06-30", 1.5).is_err());
    }

    #[test]
    fn rejects_bad_date() {
        assert!(validate_portfolio_config("not-a-date", "2026-01-31", "2026-06-01", "2026-06-30", 0.3).is_err());
    }

    #[test]
    fn accepts_valid_polygon() {
        let g = json!({"type":"Polygon","coordinates":[[[ -55.1,-7.4],[-55.0,-7.4],[-55.0,-7.3],[-55.1,-7.4]]]});
        assert!(validate_geometry(&g).is_ok());
    }

    #[test]
    fn rejects_wrong_type() {
        let g = json!({"type":"Point","coordinates":[-55.1,-7.4]});
        assert!(validate_geometry(&g).is_err());
    }

    #[test]
    fn rejects_out_of_range_coord() {
        let g = json!({"type":"Polygon","coordinates":[[[ -555.0,-7.4],[-55.0,-7.4],[-55.0,-7.3],[-555.0,-7.4]]]});
        assert!(validate_geometry(&g).is_err());
    }
}
