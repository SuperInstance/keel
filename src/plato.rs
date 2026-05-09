//! PLATO bridge for Keel CLI.
//!
//! Syncs build records to PLATO rooms, reads fleet knowledge,
//! and provides bearing-rate data from the fleet's memory server.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
pub struct PlatoTile {
    pub domain: String,
    pub question: String,
    pub answer: String,
    pub confidence: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct PlatoRoom {
    pub tiles: Vec<PlatoTile>,
    pub tile_count: Option<usize>,
}

#[derive(Debug, Deserialize)]
pub struct PlatoSubmitResponse {
    pub status: String,
    pub room: String,
    pub tile_hash: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct PlatoStatus {
    pub status: Option<String>,
    pub rooms: Option<HashMap<String, serde_json::Value>>,
    pub gate_stats: Option<serde_json::Value>,
    pub version: Option<String>,
}

/// Default PLATO server URL
const PLATO_URL: &str = "http://localhost:8847";

/// Submit a tile to a PLATO room.
pub fn submit_tile(room: &str, tile: &PlatoTile, server: &str) -> Result<PlatoSubmitResponse, String> {
    let url = format!("{}/room/{}/submit", server.trim_end_matches('/'), room);
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build().map_err(|e| format!("HTTP client: {}", e))?;
    let resp = client.post(&url)
        .json(tile)
        .send().map_err(|e| format!("PLATO connection: {}", e))?;
    let status = resp.status();
    let body = resp.text().unwrap_or_default();
    if !status.is_success() {
        return Err(format!("PLATO {}: {}", status, body));
    }
    serde_json::from_str(&body).map_err(|e| format!("PLATO parse: {}", e))
}

/// Fetch all tiles from a PLATO room.
pub fn get_room(room: &str, server: &str) -> Result<PlatoRoom, String> {
    let url = format!("{}/room/{}", server.trim_end_matches('/'), room);
    let resp = reqwest::blocking::get(&url)
        .map_err(|e| format!("PLATO connection: {}", e))?;
    let status = resp.status();
    let body = resp.text().unwrap_or_default();
    if !status.is_success() {
        return Err(format!("PLATO {}: {}", status, body));
    }
    serde_json::from_str(&body).map_err(|e| format!("PLATO parse: {}", e))
}

/// Get server status.
pub fn get_status(server: &str) -> Result<PlatoStatus, String> {
    let url = format!("{}/status", server.trim_end_matches('/'));
    let resp = reqwest::blocking::get(&url)
        .map_err(|e| format!("PLATO connection: {}", e))?;
    resp.json().map_err(|e| format!("PLATO parse: {}", e))
}

/// Sync the local build record to a PLATO room.
/// Creates one tile per refit entry.
pub fn sync_build_record(project_name: &str, refits_dir: &std::path::Path, server: &str) -> Result<usize, String> {
    let room_name = format!("keel_{}", project_name.replace('-', "_").to_lowercase());
    let mut synced = 0usize;

    if !refits_dir.exists() {
        return Err(format!("No refits directory at {}", refits_dir.display()));
    }

    for entry in std::fs::read_dir(refits_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        let content = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
        let filename = path.file_stem().and_then(|s| s.to_str()).unwrap_or("refit");

        let tile = PlatoTile {
            domain: "keel.refit".to_string(),
            question: format!("{}:{}", project_name, filename),
            answer: content,
            confidence: Some(0.95),
        };

        match submit_tile(&room_name, &tile, server) {
            Ok(_) => synced += 1,
            Err(e) => eprintln!("  ⚠️  Could not sync {}: {}", filename, e),
        }
    }

    Ok(synced)
}

/// Fetch bearing observations from a PLATO room.
/// Each tile with domain "bearing" is parsed.
pub fn fetch_bearings(room: &str, server: &str) -> Result<Vec<BearingObs>, String> {
    let room_data = get_room(room, server)?;
    let mut bearings = Vec::new();

    for tile in &room_data.tiles {
        if tile.domain == "bearing" {
            // Answer format: "agent_a|agent_b|angle|rate"
            let parts: Vec<&str> = tile.answer.split('|').collect();
            if parts.len() >= 4 {
                if let (Ok(angle), Ok(rate)) = (parts[2].parse::<f64>(), parts[3].parse::<f64>()) {
                    bearings.push(BearingObs {
                        agent_a: parts[0].to_string(),
                        agent_b: parts[1].to_string(),
                        angle,
                        rate,
                        source: tile.question.clone(),
                    });
                }
            }
        }
    }
    Ok(bearings)
}

#[derive(Debug, Clone)]
pub struct BearingObs {
    pub agent_a: String,
    pub agent_b: String,
    pub angle: f64,
    pub rate: f64,
    pub source: String,
}

pub fn collision_risk(angle: f64, rate: f64) -> &'static str {
    if rate.abs() < 0.01 && angle.abs() < 1.0 {
        "COLLISION"
    } else {
        "STABLE"
    }
}
