"""Formatter system for APEX — mirrors OpenCode's formatter UX."""

from __future__ import annotations

import copy
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FormatterConfig:
    name: str
    command: list[str]
    extensions: list[str]
    environment: dict[str, str] = field(default_factory=dict)
    disabled: bool = False
    requirements: list[str] | None = None  # e.g. ["package.json:prettier"]


BUILTIN_FORMATTERS: list[FormatterConfig] = [
    FormatterConfig(
        name="ruff",
        command=["ruff", "format", "$FILE"],
        extensions=[".py", ".pyi"],
    ),
    FormatterConfig(
        name="prettier",
        command=["npx", "prettier", "--write", "$FILE"],
        extensions=[".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".md", ".html", ".css"],
        requirements=["package.json:prettier"],
    ),
    FormatterConfig(
        name="biome",
        command=["npx", "@biomejs/biome", "format", "--write", "$FILE"],
        extensions=[".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".html", ".md"],
        requirements=["biome.json", "biome.jsonc"],
    ),
    FormatterConfig(
        name="rustfmt",
        command=["rustfmt", "$FILE"],
        extensions=[".rs"],
    ),
    FormatterConfig(
        name="cargofmt",
        command=["cargo", "fmt", "--", "$FILE"],
        extensions=[".rs"],
    ),
    FormatterConfig(
        name="gofmt",
        command=["gofmt", "-w", "$FILE"],
        extensions=[".go"],
    ),
    FormatterConfig(
        name="google-java-format",
        command=["google-java-format", "$FILE"],
        extensions=[".java"],
    ),
    FormatterConfig(
        name="clang-format",
        command=["clang-format", "-i", "$FILE"],
        extensions=[".c", ".h", ".cpp", ".hpp", ".ino"],
    ),
    FormatterConfig(
        name="rubocop",
        command=["rubocop", "-a", "$FILE"],
        extensions=[".rb", ".rake", ".gemspec", ".ru"],
    ),
    FormatterConfig(
        name="scalafmt",
        command=["scalafmt", "$FILE"],
        extensions=[".scala"],
    ),
    FormatterConfig(
        name="ktlint",
        command=["ktlint", "$FILE"],
        extensions=[".kt", ".kts"],
    ),
    FormatterConfig(
        name="swift-format",
        command=["swift-format", "-i", "$FILE"],
        extensions=[".swift"],
    ),
    FormatterConfig(
        name="zig-fmt",
        command=["zig", "fmt", "$FILE"],
        extensions=[".zig", ".zon"],
    ),
    FormatterConfig(
        name="dart",
        command=["dart", "format", "$FILE"],
        extensions=[".dart"],
    ),
    FormatterConfig(
        name="shfmt",
        command=["shfmt", "-w", "$FILE"],
        extensions=[".sh", ".bash"],
    ),
    FormatterConfig(
        name="terraform",
        command=["terraform", "fmt", "$FILE"],
        extensions=[".tf", ".tfvars"],
    ),
    FormatterConfig(
        name="mix",
        command=["mix", "format", "$FILE"],
        extensions=[".ex", ".exs", ".eex", ".heex"],
    ),
    FormatterConfig(
        name="nixfmt",
        command=["nixfmt", "$FILE"],
        extensions=[".nix"],
    ),
    FormatterConfig(
        name="standardrb",
        command=["standardrb", "--fix", "$FILE"],
        extensions=[".rb", ".rake", ".gemspec", ".ru"],
    ),
    FormatterConfig(
        name="uv",
        command=["uv", "tool", "run", "ruff", "format", "$FILE"],
        extensions=[".py", ".pyi"],
    ),
]


class FormatterManager:
    def __init__(self) -> None:
        self._formatters: list[FormatterConfig] = copy.deepcopy(BUILTIN_FORMATTERS)
        self._available: dict[str, bool] = {}
        self._loaded = False

    @property
    def formatters(self) -> list[FormatterConfig]:
        return list(self._formatters)

    def load_from_config(self) -> None:
        from .config_v2 import apex_config

        cfg = apex_config.formatter
        self._formatters = copy.deepcopy(BUILTIN_FORMATTERS)

        if cfg is False:
            self._disable_all()
            return
        if cfg is True:
            self._finish_loading()
            return
        if not isinstance(cfg, dict):
            self._finish_loading()
            return
        if cfg.get("disabled", False) is True:
            self._disable_all()
            return

        for name, opts in cfg.items():
            if isinstance(opts, dict):
                self._apply_formatter_options(name, opts)

        self._finish_loading()

    def _disable_all(self) -> None:
        """Disable every registered formatter."""
        for fmt in self._formatters:
            fmt.disabled = True
        self._loaded = True
        self._available = {f.name: False for f in self._formatters}

    def _finish_loading(self) -> None:
        """Mark the manager as loaded and discover availability."""
        self._loaded = True
        self.discover_available()

    def _apply_formatter_options(self, name: str, opts: dict) -> None:
        """Apply one formatter's options."""
        existing = next((f for f in self._formatters if f.name == name), None)
        if existing is not None:
            existing.disabled = opts.get("disabled", False)
            if "command" in opts:
                existing.command = opts["command"]
            if "extensions" in opts:
                existing.extensions = opts["extensions"]
            if "environment" in opts:
                existing.environment = opts["environment"]
            return
        if "command" in opts and "extensions" in opts:
            self._formatters.append(
                FormatterConfig(
                    name=name,
                    command=opts["command"],
                    extensions=opts["extensions"],
                    environment=opts.get("environment", {}),
                    disabled=opts.get("disabled", False),
                )
            )

    @staticmethod
    def _check_requirement(req: str) -> bool:
        if ":" in req:
            file_part, dep = req.split(":", 1)
            p = Path(file_part)
            if not p.is_file():
                return False
            try:
                return dep in p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                logger.debug("failed to read %s", p)
                return False
        p = Path(req)
        if p.is_file():
            return True
        return shutil.which(req.split()[0]) is not None

    def discover_available(self) -> None:
        self._available = {}
        for fmt in self._formatters:
            if fmt.requirements and not all(self._check_requirement(r) for r in fmt.requirements):
                self._available[fmt.name] = False
                continue
            binary = fmt.command[0].split()[0]
            if binary == "npx":
                self._available[fmt.name] = shutil.which("node") is not None
            elif binary == "cargo":
                self._available[fmt.name] = shutil.which("cargo") is not None
            else:
                self._available[fmt.name] = shutil.which(binary) is not None

    def list_available(self) -> list[FormatterConfig]:
        if not self._loaded:
            self.load_from_config()
        return [
            f for f in self._formatters if not f.disabled and self._available.get(f.name, False)
        ]

    def get_formatter_for(self, file_path: str) -> FormatterConfig | None:
        if not self._loaded:
            self.load_from_config()
        ext = Path(file_path).suffix.lower()
        for fmt in self._formatters:
            if fmt.disabled:
                continue
            if ext in fmt.extensions and self._available.get(fmt.name, False):
                return fmt
        return None

    def is_formattable(self, file_path: str) -> bool:
        return self.get_formatter_for(file_path) is not None

    def format_file(self, file_path: str) -> bool:
        fmt = self.get_formatter_for(file_path)
        if fmt is None:
            return False
        return self._run_formatter(fmt, file_path)

    def format_files(self, file_paths: list[str]) -> dict[str, bool]:
        return {fp: self.format_file(fp) for fp in file_paths}

    def format_code(self, code: str, extension: str) -> str:
        if not self._loaded:
            self.load_from_config()
        if not self._valid_extension(extension):
            return code
        ext = extension if extension.startswith(".") else f".{extension}"
        formatter = self._available_formatter(ext)
        if formatter is None:
            return code
        return self._run_formatter_tempfile(formatter, code, ext)

    @staticmethod
    def _valid_extension(extension: str) -> bool:
        """Whether an extension is safe to use as a temp file suffix."""
        if not extension:
            return False
        if "/" in extension:
            return False
        if "\\" in extension:
            return False
        return ".." not in extension

    def _available_formatter(self, extension: str) -> FormatterConfig | None:
        """The first available formatter for an extension."""
        for formatter in self._formatters:
            if formatter.disabled:
                continue
            if extension in formatter.extensions and self._available.get(formatter.name, False):
                return formatter
        return None

    def _build_command(self, fmt: FormatterConfig, file_path: str) -> list[str]:
        return [part.replace("$FILE", file_path) for part in fmt.command]

    def _run_formatter(self, fmt: FormatterConfig, file_path: str) -> bool:
        if not os.path.isfile(file_path):
            return False
        cmd = self._build_command(fmt, file_path)
        env = {**os.environ, **fmt.environment}
        try:
            # cmd is a list (not shell=True), so shell injection is impossible.
            # file_path comes from formatter config / user input but is passed
            # as a discrete argument, not interpolated into a shell string.
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                timeout=60,
                check=False,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _run_formatter_tempfile(self, fmt: FormatterConfig, code: str, extension: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=extension, delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        try:
            cmd = self._build_command(fmt, tmp_path)
            env = {**os.environ, **fmt.environment}
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                timeout=60,
                check=False,
            )
            if result.returncode == 0:
                return Path(tmp_path).read_text(encoding="utf-8")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return code


formatter_manager = FormatterManager()


__all__ = [
    "BUILTIN_FORMATTERS",
    "FormatterConfig",
    "FormatterManager",
    "formatter_manager",
]
