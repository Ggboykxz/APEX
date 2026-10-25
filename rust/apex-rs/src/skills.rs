//! Skills, diffs, search/replace and code analysis — port of `apex/skills.py`.
//!
//! The Python implementation leans on `re` and `difflib`; the Rust port keeps
//! the same behaviour. Regex-backed helpers use the `regex` crate (the only
//! new dependency this port added).

use regex::Regex;
use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

// ──────────────────────────────────────────────────────────────────────
// SkillManager
// ──────────────────────────────────────────────────────────────────────

#[derive(Clone)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub prompt: String,
}

pub struct SkillManager {
    pub cwd: PathBuf,
    skills: std::collections::BTreeMap<String, Skill>,
}

impl SkillManager {
    pub fn new(cwd: &Path) -> Self {
        let mut sm = Self {
            cwd: cwd.to_path_buf(),
            skills: Default::default(),
        };
        sm.load_skills();
        sm
    }

    pub fn load_skills(&mut self) {
        let mut dirs = vec![self.cwd.join(".apex").join("skills")];
        if let Some(home) = dirs::home_dir() {
            dirs.push(home.join(".apex").join("skills"));
        }
        for dir in dirs {
            if !dir.exists() {
                continue;
            }
            let Ok(rd) = fs::read_dir(&dir) else { continue };
            for entry in rd.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) != Some("md") {
                    continue;
                }
                if let Some(skill) = Self::load_skill_file(&path) {
                    self.skills.insert(skill.name.clone(), skill);
                }
            }
        }
    }

    fn load_skill_file(path: &Path) -> Option<Skill> {
        let content = fs::read_to_string(path).ok()?;
        let lines: Vec<&str> = content.trim().split('\n').collect();
        let name = path.file_stem()?.to_string_lossy().to_string();
        let mut description = String::new();
        let mut prompt_lines: Vec<&str> = Vec::new();
        let mut in_prompt = false;
        for line in &lines {
            if line.starts_with("## Description:") {
                description = line
                    .split_once(':')
                    .map(|x| x.1)
                    .unwrap_or("")
                    .trim()
                    .to_string();
            } else if line.trim() == "## Prompt" {
                in_prompt = true;
            } else if in_prompt {
                prompt_lines.push(line);
            }
        }
        let prompt = prompt_lines.join("\n").trim().to_string();
        if prompt.is_empty() {
            return None;
        }
        Some(Skill {
            name,
            description,
            prompt,
        })
    }

    pub fn get(&self, name: &str) -> Option<&Skill> {
        self.skills.get(name)
    }

    pub fn list_skills(&self) -> Vec<(String, String)> {
        self.skills
            .values()
            .map(|s| (s.name.clone(), s.description.clone()))
            .collect()
    }

    pub fn render(
        &self,
        name: &str,
        args: &std::collections::BTreeMap<String, String>,
    ) -> Option<String> {
        let skill = self.get(name)?;
        let mut result = skill.prompt.clone();
        for (key, value) in args {
            result = result.replace(&format!("{{{key}}}"), value);
        }
        Some(result)
    }

    pub fn add(&mut self, name: &str, description: &str, prompt: &str) {
        self.skills.insert(
            name.to_string(),
            Skill {
                name: name.to_string(),
                description: description.to_string(),
                prompt: prompt.to_string(),
            },
        );
    }

    pub fn remove(&mut self, name: &str) -> bool {
        self.skills.remove(name).is_some()
    }
}

// ──────────────────────────────────────────────────────────────────────
// DiffTool
// ──────────────────────────────────────────────────────────────────────

pub struct DiffTool {
    pub cwd: PathBuf,
}

impl DiffTool {
    pub fn new(cwd: &Path) -> Self {
        Self {
            cwd: cwd.to_path_buf(),
        }
    }

    pub fn diff(&self, path_a: &str, path_b: &str) -> String {
        let p1 = self.cwd.join(path_a);
        let p2 = self.cwd.join(path_b);
        if !p1.exists() {
            return format!("ERROR: File not found: {path_a}");
        }
        if !p2.exists() {
            return format!("ERROR: File not found: {path_b}");
        }
        // Python uses difflib.unified_diff over splitlines(); reproduce with
        // the system `diff -u` and normalise the header to Python's shape
        // (`--- <from>`, `+++ <to>` without timestamps).
        match Command::new("diff")
            .args(["-u", &p1.to_string_lossy(), &p2.to_string_lossy()])
            .output()
        {
            Ok(o) => {
                let out = String::from_utf8_lossy(&o.stdout).to_string();
                if out.trim().is_empty() {
                    return "[files are identical]".to_string();
                }
                let mut lines: Vec<String> = out.lines().map(|l| l.to_string()).collect();
                let mut replaced = 0;
                for line in lines.iter_mut() {
                    if replaced == 0 && line.starts_with("--- ") {
                        *line = format!("--- {}", p1.to_string_lossy());
                        replaced += 1;
                    } else if replaced == 1 && line.starts_with("+++ ") {
                        *line = format!("+++ {}", p2.to_string_lossy());
                        replaced += 1;
                    }
                }
                lines.join("\n")
            }
            Err(e) => format!("ERROR: Cannot diff files: {e}"),
        }
    }

    pub fn three_way_diff(&self, base: &str, local: &str, remote: &str) -> String {
        let b = self.cwd.join(base);
        let l = self.cwd.join(local);
        let r = self.cwd.join(remote);
        if !b.exists() || !l.exists() || !r.exists() {
            return "ERROR: One or more files not found".to_string();
        }
        match Command::new("diff3")
            .args([
                "-m",
                "-E",
                &b.to_string_lossy(),
                &l.to_string_lossy(),
                &r.to_string_lossy(),
            ])
            .output()
        {
            Ok(o) => {
                let out = String::from_utf8_lossy(&o.stdout).to_string();
                if out.trim().is_empty() {
                    "No conflicts".to_string()
                } else {
                    out
                }
            }
            Err(e) => format!("ERROR: {e}"),
        }
    }
}

// ──────────────────────────────────────────────────────────────────────
// SearchReplace
// ──────────────────────────────────────────────────────────────────────

pub struct SearchReplace {
    pub cwd: PathBuf,
}

impl SearchReplace {
    pub fn new(cwd: &Path) -> Self {
        Self {
            cwd: cwd.to_path_buf(),
        }
    }

    /// Returns `{"files_modified": [...], "replacements": N, "errors": [...]}`.
    pub fn replace_in_files(
        &self,
        pattern: &str,
        replacement: &str,
        globs: &[String],
        dry_run: bool,
    ) -> Value {
        let mut result = json!({"files_modified": [], "replacements": 0, "errors": []});
        let re = match Regex::new(pattern) {
            Ok(r) => r,
            Err(e) => return json!({"error": format!("Invalid regex: {e}")}),
        };
        // Python uses \1-style group references in the replacement; Rust uses $1.
        let rust_repl = python_repl_to_rust(replacement);

        let mut files_modified: Vec<String> = Vec::new();
        let mut total = 0i64;
        let mut errors: Vec<String> = Vec::new();

        for glob_pattern in globs {
            // Python: self.cwd.rglob(glob_pattern). Collect deterministically.
            let mut files: Vec<PathBuf> = Vec::new();
            collect_rglob(&self.cwd, &self.cwd, glob_pattern, &mut files);
            files.sort();
            for filepath in files {
                if !filepath.is_file() {
                    continue;
                }
                let content = match fs::read_to_string(&filepath) {
                    Ok(c) => c,
                    Err(e) => {
                        errors.push(format!("{}: {e}", filepath.display()));
                        continue;
                    }
                };
                let count = re.find_iter(&content).count();
                if count == 0 {
                    continue;
                }
                let new_content = re.replace_all(&content, &rust_repl).to_string();
                total += count as i64;
                let rel = filepath
                    .strip_prefix(&self.cwd)
                    .unwrap_or(&filepath)
                    .to_string_lossy()
                    .to_string();
                if !dry_run {
                    if let Err(e) = fs::write(&filepath, &new_content) {
                        errors.push(format!("{}: {e}", filepath.display()));
                        continue;
                    }
                    files_modified.push(rel);
                } else {
                    files_modified.push(format!("{rel} ({count} replacements)"));
                }
            }
        }
        result["files_modified"] = json!(files_modified);
        result["replacements"] = json!(total);
        result["errors"] = json!(errors);
        result
    }
}

fn python_repl_to_rust(repl: &str) -> String {
    // Convert Python's \1..\9 group references to Rust's $1..$9.
    let re = Regex::new(r"\\([1-9])").unwrap();
    re.replace_all(repl, "$$${1}").to_string()
}

/// Minimal glob: support '*' and '**' by walking the tree and matching the
/// relative path. Python's Path.rglob matches the whole relative path.
fn collect_rglob(_root: &Path, base: &Path, pattern: &str, out: &mut Vec<PathBuf>) {
    fn walk(root: &Path, dir: &Path, pattern: &str, out: &mut Vec<PathBuf>) {
        let Ok(rd) = fs::read_dir(dir) else { return };
        for entry in rd.flatten() {
            let p = entry.path();
            if p.is_dir() {
                walk(root, &p, pattern, out);
            } else if p.is_file() {
                let rel = p.strip_prefix(root).unwrap_or(&p).to_string_lossy();
                if glob_match(pattern, &rel) {
                    out.push(p);
                }
            }
        }
    }
    walk(base, base, pattern, out);
}

/// Minimal glob matcher supporting `*`, `**` and `?`.
fn glob_match(pattern: &str, text: &str) -> bool {
    // Convert glob to a regex-ish matcher by hand (only * and ?).
    fn rec(p: &[u8], t: &[u8]) -> bool {
        if p.is_empty() {
            return t.is_empty();
        }
        if p[0] == b'*' {
            // '**' behaves like '*' for our purposes (match across dirs).
            if p.len() > 1 && p[1] == b'*' {
                let p = &p[2..];
                let p = if p.first() == Some(&b'/') { &p[1..] } else { p };
                for i in 0..=t.len() {
                    if rec(p, &t[i..]) {
                        return true;
                    }
                }
                return false;
            }
            for i in 0..=t.len() {
                if rec(&p[1..], &t[i..]) {
                    return true;
                }
            }
            return false;
        }
        if !t.is_empty() && (p[0] == b'?' || p[0] == t[0]) {
            return rec(&p[1..], &t[1..]);
        }
        false
    }
    rec(pattern.as_bytes(), text.as_bytes())
}

// ──────────────────────────────────────────────────────────────────────
// CodeAnalyzer
// ──────────────────────────────────────────────────────────────────────

pub struct CodeAnalyzer {
    pub cwd: PathBuf,
}

impl CodeAnalyzer {
    pub fn new(cwd: &Path) -> Self {
        Self {
            cwd: cwd.to_path_buf(),
        }
    }

    pub fn analyze_file(&self, path: &str) -> Value {
        let filepath = self.cwd.join(path);
        let Ok(content) = fs::read_to_string(&filepath) else {
            return json!({"error": "File not found"});
        };
        let lines: Vec<&str> = content.split('\n').collect();
        let func_re = Regex::new(r"^(\s*)def\s+(\w+)\s*\(").unwrap();
        let class_re = Regex::new(r"^class\s+(\w+)").unwrap();
        let import_re = Regex::new(r"^import\s+(\S+)|^from\s+(\S+)\s+import").unwrap();

        let mut functions: Vec<Value> = Vec::new();
        let mut classes: Vec<Value> = Vec::new();
        let mut imports: Vec<String> = Vec::new();
        let mut blank = 0usize;
        let mut code = 0usize;
        let mut comments = 0usize;

        for (i, line) in lines.iter().enumerate() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                blank += 1;
            } else if trimmed.starts_with('#') {
                comments += 1;
            } else {
                code += 1;
            }
            if let Some(c) = func_re.captures(line) {
                functions.push(json!({"name": c.get(2).unwrap().as_str(), "line": i + 1}));
            }
            if let Some(c) = class_re.captures(line) {
                classes.push(json!({"name": c.get(1).unwrap().as_str(), "line": i + 1}));
            }
            if let Some(c) = import_re.captures(line) {
                let imp = c
                    .get(1)
                    .or_else(|| c.get(2))
                    .map(|m| m.as_str().to_string())
                    .unwrap_or_default();
                imports.push(imp);
            }
        }

        json!({
            "path": path,
            "lines": lines.len(),
            "blank_lines": blank,
            "code_lines": code,
            "comment_lines": comments,
            "functions": functions,
            "classes": classes,
            "imports": imports,
        })
    }

    pub fn explain_code(&self, path: &str, start: i64, end: Option<i64>) -> String {
        let analysis = self.analyze_file(path);
        if let Some(err) = analysis.get("error").and_then(|e| e.as_str()) {
            return err.to_string();
        }
        let lines = analysis["lines"].as_i64().unwrap_or(0);
        let end_line = end.unwrap_or(lines);
        format!(
            "File: {path}\nLines: {lines} (showing {start}-{end_line})\n\nSummary:\n- {} functions defined\n- {} classes defined\n- {} imports\n\nFunctions: {}\nClasses: {}\nImports: {}",
            analysis["functions"].as_array().map(|a| a.len()).unwrap_or(0),
            analysis["classes"].as_array().map(|a| a.len()).unwrap_or(0),
            analysis["imports"].as_array().map(|a| a.len()).unwrap_or(0),
            analysis["functions"]
                .as_array()
                .map(|a| a.iter().filter_map(|f| f.get("name").and_then(|n| n.as_str())).collect::<Vec<_>>().join(", "))
                .unwrap_or_default(),
            analysis["classes"]
                .as_array()
                .map(|a| a.iter().filter_map(|c| c.get("name").and_then(|n| n.as_str())).collect::<Vec<_>>().join(", "))
                .unwrap_or_default(),
            analysis["imports"]
                .as_array()
                .map(|a| a.iter().filter_map(|i| i.as_str()).take(10).collect::<Vec<_>>().join(", "))
                .unwrap_or_default(),
        )
    }
}

// ──────────────────────────────────────────────────────────────────────
// Global skill manager (Python: get_skill_manager caches a singleton)
// ──────────────────────────────────────────────────────────────────────

pub fn get_skill_manager(cwd: &Path) -> SkillManager {
    SkillManager::new(cwd)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn skill_manager_loads_and_renders() {
        let dir = tempdir().unwrap();
        let skills = dir.path().join(".apex").join("skills");
        fs::create_dir_all(&skills).unwrap();
        fs::write(
            skills.join("greet.md"),
            "## Description: greet someone\n## Prompt\nHello {name}, welcome to {place}!\n",
        )
        .unwrap();
        let mut sm = SkillManager::new(dir.path());
        assert_eq!(
            sm.list_skills(),
            vec![("greet".to_string(), "greet someone".to_string())]
        );
        assert!(sm.get("greet").is_some());
        let mut args = std::collections::BTreeMap::new();
        args.insert("name".to_string(), "Ada".to_string());
        args.insert("place".to_string(), "APEX".to_string());
        assert_eq!(
            sm.render("greet", &args).unwrap(),
            "Hello Ada, welcome to APEX!"
        );
        assert!(sm.render("missing", &args).is_none());
        sm.add("x", "desc", "prompt body");
        assert!(sm.remove("x"));
        assert!(!sm.remove("x"));
    }

    #[test]
    fn skill_manager_skips_promptless_files() {
        let dir = tempdir().unwrap();
        let skills = dir.path().join(".apex").join("skills");
        fs::create_dir_all(&skills).unwrap();
        fs::write(skills.join("empty.md"), "## Description: no prompt here\n").unwrap();
        let sm = SkillManager::new(dir.path());
        assert!(sm.list_skills().is_empty());
    }

    #[cfg(unix)]
    #[test]
    fn diff_tool_reports_identical_and_missing() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "one\ntwo\n").unwrap();
        fs::write(dir.path().join("b.txt"), "one\ntwo\n").unwrap();
        let dt = DiffTool::new(dir.path());
        assert_eq!(dt.diff("a.txt", "b.txt"), "[files are identical]");
        assert!(dt
            .diff("a.txt", "nope.txt")
            .starts_with("ERROR: File not found"));
    }

    #[cfg(unix)]
    #[test]
    fn diff_tool_unified_output() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "one\ntwo\nthree\n").unwrap();
        fs::write(dir.path().join("b.txt"), "one\nTWO\nthree\n").unwrap();
        let dt = DiffTool::new(dir.path());
        let out = dt.diff("a.txt", "b.txt");
        assert!(out.contains("-two") || out.contains("-two"), "got {out}");
        assert!(out.contains("+TWO"), "got {out}");
    }

    #[test]
    fn search_replace_dry_run_and_apply() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("f.txt"), "foo bar foo\n").unwrap();
        let sr = SearchReplace::new(dir.path());
        let res = sr.replace_in_files("foo", "baz", &["*.txt".to_string()], true);
        assert_eq!(res["replacements"], 2);
        assert_eq!(res["files_modified"][0], "f.txt (2 replacements)");
        // dry run must not touch the file
        assert_eq!(
            fs::read_to_string(dir.path().join("f.txt")).unwrap(),
            "foo bar foo\n"
        );

        let res = sr.replace_in_files("foo", "baz", &["*.txt".to_string()], false);
        assert_eq!(res["replacements"], 2);
        assert_eq!(
            fs::read_to_string(dir.path().join("f.txt")).unwrap(),
            "baz bar baz\n"
        );
        assert_eq!(res["files_modified"], json!(["f.txt"]));
    }

    #[test]
    fn search_replace_regex_groups() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("f.txt"), "abc 123\n").unwrap();
        let sr = SearchReplace::new(dir.path());
        // Python replacement uses \1; Rust must accept it.
        let res = sr.replace_in_files(r"(\w+) (\d+)", r"\2 \1", &["*.txt".to_string()], false);
        assert_eq!(res["replacements"], 1);
        assert_eq!(
            fs::read_to_string(dir.path().join("f.txt")).unwrap(),
            "123 abc\n"
        );
    }

    #[test]
    fn search_replace_invalid_regex() {
        let dir = tempdir().unwrap();
        let sr = SearchReplace::new(dir.path());
        let res = sr.replace_in_files("[", "x", &["*.txt".to_string()], true);
        assert!(res
            .get("error")
            .unwrap()
            .to_string()
            .contains("Invalid regex"));
    }

    #[test]
    fn search_replace_rglob_and_errors() {
        let dir = tempdir().unwrap();
        let sub = dir.path().join("sub");
        fs::create_dir(&sub).unwrap();
        fs::write(sub.join("a.txt"), "x\n").unwrap();
        let sr = SearchReplace::new(dir.path());
        let res = sr.replace_in_files("x", "y", &["**/*.txt".to_string()], true);
        assert_eq!(res["replacements"], 1);
    }

    #[test]
    fn code_analyzer_counts_and_lists() {
        let dir = tempdir().unwrap();
        fs::write(
            dir.path().join("m.py"),
            "import os\nfrom x import y\n\nclass A:\n    pass\n\ndef f(a, b):\n    # comment\n    return a\n",
        )
        .unwrap();
        let ca = CodeAnalyzer::new(dir.path());
        let a = ca.analyze_file("m.py");
        assert_eq!(a["lines"], 10);
        assert_eq!(a["blank_lines"], 3);
        assert_eq!(a["code_lines"], 6);
        assert_eq!(a["comment_lines"], 1);
        assert_eq!(a["functions"][0]["name"], "f");
        assert_eq!(a["functions"][0]["line"], 7);
        assert_eq!(a["classes"][0]["name"], "A");
        assert_eq!(a["classes"][0]["line"], 4);
        assert_eq!(a["imports"], json!(["os", "x"]));
        assert_eq!(ca.analyze_file("nope.py")["error"], "File not found");

        let explained = ca.explain_code("m.py", 1, Some(3));
        assert!(explained.starts_with("File: m.py"));
        assert!(explained.contains("Functions: f"));
    }
}
