//! Code generation & refactoring — port of `apex/codegen.py`.
//!
//! The Python implementation uses `re`; to keep the crate dependency-free the
//! few patterns it relies on (`\bdef \w+`, `^import `, `def (\w+)\((.*?)\):`, …)
//! are re-implemented as small scanners. Behaviour is pinned by tests whose
//! expectations come from running the Python code.

use serde_json::{json, Value};
use std::path::{Path, PathBuf};

fn is_word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// `\b<word>\b` — whole-word occurrences.
fn count_whole_word(text: &str, word: &str) -> usize {
    let mut count = 0;
    let mut start = 0;
    while let Some(pos) = text[start..].find(word) {
        let i = start + pos;
        let after = i + word.len();
        let before_ok = i == 0 || text[..i].chars().next_back().map(|c| !is_word_char(c)).unwrap_or(true);
        let after_ok = text[after..].chars().next().map(|c| !is_word_char(c)).unwrap_or(true);
        if before_ok && after_ok {
            count += 1;
        }
        start = after;
    }
    count
}

/// `\b<kw>\w` — keyword followed by a word (e.g. `\bdef \w+`).
fn count_kw_before_word(text: &str, kw: &str) -> usize {
    let mut count = 0;
    let mut start = 0;
    while let Some(pos) = text[start..].find(kw) {
        let i = start + pos;
        let after = i + kw.len();
        let before_ok = i == 0 || text[..i].chars().next_back().map(|c| !is_word_char(c)).unwrap_or(true);
        let after_ok = text[after..].chars().next().map(is_word_char).unwrap_or(false);
        if before_ok && after_ok {
            count += 1;
        }
        start = after;
    }
    count
}

/// `^import |^from ` in MULTILINE mode.
fn count_line_starts(text: &str, prefixes: &[&str]) -> usize {
    text.lines()
        .filter(|l| prefixes.iter().any(|p| l.starts_with(p)))
        .count()
}

pub struct CodeRefactorer {
    pub cwd: PathBuf,
}

impl CodeRefactorer {
    pub fn new(cwd: &Path) -> Self {
        Self { cwd: cwd.to_path_buf() }
    }

    fn read(&self, filepath: &str) -> Result<String, String> {
        std::fs::read_to_string(self.cwd.join(filepath)).map_err(|_| "File not found".to_string())
    }

    /// Add type hints / make a function `async` (styles: `modern`, `async`, `type_hints`).
    pub fn refactor_function(&self, filepath: &str, function_name: &str, style: &str) -> Value {
        let content = match self.read(filepath) {
            Ok(c) => c,
            Err(e) => return json!({"error": e}),
        };
        let mut lines: Vec<String> = content.split('\n').map(|s| s.to_string()).collect();
        for line in lines.iter_mut() {
            if line.contains(&format!("def {function_name}")) {
                *line = match style {
                    "async" => line.replace("def ", "async def "),
                    "type_hints" => line.replace(')', ") -> Any "),
                    "modern" => {
                        if line.contains("async") {
                            line.clone()
                        } else {
                            line.replace("def ", "async def ")
                        }
                    }
                    _ => line.clone(),
                };
                let new_content = lines.join("\n");
                if std::fs::write(self.cwd.join(filepath), new_content).is_err() {
                    return json!({"error": "write failed"});
                }
                return json!({"success": true, "function": function_name, "style": style});
            }
        }
        json!({"error": "Function not found"})
    }

    /// Insert a new method right after the `class <name>:` line.
    pub fn extract_method(
        &self,
        filepath: &str,
        class_name: &str,
        code: &str,
        new_method: &str,
    ) -> Value {
        let content = match self.read(filepath) {
            Ok(c) => c,
            Err(e) => return json!({"error": e}),
        };
        if !content.contains(class_name) {
            return json!({"error": format!("Class {class_name} not found")});
        }
        let new_method_code = format!("\n    def {new_method}(self):\n        {code}\n");
        let updated = content.replace(
            &format!("class {class_name}:"),
            &format!("class {class_name}:{new_method_code}"),
        );
        if std::fs::write(self.cwd.join(filepath), updated).is_err() {
            return json!({"error": "write failed"});
        }
        json!({"success": true, "method": new_method})
    }

    /// Wrap a function into a class.
    ///
    /// Ported as-is from `apex/codegen.py`, including its quirk: the generated
    /// body reads `class Foo:\n    def def foo(...)` (the Python code prefixes
    /// `def ` to a snippet that already starts with `def`).
    pub fn convert_to_class(&self, filepath: &str, function_name: &str) -> Value {
        let content = match self.read(filepath) {
            Ok(c) => c,
            Err(e) => return json!({"error": e}),
        };
        // `def name\([^)]*\):.*?(?=\n(?:def |class |$))` with DOTALL.
        let needle = format!("def {function_name}(");
        let Some(start) = content.find(&needle) else {
            return json!({"error": "Function not found"});
        };
        let after_args = start + needle.len();
        let Some(close) = content[after_args..].find(')').map(|i| after_args + i) else {
            return json!({"error": "Function not found"});
        };
        if !content[close + 1..].starts_with(':') {
            return json!({"error": "Function not found"});
        }
        let rest = &content[start..];
        let Some(end) = rest
            .match_indices('\n')
            .find(|(i, _)| {
                let next = &rest[i + 1..];
                // `(?=\n(?:def |class |$))` — `$` covers end-of-string and a
                // trailing newline.
                next.starts_with("def ")
                    || next.starts_with("class ")
                    || next.chars().all(|c| c == '\n')
            })
            .map(|(i, _)| i)
        else {
            // Python's regex cannot match either without a terminator.
            return json!({"error": "Function not found"});
        };
        let func_code = &rest[..end];

        let mut name_chars = function_name.chars();
        let class_name = match name_chars.next() {
            Some(first) => first.to_uppercase().collect::<String>() + name_chars.as_str(),
            None => String::new(),
        };
        let class_code = format!("class {class_name}:\n    def {func_code}\n");
        let updated = content.replace(func_code, &class_code);
        if std::fs::write(self.cwd.join(filepath), updated).is_err() {
            return json!({"error": "write failed"});
        }
        json!({"success": true, "class": class_name})
    }

    /// `def name(args):` → `def name(args) -> Any:` for every function.
    pub fn add_type_hints(&self, filepath: &str) -> Value {
        let content = match self.read(filepath) {
            Ok(c) => c,
            Err(e) => return json!({"error": e}),
        };
        let mut out = String::with_capacity(content.len());
        let mut rest = content.as_str();
        loop {
            let Some(pos) = rest.find("def ") else {
                out.push_str(rest);
                break;
            };
            out.push_str(&rest[..pos + 4]);
            let after = &rest[pos + 4..];
            // `\w+` function name
            let name_len = after.chars().take_while(|c| is_word_char(*c)).map(|c| c.len_utf8()).sum::<usize>();
            let (name, after_name) = after.split_at(name_len);
            out.push_str(name);
            if !after_name.starts_with('(') {
                // Not a function definition (e.g. "def " inside a string): keep going.
                rest = after_name;
                continue;
            }
            // `\(([^)]*)\):` — `[^)]` may span newlines, like Python's regex.
            match after_name.find(')') {
                Some(close) if after_name[close + 1..].starts_with(':') => {
                    out.push_str(&after_name[..close + 1]);
                    out.push_str(" -> Any");
                    out.push(':');
                    rest = &after_name[close + 2..];
                }
                _ => {
                    rest = after_name;
                }
            }
        }
        if std::fs::write(self.cwd.join(filepath), out).is_err() {
            return json!({"error": "write failed"});
        }
        json!({"success": true, "file": filepath})
    }
}

pub struct DatabaseManager;

impl DatabaseManager {
    pub fn get_connection_string(db_type: &str) -> String {
        match db_type {
            "sqlite" => "sqlite:///db.sqlite",
            "postgres" => "postgresql://user:password@localhost:5432/db",
            "mysql" => "mysql://user:password@localhost:3306/db",
            "mongodb" => "mongodb://localhost:27017/db",
            _ => "",
        }
        .to_string()
    }

    pub fn generate_model(table_name: &str, columns: &[Value]) -> String {
        let mut name_chars = table_name.chars();
        let class_name = match name_chars.next() {
            Some(first) => first.to_uppercase().collect::<String>() + name_chars.as_str(),
            None => String::new(),
        };
        let mut lines = vec![format!("class {class_name}:"), String::new()];
        for col in columns {
            let name = col.get("name").and_then(|v| v.as_str()).unwrap_or("field");
            let col_type = col.get("type").and_then(|v| v.as_str()).unwrap_or("str");
            let python_type = match col_type.to_lowercase().as_str() {
                "int" => "int",
                "varchar" => "str",
                "text" => "str",
                "bool" => "bool",
                "date" => "datetime",
                _ => "Any",
            };
            lines.push(format!("    {name}: {python_type} = None"));
        }
        lines.push(String::new());
        lines.push("    def __init__(self, **kwargs):".to_string());
        lines.push("        for key, value in kwargs.items():".to_string());
        lines.push("            setattr(self, key, value)".to_string());
        lines.join("\n")
    }

    pub fn generate_queries(table_name: &str) -> Value {
        json!({
            "create": format!("CREATE TABLE {table_name} (id INTEGER PRIMARY KEY);"),
            "insert": format!("INSERT INTO {table_name} VALUES (:id);"),
            "select": format!("SELECT * FROM {table_name} WHERE id = :id;"),
            "update": format!("UPDATE {table_name} SET column = :value WHERE id = :id;"),
            "delete": format!("DELETE FROM {table_name} WHERE id = :id;"),
        })
    }
}

pub struct DockerManager;

const UNSUPPORTED_LANGUAGE: &str = "# Unsupported language";

impl DockerManager {
    pub fn generate_dockerfile(language: &str) -> String {
        match language {
            "python" => "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"main.py\"]\n",
            "node" => "FROM node:20-slim\nWORKDIR /app\nCOPY package*.json ./\nRUN npm install\nCOPY . .\nCMD [\"node\", \"index.js\"]\n",
            "go" => "FROM golang:1.21-slim\nWORKDIR /app\nCOPY . .\nRUN go build -o main .\nCMD [\"./main\"]\n",
            "rust" => "FROM rust:1.75-slim\nWORKDIR /app\nCOPY . .\nRUN cargo build --release\nCMD [\"./target/release/app\"]\n",
            "java" => "FROM eclipse-temurin:17-jdk\nWORKDIR /app\nCOPY . .\nRUN ./mvnw package\nCMD [\"java\", \"-jar\", \"target/app.jar\"]\n",
            _ => UNSUPPORTED_LANGUAGE,
        }
        .to_string()
    }

    pub fn generate_docker_compose(services: &[Value]) -> String {
        let mut lines = vec!["version: '3.8'".to_string(), String::new(), "services:".to_string()];
        for svc in services {
            let name = svc.get("name").and_then(|v| v.as_str()).unwrap_or("service");
            let image = svc.get("image").and_then(|v| v.as_str()).unwrap_or("nginx");
            let ports: Vec<String> = svc
                .get("ports")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().filter_map(|p| p.as_str().map(|s| s.to_string())).collect())
                .unwrap_or_else(|| vec!["80:80".to_string()]);
            lines.push(format!("  {name}:"));
            lines.push(format!("    image: {image}"));
            lines.push("    ports:".to_string());
            for p in ports {
                lines.push(format!("      - '{p}'"));
            }
        }
        lines.join("\n")
    }
}

pub struct ApiClientGenerator {
    pub cwd: PathBuf,
}

impl ApiClientGenerator {
    pub fn new(cwd: &Path) -> Self {
        Self { cwd: cwd.to_path_buf() }
    }

    pub fn generate_from_openapi(&self, spec_path: &str) -> String {
        let path = self.cwd.join(spec_path);
        if !path.exists() {
            return "ERROR: Spec file not found".to_string();
        }
        let spec: Value = match std::fs::read_to_string(&path).ok().and_then(|d| serde_json::from_str(&d).ok()) {
            Some(v) => v,
            None => return "ERROR: Invalid JSON spec".to_string(),
        };
        let base_url = spec
            .get("servers")
            .and_then(|s| s.as_array())
            .and_then(|a| a.first())
            .and_then(|s| s.get("url"))
            .and_then(|u| u.as_str())
            .unwrap_or("http://localhost");
        let mut lines = vec![
            "import requests".to_string(),
            String::new(),
            "class APIClient:".to_string(),
            String::new(),
            format!("    def __init__(self, base_url=\"{base_url}\"):"),
            "        self.base_url = base_url".to_string(),
            "        self.session = requests.Session()".to_string(),
            String::new(),
        ];
        if let Some(paths) = spec.get("paths").and_then(|p| p.as_object()) {
            for (path_name, methods) in paths {
                if let Some(methods) = methods.as_object() {
                    for (method, _details) in methods {
                        if ["get", "post", "put", "delete", "patch"].contains(&method.as_str()) {
                            let func_name = format!(
                                "{method}_{}",
                                path_name.replace('/', "_").trim_matches('_')
                            );
                            lines.push(format!("    def {func_name}(self, **kwargs):"));
                            lines.push(format!(
                                "        return self.session.{method}(f\"{{self.base_url}}{path_name}\", **kwargs)"
                            ));
                            lines.push(String::new());
                        }
                    }
                }
            }
        }
        lines.join("\n")
    }

    pub fn generate_curl(method: &str, url: &str, headers: Option<&Value>, data: Option<&Value>) -> String {
        let mut parts = vec!["curl".to_string(), format!("-X {}", method.to_uppercase()), format!("\"{url}\"")];
        if let Some(headers) = headers.and_then(|h| h.as_object()) {
            for (k, v) in headers {
                let value = v.as_str().map(|s| s.to_string()).unwrap_or_else(|| v.to_string());
                parts.push(format!("-H '{k}: {value}'"));
            }
        }
        if let Some(data) = data {
            let value = data.as_str().map(|s| s.to_string()).unwrap_or_else(|| data.to_string());
            parts.push(format!("-d '{value}'"));
        }
        parts.join(" ")
    }
}

pub struct DocumentationGenerator {
    pub cwd: PathBuf,
}

impl DocumentationGenerator {
    pub fn new(cwd: &Path) -> Self {
        Self { cwd: cwd.to_path_buf() }
    }

    pub fn generate_readme(&self) -> String {
        let mut files: Vec<String> = std::fs::read_dir(&self.cwd)
            .map(|rd| {
                rd.flatten()
                    .filter(|e| {
                        let name = e.file_name().to_string_lossy().to_string();
                        // Python's glob() skips hidden entries.
                        !name.starts_with('.')
                            && e.path().extension().and_then(|x| x.to_str()) == Some("py")
                    })
                    .map(|e| e.file_name().to_string_lossy().to_string())
                    .collect()
            })
            .unwrap_or_default();
        files.sort();
        if files.is_empty() {
            return "# Project\n\nNo Python files found.".to_string();
        }
        let mut lines = vec![
            "# Project\n".to_string(),
            "## Overview\n".to_string(),
            "## Installation\n".to_string(),
            "```bash\npip install -r requirements.txt\n```\n".to_string(),
            "## Usage\n".to_string(),
        ];
        for f in files.iter().take(5) {
            let stem = f.strip_suffix(".py").unwrap_or(f);
            lines.push(format!("### {stem}\n"));
            lines.push(format!("Run with: `python {f}`\n"));
        }
        lines.join("\n")
    }

    /// `def (\w+)\((.*?)\):` per line (Python's `.` does not match newlines).
    pub fn generate_api_docs(&self, filepath: &str) -> String {
        let path = self.cwd.join(filepath);
        let Ok(content) = std::fs::read_to_string(&path) else {
            return "ERROR: File not found".to_string();
        };
        let mut lines = vec![format!("# API Documentation: {filepath}\n")];
        for line in content.lines() {
            let mut rest = line;
            while let Some(pos) = rest.find("def ") {
                let after = &rest[pos + 4..];
                let name_len: usize = after.chars().take_while(|c| is_word_char(*c)).map(|c| c.len_utf8()).sum();
                let (name, after_name) = after.split_at(name_len);
                if name.is_empty() || !after_name.starts_with('(') {
                    rest = after;
                    continue;
                }
                let args_region = &after_name[1..];
                if let Some(close) = args_region.find("):") {
                    let args = &args_region[..close];
                    lines.push(format!("## {name}\n"));
                    lines.push(format!(
                        "**Parameters:** {}\n",
                        if args.is_empty() { "none" } else { args }
                    ));
                    lines.push("**Returns:** Any\n".to_string());
                }
                rest = after_name;
            }
        }
        lines.join("\n")
    }

    /// `class (\w+).*:` over every `**/*.py`, first 20 classes.
    pub fn generate_markdoc(&self) -> String {
        let mut classes: Vec<(String, String)> = Vec::new();
        let mut stack = vec![self.cwd.clone()];
        let mut py_files: Vec<PathBuf> = Vec::new();
        while let Some(dir) = stack.pop() {
            let Ok(rd) = std::fs::read_dir(&dir) else { continue };
            for e in rd.flatten() {
                let p = e.path();
                let hidden = p
                    .file_name()
                    .map(|n| n.to_string_lossy().starts_with('.'))
                    .unwrap_or(false);
                // Python's Path.glob('**/*.py') does not descend into dot dirs.
                if hidden {
                    continue;
                }
                if p.is_dir() {
                    stack.push(p);
                } else if p.extension().and_then(|x| x.to_str()) == Some("py") {
                    py_files.push(p);
                }
            }
        }
        py_files.sort();
        for f in py_files {
            let Ok(content) = std::fs::read_to_string(&f) else { continue };
            for line in content.lines() {
                if let Some(pos) = line.find("class ") {
                    let after = &line[pos + 6..];
                    let name: String = after.chars().take_while(|c| is_word_char(*c)).collect();
                    if name.is_empty() || !line.contains(':') {
                        continue;
                    }
                    let rel = f.strip_prefix(&self.cwd).unwrap_or(&f).to_string_lossy().to_string();
                    classes.push((name, rel));
                }
            }
        }
        let mut lines = vec!["# Documentation\n".to_string(), "## Classes\n".to_string()];
        for (name, file) in classes.iter().take(20) {
            lines.push(format!("- **{name}** ({file})"));
        }
        lines.join("\n")
    }
}

pub struct PerformanceProfiler {
    pub cwd: PathBuf,
}

impl PerformanceProfiler {
    pub fn new(cwd: &Path) -> Self {
        Self { cwd: cwd.to_path_buf() }
    }

    pub fn profile_file(&self, filepath: &str) -> Value {
        let path = self.cwd.join(filepath);
        let Ok(content) = std::fs::read_to_string(&path) else {
            return json!({"error": "File not found"});
        };
        let loops = count_whole_word(&content, "for") + count_whole_word(&content, "while");
        let conditionals = count_whole_word(&content, "if")
            + count_whole_word(&content, "elif")
            + count_whole_word(&content, "else");
        json!({
            "lines": content.matches('\n').count() + 1,
            "functions": count_kw_before_word(&content, "def "),
            "classes": count_kw_before_word(&content, "class "),
            "imports": count_line_starts(&content, &["import ", "from "]),
            "complexity_score": loops + conditionals,
        })
    }

    pub fn suggest_optimizations(&self, filepath: &str) -> Vec<String> {
        let path = self.cwd.join(filepath);
        let Ok(content) = std::fs::read_to_string(&path) else {
            return vec!["File not found".to_string()];
        };
        let mut suggestions = Vec::new();
        if content.contains("for i in range") {
            suggestions.push("Use list comprehension instead of range loops".to_string());
        }
        if content.contains(".append(") {
            suggestions.push("Consider using list comprehension or generator".to_string());
        }
        if content.contains("open(") && !content.contains("with") {
            suggestions.push("Use 'with' statement for file operations".to_string());
        }
        if content.len() > 5000 {
            suggestions.push("Consider splitting into multiple modules".to_string());
        }
        if suggestions.is_empty() {
            suggestions.push("Code looks optimized".to_string());
        }
        suggestions
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn word_counters_match_regex_semantics() {
        assert_eq!(count_whole_word("for x in y: for i in z", "for"), 2);
        assert_eq!(count_whole_word("format(elsewhere)", "for"), 0);
        assert_eq!(count_whole_word("if a ifelse elif b else c", "if"), 1);
        assert_eq!(count_kw_before_word("def foo():", "def "), 1);
        assert_eq!(count_kw_before_word("xdef foo():", "def "), 0);
        assert_eq!(count_line_starts("import os\nfrom x import y\nimport numpy", &["import ", "from "]), 3);
        assert_eq!(count_line_starts("ximport os", &["import "]), 0);
    }

    #[test]
    fn refactor_function_styles() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("m.py");
        std::fs::write(&file, "def foo(a):\n    return a\n\ndef bar(b):\n    return b\n").unwrap();
        let cr = CodeRefactorer::new(dir.path());

        let r = cr.refactor_function("m.py", "foo", "async");
        assert_eq!(r["success"], true);
        assert_eq!(r["style"], "async");
        let content = std::fs::read_to_string(&file).unwrap();
        assert!(content.contains("async def foo(a):"));
        assert!(content.contains("def bar(b):"), "other functions untouched");

        // type_hints style replaces every `)` on the def line (Python parity).
        let r = cr.refactor_function("m.py", "bar", "type_hints");
        assert_eq!(r["success"], true);
        let content = std::fs::read_to_string(&file).unwrap();
        assert!(content.contains("def bar(b) -> Any :"), "got: {content}");

        let r = cr.refactor_function("m.py", "missing", "async");
        assert_eq!(r["error"], "Function not found");
        let r = cr.refactor_function("nope.py", "foo", "async");
        assert_eq!(r["error"], "File not found");
    }

    #[test]
    fn add_type_hints_matches_python_output() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("m.py");
        std::fs::write(&file, "def foo(a):\n    return a\n\nx = 1\ndef bar(b, c):\n    return b\n").unwrap();
        let cr = CodeRefactorer::new(dir.path());
        let r = cr.add_type_hints("m.py");
        assert_eq!(r["success"], true);
        let content = std::fs::read_to_string(&file).unwrap();
        assert_eq!(
            content,
            "def foo(a) -> Any:\n    return a\n\nx = 1\ndef bar(b, c) -> Any:\n    return b\n"
        );
    }

    #[test]
    fn extract_method_inserts_after_class_line() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("m.py");
        std::fs::write(&file, "class Foo:\n    pass\n").unwrap();
        let cr = CodeRefactorer::new(dir.path());
        let r = cr.extract_method("m.py", "Foo", "return 1", "bar");
        assert_eq!(r["success"], true);
        let content = std::fs::read_to_string(&file).unwrap();
        assert_eq!(content, "class Foo:\n    def bar(self):\n        return 1\n\n    pass\n");
        let r = cr.extract_method("m.py", "Missing", "x", "y");
        assert_eq!(r["error"], "Class Missing not found");
    }

    #[test]
    fn dockerfile_and_compose() {
        assert!(DockerManager::generate_dockerfile("python").starts_with("FROM python:3.11-slim"));
        assert!(DockerManager::generate_dockerfile("rust").contains("cargo build --release"));
        assert_eq!(DockerManager::generate_dockerfile("cobol"), "# Unsupported language");
        let compose = DockerManager::generate_docker_compose(&[json!({
            "name": "web", "image": "nginx", "ports": ["8080:80"]
        })]);
        assert_eq!(
            compose,
            "version: '3.8'\n\nservices:\n  web:\n    image: nginx\n    ports:\n      - '8080:80'"
        );
        // Defaults are `nginx` and `80:80`, like Python.
        let compose = DockerManager::generate_docker_compose(&[json!({"name": "db"})]);
        assert_eq!(
            compose,
            "version: '3.8'\n\nservices:\n  db:\n    image: nginx\n    ports:\n      - '80:80'"
        );
    }

    #[test]
    fn db_model_matches_python() {
        let model = DatabaseManager::generate_model(
            "user",
            &[json!({"name": "id", "type": "int"}), json!({"name": "name", "type": "varchar"})],
        );
        assert_eq!(
            model,
            "class User:\n\n    id: int = None\n    name: str = None\n\n    def __init__(self, **kwargs):\n        for key, value in kwargs.items():\n            setattr(self, key, value)"
        );
        assert_eq!(DatabaseManager::get_connection_string("sqlite"), "sqlite:///db.sqlite");
        assert_eq!(DatabaseManager::get_connection_string("oracle"), "");
        assert_eq!(DatabaseManager::generate_queries("user")["select"], "SELECT * FROM user WHERE id = :id;");
    }

    #[test]
    fn openapi_client_generation() {
        let dir = tempdir().unwrap();
        std::fs::write(
            dir.path().join("spec.json"),
            r#"{"servers":[{"url":"https://api.example.com"}],"paths":{"/users/{id}":{"get":{}},"/users":{"post":{}}}}"#,
        )
        .unwrap();
        let acg = ApiClientGenerator::new(dir.path());
        let code = acg.generate_from_openapi("spec.json");
        assert!(code.starts_with("import requests\n\nclass APIClient:"));
        assert!(code.contains("def __init__(self, base_url=\"https://api.example.com\"):"));
        // Python keeps the braces: `/users/{id}` -> `get_users_{id}`.
        assert!(code.contains("def get_users_{id}(self, **kwargs):"));
        assert!(code.contains("return self.session.get(f\"{self.base_url}/users/{id}\", **kwargs)"));
        assert_eq!(acg.generate_from_openapi("missing.json"), "ERROR: Spec file not found");
        assert!(acg.generate_from_openapi("spec.json").contains("def post_users"));
        let curl = ApiClientGenerator::generate_curl(
            "post",
            "https://x/y",
            Some(&json!({"Content-Type": "application/json"})),
            Some(&json!("{\"a\":1}")),
        );
        assert_eq!(curl, "curl -X POST \"https://x/y\" -H 'Content-Type: application/json' -d '{\"a\":1}'");
        assert_eq!(ApiClientGenerator::generate_curl("get", "http://u", None, None), "curl -X GET \"http://u\"");
    }

    #[test]
    fn convert_to_class_matches_python_outputs() {
        let dir = tempdir().unwrap();
        let cr = CodeRefactorer::new(dir.path());

        // Fixtures and expectations generated with `apex/codegen.py` (the
        // generated body reads `def def foo(...)` in Python too).
        let cases = [
            (
                "a.py",
                "def foo(a):\n    return a\n\ndef bar():\n    pass\n",
                Some("class Foo:\n    def def foo(a):\n    return a\n\n\ndef bar():\n    pass\n"),
            ),
            ("b.py", "def foo(a):\n    return a", None),
            (
                "c.py",
                "def foo(a):\n    return a\n",
                Some("class Foo:\n    def def foo(a):\n    return a\n\n"),
            ),
            (
                "d.py",
                "x = 1\ndef foo(a):\n    return a\n\n\nclass Z:\n    pass\n",
                Some("x = 1\nclass Foo:\n    def def foo(a):\n    return a\n\n\n\nclass Z:\n    pass\n"),
            ),
        ];
        for (name, content, expected) in cases {
            let path = dir.path().join(name);
            std::fs::write(&path, content).unwrap();
            let result = cr.convert_to_class(name, "foo");
            match expected {
                Some(expected) => {
                    assert_eq!(result["success"], true, "{name}: {result}");
                    assert_eq!(std::fs::read_to_string(&path).unwrap(), expected, "{name}");
                }
                None => {
                    assert_eq!(result["error"], "Function not found", "{name}");
                    assert_eq!(std::fs::read_to_string(&path).unwrap(), content, "{name} unchanged");
                }
            }
        }
    }

    #[test]
    fn markdoc_skips_hidden_directories() {
        let dir = tempdir().unwrap();
        std::fs::create_dir(dir.path().join(".venv")).unwrap();
        std::fs::write(dir.path().join(".venv").join("site.py"), "class FromVenv:\n    pass\n").unwrap();
        std::fs::write(dir.path().join("app.py"), "class App:\n    pass\n").unwrap();
        std::fs::write(dir.path().join(".hidden.py"), "class Hidden:\n    pass\n").unwrap();
        let dg = DocumentationGenerator::new(dir.path());
        let doc = dg.generate_markdoc();
        assert!(doc.contains("- **App** (app.py)"), "got {doc}");
        assert!(!doc.contains("FromVenv"));
        assert!(!doc.contains("Hidden"));
    }

    #[test]
    fn readme_ignores_hidden_files() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join(".secret.py"), "x = 1\n").unwrap();
        std::fs::write(dir.path().join("main.py"), "x = 1\n").unwrap();
        let dg = DocumentationGenerator::new(dir.path());
        let readme = dg.generate_readme();
        assert!(readme.contains("### main"));
        assert!(!readme.contains(".secret"));
    }

    #[test]
    fn docs_generators() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("main.py"), "def run(a, b):\n    pass\n").unwrap();
        std::fs::create_dir(dir.path().join("pkg")).unwrap();
        std::fs::write(dir.path().join("pkg").join("mod.py"), "class Thing:\n    pass\n").unwrap();
        let dg = DocumentationGenerator::new(dir.path());

        let readme = dg.generate_readme();
        assert!(readme.starts_with("# Project\n\n## Overview"));
        assert!(readme.contains("### main\n\nRun with: `python main.py`"));

        let api = dg.generate_api_docs("main.py");
        assert!(api.starts_with("# API Documentation: main.py\n"));
        assert!(api.contains("## run\n"));
        assert!(api.contains("**Parameters:** a, b\n"));
        assert_eq!(dg.generate_api_docs("nope.py"), "ERROR: File not found");

        let markdoc = dg.generate_markdoc();
        assert!(markdoc.contains("- **Thing** (pkg/mod.py)"));
        assert!(markdoc.contains("# Documentation"));
    }

    #[test]
    fn readme_without_python_files() {
        let dir = tempdir().unwrap();
        let dg = DocumentationGenerator::new(dir.path());
        assert_eq!(dg.generate_readme(), "# Project\n\nNo Python files found.");
    }

    #[test]
    fn profiler_counts_match_python() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("p.py");
        std::fs::write(
            &file,
            "import os\nfrom x import y\n\nclass A:\n    pass\n\ndef f():\n    for i in range(3):\n        if i:\n            pass\n        else:\n            pass\n    while False:\n        pass\n",
        )
        .unwrap();
        let pp = PerformanceProfiler::new(dir.path());
        let profile = pp.profile_file("p.py");
        assert_eq!(profile["lines"], 15, "Python counts split('\\n') elements");
        assert_eq!(profile["functions"], 1);
        assert_eq!(profile["classes"], 1);
        assert_eq!(profile["imports"], 2);
        // for + while + if + else = 4
        assert_eq!(profile["complexity_score"], 4);
        assert_eq!(pp.profile_file("missing.py")["error"], "File not found");

        let empty = dir.path().join("empty.py");
        std::fs::write(&empty, "x = 1\n").unwrap();
        assert_eq!(pp.suggest_optimizations("empty.py"), vec!["Code looks optimized"]);

        let slow = dir.path().join("slow.py");
        std::fs::write(&slow, "data = []\nfor i in range(10):\n    data.append(i)\nf = open('x')\n").unwrap();
        let s = pp.suggest_optimizations("slow.py");
        assert!(s.contains(&"Use list comprehension instead of range loops".to_string()));
        assert!(s.contains(&"Consider using list comprehension or generator".to_string()));
        assert!(s.contains(&"Use 'with' statement for file operations".to_string()));
    }
}
