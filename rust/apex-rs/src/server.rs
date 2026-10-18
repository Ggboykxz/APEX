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