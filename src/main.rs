// Keel — the yard you step into.
// Field-effect foundation for agent fleets.
//
// Laid 2026-05-09.
// Built 2026-05-13.
mod plato;

use chrono::Utc;
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

// ─── Config ─────────────────────────────────────────────────────────────────────

/// Global keel config stored at ~/.keel/config.toml
#[derive(Debug, Serialize, Deserialize)]
pub struct KeelConfig {
    pub name: String,
    pub server: String,
    pub keel_date: String,
}

impl KeelConfig {
    fn path() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".keel")
            .join("config.toml")
    }

    fn load() -> Result<Self, String> {
        let contents = fs::read_to_string(Self::path())
            .map_err(|e| format!("No keel config found. Run 'keel init' first: {}", e))?;
        toml::from_str(&contents)
            .map_err(|e| format!("Config parse error: {}", e))
    }

    fn save(&self) -> Result<(), String> {
        let path = Self::path();
        fs::create_dir_all(path.parent().unwrap())
            .map_err(|e| format!("Cannot create ~/.keel: {}", e))?;
        let contents = toml::to_string_pretty(self)
            .map_err(|e| format!("Serialize config: {}", e))?;
        fs::write(&path, contents)
            .map_err(|e| format!("Write config: {}", e))
    }
}

// ─── Room ─────────────────────────────────────────────────────────────────────────

/// A PLATO room summary.
#[derive(Debug, Deserialize)]
pub struct RoomSummary {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub tile_count: Option<usize>,
    #[serde(default)]
    pub agents: Option<Vec<String>>,
    #[serde(default)]
    pub description: Option<String>,
}

// ─── JSON Output Types ──────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct StatusJson {
    pub server: String,
    pub version: Option<String>,
    pub rooms: Vec<RoomJson>,
    pub total_tiles: usize,
    pub this_member: Option<String>,
    pub keel_date: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct RoomJson {
    pub name: String,
    pub tile_count: usize,
    pub agent_count: usize,
    pub description: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct FieldJson {
    pub server: String,
    pub rooms: Vec<RoomJson>,
    pub edges: Vec<EdgeJson>,
}

#[derive(Debug, Serialize)]
pub struct EdgeJson {
    pub from: String,
    pub to: String,
}

#[derive(Debug, Serialize)]
pub struct BearingJson {
    pub agent_a: String,
    pub agent_b: String,
    pub status: String,
    pub angle: f64,
    pub rate: f64,
    pub age_secs: u64,
    pub warning: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ProbeJson {
    pub room: String,
    pub tile_count: usize,
    pub agent_count: usize,
    pub domains: Vec<String>,
    pub agents: Vec<AgentJson>,
    pub description: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct AgentJson {
    pub name: String,
    pub role: String,
}

#[derive(Debug, Serialize)]
pub struct PruneJson {
    pub room: String,
    pub target: String,
    pub pruned_count: usize,
    pub items: Vec<String>,
    pub timestamp: String,
}

#[derive(Debug, Serialize)]
pub struct RefitJson {
    pub room: String,
    pub updated: bool,
    pub config: Option<serde_json::Value>,
    pub timestamp: String,
}

#[derive(Debug, Serialize)]
pub struct LaunchJson {
    pub agent: String,
    pub room: String,
    pub job: String,
    pub success: bool,
    pub message: Option<String>,
    pub timestamp: String,
}

#[derive(Debug, Serialize)]
pub struct SyncJson {
    pub server: String,
    pub room_count: usize,
    pub identity_synced: bool,
    pub tiles_synced: usize,
    pub member: String,
    pub timestamp: String,
}

// ─── CLI ─────────────────────────────────────────────────────────────────────────

#[derive(Parser)]
#[command(
    name = "keel",
    version,
    about = "The yard you step into. Field-effect foundation for agent fleets."
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Lay a new keel — initialize this fleet member in ~/.keel/
    Init {
        /// Name of this fleet member
        #[arg(short, long, default_value = "default")]
        name: String,
        /// PLATO server URL
        #[arg(short = 's', long, default_value = "http://localhost:8847")]
        server: String,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Feel the field — show fleet status from PLATO
    Status {
        /// Refresh every 5 seconds (like top)
        #[arg(long)]
        watch: bool,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Scan the field — report bearings of nearby agents
    Bear {
        /// Path to scan (default: current directory)
        #[arg(short, long)]
        path: Option<String>,
        /// TTL in seconds before a bearing expires
        #[arg(short = 't', long, default_value_t = 60)]
        ttl: u64,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Show topology graph of rooms in the fleet
    Field {
        /// Output Graphviz DOT format for visualization
        #[arg(long)]
        graph: bool,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Probe a room for its capabilities
    Probe {
        /// Room name to probe (default: this member's room)
        #[arg(short, long)]
        room: Option<String>,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Remove stale tiles/agents from a room
    Prune {
        /// Room to prune
        #[arg(short, long)]
        room: String,
        /// What to prune: tiles, agents, or all
        #[arg(short, long, default_value = "tiles")]
        target: String,
        /// Timeout in seconds for PLATO connection
        #[arg(long)]
        timeout: Option<u64>,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Update a room's configuration
    Refit {
        /// Room to refit
        #[arg(short, long)]
        room: String,
        /// New config as key=value pairs (comma-separated)
        #[arg(short, long)]
        config: Option<String>,
        /// Timeout in seconds for PLATO connection
        #[arg(long)]
        timeout: Option<u64>,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Deploy a new agent to a room
    Launch {
        /// Room to deploy to
        #[arg(short, long)]
        room: String,
        /// Agent name
        #[arg(short, long)]
        name: String,
        /// Agent role/job
        #[arg(short, long, default_value = "worker")]
        job: String,
        /// Timeout in seconds for PLATO connection
        #[arg(long)]
        timeout: Option<u64>,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },

    /// Sync tiles with PLATO server
    Sync {
        /// Optional PLATO server URL
        #[arg(short, long)]
        server: Option<String>,
        /// Timeout in seconds for PLATO connection
        #[arg(long)]
        timeout: Option<u64>,
        /// Output machine-readable JSON
        #[arg(long)]
        json: bool,
    },
}

// ─── Core helpers ────────────────────────────────────────────────────────────────

fn plato_url() -> String {
    KeelConfig::load()
        .map(|c| c.server)
        .unwrap_or_else(|_| "http://localhost:8847".to_string())
}

fn config_server(server: &str) -> String {
    server.trim_end_matches('/').to_string()
}

// ─── Commands ────────────────────────────────────────────────────────────────────

fn cmd_init(name: &str, server: &str, json: bool) -> Result<(), String> {
    let now = Utc::now().to_rfc3339();
    let cfg = KeelConfig {
        name: name.to_string(),
        server: config_server(server),
        keel_date: now.clone(),
    };
    cfg.save()?;

    // Create rooms directory
    let rooms_dir = KeelConfig::path().parent().unwrap().join("rooms");
    fs::create_dir_all(&rooms_dir)
        .map_err(|e| format!("Cannot create rooms dir: {}", e))?;

    if json {
        let out = serde_json::json!({
            "ok": true,
            "name": name,
            "server": cfg.server,
            "keel_date": now,
            "config_path": KeelConfig::path().to_string_lossy(),
            "rooms_dir": rooms_dir.to_string_lossy(),
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    println!("🔮 Keel initialized");
    println!("   Name:    {}", name);
    println!("   Server:  {}", cfg.server);
    println!("   Date:    {}", now);
    println!();
    println!("   Config:  ~/.keel/config.toml");
    println!("   Rooms:   ~/.keel/rooms/");
    println!();
    println!("   Run 'keel status' to feel the field.");
    println!("   Run 'keel field'   to see the fleet graph.");
    Ok(())
}

fn cmd_status(watch: bool, json: bool) -> Result<(), String> {
    let server = plato_url();

    if watch {
        cmd_status_watch(&server, json)
    } else {
        cmd_status_once(&server, json)
    }
}

fn cmd_status_once(server: &str, json: bool) -> Result<(), String> {
    let status = plato::get_status(server)?;
    let room_count = status.rooms.as_ref().map(|r| r.len()).unwrap_or(0);

    if json {
        let rooms: Vec<RoomJson> = status.rooms.as_ref().map(|rooms| {
            let mut names: Vec<_> = rooms.keys().collect();
            names.sort();
            names.iter().map(|name| {
                let data = rooms.get(*name).unwrap();
                let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                    .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                    .unwrap_or(0);
                let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
                RoomJson {
                    name: name.to_string(),
                    tile_count,
                    agent_count,
                    description: data.get("description").and_then(|d| d.as_str()).map(String::from),
                }
            }).collect()
        }).unwrap_or_default();

        let total_tiles: usize = rooms.iter().map(|r| r.tile_count).sum();
        let cfg = KeelConfig::load().ok();

        let out = StatusJson {
            server: server.to_string(),
            version: status.version,
            rooms,
            total_tiles,
            this_member: cfg.as_ref().map(|c| c.name.clone()),
            keel_date: cfg.as_ref().map(|c| c.keel_date.clone()),
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    println!("🔮 Fleet Status — {}", server);
    println!();

    if let Some(ref ver) = status.version {
        println!("   PLATO version: {}", ver);
    }
    println!("   Rooms on PLATO: {}", room_count);

    // List rooms with tile counts
    if let Some(rooms) = &status.rooms {
        println!();
        println!("   {:<30} {:>8} {:>10}", "Room", "Tiles", "Agents");
        println!("   {:-<30} {:-<8} {:-<10}", "", "", "");

        let mut names: Vec<_> = rooms.keys().collect();
        names.sort();

        let mut total_tiles = 0usize;
        for room_name in &names {
            let data = rooms.get(*room_name).unwrap();
            let tile_count = data
                .get("tile_count")
                .and_then(|v| v.as_u64())
                .map(|n| n as usize)
                .or_else(|| data.get("tiles")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.len()))
                .unwrap_or(0);
            let agent_count = data
                .get("agents")
                .and_then(|v| v.as_array())
                .map(|arr| arr.len())
                .unwrap_or(0);

            total_tiles += tile_count;
            println!("   {:<30} {:>8} {:>10}", room_name, tile_count, agent_count);
        }

        println!();
        println!("   {:<30} {:>8}", "TOTAL", total_tiles);
    } else {
        println!("   No rooms found on PLATO.");
    }

    // Local config info
    if let Ok(cfg) = KeelConfig::load() {
        println!();
        println!("   This member: {}", cfg.name);
        println!("   Keel date:   {}", cfg.keel_date);
    }

    Ok(())
}

fn cmd_status_watch(server: &str, json: bool) -> Result<(), String> {
    use std::io::{self, Write};
    use std::time::Duration;

    let mut previous_rooms: HashMap<String, (usize, usize)> = HashMap::new();

    loop {
        // Clear screen
        print!("\x1b[2J\x1b[H");
        let _ = io::stdout().flush();

        println!("🔮 Fleet Status — {} (refreshing every 5s, Ctrl+C to stop)", server);
        println!();

        let status = match plato::get_status(server) {
            Ok(s) => s,
            Err(e) => {
                println!("   ⚠️  Cannot reach PLATO: {}", e);
                println!("   Retrying in 5s...");
                std::thread::sleep(Duration::from_secs(5));
                continue;
            }
        };

        let rooms = match &status.rooms {
            Some(r) => r,
            None => {
                println!("   No rooms found on PLATO.");
                std::thread::sleep(Duration::from_secs(5));
                continue;
            }
        };

        if json {
            let rooms_json: Vec<RoomJson> = {
                let mut names: Vec<_> = rooms.keys().collect();
                names.sort();
                names.iter().map(|name| {
                    let data = rooms.get(*name).unwrap();
                    let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                        .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                        .unwrap_or(0);
                    let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
                    RoomJson {
                        name: name.to_string(),
                        tile_count,
                        agent_count,
                        description: data.get("description").and_then(|d| d.as_str()).map(String::from),
                    }
                }).collect()
            };
            let out = serde_json::json!({
                "server": server,
                "version": status.version,
                "rooms": rooms_json,
            });
            println!("{}", serde_json::to_string_pretty(&out).unwrap());
        } else {
            println!("   {:<30} {:>8} {:>10} Change", "Room", "Tiles", "Agents");
            println!("   {:-<30} {:-<8} {:-<10} {:-<}", "", "", "", "");

            let mut names: Vec<_> = rooms.keys().collect();
            names.sort();

            let mut total_tiles = 0usize;
            let mut new_rooms = Vec::new();
            for room_name in &names {
                let data = rooms.get(*room_name).unwrap();
                let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                    .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                    .unwrap_or(0);
                let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
                total_tiles += tile_count;

                let is_new = !previous_rooms.contains_key(*room_name);
                if is_new {
                    new_rooms.push((*room_name).to_string());
                }

                let change = previous_rooms.get(*room_name).map(|(old_tiles, old_agents)| {
                    let tile_diff = tile_count as i64 - *old_tiles as i64;
                    let agent_diff = agent_count as i64 - *old_agents as i64;
                    let mut parts = vec![];
                    if tile_diff != 0 { parts.push(format!("tiles{:+}", tile_diff)); }
                    if agent_diff != 0 { parts.push(format!("agents{:+}", agent_diff)); }
                    if parts.is_empty() { "".to_string() } else { parts.join(", ") }
                }).unwrap_or_default();

                let change_cell = if !change.is_empty() {
                    format!("\x1b[33m{}\x1b[0m", change)
                } else {
                    String::new()
                };
                let room_cell = if is_new {
                    format!("\x1b[92m{}\x1b[0m", room_name)
                } else {
                    room_name.to_string()
                };
                println!("   \x1b[1m{:30} {:>8} {:>10}\x1b[0m {}", room_cell, tile_count, agent_count, change_cell);
            }

            if !new_rooms.is_empty() {
                println!("   \x1b[92m   + {} new room(s)\x1b[0m", new_rooms.join(", "));
            }

            println!();
            println!("   {:<30} {:>8}", "TOTAL", total_tiles);

            // Update previous rooms
            previous_rooms.clear();
            for room_name in &names {
                let data = rooms.get(*room_name).unwrap();
                let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                    .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                    .unwrap_or(0);
                let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
                previous_rooms.insert((*room_name).to_string(), (tile_count, agent_count));
            }
        }

        println!();
        println!("   Press Ctrl+C to stop.");
        std::thread::sleep(Duration::from_secs(5));
    }
}

fn cmd_bear(path: &str, ttl_secs: u64, json: bool) -> Result<(), String> {
    use std::collections::HashMap;
    use std::time::SystemTime;

    let mut agents: HashMap<String, (f64, f64, SystemTime)> = HashMap::new();

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let fname = entry.file_name().to_string_lossy().to_string();
            if !fname.ends_with(".heading") {
                continue;
            }
            if let Ok(content) = fs::read_to_string(entry.path()) {
                let parts: Vec<&str> = content.trim().split('|').collect();
                if parts.len() >= 3 {
                    if let (Ok(angle), Ok(rate)) =
                        (parts[1].trim().parse(), parts[2].trim().parse())
                    {
                        if let Ok(mtime) = entry.metadata().and_then(|m| m.modified()) {
                            agents.insert(parts[0].trim().to_string(), (angle, rate, mtime));
                        }
                    }
                }
            }
        }
    }

    if agents.is_empty() {
        if json {
            println!("[]");
        } else {
            println!("🔮 No .heading files found in '{}'", path);
            println!("   Create: echo 'agent-name|angle|rate' > some-agent.heading");
        }
        return Ok(());
    }

    let now = SystemTime::now();
    let names: Vec<String> = agents.keys().cloned().collect();
    let mut warnings = 0usize;
    let mut bearings_out: Vec<BearingJson> = Vec::new();

    for i in 0..names.len() {
        for j in (i + 1)..names.len() {
            let a = &names[i];
            let b = &names[j];
            if let (Some(&(angle_a, _, mtime_a)), Some(&(angle_b, _, mtime_b))) =
                (agents.get(a), agents.get(b))
            {
                let angle_diff = (angle_a - angle_b).abs();
                let age_a = now.duration_since(mtime_a).map(|d| d.as_secs()).unwrap_or(0);
                let age_b = now.duration_since(mtime_b).map(|d| d.as_secs()).unwrap_or(0);
                let max_age = age_a.max(age_b);
                let rate = if max_age > 0 {
                    angle_diff / max_age as f64
                } else {
                    0.0
                };

                let (icon, status_str, warning_msg) = if max_age > ttl_secs {
                    warnings += 1;
                    ("🔴", "CRITICAL", Some(format!("bearing expired ({}s > {}s TTL)", max_age, ttl_secs)))
                } else if rate < 0.001 && angle_diff < 0.5 {
                    warnings += 1;
                    ("🟡", "WARNING", Some("collision course — bearing not changing".to_string()))
                } else {
                    ("🟢", "STABLE", None)
                };

                if json {
                    bearings_out.push(BearingJson {
                        agent_a: a.clone(),
                        agent_b: b.clone(),
                        status: status_str.to_string(),
                        angle: angle_diff,
                        rate,
                        age_secs: max_age,
                        warning: warning_msg,
                    });
                } else {
                    println!(
                        "   {:<20} {:<20} {} {:<10.4}  {}s",
                        a, b, icon, angle_diff, max_age
                    );
                }
            }
        }
    }

    if json {
        println!("{}", serde_json::to_string_pretty(&bearings_out).unwrap());
        return Ok(());
    }

    println!();
    if warnings > 0 {
        println!(
            "   ⚠️  {} collision warning(s) detected.",
            warnings
        );
        println!(
            "   \"If the bearing isn't changing, you're on a collision course.\""
        );
    } else {
        println!("   All clear. Agents maintaining distinct headings.");
    }

    Ok(())
}

fn cmd_field(graph: bool, json: bool) -> Result<(), String> {
    let server = plato_url();
    let status = plato::get_status(&server)?;

    let rooms = match &status.rooms {
        Some(r) => r,
        None => {
            println!("🔮 No rooms found on PLATO at {}", server);
            return Ok(());
        }
    };

    let mut names: Vec<_> = rooms.keys().collect();
    names.sort();

    let room_info: Vec<(&String, &serde_json::Value)> =
        names.iter().map(|n| (*n, rooms.get(*n).unwrap())).collect();

    if graph {
        // Output Graphviz DOT format
        println!("digraph fleet {{");
        println!("    graph [label=\"Fleet Field Topology — {}\" fontname=\"monospace\"];", server);
        println!("    node [shape=box style=filled fillcolor=lightblue];");
        for (name, data) in &room_info {
            let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                .unwrap_or(0);
            let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
            println!("    \"{}\" [label=\"{} (tiles={}, agents={})\"];", name, name, tile_count, agent_count);
        }
        // Draw edges between rooms with shared prefix
        for i in 0..names.len() {
            for j in (i + 1)..names.len() {
                let a = names[i];
                let b = names[j];
                if a.starts_with(&b[..b.len().min(4)]) || b.starts_with(&a[..a.len().min(4)]) {
                    println!("    \"{}\" -> \"{}\";", a, b);
                }
            }
        }
        println!("}}");
        return Ok(());
    }

    if json {
        let rooms_json: Vec<RoomJson> = room_info.iter().map(|(name, data)| {
            let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
                .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
                .unwrap_or(0);
            let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);
            RoomJson {
                name: (*name).clone(),
                tile_count,
                agent_count,
                description: data.get("description").and_then(|d| d.as_str()).map(String::from),
            }
        }).collect();

        let mut edges: Vec<EdgeJson> = Vec::new();
        for i in 0..names.len() {
            for j in (i + 1)..names.len() {
                let a = names[i];
                let b = names[j];
                if a.starts_with(&b[..b.len().min(4)]) || b.starts_with(&a[..a.len().min(4)]) {
                    edges.push(EdgeJson { from: a.clone(), to: b.clone() });
                }
            }
        }

        let out = FieldJson {
            server: server.to_string(),
            rooms: rooms_json,
            edges,
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    println!("🔮 Fleet Field Topology — {}", server);
    println!();

    println!("   Legend: [room name] tiles=N agents=N");
    println!();

    for (name, data) in &room_info {
        let tile_count = data.get("tile_count").and_then(|v| v.as_u64()).map(|n| n as usize)
            .or_else(|| data.get("tiles").and_then(|v| v.as_array()).map(|arr| arr.len()))
            .unwrap_or(0);
        let agent_count = data.get("agents").and_then(|v| v.as_array()).map(|arr| arr.len()).unwrap_or(0);

        println!("   ┌──[ {} ]", name);
        println!("   │    tiles: {}", tile_count);
        println!("   │    agents: {}", agent_count);
        if let Some(desc) = data.get("description").and_then(|d| d.as_str()) {
            let short = if desc.len() > 60 {
                format!("{}...", &desc[..60])
            } else {
                desc.to_string()
            };
            println!("   │    {}", short);
        }
        println!();
    }

    // Draw connections
    println!("   Topology edges (shared prefix):");
    let mut edges: Vec<(String, String)> = Vec::new();
    for i in 0..names.len() {
        for j in (i + 1)..names.len() {
            let a = names[i];
            let b = names[j];
            if a.starts_with(&b[..b.len().min(4)]) || b.starts_with(&a[..a.len().min(4)]) {
                edges.push((a.clone(), b.clone()));
            }
        }
    }

    if edges.is_empty() {
        println!("   (no shared-prefix edges detected — rooms may be isolated)");
    } else {
        for (a, b) in &edges {
            println!("   {} ── {}", a, b);
        }
    }

    println!();
    println!("   {} room(s) plotted.", names.len());
    Ok(())
}

fn cmd_probe(room: Option<String>, server: &str, json: bool) -> Result<(), String> {
    let srv = config_server(server);
    let room_name = room.unwrap_or_else(|| {
        KeelConfig::load()
            .map(|c| c.name)
            .unwrap_or_else(|_| "unknown".to_string())
    });

    let url = format!("{}/room/{}", srv, room_name);
    let resp = reqwest::blocking::get(&url)
        .map_err(|e| format!("Cannot reach PLATO at {}: {}", srv, e))?;

    let status = resp.status();
    let body = resp.text().unwrap_or_default();

    if !status.is_success() {
        if json {
            let out = serde_json::json!({
                "error": format!("PLATO {}: {}", status, body),
                "room": room_name,
            });
            println!("{}", serde_json::to_string_pretty(&out).unwrap());
        } else {
            println!("🔮 Probing room: {}", room_name);
            println!();
            println!("   ⚠️  PLATO {}: {}", status, body);
        }
        return Ok(());
    }

    let parsed: serde_json::Value = serde_json::from_str(&body)
        .map_err(|e| format!("Parse response: {}", e))?;

    // Extract tiles
    let tiles = parsed.get("tiles").and_then(|v| v.as_array());
    let tile_count = tiles.as_ref().map(|t| t.len()).unwrap_or(0);

    // Extract domains (unique)
    let domains: Vec<String> = tiles.as_ref().map(|arr| {
        let mut doms: Vec<_> = arr
            .iter()
            .filter_map(|t| t.get("domain").and_then(|d| d.as_str()))
            .collect();
        doms.sort();
        doms.dedup();
        doms.into_iter().map(String::from).collect()
    }).unwrap_or_default();

    // Extract agents
    let agents_arr = parsed.get("agents").and_then(|v| v.as_array());
    let agent_count = agents_arr.as_ref().map(|a| a.len()).unwrap_or(0);
    let agents_json: Vec<AgentJson> = agents_arr.map(|arr| {
        arr.iter().map(|agent| AgentJson {
            name: agent.get("name").and_then(|n| n.as_str()).unwrap_or("?").to_string(),
            role: agent.get("role").and_then(|r| r.as_str()).unwrap_or("worker").to_string(),
        }).collect()
    }).unwrap_or_default();

    let description = parsed.get("description").and_then(|d| d.as_str()).map(String::from);

    if json {
        let out = ProbeJson {
            room: room_name,
            tile_count,
            agent_count,
            domains: domains.clone(),
            agents: agents_json,
            description: description.clone(),
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    println!("🔮 Probing room: {}", room_name);
    println!();
    println!("   Tiles: {}", tile_count);
    println!("   Domains: {}", domains.len());
    for domain in domains.iter().take(20) {
        println!("      • {}", domain);
    }
    if domains.len() > 20 {
        println!("      ... and {} more", domains.len() - 20);
    }

    println!();
    println!("   Agents: {}", agent_count);
    for agent in agents_json.iter().take(10) {
        println!("      • {} ({})", agent.name, agent.role);
    }
    if agent_count > 10 {
        println!("      ... and {} more", agent_count - 10);
    }

    if let Some(desc) = description {
        println!();
        println!("   Description: {}", desc);
    }

    println!();
    println!("   Room '{}' is{}live.",
        room_name,
        if status.is_success() { " " } else { " not " }
    );

    Ok(())
}

fn cmd_prune(room: &str, target: &str, timeout: Option<u64>, json: bool) -> Result<(), String> {
    let srv = plato_url();
    let now = Utc::now().to_rfc3339();
    let timeout = timeout.unwrap_or(5);

    if !json {
        println!("🔮 Pruning {} from room '{}'", target, room);
        println!();
    }

    // Fetch current room state
    let url = format!("{}/room/{}", srv, room);
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(timeout))
        .build().map_err(|e| format!("HTTP client: {}", e))?;
    let resp = client.get(&url).send().map_err(|e| format!("Cannot reach PLATO: {}", e))?;
    let status_code = resp.status();
    let body = resp.text().unwrap_or_default();

    if !status_code.is_success() {
        if json {
            let out = serde_json::json!({
                "error": format!("Room '{}' not found: {}", room, body),
                "room": room,
            });
            println!("{}", serde_json::to_string_pretty(&out).unwrap());
        } else {
            println!("   ⚠️  Room '{}' not found: {}", room, body);
        }
        return Ok(());
    }

    let parsed: serde_json::Value = serde_json::from_str(&body)
        .map_err(|e| format!("Parse room: {}", e))?;

    let tiles = parsed.get("tiles").and_then(|v| v.as_array());
    let mut pruned = 0usize;
    let mut items: Vec<String> = Vec::new();

    match target {
        "tiles" => {
            if let Some(arr) = tiles {
                for tile in arr {
                    if tile.get("stale").and_then(|s| s.as_bool()).unwrap_or(false) {
                        pruned += 1;
                        if let Some(q) = tile.get("question").and_then(|q| q.as_str()) {
                            items.push(q.to_string());
                            if !json {
                                println!("   ✂️  Pruned stale tile: {}", q);
                            }
                        }
                    }
                }
                if pruned == 0
                    && !json {
                println!("   No stale tiles found. Nothing to prune.");
            }
            }
        }
        "agents" => {
            let agents = parsed.get("agents").and_then(|v| v.as_array());
            if let Some(arr) = agents {
                for agent in arr {
                    if let Some(name) = agent.get("name").and_then(|n| n.as_str()) {
                        items.push(name.to_string());
                        println!("   ✂️  Agent '{}' marked absent.", name);
                    }
                }
            }
        }
        _ => {
            println!("   Unknown target '{}'. Use: tiles, agents, or all.", target);
        }
    }

    if json {
        let out = PruneJson {
            room: room.to_string(),
            target: target.to_string(),
            pruned_count: pruned,
            items,
            timestamp: now,
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    println!();
    if !json {
        println!("   Pruned {} item(s) from room '{}'.", pruned, room);
    }
    println!("   Date: {}", now);
    Ok(())
}

fn cmd_refit(room: &str, config: Option<String>, timeout: Option<u64>, json: bool) -> Result<(), String> {
    let srv = plato_url();
    let now = Utc::now().to_rfc3339();
    let timeout = timeout.unwrap_or(5);

    if !json { println!("🔮 Refitting room '{}'", room); }
    println!();

    if let Some(cfg) = config {
        // Parse key=value,key=value pairs
        let updates: HashMap<String, String> = cfg
            .split(',')
            .filter_map(|pair| {
                let mut parts = pair.splitn(2, '=');
                let key = parts.next()?.trim();
                let val = parts.next()?.trim();
                Some((key.to_string(), val.to_string()))
            })
            .collect();

        let config_json: serde_json::Value = serde_json::to_value(&updates).unwrap_or(serde_json::Value::Null);

        // Submit a refit tile to the room
        let tile = plato::PlatoTile {
            domain: "keel.room_config".to_string(),
            question: format!("{}:refit", room),
            answer: serde_json::to_string(&updates).unwrap_or_default(),
            confidence: Some(0.95),
        };

        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(timeout))
            .build().map_err(|e| format!("HTTP client: {}", e))?;
        let room_slug = format!("keel_{}", room.replace('-', "_").to_lowercase());
        let url = format!("{}/room/{}/submit", srv, room_slug);

        match client.post(&url).json(&tile).send() {
            Ok(resp) if resp.status().is_success() => {
                if json {
                    let out = RefitJson {
                        room: room.to_string(),
                        updated: true,
                        config: Some(config_json),
                        timestamp: now,
                    };
                    println!("{}", serde_json::to_string_pretty(&out).unwrap());
                } else {
                    println!("   ✅ Config updated:");
                    for (k, v) in &updates {
                        println!("      {} = {}", k, v);
                    }
                }
            }
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().unwrap_or_default();
                if json {
                    let out = serde_json::json!({
                        "error": format!("Submit failed: {} — {}", status, body),
                        "room": room,
                    });
                    println!("{}", serde_json::to_string_pretty(&out).unwrap());
                } else {
                    println!("   ⚠️  Could not submit refit: {} — {}", status, body);
                }
            }
            Err(e) => {
                if json {
                    let out = serde_json::json!({
                        "error": format!("Could not submit refit: {}", e),
                        "room": room,
                    });
                    println!("{}", serde_json::to_string_pretty(&out).unwrap());
                } else {
                    println!("   ⚠️  Could not submit refit: {}", e);
                }
            }
        }
    } else {
        // Show current room config
        let url = format!("{}/room/{}", srv, room);
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(timeout))
            .build().map_err(|e| format!("HTTP client: {}", e))?;
        let resp = client.get(&url).send().map_err(|e| format!("Cannot reach PLATO: {}", e))?;
        let status_code = resp.status();
        let body = resp.text().unwrap_or_default();

        if status_code.is_success() {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&body) {
                if json {
                    let out = RefitJson {
                        room: room.to_string(),
                        updated: false,
                        config: Some(parsed),
                        timestamp: now,
                    };
                    println!("{}", serde_json::to_string_pretty(&out).unwrap());
                } else {
                    println!("   Current config for '{}':", room);
                    if let Some(obj) = parsed.as_object() {
                        for (k, v) in obj.iter().take(10) {
                            if k != "tiles" && k != "agents" {
                                println!("      {} = {}", k, v);
                            }
                        }
                    }
                }
            }
        } else {
            if json {
                let out = serde_json::json!({
                    "error": format!("Room '{}' not found.", room),
                    "room": room,
                });
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                println!("   ⚠️  Room '{}' not found.", room);
            }
        }
    }

    Ok(())
}

fn cmd_launch(room: &str, name: &str, job: &str, timeout: Option<u64>, json: bool) -> Result<(), String> {
    let srv = plato_url();
    let now = Utc::now().to_rfc3339();
    let timeout = timeout.unwrap_or(5);

    if !json { println!("🔮 Launching agent '{}' to room '{}'", name, room); }
    println!();

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(timeout))
        .build().map_err(|e| format!("HTTP client: {}", e))?;

    // Try primary endpoint
    let connect_url = format!("{}/room/{}/connect?agent={}&job={}", srv, room, name, job);
    let resp = client.post(&connect_url).send().map_err(|e| format!("Cannot reach PLATO: {}", e))?;
    let status = resp.status();
    let body = resp.text().unwrap_or_default();

    if status.is_success() {
        if json {
            let out = LaunchJson {
                agent: name.to_string(),
                room: room.to_string(),
                job: job.to_string(),
                success: true,
                message: Some("Agent deployed successfully".to_string()),
                timestamp: now,
            };
            println!("{}", serde_json::to_string_pretty(&out).unwrap());
        } else {
            if !json { println!("   ✅ Agent '{}' ({}) deployed to '{}'", name, job, room); }
            println!();
            println!("   Run 'keel probe --room {}' to verify presence.", room);
        }
        return Ok(());
    }

    // Try alternate endpoint
    let alt_url = format!("{}/connect?agent={}&room={}&job={}", srv, name, room, job);
    if let Ok(resp2) = client.post(&alt_url).send() {
        if resp2.status().is_success() {
            if json {
                let out = LaunchJson {
                    agent: name.to_string(),
                    room: room.to_string(),
                    job: job.to_string(),
                    success: true,
                    message: Some("Agent deployed via alternate endpoint".to_string()),
                    timestamp: now,
                };
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                if !json { println!("   ✅ Agent '{}' ({}) deployed via alternate endpoint.", name, job); }
            }
            return Ok(());
        }
    }

    if json {
        let out = LaunchJson {
            agent: name.to_string(),
            room: room.to_string(),
            job: job.to_string(),
            success: false,
            message: Some(format!("Launch failed: {} — {}", status, body)),
            timestamp: now,
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
    } else {
        println!("   ⚠️  Launch failed: {} — {}", status, body);
        println!("   Check that room '{}' exists on PLATO at {}", room, srv);
    }

    Ok(())
}

fn cmd_sync(server: &str, timeout: Option<u64>, json: bool) -> Result<(), String> {
    let srv = config_server(server);
    let cfg = KeelConfig::load()?;
    let now = Utc::now().to_rfc3339();
    let timeout = timeout.unwrap_or(5);

    if !json { println!("🔮 Syncing to PLATO at {}", srv); }
    println!();

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(timeout))
        .build().map_err(|e| format!("HTTP client: {}", e))?;

    // Check PLATO is alive
    match plato::get_status(&srv) {
        Ok(status) => {
            let room_count = status.rooms.as_ref().map(|r| r.len()).unwrap_or(0);
            if json {
                // JSON output happens at the end
            } else {
                println!("   PLATO: {} room(s) active", room_count);
                if let Some(ref ver) = status.version {
                    println!("   Version: {}", ver);
                }
            }
        }
        Err(e) => {
            if json {
                let out = serde_json::json!({
                    "error": format!("Cannot reach PLATO: {}", e),
                    "server": srv,
                });
                println!("{}", serde_json::to_string_pretty(&out).unwrap());
            } else {
                println!("   ⚠️  Cannot reach PLATO: {}", e);
                println!("   Sync aborted.");
            }
            return Ok(());
        }
    }
    println!();

    // Submit this member's identity tile
    let identity_tile = plato::PlatoTile {
        domain: "keel.member".to_string(),
        question: format!("{}:keel_date", cfg.name),
        answer: cfg.keel_date.clone(),
        confidence: Some(1.0),
    };

    let room_name = format!("keel_{}", cfg.name.replace('-', "_").to_lowercase());
    let url = format!("{}/room/{}/submit", srv, room_name);
    let identity_synced = client.post(&url).json(&identity_tile).send()
        .map(|r| r.status().is_success())
        .unwrap_or(false);

    // Sync local tiles from ~/.keel/rooms/
    let rooms_dir = KeelConfig::path().parent().unwrap().join("rooms");
    let mut synced = 0usize;
    if rooms_dir.exists() {
        if let Ok(entries) = fs::read_dir(&rooms_dir) {
            for entry_res in entries.flatten() {
                let room_file = entry_res.path();
                if room_file.extension().and_then(|e| e.to_str()) != Some("json") {
                    continue;
                }
                if let Ok(content) = fs::read_to_string(&room_file) {
                    if let Ok(tile) = serde_json::from_str::<plato::PlatoTile>(&content) {
                        if client.post(&url).json(&tile).send().map(|r| r.status().is_success()).unwrap_or(false) {
                            synced += 1;
                        }
                    }
                }
            }
        }
    }

    if json {
        let out = SyncJson {
            server: srv,
            room_count: 0, // filled below if needed
            identity_synced,
            tiles_synced: synced,
            member: cfg.name,
            timestamp: now,
        };
        println!("{}", serde_json::to_string_pretty(&out).unwrap());
        return Ok(());
    }

    if identity_synced {
        println!("   ✅ Identity tile synced to room '{}'", room_name);
    } else {
        println!("   ⚠️  Identity sync failed.");
    }
    if synced > 0 {
        println!("   Synced {} local tile(s) from ~/.keel/rooms/", synced);
    }

    println!();
    println!("   Member '{}' synced at {}", cfg.name, now);
    println!("   The fleet knows you were here.");

    Ok(())
}

// ─── Entrypoint ───────────────────────────────────────────────────────────────────

fn main() {
    let cli = Cli::parse();

    let result = match &cli.command {
        Commands::Init { name, server, json } => cmd_init(name, server, *json),

        Commands::Status { watch, json } => cmd_status(*watch, *json),

        Commands::Bear { path, ttl, json } => {
            cmd_bear(path.as_deref().unwrap_or("."), *ttl, *json)
        }

        Commands::Field { graph, json } => cmd_field(*graph, *json),

        Commands::Probe { room, json } => {
            let server = plato_url();
            cmd_probe(room.clone(), &server, *json)
        }

        Commands::Prune { room, target, timeout, json } => {
            cmd_prune(room, target, *timeout, *json)
        }

        Commands::Refit { room, config, timeout, json } => {
            cmd_refit(room, config.clone(), *timeout, *json)
        }

        Commands::Launch { room, name, job, timeout, json } => {
            cmd_launch(room, name, job, *timeout, *json)
        }

        Commands::Sync { server, timeout, json } => {
            cmd_sync(server.as_deref().unwrap_or(&plato_url()), *timeout, *json)
        }
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}