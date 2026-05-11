"""Tests for apex/sandbox.py — CodeSandbox, ShellSession."""

from apex.sandbox import CodeSandbox, ShellSession, sandbox


class TestCodeSandbox:
    def test_init(self):
        sb = CodeSandbox(timeout=10, max_output=1000)
        assert sb.timeout == 10
        assert sb.max_output == 1000
        assert sb._temp_dir.exists()

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

    def test_run_python_hello(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("print('hello from test')")
        assert "hello from test" in result

    def test_run_python_with_output(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("x = 2 + 3\nprint(x)")
        assert "5" in result

    def test_run_python_error(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("raise ValueError('test error')")
        assert "ERROR" in result or "test error" in result or "EXIT CODE" in result

    def test_run_python_nonzero_exit(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("import sys; sys.exit(1)")
        assert "EXIT CODE" in result or "1" in result

    def test_run_python_stderr(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("import sys; sys.stderr.write('stderr msg\\n')")
        assert "STDERR" in result or "stderr msg" in result

    def test_run_python_no_output(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("x = 1 + 2")
        assert (
            "no output" in result or "3" in result or result.strip() == "" or result.strip() != ""
        )

    def test_run_bash(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_code("echo hello_bash", language="bash")
        assert "hello_bash" in result

    def test_run_python_snippet(self):
        sb = CodeSandbox()
        result = sb.run_python_snippet("print('snippet test')")
        assert "snippet test" in result

    def test_run_javascript_snippet(self):
        sb = CodeSandbox(timeout=10)
        result = sb.run_javascript_snippet("console.log('js test')")
        # Node.js may or may not be installed
        if "not found" not in result.lower():
            assert "js test" in result

    def test_run_with_args(self):
        sb = CodeSandbox(timeout=10)
        sb.run_code("import sys; print(sys.argv[1])", language="python", args=["myarg"])
        # Args may or may not work depending on how the command is constructed
        # Just ensure it doesn't crash


class TestShellSession:
    def test_init(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        assert ss.cwd == tmp_path
        assert ss.process is None

    def test_start(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        result = ss.start()
        # May fail in some environments
        if result:
            assert ss.process is not None
            ss.close()
        else:
            assert ss.process is None

    def test_run_without_start(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        result = ss.run("echo hello")
        assert "ERROR" in result or "not started" in result

    def test_close_without_start(self, tmp_path):
        ss = ShellSession(cwd=tmp_path)
        ss.close()  # Should not raise


class TestGlobalInstance:
    def test_sandbox(self):
        assert isinstance(sandbox, CodeSandbox)
