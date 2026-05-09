// Keel — the yard you step into.
// Field-effect foundation for agent fleets.
//
// Laid 2026-05-09.
mod plato;
// "Constraints breed clarity."

use chrono::Utc;
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::fs;

use std::path::{Path, PathBuf};
use std::process::Command;

// ─── Data structures ───────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
struct KeelManifest {
    keel: KeelMeta,
    field: FieldDecl,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct KeelMeta {
    name: String,
    keel_date: String,
    heading: String,
    refits: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct FieldDecl {
    center: String,
    specialists: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct AgentArchetype {
    name: String,
    role: String,
    keel_date: String,
    heading: String,
    capabilities: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct RefitEntry {
    date: String,
    component: String,
    reason: String,
    pruned: Vec<String>,
}

// ─── CLI ───────────────────────────────────────────────────────────────────────────

#[derive(Parser)]
#[command(name = "keel", version, about = "The yard you step into. Field-effect foundation for agent fleets.")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Lay a new keel — start a project with a birthday
    Init {
        /// Name of your vessel (project)
        name: String,
        /// Optional heading (what you're making way toward)
        #[arg(short = 'd', long, default_value = "discovery")]
        heading: String,
        /// Comma-separated specialist archetypes to include
        #[arg(short, long, default_value = "shipwright,lookout,engineer,purser,signalman")]
        specialists: String,
    },
    /// Feel the field — show keel date, heading, agents, refits
    Status {},
    /// Remove what you don't need — prune a component with reason
    Prune {
        /// What to prune (agent name, file path, etc.)
        target: String,
        /// Why you're pruning it
        reason: String,
    },
    /// Replate a component — record a refit in the build record
    Refit {
        /// What component changed
        component: String,
        /// What changed and why
        reason: String,
    },
    /// Splash — mark your vessel as launched
    Launch {
        /// Optional message for the launch record
        #[arg(short, long)]
        message: Option<String>,
    },
    /// Probe hardware — discover the constraints of your physical environment
    Probe {},
    /// Scan bearing rates between agents — detect collision courses
    Bear {
        /// Path to scan for .heading files (default: current dir)
        path: Option<String>,
        /// TTL in seconds before a bearing expires
        #[arg(short = 't', long, default_value_t = 60)]
        ttl: u64,
    },
    /// Sync build record to PLATO — share with the fleet
    Sync {
        /// Optional PLATO server URL
        #[arg(short, long)]
        server: Option<String>,
    },
}

// ─── Core logic ────────────────────────────────────────────────────────────────────

fn find_keel_dir() -> Option<PathBuf> {
    let mut cwd = std::env::current_dir().ok()?;
    loop {
        let keel_path = cwd.join(".keel");
        if keel_path.join("keel.toml").exists() {
            return Some(keel_path);
        }
        if !cwd.pop() {
            return None;
        }
    }
}

fn load_manifest(keel_dir: &Path) -> Result<KeelManifest, String> {
    let path = keel_dir.join("keel.toml");
    let contents = fs::read_to_string(&path)
        .map_err(|e| format!("Cannot read {}: {}", path.display(), e))?;
    toml::from_str(&contents)
        .map_err(|e| format!("Cannot parse keel manifest: {}", e))
}

fn save_manifest(keel_dir: &Path, manifest: &KeelManifest) -> Result<(), String> {
    let path = keel_dir.join("keel.toml");
    let contents = toml::to_string_pretty(manifest)
        .map_err(|e| format!("Cannot serialize manifest: {}", e))?;
    fs::write(&path, contents)
        .map_err(|e| format!("Cannot write {}: {}", path.display(), e))
}

fn cmd_init(name: &str, heading: &str, specialists: &str) -> Result<(), String> {
    let target = PathBuf::from(name);
    if target.exists() {
        return Err(format!("'{}' already exists. Keel can only be laid on new ground.", name));
    }

    let now = Utc::now().to_rfc3339();
    let specialist_list: Vec<String> = specialists
        .split(',')
        .map(|s| s.trim().to_lowercase())
        .collect();

    // Create directory structure
    let keel_dir = target.join(".keel");
    let agents_dir = target.join("agents");
    let memory_dir = target.join("memory");
    let refits_dir = target.join("refits");

    fs::create_dir_all(&keel_dir)
        .map_err(|e| format!("Cannot create {}: {}", keel_dir.display(), e))?;
    fs::create_dir_all(&agents_dir)
        .map_err(|e| format!("Cannot create {}: {}", agents_dir.display(), e))?;
    fs::create_dir_all(&memory_dir)
        .map_err(|e| format!("Cannot create {}: {}", memory_dir.display(), e))?;
    fs::create_dir_all(&refits_dir)
        .map_err(|e| format!("Cannot create {}: {}", refits_dir.display(), e))?;

    // Write keel manifest
    let manifest = KeelManifest {
        keel: KeelMeta {
            name: name.to_string(),
            keel_date: now.clone(),
            heading: heading.to_string(),
            refits: 0,
        },
        field: FieldDecl {
            center: "self".to_string(),
            specialists: specialist_list.clone(),
        },
    };
    save_manifest(&keel_dir, &manifest)?;

    // Write field declaration
    let field_toml_path = target.join("field.toml");
    let field_contents = format!(
        r#"# Your field declaration.
# This is not a configuration file — it's a presence declaration.
# Everything in this project orients toward the center.

[keel]
name = "{}"
keel_date = "{}"
heading = "{}"

[field]
center = "self"
specialists = [{}]

# No rules. No plugins. No dependencies.
# Just orientation.
"#,
        name,
        now,
        heading,
        specialist_list
            .iter()
            .map(|s| format!("\"{}\"", s))
            .collect::<Vec<_>>()
            .join(", "),
    );
    fs::write(&field_toml_path, &field_contents)
        .map_err(|e| format!("Cannot write field.toml: {}", e))?;

    // Write agent archetype stubs
    let archetypes: Vec<(&str, &str, Vec<&str>)> = vec![
        ("shipwright", "Builds and implements. Gives form to the idea.", 
         vec!["code", "implementation", "architecture", "testing"]),
        ("lookout", "Researches and monitors. Scans the horizon for what matters.",
         vec!["research", "analysis", "monitoring", "alerts"]),
        ("engineer", "Runs the infrastructure. Keeps the yard's equipment running.",
         vec!["ops", "infrastructure", "deployment", "reliability"]),
        ("purser", "Tends the memory. Preserves what the fleet learns.",
         vec!["knowledge", "memory", "plato", "archival"]),
        ("signalman", "Coordinates between agents. Watches bearing rates.",
         vec!["communication", "coordination", "protocol", "routing"]),
    ];

    for (name, role, capabilities) in &archetypes {
        if !specialist_list.contains(&name.to_string()) {
            continue;
        }
        let agent_toml = format!(
            r#"name = "{}"
role = "{}"
keel_date = "{}"
heading = "standby"

capabilities = [{}]

# Prune what doesn't fit. Refit as you grow.
# This agent was born the same day as the keel. It will learn its boat.
"#,
            name,
            role,
            now,
            capabilities
                .iter()
                .map(|c| format!("\"{}\"", c))
                .collect::<Vec<_>>()
                .join(", "),
        );

        let agent_dir = agents_dir.join(name);
        fs::create_dir_all(&agent_dir)
            .map_err(|e| format!("Cannot create {}: {}", agent_dir.display(), e))?;
        fs::write(agent_dir.join("agent.toml"), &agent_toml)
            .map_err(|e| format!("Cannot write agent.toml: {}", e))?;

        // Write a brief README for each agent
        let readme = format!(
            "# {}\n\n{}\n\nCapabilities: {}\n\nKeel date: {}\n\n*\"Know why you question, and the answer becomes less important on the big things.*\n",
            name,
            role,
            capabilities.join(", "),
            now,
        );
        fs::write(agent_dir.join("README.md"), &readme).ok();
    }

    // Write memory README
    let memory_readme = r#"# Memory

This is where the fleet's build record lives. Every decision, every prune, every refit.

Connect to a PLATO room server to persist memory across agent restarts and session boundaries.

```bash
# Seed the PLATO room for this project
curl -X POST http://localhost:8847/room/keel-$PROJECT/submit \
  -H "Content-Type: application/json" \
  -d '{"domain":"keel","question":"keel_date","answer":"'"$(cat .keel/keel.toml | grep keel_date)"'","confidence":1.0}'
```

The boat is the motion the idea causes in the intelligence of those who know what it means.
Everything else is just steel catching up.
"#;
    fs::write(memory_dir.join("README.md"), memory_readme)
        .map_err(|e| format!("Cannot write memory README: {}", e))?;

    // Write refits README
    let refits_readme = r#"# Refits

Every time you replate a component, record it here.

```json
{
  "date": "2026-05-09",
  "component": "engine",
  "reason": "Repowered with more torque",
  "pruned": ["old_engine_config.json"]
}
```

The keel date doesn't change. The boat is still the same boat.
"#;
    fs::write(refits_dir.join("README.md"), refits_readme)
        .map_err(|e| format!("Cannot write refits README: {}", e))?;

    // Write .gitignore
    let gitignore = "# Keel ignores nothing. Every prune, every refit, every decision is part of the build record.\n# But compiled artifacts don't need to commit.\ntarget/\n";
    fs::write(target.join(".gitignore"), gitignore)
        .map_err(|e| format!("Cannot write .gitignore: {}", e))?;

    println!("🔮 Keel laid: {} ({} UTC)", name, now);
    println!("   Heading: {}", heading);
    println!("   Specialists: {}", specialist_list.join(", "));
    println!("   Birthday: {}", now);
    println!();
    println!("   The keel is the first structural element laid.");
    println!("   Everything after is just steel catching up.");
    println!();
    println!("   → cd {}/", name);
    println!("   → keel status    (feel the field)");
    println!("   → keel prune     (cut away what isn't your boat)");
    println!("   → keel refit     (record a change)");
    println!("   → keel launch    (splash when ready)");

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

fn cmd_status() -> Result<(), String> {
    let keel_dir = find_keel_dir()
        .ok_or_else(|| "No keel found. Are you in a keel workspace?".to_string())?;
    let manifest = load_manifest(&keel_dir)?;

    let keel_date = &manifest.keel.keel_date;
    let _now = Utc::now().to_rfc3339();

    println!("🔮 Keel Status");
    println!("   Vessel:    {}", manifest.keel.name);
    println!("   Birthday:  {}", keel_date);
    println!("   Heading:   {}", manifest.keel.heading);
    println!("   Refits:    {}", manifest.keel.refits);
    println!("   Field:     {} agents", manifest.field.specialists.len());
    println!();

    // List agents
    let agents_dir = keel_dir.parent().unwrap().join("agents");
    if agents_dir.exists() {
        println!("   Agents:");
        if let Ok(entries) = fs::read_dir(&agents_dir) {
            for entry_res in entries {
                if let Ok(entry) = entry_res {
                    if let Ok(ft) = entry.file_type() {
                        if ft.is_dir() {
                            let agent_toml = entry.path().join("agent.toml");
                            if agent_toml.exists() {
                                if let Ok(contents) = fs::read_to_string(&agent_toml) {
                                    if let Ok(agent) = toml::from_str::<AgentArchetype>(&contents) {
                                        println!("      🚢 {} — {} (heading: {})", agent.name, agent.role, agent.heading);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    println!();

    // Check refits
    let refits_dir = keel_dir.parent().unwrap().join("refits");
    if refits_dir.exists() {
        let refit_count = fs::read_dir(&refits_dir)
            .map(|e| e.filter_map(|e| e.ok()).count())
            .unwrap_or(0);
        if refit_count > 1 {
            println!("   Build record: {} entries (see refits/)", refit_count - 1); // subtract README
        }
    }

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

fn cmd_prune(target: &str, reason: &str) -> Result<(), String> {
    let keel_dir = find_keel_dir()
        .ok_or_else(|| "No keel found. Are you in a keel workspace?".to_string())?;
    let mut manifest = load_manifest(&keel_dir)?;
    let project_dir = keel_dir.parent().unwrap();
    let now = Utc::now().to_rfc3339();

    // Record the prune
    manifest.keel.refits += 1;
    save_manifest(&keel_dir, &manifest)?;

    let entry = RefitEntry {
        date: now.clone(),
        component: target.to_string(),
        reason: reason.to_string(),
        pruned: vec![target.to_string()],
    };

    let refits_dir = project_dir.join("refits");
    let refit_file = refits_dir.join(format!("refit-{:04}.json", manifest.keel.refits));
    let contents = serde_json::to_string_pretty(&entry)
        .map_err(|e: serde_json::Error| e.to_string())?;
    fs::write(&refit_file, &contents)
        .map_err(|e| format!("Cannot write refit record: {}", e))?;

    // Remove the target if it exists in our workspace
    let target_path = project_dir.join(target);
    if target_path.exists() {
        if target_path.is_dir() {
            fs::remove_dir_all(&target_path)
                .map_err(|e| format!("Cannot remove {}: {}", target_path.display(), e))?;
        } else {
            fs::remove_file(&target_path)
                .map_err(|e| format!("Cannot remove {}: {}", target_path.display(), e))?;
        }
        println!("✂️  Pruned: {}", target);
    } else {
        println!("⚠️  Recorded prune for '{}' but couldn't find it to remove.", target);
    }

    println!("   Reason: {}", reason);
    println!("   Recorded in: refits/refit-{:04}.json", manifest.keel.refits);
    println!("   Total refits: {}", manifest.keel.refits);

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

fn cmd_refit(component: &str, reason: &str) -> Result<(), String> {
    let keel_dir = find_keel_dir()
        .ok_or_else(|| "No keel found. Are you in a keel workspace?".to_string())?;
    let mut manifest = load_manifest(&keel_dir)?;
    let project_dir = keel_dir.parent().unwrap();
    let now = Utc::now().to_rfc3339();

    manifest.keel.refits += 1;
    save_manifest(&keel_dir, &manifest)?;

    let entry = RefitEntry {
        date: now.clone(),
        component: component.to_string(),
        reason: reason.to_string(),
        pruned: vec![],
    };

    let refits_dir = project_dir.join("refits");
    let refit_file = refits_dir.join(format!("refit-{:04}.json", manifest.keel.refits));
    let contents = serde_json::to_string_pretty(&entry)
        .map_err(|e: serde_json::Error| e.to_string())?;
    fs::write(&refit_file, &contents)
        .map_err(|e| format!("Cannot write refit record: {}", e))?;

    println!("🔧 Refit recorded: {}", component);
    println!("   Reason: {}", reason);
    println!("   Recorded in: refits/refit-{:04}.json", manifest.keel.refits);
    println!("   Total refits: {}", manifest.keel.refits);

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

fn cmd_launch(message: Option<String>) -> Result<(), String> {
    let keel_dir = find_keel_dir()
        .ok_or_else(|| "No keel found. Are you in a keel workspace?".to_string())?;
    let manifest = load_manifest(&keel_dir)?;
    let project_dir = keel_dir.parent().unwrap();
    let now = Utc::now().to_rfc3339();

    let msg = message.unwrap_or_default();
    let launch_content = format!(
        r#"{{
  "vessel": "{}",
  "keel_date": "{}",
  "splash_date": "{}",
  "refits_at_launch": {},
  "heading": "{}",
  "message": "{}"
}}
"#,
        manifest.keel.name,
        manifest.keel.keel_date,
        now,
        manifest.keel.refits,
        manifest.keel.heading,
        msg,
    );

    let splash_file = project_dir.join("refits").join("splash.json");
    fs::write(&splash_file, &launch_content)
        .map_err(|e| format!("Cannot write splash record: {}", e))?;

    println!("🚢 {} launched! ({})", manifest.keel.name, now);
    println!("   Keel laid:  {}", manifest.keel.keel_date);
    println!("   On the ways: {} days", "?"); // could calc diff
    println!("   Refits:     {}", manifest.keel.refits);
    println!();
    if !msg.is_empty() {
        println!("   \"{}\"", msg);
    }
    println!();
    println!("   The boat is the motion the idea causes");
    println!("   in the intelligence of those who know what it means.");
    println!("   Everything else is just steel catching up.");

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}


// ─── Bearing Scan ─────────────────────────────────────────────────────────────────

fn cmd_bear(path: &str, ttl_secs: u64) -> Result<(), String> {
    use std::collections::HashMap;
    use std::fs;
    use std::time::SystemTime;

    let mut agents: HashMap<String, (f64, f64, SystemTime)> = HashMap::new();
    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let fname = entry.file_name().to_string_lossy().to_string();
            if !fname.ends_with(".heading") { continue; }
            if let Ok(content) = fs::read_to_string(entry.path()) {
                let parts: Vec<&str> = content.trim().split('|').collect();
                if parts.len() >= 3 {
                    if let (Ok(angle), Ok(rate)) = (parts[1].trim().parse(), parts[2].trim().parse()) {
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
        println!("   Create: echo 'researching|0.5|0.01' > agent.heading");
        return Ok(());
    }

    let now = SystemTime::now();
    let names: Vec<String> = agents.keys().cloned().collect();
    let mut warnings = 0;

    println!("🔮 Bearing-Rate Scan");
    println!("   Agents found: {}", names.len());
    println!();
    println!("   {:<12} {:<12} {:<10} {:<8} {}", "Agent A", "Agent B", "Status", "Angle", "Age");
    println!("   {:-<12} {:-<12} {:-<10} {:-<8} {:-<}", "", "", "", "", "");

    for i in 0..names.len() {
        for j in (i + 1)..names.len() {
            let a = &names[i];
            let b = &names[j];
            if let (Some(&(angle_a, _, mtime_a)), Some(&(angle_b, _, mtime_b))) = (agents.get(a), agents.get(b)) {
                let angle_diff = (angle_a - angle_b).abs();
                let age_a = now.duration_since(mtime_a).map(|d| d.as_secs()).unwrap_or(0);
                let age_b = now.duration_since(mtime_b).map(|d| d.as_secs()).unwrap_or(0);
                let max_age = age_a.max(age_b);
                let rate = if max_age > 0 { angle_diff / max_age as f64 } else { 0.0 };

                let (icon, status) = if max_age > ttl_secs {
                    warnings += 1;
                    ("🔴", "CRITICAL")
                } else if rate < 0.001 && angle_diff < 0.5 {
                    warnings += 1;
                    ("🟡", "WARNING")
                } else {
                    ("🟢", "STABLE")
                };

                println!("   {:<12} {:<12} {} {:<8.4}  {}s", a, b, icon, angle_diff, max_age);
            }
        }
    }

    println!();
    if warnings > 0 {
        println!("   {} collision warning(s) detected.", warnings);
        println!("   \"If the bearing isn't changing, you're on a collision course.\"");
    } else {
        println!("   All clear. Agents maintaining distinct headings.");
    }

    Ok(())
}


// ─── PLATO Sync ───────────────────────────────────────────────────────────────────

fn cmd_sync(server: &str) -> Result<(), String> {
    let keel_dir = find_keel_dir()
        .ok_or_else(|| "No keel found. Are you in a keel workspace?".to_string())?;
    let manifest = load_manifest(&keel_dir)?;
    let project_dir = keel_dir.parent().unwrap();
    let refits_dir = project_dir.join("refits");
    let project_name = &manifest.keel.name;

    println!("🔮 Syncing {} to PLATO at {}", project_name, server);
    println!();

    // Check PLATO is alive
    match plato::get_status(server) {
        Ok(status) => {
            let room_count = status.rooms.map(|r| r.len()).unwrap_or(0);
            println!("   PLATO: {} rooms active", room_count);
            if let Some(ref ver) = status.version {
                println!("   Version: {}", ver);
            }
        }
        Err(e) => {
            println!("   ⚠️  Cannot reach PLATO: {}", e);
            println!("   Sync skipped.");
            return Ok(());
        }
    }
    println!();

    // Sync build record
    let synced = plato::sync_build_record(project_name, &refits_dir, server)
        .unwrap_or(0);
    println!("   Synced {} refit records", synced);

    // Submit keel_date tile
    let date_tile = plato::PlatoTile {
        domain: "keel.meta".to_string(),
        question: format!("{}:keel_date", project_name),
        answer: manifest.keel.keel_date.clone(),
        confidence: Some(1.0),
    };
    match plato::submit_tile(
        &format!("keel_{}", project_name.replace('-', "_").to_lowercase()),
        &date_tile,
        server,
    ) {
        Ok(_) => println!("   Keel date synced"),
        Err(e) => println!("   ⚠️  Could not sync keel date: {}", e),
    }

    println!();
    println!("   Build record is now visible to the fleet.");
    println!("   Other agents can read your heading, refits, and constraints.");

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

// ─── Hardware Probe ────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
struct HardwareProfile {
    probe_date: String,
    platform: String,
    cpu: CpuInfo,
    memory: MemInfo,
    disk: DiskInfo,
    gpu: Option<GpuInfo>,
    power: Option<PowerInfo>,
}

#[derive(Debug, Serialize, Deserialize)]
struct CpuInfo {
    cores: u32,
    model: String,
    arch: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct MemInfo {
    total_kb: u64,
    available_kb: u64,
}

#[derive(Debug, Serialize, Deserialize)]
struct DiskInfo {
    total_gb: u64,
    available_gb: u64,
    usage_pct: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct GpuInfo {
    model: String,
    memory_mb: u64,
    driver: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct PowerInfo {
    state: String,
    max_watts: Option<u32>,
}

fn detect_platform() -> String {
    // Check for known embedded platforms
    if Path::new("/etc/nv_boot_control").exists() {
        if let Ok(content) = fs::read_to_string("/proc/device-tree/model") {
            return format!("Jetson: {}", content.trim_end_matches('\0'));
        }
        return "NVIDIA Jetson".to_string();
    }
    if Path::new("/sys/firmware/devicetree/base/model").exists() {
        if let Ok(mut content) = fs::read_to_string("/sys/firmware/devicetree/base/model") {
            content.truncate(content.trim_end_matches('\0').len());
            if content.contains("Raspberry") || content.contains("BCM") {
                return content.trim().to_string();
            }
        }
    }
    // Generic Linux
    if let Ok(content) = fs::read_to_string("/etc/os-release") {
        for line in content.lines() {
            if line.starts_with("PRETTY_NAME=") {
                return line.trim_start_matches("PRETTY_NAME=").trim_matches('"').to_string();
            }
        }
    }
    // Check uname
    if let Ok(output) = Command::new("uname").arg("-om").output() {
        if let Ok(name) = String::from_utf8(output.stdout) {
            return name.trim().to_string();
        }
    }
    "Unknown".to_string()
}

fn detect_cpu() -> CpuInfo {
    let mut cores = 0u32;
    let mut model = String::new();
    let mut arch = String::new();

    if let Ok(content) = fs::read_to_string("/proc/cpuinfo") {
        for line in content.lines() {
            if line.starts_with("processor") {
                cores += 1;
            } else if line.starts_with("model name") && model.is_empty() {
                model = line.split(':').nth(1).unwrap_or("").trim().to_string();
            } else if line.starts_with("Hardware") && model.is_empty() {
                model = line.split(':').nth(1).unwrap_or("").trim().to_string();
            }
        }
    }

    // For ARM / aarch64, /proc/cpuinfo might not have "processor" lines the same way
    if cores == 0 {
        if let Ok(content) = fs::read_to_string("/proc/cpuinfo") {
            cores = content.lines().filter(|l| l.starts_with("processor") || l.starts_with("CPU")).count() as u32;
        }
    }
    if cores == 0 {
        cores = 1;
    }

    if let Ok(output) = Command::new("uname").arg("-m").output() {
        arch = String::from_utf8(output.stdout).unwrap_or_default().trim().to_string();
    }

    CpuInfo { cores, model: model.trim().to_string(), arch }
}

fn detect_memory() -> MemInfo {
    let mut total_kb = 0u64;
    let mut available_kb = 0u64;
    if let Ok(content) = fs::read_to_string("/proc/meminfo") {
        for line in content.lines() {
            if line.starts_with("MemTotal:") {
                total_kb = line.split_whitespace().nth(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            } else if line.starts_with("MemAvailable:") {
                available_kb = line.split_whitespace().nth(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            }
        }
    }
    MemInfo { total_kb, available_kb }
}

fn detect_disk() -> DiskInfo {
    if let Ok(output) = Command::new("df").arg("-B1").arg("/").output() {
        let stdout = String::from_utf8(output.stdout).unwrap_or_default();
        let mut lines = stdout.lines();
        lines.next(); // skip header
        if let Some(line) = lines.next() {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 4 {
                let total = parts[1].parse::<f64>().unwrap_or(0.0);
                let avail = parts[3].parse::<f64>().unwrap_or(0.0);
                let usage = if total > 0.0 { (1.0 - avail / total) * 100.0 } else { 0.0 };
                return DiskInfo {
                    total_gb: (total / 1_000_000_000.0) as u64,
                    available_gb: (avail / 1_000_000_000.0) as u64,
                    usage_pct: usage,
                };
            }
        }
    }
    DiskInfo { total_gb: 0, available_gb: 0, usage_pct: 0.0 }
}

fn detect_gpu() -> Option<GpuInfo> {
    // Try nvidia-smi
    if let Ok(output) = Command::new("nvidia-smi")
        .args(["--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
        .output()
    {
        if let Ok(stdout) = String::from_utf8(output.stdout) {
            let line = stdout.lines().next().unwrap_or("");
            let parts: Vec<&str> = line.split(", ").collect();
            if parts.len() >= 3 {
                return Some(GpuInfo {
                    model: parts[0].to_string(),
                    memory_mb: parts[1].parse().unwrap_or(0),
                    driver: parts[2].to_string(),
                });
            }
        }
    }
    // Check for vcio / GPU on Raspberry Pi
    if Path::new("/opt/vc/bin/vcgencmd").exists() {
        return Some(GpuInfo {
            model: "Broadcom VideoCore".to_string(),
            memory_mb: 0,
            driver: "vc4".to_string(),
        });
    }
    None
}

fn detect_power() -> Option<PowerInfo> {
    // Check for Jetson power mode
    if let Ok(output) = Command::new("nvpmodel").arg("-q").output() {
        if let Ok(stdout) = String::from_utf8(output.stdout) {
            let line = stdout.lines().next().unwrap_or("");
            let _is_quiet = line.contains("quiet") || line.contains("MAXN") || line.contains("15W") || line.contains("7W");
            // Try to extract wattage
            for part in line.split(|c| c == ' ' || c == ':') {
                if let Ok(w) = part.trim().trim_end_matches('W').parse::<u32>() {
                    if w < 100 {
                        return Some(PowerInfo { state: line.trim().to_string(), max_watts: Some(w) });
                    }
                }
            }
            return Some(PowerInfo { state: line.trim().to_string(), max_watts: None });
        }
    }
    None
}

fn cmd_probe() -> Result<(), String> {
    let now = Utc::now().to_rfc3339();
    let platform = detect_platform();
    let cpu = detect_cpu();
    let memory = detect_memory();
    let disk = detect_disk();
    let gpu = detect_gpu();
    let power = detect_power();

    let profile = HardwareProfile {
        probe_date: now.clone(),
        platform: platform.clone(),
        cpu,
        memory,
        disk,
        gpu,
        power,
    };

    // Try to save to keel workspace
    let mut saved_to = String::new();
    if let Some(keel_dir) = find_keel_dir() {
        let refits_dir = keel_dir.parent().unwrap().join("refits");
        let probe_file = refits_dir.join("hardware-profile.json");
        if let Ok(json) = serde_json::to_string_pretty(&profile) {
            fs::write(&probe_file, &json).ok();
            saved_to = format!("\n   Recorded in: refits/hardware-profile.json");
        }
    }

    // Print report
    println!("🔮 Hardware Probe");
    println!("   Platform: {}", platform);
    println!();
    println!("   CPU:");
    println!("      {} cores ({})", profile.cpu.cores, profile.cpu.arch);
    if !profile.cpu.model.is_empty() {
        println!("      {}", profile.cpu.model);
    }
    println!();
    println!("   Memory:");
    println!("      Total:     {} GB", profile.memory.total_kb / 1_000_000);
    println!("      Available: {} GB", profile.memory.available_kb / 1_000_000);
    println!();
    println!("   Disk:");
    println!("      Total: {} GB", profile.disk.total_gb);
    println!("      Free:  {} GB", profile.disk.available_gb);
    println!("      Used:  {:.0}%", profile.disk.usage_pct);

    if let Some(gpu) = &profile.gpu {
        println!();
        println!("   GPU:");
        println!("      {}", gpu.model);
        if gpu.memory_mb > 0 {
            println!("      {} MB VRAM", gpu.memory_mb);
        }
    }

    if let Some(power) = &profile.power {
        println!();
        println!("   Power:");
        println!("      Mode: {}", power.state);
        if let Some(w) = power.max_watts {
            println!("      Max:  {}W", w);
        }
    }

    println!();
    println!("   Probe date: {}", profile.probe_date);
    println!("   {}", saved_to);
    println!();
    println!("   These are the constraints that breed clarity.");
    println!("   You cannot change the innate seaworthiness of your hardware.");
    println!("   You can only learn it and work within it.");

    // Fleet status (PLATO)
    match plato::get_status("http://localhost:8847") {
        Ok(s) => {
            if let Some(ref rooms) = s.rooms {
                println!("   Fleet: {} rooms on PLATO", rooms.len());
            }
        }
        Err(_) => {}
    }
    Ok(())
}

// ─── Entrypoint ─────────────────────────────────────────────────────────────────────

fn main() {
    let cli = Cli::parse();

    let result = match &cli.command {
        Commands::Init { name, heading, specialists } => {
            cmd_init(name, heading, specialists)
        }
        Commands::Status {} => cmd_status(),
        Commands::Prune { target, reason } => cmd_prune(target, reason),
        Commands::Refit { component, reason } => cmd_refit(component, reason),
        Commands::Launch { message } => cmd_launch(message.clone()),
        Commands::Probe {} => cmd_probe(),
        Commands::Bear { path, ttl } => cmd_bear(path.as_deref().unwrap_or("."), *ttl),
        
        Commands::Sync { server } => cmd_sync(server.as_deref().unwrap_or("http://localhost:8847")),
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}
