//! Repository context — port of `apex/context.py`.
//!
//! Builds the same repository map / git status / language statistics that
//! Python's `get_repo_map` tool returns, without pulling extra crates.

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// Extensions grouped the way Python groups them for the repo map.
fn source_exts() -> &'static [&'static str] {
    &[
        "py", "js", "ts", "jsx", "tsx", "go", "rs", "java", "c", "cpp", "h", "hpp", "rb", "php",
        "swift", "kt",
    ]
}

fn config_exts() -> &'static [&'static str] {
    &["json", "yaml", "yml", "toml", "ini", "cfg", "conf"]
}

fn doc_exts() -> &'static [&'static str] {
    &["md", "txt", "rst", "adoc"]
}

const IGNORE_DIRS: &[&str] = &[
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

/// Python: `get_repo_map(path)`.
pub fn get_repo_map(path: &Path) -> String {
    if !path.exists() {
        return format!("ERROR: Path does not exist: {}", path.display());
    }

    let mut lines = vec![
        format!(
            "Repository: {}",
            path.file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_default()
        ),
        "=".repeat(50),
    ];

    let mut source_files: Vec<String> = Vec::new();
    let mut config_files: Vec<String> = Vec::new();
    let mut doc_files: Vec<String> = Vec::new();
    let mut subdirs: Vec<String> = Vec::new();

    let entries = match fs::read_dir(path) {
        Ok(e) => e,
        Err(_) => return "ERROR: Permission denied".to_string(),
    };
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with('.') || IGNORE_DIRS.contains(&name.as_str()) {
            continue;
        }
        let p = entry.path();
        if p.is_dir() {
            subdirs.push(name);
        } else if source_exts().contains(&p.extension().and_then(|e| e.to_str()).unwrap_or("")) {
            source_files.push(name);
        } else if config_exts().contains(&p.extension().and_then(|e| e.to_str()).unwrap_or("")) {
            config_files.push(name);
        } else if doc_exts().contains(&p.extension().and_then(|e| e.to_str()).unwrap_or("")) {
            doc_files.push(name);
        }
    }

    if !subdirs.is_empty() {
        lines.push("\n[DIRECTORIES]".to_string());
        let mut d = subdirs;
        d.sort();
        for name in d.iter().take(10) {
            lines.push(format!("  📁 {name}/"));
        }
    }
    if !source_files.is_empty() {
        lines.push("\n[SOURCE FILES]".to_string());
        let mut f = source_files;
        f.sort();
        for name in f.iter().take(15) {
            lines.push(format!("  • {name}"));
        }
    }
    if !config_files.is_empty() {
        lines.push("\n[CONFIG FILES]".to_string());
        let mut f = config_files;
        f.sort();
        for name in f {
            lines.push(format!("  ⚙ {name}"));
        }
    }
    if !doc_files.is_empty() {
        lines.push("\n[DOCUMENTATION]".to_string());
        let mut f = doc_files;
        f.sort();
        for name in f.iter().take(5) {
            lines.push(format!("  📄 {name}"));
        }
    }

    let git_info = get_git_info(path);
    if !git_info.is_empty() {
        lines.push(format!("\n{git_info}"));
    }
    lines.join("\n")
}

/// Python: `get_git_info(path)` — branch + change count, empty when not a repo.
pub fn get_git_info(path: &Path) -> String {
    let git_dir = path.join(".git");
    if !git_dir.exists() {
        return String::new();
    }
    let head = match fs::read_to_string(git_dir.join("HEAD")) {
        Ok(h) => h.trim().to_string(),
        Err(_) => return String::new(),
    };
    let branch = if let Some(rest) = head.strip_prefix("ref: ") {
        rest.rsplit('/').next().unwrap_or(rest).to_string()
    } else {
        head
    };
    let output = Command::new("git")
        .args(["status", "--porcelain"])
        .current_dir(path)
        .output();
    let changes = match output {
        Ok(o) => {
            let stdout = String::from_utf8_lossy(&o.stdout);
            if stdout.trim().is_empty() {
                0
            } else {
                stdout.trim().split('\n').count()
            }
        }
        Err(_) => return String::new(),
    };
    if changes > 0 {
        format!("[GIT] Branch: {branch} ({changes} changes)")
    } else {
        format!("[GIT] Branch: {branch} (clean)")
    }
}

/// Python: `get_language_stats(path)`.
pub fn get_language_stats(path: &Path) -> Value {
    let ext_map = [
        ("py", "Python"),
        ("js", "JavaScript"),
        ("ts", "TypeScript"),
        ("jsx", "React"),
        ("tsx", "React"),
        ("go", "Go"),
        ("rs", "Rust"),
        ("java", "Java"),
        ("c", "C"),
        ("cpp", "C++"),
        ("rb", "Ruby"),
        ("php", "PHP"),
        ("swift", "Swift"),
        ("kt", "Kotlin"),
        ("scala", "Scala"),
    ];
    let ignore = [
        ".git",
        "node_modules",
        "__pycache__",
        "venv",
        ".venv",
        "target",
    ];
    let mut stats: Vec<(String, u64)> = Vec::new();
    let mut stack = vec![path.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(rd) = fs::read_dir(&dir) else { continue };
        for entry in rd.flatten() {
            let p = entry.path();
            if p.is_dir() {
                let name = p
                    .file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();
                if ignore.contains(&name.as_str()) {
                    continue;
                }
                stack.push(p);
            } else {
                let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                let lang = ext_map
                    .iter()
                    .find(|(e, _)| *e == ext)
                    .map(|(_, l)| *l)
                    .unwrap_or("Other");
                if let Some(slot) = stats.iter_mut().find(|(l, _)| l == lang) {
                    slot.1 += 1;
                } else {
                    stats.push((lang.to_string(), 1));
                }
            }
        }
    }
    let mut obj = serde_json::Map::new();
    for (lang, count) in stats {
        obj.insert(lang, json!(count));
    }
    Value::Object(obj)
}

/// Python: `generate_ctags(path)` — first 50 code files from `git ls-files`.
pub fn generate_ctags(path: &Path) -> String {
    if !path.join(".git").exists() {
        return "ERROR: Not a git repository".to_string();
    }
    let Ok(o) = Command::new("git")
        .args(["ls-files", "-z"])
        .current_dir(path)
        .output()
    else {
        return "ERROR: git ls-files failed".to_string();
    };
    let stdout = String::from_utf8_lossy(&o.stdout);
    let files: Vec<&str> = stdout.split('\0').filter(|s| !s.is_empty()).collect();
    let code_exts = ["py", "js", "ts", "go", "rs", "java"];
    let code_files: Vec<&str> = files
        .iter()
        .copied()
        .filter(|f| {
            let ext = f.rsplit('.').next().unwrap_or("");
            code_exts.contains(&ext) && f.contains('.')
        })
        .take(50)
        .collect();
    if code_files.is_empty() {
        "[no code files found]".to_string()
    } else {
        code_files.join("\n")
    }
}

/// ASCII tree, mirroring Python's `get_file_tree` (dirs first, dotfiles skipped).
pub fn file_tree(path: &Path, max_depth: usize) -> Result<String, String> {
    if !path.exists() {
        return Err(format!("ERROR: Path not found: {}", path.display()));
    }
    let root = path
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_default();
    let mut lines = vec![if path.is_dir() {
        format!("{root}/")
    } else {
        root
    }];
    if path.is_dir() {
        walk_tree(path, "", 0, max_depth, &mut lines);
    }
    Ok(lines.join("\n"))
}

fn walk_tree(dir: &Path, prefix: &str, depth: usize, max_depth: usize, out: &mut Vec<String>) {
    if depth > max_depth {
        return;
    }
    let Ok(rd) = fs::read_dir(dir) else {
        out.push(format!("{prefix}[permission denied]"));
        return;
    };
    let mut entries: Vec<PathBuf> = rd.flatten().map(|e| e.path()).collect();
    // Dirs first, then name (case-insensitive).
    entries.sort_by_key(|p| {
        let is_dir = p.is_dir();
        let name = p
            .file_name()
            .map(|n| n.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        (!is_dir, name)
    });
    let visible: Vec<&PathBuf> = entries
        .iter()
        .filter(|p| {
            !p.file_name()
                .map(|n| n.to_string_lossy().starts_with('.'))
                .unwrap_or(false)
        })
        .collect();
    for (i, entry) in visible.iter().enumerate() {
        let is_last = i == visible.len() - 1;
        let connector = if is_last { "└── " } else { "├── " };
        let name = entry
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();
        out.push(format!("{prefix}{connector}{name}"));
        if entry.is_dir() {
            let extension = if is_last { "    " } else { "│   " };
            walk_tree(
                entry,
                &format!("{prefix}{extension}"),
                depth + 1,
                max_depth,
                out,
            );
        }
    }
}

/// Minimal glob matcher (`*`, `**`, `?`, `[...]`), matching the whole relative
/// path. Shared by `glob_search` and the file tree walk.
pub fn glob_match(pattern: &str, text: &str) -> bool {
    fn rec(p: &[u8], t: &[u8]) -> bool {
        if p.is_empty() {
            return t.is_empty();
        }
        match p[0] {
            b'*' => {
                if p.len() > 1 && p[1] == b'*' {
                    // `**` spans path separators; `**/` also matches no dir.
                    let rest = if p.len() > 2 && p[2] == b'/' {
                        &p[3..]
                    } else {
                        &p[2..]
                    };
                    for i in 0..=t.len() {
                        if rec(rest, &t[i..]) {
                            return true;
                        }
                    }
                    return false;
                }
                // A single `*` never crosses a `/` (Python's Path.glob).
                let end = t.iter().position(|&c| c == b'/').unwrap_or(t.len());
                for i in 0..=end {
                    if rec(&p[1..], &t[i..]) {
                        return true;
                    }
                }
                false
            }
            b'?' => !t.is_empty() && t[0] != b'/' && rec(&p[1..], &t[1..]),
            b'[' => {
                let Some(close) = p.iter().position(|&c| c == b']') else {
                    return !t.is_empty() && t[0] == b'[' && rec(&p[1..], &t[1..]);
                };
                let negate = p[1] == b'!' || p[1] == b'^';
                let set = &p[1..close];
                let mut hit = false;
                let mut i = if negate { 1 } else { 0 };
                while i < set.len() {
                    if i + 2 < set.len() && set[i + 1] == b'-' {
                        if !t.is_empty() && set[i] <= t[0] && t[0] <= set[i + 2] {
                            hit = true;
                        }
                        i += 3;
                    } else {
                        if !t.is_empty() && set[i] == t[0] {
                            hit = true;
                        }
                        i += 1;
                    }
                }
                if hit != negate && !t.is_empty() {
                    rec(&p[close + 1..], &t[1..])
                } else {
                    false
                }
            }
            c => !t.is_empty() && c == t[0] && rec(&p[1..], &t[1..]),
        }
    }
    rec(pattern.as_bytes(), text.as_bytes())
}

/// Python: `directory.glob(pattern)` — relative paths, files and directories.
pub fn glob_search(directory: &Path, pattern: &str) -> Result<Vec<String>, String> {
    if !directory.exists() {
        return Err(format!(
            "ERROR: Directory not found: {}",
            directory.display()
        ));
    }
    let mut matches: Vec<String> = Vec::new();
    let mut stack = vec![directory.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(rd) = fs::read_dir(&dir) else { continue };
        for entry in rd.flatten() {
            let p = entry.path();
            let rel = p
                .strip_prefix(directory)
                .unwrap_or(&p)
                .to_string_lossy()
                .replace('\\', "/");
            if glob_match(pattern, &rel) {
                matches.push(rel.clone());
            }
            if p.is_dir() {
                stack.push(p);
            }
        }
    }
    matches.sort();
    Ok(matches)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn repo_map_groups_and_includes_git_info() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("main.py"), "x = 1\n").unwrap();
        fs::write(dir.path().join("README.md"), "# hi\n").unwrap();
        fs::write(dir.path().join("package.json"), "{}\n").unwrap();
        fs::create_dir(dir.path().join("src")).unwrap();
        fs::write(dir.path().join(".hidden.py"), "x = 1\n").unwrap();

        let map = get_repo_map(dir.path());
        assert!(map.starts_with("Repository: "), "got {map}");
        assert!(map.contains("[DIRECTORIES]") && map.contains("📁 src/"));
        assert!(map.contains("[SOURCE FILES]") && map.contains("• main.py"));
        assert!(map.contains("[CONFIG FILES]") && map.contains("⚙ package.json"));
        assert!(map.contains("[DOCUMENTATION]") && map.contains("📄 README.md"));
        assert!(!map.contains(".hidden"), "dotfiles skipped: {map}");
        assert!(!map.contains("[GIT]"), "tempdir is not a git repo");
        assert_eq!(
            get_repo_map(&dir.path().join("missing")),
            "ERROR: Path does not exist: ".to_string()
                + &dir.path().join("missing").to_string_lossy()
        );
    }

    #[test]
    fn repo_map_ignores_noise_directories() {
        let dir = tempdir().unwrap();
        for name in ["node_modules", "target", "__pycache__", ".git"] {
            fs::create_dir_all(dir.path().join(name)).unwrap();
            fs::write(dir.path().join(name).join("x.py"), "x = 1\n").unwrap();
        }
        let map = get_repo_map(dir.path());
        assert!(!map.contains("node_modules"));
        assert!(!map.contains("target/"));
    }

    #[test]
    fn language_stats_and_ctags() {
        let dir = tempdir().unwrap();
        fs::write(dir.path().join("a.py"), "x = 1\n").unwrap();
        fs::write(dir.path().join("b.rs"), "fn main() {}\n").unwrap();
        fs::write(dir.path().join("c.txt"), "hi\n").unwrap();
        fs::create_dir(dir.path().join("node_modules")).unwrap();
        fs::write(dir.path().join("node_modules").join("d.py"), "x = 1\n").unwrap();
        let stats = get_language_stats(dir.path());
        assert_eq!(stats["Python"], 1);
        assert_eq!(stats["Rust"], 1);
        assert_eq!(stats["Other"], 1);
        assert_eq!(generate_ctags(dir.path()), "ERROR: Not a git repository");

        // With a git repo, ctags lists code files.
        for args in [
            vec!["init", "-q"],
            vec!["add", "."],
            vec![
                "-c",
                "user.email=t@e.com",
                "-c",
                "user.name=T",
                "commit",
                "-qm",
                "init",
            ],
        ] {
            std::process::Command::new("git")
                .args(&args)
                .current_dir(dir.path())
                .output()
                .unwrap();
        }
        // `git ls-files` tracks node_modules too (Python does not filter it).
        assert_eq!(generate_ctags(dir.path()), "a.py\nb.rs\nnode_modules/d.py");
    }

    #[test]
    fn file_tree_matches_python_layout() {
        let dir = tempdir().unwrap();
        fs::create_dir(dir.path().join("sub")).unwrap();
        fs::write(dir.path().join("a.py"), "x = 1\n").unwrap();
        fs::write(dir.path().join("sub").join("b.py"), "x = 1\n").unwrap();
        fs::write(dir.path().join(".hidden"), "x\n").unwrap();
        let tree = file_tree(dir.path(), 3).unwrap();
        let dir_name = dir
            .path()
            .file_name()
            .unwrap()
            .to_string_lossy()
            .to_string();
        assert!(tree.starts_with(&format!("{dir_name}/\n")), "got {tree}");
        assert!(tree.contains("├── sub"), "got {tree}");
        assert!(tree.contains("│   └── b.py"), "got {tree}");
        assert!(tree.contains("└── a.py"), "got {tree}");
        assert!(!tree.contains("hidden"), "dotfiles skipped: {tree}");
        assert!(tree.ends_with("└── a.py"), "dirs come first: {tree}");
    }

    #[test]
    fn file_tree_depth_limit() {
        let dir = tempdir().unwrap();
        // Use a fixed root name: `tempdir()` names may contain `a`/`b`/`c`
        // (e.g. `.tmp4dcMLz` on Linux), which would make the assertions below
        // pass or fail by accident.
        let root = dir.path().join("root");
        let deep = root.join("a/b/c");
        fs::create_dir_all(&deep).unwrap();
        fs::write(deep.join("x.py"), "x = 1\n").unwrap();
        let tree = file_tree(&root, 1).unwrap();
        assert!(tree.contains("a"), "got {tree}");
        assert!(!tree.contains("c"), "depth limited: {tree}");
        assert!(!tree.contains("x.py"), "depth limited: {tree}");
    }

    #[test]
    fn glob_search_and_match() {
        let dir = tempdir().unwrap();
        fs::create_dir_all(dir.path().join("pkg").join("nested")).unwrap();
        fs::write(dir.path().join("main.py"), "x = 1\n").unwrap();
        fs::write(dir.path().join("pkg").join("mod.py"), "x = 1\n").unwrap();
        fs::write(
            dir.path().join("pkg").join("nested").join("deep.py"),
            "x = 1\n",
        )
        .unwrap();
        fs::write(dir.path().join("notes.txt"), "x\n").unwrap();

        let all = glob_search(dir.path(), "**/*").unwrap();
        assert!(all.contains(&"main.py".to_string()));
        assert!(all.contains(&"pkg/mod.py".to_string()));
        assert!(all.contains(&"pkg/nested/deep.py".to_string()));
        assert!(
            all.contains(&"pkg".to_string()),
            "directories match too: {all:?}"
        );

        let top = glob_search(dir.path(), "*.py").unwrap();
        assert_eq!(top, vec!["main.py"]);
        let nested = glob_search(dir.path(), "**/*.py").unwrap();
        assert_eq!(nested, vec!["main.py", "pkg/mod.py", "pkg/nested/deep.py"]);
        assert_eq!(
            glob_search(dir.path(), "*.ts").unwrap(),
            Vec::<String>::new()
        );
        assert!(glob_search(&dir.path().join("missing"), "*.py").is_err());

        assert!(glob_match("[a-c].py", "b.py"));
        assert!(!glob_match("[!a-c].py", "b.py"));
        assert!(glob_match("**/*.py", "pkg/deep.py"));
    }
}
