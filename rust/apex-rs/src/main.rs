mod agent;
mod config;
mod formatter;
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
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let config = Config::from_env();
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
        None => {
            println!("APEX (Rust) — type 'apex-rs --help'");
        }
    }
}