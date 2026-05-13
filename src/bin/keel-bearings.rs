//! Bearing-Rate Collision Detector
//!
//! Reads agent headings from shared state (PLATO rooms or workspace files),
//! computes bearing rates between pairs, flags collision courses.
//!
//! "If the bearing isn't changing, you're on a collision course."
//! No central scheduler. No direct messages. The field communicates.

use std::collections::HashMap;
use std::fs;

/// A simplified bearing observation between two agents.
struct Bearing {
    agent_a: String,
    agent_b: String,
    /// Angular difference between heading vectors (radians, 0 = same heading)
    angle: f64,
    /// Current rate of change of the angle (radians/sec)
    rate: f64,
    /// Seconds since this bearing was observed
    age_secs: u64,
}

#[derive(Debug)]
enum Risk {
    Stable,
    Warning(String),
    Critical(String),
}

/// Collision risk assessment:
/// - Constant angle + near-zero rate + age under threshold = collision warning
/// - Age over threshold = stale bearing = critical (position unknown)
/// - Changing angle = stable (course is diverging or converging safely)
fn assess(angle: f64, rate: f64, age_secs: u64, ttl_secs: u64) -> Risk {
    if age_secs > ttl_secs {
        return Risk::Critical(format!(
            "bearing expired ({}s > {}s TTL) — position unknown",
            age_secs, ttl_secs
        ));
    }
    let rate_abs = rate.abs();
    if rate_abs < 0.01 && angle.abs() < 1.0 {
        return Risk::Warning(format!(
            "collision course — bearing not changing (angle={:.3}, rate={:.5})",
            angle, rate
        ));
    }
    Risk::Stable
}

/// Scan a directory for agent heading files and compute all pairwise bearings.
fn scan_directory(path: &str) -> Vec<Bearing> {
    let mut agents: HashMap<String, (String, f64, std::time::SystemTime)> = HashMap::new();

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let fname = entry.file_name().to_string_lossy().to_string();
            if !fname.ends_with(".heading") {
                continue;
            }
            // Format: agent-name.heading containing "heading|angle|rate"
            if let Ok(content) = fs::read_to_string(entry.path()) {
                let parts: Vec<&str> = content.trim().split('|').collect();
                if parts.len() >= 3 {
                    if let (Ok(angle), Ok(_rate)) = (parts[1].parse::<f64>(), parts[2].parse::<f64>()) {
                        let mtime = entry.metadata().ok()
                            .and_then(|m| m.modified().ok())
                            .unwrap_or(std::time::SystemTime::UNIX_EPOCH);
                        let name = fname.trim_end_matches(".heading").to_string();
                        agents.insert(name, (parts[0].to_string(), angle, mtime));
                    }
                }
            }
        }
    }

    let now = std::time::SystemTime::now();
    let mut bearings = Vec::new();
    let names: Vec<String> = agents.keys().cloned().collect();

    for i in 0..names.len() {
        for j in (i + 1)..names.len() {
            let a = &names[i];
            let b = &names[j];
            if let (Some((_, angle_a, mtime_a)), Some((_, angle_b, mtime_b))) =
                (agents.get(a), agents.get(b))
            {
                let angle_diff = (angle_a - angle_b).abs();
                let age_a = now.duration_since(*mtime_a).map(|d| d.as_secs()).unwrap_or(0);
                let age_b = now.duration_since(*mtime_b).map(|d| d.as_secs()).unwrap_or(0);
                let max_age = age_a.max(age_b);
                // Rate is estimated from the mtime age — older observations have lower rates
                let rate = if max_age > 0 { angle_diff / max_age as f64 } else { 0.0 };

                bearings.push(Bearing {
                    agent_a: a.clone(),
                    agent_b: b.clone(),
                    angle: angle_diff,
                    rate,
                    age_secs: max_age,
                });
            }
        }
    }
    bearings
}

fn main() {
    // Default: scan the current directory for .heading files
    let scan_path = std::env::args().nth(1).unwrap_or_else(|| ".".to_string());
    let ttl_secs: u64 = std::env::args().nth(2)
        .and_then(|s| s.parse().ok())
        .unwrap_or(60); // default TTL: 60 seconds

    let bearings = scan_directory(&scan_path);
    if bearings.is_empty() {
        println!("No agent heading files found in '{}'", scan_path);
        println!("Create .heading files: echo 'researching|0.5|0.01' > agent1.heading");
        return;
    }

    println!("🔮 Bearing-Rate Scan — {} agents, {} pairs", bearings.len() + 1, bearings.len());
    println!("   TTL: {}s", ttl_secs);
    println!();

    for b in &bearings {
        let risk = assess(b.angle, b.rate, b.age_secs, ttl_secs);
        let icon = match risk {
            Risk::Critical(_) => "🔴",
            Risk::Warning(_) => "🟡",
            Risk::Stable => "🟢",
        };
        let msg = match risk {
            Risk::Critical(ref m) | Risk::Warning(ref m) => m.clone(),
            Risk::Stable => format!("stable (angle={:.3}, rate={:.6})", b.angle, b.rate),
        };
        println!("   {} {} ↔ {}: {}", icon, b.agent_a, b.agent_b, msg);
    }
}
