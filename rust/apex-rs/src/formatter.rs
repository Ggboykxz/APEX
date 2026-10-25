use std::path::Path;
use std::process::Command;

/// Run a known formatter on a file if available. Returns a status message.
pub fn format_file(path: &Path) -> String {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();
    let (cmd, args): (&str, Vec<&str>) = match ext.as_str() {
        "rs" => ("rustfmt", vec![]),
        "py" => ("ruff", vec!["format"]),
        "js" | "ts" | "jsx" | "tsx" => ("prettier", vec!["--write"]),
        "go" => ("gofmt", vec!["-w"]),
        "c" | "cpp" | "h" | "hpp" => ("clang-format", vec!["-i"]),
        _ => return "No formatter for this file type".to_string(),
    };

    if which(cmd).is_none() {
        return format!("Formatter '{cmd}' not installed; skipped");
    }

    let mut c = Command::new(cmd);
    c.args(&args).arg(path);
    match c.output() {
        Ok(o) if o.status.success() => format!("Formatted with {cmd}"),
        Ok(o) => format!(
            "Formatter {cmd} failed: {}",
            String::from_utf8_lossy(&o.stderr)
        ),
        Err(e) => format!("ERROR: {e}"),
    }
}

fn which(name: &str) -> Option<std::path::PathBuf> {
    let path = std::env::var("PATH").unwrap_or_default();
    for dir in path.split(':') {
        let p = std::path::Path::new(dir).join(name);
        if p.is_file() {
            return Some(p);
        }
    }
    None
}
