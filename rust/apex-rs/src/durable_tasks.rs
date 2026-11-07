//! Port of `apex/task_queue.py` — durable background tasks that survive
//! restarts.
//!
//! The queue persists to `tasks.json` under `~/.apex/tasks` (Python's
//! default `queue_dir`); every mutation rewrites the file, and a fresh
//! instance rehydrates from it.
//!
//! Python's only production consumer is the TUI REPL `/tasks` command
//! (`main.py`), which the Rust port excludes (the TUI is the TypeScript
//! frontend), so the Rust HTTP routes in `server.rs` (`/api/v1/tasks/*`) are
//! the production surface — like the snapshot manager, the port is wired
//! further than Python.
//!
//! Divergences:
//! - `created_at` is written in local time with 6 fractional digits, like
//!   Python's naive local `isoformat()`; lexicographic order is preserved,
//!   which is all `list_tasks` relies on.
//! - `get` returns a snapshot copy (Python returns a live reference; the
//!   queue is the only writer in both ports).
//! - `start_worker`/`stop_workers` are dead in Python too (production never
//!   starts a worker); they are ported for API parity and exercised by the
//!   unit tests only.
//! - `stop_workers` joins each thread instead of `join(timeout=1)`: the
//!   worker loop re-checks the stop flag at most one second per iteration,
//!   so the join returns within that window unless a user handler hangs.
//! - A corrupt or inconsistent `tasks.json` resets the queue to empty
//!   (Python's `except (JSONDecodeError, TypeError)` does the same; Python
//!   additionally crashes on an invalid status string, which the port treats
//!   as corrupt).
//! - `enqueue` keeps Python's unused `priority` parameter (accepted, never
//!   ordered by); the workers process the newest pending task first
//!   (`created_at` descending), exactly like Python's `list_tasks(PENDING, 1)`.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::thread::JoinHandle;

/// Python's `TaskStatus` enum (lowercase string values).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum TaskStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
}

impl TaskStatus {
    /// The lowercase wire value.
    ///
    /// Dead in the Rust production path: serde's `rename_all = "lowercase"`
    /// does the same job for persistence and HTTP (Python reads
    /// `status.value` in `main.py` and `_save_tasks`, both excluded/covered).
    /// TODO(v2.6): expose status strings in a CLI view.
    #[allow(dead_code)]
    pub fn as_str(self) -> &'static str {
        match self {
            TaskStatus::Pending => "pending",
            TaskStatus::Running => "running",
            TaskStatus::Completed => "completed",
            TaskStatus::Failed => "failed",
            TaskStatus::Cancelled => "cancelled",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "pending" => Some(TaskStatus::Pending),
            "running" => Some(TaskStatus::Running),
            "completed" => Some(TaskStatus::Completed),
            "failed" => Some(TaskStatus::Failed),
            "cancelled" => Some(TaskStatus::Cancelled),
            _ => None,
        }
    }
}

/// Python's `Task` dataclass (10 fields, same JSON shape on disk).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub name: String,
    pub description: String,
    pub payload: Value,
    pub status: TaskStatus,
    pub created_at: String,
    pub started_at: Option<String>,
    pub completed_at: Option<String>,
    pub result: Option<Value>,
    pub error: Option<String>,
}

/// Durable task queue with persistence (Python's `TaskQueue`).
pub struct TaskQueue {
    pub queue_dir: PathBuf,
    tasks_file: PathBuf,
    tasks: Mutex<BTreeMap<String, Task>>,
    running: AtomicBool,
    workers: Mutex<Vec<JoinHandle<()>>>,
}

impl TaskQueue {
    /// Python's `__init__` — defaults to `~/.apex/tasks` and rehydrates.
    pub fn new(queue_dir: Option<PathBuf>) -> Self {
        let queue_dir = queue_dir.unwrap_or_else(|| {
            crate::config::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join(".apex")
                .join("tasks")
        });
        let queue = Self {
            queue_dir: queue_dir.clone(),
            tasks_file: queue_dir.join("tasks.json"),
            tasks: Mutex::new(BTreeMap::new()),
            running: AtomicBool::new(false),
            workers: Mutex::new(Vec::new()),
        };
        let _ = std::fs::create_dir_all(&queue.queue_dir);
        queue.load_tasks();
        queue
    }

    /// Python's `_load_tasks` — a corrupt file resets the queue to empty.
    fn load_tasks(&self) {
        if !self.tasks_file.exists() {
            return;
        }
        if let Some(tasks) = std::fs::read_to_string(&self.tasks_file)
            .ok()
            .and_then(|text| serde_json::from_str::<BTreeMap<String, Task>>(&text).ok())
        {
            *self.tasks.lock().unwrap() = tasks;
        }
    }

    /// Python's `_save_tasks` — `{task_id: {…}}` with 2-space indentation.
    fn save_tasks(&self) {
        let tasks = self.tasks.lock().unwrap().clone();
        if let Ok(text) = serde_json::to_string_pretty(&tasks) {
            let _ = std::fs::write(&self.tasks_file, text);
        }
    }

    /// Python's `_generate_id` — `task_{YYYYmmddHHMMSS}_{len+1}` (local time).
    fn generate_id(&self) -> String {
        let timestamp = chrono::Local::now().format("%Y%m%d%H%M%S").to_string();
        let count = self.tasks.lock().unwrap().len() + 1;
        format!("task_{timestamp}_{count}")
    }

    fn now_iso() -> String {
        chrono::Local::now()
            .format("%Y-%m-%dT%H:%M:%S%.6f")
            .to_string()
    }

    /// Python's `enqueue` (`priority` is accepted but never used, like there).
    pub fn enqueue(&self, name: &str, description: &str, payload: Value, _priority: i64) -> String {
        let task_id = self.generate_id();
        let task = Task {
            id: task_id.clone(),
            name: name.to_string(),
            description: description.to_string(),
            payload,
            status: TaskStatus::Pending,
            created_at: Self::now_iso(),
            started_at: None,
            completed_at: None,
            result: None,
            error: None,
        };
        self.tasks.lock().unwrap().insert(task_id.clone(), task);
        self.save_tasks();
        task_id
    }

    /// Python's `get` (returns a snapshot copy; see the module docs).
    pub fn get(&self, task_id: &str) -> Option<Task> {
        self.tasks.lock().unwrap().get(task_id).cloned()
    }

    /// Python's `list_tasks(status, limit=100)` — newest first.
    pub fn list_tasks(&self, status: Option<TaskStatus>, limit: usize) -> Vec<Task> {
        let tasks = self.tasks.lock().unwrap();
        let mut listed: Vec<Task> = tasks.values().cloned().collect();
        if let Some(status) = status {
            listed.retain(|t| t.status == status);
        }
        listed.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        listed.truncate(limit);
        listed
    }

    /// Python's `start_worker` — one polling thread per worker, 1 s period.
    ///
    /// Requires an `Arc<Self>` so the worker threads share the same queue
    /// state (Python's threads share `self`).
    ///
    /// Dead in Python too: production never starts a worker.
    /// TODO(v2.6): wire worker startup behind a config flag or route.
    #[allow(dead_code)]
    pub fn start_worker<F>(self: &Arc<Self>, handler: F, max_workers: usize)
    where
        F: Fn(&Task) -> Result<Value, String> + Send + Sync + 'static,
    {
        self.running.store(true, Ordering::SeqCst);
        let handler = Arc::new(handler);
        for _ in 0..max_workers {
            let queue = self.clone();
            let handler = Arc::clone(&handler);
            let handle = std::thread::spawn(move || {
                while queue.running.load(Ordering::SeqCst) {
                    let pending = queue.list_tasks(Some(TaskStatus::Pending), 1);
                    if pending.is_empty() {
                        std::thread::sleep(std::time::Duration::from_secs(1));
                        continue;
                    }
                    let task = pending[0].clone();
                    {
                        let mut tasks = queue.tasks.lock().unwrap();
                        if let Some(t) = tasks.get_mut(&task.id) {
                            t.status = TaskStatus::Running;
                            t.started_at = Some(TaskQueue::now_iso());
                        }
                    }
                    queue.save_tasks();
                    let outcome = (handler)(&task);
                    {
                        let mut tasks = queue.tasks.lock().unwrap();
                        if let Some(t) = tasks.get_mut(&task.id) {
                            match outcome {
                                Ok(result) => {
                                    t.status = TaskStatus::Completed;
                                    t.result = Some(result);
                                }
                                Err(error) => {
                                    t.status = TaskStatus::Failed;
                                    t.error = Some(error);
                                }
                            }
                            t.completed_at = Some(TaskQueue::now_iso());
                        }
                    }
                    queue.save_tasks();
                }
            });
            self.workers.lock().unwrap().push(handle);
        }
    }

    /// Python's `stop_workers`.
    ///
    /// Dead in Python too: production never starts a worker.
    /// TODO(v2.6): wire worker startup behind a config flag or route.
    #[allow(dead_code)]
    pub fn stop_workers(&self) {
        self.running.store(false, Ordering::SeqCst);
        let handles = std::mem::take(&mut *self.workers.lock().unwrap());
        for handle in handles {
            let _ = handle.join();
        }
    }

    /// Python's `cancel` — PENDING tasks only.
    pub fn cancel(&self, task_id: &str) -> bool {
        let mut tasks = self.tasks.lock().unwrap();
        let Some(task) = tasks.get_mut(task_id) else {
            return false;
        };
        if task.status != TaskStatus::Pending {
            return false;
        }
        task.status = TaskStatus::Cancelled;
        drop(tasks);
        self.save_tasks();
        true
    }

    /// Python's `clear_completed` — removes COMPLETED tasks, returns the count.
    pub fn clear_completed(&self) -> usize {
        let mut tasks = self.tasks.lock().unwrap();
        let completed: Vec<String> = tasks
            .iter()
            .filter(|(_, t)| t.status == TaskStatus::Completed)
            .map(|(id, _)| id.clone())
            .collect();
        for id in &completed {
            tasks.remove(id);
        }
        drop(tasks);
        self.save_tasks();
        completed.len()
    }

    /// Python's `delete_task` — removes any task completely.
    pub fn delete_task(&self, task_id: &str) -> bool {
        let mut tasks = self.tasks.lock().unwrap();
        if tasks.remove(task_id).is_some() {
            drop(tasks);
            self.save_tasks();
            true
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    fn temp_queue() -> (tempfile::TempDir, Arc<TaskQueue>) {
        let dir = tempfile::tempdir().unwrap();
        let queue_dir = dir.path().join("tasks");
        (dir, Arc::new(TaskQueue::new(Some(queue_dir))))
    }

    fn wait_for_status(queue: &TaskQueue, task_id: &str, expected: TaskStatus) -> bool {
        for _ in 0..50 {
            if let Some(task) = queue.get(task_id) {
                if task.status == expected {
                    return true;
                }
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        false
    }

    #[test]
    fn task_status_values() {
        assert_eq!(TaskStatus::Pending.as_str(), "pending");
        assert_eq!(TaskStatus::Running.as_str(), "running");
        assert_eq!(TaskStatus::Completed.as_str(), "completed");
        assert_eq!(TaskStatus::Failed.as_str(), "failed");
        assert_eq!(TaskStatus::Cancelled.as_str(), "cancelled");
        assert_eq!(TaskStatus::parse("pending"), Some(TaskStatus::Pending));
        assert_eq!(TaskStatus::parse("completed"), Some(TaskStatus::Completed));
        assert_eq!(TaskStatus::parse("bogus"), None);
    }

    #[test]
    fn task_creation() {
        let task = Task {
            id: "task_1".to_string(),
            name: "test".to_string(),
            description: "desc".to_string(),
            payload: serde_json::json!({"key": "val"}),
            status: TaskStatus::Pending,
            created_at: "2024-01-01".to_string(),
            started_at: None,
            completed_at: None,
            result: None,
            error: None,
        };
        assert_eq!(task.id, "task_1");
        assert_eq!(task.name, "test");
        assert_eq!(task.status, TaskStatus::Pending);
        assert_eq!(task.payload, serde_json::json!({"key": "val"}));
        assert!(task.result.is_none());
        assert!(task.error.is_none());
    }

    #[test]
    fn queue_init_creates_dir() {
        let (dir, queue) = temp_queue();
        assert_eq!(queue.queue_dir, dir.path().join("tasks"));
        assert!(queue.queue_dir.exists());
        assert!(queue.list_tasks(None, 100).is_empty());
        assert!(!queue.running.load(Ordering::SeqCst));
    }

    #[test]
    fn enqueue_returns_pending_id() {
        let (_dir, queue) = temp_queue();
        let task_id = queue.enqueue(
            "test_task",
            "A test",
            serde_json::json!({"data": "value"}),
            0,
        );
        assert!(task_id.starts_with("task_"));
        let task = queue.get(&task_id).unwrap();
        assert_eq!(task.status, TaskStatus::Pending);
        assert_eq!(task.name, "test_task");
        // Python: priority is accepted but never used.
        let _ = queue.enqueue("test", "desc", serde_json::json!({}), 5);
        assert!(queue.get("nonexistent").is_none());
    }

    #[test]
    fn list_tasks_filter_and_limit() {
        let (_dir, queue) = temp_queue();
        for i in 0..5 {
            queue.enqueue(
                &format!("task{i}"),
                &format!("Task {i}"),
                serde_json::json!({}),
                0,
            );
        }
        assert_eq!(queue.list_tasks(None, 100).len(), 5);
        assert_eq!(queue.list_tasks(None, 3).len(), 3);
        // Newest first: the last enqueued task sorts first.
        assert_eq!(queue.list_tasks(None, 100)[0].name, "task4");
        let id0 = queue
            .list_tasks(None, 100)
            .into_iter()
            .find(|t| t.name == "task0")
            .unwrap()
            .id;
        assert!(queue.cancel(&id0));
        assert_eq!(queue.list_tasks(Some(TaskStatus::Cancelled), 100).len(), 1);
    }

    #[test]
    fn cancel_rules() {
        let (_dir, queue) = temp_queue();
        let task_id = queue.enqueue("cancel_me", "desc", serde_json::json!({}), 0);
        assert!(queue.cancel(&task_id));
        assert_eq!(queue.get(&task_id).unwrap().status, TaskStatus::Cancelled);
        // Not pending anymore.
        assert!(!queue.cancel(&task_id));
        assert!(!queue.cancel("nonexistent"));
    }

    #[test]
    fn clear_completed_and_delete() {
        let (_dir, queue) = temp_queue();
        assert_eq!(queue.clear_completed(), 0);
        let id1 = queue.enqueue("done", "desc", serde_json::json!({}), 0);
        let id2 = queue.enqueue("pending", "desc", serde_json::json!({}), 0);
        assert!(queue.cancel(&id1));
        assert_eq!(queue.clear_completed(), 0); // cancelled is not completed
        assert!(queue.delete_task(&id1));
        assert!(queue.get(&id1).is_none());
        assert!(queue.get(&id2).is_some());
        assert!(!queue.delete_task("nonexistent"));
    }

    #[test]
    fn persistence_across_instances() {
        let dir = tempfile::tempdir().unwrap();
        let queue_dir = dir.path().join("tasks");
        let q1 = TaskQueue::new(Some(queue_dir.clone()));
        q1.enqueue("persist_test", "desc", serde_json::json!({"key": "val"}), 0);
        drop(q1);
        let q2 = TaskQueue::new(Some(queue_dir));
        let tasks = q2.list_tasks(None, 100);
        assert_eq!(tasks.len(), 1);
        assert_eq!(tasks[0].name, "persist_test");
        assert_eq!(tasks[0].status, TaskStatus::Pending);
        assert_eq!(tasks[0].payload, serde_json::json!({"key": "val"}));
    }

    #[test]
    fn save_tasks_file_shape() {
        let (dir, queue) = temp_queue();
        let task_id = queue.enqueue("save_test", "desc", serde_json::json!({}), 0);
        let tasks_file = dir.path().join("tasks").join("tasks.json");
        let data: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(tasks_file).unwrap()).unwrap();
        let task = &data[&task_id];
        assert_eq!(task["status"], "pending");
        for field in [
            "id",
            "name",
            "description",
            "payload",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "result",
            "error",
        ] {
            assert!(task.get(field).is_some(), "missing {field}");
        }
    }

    #[test]
    fn corrupt_file_resets_to_empty() {
        let dir = tempfile::tempdir().unwrap();
        let queue_dir = dir.path().join("tasks");
        std::fs::create_dir_all(&queue_dir).unwrap();
        std::fs::write(queue_dir.join("tasks.json"), "not valid json{{{").unwrap();
        let queue = TaskQueue::new(Some(queue_dir));
        assert!(queue.list_tasks(None, 100).is_empty());
    }

    #[test]
    fn generate_id_shape() {
        let (_dir, queue) = temp_queue();
        let id = queue.generate_id();
        assert!(id.starts_with("task_"));
        assert!(id.len() > 5, "id must be task_<14 digits>_<n>, got: {id}");
        let rest = id.strip_prefix("task_").unwrap();
        assert_eq!(rest.split('_').next().unwrap().len(), 14);
    }

    #[test]
    fn default_queue_dir_under_home() {
        let queue = TaskQueue::new(None);
        let name: Vec<String> = queue
            .queue_dir
            .components()
            .map(|c| c.as_os_str().to_string_lossy().to_string())
            .collect();
        assert!(
            name.ends_with(&[String::from(".apex"), String::from("tasks")]),
            "got: {:?}",
            queue.queue_dir
        );
    }

    #[test]
    fn worker_start_stop_flags() {
        let (_dir, queue) = temp_queue();
        queue.start_worker(|_| Ok(serde_json::json!({"processed": true})), 1);
        assert!(queue.running.load(Ordering::SeqCst));
        queue.stop_workers();
        assert!(!queue.running.load(Ordering::SeqCst));
    }

    #[test]
    fn worker_completes_and_clears() {
        let (_dir, queue) = temp_queue();
        let task_id = queue.enqueue("process_me", "desc", serde_json::json!({}), 0);
        queue.start_worker(|_| Ok(serde_json::json!({"result": "done"})), 1);
        assert!(
            wait_for_status(&queue, &task_id, TaskStatus::Completed),
            "worker did not complete the task"
        );
        queue.stop_workers();
        let task = queue.get(&task_id).unwrap();
        assert_eq!(task.result, Some(serde_json::json!({"result": "done"})));
        assert!(task.started_at.is_some());
        assert!(task.completed_at.is_some());
        assert_eq!(queue.clear_completed(), 1);
        assert!(queue.get(&task_id).is_none());
    }

    #[test]
    fn worker_records_handler_errors() {
        let (_dir, queue) = temp_queue();
        let task_id = queue.enqueue("fail_me", "desc", serde_json::json!({}), 0);
        queue.start_worker(|_| Err("boom".to_string()), 1);
        assert!(
            wait_for_status(&queue, &task_id, TaskStatus::Failed),
            "worker did not fail the task"
        );
        queue.stop_workers();
        let task = queue.get(&task_id).unwrap();
        assert_eq!(task.error.as_deref(), Some("boom"));
        assert!(task.completed_at.is_some());
    }
}
