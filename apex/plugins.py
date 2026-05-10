"""Plugin system for APEX - Dynamic plugin loading and management."""

import importlib.util
import os
import sys
import re
import logging
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


DANGEROUS_PATTERNS = [
    (r"eval\s*\(", "eval() is dangerous"),
    (r"exec\s*\(", "exec() is dangerous"),
    (r"__import__\s*\(", "__import__() is dangerous"),
    (
        r"subprocess\s*\.(run|call|Popen|check_output)\s*\(.*shell\s*=\s*True",
        "shell=True is dangerous",
    ),
    (r"os\s*\.\s*system\s*\(", "os.system() is dangerous"),
    (r"os\s*\.\s*popen\s*\(", "os.popen() is dangerous"),
    (r"pickle\s*\.(load|loads)\s*\(", "pickle.load is dangerous"),
    (r"marshal\s*\.(load|loads)\s*\(", "marshal.load is dangerous"),
    (r"tempfile\s*\.(mktemp|SpooledTemporaryFile)", "tempfile.mktemp is dangerous"),
    (r"\.read_text\s*\(\s*\)", "unrestricted file read"),
    (r"\.write_text\s*\(", "unrestricted file write"),
]


def _check_code_safety(code: str) -> list[str]:
    issues = []
    for pattern, msg in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(msg)
    return issues


@dataclass
class PluginInfo:
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)


class PluginBase(ABC):
    info: PluginInfo

    @abstractmethod
    def initialize(self, app: Any) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass


@dataclass
class PluginHook:
    name: str
    callback: Callable
    priority: int = 0


class PluginManager:
    def __init__(self, plugin_dirs: list[Path] | None = None):
        self._plugins: dict[str, PluginBase] = {}
        self._hooks: dict[str, list[PluginHook]] = {}
        self._plugin_dirs = plugin_dirs or []
        self._app: Any = None
        self._enabled: dict[str, bool] = {}

    def set_app(self, app: Any) -> None:
        self._app = app

    def add_plugin_dir(self, path: Path) -> None:
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def register_hook(self, hook_name: str, callback: Callable, priority: int = 0) -> None:
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(PluginHook(hook_name, callback, priority))
        self._hooks[hook_name].sort(key=lambda h: h.priority)

    def trigger_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        results = []
        if hook_name in self._hooks:
            for hook in self._hooks[hook_name]:
                try:
                    result = hook.callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"Hook {hook_name} error: {e}")
        return results

    async def discover_plugins(self) -> list[str]:
        discovered = []
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for entry in plugin_dir.iterdir():
                if entry.is_file() and entry.suffix == ".py" and entry.stem not in ("__init__",):
                    discovered.append(entry.stem)
                elif entry.is_dir() and (entry / "plugin.py").exists():
                    discovered.append(entry.name)
        return discovered

    def load_plugin(self, name: str) -> bool:
        for plugin_dir in self._plugin_dirs:
            plugin_path = plugin_dir / f"{name}.py"
            if not plugin_path.exists():
                plugin_path = plugin_dir / name / "plugin.py"
            if not plugin_path.exists():
                continue

            try:
                plugin_code = plugin_path.read_text()
                issues = _check_code_safety(plugin_code)
                if issues:
                    logger.warning(f"Plugin {name} contains dangerous patterns: {issues}")
                    if os.environ.get("APEX_ALLOW_DANGEROUS_PLUGINS") != "true":
                        print(f"[SECURITY] Plugin {name} blocked: {', '.join(issues)}")
                        return False

                spec = importlib.util.spec_from_file_location(name, plugin_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    spec.loader.exec_module(module)

                    if hasattr(module, "Plugin"):
                        plugin_class = module.Plugin
                        plugin = plugin_class()
                        if isinstance(plugin, PluginBase):
                            plugin.initialize(self._app)
                            self._plugins[name] = plugin
                            self._enabled[name] = True
                            logger.info(f"Loaded plugin: {name}")
                            return True
            except Exception as e:
                logger.error(f"Failed to load plugin {name}: {e}")
        return False

    def unload_plugin(self, name: str) -> bool:
        if name in self._plugins:
            try:
                self._plugins[name].cleanup()
                del self._plugins[name]
                self._enabled.pop(name, None)
                return True
            except Exception as e:
                print(f"Failed to unload plugin {name}: {e}")
        return False

    def enable_plugin(self, name: str) -> bool:
        if name in self._plugins:
            self._enabled[name] = True
            return True
        return self.load_plugin(name)

    def disable_plugin(self, name: str) -> bool:
        if name in self._plugins:
            self._enabled[name] = False
            return True
        return False

    def get_plugin(self, name: str) -> PluginBase | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [
            {
                "name": name,
                "enabled": self._enabled.get(name, False),
                "info": getattr(plugin, "info", None),
            }
            for name, plugin in self._plugins.items()
        ]

    def get_tools(self) -> list[dict]:
        tools = []
        for name, plugin in self._plugins.items():
            if not self._enabled.get(name, False):
                continue
            if hasattr(plugin, "get_tools"):
                try:
                    tools.extend(plugin.get_tools())
                except Exception:
                    pass
        return tools


class BuiltInPlugins:
    @staticmethod
    def create_logger_plugin() -> type:
        class LoggerPlugin(PluginBase):
            info = PluginInfo(
                name="logger", version="0.1.0", description="Logs all tool calls and agent actions"
            )

            def initialize(self, app) -> None:
                self.app = app
                self.app.plugin_manager.register_hook("tool_call", self.on_tool_call, priority=100)
                self.app.plugin_manager.register_hook(
                    "agent_message", self.on_agent_message, priority=100
                )

            def cleanup(self) -> None:
                pass

            def on_tool_call(self, tool_name: str, args: dict) -> None:
                print(f"[LOG] Tool: {tool_name}({args})")

            def on_agent_message(self, message: str) -> None:
                print(f"[LOG] Agent: {message[:100]}...")

        return LoggerPlugin

    @staticmethod
    def create_security_scanner_plugin() -> type:
        class SecurityScannerPlugin(PluginBase):
            info = PluginInfo(
                name="security_scanner",
                version="0.1.0",
                description="Scans code for security vulnerabilities",
            )

            def initialize(self, app) -> None:
                self.app = app
                self.app.plugin_manager.register_hook(
                    "before_tool_call", self.scan_tool, priority=-100
                )

            def cleanup(self) -> None:
                pass

            def scan_tool(self, tool_name: str, args: dict) -> bool:
                if tool_name in ("write_file", "edit_file"):
                    code = args.get("content", "") or args.get("new_string", "")
                    issues = self._scan_code(code)
                    if issues:
                        print(f"[SECURITY] Warning: {issues}")
                return True

            def _scan_code(self, code: str) -> list[str]:
                issues = []
                dangerous_patterns = [
                    (r"eval\(", "Use of eval() is dangerous"),
                    (r"exec\(", "Use of exec() is dangerous"),
                    (r"subprocess.call.*shell=True", "shell=True is dangerous"),
                    (r"password\s*=", "Hardcoded password detected"),
                    (r"api_key\s*=", "Hardcoded API key detected"),
                    (r"os\.system", "Use of os.system is discouraged"),
                    (r"pickle\.load", "pickle.load can be dangerous"),
                ]
                for pattern, msg in dangerous_patterns:
                    import re

                    if re.search(pattern, code, re.IGNORECASE):
                        issues.append(msg)
                return issues

            def get_tools(self) -> list[dict]:
                return [
                    {
                        "type": "function",
                        "function": {
                            "name": "security_scan",
                            "description": "Scan code for security issues",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "File to scan"}
                                },
                                "required": ["path"],
                            },
                        },
                    }
                ]

        return SecurityScannerPlugin


plugin_manager = PluginManager()


def load_plugins_from_config(config_path: Path, app: Any) -> None:
    if not config_path.exists():
        return

    try:
        import yaml

        with open(config_path) as f:
            config = yaml.safe_load(f)

        if not config or "plugins" not in config:
            return

        plugin_dirs = config.get("plugin_dirs", [])
        for dir_path in plugin_dirs:
            plugin_manager.add_plugin_dir(Path(dir_path).expanduser().resolve())

        plugin_manager.set_app(app)

        for plugin_name in config.get("plugins", []):
            if config["plugins"][plugin_name].get("enabled", True):
                plugin_manager.load_plugin(plugin_name)

    except Exception as e:
        print(f"Failed to load plugins: {e}")
