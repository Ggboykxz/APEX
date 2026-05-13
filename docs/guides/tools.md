# Available Tools

APEX ships with over 75 tools organized across ten categories, enabling the AI agent to interact with your filesystem, codebase, shell, version control, the web, databases, containers, cloud infrastructure, and security scanners. Tools are the building blocks that let APEX go beyond text generation and take real actions in your development environment. Each tool can be individually enabled or disabled in your configuration.

## File Tools

File tools allow APEX to read, write, create, delete, and search files on your filesystem. This includes `file_read`, `file_write`, `file_search`, `file_diff`, and `file_watch`. All file operations are scoped to your current working directory by default and require explicit approval when `auto_approve` is disabled.

## Code Tools

Code tools provide language-aware operations such as `code_search`, `code_lint`, `code_format`, and `code_refactor`. These tools leverage LSP (Language Server Protocol) integration to offer symbol navigation, go-to-definition, find-references, and real-time diagnostics across 30+ programming languages.

## Shell Tools

Shell tools give APEX the ability to execute commands in your terminal with `shell_exec`, `shell_background`, and `shell_output`. Commands run in a sandboxed environment with configurable timeouts and permission levels. Shell security policies prevent destructive operations unless explicitly allowed.

## Git Tools

Git tools expose full version control capabilities: `git_status`, `git_diff`, `git_commit`, `git_log`, `git_branch`, `git_checkout`, and `git_undo`. The `git_undo` tool is especially powerful — it can reverse commits, unstaged changes, or entire operation sequences to safely recover from mistakes.

## Web Tools

Web tools enable APEX to fetch URLs, scrape content, and interact with HTTP APIs using `web_fetch`, `web_search`, and `web_scrape`. These are essential for tasks that require looking up documentation, downloading resources, or testing API endpoints.

## Database Tools

Database tools provide read and schema-inspection access to PostgreSQL, MySQL, SQLite, and MongoDB via `db_query`, `db_schema`, and `db_list`. Write operations are disabled by default and can be enabled per-connection in your config.

## Docker Tools

Docker tools let APEX manage containers and images with `docker_ps`, `docker_run`, `docker_build`, `docker_logs`, and `docker_compose`. These tools are invaluable for agents that need to spin up test environments or inspect running services.

## Kubernetes Tools

Kubernetes tools expose cluster management through `k8s_get`, `k8s_apply`, `k8s_logs`, `k8s_describe`, and `k8s_port_forward`. APEX uses your existing kubeconfig context, so it works seamlessly with any cluster you already have configured.

## Cloud Tools

Cloud tools cover AWS, GCP, and Azure operations including `cloud_deploy`, `cloud_storage`, `cloud_function`, and `cloud_instances`. These tools use the respective cloud CLIs under the hood, inheriting your existing authentication profiles.

## Security Tools

Security tools integrate scanning and auditing capabilities: `security_scan`, `security_audit`, `security_dependency_check`, and `security_secret_detect`. These tools help APEX identify vulnerabilities, exposed secrets, and outdated dependencies in your project.
