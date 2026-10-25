use std::sync::Mutex;

type HookFn = Box<dyn Fn(&str, &serde_json::Value) + Send + Sync>;

static HOOKS: Mutex<Vec<HookFn>> = Mutex::new(Vec::new());

// No production registration site yet: hooks are triggered by tool dispatch.
// TODO(v2.6): load hook definitions from config and call this at startup.
#[allow(dead_code)]
pub fn register_hook(f: HookFn) {
    if let Ok(mut h) = HOOKS.lock() {
        h.push(f);
    }
}

pub fn trigger_hooks(tool_name: &str, args: &serde_json::Value) {
    if let Ok(h) = HOOKS.lock() {
        for f in h.iter() {
            f(tool_name, args);
        }
    }
}

// Diagnostics-only helper; the HTTP server does not expose hook state yet.
// TODO(v2.6): surface registered hook count in `/api/v1/config`.
#[allow(dead_code)]
pub fn hook_count() -> usize {
    HOOKS.lock().map(|h| h.len()).unwrap_or(0)
}
