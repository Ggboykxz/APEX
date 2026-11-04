//! i18n — Internationalization support ported from `apex/i18n.py`.
//!
//! Provides multi-language string lookup with auto-detection from environment.

#![allow(dead_code)]
#![allow(clippy::all)]

use std::collections::HashMap;
use std::sync::OnceLock;

/// Detected locale from environment variables.
pub fn detect_locale() -> String {
    let lang = std::env::var("LANG").unwrap_or_default();
    if lang.is_empty() {
        return "en".to_string();
    }

    let lang = lang.split('.').next().unwrap_or("").to_lowercase();

    if lang.contains("ja") {
        return "ja".to_string();
    }
    if lang.contains("zh") {
        return "zh-Hans".to_string();
    }
    if lang.contains("pt") {
        return "pt-BR".to_string();
    }

    "en".to_string()
}

/// Available locales.
pub const LOCALES: &[&str] = &["en", "ja", "zh-Hans", "pt-BR"];

/// Localized strings, mirrored from Python's `LOCALES`.
pub const STRINGS: &[(&str, &[(&str, &str); 13])] = &[
    (
        "en",
        &[
            ("app_name", "APEX"),
            ("welcome", "Welcome to APEX - The last coding agent you'll ever need"),
            ("prompt", ">>> "),
            ("thinking", "Thinking..."),
            ("working", "Working..."),
            ("done", "Done!"),
            ("error", "Error"),
            ("success", "Success"),
            ("help_title", "Available Commands"),
            ("model", "Model"),
            ("agent", "Agent"),
            ("cwd", "Working Directory"),
            ("clear", "Clear history"),
            ("sessions", "Sessions"),
        ],
    ),
    (
        "ja",
        &[
            ("app_name", "APEX"),
            ("welcome", "APEXへようこそ - 最後のコーディングエージェント"),
            ("prompt", ">>> "),
            ("thinking", "思考中..."),
            ("working", "実行中..."),
            ("done", "完了!"),
            ("error", "エラー"),
            ("success", "成功"),
            ("help_title", "利用可能なコマンド"),
            ("model", "モデル"),
            ("agent", "エージェント"),
            ("cwd", "作業ディレクトリ"),
            ("clear", "履歴をクリア"),
            ("sessions", "セッション"),
        ],
    ),
    (
        "zh-Hans",
        &[
            ("app_name", "APEX"),
            ("welcome", "欢迎使用APEX - 最后的编码助手"),
            ("prompt", ">>> "),
            ("thinking", "思考中..."),
            ("working", "工作中..."),
            ("done", "完成!"),
            ("error", "错误"),
            ("success", "成功"),
            ("help_title", "可用命令"),
            ("model", "模型"),
            ("agent", "代理"),
            ("cwd", "工作目录"),
            ("clear", "清除历史"),
            ("sessions", "会话"),
        ],
    ),
    (
        "pt-BR",
        &[
            ("app_name", "APEX"),
            ("welcome", "Bem-vindo ao APEX - O último agente de codificação que você precisará"),
            ("prompt", ">>> "),
            ("thinking", "Pensando..."),
            ("working", "Trabalhando..."),
            ("done", "Concluído!"),
            ("error", "Erro"),
            ("success", "Sucesso"),
            ("help_title", "Comandos Disponíveis"),
            ("model", "Modelo"),
            ("agent", "Agente"),
            ("cwd", "Diretório de Trabalho"),
            ("clear", "Limpar histórico"),
            ("sessions", "Sessões"),
        ],
    ),
];

/// Look up a translated string for a given locale and key.
fn lookup(locale: &str, key: &str) -> Option<&'static str> {
    let entry = LOCALES.iter().find(|(l, _)| *l == locale)?;
    entry.1.iter().find(|(k, _)| *k == key).map(|(_, v)| *v)
}

/// `I18n` — Internationalization support for APEX.
pub struct I18n {
    locale: String,
}

impl I18n {
    pub fn new(locale: &str) -> Self {
        let locale = if locale == "auto" {
            detect_locale()
        } else if LOCALES.contains(&locale) {
            locale.to_string()
        } else {
            "en".to_string()
        };
        Self { locale }
    }

    /// Get a translated string by key.
    pub fn get(&self, key: &str, default: &str) -> String {
        lookup(&self.locale, key).unwrap_or(default).to_string()
    }

    /// Get a translated string using bracket notation (returns key if missing).
    pub fn get_bracket(&self, key: &str) -> String {
        lookup(&self.locale, key).unwrap_or(key).to_string()
    }

    /// Check if a key exists in the current locale.
    pub fn contains(&self, key: &str) -> bool {
        lookup(&self.locale, key).is_some()
    }

    /// List available locales.
    pub fn available_locales(&self) -> Vec<&'static str> {
        LOCALES.to_vec()
    }

    /// Get the current locale.
    pub fn locale(&self) -> &str {
        &self.locale
    }
}

static I18N_INSTANCE: OnceLock<std::sync::Mutex<I18n>> = OnceLock::new();

/// Get the global i18n instance.
pub fn get_i18n(locale: &str) -> &'static std::sync::Mutex<I18n> {
    I18N_INSTANCE.get_or_init(|| std::sync::Mutex::new(I18n::new(locale)))
}

/// Set the global locale.
pub fn set_locale(locale: &str) {
    if let Some(mutex) = I18N_INSTANCE.get() {
        *mutex.lock().unwrap() = I18n::new(locale);
    } else {
        I18N_INSTANCE.set(std::sync::Mutex::new(I18n::new(locale))).ok();
    }
}