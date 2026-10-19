//! Persistent memory — port of `apex/memory.py`.
//!
//! Facts learned across sessions are stored as a JSON array in
//! `~/.apex/memory.json`:
//!
//! ```json
//! [{"fact": "…", "added": "2026-10-19T07:12:38.134721", "relevance": ["apex"]}]
//! ```
//!
//! Same file format as Python so both implementations share one memory.

use crate::cost::now_iso8601_micros;
use serde_json::{json, Value};
use std::path::PathBuf;

pub struct Memory {
    path: PathBuf,
    facts: Vec<Value>,
}

impl Default for Memory {
    fn default() -> Self {
        Self::new()
    }
}

impl Memory {
    pub fn new() -> Self {
        Self::at(memory_file())
    }

    /// Memory backed by an explicit file (used by tests).
    pub fn at(path: PathBuf) -> Self {
        let facts = std::fs::read_to_string(&path)
            .ok()
            .and_then(|data| serde_json::from_str::<Vec<Value>>(&data).ok())
            .unwrap_or_default();
        Self { path, facts }
    }

    fn save(&self) {
        if let Some(parent) = self.path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let data = serde_json::to_string_pretty(&self.facts).unwrap_or_else(|_| "[]".to_string());
        let _ = std::fs::write(&self.path, data);
    }

    pub fn add(&mut self, fact: &str, relevance: Vec<String>) {
        self.facts.push(json!({
            "fact": fact,
            "added": now_iso8601_micros(),
            "relevance": relevance,
        }));
        self.save();
    }

    pub fn get_all(&self) -> Vec<Value> {
        self.facts.clone()
    }

    pub fn get_relevant(&self, keywords: &[String]) -> Vec<Value> {
        self.facts
            .iter()
            .filter(|f| {
                f.get("relevance")
                    .and_then(|r| r.as_array())
                    .map(|rels| {
                        rels.iter().any(|r| {
                            r.as_str()
                                .map(|s| keywords.iter().any(|k| k == s))
                                .unwrap_or(false)
                        })
                    })
                    .unwrap_or(false)
            })
            .cloned()
            .collect()
    }

    /// Last 5 relevant facts, formatted for a prompt (empty string when none).
    pub fn get_context_for_prompt(&self, project_name: &str) -> String {
        let keywords: Vec<String> = if project_name.is_empty() {
            Vec::new()
        } else {
            vec![project_name.to_string()]
        };
        let relevant = self.get_relevant(&keywords);
        if relevant.is_empty() {
            return String::new();
        }
        let mut lines = vec!["[MEMORY - Relevant facts from previous sessions]".to_string()];
        let start = relevant.len().saturating_sub(5);
        for fact in &relevant[start..] {
            if let Some(text) = fact.get("fact").and_then(|f| f.as_str()) {
                lines.push(format!("- {text}"));
            }
        }
        lines.join("\n")
    }

    pub fn clear(&mut self) {
        self.facts.clear();
        self.save();
    }

    /// Remove a fact by index; returns false when out of range (Python parity).
    pub fn remove(&mut self, index: usize) -> bool {
        if index < self.facts.len() {
            self.facts.remove(index);
            self.save();
            return true;
        }
        false
    }

    pub fn list_facts(&self) -> Vec<String> {
        self.facts
            .iter()
            .filter_map(|f| f.get("fact").and_then(|v| v.as_str()).map(|s| s.to_string()))
            .collect()
    }

    pub fn search(&self, query: &str) -> Vec<Value> {
        let query_lower = query.to_lowercase();
        self.facts
            .iter()
            .filter(|f| {
                f.get("fact")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_lowercase().contains(&query_lower))
                    .unwrap_or(false)
            })
            .cloned()
            .collect()
    }

    pub fn path(&self) -> &PathBuf {
        &self.path
    }
}

/// `~/.apex/memory.json` (override with `APEX_MEMORY_FILE`, used by tests).
pub fn memory_file() -> PathBuf {
    if let Ok(p) = std::env::var("APEX_MEMORY_FILE") {
        if !p.is_empty() {
            return PathBuf::from(p);
        }
    }
    dirs::home_dir().unwrap_or_default().join(".apex").join("memory.json")
}

/// Handle the REPL `/memory` slash command.
///
/// Python's parser (`arg.split(maxsplit=2)`) only accepts a single-word fact
/// (`/memory add hello a,b`); here everything up to an optional `--tags a,b`
/// is the fact.
pub fn repl_command(arg: &str) -> String {
    let mut mem = Memory::new();
    repl_command_with(&mut mem, arg)
}

pub fn repl_command_with(mem: &mut Memory, arg: &str) -> String {
    let arg = arg.trim();
    if arg.is_empty() {
        return list_facts_report(mem);
    }
    let (sub, rest) = match arg.split_once(char::is_whitespace) {
        Some((s, r)) => (s, r.trim()),
        None => (arg, ""),
    };
    match sub {
        "add" => {
            if rest.is_empty() {
                return "Usage: /memory add <fact> [--tags a,b]".to_string();
            }
            let (fact, tags) = match rest.split_once("--tags") {
                Some((f, t)) => (f.trim(), t.trim()),
                None => (rest, ""),
            };
            let relevance: Vec<String> = tags
                .split(',')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();
            mem.add(fact, relevance);
            format!("Added to memory: {fact}")
        }
        "clear" => {
            mem.clear();
            "Memory cleared".to_string()
        }
        "search" => {
            if rest.is_empty() {
                return "Usage: /memory search <query>".to_string();
            }
            let results = mem.search(rest);
            if results.is_empty() {
                "No matching facts found".to_string()
            } else {
                let mut lines = vec!["Search results:".to_string()];
                for f in results {
                    lines.push(format!("  {}", f["fact"].as_str().unwrap_or("")));
                }
                lines.join("\n")
            }
        }
        "remove" => match rest.parse::<usize>() {
            Ok(idx) if mem.remove(idx) => format!("Removed fact {idx}"),
            Ok(_) => "Index out of range".to_string(),
            Err(_) => "Usage: /memory remove <index>".to_string(),
        },
        _ => "Usage: /memory [add <fact> [--tags a,b] | search <query> | remove <index> | clear]"
            .to_string(),
    }
}

/// Numbered fact listing shared by the REPL and the CLI.
pub fn list_facts_report(mem: &Memory) -> String {
    let facts = mem.get_all();
    if facts.is_empty() {
        return "No memory facts stored".to_string();
    }
    let mut lines = vec!["Memory facts:".to_string()];
    for (i, f) in facts.iter().enumerate() {
        let relevance: Vec<String> = f
            .get("relevance")
            .and_then(|r| r.as_array())
            .map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect())
            .unwrap_or_default();
        lines.push(format!(
            "  {i}: {} [relevance: {}]",
            f["fact"].as_str().unwrap_or(""),
            relevance.join(", ")
        ));
    }
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn add_list_search_roundtrip() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("memory.json");
        let mut m = Memory::at(path.clone());

        m.add("APEX uses Rust", vec!["apex".to_string()]);
        m.add("Okiba uses Flutter", vec!["okiba".to_string()]);

        assert_eq!(m.list_facts(), vec!["APEX uses Rust", "Okiba uses Flutter"]);
        assert_eq!(m.search("rust").len(), 1);
        assert_eq!(m.search("RUST").len(), 1, "search is case-insensitive");
        assert_eq!(m.search("nothing").len(), 0);

        // Persisted in the same shape as Python.
        let raw: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(raw[0]["fact"], "APEX uses Rust");
        assert_eq!(raw[0]["relevance"][0], "apex");
        assert!(raw[0]["added"].as_str().unwrap().len() == 26);

        // And re-loaded by a fresh instance (shared file with Python).
        let m2 = Memory::at(path);
        assert_eq!(m2.get_all().len(), 2);
    }

    #[test]
    fn relevance_and_prompt_context() {
        let dir = tempdir().unwrap();
        let mut m = Memory::at(dir.path().join("memory.json"));
        m.add("fact about apex", vec!["apex".to_string()]);
        m.add("fact about other", vec!["other".to_string()]);

        assert_eq!(m.get_relevant(&["apex".to_string()]).len(), 1);
        assert_eq!(m.get_relevant(&[]).len(), 0);

        let ctx = m.get_context_for_prompt("apex");
        assert!(ctx.starts_with("[MEMORY - Relevant facts from previous sessions]"));
        assert!(ctx.contains("- fact about apex"));
        assert!(!ctx.contains("fact about other"));
        assert_eq!(m.get_context_for_prompt("unknown"), "");
        assert_eq!(m.get_context_for_prompt(""), "");
    }

    #[test]
    fn remove_and_clear() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("memory.json");
        let mut m = Memory::at(path.clone());
        m.add("a", vec![]);
        m.add("b", vec![]);

        assert!(m.remove(0));
        assert!(!m.remove(5));
        assert_eq!(m.list_facts(), vec!["b"]);

        m.clear();
        assert!(m.list_facts().is_empty());
        assert_eq!(Memory::at(path).get_all().len(), 0);
    }

    #[test]
    fn corrupt_file_is_treated_as_empty() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("memory.json");
        std::fs::write(&path, "{not json").unwrap();
        let m = Memory::at(path);
        assert!(m.list_facts().is_empty());
    }

    #[test]
    fn prompt_context_keeps_last_five() {
        let dir = tempdir().unwrap();
        let mut m = Memory::at(dir.path().join("memory.json"));
        for i in 0..7 {
            m.add(&format!("fact {i}"), vec!["p".to_string()]);
        }
        let ctx = m.get_context_for_prompt("p");
        assert!(ctx.contains("- fact 6"));
        assert!(!ctx.contains("- fact 1\n"), "only the last five are kept: {ctx}");
        assert_eq!(ctx.lines().count(), 6);
    }

    #[test]
    fn repl_commands() {
        let dir = tempdir().unwrap();
        let mut m = Memory::at(dir.path().join("memory.json"));

        assert_eq!(repl_command_with(&mut m, ""), "No memory facts stored");
        assert_eq!(
            repl_command_with(&mut m, "add my multi word fact --tags apex,rust"),
            "Added to memory: my multi word fact"
        );
        assert_eq!(
            repl_command_with(&mut m, "add plain fact"),
            "Added to memory: plain fact"
        );
        assert_eq!(m.get_all().len(), 2);
        assert_eq!(m.get_all()[0]["relevance"], json!(["apex", "rust"]));
        assert_eq!(m.get_all()[1]["relevance"], json!([]));

        let listing = repl_command_with(&mut m, "");
        assert!(listing.starts_with("Memory facts:\n"), "got {listing}");
        assert!(listing.contains("0: my multi word fact [relevance: apex, rust]"));
        assert!(listing.contains("1: plain fact [relevance: ]"));

        let found = repl_command_with(&mut m, "search multi");
        assert!(found.starts_with("Search results:"));
        assert!(found.contains("my multi word fact"));
        assert_eq!(repl_command_with(&mut m, "search missing"), "No matching facts found");
        assert_eq!(repl_command_with(&mut m, "search"), "Usage: /memory search <query>");
        assert_eq!(repl_command_with(&mut m, "add"), "Usage: /memory add <fact> [--tags a,b]");

        assert_eq!(repl_command_with(&mut m, "remove 9"), "Index out of range");
        assert_eq!(repl_command_with(&mut m, "remove abc"), "Usage: /memory remove <index>");
        assert_eq!(repl_command_with(&mut m, "remove 0"), "Removed fact 0");
        assert_eq!(m.list_facts(), vec!["plain fact"]);

        assert_eq!(repl_command_with(&mut m, "clear"), "Memory cleared");
        assert_eq!(repl_command_with(&mut m, ""), "No memory facts stored");
        assert!(repl_command_with(&mut m, "bogus").starts_with("Usage: /memory"));
    }
}
