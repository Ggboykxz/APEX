//! Codegen tools — port of `apex/tools.py` code generation operations.
//!
//! Implements: generate_tests, inline_edit, apply_code_action.
//!
//! `generate_tests` reuses `skills::CodeAnalyzer` (already ported) to analyze
//! a file and emit pytest- or Jest-style test stubs.

use serde_json::Value;
use std::fs;
use std::path::Path;

use crate::skills::CodeAnalyzer;

/// `generate_tests` — Generate unit tests for a file or function.
/// Mirrors Python's `_execute_generate_tests`.
pub fn generate_tests(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let framework = args
        .get("framework")
        .and_then(|v| v.as_str())
        .unwrap_or("pytest");

    let ca = CodeAnalyzer::new(cwd);
    let analysis = ca.analyze_file(path);

    if analysis.get("error").and_then(|v| v.as_str()).is_some() {
        return analysis["error"]
            .as_str()
            .unwrap_or("File not found")
            .to_string();
    }

    let funcs = analysis
        .get("functions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    if funcs.is_empty() {
        return "No functions found to generate tests for.".to_string();
    }

    let replaced = path.replace(std::path::MAIN_SEPARATOR, ".");
    let module_path = replaced.rsplit(".py").next().unwrap_or(path);

    let mut lines: Vec<String> = Vec::new();

    if framework == "pytest" {
        lines.push(format!("\"\"\"Tests for {module_path}\"\"\""));
        lines.push(String::new());
        lines.push("import pytest".to_string());
        lines.push(format!("from {module_path} import *"));
        lines.push(String::new());
        for f in funcs.iter().take(5) {
            let name = f.get("name").and_then(|v| v.as_str()).unwrap_or("unknown");
            lines.push(format!("def test_{name}():"));
            lines.push("    pass".to_string());
        }
    } else {
        lines.push(format!("// Tests for {path}"));
        lines.push(String::new());
        for f in funcs.iter().take(5) {
            let name = f.get("name").and_then(|v| v.as_str()).unwrap_or("unknown");
            lines.push(format!("describe('{name}', () => {{"));
            lines.push("  it('should work', () => {".to_string());
            lines.push("    // implement test".to_string());
            lines.push("  });".to_string());
            lines.push("});".to_string());
        }
    }

    lines.join("\n")
}

/// `inline_edit` — Replace N lines starting at `line` with `content`.
/// Mirrors Python's `_execute_inline_edit`.
pub fn inline_edit(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let line = args.get("line").and_then(|v| v.as_i64()).unwrap_or(1) as usize;
    let content = args.get("content").and_then(|v| v.as_str()).unwrap_or("");
    let replace = args.get("replace").and_then(|v| v.as_i64()).unwrap_or(1) as usize;

    let full = if Path::new(path).is_absolute() {
        Path::new(path).to_path_buf()
    } else {
        cwd.join(path)
    };

    if !full.exists() {
        return format!("ERROR: File not found: {}", full.display());
    }

    let text = match fs::read_to_string(&full) {
        Ok(t) => t,
        Err(e) => return format!("ERROR: {e}"),
    };

    let lines: Vec<String> = text.lines().map(|s| s.to_string()).collect();
    let start = line.saturating_sub(1);
    let end = (start + replace).min(lines.len());
    let mut new_lines: Vec<String> = lines[..start].to_vec();
    new_lines.push(content.to_string());
    new_lines.extend(lines[end..].iter().cloned());

    match fs::write(&full, new_lines.join("\n")) {
        Ok(_) => format!("SUCCESS: Edited {} at line {}", full.display(), line),
        Err(e) => format!("ERROR: {e}"),
    }
}

/// `apply_code_action` — Apply a suggested code action/fix.
/// Mirrors Python's `_execute_apply_code_action` (LSP code actions not yet
/// fully integrated in the Rust port).
pub fn apply_code_action(args: &Value) -> String {
    let action_id = args.get("action_id").and_then(|v| v.as_str()).unwrap_or("");
    format!("Applying code action: {action_id}\n\n(Note: LSP code actions require full LSP integration)")
}
