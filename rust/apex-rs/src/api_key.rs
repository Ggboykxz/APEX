//! API key management — port of `apex/api_key.py`.
//!
//! Divergence from the Python reference (documented in PARITY.md): the store
//! is a JSON file (`~/.apex/api_keys.json`, overridable with
//! `APEX_API_KEYS_FILE`) instead of SQLite, because the Rust port carries no
//! SQLite dependency. The semantics match Python's: keys are `apex_` + 32
//! random urlsafe-base64 bytes, only the sha256 hex is persisted, and
//! validation checks prefix → hash → active → expiry before updating
//! `last_used`/`request_count`. Workspaces exist only as the fixed
//! `"default"` id — Python's `validate_key` never checks workspace state
//! either, and workspace CRUD is not ported.

use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

/// Fixed workspace id: the Rust port has no workspace CRUD.
pub const DEFAULT_WORKSPACE: &str = "default";

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn sha256_hex(value: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(value.as_bytes());
    hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

/// Python: `str(uuid.uuid4())[:8]` — an 8-char hex id. The Rust port has no
/// uuid dependency; the id is a time/counter mix in the same shape (the same
/// pattern as `task_queue::new_task_id`).
fn new_key_id() -> String {
    static COUNTER: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0);
    let n = COUNTER.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
    format!("{:08x}", (now ^ n) & 0xFFFF_FFFF)
}

/// Python: `APIKeyInfo`. The rate-limit/permission/metadata fields are kept
/// for schema parity even though the Rust server applies one global limit.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct APIKeyInfo {
    pub key_id: String,
    pub key_hash: String,
    pub workspace_id: String,
    pub name: String,
    pub created_at: f64,
    #[serde(default)]
    pub expires_at: Option<f64>,
    #[serde(default)]
    pub last_used: Option<f64>,
    #[serde(default)]
    pub request_count: u64,
    #[serde(default = "default_true")]
    pub is_active: bool,
    #[serde(default = "default_rate_minute")]
    pub rate_limit_per_minute: u32,
    #[serde(default = "default_rate_hour")]
    pub rate_limit_per_hour: u32,
    #[serde(default)]
    pub permissions: Vec<String>,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

fn default_true() -> bool {
    true
}

fn default_rate_minute() -> u32 {
    60
}

fn default_rate_hour() -> u32 {
    1000
}

/// Python's `InvalidKeyError` / `KeyExpiredError` / `KeyDisabledError`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyError {
    /// Malformed or unknown key (Python folds "not found" into `InvalidKeyError`).
    Invalid,
    Expired,
    Disabled,
}

impl std::fmt::Display for KeyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            KeyError::Invalid => f.write_str("Invalid API key"),
            KeyError::Expired => f.write_str("API key has expired"),
            KeyError::Disabled => f.write_str("API key is disabled"),
        }
    }
}

/// `~/.apex/api_keys.json` (Python: `~/.apex/api_keys.db`), overridable with
/// `APEX_API_KEYS_FILE` for tests and alternate deployments.
pub fn default_store_path() -> PathBuf {
    if let Ok(path) = std::env::var("APEX_API_KEYS_FILE") {
        if !path.trim().is_empty() {
            return PathBuf::from(path);
        }
    }
    crate::config::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".apex")
        .join("api_keys.json")
}

#[derive(Serialize, Deserialize, Default)]
struct Store {
    #[serde(default)]
    keys: Vec<APIKeyInfo>,
}

/// Port of `KeyManager` (JSON-file backend).
///
/// The file is re-read on every operation, so a key created or revoked by
/// another process (the `key` CLI) is visible immediately — the same
/// behaviour as Python's per-call SQLite connections.
pub struct KeyManager {
    path: PathBuf,
    /// Serialises read-modify-write cycles inside this process.
    lock: Mutex<()>,
}

impl KeyManager {
    pub fn new(path: impl Into<PathBuf>) -> Self {
        let path = path.into();
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        Self {
            path,
            lock: Mutex::new(()),
        }
    }

    pub fn default_store() -> Self {
        Self::new(default_store_path())
    }

    fn guard(&self) -> std::sync::MutexGuard<'_, ()> {
        match self.lock.lock() {
            Ok(g) => g,
            Err(poisoned) => poisoned.into_inner(),
        }
    }

    fn load(&self) -> Vec<APIKeyInfo> {
        match std::fs::read_to_string(&self.path) {
            Ok(text) => serde_json::from_str::<Store>(&text)
                .map(|store| store.keys)
                .unwrap_or_else(|err| {
                    // Fail closed: a corrupt store authenticates nobody.
                    eprintln!(
                        "WARNING: ignoring malformed key store {}: {err}",
                        self.path.display()
                    );
                    Vec::new()
                }),
            Err(_) => Vec::new(),
        }
    }

    fn save(&self, keys: &[APIKeyInfo]) {
        let store = Store {
            keys: keys.to_vec(),
        };
        let Ok(text) = serde_json::to_string_pretty(&store) else {
            return;
        };
        if let Some(parent) = self.path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        // Atomic replace: a concurrent reader never sees a half-written store.
        let tmp = self.path.with_extension("json.tmp");
        if let Err(err) = std::fs::write(&tmp, text) {
            eprintln!(
                "WARNING: failed to write key store {}: {err}",
                self.path.display()
            );
            return;
        }
        if let Err(err) = std::fs::rename(&tmp, &self.path) {
            eprintln!(
                "WARNING: failed to replace key store {}: {err}",
                self.path.display()
            );
            let _ = std::fs::remove_file(&tmp);
        }
    }

    /// Python: `create_key` — returns the plaintext key (shown once) and the
    /// stored info. `expires_in` is seconds from now; `None` or 0 means no
    /// expiry (Python's falsy check). A negative value yields an
    /// already-expired key, exactly as in Python.
    pub fn create_key(&self, name: &str, expires_in: Option<i64>) -> (String, APIKeyInfo) {
        let _guard = self.guard();
        let mut bytes = [0u8; 32];
        if getrandom::getrandom(&mut bytes).is_err() {
            // The OS CSPRNG is the only acceptable source for API keys; a
            // failure must not fall back to a weaker generator.
            panic!("failed to obtain random bytes for an API key");
        }
        let key = format!("apex_{}", URL_SAFE_NO_PAD.encode(bytes));
        let created_at = now_secs();
        let info = APIKeyInfo {
            key_id: new_key_id(),
            key_hash: sha256_hex(&key),
            workspace_id: DEFAULT_WORKSPACE.to_string(),
            name: name.to_string(),
            created_at,
            expires_at: expires_in
                .filter(|seconds| *seconds != 0)
                .map(|seconds| created_at + seconds as f64),
            last_used: None,
            request_count: 0,
            is_active: true,
            rate_limit_per_minute: 60,
            rate_limit_per_hour: 1000,
            permissions: Vec::new(),
            metadata: serde_json::json!({}),
        };
        let mut keys = self.load();
        keys.push(info.clone());
        self.save(&keys);
        (key, info)
    }

    /// Python: `validate_key`. Returns the pre-update info (its
    /// `request_count` is stale by one, exactly like Python) after persisting
    /// `last_used` and incrementing `request_count`.
    pub fn validate_key(&self, key: &str) -> Result<APIKeyInfo, KeyError> {
        if key.is_empty() || !key.starts_with("apex_") {
            return Err(KeyError::Invalid);
        }
        let hash = sha256_hex(key);
        let _guard = self.guard();
        let mut keys = self.load();
        let index = keys
            .iter()
            .position(|candidate| candidate.key_hash == hash)
            .ok_or(KeyError::Invalid)?;
        let info = keys[index].clone();
        if !info.is_active {
            return Err(KeyError::Disabled);
        }
        if let Some(expires_at) = info.expires_at {
            if now_secs() > expires_at {
                return Err(KeyError::Expired);
            }
        }
        keys[index].last_used = Some(now_secs());
        keys[index].request_count += 1;
        self.save(&keys);
        Ok(info)
    }

    /// Python: `revoke_key` — deactivate; `false` when the id is unknown.
    pub fn revoke_key(&self, key_id: &str) -> bool {
        let _guard = self.guard();
        let mut keys = self.load();
        let Some(info) = keys.iter_mut().find(|candidate| candidate.key_id == key_id) else {
            return false;
        };
        info.is_active = false;
        self.save(&keys);
        true
    }

    /// Python: `delete_key`.
    pub fn delete_key(&self, key_id: &str) -> bool {
        let _guard = self.guard();
        let mut keys = self.load();
        let before = keys.len();
        keys.retain(|candidate| candidate.key_id != key_id);
        if keys.len() == before {
            return false;
        }
        self.save(&keys);
        true
    }

    /// Python: `list_keys(workspace_id)` for the fixed default workspace.
    pub fn list_keys(&self) -> Vec<APIKeyInfo> {
        self.load()
            .into_iter()
            .filter(|candidate| candidate.workspace_id == DEFAULT_WORKSPACE)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn manager() -> (tempfile::TempDir, KeyManager) {
        let dir = tempdir().unwrap();
        let km = KeyManager::new(dir.path().join("api_keys.json"));
        (dir, km)
    }

    #[test]
    fn create_validate_and_hash_at_rest() {
        let (dir, km) = manager();
        let (key, info) = km.create_key("ci", None);
        assert!(key.starts_with("apex_"));
        // 32 random bytes → 43 urlsafe-base64 chars, no padding.
        assert_eq!(key.len(), "apex_".len() + 43);
        assert_eq!(info.key_id.len(), 8);
        assert!(info.key_id.chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(info.workspace_id, DEFAULT_WORKSPACE);
        assert_eq!(info.expires_at, None);
        assert!(info.is_active);

        let stored = std::fs::read_to_string(dir.path().join("api_keys.json")).unwrap();
        assert!(!stored.contains(&key), "plaintext key must not be stored");
        assert!(stored.contains(&sha256_hex(&key)));
        assert!(stored.contains(&info.key_id));

        let validated = km.validate_key(&key).expect("valid key");
        assert_eq!(validated.key_id, info.key_id);
        assert_eq!(validated.request_count, 0, "returned info is pre-update");
        km.validate_key(&key).unwrap();

        let listed = km.list_keys();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].request_count, 2);
        assert!(listed[0].last_used.is_some());
    }

    #[test]
    fn malformed_and_unknown_keys_are_invalid() {
        let (_dir, km) = manager();
        assert_eq!(km.validate_key(""), Err(KeyError::Invalid));
        assert_eq!(km.validate_key("not-a-key"), Err(KeyError::Invalid));
        // Correct shape, but not in the store.
        assert_eq!(
            km.validate_key("apex_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"),
            Err(KeyError::Invalid)
        );
    }

    #[test]
    fn expired_key_is_rejected() {
        let (_dir, km) = manager();
        let (key, _) = km.create_key("old", Some(-60));
        assert_eq!(km.validate_key(&key), Err(KeyError::Expired));
        // Python quirk: 0 is falsy → no expiry.
        let (key2, info2) = km.create_key("forever", Some(0));
        assert_eq!(info2.expires_at, None);
        assert!(km.validate_key(&key2).is_ok());
    }

    #[test]
    fn revoked_key_is_rejected() {
        let (_dir, km) = manager();
        let (key, info) = km.create_key("ci", None);
        assert!(km.revoke_key(&info.key_id));
        assert_eq!(km.validate_key(&key), Err(KeyError::Disabled));
        assert!(!km.revoke_key("deadbeef"));
        // Revoking twice still succeeds: the row exists.
        assert!(km.revoke_key(&info.key_id));
    }

    #[test]
    fn delete_removes_key() {
        let (_dir, km) = manager();
        let (key, info) = km.create_key("ci", None);
        assert!(km.delete_key(&info.key_id));
        assert_eq!(km.validate_key(&key), Err(KeyError::Invalid));
        assert!(!km.delete_key(&info.key_id));
        assert!(km.list_keys().is_empty());
    }

    #[test]
    fn keys_survive_reload_and_list_reports_all() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("api_keys.json");
        let first = KeyManager::new(&path);
        let (key_a, _) = first.create_key("a", None);
        let (key_b, _) = first.create_key("b", None);
        let names: Vec<String> = first.list_keys().into_iter().map(|k| k.name).collect();
        assert_eq!(names, vec!["a", "b"]);

        // A fresh manager (like a new server process) sees both keys.
        let second = KeyManager::new(&path);
        assert!(second.validate_key(&key_a).is_ok());
        assert!(second.validate_key(&key_b).is_ok());
    }

    #[test]
    fn external_changes_are_visible_without_restart() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("api_keys.json");
        let server_view = KeyManager::new(&path);
        let cli_view = KeyManager::new(&path);
        let (key, info) = cli_view.create_key("out-of-band", None);
        // The server created its manager before the key existed.
        assert!(server_view.validate_key(&key).is_ok());
        assert!(cli_view.revoke_key(&info.key_id));
        assert_eq!(server_view.validate_key(&key), Err(KeyError::Disabled));
    }

    #[test]
    fn default_store_path_honours_override() {
        // Only this test touches APEX_API_KEYS_FILE.
        let previous = std::env::var_os("APEX_API_KEYS_FILE");
        std::env::set_var("APEX_API_KEYS_FILE", "/tmp/custom-keys.json");
        assert_eq!(default_store_path(), PathBuf::from("/tmp/custom-keys.json"));
        match previous {
            Some(value) => std::env::set_var("APEX_API_KEYS_FILE", value),
            None => std::env::remove_var("APEX_API_KEYS_FILE"),
        }
    }
}
