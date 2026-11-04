//! Mention system — port of `apex/mentions.py`.
//!
//! OpenCode-style `@mention` handling: `@file.py` (file mention) and
//! `@agent` (agent mention). Parses mentions out of free text, resolves file
//! paths relative to a working directory, and can inline mentioned file
//! content (capped at 5000 chars) back into a message.

use std::collections::{BTreeSet, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

/// A mention of a file in the text.
#[allow(dead_code)]
// wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileMention {
    pub path: String,
    pub start: usize,
    pub end: usize,
}

/// A mention of an agent in the text.
#[allow(dead_code)]
// wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgentMention {
    pub name: String,
    pub start: usize,
    pub end: usize,
}

/// Parses @mentions out of free text.
///
/// Matches `@mention` only when preceded by start-of-string or whitespace,
/// and also matches `@` inside a word when followed by something with a dot
/// (file extension), e.g. `see @src/main.py`.
#[allow(dead_code)] // wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
pub struct MentionParser {
    agent_names: HashSet<String>,
    cwd: PathBuf,
}

#[allow(dead_code)] // wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
impl MentionParser {
    /// Agent names recognized as agent mentions (lower-cased).
    const AGENT_NAMES: [&str; 11] = [
        "build",
        "plan",
        "planner",
        "reviewer",
        "shell",
        "general",
        "explore",
        "scout",
        "compaction",
        "title",
        "summary",
    ];

    pub fn new(cwd: impl AsRef<Path>) -> Self {
        Self {
            agent_names: Self::AGENT_NAMES.iter().map(|s| s.to_string()).collect(),
            cwd: cwd.as_ref().to_path_buf(),
        }
    }

    /// Parse text into file mentions and agent mentions.
    #[allow(clippy::invalid_regex)] // regex compiled at runtime; static macro unavailable in pinned regex version
    pub fn parse(&self, text: &str) -> (Vec<FileMention>, Vec<AgentMention>) {
        let mut file_mentions = Vec::new();
        let mut agent_mentions = Vec::new();
        let mut seen_agents = HashSet::new();
        let mut seen_positions = HashSet::new();

        // Collect all matches from both patterns.
        let mut matches: Vec<(String, usize)> = Vec::new();

        // Match @mention at start-of-string or after whitespace.
        // Rust regex has no lookbehind, so capture the optional preceding
        // whitespace in group 1 and adjust the @ position accordingly.
        // Python: (?:^|(?<=\s))@(\S+)
        let boundary_re = regex::Regex::new(r"(?:^|(\s))@(\S+)").unwrap();
        for cap in boundary_re.captures_iter(text) {
            let m0 = cap.get(0).unwrap();
            // group 2 is the name; group 1 is the preceding whitespace (if any)
            let name = cap.get(2).unwrap().as_str().to_string();
            let at_pos = m0.start() + if cap.get(1).is_some() { 1 } else { 0 };
            // Handle @@ cases: if name starts with @, strip it and adjust position.
            let (name, at_pos) = if let Some(stripped) = name.strip_prefix('@') {
                if stripped.is_empty() {
                    // bare @@ → skip
                    continue;
                }
                (stripped.to_string(), at_pos + 1)
            } else {
                (name, at_pos)
            };
            matches.push((name, at_pos));
        }

        // Match @ inside a word when followed by something with a dot.
        // Python: (?<=\S)@(\S+\.\S+)  ->  Rust: (\S)@(\S+\.\S+)
        let dot_re = regex::Regex::new(r"(\S)@(\S+\.\S+)").unwrap();
        for cap in dot_re.captures_iter(text) {
            let m0 = cap.get(0).unwrap();
            let name = cap.get(2).unwrap().as_str().to_string();
            let at_pos = m0.start() + 1; // skip the preceding non-space char
                                         // Skip if already covered by boundary pattern (dedup by @ position).
            if matches.iter().any(|m| m.1 == at_pos) {
                continue;
            }
            matches.push((name, at_pos));
        }

        for (name, at_pos) in matches {
            if seen_positions.contains(&at_pos) {
                continue;
            }
            seen_positions.insert(at_pos);

            let mention_start = at_pos;
            let mention_end = at_pos + 1 + name.len();

            let name_lower = name.to_lowercase();
            if self.agent_names.contains(&name_lower) {
                // Agent mention: only record once (dedup case-insensitively).
                if seen_agents.insert(name_lower.clone()) {
                    agent_mentions.push(AgentMention {
                        name: name_lower,
                        start: mention_start,
                        end: mention_end,
                    });
                }
                // Already-seen agent: skip entirely (not a file).
            } else {
                file_mentions.push(FileMention {
                    path: name,
                    start: mention_start,
                    end: mention_end,
                });
            }
        }

        (file_mentions, agent_mentions)
    }

    /// Resolve a mentioned file path relative to the working directory.
    pub fn resolve_file(&self, path: &str) -> PathBuf {
        let p = Path::new(path);
        if p.is_absolute() {
            return p.to_path_buf();
        }
        self.cwd.join(p)
    }

    /// Read mentioned files from text, returning `path -> content` (capped at
    /// 5000 chars, files that don't exist or aren't readable are skipped).
    pub fn read_mentioned_files(&self, text: &str) -> Vec<(String, String)> {
        let (file_mentions, _) = self.parse(text);
        let mut result = Vec::new();

        for fm in file_mentions {
            let resolved = self.resolve_file(&fm.path);
            if resolved.exists() && resolved.is_file() {
                if let Ok(content) = fs::read_to_string(&resolved) {
                    result.push((fm.path, content.chars().take(5000).collect()));
                }
            }
        }

        result
    }
}

/// Completer for file mentions — suggests files matching a prefix.
#[allow(dead_code)] // wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
pub struct FileMentionCompleter {
    cwd: PathBuf,
}

#[allow(dead_code)] // wiring into the message dispatch / tool chain pending — TODO(v2.6): wire into agent message parsing
impl FileMentionCompleter {
    pub fn new(cwd: impl AsRef<Path>) -> Self {
        Self {
            cwd: cwd.as_ref().to_path_buf(),
        }
    }

    /// Complete `prefix` against files under `cwd`, ignoring common dirs.
    pub fn complete(&self, prefix: &str) -> Vec<String> {
        if prefix.is_empty() {
            return Vec::new();
        }

        let ignore: &[&str] = &[
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
        ];

        let mut results: BTreeSet<String> = BTreeSet::new();
        let _ = self.rglob(&self.cwd, prefix, ignore, &mut results);

        results.into_iter().take(20).collect()
    }

    fn rglob(
        &self,
        dir: &Path,
        prefix: &str,
        ignore: &[&str],
        results: &mut BTreeSet<String>,
    ) -> std::io::Result<()> {
        let Ok(entries) = fs::read_dir(dir) else {
            return Ok(());
        };
        for entry in entries.flatten() {
            let path = entry.path();
            let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
                continue;
            };
            // Skip ignored directories/files.
            if ignore.contains(&name) {
                continue;
            }
            if path.is_dir() {
                let _ = self.rglob(&path, prefix, ignore, results);
            } else if path.is_file() {
                let rel = path
                    .strip_prefix(&self.cwd)
                    .unwrap_or(&path)
                    .to_string_lossy()
                    .to_string();
                if rel.contains(prefix) {
                    results.insert(rel);
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_agent_and_file_mentions() {
        let parser = MentionParser::new("/tmp/proj");
        let text = "@reviewer fix @src/main.py and @shell deploy";
        let (files, agents) = parser.parse(text);
        assert_eq!(agents.len(), 2);
        assert_eq!(agents[0].name, "reviewer");
        assert_eq!(agents[1].name, "shell");
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, "src/main.py");
        // Positions are end-exclusive and point at the @ character.
        assert!(agents[0].start < agents[0].end);
        assert!(agents[1].start < agents[1].end);
        assert_eq!(&text[agents[0].start..agents[0].end], "@reviewer");
        assert_eq!(&text[agents[1].start..agents[1].end], "@shell");
        assert_eq!(&text[files[0].start..files[0].end], "@src/main.py");
    }

    #[test]
    fn parse_dot_mention_in_word() {
        let parser = MentionParser::new("/tmp/proj");
        let (files, agents) = parser.parse("see src@config.yaml here");
        assert_eq!(agents.len(), 0);
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, "config.yaml");
    }

    #[test]
    fn double_at_strips_one() {
        let parser = MentionParser::new("/tmp/proj");
        let (files, _) = parser.parse("@@test.py");
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, "test.py");
        assert_eq!(files[0].start, 1);
    }

    #[test]
    fn dedup_agent_names() {
        let parser = MentionParser::new("/tmp/proj");
        let (files, agents) = parser.parse("@reviewer @REVIEWER @reviewer");
        assert_eq!(agents.len(), 1);
        assert_eq!(agents[0].name, "reviewer");
        assert!(files.is_empty());
    }

    #[test]
    fn resolve_file_relative_and_absolute() {
        let parser = MentionParser::new("/tmp/proj");
        assert_eq!(
            parser.resolve_file("src/main.rs"),
            PathBuf::from("/tmp/proj/src/main.rs")
        );
        assert_eq!(
            parser.resolve_file("/abs/path.rs"),
            PathBuf::from("/abs/path.rs")
        );
    }

    #[test]
    fn read_mentioned_files_reads_existing() {
        let dir = tempfile::tempdir().unwrap();
        let p = dir.path().join("hello.txt");
        std::fs::write(&p, "world").unwrap();
        let parser = MentionParser::new(dir.path());
        let found = parser.read_mentioned_files("@hello.txt");
        assert_eq!(found.len(), 1);
        assert_eq!(found[0].0, "hello.txt");
        assert_eq!(found[0].1, "world");
    }

    #[test]
    fn read_mentioned_files_skips_missing() {
        let parser = MentionParser::new("/tmp/nonexistent");
        let found = parser.read_mentioned_files("@nope.txt");
        assert!(found.is_empty());
    }

    #[test]
    fn completer_matches_prefix() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join("src")).unwrap();
        std::fs::write(dir.path().join("src").join("main.rs"), "").unwrap();
        std::fs::write(dir.path().join("lib.rs"), "").unwrap();
        let completer = FileMentionCompleter::new(dir.path());
        let results = completer.complete("main");
        assert!(results.iter().any(|r| r.ends_with("main.rs")));
    }

    #[test]
    fn completer_ignores_git() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::create_dir_all(dir.path().join(".git").join("objects")).unwrap();
        std::fs::write(dir.path().join(".git").join("objects").join("pack"), "x").unwrap();
        std::fs::write(dir.path().join("keep.rs"), "").unwrap();
        let completer = FileMentionCompleter::new(dir.path());
        let results = completer.complete("keep");
        assert!(!results.iter().any(|r| r.contains(".git")));
        assert!(results.iter().any(|r| r == "keep.rs"));
    }
}
