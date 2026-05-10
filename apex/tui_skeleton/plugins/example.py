"""Example TUI plugin."""

from ..plugins import Plugin, PluginMetadata


class ExamplePlugin(Plugin):
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.name = metadata.name or "Example Plugin"
        self.version = metadata.version or "0.0.1"

    def on_install(self) -> None:
        print(f"Installing {self.name} v{self.version}")

    def on_enable(self) -> None:
        print(f"Enabling {self.name}")
        self.register_command("example", lambda: print("Example command executed"))

    def on_disable(self) -> None:
        print(f"Disabling {self.name}")


def register(manager):
    return manager.load_plugin("example", ExamplePlugin)