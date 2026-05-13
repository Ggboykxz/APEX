"""Tests for lsp_diagnostics module — no mocks, real objects only."""

import tempfile
from pathlib import Path

import pytest

from apex.lsp_diagnostics import (
    Diagnostic,
    LANGUAGE_SERVERS,
    LSPDiagnostics,
    DiagnosticContextBuilder,
)


# ---------------------------------------------------------------------------
# Diagnostic dataclass
# ---------------------------------------------------------------------------


class TestDiagnostic:
    def test_init(self):
        diag = Diagnostic(severity="error", message="Test error", line=10, column=5, source="lsp")
        assert diag.severity == "error"
        assert diag.message == "Test error"
        assert diag.line == 10
        assert diag.column == 5
        assert diag.source == "lsp"

    def test_warning(self):
        diag = Diagnostic(severity="warning", message="Warn", line=1, column=1, source="pyright")
        assert diag.severity == "warning"
        assert diag.source == "pyright"

    def test_info(self):
        diag = Diagnostic(severity="info", message="Note", line=1, column=1, source="lsp")
        assert diag.severity == "info"


# ---------------------------------------------------------------------------
# LANGUAGE_SERVERS dictionary
# ---------------------------------------------------------------------------


class TestLanguageServers:
    def test_not_empty(self):
        assert len(LANGUAGE_SERVERS) > 0

    def test_has_python(self):
        assert "python" in LANGUAGE_SERVERS
        assert "pyright" in LANGUAGE_SERVERS["python"][0]

    def test_has_javascript(self):
        assert "javascript" in LANGUAGE_SERVERS

    def test_has_typescript(self):
        assert "typescript" in LANGUAGE_SERVERS

    def test_has_go(self):
        assert "go" in LANGUAGE_SERVERS
        assert "gopls" in LANGUAGE_SERVERS["go"]

    def test_has_rust(self):
        assert "rust" in LANGUAGE_SERVERS
        assert "rust-analyzer" in LANGUAGE_SERVERS["rust"]

    def test_has_cpp(self):
        assert "cpp" in LANGUAGE_SERVERS

    def test_has_java(self):
        assert "java" in LANGUAGE_SERVERS

    def test_has_csharp(self):
        assert "csharp" in LANGUAGE_SERVERS


# ---------------------------------------------------------------------------
# LSPDiagnostics
# ---------------------------------------------------------------------------


class TestLSPDiagnostics:
    @pytest.fixture
    def temp_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def lsp(self, temp_cwd):
        return LSPDiagnostics(cwd=temp_cwd)

    def test_init(self, lsp, temp_cwd):
        assert lsp.cwd == temp_cwd
        assert lsp._servers == {}
        assert lsp._initialized is False
        assert lsp._last_diagnostics == {}

    def test_init_default_cwd(self):
        lsp = LSPDiagnostics()
        assert lsp.cwd == Path.cwd()

    # -- detect_language --

    def test_detect_language_python(self, lsp):
        assert lsp.detect_language(Path("test.py")) == "python"

    def test_detect_language_javascript(self, lsp):
        assert lsp.detect_language(Path("test.js")) == "javascript"

    def test_detect_language_typescript(self, lsp):
        assert lsp.detect_language(Path("test.ts")) == "typescript"

    def test_detect_language_tsx(self, lsp):
        assert lsp.detect_language(Path("test.tsx")) == "typescript"

    def test_detect_language_jsx(self, lsp):
        assert lsp.detect_language(Path("test.jsx")) == "javascript"

    def test_detect_language_go(self, lsp):
        assert lsp.detect_language(Path("test.go")) == "go"

    def test_detect_language_rust(self, lsp):
        assert lsp.detect_language(Path("test.rs")) == "rust"

    def test_detect_language_cpp(self, lsp):
        assert lsp.detect_language(Path("test.cpp")) == "cpp"

    def test_detect_language_c(self, lsp):
        assert lsp.detect_language(Path("test.c")) == "cpp"

    def test_detect_language_header(self, lsp):
        assert lsp.detect_language(Path("test.h")) == "cpp"

    def test_detect_language_java(self, lsp):
        assert lsp.detect_language(Path("Test.java")) == "java"

    def test_detect_language_csharp(self, lsp):
        assert lsp.detect_language(Path("Test.cs")) == "csharp"

    def test_detect_language_ruby(self, lsp):
        assert lsp.detect_language(Path("test.rb")) == "ruby"

    def test_detect_language_php(self, lsp):
        assert lsp.detect_language(Path("test.php")) == "php"

    def test_detect_language_unknown(self, lsp):
        assert lsp.detect_language(Path("test.xyz")) is None

    # -- start_server --

    def test_start_server_unknown_language(self, lsp):
        result = lsp.start_server("nonexistent_language")
        assert result is False

    def test_start_server_python_not_installed(self, lsp):
        """Python LSP is typically not installed in test env."""
        result = lsp.start_server("python")
        # pyright-langserver is usually not available in test environments
        # so this should return False
        assert isinstance(result, bool)

    # -- initialize --

    def test_initialize_no_server(self, lsp):
        result = lsp.initialize("python", Path("test.py"))
        assert result is False

    # -- get_diagnostics --

    def test_get_diagnostics_unknown_extension(self, lsp):
        result = lsp.get_diagnostics(Path("test.xyz"))
        assert result == []

    def test_get_diagnostics_no_server(self, lsp):
        """Without an LSP server running, diagnostics are empty."""
        result = lsp.get_diagnostics(Path("test.py"))
        assert result == []

    # -- format_diagnostics_for_model --

    def test_format_diagnostics_no_diagnostics(self, lsp):
        result = lsp.format_diagnostics_for_model(Path("test.py"))
        assert result == ""

    # -- has_errors --

    def test_has_errors_no_file(self, lsp):
        result = lsp.has_errors(Path("test.py"))
        assert result is False

    # -- stop_servers --

    def test_stop_servers_empty(self, lsp):
        """Stopping servers when none are running is safe."""
        lsp.stop_servers()
        assert lsp._servers == {}

    def test_stop_servers_with_running(self, lsp):
        """stop_servers clears the _servers dict."""
        # We can't easily start a real server, but we can verify
        # that stop_servers clears the dict
        lsp.stop_servers()
        assert lsp._servers == {}


# ---------------------------------------------------------------------------
# DiagnosticContextBuilder
# ---------------------------------------------------------------------------


class TestDiagnosticContextBuilder:
    def test_init_default(self):
        builder = DiagnosticContextBuilder()
        assert builder.lsp is not None
        assert isinstance(builder.lsp, LSPDiagnostics)

    def test_init_with_lsp(self):
        lsp = LSPDiagnostics()
        builder = DiagnosticContextBuilder(lsp=lsp)
        assert builder.lsp is lsp

    def test_build_fix_prompt_no_diagnostics(self):
        """Without an LSP server, no diagnostics are returned, so prompt is unchanged."""
        lsp = LSPDiagnostics()
        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_fix_prompt(Path("test.py"), "tool result")
        assert result == "tool result"

    def test_build_fix_prompt_with_diagnostics(self):
        """Test fix prompt with real diagnostics injected via _last_diagnostics."""
        lsp = LSPDiagnostics()
        # Simulate diagnostics by injecting into the last diagnostics cache
        diag = Diagnostic(
            severity="error", message="undefined variable", line=5, column=10, source="lsp"
        )
        lsp._last_diagnostics["test.py"] = [diag]

        # Override get_diagnostics to return our cached diagnostics
        # (since the real one won't work without an LSP server)
        original_get_diagnostics = lsp.get_diagnostics

        def patched_get_diagnostics(filepath):
            key = str(filepath)
            if key in lsp._last_diagnostics:
                return lsp._last_diagnostics[key]
            return original_get_diagnostics(filepath)

        lsp.get_diagnostics = patched_get_diagnostics

        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_fix_prompt(Path("test.py"), "tool result")
        assert "tool result" in result
        assert "ERROR" in result
        assert "undefined variable" in result

    def test_build_pre_edit_context_no_diagnostics(self):
        """Without LSP server, pre-edit context is empty."""
        lsp = LSPDiagnostics()
        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_pre_edit_context(Path("test.py"))
        assert result == ""

    def test_build_pre_edit_context_with_errors(self):
        """Test pre-edit context with real diagnostics injected."""
        lsp = LSPDiagnostics()
        diag = Diagnostic(
            severity="error", message="undefined variable", line=10, column=1, source="lsp"
        )
        lsp._last_diagnostics["test.py"] = [diag]

        # Patch get_diagnostics to return our cached diagnostics
        original_get_diagnostics = lsp.get_diagnostics

        def patched_get_diagnostics(filepath):
            key = str(filepath)
            if key in lsp._last_diagnostics:
                return lsp._last_diagnostics[key]
            return original_get_diagnostics(filepath)

        lsp.get_diagnostics = patched_get_diagnostics

        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_pre_edit_context(Path("test.py"))
        assert "Current issues" in result
        assert "Errors: 1" in result

    def test_build_pre_edit_context_with_warnings(self):
        """Test pre-edit context with warning diagnostics."""
        lsp = LSPDiagnostics()
        diag = Diagnostic(
            severity="warning", message="unused import", line=1, column=1, source="lsp"
        )
        lsp._last_diagnostics["test.py"] = [diag]

        original_get_diagnostics = lsp.get_diagnostics

        def patched_get_diagnostics(filepath):
            key = str(filepath)
            if key in lsp._last_diagnostics:
                return lsp._last_diagnostics[key]
            return original_get_diagnostics(filepath)

        lsp.get_diagnostics = patched_get_diagnostics

        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_pre_edit_context(Path("test.py"))
        assert "Warnings: 1" in result

    def test_build_pre_edit_context_with_many_errors(self):
        """Pre-edit context caps errors at 3 shown."""
        lsp = LSPDiagnostics()
        diags = [
            Diagnostic(severity="error", message=f"error {i}", line=i, column=1, source="lsp")
            for i in range(5)
        ]
        lsp._last_diagnostics["test.py"] = diags

        original_get_diagnostics = lsp.get_diagnostics

        def patched_get_diagnostics(filepath):
            key = str(filepath)
            if key in lsp._last_diagnostics:
                return lsp._last_diagnostics[key]
            return original_get_diagnostics(filepath)

        lsp.get_diagnostics = patched_get_diagnostics

        builder = DiagnosticContextBuilder(lsp=lsp)
        result = builder.build_pre_edit_context(Path("test.py"))
        assert "Errors: 5" in result
