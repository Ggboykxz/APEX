mod agent;
mod config;
mod formatter;
mod hooks;
mod plugins;
mod jsonrpc;
mod lsp;
mod mcp_client;
mod server;
mod tools;

use clap::{Parser, Subcommand};
use config::Config;
use std::io::Write;

#[derive(Parser, Debug)]
#[command(name = "apex-rs", version, about = "APEX backend rewritten in Rust")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// One-shot prompt
    Run { prompt: String, #[arg(short, long)] session: Option<String> },
    /// Interactive REPL
    Chat { #[arg(short, long)] session: Option<String> },
    /// Start HTTP server
    Serve { #[arg(short, long, default_value = "8765")] port: u16 },
    /// List tools
    Tools,
    /// List plugins
    Plugins,
    /// Execute a single tool (useful for debugging MCP servers)
    CallTool {
        name: String,
        #[arg(default_value = "{}")]
        args: String,
    },
}

fn load_mcp_servers() {
    // Run discovery on a dedicated thread: `main` is itself async, so creating
    // and blocking on another runtime from there would panic.
    let _ = std::thread::spawn(|| {
        let base = dirs::home_dir().unwrap_or_default().join(".apex").join("mcp.json");
        if !base.exists() { return; }
        let data = match std::fs::read_to_string(&base) { Ok(d) => d, Err(_) => return };
        let v: serde_json::Value = match serde_json::from_str(&data) { Ok(v) => v, Err(_) => return };
        let servers = v.get("mcpServers").or_else(|| v.get("mcp_servers")).and_then(|x| x.as_object());
        let Some(servers) = servers else { return };
        let mut mgr = crate::mcp_client::McpManager::new();
        for (name, cfg) in servers {
            let command = cfg.get("command").and_then(|x| x.as_str()).unwrap_or("").to_string();
            let args: Vec<String> = cfg.get("args").and_then(|x| x.as_array())
                .map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect())
                .unwrap_or_default();
            if !command.is_empty() {
                mgr.add_server(name.clone(), command, args);
            }
        }
        let rt = match tokio::runtime::Runtime::new() { Ok(r) => r, Err(_) => return };
        rt.block_on(mgr.connect_all());
        crate::mcp_client::set_global(mgr);
    })
    .join();
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let config = Config::from_env();
    // Load MCP servers from ~/.apex/mcp.json if present.
    load_mcp_servers();
    match cli.command {
        Some(Commands::Run { prompt, session }) => {
            let mut agent = agent::Agent::new(config);
            if let Some(id) = &session { let _ = agent.load_session(id); }
            match agent.chat(&prompt).await {
                Ok(resp) => { println!("{resp}"); let _ = std::io::stdout().flush(); }
                Err(e) => eprintln!("ERROR: {e}"),
            }
            if let Some(id) = &session { let _ = agent.save_session(id); }
        }
        Some(Commands::Chat { session }) => {
            let mut agent = agent::Agent::new(config);
            if let Some(id) = &session { let _ = agent.load_session(id); }
            agent.run_repl();
            if let Some(id) = &session { let _ = agent.save_session(id); }
        }
        Some(Commands::Serve { port }) => {
            server::serve(config, port).await;
        }
        Some(Commands::Tools) => {
            let v = tools::tool_schemas();
            println!("{}", serde_json::to_string_pretty(&v).unwrap());
        }
        Some(Commands::Plugins) => {
            let ps = plugins::discover_plugins();
            if ps.is_empty() {
                println!("No plugins found (~/.apex/plugins/)");
            } else {
                for p in ps {
                    println!("{}", p.name);
                }
            }
        }
        Some(Commands::CallTool { name, args }) => {
            let parsed: serde_json::Value = serde_json::from_str(&args).unwrap_or(serde_json::json!({}));
            println!("{}", tools::execute_tool(&name, &parsed, &config.cwd));
        }
        None => {
            println!("APEX (Rust) — type 'apex-rs --help'");
        }
    }
}