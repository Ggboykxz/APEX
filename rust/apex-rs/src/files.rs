//! File tools — port of `apex/tools.py` file operations.
//!
//! Implements: apply_edit, preview_edit, create_directory, delete_file,
//! batch_read, batch_write, read_image, glob_search.

use std::fs;
use std::path::{Path, PathBuf};

use base64::Engine;
use serde_json::Value;

/// Resolve a path relative to cwd, mirroring Python's `_resolve`.
fn resolve(path: &str, cwd: &Path) -> PathBuf {
    let p = Path::new(path);
    if p.is_absolute() {
        p.to_path_buf()
    } else {
        cwd.join(path)
    }
}

/// `apply_edit` — Replace the first occurrence of `old_string` with `new_string`
/// in a file.
pub fn apply_edit(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let old_string = args
        .get("old_string")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let new_string = args
        .get("new_string")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let full = resolve(path, cwd);

    if !full.exists() {
        return format!("ERROR: File not found: {}", full.display());
    }

    match fs::read_to_string(&full) {
        Ok(content) => {
            if !content.contains(old_string) {
                return "ERROR: String not found in file. Use read_file to see content."
                    .to_string();
            }
            let new_content = content.replacen(old_string, new_string, 1);
            match fs::write(&full, new_content) {
                Ok(_) => format!("SUCCESS: Edited {}", full.display()),
                Err(e) => format!("ERROR: Cannot edit file: {e}"),
            }
        }
        Err(e) => format!("ERROR: Cannot read file: {e}"),
    }
}

/// `preview_edit` — Preview an edit without applying it. Shows the unified diff
/// between the current file content and the result of applying the edit.
pub fn preview_edit(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let old_string = args
        .get("old_string")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let new_string = args
        .get("new_string")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    let full = resolve(path, cwd);

    if !full.exists() {
        return format!("ERROR: File not found: {}", full.display());
    }

    match fs::read_to_string(&full) {
        Ok(content) => {
            if !content.contains(old_string) {
                return "ERROR: String not found in file. Use read_file to see content."
                    .to_string();
            }
            let new_content = content.replacen(old_string, new_string, 1);

            let old_lines: Vec<&str> = content.lines().collect();
            let new_lines: Vec<&str> = new_content.lines().collect();

            let diff: Vec<String> = difflib_unified_diff(
                &old_lines,
                &new_lines,
                path,
                &format!("{} (modified)", path),
            );

            if diff.is_empty() {
                "[No changes]".to_string()
            } else {
                format!("PREVIEW:\n{}", diff.join("\n"))
            }
        }
        Err(e) => format!("ERROR: Cannot read file: {e}"),
    }
}

/// `create_directory` — Create a directory (and parents if needed).
pub fn create_directory(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let full = resolve(path, cwd);

    match fs::create_dir_all(&full) {
        Ok(_) => format!("SUCCESS: Created directory {}", full.display()),
        Err(e) => format!("ERROR: Cannot create directory: {e}"),
    }
}

/// `delete_file` — Delete a file or empty directory.
pub fn delete_file(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let full = resolve(path, cwd);

    if !full.exists() {
        return format!("ERROR: Path not found: {}", full.display());
    }

    match fs::remove_dir_all(&full) {
        Ok(_) => format!("SUCCESS: Deleted {}", full.display()),
        Err(e) => format!("ERROR: Cannot delete: {e}"),
    }
}

/// `batch_read` — Read multiple files at once.
pub fn batch_read(args: &Value, cwd: &Path) -> String {
    let empty_paths: Vec<Value> = vec![];
    let paths: Vec<String> = args
        .get("paths")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty_paths)
        .iter()
        .filter_map(|v| v.as_str().map(|s| s.to_string()))
        .collect();

    if paths.is_empty() {
        return "ERROR: No paths provided".to_string();
    }

    if paths.len() > 50 {
        return "ERROR: Too many files in batch (max 50)".to_string();
    }

    let mut results: Vec<String> = Vec::new();
    for p in &paths {
        let full = resolve(p, cwd);
        match fs::read_to_string(&full) {
            Ok(content) => {
                results.push(format!("--- {}\n{}", p, content));
            }
            Err(e) => {
                results.push(format!("--- {}\nERROR: {e}", p));
            }
        }
    }

    results.join("\n")
}

/// `batch_write` — Write multiple files at once.
pub fn batch_write(args: &Value, cwd: &Path) -> String {
    let empty_ops: Vec<Value> = vec![];
    let operations = args
        .get("operations")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty_ops);

    if operations.is_empty() {
        return "ERROR: No operations provided".to_string();
    }

    if operations.len() > 50 {
        return "ERROR: Too many files in batch (max 50)".to_string();
    }

    let mut success_count = 0;
    let mut errors: Vec<String> = Vec::new();

    for op in operations {
        let path = op.get("path").and_then(|v| v.as_str()).unwrap_or("");
        let content = op.get("content").and_then(|v| v.as_str()).unwrap_or("");
        let full = resolve(path, cwd);

        match fs::write(&full, content) {
            Ok(_) => {
                success_count += 1;
            }
            Err(e) => {
                errors.push(format!("{}: {e}", path));
            }
        }
    }

    let mut output = format!("SUCCESS: {success_count} file(s) written");
    if !errors.is_empty() {
        output.push('\n');
        output.push_str(&errors.join("\n"));
    }
    output
}

/// `read_image` — Read an image file and return base64 encoding.
pub fn read_image(args: &Value, cwd: &Path) -> String {
    let path = args.get("path").and_then(|v| v.as_str()).unwrap_or("");
    let full = resolve(path, cwd);

    if !full.exists() {
        return format!("ERROR: Image not found: {}", full.display());
    }

    let image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"];
    let ext = full
        .extension()
        .unwrap_or_default()
        .to_string_lossy()
        .to_lowercase();
    if !image_extensions.iter().any(|e| e == &ext) {
        return format!(
            "ERROR: Not a supported image format: {}. Supported: {:?}",
            full.extension().unwrap_or_default().to_string_lossy(),
            image_extensions
        );
    }

    match fs::read(&full) {
        Ok(data) => {
            let encoded = base64::engine::general_purpose::STANDARD.encode(&data);
            format!(
                "data:image/{};base64,{}",
                full.extension().unwrap_or_default().to_string_lossy(),
                encoded
            )
        }
        Err(e) => format!("ERROR: Cannot read image: {e}"),
    }
}

/// `glob_search` — Find files by glob pattern.
pub fn glob_search(args: &Value, cwd: &Path) -> String {
    let pattern = args.get("pattern").and_then(|v| v.as_str()).unwrap_or("");
    let directory = args
        .get("directory")
        .and_then(|v| v.as_str())
        .unwrap_or(".");

    let dir = resolve(directory, cwd);
    if !dir.exists() {
        return format!("ERROR: Directory not found: {}", directory);
    }

    let mut matches: Vec<String> = Vec::new();
    let glob_pattern = format!("{}/{}", dir.display(), pattern).replace('\\', "/");
    if let Ok(entries) = glob::glob(&glob_pattern) {
        for entry in entries.flatten() {
            if entry.is_file() {
                if let Ok(rel) = entry.strip_prefix(&dir) {
                    matches.push(rel.to_string_lossy().to_string());
                }
            }
        }
    }

    if matches.is_empty() {
        return format!("no files match pattern '{pattern}'");
    }

    matches.sort();
    matches.join("\n")
}

/// Simple unified-diff implementation (no external crate dependency).
fn difflib_unified_diff(
    before: &[&str],
    after: &[&str],
    from_file: &str,
    to_file: &str,
) -> Vec<String> {
    let mut result: Vec<String> = Vec::new();
    result.push(format!("--- {}", from_file));
    result.push(format!("+++ {}", to_file));

    let mut i = 0;
    let mut j = 0;
    while i < before.len() || j < after.len() {
        if i < before.len() && j < after.len() && before[i] == after[j] {
            i += 1;
            j += 1;
        } else if i < before.len() {
            result.push(format!("-{}", before[i]));
            i += 1;
        } else if j < after.len() {
            result.push(format!("+{}", after[j]));
            j += 1;
        } else {
            break;
        }
    }

    if result.len() <= 2 {
        Vec::new()
    } else {
        result
    }
}
