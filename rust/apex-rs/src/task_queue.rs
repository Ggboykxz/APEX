//! Python: `TaskQueue` + `get_task_queue()` (in `apex/extras.py`) backing
//! the `submit_task` / `list_tasks` / `get_task` tools.
//!
//! Python runs each task as an asyncio coroutine:
//! `asyncio.run(queue.add(name, run_command))` spawns `_run_task` on the
//! fresh loop, and the loop teardown cancels the coroutine, so a submitted
//! task stays `pending` forever in practice. The Rust port implements the
//! intent instead: each task runs on a background thread. A non-zero shell
//! exit is not an error (Python's `communicate()` does not raise either) -
//! the task completes with `stdout or stderr` as its result, and only a
//! spawn failure marks it `failed`.

use std::collections::HashMap;
use std::path::Path;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{LazyLock, Mutex, MutexGuard};
use std::time::{SystemTime, UNIX_EPOCH};

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// Python: the `Task` dataclass (id/name/status/result/error).
#[derive(Clone)]
pub struct Task {
    pub id: String,
    pub name: String,
    /// "pending" | "running" | "completed" | "failed"
    pub status: String,
    pub result: Option<String>,
    pub error: Option<String>,
}

struct Queue {
    tasks: HashMap<String, Task>,
    /// Insertion order - Python dicts preserve it, so `list_tasks`
    /// reports tasks in submission order.
    order: Vec<String>,
}

static QUEUE: LazyLock<Mutex<Queue>> = LazyLock::new(|| {
    Mutex::new(Queue {
        tasks: HashMap::new(),
        order: Vec::new(),
    })
});

fn lock() -> MutexGuard<'static, Queue> {
    match QUEUE.lock() {
        Ok(g) => g,
        Err(p) => p.into_inner(),
    }
}

/// Python: `str(uuid.uuid4())[:8]` - an 8-char hex id. The Rust port has
/// no uuid dependency; the id is a time/counter mix in the same shape.
fn new_task_id() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0);
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("{:08x}", (now ^ n) & 0xFFFF_FFFF)
}

/// Python: `TaskQueue.add` - register the task (status `pending`) and run
/// it in the background.
pub fn submit(name: &str, command: &str, cwd: &Path) -> String {
    let task_id = new_task_id();
    {
        let mut q = lock();
        q.tasks.insert(
            task_id.clone(),
            Task {
                id: task_id.clone(),
                name: name.to_string(),
                status: "pending".to_string(),
                result: None,
                error: None,
            },
        );
        q.order.push(task_id.clone());
    }
    let worker_id = task_id.clone();
    let command = command.to_string();
    let cwd = cwd.to_path_buf();
    std::thread::spawn(move || {
        // Python: `_run_task` sets "running" before executing.
        {
            let mut q = lock();
            if let Some(t) = q.tasks.get_mut(&worker_id) {
                t.status = "running".to_string();
            }
        }
        let outcome = run(&command, &cwd);
        let mut q = lock();
        if let Some(t) = q.tasks.get_mut(&worker_id) {
            match outcome {
                Ok(r) => {
                    t.result = Some(r);
                    t.status = "completed".to_string();
                }
                Err(e) => {
                    t.error = Some(e);
                    t.status = "failed".to_string();
                }
            }
        }
    });
    task_id
}

/// Python: the `run_command` coroutine - shell run with stdout/stderr
/// captured, result is `stdout or stderr`.
fn run(command: &str, cwd: &Path) -> Result<String, String> {
    let mut cmd = crate::tools::shell_command(command);
    cmd.current_dir(cwd);
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    let out = cmd.output().map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&out.stdout);
    if !stdout.is_empty() {
        Ok(stdout.into_owned())
    } else {
        Ok(String::from_utf8_lossy(&out.stderr).into_owned())
    }
}

/// Python: `TaskQueue.list()` - insertion order, `str(result)[:100]` when
/// a result is set.
pub fn list() -> Vec<(String, String, String, Option<String>)> {
    let q = lock();
    q.order
        .iter()
        .filter_map(|id| q.tasks.get(id))
        .map(|t| {
            (
                t.id.clone(),
                t.name.clone(),
                t.status.clone(),
                t.result.as_ref().map(|r| r.chars().take(100).collect()),
            )
        })
        .collect()
}

/// Python: `TaskQueue.get()`.
pub fn get(task_id: &str) -> Option<Task> {
    let q = lock();
    q.tasks.get(task_id).cloned()
}

/// Test hook: empty the queue (Python tests monkeypatch the executor
/// instead of isolating the global).
#[cfg(test)]
pub(crate) fn test_reset() {
    let mut q = lock();
    q.tasks.clear();
    q.order.clear();
}
