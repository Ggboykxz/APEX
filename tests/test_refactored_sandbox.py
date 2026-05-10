"""Tests for refactored sandbox module."""

from pathlib import Path
from unittest.mock import patch

from apex.refactored_sandbox import (
    CodeExecutor, CodeSandbox, ShellSession,
    create_sandbox, create_executor, create_shell_session
)


class TestCodeExecutor:
    def test_init(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        assert executor.cwd == tmp_path
    
    def test_execute_python_success(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("print('hello')")
        assert "hello" in result
    
    def test_execute_python_with_args(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("import sys; print(sys.argv)", ["arg1"])
        assert "arg1" in result
    
    def test_execute_python_error(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("raise Exception('test')")
        assert "ERROR" in result
    
    def test_execute_python_timeout(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("import time; time.sleep(100)")
        assert "timed out" in result.lower()
    
    def test_execute_python_not_found(self, tmp_path):
        with patch('subprocess.Popen', side_effect=FileNotFoundError):
            executor = CodeExecutor(tmp_path)
            result = executor.execute_python("print(1)")
            assert "not found" in result.lower()
    
    def test_execute_javascript_success(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_javascript("console.log('hello')")
        assert "hello" in result
    
    def test_execute_javascript_error(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_javascript("throw new Error('test')")
        assert "ERROR" in result
    
    def test_execute_shell_success(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("echo hello")
        assert "hello" in result
    
    def test_execute_shell_error(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("exit 1")
        assert "ERROR" in result


class TestCodeSandbox:
    def test_init_default(self):
        sandbox = CodeSandbox()
        assert sandbox.cwd == Path(".")
    
    def test_init_with_cwd(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        assert sandbox.cwd == tmp_path
    
    def test_run_code_python(self):
        sandbox = CodeSandbox()
        result = sandbox.run_code("print('test')", "python")
        assert "test" in result
    
    def test_run_code_javascript(self):
        sandbox = CodeSandbox()
        result = sandbox.run_code("console.log('test')", "javascript")
        assert "test" in result
    
    def test_run_code_shell(self):
        sandbox = CodeSandbox()
        result = sandbox.run_code("echo test", "shell")
        assert "test" in result
    
    def test_run_code_unknown_language(self):
        sandbox = CodeSandbox()
        result = sandbox.run_code("code", "unknown_lang_xyz")
        assert "Unsupported" in result
    
    def test_run_python_snippet(self):
        sandbox = CodeSandbox()
        result = sandbox.run_python_snippet("print(1 + 1)")
        assert "2" in result
    
    def test_run_javascript_snippet(self):
        sandbox = CodeSandbox()
        result = sandbox.run_javascript_snippet("console.log(1 + 1)")
        assert "2" in result


class TestShellSession:
    def test_init_default(self):
        session = ShellSession()
        assert session.cwd == Path(".")
    
    def test_init_with_cwd(self, tmp_path):
        session = ShellSession(str(tmp_path))
        assert session.cwd == tmp_path
    
    def test_run_success(self):
        session = ShellSession()
        result = session.run("echo hello")
        assert "hello" in result
    
    def test_run_with_cwd(self, tmp_path):
        (tmp_path / "test.txt").write_text("content")
        session = ShellSession()
        result = session.run("ls", str(tmp_path))
        assert "test.txt" in result
    
    def test_run_error(self):
        session = ShellSession()
        result = session.run("exit 1")
        assert "ERROR" in result
    
    def test_run_timeout(self):
        session = ShellSession()
        result = session.run("sleep 100")
        assert "timed out" in result.lower()
    
    def test_close(self):
        session = ShellSession()
        session.close()  # Should not raise


class TestFactoryFunctions:
    def test_create_sandbox(self):
        sandbox = create_sandbox()
        assert isinstance(sandbox, CodeSandbox)
    
    def test_create_sandbox_with_cwd(self, tmp_path):
        sandbox = create_sandbox(str(tmp_path))
        assert sandbox.cwd == tmp_path
    
    def test_create_executor(self, tmp_path):
        executor = create_executor(str(tmp_path))
        assert isinstance(executor, CodeExecutor)
        assert executor.cwd == tmp_path
    
    def test_create_shell_session(self):
        session = create_shell_session()
        assert isinstance(session, ShellSession)
    
    def test_create_shell_session_with_cwd(self, tmp_path):
        session = create_shell_session(str(tmp_path))
        assert session.cwd == tmp_path