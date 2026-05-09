// Keel Field Visualization Server
// Serves the field-view.html dashboard and proxies PLATO API calls.

use std::io::Read;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;

static RUNNING: AtomicBool = AtomicBool::new(true);

pub fn start(port: u16) -> Result<(), String> {
    let addr = format!("0.0.0.0:{}", port);
    let server = tiny_http::Server::http(&addr)
        .map_err(|e| format!("Failed to start server: {}", e))?;
    
    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();
    
    println!("🔮 Keel Field Dashboard");
    println!("   Serving at: http://localhost:{}/", port);
    println!("   Press Ctrl+C to stop.");
    println!();
    
    ctrlc::set_handler(move || {
        r.store(false, Ordering::SeqCst);
        println!("\n   Shutting down.");
    }).map_err(|e| format!("Ctrl+C handler: {}", e))?;
    
    while RUNNING.load(Ordering::SeqCst) {
        match server.recv_timeout(std::time::Duration::from_secs(1)) {
            Ok(Some(mut request)) => {
                let url = request.url().to_string();
                let response = handle_request(&url);
                let _ = request.respond(response);
            }
            Ok(None) => {}
            Err(_) => break,
        }
    }
    
    Ok(())
}

fn handle_request(url: &str) -> tiny_http::Response<std::io::Cursor<Vec<u8>>> {
    // Route: / -> serve the field view HTML
    // Route: /status -> proxy PLATO status
    // Route: /room/{name} -> proxy PLATO room
    
    if url == "/" || url == "/index.html" {
        let html = include_str!("../web/field-view.html");
        let resp = tiny_http::Response::from_string(html.to_string())
            .with_header(
                "Content-Type: text/html; charset=utf-8".parse::<tiny_http::Header>().unwrap()
            );
        return resp;
    }
    
    // Proxy to PLATO
    let plato_url = format!("http://localhost:8847{}", url);
    match fetch_url(&plato_url) {
        Ok((body, content_type)) => {
            let ct = content_type.unwrap_or_else(|| "application/json".to_string());
            let mut response = tiny_http::Response::from_string(body)
                .with_header(
                    format!("Content-Type: {}", ct).parse::<tiny_http::Header>().unwrap()
                )
                .with_header(
                    "Access-Control-Allow-Origin: *".parse::<tiny_http::Header>().unwrap()
                );
            response
        }
        Err(e) => {
            tiny_http::Response::from_string(format!("{{ \"error\": \"{}\" }}", e))
                .with_status_code(502)
        }
    }
}

fn fetch_url(url: &str) -> Result<(String, Option<String>), String> {
    let resp = reqwest::blocking::get(url)
        .map_err(|e| format!("Fetch error: {}", e))?;
    let ct = resp.headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string());
    let body = resp.text().map_err(|e| format!("Body error: {}", e))?;
    Ok((body, ct))
}
