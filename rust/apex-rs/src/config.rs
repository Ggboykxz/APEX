use std::env;

#[derive(Clone)]
pub struct Config {
    pub model: String,
    pub api_key: String,
    pub base_url: String,
    pub cwd: std::path::PathBuf,
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
        Self { model, api_key, base_url, cwd }
    }
}