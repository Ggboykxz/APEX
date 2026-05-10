# Plugins

APEX has a powerful plugin system for extending functionality.

## Built-in Plugins

### Logger Plugin

Logs all tool calls and agent messages for debugging.

```python
from apex.plugins import BuiltInPlugins

LoggerPlugin = BuiltInPlugins.create_logger_plugin()
```

Enables automatically when loaded via config.

### Security Scanner Plugin

Scans code for security vulnerabilities before execution.

```yaml
# .apex/config.yaml
plugins:
  security_scanner:
    enabled: true
```

Checks for:
- Use of `eval()` or `exec()`
- `shell=True` in subprocess calls
- Hardcoded passwords or API keys
- Use of `os.system`
- Dangerous `pickle` operations

## Custom Plugins

Create your own plugins by extending `PluginBase`:

```python
from apex.plugins import PluginBase, PluginInfo, PluginManager

class MyPlugin(PluginBase):
    info = PluginInfo(
        name="my-plugin",
        version="0.1.0",
        description="My custom plugin"
    )

    def initialize(self, app):
        # Called when plugin loads
        self.app = app
        app.plugin_manager.register_hook("tool_call", self.on_tool_call)

    def cleanup(self):
        # Called when plugin unloads
        pass

    def on_tool_call(self, tool_name, args):
        print(f"Tool called: {tool_name}")
```

## Hooks

Plugins can register hooks for various events:

| Hook | Description | Parameters |
|------|-------------|------------|
| `agent_start` | Agent initialized | model, agent |
| `agent_message` | New message | message |
| `tool_call` | Tool about to run | tool_name, args |
| `tool_result` | Tool completed | tool_name, result |
| `before_tool_call` | Before tool execution | tool_name, args |
| `error` | Error occurred | error_type, message |

## Configuration

Load plugins from config:

```yaml
# .apex/config.yaml
plugin_dirs:
  - ~/.apex/plugins

plugins:
  logger:
    enabled: true
  security_scanner:
    enabled: true
```

## Plugin Directory Structure

```
~/.apex/plugins/
├── my_plugin.py
├── another_plugin/
│   ├── plugin.py
│   └── config.yaml
└── __init__.py
```

## Plugin API

```python
from apex import plugin_manager

# List loaded plugins
plugin_manager.list_plugins()

# Enable/disable plugin
plugin_manager.enable_plugin("my-plugin")
plugin_manager.disable_plugin("my-plugin")

# Get plugin instance
plugin = plugin_manager.get_plugin("my-plugin")

# Get custom tools from plugins
tools = plugin_manager.get_tools()
```

## Example: Custom Linter Plugin

```python
import re
from apex.plugins import PluginBase, PluginInfo

class LinterPlugin(PluginBase):
    info = PluginInfo(
        name="linter",
        version="0.1.0",
        description="Code linting plugin"
    )

    def initialize(self, app):
        self.app = app
        app.plugin_manager.register_hook("before_tool_call", self.lint_code)

    def cleanup(self):
        pass

    def lint_code(self, tool_name, args):
        if tool_name in ("write_file", "edit_file"):
            code = args.get("content", "") or args.get("new_string", "")
            issues = self._lint(code)
            if issues:
                print(f"[LINTER] Issues found: {issues}")

    def _lint(self, code):
        issues = []
        if "TODO" in code:
            issues.append("TODO comment found")
        if len(code.splitlines()) > 500:
            issues.append("File exceeds 500 lines")
        return issues
```

## Loading Plugins Programmatically

```python
from apex.plugins import plugin_manager, load_plugins_from_config

# Set the app reference
plugin_manager.set_app(app)

# Load from config
load_plugins_from_config(Path("~/.apex/config.yaml"), app)

# Or load manually
plugin_manager.add_plugin_dir(Path("~/.apex/plugins"))
plugin_manager.load_plugin("my-plugin")
```