"""Tests for apex/extras.py — full coverage edge cases."""

import tempfile
import os
from pathlib import Path
from apex.extras import (
    ShellExpander,
    EnvManager,
    WorkspaceValidator,
    SecurityAuditor,
)


class TestShellExpanderFull:
    def test_multiple_vars(self):
        os.environ["APEX_VAR_A"] = "alpha"
        os.environ["APEX_VAR_B"] = "beta"
        result = ShellExpander.expand("$APEX_VAR_A and $APEX_VAR_B")
        assert result == "alpha and beta"
        del os.environ["APEX_VAR_A"]
        del os.environ["APEX_VAR_B"]

    def test_expand_path_with_vars(self):
        os.environ["APEX_BASE_DIR"] = "/tmp"
        result = ShellExpander.expand_path("$APEX_BASE_DIR/subdir")
        assert result == "/tmp/subdir"
        del os.environ["APEX_BASE_DIR"]

    def test_expand_command_just_text(self):
        result = ShellExpander.expand_command("echo hello")
        assert result == "echo hello"


class TestEnvManagerFull:
    def test_save_and_load_roundtrip(self, tmp_path):
        mgr1 = EnvManager(str(tmp_path))
        mgr1.set("KEY_A", "val_a")
        mgr1.set("KEY_B", "val_b")
        mgr1.save_to_file()

        mgr2 = EnvManager(str(tmp_path))
        mgr2.load_from_file()
        assert mgr2.get("KEY_A") == "val_a"
        assert mgr2.get("KEY_B") == "val_b"

    def test_list_includes_both_envs(self, tmp_path):
        mgr = EnvManager(str(tmp_path))
        mgr.set("LOCAL_ONLY", "local")
        result = mgr.list()
        assert "LOCAL_ONLY" in result
        assert "PATH" in result


class TestWorkspaceValidatorFull:
    def test_validate_multiple_rules(self, tmp_path):
        wv = WorkspaceValidator(str(tmp_path))
        Path(tmp_path, "README.md").write_text("# Test")
        wv.add_rule("has_readme", lambda c: (c / "README.md").exists(), "No README")
        wv.add_rule("has_tests", lambda c: (c / "tests").exists(), "No tests dir")
        result = wv.validate()
        assert "has_readme" in result["passed"]
        assert len(result["failed"]) == 1

    def test_validate_config_with_apex_yaml(self, tmp_path):
        Path(tmp_path, ".apex.yaml").write_text("test: true")
        Path(tmp_path, "test.py").write_text("print('hi')")
        Path(tmp_path, ".git").mkdir()
        wv = WorkspaceValidator(str(tmp_path))
        result = wv.validate_config()
        assert result["valid"] is True
        assert result["issues"] == []


class TestSecurityAuditorFull:
    def test_audit_file_os_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("os.system('rm -rf /')")
            issues = sa.audit_file(test_file)
            assert any("os.system" in i["message"].lower() for i in issues)

    def test_audit_file_pickle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("pickle.load(f)")
            issues = sa.audit_file(test_file)
            assert any(
                "unpickling" in i["message"].lower() or "pickle" in i["message"].lower()
                for i in issues
            )

    def test_audit_file_yaml_unsafe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("yaml.load(data, Loader=None)")
            issues = sa.audit_file(test_file)
            assert any("yaml" in i["message"].lower() for i in issues)

    def test_audit_file_hardcoded_secret(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sa = SecurityAuditor(tmpdir)
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('secret = "my_secret_value"')
            issues = sa.audit_file(test_file)
            assert any("secret" in i["message"].lower() for i in issues)

    def test_audit_project_nested(self, tmp_path):
        sa = SecurityAuditor(str(tmp_path))
        subdir = tmp_path / "sub"
        subdir.mkdir()
        Path(subdir, "bad.py").write_text("eval('test')")
        results = sa.audit_project()
        assert results["total_issues"] > 0
