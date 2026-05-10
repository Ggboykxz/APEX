"""Tests for refactored main module."""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from apex.refactored_main import (
    create_parser,
    list_available_models,
    validate_model,
    get_working_directory,
    run_non_interactive,
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


class TestListAvailableModels:
    def test_list_models(self, capsys):
        list_available_models()
        captured = capsys.readouterr()
        assert "Available models:" in captured.out
        assert "claude-4-sonnet" in captured.out


class TestValidateModel:
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


class TestRunNonInteractive:
    def test_run_with_agent(self, tmp_path):
        with patch('apex.agent.Agent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.run.return_value = "Test response"
            
            with patch('apex.ui.UI') as MockUI:
                mock_ui = MockUI.return_value
                
                run_non_interactive("test prompt", tmp_path, model="claude-4-sonnet", stream=False, verbose=False)
                
                MockAgent.assert_called_once()
                mock_agent.run.assert_called_once_with("test prompt")
    
    def test_run_with_verbose(self, tmp_path, capsys):
        with patch('apex.agent.Agent') as MockAgent:
            mock_agent = MockAgent.return_value
            mock_agent.run.return_value = "Test response"
            
            with patch('apex.ui.UI'):
                run_non_interactive("test prompt", tmp_path, verbose=True)
                
                captured = capsys.readouterr()
                assert "test prompt" in captured.out