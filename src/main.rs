// Keel — the yard you step into.
// Field-effect foundation for agent fleets.
//
// Laid 2026-05-09.
// "Constraints breed clarity."

use chrono::Utc;
use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

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
    };

    if let Err(e) = result {
        eprintln!("Error: {}", e);
        std::process::exit(1);
    }
}
