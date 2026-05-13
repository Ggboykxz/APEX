"""Tests for apex/sandbox.py — CodeSandbox, ShellSession."""
import os
import subprocess
import time as time_module
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apex.sandbox import CodeSandbox, ShellSession, sandbox


class TestCodeSandbox:
    def test_init(self):
        sb = CodeSandbox(timeout=10, max_output=1000)
        assert sb.timeout == 10
        assert sb.max_output == 1000

    def test_init_creates_temp_dir(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox()
            expected = tmp_path / "apex_sandbox"
            assert expected.exists()
            mode = os.stat(expected).st_mode
            assert mode & 0o700 == 0o700

    def test_languages_supported(self):
        sb = CodeSandbox()
        assert "python" in sb.LANGUAGES
        assert "javascript" in sb.LANGUAGES
        assert "bash" in sb.LANGUAGES
        assert "ruby" in sb.LANGUAGES
        assert "go" in sb.LANGUAGES
        assert "rust" in sb.LANGUAGES

    def test_unsupported_language(self):
        sb = CodeSandbox()
        result = sb.run_code("print('hi')", language="cobol")
        assert "ERROR" in result
        assert "Unsupported" in result

    def test_run_code_success(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="hello world\n", stderr="", returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("print('hello')")
                assert "hello world" in result

    def test_run_code_with_stderr(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="", stderr="some error\n", returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("bad_code()")
                assert "[STDERR]" in result
                assert "some error" in result

    def test_run_code_nonzero_exit(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="", stderr="", returncode=2)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("exit(2)")
                assert "[EXIT CODE: 2]" in result

    def test_run_code_no_output(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="", stderr="", returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("x = 1")
                assert "[no output]" in result

    def test_run_code_with_args(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="", stderr="", returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result) as mock_run:
                sb.run_code("import sys; print(sys.argv)", args=["--verbose"])
                cmd = mock_run.call_args[0][0]
                assert "--verbose" in cmd

    def test_run_code_timeout(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            with patch(
                "apex.sandbox.subprocess.run",
                side_effect=subprocess.TimeoutExpired("cmd", 10),
            ):
                result = sb.run_code("print('hi')")
                assert "timed out" in result

    def test_run_code_file_not_found(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            with patch("apex.sandbox.subprocess.run", side_effect=FileNotFoundError()):
                result = sb.run_code("print('hi')")
                assert "not found" in result

    def test_run_code_generic_exception(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            with patch(
                "apex.sandbox.subprocess.run",
                side_effect=PermissionError("denied"),
            ):
                result = sb.run_code("print('hi')")
                assert "ERROR" in result
                assert "denied" in result

    def test_run_code_max_output_truncation(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10, max_output=10)
            mock_result = MagicMock(stdout="a" * 100, stderr="b" * 100, returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("print('a'*100)")
                assert ("a" * 11) not in result
                assert ("b" * 11) not in result
                assert ("a" * 10) in result
                assert ("b" * 10) in result

    def test_run_code_rust_success(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_compile = MagicMock(stdout="", stderr="", returncode=0)
            mock_run = MagicMock(stdout="hello rust\n", stderr="", returncode=0)
            with patch(
                "apex.sandbox.subprocess.run",
                side_effect=[mock_compile, mock_run],
            ):
                result = sb.run_code(
                    'fn main() { println!("hello rust"); }', language="rust"
                )
                assert "hello rust" in result

    def test_run_code_rust_compile_error(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="", stderr="syntax error\n", returncode=1)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                result = sb.run_code("bad rust code", language="rust")
                assert "Compilation failed" in result

    def test_cleanup_on_success(self, tmp_path):
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            sb = CodeSandbox(timeout=10)
            mock_result = MagicMock(stdout="ok\n", stderr="", returncode=0)
            with patch("apex.sandbox.subprocess.run", return_value=mock_result):
                sb.run_code("print('hi')")
            files = list(sb._temp_dir.iterdir())
            assert len(files) == 0

    def test_cleanup_rust_binary(self, tmp_path):
        known_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            with patch("apex.sandbox.uuid.uuid4", return_value=known_uuid):
                sb = CodeSandbox(timeout=10)
                binary_path = sb._temp_dir / "12345678_binary"
                binary_path.touch()
                mock_compile = MagicMock(stdout="", stderr="", returncode=0)
                mock_run = MagicMock(stdout="ok\n", stderr="", returncode=0)
                with patch(
                    "apex.sandbox.subprocess.run",
                    side_effect=[mock_compile, mock_run],
                ):
                    sb.run_code("fn main(){}", language="rust")
                files = list(sb._temp_dir.iterdir())
                assert len(files) == 0

    def test_cleanup_file_already_deleted(self, tmp_path):
        known_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        with patch("apex.sandbox.tempfile.gettempdir", return_value=str(tmp_path)):
            with patch("apex.sandbox.uuid.uuid4", return_value=known_uuid):
                sb = CodeSandbox(timeout=10)
                mock_result = MagicMock(stdout="", stderr="", returncode=0)

                def _side_effect(*args, **kwargs):
                    file_path = sb._temp_dir / "12345678.py"
                    if file_path.exists():
                        file_path.unlink()
                    return mock_result

                with patch("apex.sandbox.subprocess.run", side_effect=_side_effect):
                    result = sb.run_code("print('hi')")
                    assert "[no output]" in result

    def test_run_python_snippet(self):
        sb = CodeSandbox(timeout=10)
        with patch.object(sb, "run_code", return_value="ok") as mock_run:
            result = sb.run_python_snippet("print('test')")
            assert result == "ok"
            mock_run.assert_called_once_with("print('test')", "python")

    def test_run_javascript_snippet(self):
        sb = CodeSandbox(timeout=10)
        with patch.object(sb, "run_code", return_value="ok") as mock_run:
            result = sb.run_javascript_snippet("console.log('test')")
            assert result == "ok"
            mock_run.assert_called_once_with("console.log('test')", "javascript")


class TestShellSession:
    def test_init_defaults(self):
        ss = ShellSession()
        assert ss.cwd == Path.cwd()
        assert ss.env == os.environ.copy()
        assert ss.process is None

    def test_init_custom(self, tmp_path):
        env = {"CUSTOM": "value"}
        ss = ShellSession(cwd=tmp_path, env=env)
        assert ss.cwd == tmp_path
        assert ss.env == env
        assert ss.process is None

    def test_start_success(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        with patch("apex.sandbox.subprocess.Popen", return_value=mock_process):
            result = ss.start()
            assert result is True
            assert ss.process is mock_process
            ss.close()

    def test_start_failure(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        with patch("apex.sandbox.subprocess.Popen", side_effect=OSError("no bash")):
            result = ss.start()
            assert result is False
            assert ss.process is None

    def test_run_not_started(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        result = ss.run("echo hello")
        assert "ERROR" in result
        assert "not started" in result

    def test_run_success(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.readline.side_effect = ["line1", "line2", ""]
        mock_process.stdout = mock_stdout
        ss.process = mock_process
        result = ss.run("echo hello", timeout=5)
        assert "line1" in result
        assert "line2" in result
        mock_process.stdin.write.assert_called_once_with("echo hello\n")
        mock_process.stdin.flush.assert_called_once()

    def test_run_no_output(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = ""
        mock_process.stdout = mock_stdout
        ss.process = mock_process
        result = ss.run("echo hello", timeout=5)
        assert "[no output]" in result

    def test_run_timeout_exit(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.readline.return_value = "still running"
        mock_process.stdout = mock_stdout
        ss.process = mock_process
        with patch.object(time_module, "time", side_effect=[0, 1, 31]):
            result = ss.run("echo hello", timeout=30)
        assert "still running" in result

    def test_run_exception(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.write.side_effect = OSError("broken pipe")
        ss.process = mock_process
        result = ss.run("echo hello", timeout=5)
        assert "ERROR" in result
        assert "broken pipe" in result

    def test_close_normal(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        ss.process = mock_process
        ss.close()
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_close_kill_on_timeout(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        mock_process = MagicMock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired("bash", 5)
        ss.process = mock_process
        ss.close()
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        mock_process.kill.assert_called_once()

    def test_close_no_process(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        ss.close()


class TestGlobalInstance:
    def test_sandbox_singleton(self):
        assert isinstance(sandbox, CodeSandbox)
