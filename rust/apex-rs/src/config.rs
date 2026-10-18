use std::env;

#[derive(Clone)]
pub struct Config {
    pub model: String,
    pub api_key: String,
    pub base_url: String,
    pub cwd: std::path::PathBuf,
    pub denied_tools: Vec<String>,
    pub auto_compact: bool,
    pub compact_threshold: usize,
}

impl Config {
    pub fn from_env() -> Self {
        let model = env::var("APEX_MODEL").unwrap_or_else(|_| "gpt-4o-mini".to_string());
        let api_key = env::var("APEX_API_KEY")
            .or_else(|_| env::var("OPENAI_API_KEY"))
            .unwrap_or_default();
        let base_url = env::var("APEX_BASE_URL")
            .unwrap_or_else(|_| "https://api.openai.com/v1".to_string());
        let cwd = env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
        let denied_tools = env::var("APEX_DENIED_TOOLS")
            .map(|v| v.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect())
            .unwrap_or_default();
        let auto_compact = env::var("APEX_AUTO_COMPACT").map(|v| v != "0" && v.to_lowercase() != "false").unwrap_or(true);
        let compact_threshold = env::var("APEX_COMPACT_THRESHOLD").ok().and_then(|v| v.parse().ok()).unwrap_or(20);
        Self { model, api_key, base_url, cwd, denied_tools, auto_compact, compact_threshold }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::sync::Mutex;

    static ENV_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn defaults() {
        let _g = ENV_LOCK.lock().unwrap();
        env::set_var("APEX_MODEL", "gpt-4o-mini");
        env::set_var("APEX_DENIED_TOOLS", "");
        env::set_var("APEX_AUTO_COMPACT", "true");
        env::set_var("APEX_COMPACT_THRESHOLD", "20");
        let c = Config::from_env();
        assert_eq!(c.model, "gpt-4o-mini");
        assert!(c.denied_tools.is_empty());
        assert!(c.auto_compact);
        assert_eq!(c.compact_threshold, 20);
        env::remove_var("APEX_MODEL");
        env::remove_var("APEX_DENIED_TOOLS");
        env::remove_var("APEX_AUTO_COMPACT");
        env::remove_var("APEX_COMPACT_THRESHOLD");
    }

    #[test]
    fn denied_tools_parsed() {
        let _g = ENV_LOCK.lock().unwrap();
        env::set_var("APEX_DENIED_TOOLS", "run_command, write_file");
        let c = Config::from_env();
        assert_eq!(c.denied_tools, vec!["run_command", "write_file"]);
        env::remove_var("APEX_DENIED_TOOLS");
    }
}