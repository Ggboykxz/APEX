//! Session persistence, sharing and export.
//!
//! Mirrors `apex/session.py` and `apex/share.py`:
//!   * sessions are Fernet-encrypted in `~/.apex/sessions/<ts>_<name>.enc`
//!   * `latest_<name>.json` is a symlink to the newest `.enc` file
//!   * sharing/exporting sanitizes secrets before writing.

use crate::session_crypto::{BranchEntry, SessionMetadata};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

pub fn shares_dir() -> PathBuf {
    crate::config::home_dir()
        .unwrap_or_default()
        .join(".config")
        .join("apex")
        .join("shares")
}

pub fn sessions_dir() -> PathBuf {
    crate::config::home_dir()
        .unwrap_or_default()
        .join(".apex")
        .join("sessions")
}

// ---------------------------------------------------------------- time utils

fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

/// (YYYYMMDD_HHMMSS, ISO-ish timestamp) in UTC.
pub fn now_stamps() -> (String, String) {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let days = secs.div_euclid(86400);
    let rem = secs.rem_euclid(86400);
    let (y, mo, d) = civil_from_days(days);
    let (h, mi, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    (
        format!("{y:04}{mo:02}{d:02}_{h:02}{mi:02}{s:02}"),
        format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z"),
    )
}

fn now_iso_micro() -> String {
    let (_, ts) = now_stamps();
    format!("{ts}000000Z")
}

fn now_nanos_hex() -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{nanos:x}")
}

// ------------------------------------------------------------- sanitization

fn looks_sensitive_key(key: &str) -> bool {
    let up = key.to_uppercase();
    up.ends_with("_API_KEY")
        || up.ends_with("_TOKEN")
        || up.ends_with("_SECRET")
        || up.ends_with("_PASSWORD")
        || up.ends_with("_CREDENTIALS")
        || up.contains("APIKEY")
}

/// Redact obvious credentials in a string (sk-..., ghp_..., Bearer/Basic <token>).
pub fn redact_string(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    for token in input.split_inclusive(char::is_whitespace) {
        let trimmed = token.trim_end();
        let lower = trimmed.to_lowercase();
        let sensitive = lower.starts_with("sk-")
            || lower.starts_with("ghp_")
            || lower.starts_with("gho_")
            || lower.starts_with("xoxb-")
            || lower.starts_with("xoxp-")
            || (lower.starts_with("bearer ") && trimmed.len() > 27)
            || (lower.starts_with("basic ") && trimmed.len() > 26);
        if sensitive {
            out.push_str("[REDACTED]");
            out.push_str(&token[trimmed.len()..]);
        } else {
            out.push_str(token);
        }
    }
    out
}

pub fn sanitize(v: &Value) -> Value {
    match v {
        Value::Object(map) => {
            let mut out = serde_json::Map::new();
            for (k, val) in map {
                if looks_sensitive_key(k) {
                    continue;
                }
                out.insert(k.clone(), sanitize(val));
            }
            Value::Object(out)
        }
        Value::Array(items) => Value::Array(items.iter().map(sanitize).collect()),
        Value::String(s) => Value::String(redact_string(s)),
        other => other.clone(),
    }
}

// ------------------------------------------------------------------ sessions

fn read_session_file(path: &Path) -> Option<Value> {
    let raw = std::fs::read(path).ok()?;
    if let Ok(v) = serde_json::from_slice::<Value>(&raw) {
        return Some(v);
    }
    let text = String::from_utf8_lossy(&raw).to_string();
    let decrypted = crate::session_crypto::decrypt(&text)?;
    serde_json::from_str(&decrypted).ok()
}

/// Resolve and read a session by name (latest symlink, then newest matching .enc).
pub fn load_session(session_id: &str) -> Option<Value> {
    let dir = sessions_dir();
    let latest = dir.join(format!("latest_{session_id}.json"));
    let mut candidates: Vec<PathBuf> = Vec::new();
    if latest.exists() {
        if let Ok(target) = std::fs::read_link(&latest) {
            candidates.push(dir.join(target));
        } else {
            candidates.push(latest.clone());
        }
    }
    if candidates.iter().all(|p| !p.exists()) {
        let mut matching: Vec<PathBuf> = Vec::new();
        if let Ok(rd) = std::fs::read_dir(&dir) {
            for e in rd.flatten() {
                let name = e.file_name().to_string_lossy().to_string();
                if name.ends_with(&format!("_{session_id}.enc")) {
                    matching.push(e.path());
                }
            }
        }
        matching.sort_by_key(|p| std::fs::metadata(p).and_then(|m| m.modified()).ok());
        if let Some(last) = matching.pop() {
            candidates.push(last);
        }
    }
    candidates.iter().find_map(|p| read_session_file(p))
}

/// Extract the `history` array from a session payload.
pub fn history_of(data: &Value) -> Vec<Value> {
    data.get("history")
        .or_else(|| data.get("messages"))
        .and_then(|m| m.as_array())
        .cloned()
        .unwrap_or_default()
}

pub fn safe_session_name(name: &str) -> String {
    name.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '_' || c == '-' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

/// Extract fork/branch metadata from a session payload.
pub fn metadata_of(data: &Value) -> SessionMetadata {
    // Try to parse the metadata fields from the session value.
    // We deserialize the whole value as SessionMetadata, which will use
    // defaults for any missing fields.
    serde_json::from_value(data.clone()).unwrap_or_default()
}

/// Merge `SessionMetadata` into a session payload.
pub fn with_metadata(data: Value, meta: &SessionMetadata) -> Value {
    let mut obj = match data {
        Value::Object(obj) => obj,
        other => return other,
    };
    if let Ok(Value::Object(meta_obj)) = serde_json::to_value(meta) {
        for (k, val) in meta_obj {
            // Only insert if not null/empty (to preserve skip_serializing_if behavior)
            if !val.is_null() && !(val.is_array() && val.as_array().unwrap().is_empty()) {
                obj.insert(k, val);
            }
        }
    }
    Value::Object(obj)
}

/// Write an encrypted session with optional fork/branch metadata.
pub fn save_session_with_metadata(
    name: &str,
    model: &str,
    cwd: &str,
    history: &[Value],
    metadata: Option<&SessionMetadata>,
) -> Option<PathBuf> {
    let dir = sessions_dir();
    std::fs::create_dir_all(&dir).ok()?;
    let safe = safe_session_name(name);
    let (ts, iso) = now_stamps();
    let filename = format!("{ts}_{safe}.enc");
    let filepath = dir.join(&filename);

    let mut payload = json!({
        "name": name,
        "timestamp": iso,
        "model": model,
        "cwd": cwd,
        "history": history,
        "usage": {},
    });

    // Merge metadata if provided
    if let Some(meta) = metadata {
        payload = with_metadata(payload, meta);
    }

    let plain = serde_json::to_string(&payload).ok()?;
    let token = crate::session_crypto::encrypt(&plain)?;
    std::fs::write(&filepath, token).ok()?;

    // Atomically refresh the `latest` pointer.
    let latest = dir.join(format!("latest_{safe}.json"));
    let tmp = dir.join(format!(".latest_{safe}.tmp"));
    let _ = std::fs::remove_file(&tmp);
    #[cfg(unix)]
    {
        if std::os::unix::fs::symlink(&filename, &tmp).is_ok() {
            let _ = std::fs::rename(&tmp, &latest);
        }
    }
    #[cfg(not(unix))]
    {
        let _ = std::fs::copy(&filepath, &latest);
    }
    Some(filepath)
}

/// Backward-compatible save_session without metadata.
pub fn save_session(name: &str, model: &str, cwd: &str, history: &[Value]) -> Option<PathBuf> {
    save_session_with_metadata(name, model, cwd, history, None)
}

/// List sessions (name, timestamp, model, history_len), newest first.
pub fn list_sessions() -> Vec<Value> {
    let dir = sessions_dir();
    let mut sessions = Vec::new();
    let Ok(rd) = std::fs::read_dir(&dir) else {
        return sessions;
    };
    for e in rd.flatten() {
        let path = e.path();
        let is_symlink = std::fs::symlink_metadata(&path)
            .map(|m| m.file_type().is_symlink())
            .unwrap_or(false);
        if is_symlink {
            continue;
        }
        let fname = e.file_name().to_string_lossy().to_string();
        let is_enc = fname.ends_with(".enc");
        if !is_enc && !fname.ends_with(".json") {
            continue;
        }
        let Some(data) = read_session_file(&path) else {
            continue;
        };
        sessions.push(json!({
            "id": fname.trim_end_matches(".enc").trim_end_matches(".json"),
            "name": data.get("name").and_then(|v| v.as_str()).unwrap_or("unknown"),
            "timestamp": data.get("timestamp").and_then(|v| v.as_str()).unwrap_or(""),
            "model": data.get("model").and_then(|v| v.as_str()).unwrap_or(""),
            "history_len": history_of(&data).len(),
        }));
    }
    sessions.sort_by(|a, b| {
        b["timestamp"]
            .as_str()
            .unwrap_or("")
            .cmp(a["timestamp"].as_str().unwrap_or(""))
    });
    sessions
}

/// Fork a session: load the parent, write a child session with the same model,
/// cwd, and history but tagged with fork metadata.
///
/// Returns the `(child_id, child_path)` on success, or `None` if the parent
/// session could not be loaded or the child could not be saved.
pub fn fork_session(
    parent_id: &str,
    child_name: &str,
    branch_name: &str,
    fork_point: u32,
) -> Option<(String, PathBuf)> {
    let parent_data = load_session(parent_id)?;
    let model = parent_data
        .get("model")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let cwd = parent_data
        .get("cwd")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let history: Vec<Value> = history_of(&parent_data);

    let mut metadata = SessionMetadata::new_fork(
        parent_id.to_string(),
        branch_name.to_string(),
        fork_point,
    );
    // Record this fork as a branch-history entry.
    let (_ts, iso) = now_stamps();
    metadata.add_branch_entry(BranchEntry {
        session_id: child_name.to_string(),
        branch_name: branch_name.to_string(),
        timestamp: iso,
        parent_id: Some(parent_id.to_string()),
    });

    let path = save_session_with_metadata(
        child_name,
        &model,
        &cwd,
        &history,
        Some(&metadata),
    )?;

    // Use the session name as the child id for lookups
    let child_id = safe_session_name(child_name);

    Some((child_id, path))
}

/// Return the branch history for a session, or an empty vector if absent.
pub fn branch_history_of(data: &Value) -> Vec<BranchEntry> {
    metadata_of(data).branch_history
}

/// Extract fork/branch metadata from a session as a JSON value.
pub fn metadata_json(data: &Value) -> Value {
    serde_json::to_value(metadata_of(data)).unwrap_or_default()
}

/// Extract branch history as a JSON array (for HTTP responses).
pub fn branch_history_json(data: &Value) -> Value {
    let history = branch_history_of(data);
    serde_json::to_value(history).unwrap_or_default()
}

// -------------------------------------------------------------------- shares

/// Create a local share record. Returns (share_id, url).
pub fn share_session(
    session_id: &str,
    title: &str,
    live_history: Option<Vec<Value>>,
) -> (String, String) {
    let share_id = now_nanos_hex();
    let url = format!("https://apex-ai.dev/s/{share_id}");
    let raw = load_session(session_id)
        .unwrap_or_else(|| json!({"history": live_history.clone().unwrap_or_default()}));
    let safe = sanitize(&raw);
    let messages = history_of(&safe);
    let share = json!({
        "id": share_id,
        "session_id": session_id,
        "title": title,
        "created_at": now_iso_micro(),
        "url": url,
        "messages_count": messages.len(),
        "messages": messages,
    });
    let _ = std::fs::create_dir_all(shares_dir());
    let path = shares_dir().join(format!("{share_id}.json"));
    let _ = std::fs::write(
        &path,
        serde_json::to_string_pretty(&share).unwrap_or_default(),
    );
    (share_id, url)
}

pub fn unshare_session(share_id: &str) -> bool {
    let path = shares_dir().join(format!("{share_id}.json"));
    if path.exists() {
        std::fs::remove_file(path).is_ok()
    } else {
        false
    }
}

pub fn list_shares() -> Vec<Value> {
    let mut out = Vec::new();
    if let Ok(rd) = std::fs::read_dir(shares_dir()) {
        for e in rd.flatten() {
            if let Ok(data) = std::fs::read_to_string(e.path()) {
                if let Ok(v) = serde_json::from_str::<Value>(&data) {
                    out.push(json!({
                        "id": v.get("id"),
                        "session_id": v.get("session_id"),
                        "title": v.get("title"),
                        "created_at": v.get("created_at"),
                        "url": v.get("url"),
                        "messages_count": v.get("messages_count"),
                    }));
                }
            }
        }
    }
    out.sort_by(|a, b| {
        b["created_at"]
            .as_str()
            .unwrap_or("")
            .cmp(a["created_at"].as_str().unwrap_or(""))
    });
    out
}

/// Export a session to `session_<id>.json` in `cwd`. Returns the written path.
pub fn export_session(
    session_id: &str,
    cwd: &Path,
    live_history: Option<Vec<Value>>,
) -> Option<PathBuf> {
    let raw = load_session(session_id).or_else(|| live_history.map(|h| json!({"history": h})))?;
    let export = json!({
        "exported_at": now_iso_micro(),
        "session_id": session_id,
        "apex_version": env!("CARGO_PKG_VERSION"),
        "data": sanitize(&raw),
    });
    let name = if session_id.is_empty() {
        "current"
    } else {
        session_id
    };
    let path = cwd.join(format!("session_{name}.json"));
    std::fs::write(&path, serde_json::to_string_pretty(&export).ok()?).ok()?;
    Some(path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn redacts_tokens() {
        let s = redact_string("Authorization: Bearer sk-abcdefghijklmnopqrstuvwxyz0123456789 done");
        assert!(!s.contains("sk-abcdefghijklmnopqrstuvwxyz0123456789"));
        assert!(s.contains("[REDACTED]"));
        let g = redact_string("token ghp_0123456789012345678901234567890123456789");
        assert!(!g.contains("ghp_0123456789012345678901234567890123456789"));
    }

    #[test]
    fn sanitize_drops_secret_keys() {
        let v = json!({
            "OPENAI_API_KEY": "sk-xyz",
            "model": "gpt-4o",
            "nested": {"MY_TOKEN": "abc", "ok": true}
        });
        let s = sanitize(&v);
        assert!(s.get("OPENAI_API_KEY").is_none());
        assert_eq!(s["model"], "gpt-4o");
        assert!(s["nested"].get("MY_TOKEN").is_none());
        assert_eq!(s["nested"]["ok"], true);
    }

    #[test]
    fn stamps_have_expected_shape() {
        let (compact, iso) = now_stamps();
        assert_eq!(compact.len(), 15);
        assert!(compact.contains('_'));
        assert!(iso.starts_with("20"));
    }

    #[test]
    fn safe_names() {
        assert_eq!(safe_session_name("my/session..name"), "my_session__name");
        assert_eq!(safe_session_name("ok-name_1"), "ok-name_1");
    }

    #[test]
    fn metadata_roundtrip_with_fork() {
        let data = json!({
            "name": "child",
            "fork_parent_id": "parent-123",
            "branch_name": "feature",
            "fork_point": 7,
            "branch_history": [
                {"session_id": "parent-123", "branch_name": "main", "timestamp": "2026-01-01T00:00:00Z", "parent_id": null}
            ],
        });
        let meta = metadata_of(&data);
        assert_eq!(meta.fork_parent_id.as_deref(), Some("parent-123"));
        assert_eq!(meta.branch_name.as_deref(), Some("feature"));
        assert_eq!(meta.fork_point, Some(7));
        assert_eq!(meta.branch_history.len(), 1);
        assert_eq!(meta.branch_history[0].session_id, "parent-123");
        assert_eq!(meta.branch_history[0].branch_name, "main");
    }

    #[test]
    fn metadata_backward_compat_no_fields() {
        let data = json!({
            "name": "old",
            "timestamp": "2026-01-01T00:00:00Z",
            "model": "gpt-4",
            "cwd": "/tmp",
            "history": [],
            "usage": {},
        });
        let meta = metadata_of(&data);
        assert_eq!(meta.fork_parent_id, None);
        assert_eq!(meta.branch_name, None);
        assert_eq!(meta.fork_point, None);
        assert!(meta.branch_history.is_empty());
    }

    #[test]
    fn with_metadata_merges_fields() {
        let data = json!({"name": "test", "history": []});
        let meta = SessionMetadata::new_fork("p1".into(), "br".into(), 3);
        let merged = with_metadata(data.clone(), &meta);
        assert_eq!(merged["fork_parent_id"], "p1");
        assert_eq!(merged["branch_name"], "br");
        assert_eq!(merged["fork_point"], 3);
        assert_eq!(merged["name"], "test");
    }

    #[test]
    fn with_metadata_omits_empty() {
        let data = json!({"name": "test", "history": []});
        let meta = SessionMetadata::default();
        let merged = with_metadata(data.clone(), &meta);
        assert!(merged.get("fork_parent_id").is_none());
        assert!(merged.get("branch_name").is_none());
        assert!(merged.get("fork_point").is_none());
        assert!(merged.get("branch_history").is_none());
        assert_eq!(merged["name"], "test");
    }

    #[test]
    fn branch_history_of_extracts() {
        let data = json!({
            "branch_history": [
                {"session_id": "s1", "branch_name": "main", "timestamp": "2026-01-01T00:00:00Z", "parent_id": null}
            ]
        });
        let history = branch_history_of(&data);
        assert_eq!(history.len(), 1);
        assert_eq!(history[0].session_id, "s1");
    }

    #[test]
    fn branch_history_of_empty_when_absent() {
        let data = json!({"name": "no-branch"});
        let history = branch_history_of(&data);
        assert!(history.is_empty());
    }
}
