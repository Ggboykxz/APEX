"""Comprehensive tests for formatter.py — aims for 100 % line coverage."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from apex.formatter import (
    BUILTIN_FORMATTERS,
    FormatterConfig,
    FormatterManager,
    formatter_manager,
)


# ---------------------------------------------------------------------------
# FormatterConfig dataclass
# ---------------------------------------------------------------------------


class TestFormatterConfig:
    def test_all_fields(self):
        cfg = FormatterConfig(
            name="test-fmt",
            command=["tool", "$FILE"],
            extensions=[".xyz", ".abc"],
            environment={"KEY": "val"},
            disabled=True,
        )
        assert cfg.name == "test-fmt"
        assert cfg.command == ["tool", "$FILE"]
        assert cfg.extensions == [".xyz", ".abc"]
        assert cfg.environment == {"KEY": "val"}
        assert cfg.disabled is True

    def test_environment_defaults_to_empty_dict(self):
        cfg = FormatterConfig(name="e", command=["e"], extensions=[".e"])
        assert cfg.environment == {}

    def test_disabled_defaults_to_false(self):
        cfg = FormatterConfig(name="e", command=["e"], extensions=[".e"])
        assert cfg.disabled is False

    def test_repr_and_str(self):
        cfg = FormatterConfig(
            name="rfmt", command=["rfmt", "$FILE"], extensions=[".r"]
        )
        assert "rfmt" in repr(cfg)


# ---------------------------------------------------------------------------
# BUILTIN_FORMATTERS
# ---------------------------------------------------------------------------


class TestBuiltinFormatters:
    def test_eleven_formatters(self):
        assert len(BUILTIN_FORMATTERS) == 11

    def test_each_has_name_command_extensions(self):
        for fmt in BUILTIN_FORMATTERS:
            assert fmt.name
            assert fmt.command
            assert fmt.extensions
            assert "$FILE" in " ".join(fmt.command)

    def test_ruff(self):
        f = BUILTIN_FORMATTERS[0]
        assert f.name == "ruff"
        assert f.command == ["ruff", "format", "$FILE"]
        assert f.extensions == [".py"]

    def test_prettier(self):
        f = BUILTIN_FORMATTERS[1]
        assert f.name == "prettier"
        assert f.command == ["npx", "prettier", "--write", "$FILE"]
        assert f.extensions == [".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".md"]

    def test_rustfmt(self):
        f = BUILTIN_FORMATTERS[2]
        assert f.name == "rustfmt"
        assert f.extensions == [".rs"]

    def test_gofmt(self):
        f = BUILTIN_FORMATTERS[3]
        assert f.name == "gofmt"
        assert f.extensions == [".go"]

    def test_google_java_format(self):
        f = BUILTIN_FORMATTERS[4]
        assert f.name == "google-java-format"
        assert f.extensions == [".java"]

    def test_clang_format(self):
        f = BUILTIN_FORMATTERS[5]
        assert f.name == "clang-format"
        assert f.extensions == [".c", ".h", ".cpp"]

    def test_rubocop(self):
        f = BUILTIN_FORMATTERS[6]
        assert f.name == "rubocop"
        assert f.extensions == [".rb"]

    def test_scalafmt(self):
        f = BUILTIN_FORMATTERS[7]
        assert f.name == "scalafmt"
        assert f.extensions == [".scala"]

    def test_ktlint(self):
        f = BUILTIN_FORMATTERS[8]
        assert f.name == "ktlint"
        assert f.extensions == [".kt"]

    def test_swift_format(self):
        f = BUILTIN_FORMATTERS[9]
        assert f.name == "swift-format"
        assert f.extensions == [".swift"]

    def test_zig_fmt(self):
        f = BUILTIN_FORMATTERS[10]
        assert f.name == "zig-fmt"
        assert f.extensions == [".zig"]
        assert f.command == ["zig", "fmt", "$FILE"]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestFormatterManagerSingleton:
    def test_formatter_manager_is_instance(self):
        assert isinstance(formatter_manager, FormatterManager)

    def test_singleton_has_initial_state(self):
        assert len(formatter_manager._formatters) == 11
        assert formatter_manager._loaded is False
        assert formatter_manager._available == {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def manager():
    """Fresh FormatterManager with _loaded=True — skips config loading."""
    m = FormatterManager()
    m._loaded = True
    return m


# ---------------------------------------------------------------------------
# is_formattable
# ---------------------------------------------------------------------------


class TestIsFormattable:
    def test_all_supported_extensions(self, manager):
        ext_to_fmt = {}
        for fmt in BUILTIN_FORMATTERS:
            for ext in fmt.extensions:
                ext_to_fmt[ext] = fmt.name
            manager._available[fmt.name] = True

        for ext in sorted(ext_to_fmt):
            assert manager.is_formattable(f"/path/file{ext}"), f"{ext} should be formattable"

    def test_unsupported_extensions_return_false(self, manager):
        for ext in [".xyz", ".unknown", ".foo", "", ".exe"]:
            assert not manager.is_formattable(f"/path/file{ext}")

    def test_disabled_formatter_not_formattable(self, manager):
        fmt = manager._formatters[0]
        ext = fmt.extensions[0]
        manager._available[fmt.name] = True
        assert manager.is_formattable(f"/path/file{ext}")
        fmt.disabled = True
        assert not manager.is_formattable(f"/path/file{ext}")

    def test_unavailable_formatter_not_formattable(self, manager):
        fmt = BUILTIN_FORMATTERS[0]
        ext = fmt.extensions[0]
        manager._available[fmt.name] = False
        assert not manager.is_formattable(f"/path/file{ext}")

    def test_triggers_load_when_not_loaded(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = True
            m = FormatterManager()
            assert m._loaded is False
            m.is_formattable("/path/file.py")
            assert m._loaded is True


# ---------------------------------------------------------------------------
# get_formatter_for
# ---------------------------------------------------------------------------


class TestGetFormatterFor:
    def test_returns_correct_formatter(self, manager):
        for fmt in manager._formatters:
            ext = fmt.extensions[0]
            manager._available[fmt.name] = True
            result = manager.get_formatter_for(f"/path/file{ext}")
            assert result is not None, f"No formatter for {ext} ({fmt.name})"
            assert result.name == fmt.name

    def test_returns_none_for_unsupported_extension(self, manager):
        assert manager.get_formatter_for("/path/file.xyz") is None

    def test_skips_disabled_formatters(self, manager):
        fmt = manager._formatters[0]
        ext = fmt.extensions[0]
        manager._available[fmt.name] = True
        assert manager.get_formatter_for(f"/path/file{ext}") is not None
        fmt.disabled = True
        assert manager.get_formatter_for(f"/path/file{ext}") is None

    def test_skips_unavailable_formatters(self, manager):
        fmt = BUILTIN_FORMATTERS[0]
        ext = fmt.extensions[0]
        manager._available[fmt.name] = False
        assert manager.get_formatter_for(f"/path/file{ext}") is None

    def test_triggers_load_when_not_loaded(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = True
            m = FormatterManager()
            assert m._loaded is False
            result = m.get_formatter_for("/path/file.py")
            assert m._loaded is True
            # ruff not installed, so None
            assert result is None


# ---------------------------------------------------------------------------
# format_code
# ---------------------------------------------------------------------------


class TestFormatCode:
    def test_returns_formatted_code(self, manager):
        manager._available["ruff"] = True

        def _mock_run(cmd, **kwargs):
            file_path = cmd[-1]
            Path(file_path).write_text("# formatted by ruff\nx = 1\n")
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"", stderr=b""
            )

        with patch("apex.formatter.subprocess.run", side_effect=_mock_run):
            result = manager.format_code("x=1\n", ".py")

        assert result == "# formatted by ruff\nx = 1\n"

    def test_returns_original_on_no_matching_formatter(self, manager):
        result = manager.format_code("some code", ".xyz")
        assert result == "some code"

    def test_returns_original_on_subprocess_nonzero(self, manager):
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=b"", stderr=b"error"
            ),
        ):
            result = manager.format_code("x=1\n", ".py")

        assert result == "x=1\n"

    def test_returns_original_on_subprocess_exception(self, manager):
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["ruff"], timeout=60),
        ):
            result = manager.format_code("x=1\n", ".py")

        assert result == "x=1\n"

    def test_skips_disabled_formatter_in_loop(self, manager):
        fmt = manager._formatters[0]
        fmt.disabled = True
        manager._available["ruff"] = True
        result = manager.format_code("x=1\n", ".py")
        assert result == "x=1\n"

    def test_accepts_extension_without_dot(self, manager):
        manager._available["ruff"] = True

        def _mock_run(cmd, **kwargs):
            file_path = cmd[-1]
            Path(file_path).write_text("# formatted\nx = 1\n")
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"", stderr=b""
            )

        with patch("apex.formatter.subprocess.run", side_effect=_mock_run):
            result = manager.format_code("x=1\n", "py")

        assert "# formatted" in result

    def test_tempfile_cleanup_handles_oserror(self, manager):
        manager._available["ruff"] = True

        def _mock_run(cmd, **kwargs):
            file_path = cmd[-1]
            Path(file_path).write_text("formatted_code")
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"", stderr=b""
            )

        with patch("apex.formatter.subprocess.run", side_effect=_mock_run):
            with patch("apex.formatter.os.unlink", side_effect=OSError("permission denied")):
                result = manager.format_code("x=1\n", ".py")

        assert result == "formatted_code"

    def test_triggers_load_when_not_loaded(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = True
            m = FormatterManager()
            assert m._loaded is False
            result = m.format_code("x=1\n", ".xyz")
            assert m._loaded is True
            assert result == "x=1\n"


# ---------------------------------------------------------------------------
# format_file
# ---------------------------------------------------------------------------


class TestFormatFile:
    def test_returns_true_on_success(self, tmp_path, manager):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"", stderr=b""
            ),
        ):
            assert manager.format_file(str(f)) is True

    def test_returns_false_on_nonexistent_file(self, manager):
        manager._available["ruff"] = True
        assert manager.format_file("/nonexistent/file.py") is False

    def test_returns_false_on_no_formatter(self, manager):
        assert manager.format_file("/path/file.xyz") is False

    def test_returns_false_on_subprocess_failure(self, tmp_path, manager):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=b"", stderr=b""
            ),
        ):
            assert manager.format_file(str(f)) is False

    def test_returns_false_on_subprocess_exception(self, tmp_path, manager):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            side_effect=FileNotFoundError("binary not found"),
        ):
            assert manager.format_file(str(f)) is False

    def test_custom_env_vars_passed_to_subprocess(self, tmp_path, manager):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")

        custom_fmt = FormatterConfig(
            name="myfmt",
            command=["myfmt", "$FILE"],
            extensions=[".py"],
            environment={"MY_VAR": "hello"},
        )
        manager._formatters.append(custom_fmt)
        manager._available["myfmt"] = True

        with patch("apex.formatter.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"", stderr=b""
            )
            manager.format_file(str(f))

            _call_env = mock_run.call_args[1]["env"]
            assert _call_env["MY_VAR"] == "hello"

    def test_oserror_handled_gracefully(self, tmp_path, manager):
        f = tmp_path / "test.py"
        f.write_text("x = 1\n")
        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            assert manager.format_file(str(f)) is False


# ---------------------------------------------------------------------------
# format_files
# ---------------------------------------------------------------------------


class TestFormatFiles:
    def test_processes_multiple_files(self, tmp_path, manager):
        py_file = tmp_path / "a.py"
        js_file = tmp_path / "b.js"
        py_file.write_text("x = 1\n")
        js_file.write_text("const x = 1\n")

        manager._available["ruff"] = True
        manager._available["prettier"] = True
        manager._formatters[1].disabled = False

        with patch(
            "apex.formatter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"", stderr=b""
            ),
        ):
            results = manager.format_files([str(py_file), str(js_file)])

        assert len(results) == 2
        assert results[str(py_file)] is True
        assert results[str(js_file)] is True

    def test_mixed_results(self, tmp_path, manager):
        py_file = tmp_path / "a.py"
        unknown_file = tmp_path / "b.xyz"
        py_file.write_text("x = 1\n")
        unknown_file.write_text("stuff\n")

        manager._available["ruff"] = True

        with patch(
            "apex.formatter.subprocess.run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout=b"", stderr=b""
            ),
        ):
            results = manager.format_files([str(py_file), str(unknown_file)])

        assert results[str(py_file)] is True
        assert results[str(unknown_file)] is False


# ---------------------------------------------------------------------------
# load_from_config
# ---------------------------------------------------------------------------


class TestLoadFromConfig:
    def test_formatter_true_enables_all(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = True
            m = FormatterManager()
            m.load_from_config()

        assert m._loaded is True
        assert all(not f.disabled for f in m._formatters)

    def test_formatter_false_disables_all(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = False
            m = FormatterManager()
            m.load_from_config()

        assert m._loaded is True
        assert all(f.disabled for f in m._formatters)
        assert all(v is False for v in m._available.values())

    def test_dict_disabled_true_disables_all(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {"disabled": True}
            m = FormatterManager()
            m.load_from_config()

        assert m._loaded is True
        assert all(f.disabled for f in m._formatters)

    def test_custom_formatter_added(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "my-fmt": {
                    "command": ["my-tool", "$FILE"],
                    "extensions": [".xyz"],
                    "environment": {"K": "V"},
                    "disabled": False,
                }
            }
            m = FormatterManager()
            m.load_from_config()

        assert len(m._formatters) == 12
        custom = next((f for f in m._formatters if f.name == "my-fmt"), None)
        assert custom is not None
        assert custom.command == ["my-tool", "$FILE"]
        assert custom.extensions == [".xyz"]
        assert custom.environment == {"K": "V"}
        assert custom.disabled is False

    def test_custom_formatter_minimal(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "mini-fmt": {
                    "command": ["mini", "$FILE"],
                    "extensions": [".mn"],
                }
            }
            m = FormatterManager()
            m.load_from_config()

        custom = next(
            (f for f in m._formatters if f.name == "mini-fmt"), None
        )
        assert custom is not None
        assert custom.environment == {}
        assert custom.disabled is False

    def test_update_existing_formatter(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "ruff": {
                    "disabled": True,
                    "extensions": [".py", ".pyi"],
                }
            }
            m = FormatterManager()
            m.load_from_config()

        ruff = next(f for f in m._formatters if f.name == "ruff")
        assert ruff.disabled is True
        assert ruff.extensions == [".py", ".pyi"]
        assert ruff.command == ["ruff", "format", "$FILE"]

    def test_update_existing_formatter_environment(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "ruff": {
                    "environment": {"RUFF_CACHE": "/tmp/cache"},
                }
            }
            m = FormatterManager()
            m.load_from_config()

        ruff = next(f for f in m._formatters if f.name == "ruff")
        assert ruff.environment == {"RUFF_CACHE": "/tmp/cache"}

    def test_update_existing_formatter_with_command(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "ruff": {
                    "command": ["ruff", "check", "--fix", "$FILE"],
                }
            }
            m = FormatterManager()
            m.load_from_config()

        ruff = next(f for f in m._formatters if f.name == "ruff")
        assert ruff.command == ["ruff", "check", "--fix", "$FILE"]

    def test_custom_formatter_missing_command_not_added(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "ghost": {
                    "extensions": [".ghost"],
                }
            }
            m = FormatterManager()
            m.load_from_config()

        names = [f.name for f in m._formatters]
        assert "ghost" not in names
        assert len(m._formatters) == 11

    def test_custom_formatter_missing_extensions_not_added(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = {
                "ghost": {
                    "command": ["ghost", "$FILE"],
                }
            }
            m = FormatterManager()
            m.load_from_config()

        names = [f.name for f in m._formatters]
        assert "ghost" not in names


# ---------------------------------------------------------------------------
# discover_available
# ---------------------------------------------------------------------------


class TestDiscoverAvailable:
    def test_regular_binary(self, manager):
        with patch("apex.formatter.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/ruff"
            manager.discover_available()
            assert manager._available["ruff"] is True

    def test_npx_formatter_checks_node(self, manager):
        def _which_side(binary):
            return "/usr/bin/node" if binary == "node" else None

        with patch("apex.formatter.shutil.which", side_effect=_which_side):
            manager.discover_available()
            assert manager._available["prettier"] is True
            assert manager._available["ruff"] is False

    def test_cargo_formatter(self, manager):
        cargo_fmt = FormatterConfig(
            name="cargo-fmt",
            command=["cargo", "fmt", "--", "$FILE"],
            extensions=[".rs2"],
        )
        manager._formatters.append(cargo_fmt)

        def _which_side(binary):
            return "/usr/bin/cargo" if binary == "cargo" else None

        with patch("apex.formatter.shutil.which", side_effect=_which_side):
            manager.discover_available()
            assert manager._available["cargo-fmt"] is True

    def test_all_unknown_binaries_return_false(self, manager):
        with patch("apex.formatter.shutil.which", return_value=None):
            manager.discover_available()
            assert all(v is False for v in manager._available.values())


# ---------------------------------------------------------------------------
# list_available
# ---------------------------------------------------------------------------


class TestListAvailable:
    def test_returns_only_enabled_and_available(self, manager):
        manager._available = {f.name: True for f in manager._formatters}
        manager._formatters[0].disabled = True

        avail = manager.list_available()
        assert len(avail) == 10
        assert all(not f.disabled for f in avail)

    def test_returns_empty_when_all_disabled(self, manager):
        for f in manager._formatters:
            f.disabled = True
        manager._available = {f.name: True for f in manager._formatters}

        avail = manager.list_available()
        assert avail == []

    def test_returns_empty_when_none_available(self, manager):
        manager._available = {f.name: False for f in manager._formatters}
        avail = manager.list_available()
        assert avail == []

    def test_triggers_load_when_not_loaded(self):
        with patch("apex.config_v2.apex_config") as mock_cfg:
            mock_cfg.formatter = False
            m = FormatterManager()
            assert m._loaded is False
            avail = m.list_available()
            assert m._loaded is True
            assert avail == []


# ---------------------------------------------------------------------------
# _build_command / $FILE placeholder
# ---------------------------------------------------------------------------


class TestFilePlaceholder:
    def test_single_placeholder(self):
        m = FormatterManager()
        fmt = FormatterConfig(
            name="t",
            command=["tool", "$FILE"],
            extensions=[".t"],
        )
        cmd = m._build_command(fmt, "/path/to/file.t")
        assert cmd == ["tool", "/path/to/file.t"]

    def test_multiple_placeholders(self):
        m = FormatterManager()
        fmt = FormatterConfig(
            name="t",
            command=["cp", "$FILE", "$FILE.bak"],
            extensions=[".t"],
        )
        cmd = m._build_command(fmt, "/path/to/file.t")
        assert cmd == ["cp", "/path/to/file.t", "/path/to/file.t.bak"]

    def test_no_placeholder(self):
        m = FormatterManager()
        fmt = FormatterConfig(
            name="t",
            command=["echo", "hello"],
            extensions=[".t"],
        )
        cmd = m._build_command(fmt, "/path/to/file.t")
        assert cmd == ["echo", "hello"]


# ---------------------------------------------------------------------------
# Edge cases: property access, formatters property
# ---------------------------------------------------------------------------


class TestFormatterManagerProperties:
    def test_formatters_property_returns_copy(self):
        m = FormatterManager()
        fmts = m.formatters
        assert len(fmts) == 11
        fmts.clear()
        assert len(m.formatters) == 11

    def test_formatter_manager_initial_state(self):
        m = FormatterManager()
        assert m._loaded is False
        assert m._available == {}
        assert len(m._formatters) == 11
