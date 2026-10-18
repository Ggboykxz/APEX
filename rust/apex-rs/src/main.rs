mod agent;
mod config;
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
    Run { prompt: String },
    /// Interactive REPL
    Chat,
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
        Some(Commands::Run { prompt }) => {
            let mut agent = agent::Agent::new(config);
            match agent.chat(&prompt).await {
                Ok(resp) => { println!("{resp}"); let _ = std::io::stdout().flush(); }
                Err(e) => eprintln!("ERROR: {e}"),
            }
        }
        Some(Commands::Chat) => {
            let mut agent = agent::Agent::new(config);
            agent.run_repl();
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