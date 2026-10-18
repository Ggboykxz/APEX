use crate::agent::Agent;
use crate::config::Config;
use axum::{routing::{get, post}, Json, Router};
use serde_json;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Deserialize)]
struct ChatReq { prompt: String }

#[derive(Serialize)]
struct ChatResp { response: String }

pub async fn serve(config: Config, port: u16) {
    let agent = Arc::new(Mutex::new(Agent::new(config)));
    let app = Router::new()
        .route("/health", get(|| async { "ok" }))
        .route("/api/v1/tools", get(|| async {
            Json(serde_json::to_value(crate::tools::tool_schemas()).unwrap())
        }))
        .route("/api/v1/models", get(|| async {
            Json(serde_json::json!({"models":[std::env::var("APEX_MODEL").unwrap_or_else(|_| "gpt-4o-mini".to_string())]}))
        }))
        .route("/api/v1/sessions", get(|| async {
            let base = dirs::home_dir().unwrap_or_default().join(".apex").join("sessions");
            let mut names = Vec::new();
            if let Ok(rd) = std::fs::read_dir(&base) {
                for e in rd.flatten() {
                    if let Some(n) = e.file_name().to_str() {
                        names.push(n.trim_end_matches(".json").to_string());
                    }
                }
            }
            Json(serde_json::json!({"sessions": names}))
        }))
        .route("/api/v1/chat", post({
            let agent = agent.clone();
            move |Json(req): Json<ChatReq>| async move {
                let mut a = agent.lock().await;
                let resp = a.chat(&req.prompt).await.unwrap_or_else(|e| format!("ERROR: {e}"));
                Json(ChatResp { response: resp })
            }
        }));
    let addr = format!("127.0.0.1:{port}");
    println!("APEX (Rust) listening on {addr}");
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}