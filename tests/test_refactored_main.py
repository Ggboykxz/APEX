"""Tests for refactored main module — no mocks, real operations."""

from argparse import Namespace
from pathlib import Path

import os

import pytest

from apex.refactored_main import (
    create_parser,
    list_available_models,
    validate_model,
    get_working_directory,
)


class TestCreateParser:
    def test_create_parser(self):
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "apex"

    def test_parse_no_args(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.prompt is None
        assert args.model is None

    def test_parse_with_prompt(self):
        parser = create_parser()
        args = parser.parse_args(["test prompt"])
        assert args.prompt == "test prompt"

    def test_parse_with_model(self):
        parser = create_parser()
        args = parser.parse_args(["--model", "claude-4-sonnet", "test"])
        assert args.model == "claude-4-sonnet"

    def test_parse_list_models_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--list-models"])
        assert args.list_models is True

    def test_parse_no_stream_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--no-stream", "test"])
        assert args.no_stream is True

    def test_parse_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(["-v", "test"])
        assert args.verbose is True

    def test_parse_verbose_long_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--verbose", "test"])
        assert args.verbose is True


class TestListAvailableModels:
    def test_list_models(self, capsys):
        list_available_models()
        captured = capsys.readouterr()
        assert "Available models:" in captured.out


class TestValidateModel:
    @pytest.mark.skipif(
        bool(os.environ.get("CI")),
        reason="Requires API keys / running services not available in CI",
    )
    def test_validate_valid_model(self):
        result = validate_model("claude-4-sonnet")
        assert result is True

    def test_validate_invalid_model(self):
        result = validate_model("nonexistent-model-xyz")
        assert result is False


class TestGetWorkingDirectory:
    def test_get_cwd_default(self):
        args = Namespace(cwd=None)
        result = get_working_directory(args)
        assert result == Path.cwd()

    def test_get_cwd_from_args(self):
        args = Namespace(cwd="/tmp/test")
        result = get_working_directory(args)
        assert result == Path("/tmp/test")

    def test_get_cwd_empty_string(self):
        args = Namespace(cwd="")
        result = get_working_directory(args)
        assert result == Path.cwd()

    def test_get_cwd_no_attr(self):
        args = Namespace()
        result = get_working_directory(args)
        assert result == Path.cwd()
