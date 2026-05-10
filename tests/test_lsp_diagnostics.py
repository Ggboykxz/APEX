"""Tests for lsp_diagnostics module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from apex.lsp_diagnostics import (
    Diagnostic,
    LANGUAGE_SERVERS,
    LSPDiagnostics,
    DiagnosticContextBuilder,
)


class TestDiagnostic:
    """Test Diagnostic dataclass."""

    def test_init(self):
        """Test initialization."""
        diag = Diagnostic(severity="error", message="Test error", line=10, column=5, source="lsp")
        assert diag.severity == "error"
        assert diag.message == "Test error"
        assert diag.line == 10
        assert diag.column == 5
        assert diag.source == "lsp"


class TestLanguageServers:
    """Test LANGUAGE_SERVERS dictionary."""

    def test_not_empty(self):
        """Test servers dictionary is not empty."""
        assert len(LANGUAGE_SERVERS) > 0

    def test_has_python(self):
        """Test Python LSP exists."""
        assert "python" in LANGUAGE_SERVERS
        assert "pyright" in LANGUAGE_SERVERS["python"][0]

    def test_has_javascript(self):
        """Test JavaScript LSP exists."""
        assert "javascript" in LANGUAGE_SERVERS

    def test_has_go(self):
        """Test Go LSP exists."""
        assert "go" in LANGUAGE_SERVERS
        assert "gopls" in LANGUAGE_SERVERS["go"]

    def test_has_rust(self):
        """Test Rust LSP exists."""
        assert "rust" in LANGUAGE_SERVERS
        assert "rust-analyzer" in LANGUAGE_SERVERS["rust"]


class TestLSPDiagnostics:
    """Test LSPDiagnostics class."""

    @pytest.fixture
    def temp_cwd(self):
        """Create temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def lsp(self, temp_cwd):
        """Create LSPDiagnostics instance."""
        return LSPDiagnostics(cwd=temp_cwd)

    def test_init(self, lsp, temp_cwd):
        """Test initialization."""
        assert lsp.cwd == temp_cwd
        assert lsp._servers == {}
        assert lsp._initialized is False
        assert lsp._last_diagnostics == {}

    def test_detect_language_python(self, lsp):
        """Test Python detection."""
        lang = lsp.detect_language(Path("test.py"))
        assert lang == "python"

    def test_detect_language_javascript(self, lsp):
        """Test JavaScript detection."""
        lang = lsp.detect_language(Path("test.js"))
        assert lang == "javascript"

    def test_detect_language_typescript(self, lsp):
        """Test TypeScript detection."""
        lang = lsp.detect_language(Path("test.ts"))
        assert lang == "typescript"

    def test_detect_language_unknown(self, lsp):
        """Test unknown extension."""
        lang = lsp.detect_language(Path("test.xyz"))
        assert lang is None

    def test_start_server_not_found(self, lsp):
        """Test start_server when command not found."""
        result = lsp.start_server("nonexistent_language")
        assert result is False

    def test_start_server_python_not_found(self, lsp):
        """Test start_server for Python when not installed."""
        result = lsp.start_server("python")
        assert result is False

    def test_initialize_no_server(self, lsp):
        """Test initialize without starting server."""
        result = lsp.initialize("python", Path("test.py"))
        assert result is False

    def test_get_diagnostics_no_language(self, lsp):
        """Test get_diagnostics with unknown file."""
        result = lsp.get_diagnostics(Path("test.xyz"))
        assert result == []

    def test_get_diagnostics_no_server(self, lsp):
        """Test get_diagnostics without server."""
        result = lsp.get_diagnostics(Path("test.py"))
        assert result == []

    def test_has_errors_no_file(self, lsp):
        """Test has_errors with no file."""
        result = lsp.has_errors(Path("test.py"))
        assert result is False

    def test_stop_servers(self, lsp):
        """Test stop_servers method."""
        lsp._servers["python"] = {"process": MagicMock()}
        lsp.stop_servers()
        assert lsp._servers == {}


class TestDiagnosticContextBuilder:
    """Test DiagnosticContextBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create builder instance."""
        return DiagnosticContextBuilder()

    @pytest.fixture
    def builder_with_lsp(self):
        """Create builder with mock LSP."""
        mock_lsp = MagicMock()
        mock_lsp.get_diagnostics.return_value = []
        return DiagnosticContextBuilder(lsp=mock_lsp)

    def test_init_default(self):
        """Test initialization with defaults."""
        builder = DiagnosticContextBuilder()
        assert builder.lsp is not None

    def test_init_with_lsp(self):
        """Test initialization with custom LSP."""
        mock_lsp = MagicMock()
        builder = DiagnosticContextBuilder(lsp=mock_lsp)
        assert builder.lsp is mock_lsp

    def test_build_fix_prompt_no_diagnostics(self):
        """Test build_fix_prompt with no diagnostics."""
        mock_lsp = MagicMock()
        mock_lsp.format_diagnostics_for_model.return_value = ""
        builder = DiagnosticContextBuilder(lsp=mock_lsp)

        result = builder.build_fix_prompt(Path("test.py"), "tool result")
        assert result == "tool result"

    def test_build_fix_prompt_with_diagnostics(self):
        """Test build_fix_prompt with diagnostics."""
        mock_lsp = MagicMock()
        mock_lsp.format_diagnostics_for_model.return_value = "Error at line 5"
        builder = DiagnosticContextBuilder(lsp=mock_lsp)

        result = builder.build_fix_prompt(Path("test.py"), "tool result")
        assert "tool result" in result
        assert "Error at line 5" in result

    def test_build_pre_edit_context_empty(self, builder_with_lsp):
        """Test build_pre_edit_context with no diagnostics."""
        mock_lsp = builder_with_lsp.lsp
        mock_lsp.get_diagnostics.return_value = []

        result = builder_with_lsp.build_pre_edit_context(Path("test.py"))
        assert result == ""

    def test_build_pre_edit_context_with_errors(self, builder_with_lsp):
        """Test build_pre_edit_context with diagnostics."""
        mock_diag = MagicMock()
        mock_diag.severity = "error"
        mock_diag.message = "undefined variable"
        mock_diag.line = 10

        mock_lsp = builder_with_lsp.lsp
        mock_lsp.get_diagnostics.return_value = [mock_diag]

        result = builder_with_lsp.build_pre_edit_context(Path("test.py"))
        assert "Current issues" in result
        assert "Errors: 1" in result
