"""Refactored main module - More testable CLI and logic separation."""

import argparse
import sys
from pathlib import Path
from typing import Optional


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser - testable."""
    parser = argparse.ArgumentParser(
        prog="apex",
        description="The last coding agent you'll ever need"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Initial prompt or task"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (overrides config)"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming responses"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models"
    )
    return parser


def list_available_models() -> None:
    """List all available models."""
    from apex.config import MODELS, MODEL_PROVIDERS
    print("Available models:")
    for model, provider in MODELS.items():
        provider_name = MODEL_PROVIDERS.get(model, "Unknown")
        print(f"  - {model} ({provider_name})")


def validate_model(model: str) -> bool:
    """Validate that a model is available."""
    from apex.config import MODELS
    return model in MODELS


def get_working_directory(args: argparse.Namespace) -> Path:
    """Get the working directory from args."""
    if hasattr(args, 'cwd') and args.cwd:
        return Path(args.cwd)
    return Path.cwd()


def create_agent(prompt: str, cwd: Path, model: Optional[str] = None):
    """Create and run an agent - testable factory."""
    from apex.agent import Agent
    return Agent(cwd=str(cwd), prompt=prompt, model=model)


def interactive_loop(agent):
    """Run the interactive loop - testable."""
    from apex.ui import UI
    
    ui = UI()
    print("Welcome to APEX! Type /help for commands, /exit to quit.")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                if user_input == "/exit" or user_input == "/quit":
                    break
                elif user_input == "/help":
                    ui.show_help()
                elif user_input == "/clear":
                    print("\033[2J\033[H")
                else:
                    print(f"Unknown command: {user_input}")
                continue
            
            response = agent.run(user_input)
            if response:
                ui.print_response(response)
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break


def run_non_interactive(prompt: str, cwd: Path, model: Optional[str] = None, stream: bool = True, verbose: bool = False):
    """Run in non-interactive mode - testable."""
    from apex.agent import Agent
    from apex.ui import UI
    
    ui = UI()
    agent = Agent(cwd=str(cwd), model=model)
    
    if verbose:
        print(f"Running prompt: {prompt}")
    
    response = agent.run(prompt)
    
    if response:
        ui.print_response(response)


def main_entry():
    """Main entry point - refactored for testability."""
    args = create_parser().parse_args()
    
    if args.list_models:
        list_available_models()
        return 0
    
    if args.model and not validate_model(args.model):
        print(f"Error: Unknown model '{args.model}'", file=sys.stderr)
        print("Use --list-models to see available models", file=sys.stderr)
        return 1
    
    cwd = get_working_directory(args)
    
    if args.prompt is None:
        # Interactive mode
        from apex.agent import Agent
        agent = Agent(cwd=str(cwd), model=args.model)
        interactive_loop(agent)
    else:
        # Non-interactive mode
        run_non_interactive(
            args.prompt,
            cwd,
            model=args.model,
            stream=not args.no_stream,
            verbose=args.verbose
        )
    
    return 0


# Allow running as script
if __name__ == "__main__":
    sys.exit(main_entry())