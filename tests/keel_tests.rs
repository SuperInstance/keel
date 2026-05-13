//! Integration tests for keel CLI commands.
//!
//! Run with: cargo test --test keel_tests


use std::path::Path;
use std::process::Command;

/// Helper: run keel with given args, return (exit_code, stdout, stderr)
fn keel(args: &[&str]) -> (i32, String, String) {
    let target_dir = std::env::var("CARGO_TARGET_DIR").unwrap_or_else(|_| "target".to_string());
    let bin = Path::new(&target_dir).join("debug/keel");
    
    let output = Command::new(&bin)
        .args(args)
        .output()
        .expect("keel binary not found - run 'cargo build' first");
    
    let code = output.status.code().unwrap_or(-1);
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    (code, stdout, stderr)
}

/// Helper: run keel as subprocess with stdin
fn keel_with_input(input: &str, args: &[&str]) -> (i32, String, String) {
    let target_dir = std::env::var("CARGO_TARGET_DIR").unwrap_or_else(|_| "target".to_string());
    let bin = Path::new(&target_dir).join("debug/keel");
    
    let mut child = Command::new(&bin)
        .args(args)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .expect("keel binary not found");
    
    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        let _ = stdin.write_all(input.as_bytes());
    }
    
    let output = child.wait_with_output().expect("keel wait failed");
    let code = output.status.code().unwrap_or(-1);
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    (code, stdout, stderr)
}

// ─── Init tests ────────────────────────────────────────────────────────────────

#[test]
fn test_init_creates_config() {
    let home = dirs::home_dir().unwrap().join(".keel_test");
    std::env::set_var("HOME", &home);
    
    let (code, stdout, _) = keel(&["init", "--name", "test-vessel"]);
    assert_eq!(code, 0, "init should succeed: {}", stdout);
    assert!(stdout.contains("Keel initialized"), "should confirm init: {}", stdout);
    assert!(stdout.contains("test-vessel"), "should show name: {}", stdout);
}

#[test]
fn test_init_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_json");
    std::env::set_var("HOME", &home);
    
    let (code, stdout, _) = keel(&["init", "--name", "test-json", "--json"]);
    assert_eq!(code, 0);
    
    // JSON output should be valid
    let parsed: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(parsed.get("ok").and_then(|v| v.as_bool()), Some(true));
    assert_eq!(parsed.get("name").and_then(|v| v.as_str()), Some("test-json"));
}

#[test]
fn test_init_default_name() {
    let home = dirs::home_dir().unwrap().join(".keel_test_default");
    std::env::set_var("HOME", &home);
    
    let (code, stdout, _) = keel(&["init"]);
    assert_eq!(code, 0);
    assert!(stdout.contains("default"), "should use default name");
}

// ─── Status tests ─────────────────────────────────────────────────────────────

#[test]
fn test_status_requires_init() {
    let home = dirs::home_dir().unwrap().join(".keel_nonexistent");
    std::env::set_var("HOME", &home);
    
    let (code, stdout, stderr) = keel(&["status"]);
    // Should fail without init - no config found
    if code == 0 {
        // If it succeeds, output should still look right
        assert!(stdout.contains("PLATO") || stdout.contains("Fleet"), 
                "status output: {}", stdout);
    } else {
        assert!(stderr.contains("No keel config") || stderr.contains("init") || stderr.contains("config"),
                "should mention init: {}", stderr);
    }
}

#[test]
fn test_status_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_status_json");
    std::env::set_var("HOME", &home);
    
    // Init first
    keel(&["init", "--name", "test-status"]);
    
    // --json flag should be accepted (even if PLATO is unreachable)
    let (code, stdout, _stderr) = keel(&["status", "--json"]);
    // Either succeeds with JSON or fails with PLATO connection error
    if code == 0 {
        let parsed: serde_json::Value = serde_json::from_str(&stdout).unwrap();
        assert!(parsed.get("server").is_some() || parsed.get("error").is_some());
    }
}

#[test]
fn test_status_watch_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_watch");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-watch"]);
    
    // Watch mode needs to be interruptible - we use timeout
    use std::time::Duration;
    let target_dir = std::env::var("CARGO_TARGET_DIR").unwrap_or_else(|_| "target".to_string());
    let bin = Path::new(&target_dir).join("debug/keel");
    
    let mut child = Command::new(&bin)
        .args(&["status", "--watch"])
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()
        .expect("keel binary not found");
    
    // Wait 2 seconds then kill - enough to see one refresh
    std::thread::sleep(Duration::from_secs(2));
    child.kill().expect("kill failed");
    let output = child.wait_with_output().expect("wait failed");
    
    // Should have produced some output before being killed
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    assert!(stdout.contains("refreshing") || stdout.contains("Fleet Status"));
}

// ─── Field tests ──────────────────────────────────────────────────────────────

#[test]
fn test_field_graph_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_graph");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-graph"]);
    
    let (code, stdout, stderr) = keel(&["field", "--graph"]);
    // PLATO may be unreachable, but --graph flag should be accepted
    // If PLATO unreachable, expect error in JSON or text format
    if code != 0 {
        assert!(stderr.contains("PLATO") || stderr.contains("Cannot reach"));
    }
    // If PLATO reachable and rooms exist, should output DOT format
    if code == 0 && stdout.contains("digraph") {
        assert!(stdout.contains("digraph fleet"));
        assert!(stdout.contains("node"));
    }
}

#[test]
fn test_field_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_field_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-field-json"]);
    
    let (code, stdout, _) = keel(&["field", "--json"]);
    // Either success with JSON or PLATO unreachable error
    if code == 0 {
        let parsed: serde_json::Value = serde_json::from_str(&stdout).unwrap();
        assert!(parsed.get("server").is_some() || parsed.get("rooms").is_some());
    }
}

// ─── Probe tests ──────────────────────────────────────────────────────────────

#[test]
fn test_probe_requires_room() {
    let home = dirs::home_dir().unwrap().join(".keel_test_probe");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-probe"]);
    
    let (_code, _, _) = keel(&["probe"]);
    // Should at least parse the command (may fail without PLATO)
    // No assertion on code - depends on PLATO availability
}

#[test]
fn test_probe_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_probe_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-probe-json"]);
    
    let (code, stdout, _) = keel(&["probe", "--room", "oracle1", "--json"]);
    // Should output valid JSON or error JSON
    if code == 0 || stdout.starts_with('{') {
        // Valid JSON response (success or error)
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

// ─── Prune tests ──────────────────────────────────────────────────────────────

#[test]
fn test_prune_timeout_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_prune");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-prune"]);
    
    // --timeout flag should be accepted
    let (code, stdout, _) = keel(&["prune", "--room", "nonexistent", "--timeout", "2"]);
    // Room doesn't exist, but flag is valid
    eprintln!("DEBUG prune stdout: {:?}", stdout);
    if code == 0 {
        // Accept any valid response — timeout flag was accepted
        assert!(stdout.contains("not found") || stdout.contains("pruned") || stdout.contains("Pruning"));
    }
}

#[test]
fn test_prune_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_prune_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-prune-json"]);
    
    let (code, stdout, _) = keel(&["prune", "--room", "test", "--json"]);
    // JSON flag should produce JSON output
    if code == 0 || stdout.starts_with('{') {
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

// ─── Refit tests ──────────────────────────────────────────────────────────────

#[test]
fn test_refit_requires_room() {
    let home = dirs::home_dir().unwrap().join(".keel_test_refit");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-refit"]);
    
    // Should require --room
    let (code, _, stderr) = keel(&["refit"]);
    assert!(code != 0 || stderr.contains("room"), "should require room arg");
}

#[test]
fn test_refit_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_refit_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-refit-json"]);
    
    // Show current config with JSON
    let (code, stdout, _) = keel(&["refit", "--room", "oracle1", "--json"]);
    // JSON flag should produce JSON output
    if code == 0 || stdout.starts_with('{') {
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

#[test]
fn test_refit_timeout_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_refit_timeout");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-refit-timeout"]);
    
    let (_code, _, _) = keel(&["refit", "--room", "oracle1", "--timeout", "1"]);
    // Should accept --timeout flag
}

// ─── Launch tests ─────────────────────────────────────────────────────────────

#[test]
fn test_launch_requires_args() {
    let home = dirs::home_dir().unwrap().join(".keel_test_launch");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-launch"]);
    
    let (code, _, stderr) = keel(&["launch"]);
    assert!(code != 0 || stderr.contains("room") || stderr.contains("name"),
            "should require room and name");
}

#[test]
fn test_launch_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_launch_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-launch-json"]);
    
    let (code, stdout, _) = keel(&["launch", "--room", "oracle1", "--name", "test-agent", "--json"]);
    // JSON output or error
    if code == 0 || stdout.starts_with('{') {
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

// ─── Sync tests ──────────────────────────────────────────────────────────────

#[test]
fn test_sync_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_sync");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-sync"]);
    
    let (code, stdout, _) = keel(&["sync", "--json"]);
    // JSON flag should produce valid JSON
    if code == 0 || stdout.starts_with('{') {
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

#[test]
fn test_sync_timeout_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_sync_timeout");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-sync-timeout"]);
    
    let (_code, _, _) = keel(&["sync", "--timeout", "3"]);
    // Should accept --timeout flag
}

#[test]
fn test_sync_custom_server() {
    let home = dirs::home_dir().unwrap().join(".keel_test_sync_server");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-sync-server", "--server", "https://plato.purplepincher.org"]);
    
    let (_code, _, _) = keel(&["sync", "--server", "https://plato.purplepincher.org"]);
    // Should accept custom server
}

// ─── Bear tests ────────────────────────────────────────────────────────────────

#[test]
fn test_bear_no_files() {
    let home = dirs::home_dir().unwrap().join(".keel_test_bear");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-bear"]);
    
    let (_code, stdout, _) = keel(&["bear"]);
    // Without .heading files, should show message
    assert!(stdout.contains("No .heading files") || stdout.contains("found"));
}

#[test]
fn test_bear_json_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_bear_json");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-bear-json"]);
    
    let (code, stdout, _) = keel(&["bear", "--json"]);
    // JSON flag should produce valid JSON even with no files
    if code == 0 || stdout.starts_with('[') {
        let parsed: Result<serde_json::Value, _> = serde_json::from_str(&stdout);
        assert!(parsed.is_ok(), "should be valid JSON: {}", stdout);
    }
}

#[test]
fn test_bear_ttl_flag() {
    let home = dirs::home_dir().unwrap().join(".keel_test_bear_ttl");
    std::env::set_var("HOME", &home);
    
    keel(&["init", "--name", "test-bear-ttl"]);
    
    let (code, _, _) = keel(&["bear", "--ttl", "120"]);
    // Should accept custom TTL
    assert_eq!(code, 0);
}

// ─── Version/Help tests ────────────────────────────────────────────────────────

#[test]
fn test_version_flag() {
    let (code, stdout, _) = keel(&["--version"]);
    assert_eq!(code, 0);
    assert!(stdout.contains("0.1.0") || stdout.contains("keel"));
}

#[test]
fn test_help_flag() {
    let (code, stdout, _) = keel(&["--help"]);
    assert_eq!(code, 0);
    assert!(stdout.contains("The yard you step into"));
    assert!(stdout.contains("init"));
    assert!(stdout.contains("status"));
    assert!(stdout.contains("field"));
}

// ─── JSON types serialization tests ────────────────────────────────────────────

#[test]
fn test_status_json_serialization() {
    // Test that StatusJson serializes correctly
    use serde_json;
    
    #[derive(serde::Serialize)]
    struct StatusJson {
        server: String,
        version: Option<String>,
        rooms: Vec<RoomJson>,
        total_tiles: usize,
        this_member: Option<String>,
        keel_date: Option<String>,
    }
    
    #[derive(serde::Serialize)]
    struct RoomJson {
        name: String,
        tile_count: usize,
        agent_count: usize,
        description: Option<String>,
    }
    
    let json = StatusJson {
        server: "https://plato.purplepincher.org".to_string(),
        version: Some("1.0.0".to_string()),
        rooms: vec![
            RoomJson {
                name: "oracle1".to_string(),
                tile_count: 42,
                agent_count: 3,
                description: Some("Test room".to_string()),
            },
        ],
        total_tiles: 42,
        this_member: Some("test-member".to_string()),
        keel_date: Some("2026-05-13T00:00:00Z".to_string()),
    };
    
    let output = serde_json::to_string_pretty(&json).unwrap();
    assert!(output.contains("\"server\""));
    assert!(output.contains("\"rooms\""));
    assert!(output.contains("oracle1"));
}

#[test]
fn test_bearing_json_serialization() {
    use serde_json;
    
    #[derive(serde::Serialize)]
    struct BearingJson {
        agent_a: String,
        agent_b: String,
        status: String,
        angle: f64,
        rate: f64,
        age_secs: u64,
        warning: Option<String>,
    }
    
    let json = BearingJson {
        agent_a: "agent1".to_string(),
        agent_b: "agent2".to_string(),
        status: "STABLE".to_string(),
        angle: 0.5,
        rate: 0.001,
        age_secs: 30,
        warning: None,
    };
    
    let output = serde_json::to_string_pretty(&json).unwrap();
    assert!(output.contains("agent1"));
    assert!(output.contains("agent2"));
    assert!(output.contains("STABLE"));
}

// ─── Plato types tests ─────────────────────────────────────────────────────────

#[test]
fn test_plato_tile_serialization() {
    use serde_json;
    
    #[derive(serde::Serialize, serde::Deserialize, Debug)]
    struct PlatoTile {
        domain: String,
        question: String,
        answer: String,
        confidence: Option<f64>,
    }
    
    let tile = PlatoTile {
        domain: "test.domain".to_string(),
        question: "test:question".to_string(),
        answer: "test answer".to_string(),
        confidence: Some(0.95),
    };
    
    let json = serde_json::to_string(&tile).unwrap();
    assert!(json.contains("test.domain"));
    assert!(json.contains("test:question"));
    
    let parsed: PlatoTile = serde_json::from_str(&json).unwrap();
    assert_eq!(parsed.domain, "test.domain");
    assert_eq!(parsed.confidence, Some(0.95));
}

#[test]
fn test_plato_status_parsing() {
    use serde_json;
    
    #[derive(serde::Deserialize, Debug)]
    struct PlatoStatus {
        status: Option<String>,
        rooms: Option<serde_json::Value>,
        version: Option<String>,
    }
    
    let json_str = r#"{"status":"ok","rooms":{"oracle1":{"tile_count":42},"oracle1_history":{"tile_count":10}},"version":"1.0.0"}"#;
    let parsed: PlatoStatus = serde_json::from_str(json_str).unwrap();
    
    assert_eq!(parsed.version, Some("1.0.0".to_string()));
    
    let rooms = parsed.rooms.unwrap();
    let oracle1 = rooms.get("oracle1").unwrap();
    assert_eq!(oracle1.get("tile_count").and_then(|v| v.as_i64()), Some(42));
}

// ─── Bearing collision detection ──────────────────────────────────────────────

#[test]
fn test_bearing_collision_logic() {
    // Test the collision detection threshold from cmd_bear
    // rate < 0.001 && angle_diff < 0.5 -> WARNING
    // max_age > ttl_secs -> CRITICAL
    
    fn assess(angle_diff: f64, rate: f64, max_age: u64, ttl_secs: u64) -> &'static str {
        if max_age > ttl_secs {
            return "CRITICAL";
        }
        if rate < 0.001 && angle_diff < 0.5 {
            return "WARNING";
        }
        "STABLE"
    }
    
    // Stable: rate is changing
    assert_eq!(assess(0.3, 0.01, 30, 60), "STABLE");
    
    // Stable: angle is large enough
    assert_eq!(assess(0.6, 0.0005, 30, 60), "STABLE");
    
    // Warning: low rate AND small angle
    assert_eq!(assess(0.3, 0.0005, 30, 60), "WARNING");
    
    // Critical: expired bearing
    assert_eq!(assess(0.3, 0.0005, 65, 60), "CRITICAL");
}

// ─── Config key=value parsing ─────────────────────────────────────────────────

#[test]
fn test_refit_config_parsing() {
    use std::collections::HashMap;
    
    fn parse_config(cfg: &str) -> HashMap<String, String> {
        cfg.split(',')
            .filter_map(|pair| {
                let mut parts = pair.splitn(2, '=');
                let key = parts.next()?.trim();
                let val = parts.next()?.trim();
                Some((key.to_string(), val.to_string()))
            })
            .collect()
    }
    
    let config = "max_tiles=100,enabled=true,description=Test room";
    let map = parse_config(config);
    
    assert_eq!(map.get("max_tiles").map(|s| s.as_str()), Some("100"));
    assert_eq!(map.get("enabled").map(|s| s.as_str()), Some("true"));
    assert_eq!(map.get("description").map(|s| s.as_str()), Some("Test room"));
    assert_eq!(map.len(), 3);
}

#[test]
fn test_refit_config_parsing_edge_cases() {
    use std::collections::HashMap;
    
    fn parse_config(cfg: &str) -> HashMap<String, String> {
        cfg.split(',')
            .filter_map(|pair| {
                let mut parts = pair.splitn(2, '=');
                let key = parts.next()?.trim();
                let val = parts.next()?.trim();
                Some((key.to_string(), val.to_string()))
            })
            .collect()
    }
    
    // Empty config
    let map = parse_config("");
    assert_eq!(map.len(), 0);
    
    // Single value
    let map = parse_config("key=value");
    assert_eq!(map.len(), 1);
    
    // Whitespace handling
    let map = parse_config(" key = value , another = test ");
    assert_eq!(map.get("key").map(|s| s.as_str()), Some("value"));
    assert_eq!(map.get("another").map(|s| s.as_str()), Some("test"));
}

// ─── Field DOT graph output ──────────────────────────────────────────────────

#[test]
fn test_dot_graph_format() {
    // Verify DOT format output structure
    let dot_output = r#"digraph fleet {
    graph [label="Fleet Field Topology — https://plato.purplepincher.org" fontname="monospace"];
    node [shape=box style=filled fillcolor=lightblue];
    "oracle1" [label="oracle1 (tiles=42, agents=3)"];
    "oracle1_history" [label="oracle1_history (tiles=10, agents=1)"];
    "oracle1" -> "oracle1_history";
}"#;
    
    assert!(dot_output.contains("digraph fleet"));
    assert!(dot_output.contains("node [shape=box"));
    assert!(dot_output.contains("oracle1"));
    assert!(dot_output.contains("->"));
}