mod agent;
mod api_key;
mod codegen;
mod config;
mod context;
mod cost;
mod formatter;
mod github;
mod hooks;
mod jsonrpc;
mod lsp;
mod mcp_client;
mod memory;
mod patch;
mod permission;
mod plugins;
mod rate_limiter;
mod server;
mod session_crypto;
mod share;
mod shell_security;
mod skills;
mod task_queue;
mod tools;
mod web;

use clap::{Parser, Subcommand};
use config::Config;
use std::io::Write;
use std::path::Path;

#[derive(Parser, Debug)]
#[command(name = "apex-rs", version, about = "APEX backend rewritten in Rust")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// One-shot prompt
    Run {
        prompt: String,
        #[arg(short, long)]
        session: Option<String>,
    },
    /// Interactive REPL
    Chat {
        #[arg(short, long)]
        session: Option<String>,
    },
    /// Start HTTP server
    Serve {
        #[arg(short, long, default_value = "8765")]
        port: u16,
    },
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
    /// Inspect shell-command safety (shell_security parity)
    Security {
        #[command(subcommand)]
        action: SecurityAction,
    },
    /// Repository context: repo map, git info, stats, ctags, tree, glob
    Context {
        #[command(subcommand)]
        action: ContextAction,
    },
    /// GitHub: install/run parity plus issue/PR operations and automation flows
    Github {
        #[command(subcommand)]
        action: Option<GithubAction>,
    },
    /// Manage skills (`.apex/skills/*.md`)
    Skill {
        #[command(subcommand)]
        action: SkillAction,
    },
    /// Manage HTTP API keys (`~/.apex/api_keys.json`)
    Key {
        #[command(subcommand)]
        action: KeyAction,
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
    /// Print the prompt context for a project (last 5 relevant facts)
    Context { project: String },
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

#[derive(Subcommand, Debug)]
enum SecurityAction {
    /// Analyze a command and print the verdict as JSON
    Check { command: String },
    /// List commands allowed without confirmation
    Allowed,
}

#[derive(Subcommand, Debug)]
enum ContextAction {
    /// Print the repository map (directories, source/config/doc files, git info)
    RepoMap {
        #[arg(default_value = ".")]
        path: String,
    },
    /// Print git branch and change count (empty when not a repository)
    Git {
        #[arg(default_value = ".")]
        path: String,
    },
    /// Print per-language file statistics as JSON
    Stats {
        #[arg(default_value = ".")]
        path: String,
    },
    /// List the first code files tracked by git (ctags input)
    Ctags {
        #[arg(default_value = ".")]
        path: String,
    },
    /// Print an ASCII file tree (directories first, dotfiles skipped)
    Tree {
        #[arg(default_value = ".")]
        path: String,
        #[arg(short, long, default_value_t = 3)]
        depth: usize,
    },
    /// List files and directories matching a glob pattern (e.g. `**/*.py`)
    Glob {
        pattern: String,
        #[arg(default_value = ".")]
        path: String,
    },
}

#[derive(Subcommand, Debug)]
enum GithubAction {
    /// Install the GitHub agent in the repository (Python parity: info lines only)
    Install,
    /// Run the GitHub agent (typically in CI): count open issues and PRs
    Run,
    /// Show an issue as JSON
    Issue { number: i64 },
    /// Close an issue
    IssueClose { number: i64 },
    /// Show a pull request as JSON
    Pr { number: i64 },
    /// Merge a pull request
    PrMerge {
        number: i64,
        #[arg(short, long, default_value = "squash")]
        method: String,
    },
    /// Automated issue/PR flows (see `apex-rs github automate --help`)
    Automate {
        #[command(subcommand)]
        flow: AutomateFlow,
    },
}

#[derive(Subcommand, Debug)]
enum AutomateFlow {
    /// Create a branch and a pull request for it
    CreatePr {
        #[arg(long)]
        title: String,
        #[arg(long, default_value = "")]
        body: String,
        #[arg(long)]
        branch: String,
        #[arg(long, default_value = "main")]
        base: String,
    },
    /// Create a PR describing the given file changes
    Changes { files: Vec<String> },
    /// Create a bug issue from an error message
    Issue {
        #[arg(long)]
        error: String,
        #[arg(long)]
        file: String,
    },
    /// List open issues by label (all open issues without `--label`)
    List {
        #[arg(long, default_value = "")]
        label: String,
    },
    /// List issues labelled `todo`
    Todos,
    /// Count merged PRs
    CloseCompleted,
}

#[derive(Subcommand, Debug)]
enum SkillAction {
    /// List known skills (project and home `.apex/skills/`)
    List,
    /// Add a skill: `apex-rs skill add <name> <description> <prompt>`
    Add {
        name: String,
        description: String,
        prompt: String,
    },
    /// Remove a skill by name
    Remove { name: String },
}

#[derive(Subcommand, Debug)]
enum KeyAction {
    /// Create a key and print it once (the plaintext is never stored)
    Create {
        name: String,
        /// Expiry in seconds from now (0 or omitted: no expiry)
        #[arg(long, default_value_t = 0)]
        expires_in: i64,
    },
    /// List keys (id, name, state, request count)
    List,
    /// Revoke a key by id (keeps the record, rejects future requests)
    Revoke { key_id: String },
    /// Delete a key by id
    Delete { key_id: String },
}

fn load_mcp_servers() {
    // Run discovery on a dedicated thread: `main` is itself async, so creating
    // and blocking on another runtime from there would panic.
    let _ = std::thread::spawn(|| {
        let base = config::home_dir()
            .unwrap_or_default()
            .join(".apex")
            .join("mcp.json");
        if !base.exists() {
            return;
        }
        let data = match std::fs::read_to_string(&base) {
            Ok(d) => d,
            Err(_) => return,
        };
        let v: serde_json::Value = match serde_json::from_str(&data) {
            Ok(v) => v,
            Err(_) => return,
        };
        let servers = v
            .get("mcpServers")
            .or_else(|| v.get("mcp_servers"))
            .and_then(|x| x.as_object());
        let Some(servers) = servers else { return };
        let mut mgr = crate::mcp_client::McpManager::new();
        for (name, cfg) in servers {
            let command = cfg
                .get("command")
                .and_then(|x| x.as_str())
                .unwrap_or("")
                .to_string();
            let args: Vec<String> = cfg
                .get("args")
                .and_then(|x| x.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|x| x.as_str().map(String::from))
                        .collect()
                })
                .unwrap_or_default();
            if !command.is_empty() {
                mgr.add_server(name.clone(), command, args);
            }
        }
        let rt = match tokio::runtime::Runtime::new() {
            Ok(r) => r,
            Err(_) => return,
        };
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
            if let Some(id) = &session {
                let _ = agent.load_session(id);
            }
            match agent.chat(&prompt).await {
                Ok(resp) => {
                    println!("{resp}");
                    let _ = std::io::stdout().flush();
                }
                Err(e) => eprintln!("ERROR: {e}"),
            }
            if let Some(id) = &session {
                let _ = agent.save_session(id);
            }
            // Token accounting goes to stderr so stdout stays script-friendly.
            if agent.usage.total_tokens > 0 {
                eprintln!(
                    "[usage] {} tokens, cost ${:.6}",
                    agent.usage.total_tokens,
                    agent.cost.get_session_cost()["total_cost"]
                        .as_f64()
                        .unwrap_or(0.0)
                );
            }
        }
        Some(Commands::Chat { session }) => {
            let mut agent = agent::Agent::new(config);
            if let Some(id) = &session {
                let _ = agent.load_session(id);
            }
            agent.run_repl().await;
            if let Some(id) = &session {
                let _ = agent.save_session(id);
            }
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
                    let version = if version.is_empty() {
                        String::new()
                    } else {
                        format!(" v{version}")
                    };
                    let state = if p.enabled() { "" } else { " [disabled]" };
                    let desc = p.description();
                    println!(
                        "{}{}{}{}",
                        p.name,
                        version,
                        state,
                        if desc.is_empty() {
                            String::new()
                        } else {
                            format!(" — {desc}")
                        }
                    );
                    for t in p.tools() {
                        println!(
                            "  - {} ({})",
                            t.name,
                            plugins::tool_full_name(&p.name, &t.name)
                        );
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
                MemoryAction::Context { project } => {
                    let context = mem.get_context_for_prompt(&project);
                    if context.is_empty() {
                        println!("No relevant memory facts");
                    } else {
                        println!("{context}");
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
            let parsed: serde_json::Value =
                serde_json::from_str(&args).unwrap_or(serde_json::json!({}));
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
        Some(Commands::Security { action }) => match action {
            SecurityAction::Check { command } => {
                let analysis = shell_security::SHELL_ANALYZER.analyze(&command);
                let mut verdict = analysis.to_json();
                verdict["allowed"] =
                    serde_json::json!(shell_security::SHELL_ANALYZER.is_safe(&command));
                println!(
                    "{}",
                    serde_json::to_string_pretty(&verdict).unwrap_or_default()
                );
            }
            SecurityAction::Allowed => {
                for cmd in shell_security::SHELL_ANALYZER.get_allowed_commands() {
                    println!("{cmd}");
                }
            }
        },
        Some(Commands::Context { action }) => match action {
            ContextAction::RepoMap { path } => {
                println!("{}", context::get_repo_map(Path::new(&path)));
            }
            ContextAction::Git { path } => {
                let info = context::get_git_info(Path::new(&path));
                if info.is_empty() {
                    println!("(not a git repository)");
                } else {
                    println!("{info}");
                }
            }
            ContextAction::Stats { path } => {
                let stats = context::get_language_stats(Path::new(&path));
                println!(
                    "{}",
                    serde_json::to_string_pretty(&stats).unwrap_or_default()
                );
            }
            ContextAction::Ctags { path } => {
                println!("{}", context::generate_ctags(Path::new(&path)));
            }
            ContextAction::Tree { path, depth } => {
                match context::file_tree(Path::new(&path), depth) {
                    Ok(tree) => println!("{tree}"),
                    Err(e) => {
                        eprintln!("{e}");
                        std::process::exit(1);
                    }
                }
            }
            ContextAction::Glob { pattern, path } => {
                match context::glob_search(Path::new(&path), &pattern) {
                    Ok(matches) => {
                        for m in matches {
                            println!("{m}");
                        }
                    }
                    Err(e) => {
                        eprintln!("{e}");
                        std::process::exit(1);
                    }
                }
            }
        },
        Some(Commands::Github { action }) => match action {
            None => {
                // Python's `_cmd_github` prints its own usage for a missing subcommand.
                println!(
                    "Usage: apex-rs github install|run|issue|issue-close|pr|pr-merge|automate"
                );
                println!("  install        - Install GitHub agent in repository");
                println!("  run            - Run GitHub agent (typically in CI)");
                println!("  issue <N>      - Show an issue as JSON");
                println!("  issue-close <N> - Close an issue");
                println!("  pr <N>         - Show a pull request as JSON");
                println!("  pr-merge <N>   - Merge a pull request (-m method, default squash)");
                println!("  automate       - Automated issue/PR flows (see --help)");
            }
            Some(GithubAction::Install) => {
                // Python parity: three info lines, no side effects.
                println!("Installing GitHub agent...");
                println!("This sets up APEX as a GitHub Actions workflow.");
                println!("See: https://github.com/Ggboykxz/APEX");
            }
            Some(GithubAction::Run) => {
                println!("Running GitHub agent...");
                let automation = github::GitHubAutomation::new("", &config.cwd);
                // A failed API call counts as empty, exactly like Python.
                let issues = automation.client.list_issues("open", "");
                let prs = automation.client.list_prs("open");
                println!("Found {} issues and {} PRs", issues.len(), prs.len());
            }
            Some(GithubAction::Issue { number }) => {
                let automation = github::GitHubAutomation::new("", &config.cwd);
                match automation.client.get_issue(number) {
                    Some(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap_or_default()),
                    None => {
                        eprintln!("ERROR: Issue {number} not found");
                        std::process::exit(1);
                    }
                }
            }
            Some(GithubAction::IssueClose { number }) => {
                let automation = github::GitHubAutomation::new("", &config.cwd);
                if automation.client.close_issue(number) {
                    println!("Closed issue {number}");
                } else {
                    eprintln!("ERROR: Failed to close issue {number}");
                    std::process::exit(1);
                }
            }
            Some(GithubAction::Pr { number }) => {
                let automation = github::GitHubAutomation::new("", &config.cwd);
                match automation.client.get_pr(number) {
                    Some(v) => println!("{}", serde_json::to_string_pretty(&v).unwrap_or_default()),
                    None => {
                        eprintln!("ERROR: Pull request {number} not found");
                        std::process::exit(1);
                    }
                }
            }
            Some(GithubAction::PrMerge { number, method }) => {
                let automation = github::GitHubAutomation::new("", &config.cwd);
                if automation.client.merge_pr(number, &method) {
                    println!("Merged PR {number}");
                } else {
                    eprintln!("ERROR: Failed to merge PR {number}");
                    std::process::exit(1);
                }
            }
            Some(GithubAction::Automate { flow }) => {
                let automation = github::GitHubAutomation::new("", &config.cwd);
                match flow {
                    AutomateFlow::CreatePr {
                        title,
                        body,
                        branch,
                        base,
                    } => {
                        require_repo(&automation);
                        match automation.auto_create_pr(&config.cwd, &title, &body, &branch, &base)
                        {
                            Some(v) => print_created(&v, "PR created."),
                            None => {
                                eprintln!("ERROR: PR creation failed");
                                std::process::exit(1);
                            }
                        }
                    }
                    AutomateFlow::Changes { files } => {
                        require_repo(&automation);
                        match automation.create_pr_for_changes(&config.cwd, &files) {
                            Some(v) => print_created(&v, "PR created."),
                            None => {
                                eprintln!("ERROR: PR creation failed");
                                std::process::exit(1);
                            }
                        }
                    }
                    AutomateFlow::Issue { error, file } => {
                        require_repo(&automation);
                        match automation.create_issue_from_error(&error, &file) {
                            Some(v) => print_created(&v, "Issue created."),
                            None => {
                                eprintln!("ERROR: Issue creation failed");
                                std::process::exit(1);
                            }
                        }
                    }
                    AutomateFlow::List { label } => {
                        let issues = automation.list_issues_by_label(&label);
                        if label.is_empty() {
                            println!("Open issues:");
                        } else {
                            println!("Open issues for label '{label}':");
                        }
                        print_issue_lines(&issues);
                    }
                    AutomateFlow::Todos => {
                        println!("Todo issues:");
                        print_issue_lines(&automation.get_issue_todos());
                    }
                    AutomateFlow::CloseCompleted => {
                        // Python's `close_completed_prs` counts merged PRs; it does not close.
                        println!("{} merged PR(s)", automation.close_completed_prs());
                    }
                }
            }
        },
        Some(Commands::Skill { action }) => match action {
            SkillAction::List => {
                let sm = skills::SkillManager::new(&config.cwd);
                let all = sm.list_skills();
                if all.is_empty() {
                    println!("No skills found (.apex/skills/, ~/.apex/skills/)");
                } else {
                    for (name, description) in all {
                        println!("{name}: {description}");
                    }
                }
            }
            SkillAction::Add {
                name,
                description,
                prompt,
            } => {
                if !skills::valid_skill_name(&name) {
                    eprintln!("ERROR: Invalid skill name: {name}");
                    std::process::exit(1);
                }
                let mut sm = skills::SkillManager::new(&config.cwd);
                sm.add(&name, &description, &prompt);
                let skill = sm.get(&name).expect("skill was just added");
                match skills::save_skill_file(&config.cwd, skill) {
                    Ok(path) => println!("Added skill: {name} ({})", path.display()),
                    Err(e) => {
                        eprintln!("ERROR: {e}");
                        std::process::exit(1);
                    }
                }
            }
            SkillAction::Remove { name } => {
                let mut sm = skills::SkillManager::new(&config.cwd);
                if !sm.remove(&name) {
                    eprintln!("ERROR: Skill not found: {name}");
                    std::process::exit(1);
                }
                skills::remove_skill_file(&config.cwd, &name);
                println!("Removed skill: {name}");
            }
        },
        Some(Commands::Key { action }) => {
            let manager = api_key::KeyManager::default_store();
            match action {
                KeyAction::Create { name, expires_in } => {
                    let (key, info) = manager.create_key(&name, Some(expires_in));
                    println!("Created key {}: {}", info.key_id, info.name);
                    println!("{key}");
                }
                KeyAction::List => {
                    let keys = manager.list_keys();
                    if keys.is_empty() {
                        println!("No API keys");
                    } else {
                        for info in keys {
                            let state = if info.is_active { "active" } else { "revoked" };
                            println!(
                                "  {} - {} [{}] requests={}",
                                info.key_id, info.name, state, info.request_count
                            );
                        }
                    }
                }
                KeyAction::Revoke { key_id } => {
                    if !manager.revoke_key(&key_id) {
                        eprintln!("ERROR: Key not found: {key_id}");
                        std::process::exit(1);
                    }
                    println!("Revoked key {key_id}");
                }
                KeyAction::Delete { key_id } => {
                    if !manager.delete_key(&key_id) {
                        eprintln!("ERROR: Key not found: {key_id}");
                        std::process::exit(1);
                    }
                    println!("Deleted key {key_id}");
                }
            }
        }
        None => {
            println!("APEX (Rust) — type 'apex-rs --help'");
        }
    }
}

/// Exit with a clear error when no repository can be detected for automation.
fn require_repo(automation: &github::GitHubAutomation) {
    if automation.repo.is_none() {
        eprintln!("ERROR: No GitHub repository detected (run inside a repo with an origin remote)");
        std::process::exit(1);
    }
}

/// Print the `html_url` of a created issue/PR, or a fallback line.
fn print_created(v: &serde_json::Value, fallback: &str) {
    match v.get("html_url").and_then(serde_json::Value::as_str) {
        Some(url) => println!("{url}"),
        None => println!("{fallback}"),
    }
}

/// `  #<number> - <title>` lines, or `No issues found` for an empty list.
fn print_issue_lines(issues: &[serde_json::Value]) {
    if issues.is_empty() {
        println!("No issues found");
        return;
    }
    for issue in issues {
        let number = issue
            .get("number")
            .and_then(serde_json::Value::as_i64)
            .unwrap_or(-1);
        let title = issue
            .get("title")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("");
        println!("  #{number} - {title}");
    }
}
