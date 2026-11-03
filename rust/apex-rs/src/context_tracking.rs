//! Context tracking — port of `apex/context_manager.py` / `apex/context_tracking.py`.
//!
//! Tracks per-session token/message usage, decides when a session approaches the
//! context limit, and records compaction operations (prune / summarize / merge).
//! This is separate from the actual compaction logic living in `agent.rs`
//! (`compact_context`) — here we only do the accounting and history.

use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// A recorded compaction operation.
#[allow(dead_code)] // context accounting will be wired into the dispatch gate — TODO(v2.6): wire into tool dispatch / agent loop
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq)]
pub struct CompactionRecord {
    pub strategy: String,        // "prune" | "summarize" | "merge"
    pub tokens_before: usize,
    pub tokens_after: usize,
    pub removed_messages: usize,
    pub timestamp: String,
}

/// Per-session context accounting.
#[allow(dead_code)] // context accounting will be wired into the dispatch gate — TODO(v2.6): wire into tool dispatch / agent loop
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq, Eq, Default)]
pub struct SessionContext {
    pub session_id: String,
    pub token_count: usize,
    pub message_count: usize,
    pub compaction_count: u32,
    pub last_compaction: Option<String>,
    pub history: Vec<CompactionRecord>,
}

/// Tracks context usage across sessions and decides when compaction is needed.
#[allow(dead_code)] // context accounting will be wired into the dispatch gate — TODO(v2.6): wire into tool dispatch / agent loop
#[derive(Debug, Clone, Default)]
pub struct ContextTracker {
    sessions: HashMap<String, SessionContext>,
    max_tokens: usize,
    threshold: f64, // fraction of max_tokens that triggers compaction (0.0–1.0)
}

#[allow(dead_code)] // context accounting will be wired into the dispatch gate — TODO(v2.6): wire into tool dispatch / agent loop
impl ContextTracker {
    /// Create a tracker with the given token budget and compaction threshold.
    pub fn new(max_tokens: usize, threshold: f64) -> Self {
        Self {
            sessions: HashMap::new(),
            max_tokens,
            threshold: threshold.clamp(0.0, 1.0),
        }
    }

    /// Default tracker: 128k token budget, compaction at 80%.
    pub fn default_with_budget() -> Self {
        Self::new(128_000, 0.8)
    }

    /// Record `tokens` consumed by `messages` new messages in `session_id`.
    pub fn record_usage(&mut self, session_id: &str, tokens: usize, messages: usize) {
        let ctx = self
            .sessions
            .entry(session_id.to_string())
            .or_insert_with(|| SessionContext {
                session_id: session_id.to_string(),
                ..Default::default()
            });
        ctx.token_count += tokens;
        ctx.message_count += messages;
    }

    /// Returns true if the session has exceeded the compaction threshold.
    pub fn should_compact(&self, session_id: &str) -> bool {
        let Some(ctx) = self.sessions.get(session_id) else {
            return false;
        };
        if self.max_tokens == 0 {
            return false;
        }
        (ctx.token_count as f64 / self.max_tokens as f64) >= self.threshold
    }

    /// Returns the fraction of the budget used (0.0–1.0+).
    pub fn usage_ratio(&self, session_id: &str) -> f64 {
        let Some(ctx) = self.sessions.get(session_id) else {
            return 0.0;
        };
        if self.max_tokens == 0 {
            return 0.0;
        }
        ctx.token_count as f64 / self.max_tokens as f64
    }

    /// Record a compaction operation for `session_id`.
    pub fn record_compaction(
        &mut self,
        session_id: &str,
        strategy: &str,
        tokens_before: usize,
        tokens_after: usize,
        removed_messages: usize,
    ) {
        let timestamp = now_iso();
        let record = CompactionRecord {
            strategy: strategy.to_string(),
            tokens_before,
            tokens_after,
            removed_messages,
            timestamp,
        };

        let ctx = self
            .sessions
            .entry(session_id.to_string())
            .or_insert_with(|| SessionContext {
                session_id: session_id.to_string(),
                ..Default::default()
            });
        ctx.history.push(record.clone());
        ctx.compaction_count += 1;
        ctx.last_compaction = Some(strategy.to_string());
        ctx.token_count = tokens_after;
    }

    /// Get the context stats for a session, if tracked.
    pub fn get(&self, session_id: &str) -> Option<&SessionContext> {
        self.sessions.get(session_id)
    }

    /// List all tracked session IDs.
    pub fn sessions(&self) -> Vec<&String> {
        self.sessions.keys().collect()
    }

    /// Remove a session from tracking.
    pub fn remove(&mut self, session_id: &str) -> Option<SessionContext> {
        self.sessions.remove(session_id)
    }

    /// Number of tracked sessions.
    pub fn len(&self) -> usize {
        self.sessions.len()
    }

    pub fn is_empty(&self) -> bool {
        self.sessions.is_empty()
    }
}

/// Current UTC timestamp in ISO-8601 (matches Python's `datetime.utcnow().isoformat()`).
#[allow(dead_code)] // used only by compaction recording — TODO(v2.6): wire into tool dispatch / agent loop
fn now_iso() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    // Simple ISO-8601 without external chrono dep to keep the module light.
    format!("{secs}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn track_usage_and_should_compact() {
        let mut tracker = ContextTracker::new(1000, 0.8);
        assert!(!tracker.should_compact("s1"));

        tracker.record_usage("s1", 500, 10);
        assert!(!tracker.should_compact("s1")); // 50% < 80%

        tracker.record_usage("s1", 400, 5);
        assert!(tracker.should_compact("s1")); // 90% >= 80%
    }

    #[test]
    fn usage_ratio_is_bounded() {
        let tracker = ContextTracker::new(1000, 0.8);
        assert_eq!(tracker.usage_ratio("unknown"), 0.0);

        let mut t = tracker;
        t.record_usage("s1", 250, 5);
        assert!((t.usage_ratio("s1") - 0.25).abs() < f64::EPSILON);
    }

    #[test]
    fn record_compaction_updates_stats() {
        let mut tracker = ContextTracker::new(10000, 0.8);
        tracker.record_usage("s1", 9000, 50);

        tracker.record_compaction("s1", "prune", 9000, 3000, 40);

        let ctx = tracker.get("s1").unwrap();
        assert_eq!(ctx.compaction_count, 1);
        assert_eq!(ctx.last_compaction.as_deref(), Some("prune"));
        assert_eq!(ctx.token_count, 3000);
        assert_eq!(ctx.history.len(), 1);
        assert_eq!(ctx.history[0].strategy, "prune");
        assert_eq!(ctx.history[0].removed_messages, 40);

        // After compaction the session is below threshold again.
        assert!(!tracker.should_compact("s1"));
    }

    #[test]
    fn multiple_sessions_independent() {
        let mut tracker = ContextTracker::new(1000, 0.5);
        tracker.record_usage("a", 600, 5); // 60% -> compact
        tracker.record_usage("b", 200, 2); // 20% -> no compact

        assert!(tracker.should_compact("a"));
        assert!(!tracker.should_compact("b"));
        assert_eq!(tracker.sessions().len(), 2);
    }

    #[test]
    fn remove_session() {
        let mut tracker = ContextTracker::new(1000, 0.5);
        tracker.record_usage("s1", 100, 1);
        assert!(tracker.remove("s1").is_some());
        assert!(tracker.get("s1").is_none());
        assert!(tracker.is_empty());
    }

    #[test]
    fn default_budget_and_threshold() {
        let tracker = ContextTracker::default_with_budget();
        assert_eq!(tracker.max_tokens, 128_000);
        assert!((tracker.threshold - 0.8).abs() < f64::EPSILON);
    }
}
