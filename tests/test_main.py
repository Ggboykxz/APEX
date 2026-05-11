"""Tests for apex/main.py — parse_args and handle_command with real objects."""

import argparse
import pytest
import sys


# ---------------------------------------------------------------------------
# parse_args — we must manipulate sys.argv directly (no mock/patch)
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Test parse_args function with real argument parsing."""

    def test_no_args(self):
        saved = sys.argv
        try:
            sys.argv = ["apex"]
            from apex.main import parse_args

            args = parse_args()
            assert isinstance(args, argparse.Namespace)
            assert args.prompt is None
            assert args.model is None
            assert args.cwd is None
            assert args.list_models is False
            assert args.one_shot is False
            assert args.stream is False
            assert args.auto_commit is False
            assert args.ui is False
            assert args.tui is False
            assert args.prompt_direct is None
            assert args.output_format == "text"
            assert args.quiet is False
        finally:
            sys.argv = saved

    def test_with_prompt(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "hello world"]
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt == "hello world"
        finally:
            sys.argv = saved

    def test_model_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--model", "gpt-4o", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.model == "gpt-4o"
            assert args.prompt == "hello"
        finally:
            sys.argv = saved

    def test_model_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-m", "sonnet", "test"]
            from apex.main import parse_args

            args = parse_args()
            assert args.model == "sonnet"
        finally:
            sys.argv = saved

    def test_cwd_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--cwd", "/tmp"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/tmp"
        finally:
            sys.argv = saved

    def test_cwd_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-C", "/home"]
            from apex.main import parse_args

            args = parse_args()
            assert args.cwd == "/home"
        finally:
            sys.argv = saved

    def test_list_models_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--list-models"]
            from apex.main import parse_args

            args = parse_args()
            assert args.list_models is True
        finally:
            sys.argv = saved

    def test_one_shot_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--one-shot", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.one_shot is True
        finally:
            sys.argv = saved

    def test_one_shot_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-1", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.one_shot is True
        finally:
            sys.argv = saved

    def test_stream_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--stream", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
        finally:
            sys.argv = saved

    def test_stream_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-s", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
        finally:
            sys.argv = saved

    def test_auto_commit_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--auto-commit", "hello"]
            from apex.main import parse_args

            args = parse_args()
            assert args.auto_commit is True
        finally:
            sys.argv = saved

    def test_ui_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--ui"]
            from apex.main import parse_args

            args = parse_args()
            assert args.ui is True
        finally:
            sys.argv = saved

    def test_tui_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--tui"]
            from apex.main import parse_args

            args = parse_args()
            assert args.tui is True
        finally:
            sys.argv = saved

    def test_tui_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-t"]
            from apex.main import parse_args

            args = parse_args()
            assert args.tui is True
        finally:
            sys.argv = saved

    def test_prompt_direct_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-p", "direct prompt"]
            from apex.main import parse_args

            args = parse_args()
            assert args.prompt_direct == "direct prompt"
        finally:
            sys.argv = saved

    def test_format_text(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "text"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "text"
        finally:
            sys.argv = saved

    def test_format_json(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "json"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "json"
        finally:
            sys.argv = saved

    def test_format_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-f", "json"]
            from apex.main import parse_args

            args = parse_args()
            assert args.output_format == "json"
        finally:
            sys.argv = saved

    def test_quiet_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--quiet"]
            from apex.main import parse_args

            args = parse_args()
            assert args.quiet is True
        finally:
            sys.argv = saved

    def test_quiet_short_flag(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-q"]
            from apex.main import parse_args

            args = parse_args()
            assert args.quiet is True
        finally:
            sys.argv = saved

    def test_version_flag_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--version"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_version_short_flag_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "-v"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_invalid_format_exits(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--format", "xml"]
            from apex.main import parse_args

            with pytest.raises(SystemExit):
                parse_args()
        finally:
            sys.argv = saved

    def test_combined_flags(self):
        saved = sys.argv
        try:
            sys.argv = ["apex", "--stream", "--quiet", "-f", "json", "test prompt"]
            from apex.main import parse_args

            args = parse_args()
            assert args.stream is True
            assert args.quiet is True
            assert args.output_format == "json"
            assert args.prompt == "test prompt"
        finally:
            sys.argv = saved
