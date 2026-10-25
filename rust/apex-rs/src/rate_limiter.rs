//! Rate limiting — port of `apex/rate_limiter.py` (in-memory path).
//!
//! Mirrors the Python reference (`MemoryStorage` + `RateLimiter`) with the
//! same per-minute/hour/day windows. The SQLite backend is not ported yet
//! (it would require a `rusqlite` dependency); `MemoryStorage` matches the
//! default `create_rate_limiter()` behavior.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

const WINDOW_DURATIONS: &[(&str, f64)] = &[("minute", 60.0), ("hour", 3600.0), ("day", 86400.0)];

// ────────────────────────────────────────────────────────────
// Config + result
// ────────────────────────────────────────────────────────────

/// Port of `RateLimitConfig`.
#[derive(Debug, Clone, Copy)]
pub struct RateLimitConfig {
    pub requests_per_minute: u32,
    pub requests_per_hour: u32,
    pub requests_per_day: u32,
    pub burst_size: u32,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            requests_per_minute: 60,
            requests_per_hour: 1000,
            requests_per_day: 10000,
            burst_size: 10,
        }
    }
}

/// Port of `RateLimitResult`.
#[derive(Debug, Clone)]
pub struct RateLimitResult {
    pub allowed: bool,
    pub remaining_minute: i64,
    pub remaining_hour: i64,
    pub remaining_day: i64,
    pub reset_at: f64,
    pub retry_after: Option<u64>,
}

// ────────────────────────────────────────────────────────────
// Storage
// ────────────────────────────────────────────────────────────

/// Per-window counter state.
#[derive(Debug, Clone, Default)]
struct WindowCounts {
    minute: (u32, f64),
    hour: (u32, f64),
    day: (u32, f64),
}

/// Port of `StorageBackend` (in-memory).
pub trait StorageBackend {
    fn get_counts(&self, key: &str) -> [u32; 3]; // [minute, hour, day]
    fn increment(&mut self, key: &str, window: &str);
    fn cleanup_expired(&mut self);
}

/// Port of `MemoryStorage`.
#[derive(Debug, Default)]
pub struct MemoryStorage {
    counts: HashMap<String, WindowCounts>,
}

impl StorageBackend for MemoryStorage {
    fn get_counts(&self, key: &str) -> [u32; 3] {
        let Some(w) = self.counts.get(key) else {
            return [0, 0, 0];
        };
        let now = now_secs();
        let minute = if now - w.minute.1 > 60.0 {
            0
        } else {
            w.minute.0
        };
        let hour = if now - w.hour.1 > 3600.0 { 0 } else { w.hour.0 };
        let day = if now - w.day.1 > 86400.0 { 0 } else { w.day.0 };
        [minute, hour, day]
    }

    fn increment(&mut self, key: &str, window: &str) {
        let w = self.counts.entry(key.to_string()).or_default();
        let now = now_secs();
        match window {
            "minute" => {
                if now - w.minute.1 > 60.0 {
                    w.minute = (1, now);
                } else {
                    w.minute.0 += 1;
                }
            }
            "hour" => {
                if now - w.hour.1 > 3600.0 {
                    w.hour = (1, now);
                } else {
                    w.hour.0 += 1;
                }
            }
            "day" => {
                if now - w.day.1 > 86400.0 {
                    w.day = (1, now);
                } else {
                    w.day.0 += 1;
                }
            }
            _ => {}
        }
    }

    fn cleanup_expired(&mut self) {
        let now = now_secs();
        self.counts.retain(|_, w| {
            let alive_minute = now - w.minute.1 <= 60.0;
            let alive_hour = now - w.hour.1 <= 3600.0;
            let alive_day = now - w.day.1 <= 86400.0;
            alive_minute || alive_hour || alive_day
        });
    }
}

// ────────────────────────────────────────────────────────────
// RateLimiter
// ────────────────────────────────────────────────────────────

/// Port of `RateLimiter`.
pub struct RateLimiter {
    config: RateLimitConfig,
    storage: Box<dyn StorageBackend>,
    last_cleanup: f64,
    cleanup_interval: f64,
}

impl RateLimiter {
    pub fn new(config: RateLimitConfig, storage: Box<dyn StorageBackend>) -> Self {
        Self {
            config,
            storage,
            last_cleanup: now_secs(),
            cleanup_interval: 3600.0,
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(
            RateLimitConfig::default(),
            Box::new(MemoryStorage::default()),
        )
    }

    pub fn check_rate_limit(&mut self, key: &str) -> RateLimitResult {
        if now_secs() - self.last_cleanup > self.cleanup_interval {
            self.storage.cleanup_expired();
            self.last_cleanup = now_secs();
        }
        let [minute, hour, day] = self.storage.get_counts(key);
        let now = now_secs();

        if minute >= self.config.requests_per_minute {
            return RateLimitResult {
                allowed: false,
                remaining_minute: 0,
                remaining_hour: (self.config.requests_per_hour as i64 - hour as i64).max(0),
                remaining_day: (self.config.requests_per_day as i64 - day as i64).max(0),
                reset_at: now + 60.0,
                retry_after: Some(60),
            };
        }
        if hour >= self.config.requests_per_hour {
            return RateLimitResult {
                allowed: false,
                remaining_minute: 0,
                remaining_hour: 0,
                remaining_day: (self.config.requests_per_day as i64 - day as i64).max(0),
                reset_at: now + 3600.0,
                retry_after: Some(3600),
            };
        }
        if day >= self.config.requests_per_day {
            return RateLimitResult {
                allowed: false,
                remaining_minute: 0,
                remaining_hour: 0,
                remaining_day: 0,
                reset_at: now + 86400.0,
                retry_after: Some(86400),
            };
        }

        self.storage.increment(key, "minute");
        self.storage.increment(key, "hour");
        self.storage.increment(key, "day");

        RateLimitResult {
            allowed: true,
            remaining_minute: self.config.requests_per_minute as i64 - minute as i64 - 1,
            remaining_hour: self.config.requests_per_hour as i64 - hour as i64 - 1,
            remaining_day: self.config.requests_per_day as i64 - day as i64 - 1,
            reset_at: now + 60.0,
            retry_after: None,
        }
    }

    pub fn get_status(&self, key: &str) -> serde_json::Value {
        let [minute, hour, day] = self.storage.get_counts(key);
        serde_json::json!({
            "minute": {"used": minute, "limit": self.config.requests_per_minute},
            "hour": {"used": hour, "limit": self.config.requests_per_hour},
            "day": {"used": day, "limit": self.config.requests_per_day},
        })
    }
}

// ────────────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn limiter_with(per_minute: u32) -> RateLimiter {
        let config = RateLimitConfig {
            requests_per_minute: per_minute,
            requests_per_hour: 100,
            requests_per_day: 1000,
            burst_size: 10,
        };
        RateLimiter::new(config, Box::new(MemoryStorage::default()))
    }

    #[test]
    fn allows_until_limit() {
        let mut rl = limiter_with(2);
        let r1 = rl.check_rate_limit("user_1");
        assert!(r1.allowed);
        assert_eq!(r1.remaining_minute, 1);
        let r2 = rl.check_rate_limit("user_1");
        assert!(r2.allowed);
        assert_eq!(r2.remaining_minute, 0);
    }

    #[test]
    fn blocks_over_minute_limit() {
        let mut rl = limiter_with(2);
        rl.check_rate_limit("k");
        rl.check_rate_limit("k");
        let r3 = rl.check_rate_limit("k");
        assert!(!r3.allowed);
        assert_eq!(r3.remaining_minute, 0);
        assert_eq!(r3.retry_after, Some(60));
    }

    #[test]
    fn keys_are_independent() {
        let mut rl = limiter_with(1);
        assert!(rl.check_rate_limit("a").allowed);
        assert!(rl.check_rate_limit("b").allowed);
        assert!(!rl.check_rate_limit("a").allowed);
    }

    #[test]
    fn status_shape() {
        let mut rl = limiter_with(1);
        rl.check_rate_limit("s");
        let status = rl.get_status("s");
        assert_eq!(status["minute"]["used"], 1);
        assert_eq!(status["minute"]["limit"], 1);
    }

    #[test]
    fn cleanup_removes_expired_keys() {
        let mut storage = MemoryStorage::default();
        storage.increment("old", "minute");
        // Simulate age by rewriting the timestamp far in the past.
        if let Some(w) = storage.counts.get_mut("old") {
            w.minute.1 = now_secs() - 120.0;
        }
        storage.cleanup_expired();
        assert!(storage.counts.is_empty());
    }
}
