//! Port of `apex/apply_patch.py` — a dependency-free multi-file patch engine.
//!
//! The engine understands two patch dialects:
//!
//! * Codex-style patches delimited by `*** Begin Patch` / `*** End Patch`
//!   with `*** Add File:`, `*** Update File:`, and `*** Delete File:`
//!   directives.
//! * Unified diffs with `--- a/path` / `+++ b/path` headers and `@@` hunks.
//!
//! Every patch is validated in memory before anything is written. The
//! on-disk apply phase writes files through a temporary file in the
//! destination directory and `fs::rename`, then removes deleted files only
//! once all writes have succeeded. A failure rolls previously written files
//! back on a best-effort basis.

use regex::Regex;
use std::collections::HashSet;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

pub const MAX_PATCH_BYTES: usize = 1024 * 1024;
pub const MAX_FILE_BYTES: usize = 512 * 1024;

const CODEX_BEGIN: &str = "*** Begin Patch";
const CODEX_END: &str = "*** End Patch";
const CODEX_ADD: &str = "*** Add File:";
const CODEX_UPDATE: &str = "*** Update File:";
const CODEX_DELETE: &str = "*** Delete File:";
const NO_NEWLINE: &str = "\\ No newline at end of file";
const UNIFIED_METADATA: &[&str] = &[
    "index ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
];

/// A patch could not be parsed, validated, or applied.
///
/// `reason` is a short machine-readable token such as `context_mismatch` or
/// `path_traversal`; `path` is the offending repository-relative path when
/// one is known.
#[derive(Debug)]
pub struct PatchError {
    pub reason: &'static str,
    pub message: String,
    pub path: Option<String>,
}

impl PatchError {
    fn new(reason: &'static str, message: impl Into<String>) -> Self {
        Self {
            reason,
            message: message.into(),
            path: None,
        }
    }

    fn with_path(reason: &'static str, message: impl Into<String>, path: &str) -> Self {
        Self {
            reason,
            message: message.into(),
            path: Some(path.to_string()),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    Add,
    Update,
    Delete,
}

/// One file touched by a patch, with its fully resolved contents.
///
/// `new_text` is the resulting file contents for `add`/`update` operations
/// and empty for `delete`.
#[derive(Debug)]
pub struct PatchFile {
    pub path: String,
    pub kind: Kind,
    pub additions: usize,
    pub deletions: usize,
    new_text: String,
}

/// The resolved result of a patch.
#[derive(Debug)]
pub struct PatchResult {
    pub dry_run: bool,
    pub files: Vec<PatchFile>,
    pub additions: usize,
    pub deletions: usize,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Default)]
struct Hunk {
    old_start: Option<usize>,
    old_count: Option<usize>,
    ops: Vec<(char, String)>,
    new_no_newline: bool,
}

#[derive(Debug, Clone)]
struct RawFile {
    path: String,
    kind: Kind,
    hunks: Vec<Hunk>,
    no_newline: bool,
}

/// Validate and atomically apply `patch` under `root`.
///
/// With `dry_run` every check runs but no file, directory, or temporary file
/// is created.
pub fn apply_patch(patch: &str, root: &Path, dry_run: bool) -> Result<PatchResult, PatchError> {
    let (lines, patch_eol) = normalize_patch(patch)?;
    let resolved_root = validate_root(root)?;

    let start = lines
        .iter()
        .position(|l| !l.trim().is_empty())
        .ok_or_else(|| PatchError::new("empty_patch", "patch is empty"))?;

    let first = lines[start].trim();
    let raw_files = if first == CODEX_BEGIN {
        parse_codex(&lines, start)?
    } else if lines[start].starts_with("--- ") || lines[start].starts_with("diff --git ") {
        parse_unified(&lines, start)?
    } else if first.starts_with("***") {
        return Err(PatchError::new(
            "unknown_format",
            "Codex patches must start with '*** Begin Patch'",
        ));
    } else {
        return Err(PatchError::new(
            "unknown_format",
            "expected a '*** Begin Patch' or '--- a/path' patch header",
        ));
    };

    if raw_files.is_empty() {
        return Err(PatchError::new(
            "empty_patch",
            "patch does not touch any files",
        ));
    }

    // Reject duplicate targets before resolving any contents.
    let mut seen: HashSet<PathBuf> = HashSet::new();
    for raw in &raw_files {
        let (relative, _candidate, identity) = validate_path(&raw.path, &resolved_root)?;
        if !seen.insert(identity) {
            return Err(PatchError::with_path(
                "duplicate_path",
                format!("patch touches '{relative}' more than once"),
                &relative,
            ));
        }
    }

    let mut files: Vec<PatchFile> = Vec::new();
    let mut warnings: Vec<String> = Vec::new();
    for raw in &raw_files {
        let (item, item_warnings) = resolve_file(raw, &resolved_root, &patch_eol)?;
        warnings.extend(item_warnings);
        files.push(item);
    }

    if !dry_run {
        write_files(&files, &resolved_root)?;
    }

    Ok(PatchResult {
        dry_run,
        additions: files.iter().map(|f| f.additions).sum(),
        deletions: files.iter().map(|f| f.deletions).sum(),
        files,
        warnings,
    })
}

// ---------------------------------------------------------------------------
// Patch text and format parsing
// ---------------------------------------------------------------------------

fn normalize_patch(patch: &str) -> Result<(Vec<String>, String), PatchError> {
    if patch.contains('\0') {
        return Err(PatchError::new("binary_patch", "patch contains NUL bytes"));
    }
    if patch.len() > MAX_PATCH_BYTES {
        return Err(PatchError::new(
            "patch_too_large",
            format!("patch is {} bytes; limit is {MAX_PATCH_BYTES}", patch.len()),
        ));
    }

    let crlf_count = patch.matches("\r\n").count();
    let lf_count = patch.matches('\n').count();
    let patch_eol = if crlf_count > 0 && crlf_count * 2 >= lf_count {
        "\r\n"
    } else {
        "\n"
    };
    let text = patch.replace("\r\n", "\n").replace('\r', "\n");
    let mut lines: Vec<String> = text.split('\n').map(String::from).collect();
    if lines.last().is_some_and(|l| l.is_empty()) {
        lines.pop();
    }
    Ok((lines, patch_eol.to_string()))
}

fn validate_root(root: &Path) -> Result<PathBuf, PatchError> {
    let resolved = root.canonicalize().map_err(|_| {
        PatchError::new(
            "invalid_root",
            format!("cannot resolve root: {}", root.display()),
        )
    })?;
    if !resolved.is_dir() {
        return Err(PatchError::new(
            "invalid_root",
            format!("root is not a directory: {}", root.display()),
        ));
    }
    Ok(resolved)
}

fn hunk_header_re() -> &'static Regex {
    static RE: std::sync::OnceLock<Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(
            r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?:.*)$",
        )
        .expect("static regex")
    })
}

fn parse_codex(lines: &[String], start: usize) -> Result<Vec<RawFile>, PatchError> {
    if lines[start].trim() != CODEX_BEGIN {
        return Err(PatchError::new(
            "unknown_format",
            "missing '*** Begin Patch'",
        ));
    }

    let mut files: Vec<RawFile> = Vec::new();
    let mut index = start + 1;
    let mut ended = false;
    while index < lines.len() {
        let stripped = lines[index].trim();
        if stripped.is_empty() {
            index += 1;
            continue;
        }
        if stripped == CODEX_END {
            ended = true;
            index += 1;
            break;
        }
        if stripped.starts_with(CODEX_ADD) {
            let path = codex_path(&lines[index], CODEX_ADD, index)?;
            index += 1;
            let mut ops: Vec<(char, String)> = Vec::new();
            let mut no_newline = false;
            let mut marker_seen = false;
            while index < lines.len() && !is_codex_directive(&lines[index]) {
                let raw = &lines[index];
                if raw.starts_with(NO_NEWLINE) {
                    if marker_seen || ops.is_empty() {
                        return Err(PatchError::with_path(
                            "malformed_patch",
                            "unexpected 'No newline' marker in added file",
                            &path,
                        ));
                    }
                    no_newline = true;
                    marker_seen = true;
                } else if marker_seen && !raw.trim().is_empty() {
                    return Err(PatchError::with_path(
                        "malformed_patch",
                        "'No newline' marker must terminate the file body",
                        &path,
                    ));
                } else if let Some(rest) = raw.strip_prefix('+') {
                    ops.push(('+', rest.to_string()));
                } else {
                    return Err(PatchError::with_path(
                        "malformed_patch",
                        "added file lines must start with '+'",
                        &path,
                    ));
                }
                index += 1;
            }
            let hunks = if ops.is_empty() {
                Vec::new()
            } else {
                vec![Hunk {
                    old_start: None,
                    old_count: None,
                    ops,
                    new_no_newline: false,
                }]
            };
            files.push(RawFile {
                path,
                kind: Kind::Add,
                hunks,
                no_newline,
            });
            continue;
        }
        if stripped.starts_with(CODEX_UPDATE) {
            let path = codex_path(&lines[index], CODEX_UPDATE, index)?;
            let (hunks, next) = parse_codex_update(lines, index + 1, &path)?;
            files.push(RawFile {
                path,
                kind: Kind::Update,
                hunks,
                no_newline: false,
            });
            index = next;
            continue;
        }
        if stripped.starts_with(CODEX_DELETE) {
            let path = codex_path(&lines[index], CODEX_DELETE, index)?;
            index += 1;
            while index < lines.len() && !is_codex_directive(&lines[index]) {
                if !lines[index].trim().is_empty() {
                    return Err(PatchError::with_path(
                        "malformed_patch",
                        "a deleted file cannot carry content",
                        &path,
                    ));
                }
                index += 1;
            }
            files.push(RawFile {
                path,
                kind: Kind::Delete,
                hunks: Vec::new(),
                no_newline: false,
            });
            continue;
        }
        if stripped.starts_with("***") {
            return Err(PatchError::new(
                "unsupported_directive",
                format!("unsupported Codex directive: {stripped}"),
            ));
        }
        return Err(PatchError::new(
            "malformed_patch",
            format!("unexpected content outside a Codex file section: '{stripped}'"),
        ));
    }

    if !ended {
        return Err(PatchError::new(
            "unterminated_patch",
            "missing '*** End Patch'",
        ));
    }
    while index < lines.len() {
        if !lines[index].trim().is_empty() {
            return Err(PatchError::new(
                "trailing_content",
                "unexpected content after '*** End Patch'",
            ));
        }
        index += 1;
    }
    Ok(files)
}

fn codex_path(line: &str, directive: &str, index: usize) -> Result<String, PatchError> {
    let raw = line.trim()[directive.len()..].trim().to_string();
    if raw.is_empty() {
        return Err(PatchError::new(
            "malformed_patch",
            format!(
                "{} requires a path (line {})",
                directive.trim_end_matches(':'),
                index + 1
            ),
        ));
    }
    Ok(raw)
}

fn is_codex_directive(line: &str) -> bool {
    let stripped = line.trim();
    stripped == CODEX_END
        || stripped.starts_with(CODEX_ADD)
        || stripped.starts_with(CODEX_UPDATE)
        || stripped.starts_with(CODEX_DELETE)
        || stripped.starts_with("***")
}

fn finish_current_hunk(
    hunks: &mut Vec<Hunk>,
    current: &mut Hunk,
    current_started: &mut bool,
    marker_seen: &mut bool,
    path: &str,
) -> Result<(), PatchError> {
    if !current.ops.is_empty() {
        hunks.push(std::mem::take(current));
    } else if *current_started {
        return Err(PatchError::with_path(
            "empty_hunk",
            "update hunk contains no lines",
            path,
        ));
    }
    *current_started = false;
    *marker_seen = false;
    Ok(())
}

fn parse_codex_update(
    lines: &[String],
    start: usize,
    path: &str,
) -> Result<(Vec<Hunk>, usize), PatchError> {
    let mut hunks: Vec<Hunk> = Vec::new();
    let mut current = Hunk {
        old_start: None,
        old_count: None,
        ops: Vec::new(),
        new_no_newline: false,
    };
    let mut current_started = false;
    let mut marker_seen = false;
    let mut index = start;

    while index < lines.len() && !is_codex_directive(&lines[index]) {
        let raw = &lines[index];
        if raw.starts_with("@@") {
            finish_current_hunk(
                &mut hunks,
                &mut current,
                &mut current_started,
                &mut marker_seen,
                path,
            )?;
            current_started = true;
            index += 1;
            continue;
        }
        if raw.starts_with(NO_NEWLINE) {
            if marker_seen || current.ops.is_empty() {
                return Err(PatchError::with_path(
                    "malformed_patch",
                    "unexpected 'No newline' marker",
                    path,
                ));
            }
            let last_prefix = current.ops.last().map(|(p, _)| *p).unwrap();
            current.new_no_newline = last_prefix == ' ' || last_prefix == '+';
            marker_seen = true;
            index += 1;
            continue;
        }
        if marker_seen {
            return Err(PatchError::with_path(
                "malformed_patch",
                "'No newline' marker must terminate the hunk",
                path,
            ));
        }
        if raw.is_empty() {
            return Err(PatchError::with_path(
                "malformed_patch",
                "empty hunk lines must carry a ' ', '-' or '+' prefix",
                path,
            ));
        }
        let prefix = raw.as_bytes()[0] as char;
        if !matches!(prefix, ' ' | '-' | '+') {
            return Err(PatchError::with_path(
                "malformed_patch",
                format!("invalid hunk line prefix '{prefix}'"),
                path,
            ));
        }
        current.ops.push((prefix, raw[1..].to_string()));
        current_started = true;
        index += 1;
    }

    finish_current_hunk(
        &mut hunks,
        &mut current,
        &mut current_started,
        &mut marker_seen,
        path,
    )?;
    if hunks.is_empty() {
        return Err(PatchError::with_path(
            "empty_hunk",
            "update has no hunks",
            path,
        ));
    }
    Ok((hunks, index))
}

fn parse_unified(lines: &[String], start: usize) -> Result<Vec<RawFile>, PatchError> {
    let mut files: Vec<RawFile> = Vec::new();
    let mut index = start;
    while index < lines.len() {
        let line = &lines[index];
        if line.trim().is_empty() {
            index += 1;
            continue;
        }
        if line.starts_with("diff --git ") {
            index += 1;
            continue;
        }
        if UNIFIED_METADATA.iter().any(|m| line.starts_with(*m)) {
            index += 1;
            continue;
        }
        if line.starts_with("***") {
            return Err(PatchError::new(
                "mixed_format",
                "Codex directives cannot be mixed with a unified diff",
            ));
        }
        if !line.starts_with("--- ") {
            return Err(PatchError::new(
                "malformed_patch",
                format!("expected a '--- ' file header, got '{line}'"),
            ));
        }
        if index + 1 >= lines.len() || !lines[index + 1].starts_with("+++ ") {
            return Err(PatchError::new(
                "malformed_header",
                "'--- ' header must be followed by a '+++ ' header",
            ));
        }
        let old_header = header_path(&lines[index][4..])?;
        let new_header = header_path(&lines[index + 1][4..])?;
        index += 2;

        let old_path = strip_unified_prefix(&old_header);
        let new_path = strip_unified_prefix(&new_header);
        let (kind, path) = match (old_path, new_path) {
            (None, None) => {
                return Err(PatchError::new(
                    "malformed_header",
                    "both unified diff headers cannot be /dev/null",
                ))
            }
            (None, Some(np)) => (Kind::Add, np),
            (Some(op), None) => (Kind::Delete, op),
            (Some(op), Some(np)) => {
                if op != np {
                    return Err(PatchError::with_path(
                        "rename_unsupported",
                        format!("renaming '{op}' to '{np}' is not supported"),
                        &op,
                    ));
                }
                (Kind::Update, op)
            }
        };

        let mut hunks: Vec<Hunk> = Vec::new();
        while index < lines.len() {
            let current = &lines[index];
            if current.starts_with("@@") {
                let (hunk, next) = parse_unified_hunk(lines, index, &path)?;
                index = next;
                hunks.push(hunk);
                continue;
            }
            if current.starts_with("--- ")
                || current.starts_with("diff --git ")
                || UNIFIED_METADATA.iter().any(|m| current.starts_with(*m))
            {
                break;
            }
            if current.starts_with("***") {
                return Err(PatchError::new(
                    "mixed_format",
                    "Codex directives cannot be mixed with a unified diff",
                ));
            }
            if current.trim().is_empty() {
                index += 1;
                continue;
            }
            return Err(PatchError::with_path(
                "malformed_patch",
                format!("unexpected line in unified diff: '{current}'"),
                &path,
            ));
        }

        let no_newline = hunks.last().is_some_and(|h| h.new_no_newline);
        files.push(RawFile {
            path,
            kind,
            hunks,
            no_newline,
        });
    }
    Ok(files)
}

fn header_path(value: &str) -> Result<String, PatchError> {
    let path = value.split('\t').next().unwrap_or("").trim().to_string();
    if path.is_empty() {
        return Err(PatchError::new(
            "malformed_header",
            "empty path in file header",
        ));
    }
    Ok(path)
}

fn strip_unified_prefix(path: &str) -> Option<String> {
    if path == "/dev/null" {
        return None;
    }
    if let Some(rest) = path.strip_prefix("a/") {
        return Some(rest.to_string());
    }
    if let Some(rest) = path.strip_prefix("b/") {
        return Some(rest.to_string());
    }
    Some(path.to_string())
}

fn parse_unified_hunk(
    lines: &[String],
    start: usize,
    path: &str,
) -> Result<(Hunk, usize), PatchError> {
    let header = &lines[start];
    let caps = hunk_header_re().captures(header).ok_or_else(|| {
        PatchError::with_path(
            "malformed_hunk",
            format!("invalid hunk header: '{header}'"),
            path,
        )
    })?;
    let old_start: usize = caps["old_start"].parse().unwrap();
    let old_count: usize = caps
        .name("old_count")
        .map(|m| m.as_str().parse().unwrap())
        .unwrap_or(1);
    let new_count: usize = caps
        .name("new_count")
        .map(|m| m.as_str().parse().unwrap())
        .unwrap_or(1);
    let mut index = start + 1;

    let mut ops: Vec<(char, String)> = Vec::new();
    let mut old_seen = 0usize;
    let mut new_seen = 0usize;
    while old_seen < old_count || new_seen < new_count {
        if index >= lines.len() {
            return Err(PatchError::with_path(
                "unterminated_hunk",
                "hunk ends before its counts",
                path,
            ));
        }
        let raw = &lines[index];
        if raw.starts_with('\\') {
            return Err(PatchError::with_path(
                "malformed_hunk",
                "'No newline' marker appeared before the hunk was complete",
                path,
            ));
        }
        let (prefix, text) = if raw.is_empty() {
            // Some producers omit the single space on blank context lines.
            (' ', String::new())
        } else {
            (raw.as_bytes()[0] as char, raw[1..].to_string())
        };
        match prefix {
            ' ' => {
                old_seen += 1;
                new_seen += 1;
            }
            '-' => old_seen += 1,
            '+' => new_seen += 1,
            _ => {
                return Err(PatchError::with_path(
                    "malformed_hunk",
                    format!("invalid hunk line prefix '{prefix}'"),
                    path,
                ))
            }
        }
        if old_seen > old_count || new_seen > new_count {
            return Err(PatchError::with_path(
                "malformed_hunk",
                "hunk contains more lines than its header declares",
                path,
            ));
        }
        ops.push((prefix, text));
        index += 1;
    }

    let mut no_newline = false;
    if index < lines.len() && lines[index].starts_with('\\') {
        if !lines[index].starts_with(NO_NEWLINE) {
            return Err(PatchError::with_path(
                "malformed_hunk",
                format!("unknown backslash marker: '{}'", lines[index]),
                path,
            ));
        }
        if ops.is_empty() {
            return Err(PatchError::with_path(
                "empty_hunk",
                "hunk contains no lines",
                path,
            ));
        }
        no_newline = true;
        index += 1;
    }

    let last_prefix = ops.last().map(|(p, _)| *p).unwrap();
    let mut hunk = Hunk {
        old_start: Some(old_start),
        old_count: Some(old_count),
        ops,
        new_no_newline: false,
    };
    if no_newline {
        hunk.new_no_newline = last_prefix == ' ' || last_prefix == '+';
    }
    if hunk.ops.is_empty() {
        return Err(PatchError::with_path(
            "empty_hunk",
            "hunk contains no lines",
            path,
        ));
    }
    Ok((hunk, index))
}

// ---------------------------------------------------------------------------
// Path, content, and hunk resolution
// ---------------------------------------------------------------------------

/// Validate `raw`, returning the display path, the write target, and a
/// canonical identity for duplicate detection.
fn validate_path(raw: &str, root: &Path) -> Result<(String, PathBuf, PathBuf), PatchError> {
    let value = raw.trim().to_string();
    if value.is_empty() {
        return Err(PatchError::new("invalid_path", "empty file path"));
    }
    if value.contains('\0') {
        return Err(PatchError::new("invalid_path", "path contains NUL bytes"));
    }

    let normalised = value.replace('\\', "/");
    let first = normalised.chars().next().unwrap_or_default();
    let is_drive =
        normalised.len() >= 2 && first.is_ascii_alphabetic() && normalised.as_bytes()[1] == b':';
    if normalised.starts_with('/') || normalised.starts_with('~') || is_drive {
        return Err(PatchError::new(
            "absolute_path",
            format!("absolute paths are not allowed: {value}"),
        ));
    }

    let parts: Vec<&str> = normalised
        .split('/')
        .filter(|p| !p.is_empty() && *p != ".")
        .collect();
    if parts.contains(&"..") {
        return Err(PatchError::new(
            "path_traversal",
            format!("'..' is not allowed in paths: {value}"),
        ));
    }
    if parts.is_empty() {
        return Err(PatchError::new(
            "invalid_path",
            format!("invalid file path: {value}"),
        ));
    }
    let relative = parts.join("/");

    let candidate = parts.iter().fold(root.to_path_buf(), |acc, p| acc.join(p));
    let identity = resolve_nonstrict(
        root,
        &parts.iter().map(|s| s.to_string()).collect::<Vec<_>>(),
    );
    if !identity.starts_with(root) {
        return Err(PatchError::with_path(
            "outside_root",
            format!("path escapes the project root: {value}"),
            &relative,
        ));
    }
    Ok((relative, candidate, identity))
}

/// Canonicalise `base` joined with `parts` without requiring the leaf to
/// exist: the deepest existing ancestor is canonicalised, then the rest is
/// appended.
fn resolve_nonstrict(base: &Path, parts: &[String]) -> PathBuf {
    let mut resolved = base.to_path_buf();
    let mut acc = base.to_path_buf();
    let mut found_at: Option<usize> = None;
    for (i, p) in parts.iter().enumerate() {
        let probe = acc.join(p);
        if probe.exists() {
            resolved = probe.canonicalize().unwrap_or(probe);
            found_at = Some(i);
            break;
        }
        acc = probe;
    }
    let start = found_at.map(|i| i + 1).unwrap_or(0);
    for p in &parts[start..] {
        resolved = resolved.join(p);
    }
    resolved
}

fn read_source(path: &Path, relative: &str) -> Result<String, PatchError> {
    let metadata = match fs::metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == io::ErrorKind::NotFound => {
            return Err(PatchError::with_path(
                "not_found",
                "file does not exist",
                relative,
            ))
        }
        Err(e) => {
            return Err(PatchError::with_path(
                "read_failed",
                format!("cannot stat file: {e}"),
                relative,
            ))
        }
    };
    if !metadata.is_file() {
        return Err(PatchError::with_path(
            "not_a_file",
            "path is not a regular file",
            relative,
        ));
    }
    if metadata.len() > MAX_FILE_BYTES as u64 {
        return Err(PatchError::with_path(
            "file_too_large",
            format!(
                "file is {} bytes; limit is {MAX_FILE_BYTES}",
                metadata.len()
            ),
            relative,
        ));
    }
    let data = fs::read(path).map_err(|e| {
        PatchError::with_path("read_failed", format!("cannot read file: {e}"), relative)
    })?;
    if data.contains(&0u8) {
        return Err(PatchError::with_path(
            "binary_file",
            "file contains NUL bytes",
            relative,
        ));
    }
    String::from_utf8(data)
        .map_err(|_| PatchError::with_path("binary_file", "file is not valid UTF-8 text", relative))
}

fn resolve_file(
    raw: &RawFile,
    root: &Path,
    patch_eol: &str,
) -> Result<(PatchFile, Vec<String>), PatchError> {
    let (relative, target, _identity) = validate_path(&raw.path, root)?;

    if raw.kind == Kind::Add {
        if fs::symlink_metadata(&target).is_ok() {
            return Err(PatchError::with_path(
                "file_exists",
                "file already exists",
                &relative,
            ));
        }
        validate_add_parent(&target, &relative)?;
        let (lines, no_newline) = collect_added_lines(raw, &relative)?;
        let text = join_lines(&lines, patch_eol, !no_newline);
        check_result_size(&text, &relative)?;
        return Ok((
            PatchFile {
                path: relative,
                kind: Kind::Add,
                additions: lines.len(),
                deletions: 0,
                new_text: text,
            },
            Vec::new(),
        ));
    }

    if raw.kind == Kind::Delete {
        if fs::symlink_metadata(&target).is_err() {
            return Err(PatchError::with_path(
                "not_found",
                "file does not exist",
                &relative,
            ));
        }
        let metadata = fs::metadata(&target).map_err(|e| {
            PatchError::with_path("read_failed", format!("cannot stat file: {e}"), &relative)
        })?;
        if !metadata.is_file() {
            return Err(PatchError::with_path(
                "not_a_file",
                "path is not a regular file",
                &relative,
            ));
        }
        if metadata.len() > MAX_FILE_BYTES as u64 {
            return Err(PatchError::with_path(
                "file_too_large",
                format!(
                    "file is {} bytes; limit is {MAX_FILE_BYTES}",
                    metadata.len()
                ),
                &relative,
            ));
        }
        for hunk in &raw.hunks {
            if hunk.ops.iter().any(|(p, _)| *p != '-') {
                return Err(PatchError::with_path(
                    "malformed_patch",
                    "a deleted file may only contain removed lines",
                    &relative,
                ));
            }
        }
        if !raw.hunks.is_empty() {
            let old_text = read_source(&target, &relative)?;
            match_all_hunks(&old_text, &raw.hunks, &relative, false)?;
        }
        let deletions = if metadata.len() == 0 {
            0
        } else {
            count_file_lines(&target)
        };
        return Ok((
            PatchFile {
                path: relative,
                kind: Kind::Delete,
                additions: 0,
                deletions,
                new_text: String::new(),
            },
            Vec::new(),
        ));
    }

    if raw.hunks.is_empty() {
        return Err(PatchError::with_path(
            "empty_hunk",
            "update has no hunks",
            &relative,
        ));
    }
    let old_text = read_source(&target, &relative)?;
    let (new_text, warnings) = apply_hunks(&old_text, &raw.hunks, &relative)?;
    check_result_size(&new_text, &relative)?;
    let additions = raw
        .hunks
        .iter()
        .flat_map(|h| h.ops.iter())
        .filter(|(p, _)| *p == '+')
        .count();
    let deletions = raw
        .hunks
        .iter()
        .flat_map(|h| h.ops.iter())
        .filter(|(p, _)| *p == '-')
        .count();
    Ok((
        PatchFile {
            path: relative,
            kind: Kind::Update,
            additions,
            deletions,
            new_text,
        },
        warnings,
    ))
}

fn validate_add_parent(target: &Path, relative: &str) -> Result<(), PatchError> {
    let mut parent = target
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .to_path_buf();
    while !parent.exists() {
        match parent.parent() {
            Some(p) if p != parent => parent = p.to_path_buf(),
            _ => break,
        }
    }
    if !parent.is_dir() {
        return Err(PatchError::with_path(
            "invalid_parent",
            format!("parent path is not a directory: {}", parent.display()),
            relative,
        ));
    }
    Ok(())
}

fn collect_added_lines(raw: &RawFile, relative: &str) -> Result<(Vec<String>, bool), PatchError> {
    let mut lines: Vec<String> = Vec::new();
    for hunk in &raw.hunks {
        for (prefix, text) in &hunk.ops {
            if *prefix != '+' {
                return Err(PatchError::with_path(
                    "malformed_patch",
                    "an added file may only contain added lines",
                    relative,
                ));
            }
            lines.push(text.clone());
        }
    }
    let no_newline = raw.no_newline && !lines.is_empty();
    Ok((lines, no_newline))
}

fn count_file_lines(path: &Path) -> usize {
    let data = match fs::read(path) {
        Ok(d) => d,
        Err(_) => return 0,
    };
    if data.is_empty() {
        return 0;
    }
    // Normalise CRLF/CR to LF at the byte level (binary-safe).
    let mut normalised: Vec<u8> = Vec::with_capacity(data.len());
    let mut i = 0usize;
    while i < data.len() {
        match (data[i], data.get(i + 1).copied()) {
            (b'\r', Some(b'\n')) => {
                normalised.push(b'\n');
                i += 2;
            }
            (b'\r', _) => {
                normalised.push(b'\n');
                i += 1;
            }
            (b, _) => {
                normalised.push(b);
                i += 1;
            }
        }
    }
    let mut count = normalised.iter().filter(|b| **b == b'\n').count();
    if !normalised.ends_with(b"\n") {
        count += 1;
    }
    count
}

fn check_result_size(text: &str, relative: &str) -> Result<(), PatchError> {
    if text.len() > MAX_FILE_BYTES {
        return Err(PatchError::with_path(
            "file_too_large",
            format!(
                "resulting file is {} bytes; limit is {MAX_FILE_BYTES}",
                text.len()
            ),
            relative,
        ));
    }
    Ok(())
}

fn split_lines(text: &str) -> Vec<String> {
    if text.is_empty() {
        return Vec::new();
    }
    let normalised = text.replace("\r\n", "\n").replace('\r', "\n");
    let mut lines: Vec<String> = normalised.split('\n').map(String::from).collect();
    if lines.last().is_some_and(|l| l.is_empty()) {
        lines.pop();
    }
    lines
}

fn detect_eol(text: &str) -> &str {
    if text.contains("\r\n") {
        "\r\n"
    } else if text.contains('\n') {
        "\n"
    } else if text.contains('\r') {
        "\r"
    } else {
        "\n"
    }
}

fn join_lines(lines: &[String], eol: &str, final_newline: bool) -> String {
    if lines.is_empty() {
        return String::new();
    }
    let mut text = lines.join(eol);
    if final_newline {
        text.push_str(eol);
    }
    text
}

fn old_block(hunk: &Hunk) -> Vec<String> {
    hunk.ops
        .iter()
        .filter(|(p, _)| *p == ' ' || *p == '-')
        .map(|(_, t)| t.clone())
        .collect()
}

fn new_block(hunk: &Hunk) -> Vec<String> {
    hunk.ops
        .iter()
        .filter(|(p, _)| *p == ' ' || *p == '+')
        .map(|(_, t)| t.clone())
        .collect()
}

fn find_match(
    lines: &[String],
    block: &[String],
    expected: usize,
    prefer_forward: bool,
) -> Option<usize> {
    let total = lines.len();
    let width = block.len();
    if width == 0 {
        return Some(expected.min(total));
    }
    if width > total {
        return None;
    }

    let start = expected.min(total - width);
    let candidates: Vec<usize> = if prefer_forward {
        let mut c: Vec<usize> = (start..=total - width).collect();
        // Python: candidates.extend(range(start - 1, -1, -1))
        for p in (0..start).rev() {
            c.push(p);
        }
        c
    } else {
        let mut c = Vec::new();
        let max_distance = start.max((total - width).saturating_sub(start));
        for distance in 0..=max_distance {
            let after = start + distance;
            if after <= total - width {
                c.push(after);
            }
            if distance > 0 && distance <= start {
                c.push(start - distance);
            }
        }
        c
    };

    for position in candidates {
        if lines[position..position + width] == block[..] {
            return Some(position);
        }
    }
    None
}

struct Matched {
    start: usize,
    end: usize,
    replacement: Vec<String>,
    hunk_idx: usize,
    number: usize,
}

fn match_all_hunks(
    old_text: &str,
    hunks: &[Hunk],
    relative: &str,
    codex: bool,
) -> Result<Vec<Matched>, PatchError> {
    let lines = split_lines(old_text);
    let mut matched: Vec<Matched> = Vec::new();
    let mut cursor = 0usize;
    for (i, hunk) in hunks.iter().enumerate() {
        let number = i + 1;
        let block = old_block(hunk);
        let expected = match hunk.old_start {
            Some(os) => {
                if hunk.old_count == Some(0) {
                    os
                } else {
                    os.saturating_sub(1)
                }
            }
            None => cursor,
        };
        let found = find_match(&lines, &block, expected, codex).ok_or_else(|| {
            PatchError::with_path(
                "context_mismatch",
                format!("hunk {number} does not match the current file content"),
                relative,
            )
        })?;
        matched.push(Matched {
            start: found,
            end: found + block.len(),
            replacement: new_block(hunk),
            hunk_idx: i,
            number,
        });
        cursor = found + block.len();
    }

    let mut ordered: Vec<&Matched> = matched.iter().collect();
    ordered.sort_by_key(|m| (m.start, m.end));
    let mut previous: Option<(usize, usize)> = None;
    for m in &ordered {
        if let Some((_, prev_end)) = previous {
            if m.start < prev_end {
                return Err(PatchError::with_path(
                    "overlapping_hunks",
                    "two hunks modify overlapping regions",
                    relative,
                ));
            }
        }
        if let Some((ps, pe)) = previous {
            if m.start == ps && m.end == pe && m.start == m.end {
                return Err(PatchError::with_path(
                    "overlapping_hunks",
                    "two insertion hunks target the same position",
                    relative,
                ));
            }
        }
        previous = Some((m.start, m.end));
    }
    Ok(matched)
}

fn apply_hunks(
    old_text: &str,
    hunks: &[Hunk],
    relative: &str,
) -> Result<(String, Vec<String>), PatchError> {
    let lines = split_lines(old_text);
    let codex = hunks.iter().all(|h| h.old_start.is_none());
    let matched = match_all_hunks(old_text, hunks, relative, codex)?;
    let mut warnings: Vec<String> = Vec::new();

    // Explicit line numbers only exist in unified diffs. Report fuzz visibly.
    for m in &matched {
        let hunk = &hunks[m.hunk_idx];
        if hunk.old_start.is_none() {
            continue;
        }
        let expected = if hunk.old_count == Some(0) {
            hunk.old_start.unwrap()
        } else {
            hunk.old_start.unwrap().saturating_sub(1)
        };
        if m.start != expected {
            let offset = m.start as i64 - expected as i64;
            // Parity with Python's `f"{offset:+d}"`: the sign is always shown.
            let offset = if offset < 0 {
                offset.to_string()
            } else {
                format!("+{offset}")
            };
            warnings.push(format!(
                "{relative}: hunk {number} applied at line {line} (offset {offset})",
                number = m.number,
                line = m.start + 1,
            ));
        }
    }

    let mut ordered: Vec<&Matched> = matched.iter().collect();
    ordered.sort_by_key(|m| (m.start, m.end));
    let mut output: Vec<String> = Vec::new();
    let mut position = 0usize;
    for m in &ordered {
        output.extend_from_slice(&lines[position..m.start]);
        output.extend_from_slice(&m.replacement);
        position = m.end;
    }
    output.extend_from_slice(&lines[position..]);

    let old_final_newline = old_text.ends_with('\n') || old_text.ends_with('\r');
    let mut final_newline = old_final_newline;
    if output.is_empty() {
        final_newline = false;
    } else {
        let end_hunks: Vec<&Matched> = ordered
            .iter()
            .filter(|m| m.end == lines.len())
            .copied()
            .collect();
        if let Some(m) = end_hunks.last() {
            let hunk = &hunks[m.hunk_idx];
            let last_output = hunk
                .ops
                .iter()
                .rev()
                .find(|(p, _)| *p != '-')
                .map(|(p, _)| *p);
            let last_source = hunk.ops.last().map(|(p, _)| *p);
            if hunk.new_no_newline {
                final_newline = false;
            } else if last_output == Some('+') {
                final_newline = true;
            } else if last_output == Some(' ') {
                // A context line that is still the final source line keeps the
                // source's trailing-newline state. If it was followed by
                // removed lines, the context line necessarily had a newline.
                final_newline = if last_source == Some(' ') {
                    old_final_newline
                } else {
                    true
                };
            } else {
                // The hunk removed the trailing lines; the remaining line came
                // from earlier in the file and therefore had a newline.
                final_newline = true;
            }
        }
    }

    let eol = detect_eol(old_text);
    Ok((join_lines(&output, eol, final_newline), warnings))
}

// ---------------------------------------------------------------------------
// Atomic write phase
// ---------------------------------------------------------------------------

static TEMP_COUNTER: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

fn temp_path(parent: &Path, target: &Path) -> PathBuf {
    let n = TEMP_COUNTER.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    let name = target
        .file_name()
        .and_then(|s| s.to_str())
        .unwrap_or("file");
    parent.join(format!(".apex-patch-{}-{n}-{name}.tmp", std::process::id()))
}

#[cfg(unix)]
fn file_mode(path: &Path) -> Option<u32> {
    use std::os::unix::fs::PermissionsExt;
    fs::metadata(path).ok().map(|m| m.permissions().mode())
}

#[cfg(not(unix))]
fn file_mode(_path: &Path) -> Option<u32> {
    None
}

fn atomic_write(target: &Path, data: &[u8], mode: Option<u32>) -> io::Result<()> {
    let parent = target
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "target has no parent"))?;
    fs::create_dir_all(parent)?;
    let temp = temp_path(parent, target);
    let write_result = (|| -> io::Result<()> {
        let mut handle = fs::File::create(&temp)?;
        use std::io::Write as _;
        handle.write_all(data)?;
        handle.sync_all()?;
        if let Some(mode) = mode {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                fs::set_permissions(&temp, fs::Permissions::from_mode(mode))?;
            }
            #[cfg(not(unix))]
            let _ = mode;
        }
        Ok(())
    })();
    if let Err(e) = write_result {
        let _ = fs::remove_file(&temp);
        return Err(e);
    }
    fs::rename(&temp, target).inspect_err(|_| {
        let _ = fs::remove_file(&temp);
    })
}

fn ensure_parent(parent: &Path) -> io::Result<Vec<PathBuf>> {
    let mut missing: Vec<PathBuf> = Vec::new();
    let mut current = parent.to_path_buf();
    while !current.exists() {
        match current.parent() {
            Some(p) if p != current => {
                missing.push(current.clone());
                current = p.to_path_buf();
            }
            _ => break,
        }
    }
    fs::create_dir_all(parent)?;
    missing.reverse();
    Ok(missing)
}

fn write_files(files: &[PatchFile], root: &Path) -> Result<(), PatchError> {
    let resolved_root = validate_root(root)?;
    let writes: Vec<&PatchFile> = files
        .iter()
        .filter(|f| f.kind == Kind::Add || f.kind == Kind::Update)
        .collect();
    let deletes: Vec<&PatchFile> = files.iter().filter(|f| f.kind == Kind::Delete).collect();

    // Capture every original before touching the disk.
    let mut originals: Vec<(String, Vec<u8>, Option<u32>)> = Vec::new();
    for item in writes
        .iter()
        .filter(|f| f.kind == Kind::Update)
        .chain(deletes.iter())
    {
        let target = resolved_root.join(&item.path);
        let data = fs::read(&target).map_err(|e| {
            PatchError::with_path(
                "read_failed",
                format!("cannot capture original file: {e}"),
                &item.path,
            )
        })?;
        originals.push((item.path.clone(), data, file_mode(&target)));
    }

    let mut written: Vec<&PatchFile> = Vec::new();
    let mut removed: Vec<&PatchFile> = Vec::new();
    let mut created_dirs: Vec<PathBuf> = Vec::new();
    let write_result: io::Result<()> = (|| {
        for item in &writes {
            let target = resolved_root.join(&item.path);
            let parent = target
                .parent()
                .filter(|p| !p.as_os_str().is_empty())
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "no parent"))?;
            created_dirs.extend(ensure_parent(parent)?);
            let mode = if item.kind == Kind::Update {
                originals
                    .iter()
                    .find(|(p, _, _)| p == &item.path)
                    .and_then(|(_, _, m)| *m)
            } else {
                None
            };
            atomic_write(&target, item.new_text.as_bytes(), mode)?;
            written.push(item);
        }
        for item in &deletes {
            let target = resolved_root.join(&item.path);
            fs::remove_file(&target)?;
            removed.push(item);
        }
        Ok(())
    })();
    if let Err(e) = write_result {
        let rollback_errors = rollback(
            &resolved_root,
            &written,
            &removed,
            &originals,
            &created_dirs,
        );
        let failed = written
            .last()
            .map(|f| &f.path)
            .or_else(|| removed.last().map(|f| &f.path));
        let mut detail = format!("write failed: {e}");
        if !rollback_errors.is_empty() {
            detail.push_str("; rollback incomplete: ");
            detail.push_str(&rollback_errors.join("; "));
        } else {
            detail.push_str("; partial changes were rolled back");
        }
        return Err(PatchError::with_path(
            "write_failed",
            detail,
            failed.map(String::as_str).unwrap_or(""),
        ));
    }
    Ok(())
}

fn rollback(
    root: &Path,
    written: &[&PatchFile],
    removed: &[&PatchFile],
    originals: &[(String, Vec<u8>, Option<u32>)],
    created_dirs: &[PathBuf],
) -> Vec<String> {
    let mut errors: Vec<String> = Vec::new();
    for item in written.iter().rev() {
        let target = root.join(&item.path);
        let original = originals.iter().find(|(p, _, _)| p == &item.path);
        let result = match original {
            None => fs::remove_file(&target),
            Some((_, data, mode)) => atomic_write(&target, data, *mode),
        };
        if let Err(e) = result {
            errors.push(format!("{}: {e}", item.path));
        }
    }
    for item in removed.iter().rev() {
        let target = root.join(&item.path);
        match originals.iter().find(|(p, _, _)| p == &item.path) {
            Some((_, data, mode)) => {
                if let Err(e) = atomic_write(&target, data, *mode) {
                    errors.push(format!("{}: {e}", item.path));
                }
            }
            None => errors.push(format!("{}: missing original", item.path)),
        }
    }
    for directory in created_dirs.iter().rev() {
        let _ = fs::remove_dir(directory);
    }
    errors
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn write(dir: &Path, name: &str, content: &str) {
        fs::write(dir.join(name), content).unwrap();
    }

    #[test]
    fn codex_add_update_delete() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "alpha\nbeta\nnew-line\ngamma\n");
        write(dir.path(), "b.txt", "bye\n");

        let patch = "\
*** Begin Patch
*** Add File: new.txt
+hello
+world
*** Update File: a.txt
@@
 beta
-new-line
+new-line-tuned
*** Delete File: b.txt
*** End Patch
";
        let result = apply_patch(patch, dir.path(), false).unwrap();
        assert!(!result.dry_run);
        assert_eq!(result.files.len(), 3);
        assert_eq!(
            fs::read_to_string(dir.path().join("new.txt")).unwrap(),
            "hello\nworld\n"
        );
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "alpha\nbeta\nnew-line-tuned\ngamma\n"
        );
        assert!(!dir.path().join("b.txt").exists());
        // additions: 2 (new) + 1 (a.txt) = 3; deletions: 1 (a.txt) + 1 (b.txt) = 2
        assert_eq!(result.additions, 3);
        assert_eq!(result.deletions, 2);
    }

    #[test]
    fn unified_update() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "one\ntwo\nthree\n");

        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1,3 +1,3 @@
 one
-two
+TWO
 three
";
        let result = apply_patch(patch, dir.path(), false).unwrap();
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "one\nTWO\nthree\n"
        );
        assert_eq!(result.additions, 1);
        assert_eq!(result.deletions, 1);
        assert!(result.warnings.is_empty());
    }

    #[test]
    fn unified_add_and_delete_via_dev_null() {
        let dir = tempdir().unwrap();
        write(dir.path(), "old.txt", "gone\n");

        let patch = "\
--- /dev/null
+++ b/brand_new.txt
@@ -0,0 +1,2 @@
+fresh
+content
--- a/old.txt
+++ /dev/null
@@ -1 +0,0 @@
-gone
";
        let result = apply_patch(patch, dir.path(), false).unwrap();
        assert_eq!(result.files.len(), 2);
        assert_eq!(
            fs::read_to_string(dir.path().join("brand_new.txt")).unwrap(),
            "fresh\ncontent\n"
        );
        assert!(!dir.path().join("old.txt").exists());
    }

    #[test]
    fn dry_run_writes_nothing() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "one\ntwo\n");

        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1,2 +1,2 @@
 one
-two
+TWO
";
        let result = apply_patch(patch, dir.path(), true).unwrap();
        assert!(result.dry_run);
        assert_eq!(result.files.len(), 1);
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "one\ntwo\n"
        );
    }

    #[test]
    fn reject_path_traversal() {
        let dir = tempdir().unwrap();
        let patch = "*** Begin Patch\n*** Add File: ../evil.txt\n+x\n*** End Patch\n";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "path_traversal");
    }

    #[test]
    fn reject_absolute_path() {
        let dir = tempdir().unwrap();
        let patch = "--- /etc/passwd\n+++ /etc/passwd\n@@ -1 +1 @@\n-x\n+y\n";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "absolute_path");
    }

    #[test]
    fn reject_duplicate_path() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "x\n");
        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-x
+y
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-y
+z
";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "duplicate_path");
    }

    #[test]
    fn context_mismatch_writes_nothing() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "keep\n");
        write(dir.path(), "b.txt", "real content\n");

        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-keep
+kept
--- a/b.txt
+++ b/b.txt
@@ -1 +1 @@
-wrong context
+changed
";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "context_mismatch");
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "keep\n"
        );
        assert_eq!(
            fs::read_to_string(dir.path().join("b.txt")).unwrap(),
            "real content\n"
        );
    }

    #[test]
    fn fuzz_offset_produces_warning() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "1\n2\n3\n4\n5\n");

        // Declared at line 1 but the context actually sits at line 3: +2.
        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1,3 +1,3 @@
 3
-4
+FOUR
 5
";
        let result = apply_patch(patch, dir.path(), false).unwrap();
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "1\n2\n3\nFOUR\n5\n"
        );
        assert_eq!(result.warnings.len(), 1);
        assert!(result.warnings[0].contains("offset +2"));
    }

    #[test]
    fn reject_binary_patch() {
        let dir = tempdir().unwrap();
        let patch = "*** Begin Patch\n*** Add File: a.txt\n+x\x00y\n*** End Patch\n";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "binary_patch");
    }

    #[test]
    fn reject_empty_patch() {
        let dir = tempdir().unwrap();
        let err = apply_patch("   \n  ", dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "empty_patch");
    }

    #[test]
    fn codex_no_newline_marker() {
        let dir = tempdir().unwrap();
        let patch = "\
*** Begin Patch
*** Add File: raw.txt
+first
+second
\\ No newline at end of file
*** End Patch
";
        apply_patch(patch, dir.path(), false).unwrap();
        assert_eq!(
            fs::read_to_string(dir.path().join("raw.txt")).unwrap(),
            "first\nsecond"
        );
    }

    #[test]
    fn unterminated_codex_patch() {
        let dir = tempdir().unwrap();
        let patch = "*** Begin Patch\n*** Add File: a.txt\n+x\n";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "unterminated_patch");
    }

    #[test]
    fn result_files_summary() {
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "x\n");
        let patch = "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-x\n+y\n";
        let result = apply_patch(patch, dir.path(), false).unwrap();
        assert_eq!(result.files[0].path, "a.txt");
        assert_eq!(result.files[0].kind, Kind::Update);
        assert_eq!(result.files[0].additions, 1);
        assert_eq!(result.files[0].deletions, 1);
    }

    /// Write failure after a first successful write must roll the first file
    /// back. POSIX-only: making a directory read-only does not block writes on
    /// Windows, so the failure cannot be triggered there.
    #[cfg(unix)]
    #[test]
    fn write_failure_rolls_back() {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempdir().unwrap();
        write(dir.path(), "a.txt", "one\n");
        let bdir = dir.path().join("bdir");
        fs::create_dir(&bdir).unwrap();
        write(&bdir, "b.txt", "two\n");
        // The parent of b.txt becomes read-only: temp-file creation fails.
        fs::set_permissions(&bdir, fs::Permissions::from_mode(0o555)).unwrap();

        let patch = "\
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-one
+ONE
--- a/bdir/b.txt
+++ b/bdir/b.txt
@@ -1 +1 @@
-two
+TWO
";
        let err = apply_patch(patch, dir.path(), false).unwrap_err();
        assert_eq!(err.reason, "write_failed");
        // First file restored, second untouched.
        assert_eq!(
            fs::read_to_string(dir.path().join("a.txt")).unwrap(),
            "one\n"
        );
        assert_eq!(fs::read_to_string(bdir.join("b.txt")).unwrap(), "two\n");
    }
}
