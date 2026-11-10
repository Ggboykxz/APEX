"""Project tools: repository map, scaffolding, audit and plans.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ProjectToolsMixin",
]


class ProjectToolsMixin:
    def _execute_get_repo_map(self, args: dict[str, Any]) -> str:
        from pathlib import Path

        from .context import get_repo_map

        return get_repo_map(Path(self.cwd))

    def _execute_repo_map(self, args: dict[str, Any]) -> str:
        from .context import get_symbol_map

        raw_path = args.get("path")
        path = self._resolve(raw_path) if raw_path else self.cwd
        try:
            max_tokens = int(args.get("max_tokens", 2000))
        except (TypeError, ValueError):
            max_tokens = 2000
        return get_symbol_map(path, max_tokens=max_tokens)

    def _execute_init_project(self, args: dict[str, Any]) -> str:
        from .project import get_project_initializer

        pi = get_project_initializer(str(self.cwd))
        try:
            output_path = pi.create_context_file()
            return f"SUCCESS: Project initialized\nCreated: {output_path}\n\nRun /map to see project context."
        except Exception as e:  # noqa: BLE001
            return f"ERROR: Failed to initialize project: {e}"

    def _execute_analyze_project(self, args: dict[str, Any]) -> str:
        from .project import get_project_initializer

        pi = get_project_initializer(str(self.cwd))
        analysis = pi.analyze()
        lines = ["Project Analysis", "=" * 40]
        lines.append(f"Language: {analysis.get('language', 'unknown')}")
        lines.append(f"Package Manager: {analysis.get('package_manager', 'unknown')}")
        lines.append(f"Test Framework: {analysis.get('test_framework', 'unknown')}")
        lines.append(f"LSP Server: {analysis.get('lsp_server', 'not configured')}")
        lines.append(f"Build System: {analysis.get('build_system', 'unknown')}")
        lines.append(f"Formatters: {', '.join(analysis.get('formatters', []))}")
        lines.append("")
        lines.append(f"Scripts: {len(analysis.get('scripts', {}))}")
        lines.append(f"Dependencies: {len(analysis.get('dependencies', []))}")
        lines.append(f"Dev Dependencies: {len(analysis.get('dev_dependencies', []))}")
        return "\n".join(lines)

    def _execute_validate_workspace(self, args: dict[str, Any]) -> str:
        from .extras import WorkspaceValidator

        wv = WorkspaceValidator(str(self.cwd))
        result = wv.validate_config()

        lines = ["Workspace Validation", "=" * 40]
        lines.append(f"Valid: {result['valid']}")
        if result["issues"]:
            lines.append("\nIssues:")
            for issue in result["issues"]:
                lines.append(f"  - {issue}")
        return "\n".join(lines)

    def _execute_security_audit(self, args: dict[str, Any]) -> str:
        from .extras import SecurityAuditor

        path = args.get("path")

        sa = SecurityAuditor(str(self.cwd))
        if path:
            result = sa.audit_file(self.cwd / path)
        else:
            result = sa.audit_project()

        if isinstance(result, dict) and "files" in result:
            lines = ["Security Audit", "=" * 40]
            lines.append(f"Total issues: {result['total_issues']}")
            for f in result["files"][:5]:
                lines.append(f"\n{f['path']}:")
                for issue in f["issues"]:
                    lines.append(f"  - {issue['message']}")
            return "\n".join(lines)
        else:
            return f"Issues: {result}"

    def _execute_list_commands(self, args: dict[str, Any]) -> str:
        from .commands import get_command_manager

        cm = get_command_manager(str(self.cwd))
        commands = cm.list_commands()
        if not commands:
            return "No custom commands available. Create .apex/commands/*.md files."
        output = ["Available commands:"]
        for cmd in commands:
            output.append(f"  /{cmd['name']} - {cmd['description']}")
        return "\n".join(output)

    def _execute_plan_approve(self, args: dict[str, Any]) -> str:
        plan_approval = getattr(self, "_plan_approval", None)
        if plan_approval is None:
            return "ERROR: No pending plan to approve"
        plan_approval.approve()
        return "APPROVED: Plan has been approved. Proceeding with execution..."

    def _execute_plan_reject(self, args: dict[str, Any]) -> str:
        plan_approval = getattr(self, "_plan_approval", None)
        if plan_approval is None:
            return "ERROR: No pending plan to reject"
        reason = args.get("reason", "No reason provided")
        plan_approval.reject()
        return f"REJECTED: Plan rejected. Reason: {reason}"
