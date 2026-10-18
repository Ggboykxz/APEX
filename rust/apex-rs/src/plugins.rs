use std::fs;
use std::path::PathBuf;

pub struct PluginInfo {
    pub name: String,
    pub path: PathBuf,
}

pub fn discover_plugins() -> Vec<PluginInfo> {
    let base = dirs::home_dir().unwrap_or_default().join(".apex").join("plugins");
    let mut out = Vec::new();
    if let Ok(rd) = fs::read_dir(&base) {
        for e in rd.flatten() {
            let p = e.path();
            if p.extension().and_then(|x| x.to_str()) == Some("toml") || p.is_dir() {
                out.push(PluginInfo {
                    name: e.file_name().to_string_lossy().to_string(),
                    path: p,
                });
            }
        }
    }
    out
}

pub fn plugin_count() -> usize {
    discover_plugins().len()
}