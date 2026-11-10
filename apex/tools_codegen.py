"""Code-analysis and generation tools.

Split out of ``apex.tools`` so that module keeps a single
responsibility: the tool executor core.
"""

from __future__ import annotations

import os
from typing import Any

__all__ = [
    "CodegenToolsMixin",
]


class CodegenToolsMixin:
    def _execute_analyze_code(self, args: dict[str, Any]) -> str:
        from .skills import CodeAnalyzer

        path = args["path"]
        ca = CodeAnalyzer(str(self.cwd))
        result = ca.analyze_file(path)

        if "error" in result:
            return result["error"]

        lines = ["Code Analysis", "=" * 40]
        lines.append(f"File: {result['path']}")
        lines.append(f"Lines: {result['lines']}")
        lines.append(f"Code lines: {result['code_lines']}")
        lines.append(f"Comment lines: {result['comment_lines']}")
        lines.append(f"Blank lines: {result['blank_lines']}")
        lines.append("")
        lines.append(f"Functions ({len(result['functions'])}):")
        for f in result["functions"][:5]:
            lines.append(f"  - {f['name']} (line {f['line']})")
        lines.append("")
        lines.append(f"Classes ({len(result['classes'])}):")
        for c in result["classes"][:5]:
            lines.append(f"  - {c['name']} (line {c['line']})")
        lines.append("")
        lines.append(f"Imports ({len(result['imports'])}):")
        lines.append(", ".join(result["imports"][:10]))
        return "\n".join(lines)

    def _execute_explain_code(self, args: dict[str, Any]) -> str:
        from .skills import CodeAnalyzer

        path = args["path"]
        start = args.get("start", 1)
        end = args.get("end")
        ca = CodeAnalyzer(str(self.cwd))
        return ca.explain_code(path, start, end)

    def _pytest_stub(self, path: str, funcs: list[dict]) -> list[str]:
        """Build the pytest stub of the given functions."""
        module_path = path.replace(os.sep, ".").rsplit(".py", 1)[0]
        lines = [
            f'"""Tests for {module_path}"""',
            "",
            "import pytest",
            f"from {module_path} import *",
            "",
        ]
        for f in funcs[:5]:
            lines.append(f"def test_{f['name']}():")
            lines.append("    pass")
        return lines

    def _jest_stub(self, path: str, funcs: list[dict]) -> list[str]:
        """Build the Jest stub of the given functions."""
        lines = ["// Tests for " + path, ""]
        for f in funcs[:5]:
            lines.append(f"describe('{f['name']}', () => {{")
            lines.append("  it('should work', () => {")
            lines.append("    // implement test")
            lines.append("  });")
            lines.append("});")
        return lines

    def _execute_generate_tests(self, args: dict[str, Any]) -> str:
        path = args["path"]
        framework = args.get("framework", "pytest")

        from .skills import CodeAnalyzer

        ca = CodeAnalyzer(str(self.cwd))
        analysis = ca.analyze_file(path)

        if "error" in analysis:
            return analysis["error"]

        funcs = analysis.get("functions", [])
        if not funcs:
            return "No functions found to generate tests for."

        if framework == "pytest":
            lines = self._pytest_stub(path, funcs)
        else:
            lines = self._jest_stub(path, funcs)

        return "\n".join(lines)

    def _execute_refactor_code(self, args: dict[str, Any]) -> str:
        from .codegen import CodeRefactorer

        path = args["path"]
        function = args["function"]
        style = args.get("style", "modern")

        cr = CodeRefactorer(str(self.cwd))
        result = cr.refactor_function(path, function, style)

        if "error" in result:
            return f"ERROR: {result['error']}"
        return f"SUCCESS: Refactored {function} with {style} style"

    def _execute_profile_code(self, args: dict[str, Any]) -> str:
        from .codegen import PerformanceProfiler

        path = args["path"]

        pp = PerformanceProfiler(str(self.cwd))
        result = pp.profile_file(path)

        if "error" in result:
            return result["error"]

        lines = ["Code Profile", "=" * 40]
        lines.append(f"Lines: {result['lines']}")
        lines.append(f"Functions: {result['functions']}")
        lines.append(f"Classes: {result['classes']}")
        lines.append(f"Imports: {result['imports']}")
        lines.append(f"Complexity: {result['complexity_score']}")
        return "\n".join(lines)

    def _execute_optimize_code(self, args: dict[str, Any]) -> str:
        from .codegen import PerformanceProfiler

        path = args["path"]

        pp = PerformanceProfiler(str(self.cwd))
        suggestions = pp.suggest_optimizations(path)

        lines = ["Optimization Suggestions", "=" * 40]
        for s in suggestions:
            lines.append(f"- {s}")
        return "\n".join(lines)

    def _execute_generate_db_model(self, args: dict[str, Any]) -> str:
        from .codegen import DatabaseManager

        table = args["table"]
        columns = args["columns"]

        dm = DatabaseManager(str(self.cwd))
        code = dm.generate_model(table, columns)
        return f"Generated model for {table}:\n\n{code}"

    def _execute_generate_dockerfile(self, args: dict[str, Any]) -> str:
        from .codegen import DockerManager

        language = args["language"]

        dm = DockerManager(str(self.cwd))
        dockerfile = dm.generate_dockerfile(language)
        return dockerfile

    def _execute_generate_docker_compose(self, args: dict[str, Any]) -> str:
        from .codegen import DockerManager

        services = args.get("services", [])

        dm = DockerManager(str(self.cwd))
        compose = dm.generate_docker_compose(services)
        return compose

    def _execute_generate_api_client(self, args: dict[str, Any]) -> str:
        from .codegen import APIClientGenerator

        spec = args["spec"]

        acg = APIClientGenerator(str(self.cwd))
        code = acg.generate_from_openapi(spec)
        return code

    def _execute_generate_docs(self, args: dict[str, Any]) -> str:
        from .codegen import DocumentationGenerator

        dtype = args["type"]
        path = args.get("path")

        dg = DocumentationGenerator(str(self.cwd))

        if dtype == "readme":
            return dg.generate_readme()
        elif dtype == "api" and path:
            return dg.generate_api_docs(path)
        elif dtype == "markdoc":
            return dg.generate_markdoc()

        return "ERROR: Invalid doc type or missing path"
