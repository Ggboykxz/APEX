//! telemetry — Telemetry and logging system ported from `apex/telemetry.py`.
//!
//! Provides event logging, session tracking, and performance monitoring.

#![allow(dead_code)]
#![allow(clippy::all)]

use std::collections::HashMap;
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::Value;

/// Event types for telemetry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EventType {
    AgentStart,
    AgentMessage,
    ToolCall,
    ToolResult,
    ModelSwitch,
    AgentSwitch,
    Error,
    SessionStart,
    SessionEnd,
}

impl EventType {
    pub fn as_str(&self) -> &'static str {
        match self {
            EventType::AgentStart => "agent_start",
            EventType::AgentMessage => "agent_message",
            EventType::ToolCall => "tool_call",
            EventType::ToolResult => "tool_result",
            EventType::ModelSwitch => "model_switch",
            EventType::AgentSwitch => "agent_switch",
            EventType::Error => "error",
            EventType::SessionStart => "session_start",
            EventType::SessionEnd => "session_end",
        }
    }
}

/// A single telemetry event.
#[derive(Debug, Clone, PartialEq)]
pub struct TelemetryEvent {
    pub timestamp: String,
    pub event_type: String,
    pub data: HashMap<String, Value>,
    pub duration_ms: Option<f64>,
}

/// Telemetry logger — logs events and persists to JSONL.
pub struct Logger {
    log_dir: PathBuf,
    current_session: String,
    events: Vec<TelemetryEvent>,
    start_time: f64,
}

impl Logger {
    pub fn new(log_dir: Option<&Path>) -> Self {
        let log_dir = log_dir.map(|p| p.to_path_buf()).unwrap_or_else(|| {
            dirs::home_dir()
                .unwrap_or_default()
                .join(".apex")
                .join("logs")
        });
        let _ = std::fs::create_dir_all(&log_dir);
        let current_session = Self::_new_session_id();
        let start_time = time_now();
        Self {
            log_dir,
            current_session,
            events: Vec::new(),
            start_time,
        }
    }

    fn _new_session_id() -> String {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        let secs = now.as_secs();
        // Format as YYYYMMDD_HHMMSS
        format!(
            "{:04}{:02}{:02}_{:02}{:02}{:02}",
            1970 + secs / 31556952, // rough year
            1,                      // rough month
            1,                      // rough day
            0,
            0,
            0
        ) // rough time
    }

    pub fn log(
        &mut self,
        event_type: EventType,
        data: Option<HashMap<String, Value>>,
        duration_ms: Option<f64>,
    ) {
        let event = TelemetryEvent {
            timestamp: format!("{}", time_now()),
            event_type: event_type.as_str().to_string(),
            data: data.unwrap_or_default(),
            duration_ms,
        };
        self.events.push(event);
    }

    pub fn log_agent_start(&mut self, model: &str, agent: &str) {
        let mut data = HashMap::new();
        data.insert("model".to_string(), Value::String(model.to_string()));
        data.insert("agent".to_string(), Value::String(agent.to_string()));
        self.log(EventType::AgentStart, Some(data), None);
    }

    pub fn log_tool_call(&mut self, tool_name: &str, args: &HashMap<String, Value>) -> String {
        let sanitized = self._sanitize_args(args);
        let mut data = HashMap::new();
        data.insert("tool".to_string(), Value::String(tool_name.to_string()));
        data.insert(
            "args".to_string(),
            Value::Object(sanitized.into_iter().collect()),
        );
        self.log(EventType::ToolCall, Some(data), None);
        tool_name.to_string()
    }

    pub fn log_tool_result(&mut self, tool_name: &str, result: &str, duration_ms: f64) {
        let success = !result.starts_with("ERROR");
        let mut data = HashMap::new();
        data.insert("tool".to_string(), Value::String(tool_name.to_string()));
        data.insert("success".to_string(), Value::Bool(success));
        data.insert(
            "result_length".to_string(),
            Value::Number(result.len().into()),
        );
        self.log(EventType::ToolResult, Some(data), Some(duration_ms));
    }

    pub fn log_model_switch(&mut self, old_model: &str, new_model: &str) {
        let mut data = HashMap::new();
        data.insert("old".to_string(), Value::String(old_model.to_string()));
        data.insert("new".to_string(), Value::String(new_model.to_string()));
        self.log(EventType::ModelSwitch, Some(data), None);
    }

    pub fn log_agent_switch(&mut self, old_agent: &str, new_agent: &str) {
        let mut data = HashMap::new();
        data.insert("old".to_string(), Value::String(old_agent.to_string()));
        data.insert("new".to_string(), Value::String(new_agent.to_string()));
        self.log(EventType::AgentSwitch, Some(data), None);
    }

    pub fn log_error(
        &mut self,
        error_type: &str,
        message: &str,
        context: Option<HashMap<String, Value>>,
    ) {
        let mut data = HashMap::new();
        data.insert(
            "error_type".to_string(),
            Value::String(error_type.to_string()),
        );
        data.insert("message".to_string(), Value::String(message.to_string()));
        data.insert(
            "context".to_string(),
            Value::Object(context.unwrap_or_default().into_iter().collect()),
        );
        self.log(EventType::Error, Some(data), None);
    }

    pub fn log_session_start(&mut self, cwd: &str) {
        self.start_time = time_now();
        let mut data = HashMap::new();
        data.insert("cwd".to_string(), Value::String(cwd.to_string()));
        data.insert(
            "session_id".to_string(),
            Value::String(self.current_session.clone()),
        );
        self.log(EventType::SessionStart, Some(data), None);
    }

    pub fn log_session_end(&mut self) {
        let duration = (time_now() - self.start_time) * 1000.0;
        let mut data = HashMap::new();
        data.insert(
            "session_id".to_string(),
            Value::String(self.current_session.clone()),
        );
        data.insert(
            "duration_ms".to_string(),
            Value::Number(
                serde_json::Number::from_f64(duration).unwrap_or(serde_json::Number::from(0)),
            ),
        );
        data.insert(
            "event_count".to_string(),
            Value::Number(self.events.len().into()),
        );
        self.log(EventType::SessionEnd, Some(data), None);
    }

    fn _sanitize_args(&self, args: &HashMap<String, Value>) -> HashMap<String, Value> {
        let sensitive_keys = [
            "api_key",
            "password",
            "token",
            "secret",
            "key",
            "aws_access_key",
            "aws_secret_key",
            "aws_session_token",
            "access_key",
            "secret_key",
            "session_token",
            "private_key",
            "secret_token",
            "auth_token",
            "bearer",
            "credential",
            "credentials",
        ];
        let mut sanitized = HashMap::new();
        for (k, v) in args {
            let key_lower = k.to_lowercase();
            let is_sensitive = sensitive_keys.iter().any(|s| key_lower.contains(s));
            if is_sensitive {
                sanitized.insert(k.clone(), Value::String("***".to_string()));
            } else {
                let s = v.as_str().unwrap_or("");
                sanitized.insert(k.clone(), Value::String(s.chars().take(100).collect()));
            }
        }
        sanitized
    }

    pub fn save(&self) {
        let log_file = self
            .log_dir
            .join(format!("session_{}.jsonl", self.current_session));
        if let Ok(mut f) = File::create(&log_file) {
            for event in &self.events {
                let line = serde_json::json!({
                    "timestamp": event.timestamp,
                    "event_type": event.event_type,
                    "data": event.data,
                    "duration_ms": event.duration_ms,
                });
                let _ = writeln!(f, "{}", line);
            }
        }
    }

    pub fn get_stats(&self) -> serde_json::Value {
        let mut tool_counts: HashMap<String, i64> = HashMap::new();
        let mut error_count = 0;
        let mut total_duration: f64 = 0.0;

        for event in &self.events {
            match event.event_type.as_str() {
                "tool_call" => {
                    let tool = event
                        .data
                        .get("tool")
                        .and_then(|v| v.as_str())
                        .unwrap_or("unknown");
                    *tool_counts.entry(tool.to_string()).or_insert(0) += 1;
                }
                "error" => {
                    error_count += 1;
                }
                _ => {}
            }
            if let Some(d) = event.duration_ms {
                total_duration += d;
            }
        }

        serde_json::json!({
            "session_id": self.current_session,
            "total_events": self.events.len(),
            "tool_calls": tool_counts,
            "errors": error_count,
            "total_duration_ms": total_duration,
        })
    }

    pub fn print_summary(&self) {
        let stats = self.get_stats();
        println!("\n=== Session Summary ===");
        println!("Session: {}", self.current_session);
        println!("Total Events: {}", stats["total_events"]);
        let total_calls: i64 = stats["tool_calls"]
            .as_object()
            .map(|m| m.values().map(|v| v.as_i64().unwrap_or(0)).sum())
            .unwrap_or(0);
        println!("Tool Calls: {}", total_calls);
        println!("Errors: {}", stats["errors"]);
        println!("Duration: {:.0}ms", stats["total_duration_ms"]);
        if let Some(tc) = stats["tool_calls"].as_object() {
            println!("\nTop Tools:");
            let mut sorted: Vec<(&String, i64)> = tc
                .iter()
                .filter_map(|(k, v)| v.as_i64().map(|i| (k, i)))
                .collect();
            sorted.sort_by(|a, b| b.1.cmp(&a.1));
            for (tool, count) in sorted.into_iter().take(5) {
                println!("  {}: {}", tool, count);
            }
        }
    }
}

/// Performance monitor for tracking operation timings.
pub struct PerformanceMonitor {
    measurements: HashMap<String, Vec<f64>>,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            measurements: HashMap::new(),
        }
    }

    pub fn measure(&self) -> f64 {
        time_now()
    }

    pub fn record(&mut self, operation: &str, duration_ms: f64) {
        self.measurements
            .entry(operation.to_string())
            .or_default()
            .push(duration_ms);
    }

    pub fn get_stats(&self, operation: &str) -> HashMap<String, f64> {
        let mut result = HashMap::new();
        if let Some(times) = self.measurements.get(operation) {
            if !times.is_empty() {
                let count = times.len() as f64;
                let avg: f64 = times.iter().sum::<f64>() / count;
                let min = times.iter().cloned().fold(f64::INFINITY, f64::min);
                let max = times.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                result.insert("count".to_string(), count);
                result.insert("avg".to_string(), avg);
                result.insert("min".to_string(), min);
                result.insert("max".to_string(), max);
            }
        }
        result
    }

    pub fn get_all_stats(&self) -> HashMap<String, HashMap<String, f64>> {
        self.measurements
            .iter()
            .map(|(op, _)| (op.clone(), self.get_stats(op)))
            .collect()
    }
}

fn time_now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs_f64()
}

static LOGGER: OnceLock<Mutex<Logger>> = OnceLock::new();
static PERF_MONITOR: OnceLock<Mutex<PerformanceMonitor>> = OnceLock::new();

pub fn logger() -> &'static Mutex<Logger> {
    LOGGER.get_or_init(|| Mutex::new(Logger::new(None)))
}

pub fn perf_monitor() -> &'static Mutex<PerformanceMonitor> {
    PERF_MONITOR.get_or_init(|| Mutex::new(PerformanceMonitor::new()))
}
