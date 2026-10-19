mod agent;
mod codegen;
mod config;
mod cost;
mod formatter;
mod github;
mod hooks;
mod memory;
mod plugins;
mod jsonrpc;
mod lsp;
mod mcp_client;
mod server;
mod session_crypto;
mod share;
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
    /// Show session token usage and estimated cost
    Cost,
    /// Inspect and edit persistent memory (~/.apex/memory.json)
    Memory {
        #[command(subcommand)]
        action: MemoryAction,
    },
    /// Manage saved sessions
    Session {
        #[command(subcommand)]
        action: SessionAction,
    },
}

#[derive(Subcommand, Debug)]
enum MemoryAction {
    /// List stored facts
    List,
    /// Add a fact: `apex-rs memory add "fact" "tag1,tag2"`
    Add {
        fact: String,
        #[arg(default_value = "")]
        relevance: String,
    },
    /// Search facts by substring (case-insensitive)
    Search { query: String },
    /// Remove a fact by index
    Remove { index: usize },
    /// Delete all facts
    Clear,
}

#[derive(Subcommand, Debug)]
enum SessionAction {
    /// List saved sessions (name, timestamp, model, messages)
    List,
    /// Print a saved session as JSON
    Show { id: String },
    /// Save the current (empty) history under this name
    Save { name: String },
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
            // Token accounting goes to stderr so stdout stays script-friendly.
            if agent.usage.total_tokens > 0 {
                eprintln!("[usage] {} tokens, cost ${:.6}",
                    agent.usage.total_tokens,
                    agent.cost.get_session_cost()["total_cost"].as_f64().unwrap_or(0.0));
            }
        }
        Some(Commands::Chat { session }) => {
            let mut agent = agent::Agent::new(config);
            if let Some(id) = &session { let _ = agent.load_session(id); }
            agent.run_repl().await;
            if let Some(id) = &session { let _ = agent.save_session(id); }
            if agent.usage.total_tokens > 0 {
                eprintln!("{}", agent.cost_report());
            }
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
                for p in &ps {
                    if p.manifest.is_none() {
                        println!("{} (no manifest)", p.name);
                        continue;
                    }
                    let version = p.version();
                    let version = if version.is_empty() { String::new() } else { format!(" v{version}") };
                    let state = if p.enabled() { "" } else { " [disabled]" };
                    let desc = p.description();
                    println!("{}{}{}{}", p.name, version, state, if desc.is_empty() { String::new() } else { format!(" — {desc}") });
                    for t in p.tools() {
                        println!("  - {} ({})", t.name, plugins::tool_full_name(&p.name, &t.name));
                    }
                }
            }
        }
        Some(Commands::Cost) => {
            // No chat happened in this process: report an empty session, like Python's `/cost` with no usage.
            let agent = agent::Agent::new(config);
            println!("{}", agent.cost_report());
        }
        Some(Commands::Memory { action }) => {
            let mut mem = memory::Memory::new();
            match action {
                MemoryAction::List => println!("{}", memory::list_facts_report(&mem)),
                MemoryAction::Add { fact, relevance } => {
                    let tags: Vec<String> = relevance
                        .split(',')
                        .map(|s| s.trim().to_string())
                        .filter(|s| !s.is_empty())
                        .collect();
                    mem.add(&fact, tags);
                    println!("Added to memory: {fact}");
                }
                MemoryAction::Search { query } => {
                    let results = mem.search(&query);
                    if results.is_empty() {
                        println!("No matching facts found");
                    } else {
                        println!("Search results:");
                        for f in results {
                            println!("  {}", f["fact"].as_str().unwrap_or(""));
                        }
                    }
                }
                MemoryAction::Remove { index } => {
                    if mem.remove(index) {
                        println!("Removed fact {index}");
                    } else {
                        println!("Index out of range");
                    }
                }
                MemoryAction::Clear => {
                    mem.clear();
                    println!("Memory cleared");
                }
            }
        }
        Some(Commands::CallTool { name, args }) => {
            let parsed: serde_json::Value = serde_json::from_str(&args).unwrap_or(serde_json::json!({}));
            println!("{}", tools::execute_tool(&name, &parsed, &config.cwd));
        }
        Some(Commands::Session { action }) => match action {
            SessionAction::List => {
                for s in share::list_sessions() {
                    println!(
                        "{}\t{}\t{}\t{} msgs",
                        s["name"].as_str().unwrap_or("?"),
                        s["timestamp"].as_str().unwrap_or("?"),
                        s["model"].as_str().unwrap_or("?"),
                        s["history_len"].as_u64().unwrap_or(0),
                    );
                }
            }
            SessionAction::Show { id } => match share::load_session(&id) {
                Some(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap_or_default()),
                None => eprintln!("session not found: {id}"),
            },
            SessionAction::Save { name } => {
                let cwd = config.cwd.to_string_lossy().to_string();
                match share::save_session(&name, &config.model, &cwd, &[]) {
                    Some(p) => println!("Saved {}", p.display()),
                    None => eprintln!("failed to save session"),
                }
            }
        },
        None => {
            println!("APEX (Rust) — type 'apex-rs --help'");
        }
    }
}