"""Tests for refactored sandbox module — no mocks, real subprocess."""

from pathlib import Path

from apex.refactored_sandbox import (
    CodeExecutor,
    CodeSandbox,
    ShellSession,
    _check_command_safety,
    create_sandbox,
    create_executor,
    create_shell_session,
    ALLOWED_SHELL_COMMANDS,
    BLOCKED_PATTERNS,
)


class TestCheckCommandSafety:
    def test_allowed_command(self):
        safe, msg = _check_command_safety("echo hello")
        assert safe is True
        assert msg == ""

    def test_disallowed_command(self):
        safe, msg = _check_command_safety("dangerous_cmd arg1")
        assert safe is False
        assert "not allowed" in msg

    def test_blocked_pattern_subshell(self):
        safe, msg = _check_command_safety("echo $(whoami)")
        assert safe is False
        assert "Blocked pattern" in msg

    def test_blocked_pattern_backtick(self):
        safe, msg = _check_command_safety("echo `whoami`")
        assert safe is False
        assert "Blocked pattern" in msg

    def test_blocked_pattern_curly_brace(self):
        safe, msg = _check_command_safety("echo ${var}")
        assert safe is False
        assert "Blocked pattern" in msg

    def test_blocked_pattern_pipe_sh(self):
        safe, msg = _check_command_safety("echo hello | sh")
        assert safe is False

    def test_blocked_pattern_rm_rf(self):
        safe, msg = _check_command_safety("rm -rf /something")
        assert safe is False

    def test_blocked_pattern_chmod_777(self):
        safe, msg = _check_command_safety("chmod 777 file")
        assert safe is False

    def test_blocked_pattern_etc_redirect(self):
        safe, msg = _check_command_safety("echo data > /etc/passwd")
        assert safe is False

    def test_empty_command(self):
        # Empty string: strip().split() gives [], which is falsy,
        # so the code falls through to checking parts[0] which would fail
        # but actually the code checks "if parts and parts[0] not in ALLOWED_SHELL_COMMANDS"
        # Empty parts means this check is skipped, returning True
        safe1, msg1 = _check_command_safety("")
        # For empty string, parts is [] so "if parts and ..." is False
        # Result is (True, "") since no blocked patterns either
        assert safe1 is True  # no blocked patterns, empty command passes

        # Whitespace-only: same behavior
        safe2, msg2 = _check_command_safety("   ")
        assert safe2 is True

    def test_git_allowed(self):
        safe, msg = _check_command_safety("git status")
        assert safe is True

    def test_python3_allowed(self):
        safe, msg = _check_command_safety("python3 -c 'print(1)'")
        assert safe is True

    def test_ls_allowed(self):
        safe, msg = _check_command_safety("ls -la")
        assert safe is True


class TestAllowedCommands:
    def test_common_commands_in_allowlist(self):
        assert "git" in ALLOWED_SHELL_COMMANDS
        assert "python" in ALLOWED_SHELL_COMMANDS
        assert "python3" in ALLOWED_SHELL_COMMANDS
        assert "npm" in ALLOWED_SHELL_COMMANDS
        assert "ls" in ALLOWED_SHELL_COMMANDS
        assert "echo" in ALLOWED_SHELL_COMMANDS

    def test_blocked_patterns_not_empty(self):
        assert len(BLOCKED_PATTERNS) > 0


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

    def test_execute_python_no_output(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("x = 1")
        assert "[OK]" in result

    def test_execute_python_timeout(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_python("import time; time.sleep(100)")
        assert "timed out" in result.lower()

    def test_execute_javascript_success(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_javascript("console.log('hello')")
        assert "hello" in result

    def test_execute_javascript_error(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_javascript("throw new Error('test')")
        assert "ERROR" in result

    def test_execute_javascript_no_output(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_javascript("var x = 1")
        assert "[OK]" in result

    def test_execute_shell_success(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("echo hello")
        assert "hello" in result

    def test_execute_shell_error(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("ls /nonexistent_dir_abc123")
        assert "ERROR" in result

    def test_execute_shell_blocked(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("rm -rf /something")
        assert "ERROR" in result

    def test_execute_shell_no_output(self, tmp_path):
        executor = CodeExecutor(tmp_path)
        result = executor.execute_shell("mkdir test_dir_out")
        if "[OK]" in result:
            # cleanup
            (tmp_path / "test_dir_out").rmdir()


class TestCodeSandbox:
    def test_init_default(self):
        sandbox = CodeSandbox()
        assert sandbox.cwd == Path(".")

    def test_init_with_cwd(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        assert sandbox.cwd == tmp_path

    def test_run_code_python(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("print('test')", "python")
        assert "test" in result

    def test_run_code_javascript(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("console.log('test')", "javascript")
        assert "test" in result

    def test_run_code_shell(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("echo test", "shell")
        assert "test" in result

    def test_run_code_bash(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("echo test", "bash")
        assert "test" in result

    def test_run_code_sh(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("echo test", "sh")
        assert "test" in result

    def test_run_code_unknown_language(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_code("code", "unknown_lang_xyz")
        assert "Unsupported" in result

    def test_run_python_snippet(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_python_snippet("print(1 + 1)")
        assert "2" in result

    def test_run_javascript_snippet(self, tmp_path):
        sandbox = CodeSandbox(str(tmp_path))
        result = sandbox.run_javascript_snippet("console.log(1 + 1)")
        assert "2" in result


class TestShellSession:
    def test_init_default(self):
        session = ShellSession()
        assert session.cwd == Path(".")

    def test_init_with_cwd(self, tmp_path):
        session = ShellSession(str(tmp_path))
        assert session.cwd == tmp_path

    def test_run_success(self, tmp_path):
        session = ShellSession(str(tmp_path))
        result = session.run("echo hello")
        assert "hello" in result

    def test_run_with_cwd(self, tmp_path):
        (tmp_path / "test.txt").write_text("content")
        session = ShellSession(str(tmp_path))
        result = session.run("ls", str(tmp_path))
        assert "test.txt" in result

    def test_run_error(self, tmp_path):
        session = ShellSession(str(tmp_path))
        result = session.run("ls /nonexistent_dir_abc123")
        assert "ERROR" in result

    def test_run_blocked_command(self, tmp_path):
        session = ShellSession(str(tmp_path))
        result = session.run("rm -rf /")
        assert "ERROR" in result

    def test_close(self, tmp_path):
        session = ShellSession(str(tmp_path))
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
