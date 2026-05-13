//! Unit tests for keel internal types and logic.
//!
//! Run with: cargo test

#[cfg(test)]
mod tests {
    use serde_json;

    // ─── Config tests ──────────────────────────────────────────────────────────

    #[test]
    fn test_keel_config_roundtrip() {
        #[derive(Debug, serde::Serialize, serde::Deserialize)]
        struct KeelConfig {
            name: String,
            server: String,
            keel_date: String,
        }

        let cfg = KeelConfig {
            name: "test-vessel".to_string(),
            server: "http://localhost:8847".to_string(),
            keel_date: "2026-05-13T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&cfg).unwrap();
        let parsed: KeelConfig = serde_json::from_str(&json).unwrap();

        assert_eq!(parsed.name, "test-vessel");
        assert_eq!(parsed.server, "http://localhost:8847");
    }

    #[test]
    fn test_room_json_serialization() {
        #[derive(Debug, serde::Serialize)]
        struct RoomJson {
            name: String,
            tile_count: usize,
            agent_count: usize,
            description: Option<String>,
        }

        let room = RoomJson {
            name: "oracle1".to_string(),
            tile_count: 42,
            agent_count: 3,
            description: Some("Test room".to_string()),
        };

        let json = serde_json::to_string_pretty(&room).unwrap();
        assert!(json.contains("oracle1"));
        assert!(json.contains("42"));
        assert!(json.contains("Test room"));
    }

    #[test]
    fn test_status_json_serialization() {
        #[derive(Debug, serde::Serialize)]
        struct StatusJson {
            server: String,
            version: Option<String>,
            total_tiles: usize,
        }

        let status = StatusJson {
            server: "http://localhost:8847".to_string(),
            version: Some("1.0.0".to_string()),
            total_tiles: 142,
        };

        let json = serde_json::to_string(&status).unwrap();
        assert!(json.contains("142"));
        assert!(json.contains("1.0.0"));
    }

    #[test]
    fn test_sync_json_serialization() {
        #[derive(Debug, serde::Serialize)]
        struct SyncJson {
            server: String,
            identity_synced: bool,
            tiles_synced: usize,
            member: String,
            timestamp: String,
        }

        let sync = SyncJson {
            server: "http://localhost:8847".to_string(),
            identity_synced: true,
            tiles_synced: 5,
            member: "test-vessel".to_string(),
            timestamp: "2026-05-13T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&sync).unwrap();
        assert!(json.contains("identity_synced"));
        assert!(json.contains("tiles_synced"));
    }

    #[test]
    fn test_probe_json_serialization() {
        #[derive(Debug, serde::Serialize)]
        struct ProbeJson {
            room: String,
            tile_count: usize,
            agent_count: usize,
            domains: Vec<String>,
        }

        let probe = ProbeJson {
            room: "oracle1".to_string(),
            tile_count: 42,
            agent_count: 3,
            domains: vec!["keel.member".to_string(), "test.domain".to_string()],
        };

        let json = serde_json::to_string(&probe).unwrap();
        assert!(json.contains("oracle1"));
        assert!(json.contains("domains"));
    }

    // ─── Plato type tests ───────────────────────────────────────────────────────

    #[test]
    fn test_plato_tile_serialization() {
        #[derive(Debug, serde::Serialize, serde::Deserialize, PartialEq)]
        struct PlatoTile {
            domain: String,
            question: String,
            answer: String,
            confidence: Option<f64>,
        }

        let tile = PlatoTile {
            domain: "keel.member".to_string(),
            question: "test-vessel:keel_date".to_string(),
            answer: "2026-05-13T00:00:00Z".to_string(),
            confidence: Some(1.0),
        };

        let json = serde_json::to_string(&tile).unwrap();
        let parsed: PlatoTile = serde_json::from_str(&json).unwrap();

        assert_eq!(parsed.domain, "keel.member");
        assert_eq!(parsed.confidence, Some(1.0));
    }

    #[test]
    fn test_plato_submit_response_parsing() {
        #[derive(Debug, serde::Deserialize)]
        struct PlatoSubmitResponse {
            status: String,
            room: String,
            tile_hash: Option<String>,
        }

        let json_str = r#"{"status":"ok","room":"keel_test","tile_hash":"abc123"}"#;
        let parsed: PlatoSubmitResponse = serde_json::from_str(json_str).unwrap();

        assert_eq!(parsed.status, "ok");
        assert_eq!(parsed.room, "keel_test");
        assert_eq!(parsed.tile_hash, Some("abc123".to_string()));
    }

    #[test]
    fn test_plato_status_parsing() {
        #[derive(Debug, serde::Deserialize)]
        struct PlatoStatus {
            status: Option<String>,
            rooms: Option<serde_json::Value>,
            version: Option<String>,
        }

        let json_str = r#"{"status":"ok","rooms":{"oracle1":{"tile_count":42}},"version":"1.0.0"}"#;
        let parsed: PlatoStatus = serde_json::from_str(json_str).unwrap();

        assert_eq!(parsed.status, Some("ok".to_string()));
        assert_eq!(parsed.version, Some("1.0.0".to_string()));

        let rooms = parsed.rooms.unwrap();
        let oracle1 = rooms.get("oracle1").unwrap();
        assert_eq!(oracle1.get("tile_count").and_then(|v| v.as_i64()), Some(42));
    }

    #[test]
    fn test_plato_status_empty_rooms() {
        #[derive(Debug, serde::Deserialize)]
        struct PlatoStatus {
            rooms: Option<serde_json::Value>,
        }

        let json_str = r#"{"rooms":null}"#;
        let parsed: PlatoStatus = serde_json::from_str(json_str).unwrap();
        assert!(parsed.rooms.is_none());

        let json_str2 = r#"{"rooms":{}}"#;
        let parsed2: PlatoStatus = serde_json::from_str(json_str2).unwrap();
        assert!(parsed2.rooms.is_some());
    }

    // ─── Bearing logic tests ────────────────────────────────────────────────────

    #[test]
    fn test_bearing_collision_detection() {
        fn assess(angle_diff: f64, rate: f64, max_age: u64, ttl_secs: u64) -> &'static str {
            if max_age > ttl_secs {
                return "CRITICAL";
            }
            if rate < 0.001 && angle_diff < 0.5 {
                return "WARNING";
            }
            "STABLE"
        }

        // CRITICAL: bearing expired
        assert_eq!(assess(0.3, 0.0005, 65, 60), "CRITICAL");

        // WARNING: low rate, small angle
        assert_eq!(assess(0.3, 0.0005, 30, 60), "WARNING");
        assert_eq!(assess(0.49, 0.0001, 30, 60), "WARNING");

        // STABLE: rate is changing
        assert_eq!(assess(0.3, 0.01, 30, 60), "STABLE");

        // STABLE: angle is large enough
        assert_eq!(assess(0.5, 0.0005, 30, 60), "STABLE");
        assert_eq!(assess(1.0, 0.0001, 30, 60), "STABLE");

        // STABLE: neither condition met
        assert_eq!(assess(1.0, 0.01, 30, 60), "STABLE");
    }

    #[test]
    fn test_bearing_rate_calculation() {
        fn calc_rate(angle_diff: f64, max_age_secs: u64) -> f64 {
            if max_age_secs > 0 {
                angle_diff / max_age_secs as f64
            } else {
                0.0
            }
        }

        assert_eq!(calc_rate(0.5, 10), 0.05);
        assert_eq!(calc_rate(0.5, 50), 0.01);
        assert_eq!(calc_rate(0.5, 500), 0.001);
        assert_eq!(calc_rate(0.0, 10), 0.0);
        assert_eq!(calc_rate(0.5, 0), 0.0);
    }

    // ─── Room config parsing ────────────────────────────────────────────────────

    #[test]
    fn test_room_name_normalization() {
        fn normalize(name: &str) -> String {
            format!("keel_{}", name.replace('-', "_").to_lowercase())
        }

        assert_eq!(normalize("My-Vessel"), "keel_my_vessel");
        assert_eq!(normalize("test-vessel"), "keel_test_vessel");
        assert_eq!(normalize("ORACLE1"), "keel_oracle1");
    }

    #[test]
    fn test_config_key_value_parsing() {
        fn parse_config(cfg: &str) -> Vec<(String, String)> {
            cfg.split(',')
                .filter_map(|pair| {
                    let mut parts = pair.splitn(2, '=');
                    let key = parts.next()?.trim();
                    let val = parts.next()?.trim();
                    Some((key.to_string(), val.to_string()))
                })
                .collect()
        }

        let config = "max_tiles=100,enabled=true";
        let pairs = parse_config(config);

        assert_eq!(pairs.len(), 2);
        assert_eq!(pairs[0], ("max_tiles".to_string(), "100".to_string()));
        assert_eq!(pairs[1], ("enabled".to_string(), "true".to_string()));
    }

    // ─── URL normalization ────────────────────────────────────────────────────

    #[test]
    fn test_server_url_normalization() {
        fn normalize(url: &str) -> String {
            url.trim_end_matches('/').to_string()
        }

        assert_eq!(normalize("http://localhost:8847"), "http://localhost:8847");
        assert_eq!(normalize("http://localhost:8847/"), "http://localhost:8847");
        assert_eq!(normalize("http://localhost:8847//"), "http://localhost:8847");
    }

    #[test]
    fn test_room_url_construction() {
        fn room_url(server: &str, room: &str) -> String {
            format!("{}/room/{}", server.trim_end_matches('/'), room)
        }

        assert_eq!(room_url("http://localhost:8847", "oracle1"),
                   "http://localhost:8847/room/oracle1");
        assert_eq!(room_url("http://localhost:8847/", "oracle1"),
                   "http://localhost:8847/room/oracle1");
    }

    // ─── JSON output type tests ───────────────────────────────────────────────

    #[test]
    fn test_launch_json_fields() {
        #[derive(Debug, serde::Serialize)]
        struct LaunchJson {
            agent: String,
            room: String,
            job: String,
            success: bool,
            message: Option<String>,
            timestamp: String,
        }

        let launch = LaunchJson {
            agent: "test-agent".to_string(),
            room: "oracle1".to_string(),
            job: "worker".to_string(),
            success: true,
            message: Some("Agent deployed successfully".to_string()),
            timestamp: "2026-05-13T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&launch).unwrap();
        assert!(json.contains("test-agent"));
        assert!(json.contains("success"));
        assert!(json.contains("true"));
    }

    #[test]
    fn test_prune_json_fields() {
        #[derive(Debug, serde::Serialize)]
        struct PruneJson {
            room: String,
            target: String,
            pruned_count: usize,
            items: Vec<String>,
            timestamp: String,
        }

        let prune = PruneJson {
            room: "oracle1".to_string(),
            target: "tiles".to_string(),
            pruned_count: 3,
            items: vec!["tile1".to_string(), "tile2".to_string(), "tile3".to_string()],
            timestamp: "2026-05-13T00:00:00Z".to_string(),
        };

        let json = serde_json::to_string(&prune).unwrap();
        assert!(json.contains("oracle1"));
        assert!(json.contains("tiles"));
        assert!(json.contains("3"));
    }

    #[test]
    fn test_field_json_edges() {
        #[derive(Debug, serde::Serialize)]
        struct EdgeJson {
            from: String,
            to: String,
        }

        let edges = vec![
            EdgeJson { from: "oracle1".to_string(), to: "oracle1_history".to_string() },
        ];

        let json = serde_json::to_string(&edges).unwrap();
        assert!(json.contains("oracle1"));
        assert!(json.contains("oracle1_history"));
    }

    // ─── DOT graph format tests ────────────────────────────────────────────────

    #[test]
    fn test_dot_node_format() {
        let name = "oracle1";
        let tile_count = 42;
        let agent_count = 3;

        let node = format!(
            r#"    "{}" [label="{} (tiles={}, agents={})"];"#,
            name, name, tile_count, agent_count
        );

        assert!(node.contains("oracle1"));
        assert!(node.contains("tiles=42"));
        assert!(node.contains("agents=3"));
    }

    #[test]
    fn test_dot_edge_format() {
        let from = "oracle1";
        let to = "oracle1_history";

        let edge = format!(r#"    "{}" -> "{}";"#, from, to);

        assert!(edge.contains("->"));
        assert!(edge.contains("oracle1"));
    }

    // ─── Timeout handling ─────────────────────────────────────────────────────

    #[test]
    fn test_default_timeout() {
        fn get_timeout(timeout: Option<u64>) -> u64 {
            timeout.unwrap_or(5)
        }

        assert_eq!(get_timeout(None), 5);
        assert_eq!(get_timeout(Some(1)), 1);
        assert_eq!(get_timeout(Some(30)), 30);
    }

    // ─── Edge detection ─────────────────────────────────────────────────────

    #[test]
    fn test_shared_prefix_edge_detection() {
        fn has_edge(a: &str, b: &str) -> bool {
            let min_len = a.len().min(b.len()).min(4);
            a.starts_with(&b[..min_len]) || b.starts_with(&a[..min_len])
        }

        assert!(has_edge("oracle1", "oracle1_history"));
        assert!(has_edge("oracle1_history", "oracle1"));
        assert!(has_edge("foo_bar", "foo_baz"));
        assert!(!has_edge("oracle1", "plato"));
        assert!(!has_edge("alpha", "beta"));
    }

    // ─── KeelConfig path ──────────────────────────────────────────────────────

    #[test]
    fn test_config_path_join() {
        fn config_path(home: &std::path::Path) -> std::path::PathBuf {
            home.join(".keel").join("config.toml")
        }

        let home = std::path::Path::new("/home/ubuntu");
        let path = config_path(home);

        assert_eq!(path, std::path::Path::new("/home/ubuntu/.keel/config.toml"));
    }
}