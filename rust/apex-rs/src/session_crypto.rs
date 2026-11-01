//! Fernet (AES-128-CBC + HMAC-SHA256) implementation compatible with
//! `cryptography.fernet` as used by `apex/session.py`.
//!
//! Token layout (urlsafe base64, no padding):
//!   version(1)=0x80 | timestamp(8, BE) | IV(16) | ciphertext | HMAC-SHA256(32)
//!
//! Key layout (32 bytes): signing_key(16) | encryption_key(16).
//! The key lives in `~/.apex/.session_key`:
//!   * a 44-byte urlsafe-base64 Fernet key, or
//!   * a legacy raw 32-byte key, derived as `b64(sha256(raw + b":fernet"))`.

use aes::Aes128;
use base64::Engine;
use cbc::cipher::{block_padding::Pkcs7, BlockDecryptMut, BlockEncryptMut, KeyIvInit};
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
#[cfg(unix)]
use std::io::Read;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

type Aes128CbcEnc = cbc::Encryptor<Aes128>;
type Aes128CbcDec = cbc::Decryptor<Aes128>;
type HmacSha256 = Hmac<Sha256>;

/// Python's Fernet uses `urlsafe_b64encode`, i.e. URL-safe **with** padding.
/// Decoding also accepts unpadded tokens produced by older Rust builds.
const B64: base64::engine::general_purpose::GeneralPurpose =
    base64::engine::general_purpose::URL_SAFE;
const B64_NO_PAD: base64::engine::general_purpose::GeneralPurpose =
    base64::engine::general_purpose::URL_SAFE_NO_PAD;

pub fn b64_decode(s: &str) -> Option<Vec<u8>> {
    B64.decode(s)
        .or_else(|_| B64_NO_PAD.decode(s))
        .or_else(|_| base64::engine::general_purpose::STANDARD.decode(s))
        .ok()
}

pub fn key_path() -> PathBuf {
    crate::config::home_dir()
        .unwrap_or_default()
        .join(".apex")
        .join(".session_key")
}

fn random_bytes(n: usize) -> Vec<u8> {
    let mut buf = vec![0u8; n];
    #[cfg(unix)]
    {
        if let Ok(mut f) = std::fs::File::open("/dev/urandom") {
            if f.read_exact(&mut buf).is_ok() {
                return buf;
            }
        }
    }
    // Fallback: time-derived bytes (only used when /dev/urandom is unavailable).
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let mut hasher = Sha256::new();
    hasher.update(nanos.to_be_bytes());
    hasher.update(std::process::id().to_be_bytes());
    let digest = hasher.finalize();
    for (i, b) in buf.iter_mut().enumerate() {
        *b = digest[i % digest.len()];
    }
    buf
}

fn derive_legacy_key(raw: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(raw);
    hasher.update(b":fernet");
    B64.encode(hasher.finalize())
}

/// Load (or create) the Fernet key as a base64 string.
pub fn fernet_key() -> Option<String> {
    let path = key_path();
    if let Ok(raw) = std::fs::read(&path) {
        if raw.len() == 32 {
            return Some(derive_legacy_key(&raw));
        }
        if let Ok(s) = String::from_utf8(raw) {
            let trimmed = s.trim().to_string();
            if !trimmed.is_empty() {
                return Some(trimmed);
            }
        }
    }
    // No usable key: generate one (matches _get_fernet's behaviour).
    let key = B64.encode(random_bytes(32));
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(&path, key.as_bytes());
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
    }
    Some(key)
}

fn key_material(key: &str) -> Option<Vec<u8>> {
    let raw = b64_decode(key.trim().trim_end_matches('='))?;
    if raw.len() != 32 {
        return None;
    }
    Some(raw)
}

fn key_bytes() -> Option<Vec<u8>> {
    key_material(&fernet_key()?)
}

/// Decrypt a Fernet token with an explicit key (test fixture support).
fn decrypt_with_key(token: &str, key: &str) -> Option<String> {
    let key = key_material(key)?;
    let (sign_key, enc_key) = key.split_at(16);
    let data = b64_decode(token.trim())?;
    if data.len() < 1 + 8 + 16 + 32 || data[0] != 0x80 {
        return None;
    }
    let (body, mac) = data.split_at(data.len() - 32);
    let mut h = HmacSha256::new_from_slice(sign_key).ok()?;
    h.update(body);
    h.verify_slice(mac).ok()?;
    let iv = &body[9..25];
    let ciphertext = &body[25..];
    let plain = Aes128CbcDec::new(enc_key.into(), iv.into())
        .decrypt_padded_vec_mut::<Pkcs7>(ciphertext)
        .ok()?;
    String::from_utf8(plain).ok()
}

/// Decrypt a Fernet token into a UTF-8 string.
pub fn decrypt(token: &str) -> Option<String> {
    decrypt_with_key(token, &fernet_key()?)
}

/// Encrypt a UTF-8 string into a Fernet token.
pub fn encrypt(plain: &str) -> Option<String> {
    let key = key_bytes()?;
    let (sign_key, enc_key) = key.split_at(16);
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let iv = random_bytes(16);
    let ciphertext = Aes128CbcEnc::new(enc_key.into(), iv.as_slice().into())
        .encrypt_padded_vec_mut::<Pkcs7>(plain.as_bytes());
    let mut body = Vec::with_capacity(1 + 8 + 16 + ciphertext.len());
    body.push(0x80);
    body.extend_from_slice(&ts.to_be_bytes());
    body.extend_from_slice(&iv);
    body.extend_from_slice(&ciphertext);
    let mut h = HmacSha256::new_from_slice(sign_key).ok()?;
    h.update(&body);
    let mac = h.finalize().into_bytes();
    body.extend_from_slice(&mac);
    Some(B64.encode(body))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip() {
        let token = match encrypt("hello apex") {
            Some(t) => t,
            None => return,
        };
        assert_eq!(decrypt(&token).unwrap(), "hello apex");
    }

    #[test]
    fn tampered_token_is_rejected() {
        let token = match encrypt("secret") {
            Some(t) => t,
            None => return,
        };
        let mut bytes = b64_decode(&token).unwrap();
        let last = bytes.len() - 1;
        bytes[last] ^= 0x01;
        let tampered = B64.encode(bytes);
        assert!(decrypt(&tampered).is_none());
    }

    #[test]
    fn key_is_32_bytes() {
        let key = fernet_key().unwrap();
        assert_eq!(b64_decode(key.trim()).unwrap().len(), 32);
    }

    #[test]
    fn decrypts_python_written_fernet_session() {
        let key = include_str!("../tests/fixtures/session/fernet.key");
        let token = include_str!("../tests/fixtures/session/python_session.enc");
        let plain = decrypt_with_key(token, key).expect("Python-written Fernet token must decrypt");
        let value: serde_json::Value = serde_json::from_str(&plain).unwrap();
        assert_eq!(value["name"], "python-fixture");
        assert_eq!(value["timestamp"], "2026-01-02T03:04:05.123456");
        assert_eq!(value["model"], "anthropic/claude-sonnet-4-5");
        assert_eq!(value["cwd"], "/home/python/project");
        assert_eq!(value["history"].as_array().map(Vec::len), Some(2));
        assert_eq!(value["history"][0]["role"], "user");
        assert_eq!(value["usage"]["total_tokens"], 59);
    }

    #[test]
    fn decrypts_python_written_legacy_key_session() {
        let raw = include_bytes!("../tests/fixtures/session/legacy.key");
        assert_eq!(raw.len(), 32);
        let key = derive_legacy_key(raw);
        let token = include_str!("../tests/fixtures/session/python_session_legacy.enc");
        let plain = decrypt_with_key(token, &key).expect("legacy Python Fernet token must decrypt");
        let value: serde_json::Value = serde_json::from_str(&plain).unwrap();
        assert_eq!(value["name"], "python-legacy");
        assert_eq!(value["model"], "openai/gpt-5");
        assert_eq!(value["history"].as_array().map(Vec::len), Some(2));
    }
}
