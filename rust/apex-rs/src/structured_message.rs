//! Structured message system — port of `apex/structured_message.py`.
//!
//! Messages are built from typed parts (text, file, tool_call, tool_result,
//! image, snapshot) instead of plain strings/JSON, matching OpenCode's parts
//! model.
//
//! This module is not yet wired into the dispatch gate / agent loop.
//! Allow dead code with a named exit criterion — TODO(v2.6): wire into tool
//! dispatch / agent message handling and remove this allow.
#![allow(dead_code)]

use std::collections::HashMap;
use std::time::SystemTime;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Type of a message part.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PartType {
    Text,
    File,
    ToolCall,
    ToolResult,
    Image,
    Snapshot,
}

impl PartType {
    pub fn as_str(&self) -> &'static str {
        match self {
            PartType::Text => "text",
            PartType::File => "file",
            PartType::ToolCall => "tool_call",
            PartType::ToolResult => "tool_result",
            PartType::Image => "image",
            PartType::Snapshot => "snapshot",
        }
    }
}

/// A single typed part of a message.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MessagePart {
    pub part_type: PartType,
    pub content: serde_json::Value,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl MessagePart {
    pub fn new(part_type: PartType, content: serde_json::Value) -> Self {
        Self {
            part_type,
            content,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(
        part_type: PartType,
        content: serde_json::Value,
        metadata: HashMap<String, serde_json::Value>,
    ) -> Self {
        Self {
            part_type,
            content,
            metadata,
        }
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "type": self.part_type.as_str(),
            "content": self.content,
            "metadata": self.metadata,
        })
    }
}

/// Token usage statistics.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct TokenUsage {
    pub prompt_tokens: usize,
    pub completion_tokens: usize,
    pub total_tokens: usize,
}

impl TokenUsage {
    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        })
    }
}

/// A structured message built from typed parts.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Message {
    pub id: String,
    pub role: String,
    pub parts: Vec<MessagePart>,
    pub token_usage: Option<TokenUsage>,
    pub cost_usd: Option<f64>,
    pub timestamp: DateTime<Utc>,
}

impl Message {
    pub fn new(id: impl Into<String>, role: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            role: role.into(),
            parts: Vec::new(),
            token_usage: None,
            cost_usd: None,
            timestamp: Utc::now(),
        }
    }

    pub fn add_text(&mut self, text: impl Into<String>) {
        self.parts.push(MessagePart::new(
            PartType::Text,
            serde_json::Value::String(text.into()),
        ));
    }

    pub fn add_file(&mut self, path: impl Into<String>, content: impl Into<String>) {
        let path = path.into();
        let mut metadata = HashMap::new();
        metadata.insert(
            "name".to_string(),
            serde_json::Value::String(path.rsplit('/').next().unwrap_or(&path).to_string()),
        );
        self.parts.push(MessagePart::with_metadata(
            PartType::File,
            serde_json::json!({ "path": path, "content": content.into() }),
            metadata,
        ));
    }

    pub fn add_tool_call(&mut self, tool_name: impl Into<String>, arguments: serde_json::Value) {
        self.parts.push(MessagePart::new(
            PartType::ToolCall,
            serde_json::json!({ "name": tool_name.into(), "arguments": arguments }),
        ));
    }

    pub fn add_tool_result(&mut self, tool_name: impl Into<String>, result: serde_json::Value) {
        self.parts.push(MessagePart::new(
            PartType::ToolResult,
            serde_json::json!({ "name": tool_name.into(), "result": result }),
        ));
    }

    pub fn add_image(&mut self, path: impl Into<String>, base64_data: impl Into<String>) {
        self.parts.push(MessagePart::new(
            PartType::Image,
            serde_json::json!({ "path": path.into(), "data": base64_data.into() }),
        ));
    }

    pub fn add_snapshot(&mut self, snapshot_id: impl Into<String>) {
        self.parts.push(MessagePart::new(
            PartType::Snapshot,
            serde_json::Value::String(snapshot_id.into()),
        ));
    }

    /// Concatenate all TEXT parts into a single string.
    pub fn get_text(&self) -> String {
        self.parts
            .iter()
            .filter(|p| p.part_type == PartType::Text)
            .filter_map(|p| p.content.as_str())
            .collect::<Vec<_>>()
            .join(" ")
    }

    /// Return all FILE part contents.
    pub fn get_files(&self) -> Vec<serde_json::Value> {
        self.parts
            .iter()
            .filter(|p| p.part_type == PartType::File)
            .map(|p| p.content.clone())
            .collect()
    }

    /// Return all TOOL_CALL part contents.
    pub fn get_tool_calls(&self) -> Vec<serde_json::Value> {
        self.parts
            .iter()
            .filter(|p| p.part_type == PartType::ToolCall)
            .map(|p| p.content.clone())
            .collect()
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "role": self.role,
            "parts": self.parts.iter().map(|p| p.to_dict()).collect::<Vec<_>>(),
            "token_usage": self.token_usage.as_ref().map(|u| u.to_dict()),
            "cost_usd": self.cost_usd,
            "timestamp": self.timestamp.to_rfc3339(),
        })
    }

    pub fn from_dict(data: &serde_json::Value) -> serde_json::Result<Self> {
        let id = data["id"].as_str().unwrap_or("").to_string();
        let role = data["role"].as_str().unwrap_or("").to_string();

        let parts = data["parts"]
            .as_array()
            .unwrap_or(&Vec::new())
            .iter()
            .filter_map(|p| {
                let part_type = match p["type"].as_str() {
                    Some("text") => PartType::Text,
                    Some("file") => PartType::File,
                    Some("tool_call") => PartType::ToolCall,
                    Some("tool_result") => PartType::ToolResult,
                    Some("image") => PartType::Image,
                    Some("snapshot") => PartType::Snapshot,
                    _ => return None,
                };
                Some(MessagePart {
                    part_type,
                    content: p.get("content")?.clone(),
                    metadata: p
                        .get("metadata")
                        .and_then(|m| m.as_object())
                        .map(|m| m.iter().map(|(k, v)| (k.clone(), v.clone())).collect())
                        .unwrap_or_default(),
                })
            })
            .collect();

        let token_usage = data.get("token_usage").map(|tu| TokenUsage {
            prompt_tokens: tu["prompt_tokens"].as_u64().unwrap_or(0) as usize,
            completion_tokens: tu["completion_tokens"].as_u64().unwrap_or(0) as usize,
            total_tokens: tu["total_tokens"].as_u64().unwrap_or(0) as usize,
        });

        let cost_usd = data.get("cost_usd").and_then(|v| v.as_f64());
        let timestamp = data
            .get("timestamp")
            .and_then(|v| v.as_str())
            .and_then(|s| DateTime::parse_from_rfc3339(s).ok())
            .map(|dt| dt.with_timezone(&Utc))
            .unwrap_or_else(Utc::now);

        Ok(Message {
            id,
            role,
            parts,
            token_usage,
            cost_usd,
            timestamp,
        })
    }
}

/// Factory function to create a message with an optional initial text part.
pub fn create_message(role: impl Into<String>, content: impl Into<String>) -> Message {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let role_str: String = role.into();
    let mut hasher = DefaultHasher::new();
    SystemTime::now().hash(&mut hasher);
    role_str.hash(&mut hasher);
    let msg_id = format!("{:x}", hasher.finish());
    let msg_id = &msg_id[..msg_id.len().min(16)];

    let mut msg = Message::new(msg_id, role_str);
    let content = content.into();
    if !content.is_empty() {
        msg.add_text(content);
    }
    msg
}

/// Serialize messages to a list of dicts.
pub fn serialize_messages(messages: &[Message]) -> Vec<serde_json::Value> {
    messages.iter().map(|m| m.to_dict()).collect()
}

/// Deserialize messages from a list of dicts.
pub fn deserialize_messages(data: &[serde_json::Value]) -> serde_json::Result<Vec<Message>> {
    data.iter().map(Message::from_dict).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn create_message_adds_text_part() {
        let msg = create_message("user", "hello world");
        assert_eq!(msg.role, "user");
        assert_eq!(msg.parts.len(), 1);
        assert_eq!(msg.parts[0].part_type, PartType::Text);
        assert_eq!(msg.get_text(), "hello world");
    }

    #[test]
    fn add_file_tool_call_and_result() {
        let mut msg = Message::new("m1", "assistant");
        msg.add_file("src/main.rs", "fn main() {}");
        msg.add_tool_call("read_file", serde_json::json!({ "path": "src/main.rs" }));
        msg.add_tool_result(
            "read_file",
            serde_json::json!({ "content": "fn main() {}" }),
        );

        assert_eq!(msg.parts.len(), 3);
        assert_eq!(msg.parts[0].part_type, PartType::File);
        assert_eq!(msg.parts[1].part_type, PartType::ToolCall);
        assert_eq!(msg.parts[2].part_type, PartType::ToolResult);
        assert_eq!(msg.get_text(), "");
        assert_eq!(msg.get_files().len(), 1);
        assert_eq!(msg.get_tool_calls().len(), 1);
    }

    #[test]
    fn add_image_and_snapshot() {
        let mut msg = Message::new("m2", "user");
        msg.add_image("shot.png", "base64data");
        msg.add_snapshot("snap-abc123");

        assert_eq!(msg.parts.len(), 2);
        assert_eq!(msg.parts[0].part_type, PartType::Image);
        assert_eq!(msg.parts[1].part_type, PartType::Snapshot);
    }

    #[test]
    fn get_text_concatenates_text_parts() {
        let mut msg = Message::new("m3", "user");
        msg.add_text("hello");
        msg.add_file("a.txt", "");
        msg.add_text("world");
        assert_eq!(msg.get_text(), "hello world");
    }

    #[test]
    fn to_dict_roundtrip() {
        let mut msg = create_message("user", "hi");
        msg.add_tool_call("bash", serde_json::json!({ "cmd": "ls" }));
        msg.token_usage = Some(TokenUsage {
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
        });
        msg.cost_usd = Some(0.001);

        let dict = msg.to_dict();
        let restored = Message::from_dict(&dict).unwrap();
        assert_eq!(restored.id, msg.id);
        assert_eq!(restored.role, msg.role);
        assert_eq!(restored.parts.len(), msg.parts.len());
        assert_eq!(restored.get_text(), "hi");
        assert_eq!(restored.get_tool_calls().len(), 1);
        assert_eq!(restored.token_usage.unwrap().total_tokens, 15);
        assert_eq!(restored.cost_usd, Some(0.001));
    }

    #[test]
    fn serialize_and_deserialize_messages() {
        let msgs = vec![
            create_message("user", "first"),
            create_message("assistant", "second"),
        ];
        let serialized = serialize_messages(&msgs);
        assert_eq!(serialized.len(), 2);

        let restored = deserialize_messages(&serialized).unwrap();
        assert_eq!(restored.len(), 2);
        assert_eq!(restored[0].get_text(), "first");
        assert_eq!(restored[1].get_text(), "second");
    }

    #[test]
    fn part_type_as_str() {
        assert_eq!(PartType::Text.as_str(), "text");
        assert_eq!(PartType::File.as_str(), "file");
        assert_eq!(PartType::ToolCall.as_str(), "tool_call");
        assert_eq!(PartType::ToolResult.as_str(), "tool_result");
        assert_eq!(PartType::Image.as_str(), "image");
        assert_eq!(PartType::Snapshot.as_str(), "snapshot");
    }

    #[test]
    fn message_part_metadata() {
        let mut metadata = HashMap::new();
        metadata.insert(
            "name".to_string(),
            serde_json::Value::String("x.rs".to_string()),
        );
        let part = MessagePart::with_metadata(
            PartType::File,
            serde_json::json!({ "path": "x.rs", "content": "" }),
            metadata,
        );
        let dict = part.to_dict();
        assert_eq!(dict["type"], "file");
        assert_eq!(dict["metadata"]["name"], "x.rs");
    }
}
