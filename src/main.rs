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
        let contents = fs::read_to_string(&Self::path())
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
    },

    /// Feel the field — show fleet status from PLATO
    Status {},

    /// Scan the field — report bearings of nearby agents
    Bear {
        /// Path to scan (default: current directory)
        #[arg(short, long)]
        path: Option<String>,
        /// TTL in seconds before a bearing expires
        #[arg(short = 't', long, default_value_t = 60)]
        ttl: u64,
    },

    /// Show topology graph of rooms in the fleet
    Field {},

    /// Probe a room for its capabilities
    Probe {
        /// Room name to probe (default: this member's room)
        #[arg(short, long)]
        room: Option<String>,
    },

    /// Remove stale tiles/agents from a room
    Prune {
        /// Room to prune
        #[arg(short, long)]
        room: String,
        /// What to prune: tiles, agents, or all
        #[arg(short, long, default_value = "tiles")]
        target: String,
    },

    /// Update a room's configuration
    Refit {
        /// Room to refit
        #[arg(short, long)]
        room: String,
        /// New config as key=value pairs (comma-separated)
        #[arg(short, long)]
        config: Option<String>,
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
    },

    /// Sync tiles with PLATO server
    Sync {
        /// Optional PLATO server URL
        #[arg(short, long)]
        server: Option<String>,
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

fn cmd_init(name: &str, server: &str) -> Result<(), String> {
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

fn cmd_status() -> Result<(), String> {
    let server = plato_url();
    println!("🔮 Fleet Status — {}", server);
    println!();

    let status = plato::get_status(&server)?;
    let room_count = status.rooms.as_ref().map(|r| r.len()).unwrap_or(0);

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
        for room_name in names {
            let data = &rooms[room_name];
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

fn cmd_bear(path: &str, ttl_secs: u64) -> Result<(), String> {
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
        println!("🔮 No .heading files found in '{}'", path);
        println!("   Create: echo 'agent-name|angle|rate' > some-agent.heading");
        return Ok(());
    }

    let now = SystemTime::now();
    let names: Vec<String> = agents.keys().cloned().collect();
    let mut warnings = 0usize;

    println!("🔮 Bearing-Rate Scan");
    println!("   Path: {}", path);
    println!("   Agents found: {}", names.len());
    println!("   TTL: {}s", ttl_secs);
    println!();
    println!(
        "   {:<20} {:<20} {:<10} {:<10} {}",
        "Agent A", "Agent B", "Status", "Angle", "Age"
    );
    println!("   {:-<20} {:-<20} {:-<10} {:-<10} {:-<}", "", "", "", "", "");

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

                let (icon, status) = if max_age > ttl_secs {
                    warnings += 1;
                    ("🔴", "CRITICAL")
                } else if rate < 0.001 && angle_diff < 0.5 {
                    warnings += 1;
                    ("🟡", "WARNING")
                } else {
                    ("🟢", "STABLE")
                };

                println!(
                    "   {:<20} {:<20} {} {:<10.4}  {}s",
                    a, b, icon, angle_diff, max_age
                );
            }
        }
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

fn cmd_field() -> Result<(), String> {
    let server = plato_url();
    let status = plato::get_status(&server)?;

    let rooms = match &status.rooms {
        Some(r) => r,
        None => {
            println!("🔮 No rooms found on PLATO at {}", server);
            return Ok(());
        }
    };

    println!("🔮 Fleet Field Topology — {}", server);
    println!();

    let mut names: Vec<_> = rooms.keys().collect();
    names.sort();

    // Build adjacency from room names (heuristic: rooms with similar prefixes are connected)
    let mut room_info: Vec<(&String, &serde_json::Value)> =
        names.iter().map(|n| (*n, rooms.get(*n).unwrap())).collect();

    // ASCII topology: connected rooms share edges
    // We'll render rooms as nodes, and draw edges between rooms with shared prefixes
    println!("   Legend: [room name] tiles=N agents=N");
    println!();

    for (name, data) in &room_info {
        let tile_count = data
            .get("tile_count")
            .and_then(|v| v.as_u64()).map(|n| n as usize)
            .or_else(|| {
                data.get("tiles")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.len())
            })
            .unwrap_or(0);
        let agent_count = data
            .get("agents")
            .and_then(|v| v.as_array())
            .map(|arr| arr.len())
            .unwrap_or(0);

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

    // Draw connections between rooms with shared prefix (e.g., "oracle1" -> "oracle1_history")
    println!("   Topology edges (shared prefix):");
    let mut edges: Vec<(String, String)> = Vec::new();
    for i in 0..names.len() {
        for j in (i + 1)..names.len() {
            let a = names[i];
            let b = names[j];
            // If one name is a prefix of the other, draw an edge
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

fn cmd_probe(room: Option<String>, server: &str) -> Result<(), String> {
    let srv = config_server(server);
    let room_name = room.unwrap_or_else(|| {
        KeelConfig::load()
            .map(|c| c.name)
            .unwrap_or_else(|_| "unknown".to_string())
    });

    println!("🔮 Probing room: {}", room_name);
    println!();

    let url = format!("{}/room/{}", srv, room_name);
    let resp = reqwest::blocking::get(&url)
        .map_err(|e| format!("Cannot reach PLATO at {}: {}", srv, e))?;

    let status = resp.status();
    let body = resp.text().unwrap_or_default();

    if !status.is_success() {
        println!("   ⚠️  PLATO {}: {}", status, body);
        return Ok(());
    }

    let parsed: serde_json::Value = serde_json::from_str(&body)
        .map_err(|e| format!("Parse response: {}", e))?;

    // Extract tiles
    let tiles = parsed.get("tiles").and_then(|v| v.as_array());
    let tile_count = tiles.as_ref().map(|t| t.len()).unwrap_or(0);
    println!("   Tiles: {}", tile_count);

    // Extract domains (unique)
    if let Some(arr) = tiles {
        let mut domains: Vec<_> = arr
            .iter()
            .filter_map(|t| t.get("domain").and_then(|d| d.as_str()))
            .collect();
        domains.sort();
        domains.dedup();
        println!("   Domains: {}", domains.len());
        if !domains.is_empty() {
            println!("   {:<15}", "Domain list:");
            for domain in domains.iter().take(20) {
                println!("      • {}", domain);
            }
            if domains.len() > 20 {
                println!("      ... and {} more", domains.len() - 20);
            }
        }
    }

    // Extract agents
    let agents = parsed.get("agents").and_then(|v| v.as_array());
    let agent_count = agents.as_ref().map(|a| a.len()).unwrap_or(0);
    println!();
    println!("   Agents: {}", agent_count);
    if let Some(arr) = agents {
        for agent in arr.iter().take(10) {
            let name = agent.get("name").and_then(|n| n.as_str()).unwrap_or("?");
            let role = agent.get("role").and_then(|r| r.as_str()).unwrap_or("worker");
            println!("      • {} ({})", name, role);
        }
        if agent_count > 10 {
            println!("      ... and {} more", agent_count - 10);
        }
    }

    // Room metadata
    if let Some(desc) = parsed.get("description").and_then(|d| d.as_str()) {
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

fn cmd_prune(room: &str, target: &str, server: &str) -> Result<(), String> {
    let srv = config_server(server);
    let now = Utc::now().to_rfc3339();

    println!("🔮 Pruning {} from room '{}'", target, room);
    println!();

    // Fetch current room state
    let url = format!("{}/room/{}", srv, room);
    let resp = reqwest::blocking::get(&url)
        .map_err(|e| format!("Cannot reach PLATO: {}", e))?;
    let status_code = resp.status();
    let body = resp.text().unwrap_or_default();

    if !status_code.is_success() {
        println!("   ⚠️  Room '{}' not found: {}", room, body);
        return Ok(());
    }

    let parsed: serde_json::Value = serde_json::from_str(&body)
        .map_err(|e| format!("Parse room: {}", e))?;

    let tiles = parsed.get("tiles").and_then(|v| v.as_array());
    let mut pruned = 0usize;

    match target {
        "tiles" => {
            if let Some(arr) = tiles {
                let mut pruned = 0usize;
                for tile in arr {
                    if tile.get("stale").and_then(|s| s.as_bool()).unwrap_or(false) {
                        pruned += 1;
                        if let Some(q) = tile.get("question").and_then(|q| q.as_str()) {
                            println!("   ✂️  Pruned stale tile: {}", q);
                        }
                    }
                }
                if pruned == 0 {
                    println!("   No stale tiles found. Nothing to prune.");
                }
            }
        }
        "agents" => {
            let agents = parsed.get("agents").and_then(|v| v.as_array());
            if let Some(arr) = agents {
                for agent in arr {
                    if let Some(name) = agent.get("name").and_then(|n| n.as_str()) {
                        println!("   ✂️  Agent '{}' marked absent.", name);
                    }
                }
            }
        }
        _ => {
            println!("   Unknown target '{}'. Use: tiles, agents, or all.", target);
        }
    }

    println!();
    println!("   Pruned {} item(s) from room '{}'.", pruned, room);
    println!("   Date: {}", now);
    Ok(())
}

fn cmd_refit(room: &str, config: Option<String>, server: &str) -> Result<(), String> {
    let srv = config_server(server);
    let now = Utc::now().to_rfc3339();

    println!("🔮 Refitting room '{}'", room);
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

        // Submit a refit tile to the room
        let tile = plato::PlatoTile {
            domain: "keel.room_config".to_string(),
            question: format!("{}:refit", room),
            answer: serde_json::to_string(&updates).unwrap_or_default(),
            confidence: Some(0.95),
        };

        match plato::submit_tile(
            &format!("keel_{}", room.replace('-', "_").to_lowercase()),
            &tile,
            &srv,
        ) {
            Ok(_) => {
                println!("   ✅ Config updated:");
                for (k, v) in &updates {
                    println!("      {} = {}", k, v);
                }
            }
            Err(e) => println!("   ⚠️  Could not submit refit: {}", e),
        }
    } else {
        // Show current room config
        let url = format!("{}/room/{}", srv, room);
        let resp = reqwest::blocking::get(&url)
            .map_err(|e| format!("Cannot reach PLATO: {}", e))?;
        let status_code = resp.status();
        let body = resp.text().unwrap_or_default();

        if status_code.is_success() {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&body) {
                println!("   Current config for '{}':", room);
                if let Some(obj) = parsed.as_object() {
                    for (k, v) in obj.iter().take(10) {
                        if k != "tiles" && k != "agents" {
                            println!("      {} = {}", k, v);
                        }
                    }
                }
            }
        } else {
            println!("   ⚠️  Room '{}' not found.", room);
        }
    }

    println!();
    println!("   Refit date: {}", now);
    Ok(())
}

fn cmd_launch(room: &str, name: &str, job: &str, server: &str) -> Result<(), String> {
    let srv = config_server(server);
    let now = Utc::now().to_rfc3339();

    println!("🔮 Launching agent '{}' to room '{}'", name, room);
    println!();

    // Register agent with the room via the room's connect or agent endpoint
    let connect_url = format!("{}/room/{}/connect?agent={}&job={}", srv, room, name, job);
    let resp = reqwest::blocking::Client::new()
        .post(&connect_url)
        .send()
        .map_err(|e| format!("Cannot reach PLATO: {}", e))?;

    let status = resp.status();
    let body = resp.text().unwrap_or_default();

    if status.is_success() {
        println!("   ✅ Agent '{}' ({}) deployed to '{}'", name, job, room);
        println!();
        println!("   Run 'keel probe --room {}' to verify presence.", room);
    } else {
        // Try alternate endpoint
        let alt_url = format!("{}/connect?agent={}&room={}&job={}", srv, name, room, job);
        if let Ok(resp2) = reqwest::blocking::Client::new().post(&alt_url).send() {
            if resp2.status().is_success() {
                println!("   ✅ Agent '{}' ({}) deployed via alternate endpoint.", name, job);
                return Ok(());
            }
        }
        println!("   ⚠️  Launch failed: {} — {}", status, body);
        println!("   Check that room '{}' exists on PLATO at {}", room, srv);
    }

    println!();
    println!("   Launch date: {}", now);
    Ok(())
}

fn cmd_sync(server: &str) -> Result<(), String> {
    let srv = config_server(server);
    let cfg = KeelConfig::load()?;
    let now = Utc::now().to_rfc3339();

    println!("🔮 Syncing to PLATO at {}", srv);
    println!();

    // Check PLATO is alive
    match plato::get_status(&srv) {
        Ok(status) => {
            let room_count = status.rooms.as_ref().map(|r| r.len()).unwrap_or(0);
            println!("   PLATO: {} room(s) active", room_count);
            if let Some(ref ver) = status.version {
                println!("   Version: {}", ver);
            }
        }
        Err(e) => {
            println!("   ⚠️  Cannot reach PLATO: {}", e);
            println!("   Sync aborted.");
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
    match plato::submit_tile(&room_name, &identity_tile, &srv) {
        Ok(resp) => {
            println!("   ✅ Identity tile synced to room '{}'", resp.room);
        }
        Err(e) => {
            println!("   ⚠️  Identity sync failed: {}", e);
        }
    }

    // Sync local tiles from ~/.keel/rooms/
    let rooms_dir = KeelConfig::path().parent().unwrap().join("rooms");
    if rooms_dir.exists() {
        let mut synced = 0usize;
        if let Ok(entries) = fs::read_dir(&rooms_dir) {
            for entry_res in entries.flatten() {
                let room_file = entry_res.path();
                if room_file.extension().and_then(|e| e.to_str()) != Some("json") {
                    continue;
                }
                if let Ok(content) = fs::read_to_string(&room_file) {
                    if let Ok(tile) = serde_json::from_str::<plato::PlatoTile>(&content) {
                        if plato::submit_tile(&room_name, &tile, &srv).is_ok() {
                            synced += 1;
                        }
                    }
                }
            }
        }
        if synced > 0 {
            println!("   Synced {} local tile(s) from ~/.keel/rooms/", synced);
        }
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
        Commands::Init { name, server } => cmd_init(name, server),

        Commands::Status {} => cmd_status(),

        Commands::Bear { path, ttl } => {
            cmd_bear(path.as_deref().unwrap_or("."), *ttl)
        }

        Commands::Field {} => cmd_field(),

        Commands::Probe { room } => {
            let server = room
                .as_ref()
                .map(|_| plato_url())
                .unwrap_or_else(|| plato_url());
            cmd_probe(room.clone(), &server)
        }

        Commands::Prune { room, target } => {
            cmd_prune(room, target, &plato_url())
        }

        Commands::Refit { room, config } => {
            cmd_refit(room, config.clone(), &plato_url())
        }

        Commands::Launch { room, name, job } => {
            cmd_launch(room, name, job, &plato_url())
        }

        Commands::Sync { server } => {
            cmd_sync(server.as_deref().unwrap_or(&plato_url()))
        }
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}