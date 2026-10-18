use clap::{Parser, Subcommand};
use serde::{Deserialize, Serialize};

#[derive(Parser, Debug)]
#[command(name = "apex-rs", version, about = "APEX backend (Rust spike)")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// One-shot prompt
    Run { prompt: String },
    /// List models
    Models,
    /// List tools
    Tools,
}

#[derive(Debug, Serialize, Deserialize)]
struct Message {
    role: String,
    content: String,
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Some(Commands::Run { prompt }) => {
            println!("APEX (Rust) received: {prompt}");
            println!("(agent loop not yet ported)");
        }
        Some(Commands::Models) => {
            println!("Models: (not yet ported)");
        }
        Some(Commands::Tools) => {
            println!("Tools: (not yet ported)");
        }
        None => {
            println!("APEX (Rust spike) — type 'apex-rs --help'");
        }
    }
}