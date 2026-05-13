"""Project initialization for APEX - analyze and set up projects."""

import json
from pathlib import Path
from typing import Any


class ProjectInitializer:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)

    def analyze(self) -> dict[str, Any]:
        result = {
            "language": None,
            "package_manager": None,
            "test_framework": None,
            "lsp_server": None,
            "formatters": [],
            "build_system": None,
            "structure": {},
            "dependencies": [],
            "dev_dependencies": [],
            "scripts": {},
        }

        self._detect_language(result)
        self._detect_package_manager(result)
        self._detect_test_framework(result)
        self._detect_lsp(result)
        self._detect_formatters(result)
        self._detect_build_system(result)
        self._analyze_structure(result)
        self._extract_info(result)

        return result

    def _detect_language(self, result: dict[str, Any]):
        if (self.cwd / "pyproject.toml").exists():
            result["language"] = "python"
        elif (self.cwd / "package.json").exists():
            result["language"] = "javascript"
        elif (self.cwd / "go.mod").exists():
            result["language"] = "go"
        elif (self.cwd / "Cargo.toml").exists():
            result["language"] = "rust"
        elif (self.cwd / "pom.xml").exists():
            result["language"] = "java"
        elif (self.cwd / "go.sum").exists():
            result["language"] = "go"
        elif (self.cwd / "requirements.txt").exists():
            result["language"] = "python"
        elif (self.cwd / "Gemfile").exists():
            result["language"] = "ruby"

    def _detect_package_manager(self, result: dict[str, Any]):
        if (self.cwd / "pyproject.toml").exists():
            if "poetry" in (self.cwd / "pyproject.toml").read_text():
                result["package_manager"] = "poetry"
            else:
                result["package_manager"] = "pip"
        elif (self.cwd / "package.json").exists():
            if (self.cwd / "yarn.lock").exists():
                result["package_manager"] = "yarn"
            elif (self.cwd / "pnpm-lock.yaml").exists():
                result["package_manager"] = "pnpm"
            else:
                result["package_manager"] = "npm"
        elif (self.cwd / "go.mod").exists():
            result["package_manager"] = "go mod"
        elif (self.cwd / "Cargo.toml").exists():
            result["package_manager"] = "cargo"
        elif (self.cwd / "Gemfile").exists():
            result["package_manager"] = "bundle"

    def _detect_test_framework(self, result: dict[str, Any]):
        if result["language"] == "python":
            if (self.cwd / "pytest.ini").exists():
                result["test_framework"] = "pytest"
            elif (self.cwd / "unittest.py").exists():
                result["test_framework"] = "unittest"
            elif (self.cwd / "pyproject.toml").exists():
                try:
                    import tomllib

                    with open(self.cwd / "pyproject.toml", "rb") as f:
                        data = tomllib.load(f)
                        if data.get("tool", {}).get("pytest"):
                            result["test_framework"] = "pytest"
                except Exception:
                    pass
        elif result["language"] == "javascript":
            pkg = json.loads((self.cwd / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "vitest" in deps:
                result["test_framework"] = "vitest"
            elif "jest" in deps:
                result["test_framework"] = "jest"
            elif "@playwright/test" in deps:
                result["test_framework"] = "playwright"
        elif result["language"] == "go":
            result["test_framework"] = "go test"
        elif result["language"] == "rust":
            result["test_framework"] = "cargo test"

    def _detect_lsp(self, result: dict[str, Any]):
        lsp_map = {
            "python": ["pylsp", "pyright"],
            "javascript": ["typescript-language-server", "javascript-language-server"],
            "typescript": ["typescript-language-server"],
            "go": ["gopls"],
            "rust": ["rust-analyzer"],
            "java": ["java-language-server", "eclipse-jdtls"],
            "ruby": ["solargraph"],
        }
        lang = result.get("language", "")
        if lang in lsp_map:
            result["lsp_server"] = lsp_map[lang][0]

    def _detect_formatters(self, result: dict[str, Any]):
        if result["language"] == "python":
            result["formatters"] = ["black", "ruff"]
        elif result["language"] in ("javascript", "typescript"):
            result["formatters"] = ["prettier", "eslint"]
        elif result["language"] == "go":
            result["formatters"] = ["gofmt", "goimports"]
        elif result["language"] == "rust":
            result["formatters"] = ["rustfmt", "clippy"]

    def _detect_build_system(self, result: dict[str, Any]):
        if result["language"] == "python":
            if (self.cwd / "Makefile").exists():
                result["build_system"] = "make"
            elif (self.cwd / "setup.py").exists():
                result["build_system"] = "setuptools"
        elif result["language"] == "javascript":
            result["build_system"] = "npm"
        elif result["language"] == "go":
            result["build_system"] = "go"
        elif result["language"] == "rust":
            result["build_system"] = "cargo"

    def _analyze_structure(self, result: dict[str, Any]):
        ignore = {
            ".git",
            "node_modules",
            "__pycache__",
            "venv",
            ".venv",
            "target",
            "dist",
            "build",
            ".pytest_cache",
            ".tox",
            "vendor",
        }

        src_dirs = set()
        test_dirs = set()
        config_files = []

        for item in self.cwd.iterdir():
            if item.name.startswith(".") or item.name in ignore:
                continue
            if item.is_dir():
                lower = item.name.lower()
                if "src" in lower or "lib" in lower or "app" in lower:
                    src_dirs.add(item.name)
                elif "test" in lower or "spec" in lower:
                    test_dirs.add(item.name)
            elif item.is_file():
                if item.suffix in (
                    ".json",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".ini",
                    ".cfg",
                    ".conf",
                    ".env",
                ):
                    config_files.append(item.name)

        result["structure"] = {
            "src_dirs": list(src_dirs),
            "test_dirs": list(test_dirs),
            "config_files": config_files,
        }

    def _extract_info(self, result: dict[str, Any]):
        if result["language"] == "python" and (self.cwd / "pyproject.toml").exists():
            try:
                import tomllib

                with open(self.cwd / "pyproject.toml", "rb") as f:
                    data = tomllib.load(f)
                    result["scripts"] = data.get("scripts", {})
                    result["dependencies"] = [
                        d.split("==")[0] for d in data.get("project", {}).get("dependencies", [])
                    ]
                    result["dev_dependencies"] = [
                        d.split("==")[0]
                        for d in data.get("project", {})
                        .get("optional-dependencies", {})
                        .get("dev", [])
                    ]
            except Exception:
                pass
        elif result["language"] == "javascript" and (self.cwd / "package.json").exists():
            try:
                pkg = json.loads((self.cwd / "package.json").read_text())
                result["scripts"] = pkg.get("scripts", {})
                result["dependencies"] = list(pkg.get("dependencies", {}).keys())
                result["dev_dependencies"] = list(pkg.get("devDependencies", {}).keys())
            except Exception:
                pass

    def create_context_file(self) -> str:
        analysis = self.analyze()
        output = self.cwd / "AGENTS.md"

        lines = [
            f"# {self.cwd.name}",
            "",
            f"Language: {analysis.get('language', 'unknown')}",
            f"Package Manager: {analysis.get('package_manager', 'unknown')}",
            f"Test Framework: {analysis.get('test_framework', 'unknown')}",
            f"LSP Server: {analysis.get('lsp_server', 'not configured')}",
            "",
            "## Available Scripts",
        ]

        for name, cmd in analysis.get("scripts", {}).items():
            lines.append(f"- `{name}`: {cmd}")

        lines.extend(
            [
                "",
                "## Project Structure",
                "",
                f"Source directories: {', '.join(analysis['structure'].get('src_dirs', [])) or 'none'}",
                f"Test directories: {', '.join(analysis['structure'].get('test_dirs', [])) or 'none'}",
                "",
                "## Key Dependencies",
            ]
        )

        for dep in analysis.get("dependencies", [])[:20]:
            lines.append(f"- {dep}")

        lines.extend(
            [
                "",
                "## Configuration Files",
            ]
        )

        for cf in analysis.get("structure", {}).get("config_files", []):
            lines.append(f"- {cf}")

        output.write_text("\n".join(lines))
        return str(output)


class FileWatcher:
    def __init__(self, cwd: str):
        self.cwd = Path(cwd)
        self._callbacks = []
        self._running = False

    def watch(self, patterns: list[str] = None):
        patterns = patterns or ["*.py", "*.js", "*.ts", "*.go", "*.rs"]
        try:
            import watchdog
            from watchdog.observers import Observer

            class Handler(watchdog.events.FileSystemEventHandler):
                def __init__(self, callbacks):
                    self.callbacks = callbacks

                def on_modified(self, event):
                    if not event.is_directory:
                        for cb in self.callbacks:
                            cb(event.src_path)

            handler = Handler(self._callbacks)
            observer = Observer()
            for pattern in patterns:
                observer.schedule(handler, str(self.cwd), recursive=True)
            observer.start()
            self._running = True
            return observer
        except ImportError:
            return None

    def add_callback(self, callback):
        self._callbacks.append(callback)

    def stop(self):
        self._running = False


_project_initializer: dict[str, "ProjectInitializer"] = {}


def get_project_initializer(cwd: str) -> ProjectInitializer:
    cwd_key = str(Path(cwd).resolve())
    if cwd_key not in _project_initializer:
        _project_initializer[cwd_key] = ProjectInitializer(cwd_key)
    return _project_initializer[cwd_key]
