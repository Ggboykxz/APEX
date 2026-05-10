"""APEX CLI entry point - command parsing and interactive REPL."""

import argparse
import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from .agent import Agent
from .config import Config, MODELS
from .ui import UI
from .memory import Memory
from .session import SessionManager
from .context import get_repo_map, get_language_stats
from rich.panel import Panel


memory = Memory()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apex",
        description="APEX — The last coding agent you'll ever need",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", nargs="?", help="One-shot prompt to execute")
    parser.add_argument("--model", "-m", dest="model", help="Model alias to use")
    parser.add_argument("--cwd", "-C", dest="cwd", help="Working directory")
    parser.add_argument("--version", "-v", action="version", version="APEX 0.1.0")
    parser.add_argument("--list-models", action="store_true", help="List all available models")
    parser.add_argument("--one-shot", "-1", action="store_true", help="One-shot mode (non-interactive)")
    parser.add_argument("--stream", "-s", action="store_true", help="Enable streaming responses")
    parser.add_argument("--auto-commit", action="store_true", dest="auto_commit", help="Auto commit after successful task")
    parser.add_argument("--ui", action="store_true", help="Launch APEX TUI (OpenCode-inspired design)")
    parser.add_argument("--tui", "-t", action="store_true", help="Launch APEX TUI (same as --ui)")
    parser.add_argument("--new-tui", action="store_true", help="Launch APEX TUI (same as --ui)")
    parser.add_argument("-p", dest="prompt_direct", help="Direct prompt (CI/CD mode, no TUI)")
    parser.add_argument("-f", "--format", dest="output_format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (less output)")
    return parser.parse_args()


def list_models(ui: UI) -> None:
    ui.show_models(Config().model)


def handle_command(command: str, agent: Agent, ui: UI, config: Config | None = None, session: Any = None, use_stream: bool = False) -> bool:
    config = config or Config()
    global memory
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    match cmd:
        case "/model":
            if not arg:
                ui.print_error("Usage: /model <alias> or /model auto")
                return True
            if arg == "auto":
                config.auto_model = True
                ui.print_success("Auto model selection enabled")
            elif agent.switch_model(arg):
                config.auto_model = False
                ui.print_success(f"Switched to model: {arg}")
            else:
                ui.print_error(f"Unknown model: {arg}")
            return True

        case "/models":
            ui.show_models(agent.model)
            return True

        case "/reasoning":
            level = agent.cycle_reasoning_effort()
            ui.print_success(f"Reasoning effort: {level}")
            return True

        case "/reason":
            level = agent.cycle_reasoning_effort()
            ui.print_success(f"Reasoning effort: {level}")
            return True

        case "/cwd":
            if not arg:
                ui.print_info(f"Current directory: {agent.cwd}")
                return True
            try:
                new_cwd = Path(arg).expanduser().resolve()
            except (ValueError, OSError) as e:
                ui.print_error(f"Invalid path: {e}")
                return True
            if not new_cwd.exists():
                ui.print_error(f"Directory does not exist: {new_cwd}")
                return True
            if not new_cwd.is_dir():
                ui.print_error(f"Not a directory: {new_cwd}")
                return True
            try:
                new_cwd.relative_to(agent.cwd.resolve())
            except ValueError:
                if os.environ.get("APEX_ALLOW_OUTSIDE_CWD") != "true":
                    ui.print_error(f"Path outside working directory not allowed")
                    return True
            agent.cwd = new_cwd
            os.chdir(new_cwd)
            ui.print_success(f"Changed directory to: {new_cwd}")
            return True

        case "/clear":
            agent.reset_history()
            ui.print_success("Conversation history cleared")
            return True

        case "/history":
            if not agent.history:
                ui.print_info("No conversation history")
                return True
            ui.console.print("[cyan]Conversation history:[/cyan]")
            for i, msg in enumerate(agent.history[-10:]):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    truncated = content[:100] + "..." if len(content) > 100 else content
                    ui.console.print(f"  [{role}]: {truncated}")
            return True

        case "/cost":
            from .cost_local import cost_tracker
            usage = agent.usage
            cost_info = cost_tracker.get_session_cost()
            ui.console.print("[cyan]Session Cost:[/cyan]")
            ui.console.print(f"  Input tokens: {cost_info['input_tokens']}")
            ui.console.print(f"  Output tokens: {cost_info['output_tokens']}")
            ui.console.print(f"  Total: ${cost_info['total_cost']:.6f}")
            ui.console.print("[cyan]Token usage:[/cyan]")
            ui.console.print(f"  Prompt: {usage.get('prompt_tokens', 0)}")
            ui.console.print(f"  Completion: {usage.get('completion_tokens', 0)}")
            ui.console.print(f"  Total: {usage.get('total_tokens', 0)}")
            return True

        case "/save":
            sm = SessionManager()
            name = arg or "default"
            sm.save(agent, name)
            ui.print_success(f"Session saved as: {name}")
            return True

        case "/load":
            if not arg:
                ui.print_error("Usage: /load <name>")
                return True
            sm = SessionManager()
            loaded = sm.load(arg, agent)
            if loaded:
                ui.print_success(f"Session loaded: {arg}")
            else:
                ui.print_error(f"Session not found: {arg}")
            return True

        case "/sessions":
            sm = SessionManager()
            sessions = sm.list_sessions()
            if not sessions:
                ui.print_info("No saved sessions")
                return True
            ui.console.print("[cyan]Saved sessions:[/cyan]")
            for s in sessions:
                ui.console.print(f"  {s['name']} - {s['timestamp']} ({s['history_len']} messages)")
            return True

        case "/cost":
            from .cost_local import cost_tracker
            usage = agent.usage
            cost_info = cost_tracker.get_session_cost()
            ui.console.print("[cyan]Session Cost:[/cyan]")
            ui.console.print(f"  Input tokens: {cost_info['input_tokens']}")
            ui.console.print(f"  Output tokens: {cost_info['output_tokens']}")
            ui.console.print(f"  Total: ${cost_info['total_cost']:.6f}")
            ui.console.print("[cyan]Token usage:[/cyan]")
            ui.console.print(f"  Prompt: {usage.get('prompt_tokens', 0)}")
            ui.console.print(f"  Completion: {usage.get('completion_tokens', 0)}")
            ui.console.print(f"  Total: {usage.get('total_tokens', 0)}")
            return True

        case "/memory":
            if not arg:
                facts = memory.get_all()
                if not facts:
                    ui.print_info("No memory facts stored")
                else:
                    ui.console.print("[cyan]Memory facts:[/cyan]")
                    for i, f in enumerate(facts):
                        ui.console.print(f"  {i}: {f['fact']} [relevance: {', '.join(f.get('relevance', []))}]")
                return True

            mem_parts = arg.split(maxsplit=2)
            subcmd = mem_parts[0] if mem_parts else ""

            if subcmd == "add" and len(mem_parts) >= 3:
                fact = mem_parts[1]
                relevance = mem_parts[2].split(",") if len(mem_parts) > 2 else []
                memory.add(fact.strip(), [r.strip() for r in relevance])
                ui.print_success(f"Added to memory: {fact}")
            elif subcmd == "clear":
                memory.clear()
                ui.print_success("Memory cleared")
            elif subcmd == "search" and len(mem_parts) >= 2:
                results = memory.search(mem_parts[1])
                if not results:
                    ui.print_info("No matching facts found")
                else:
                    ui.console.print("[cyan]Search results:[/cyan]")
                    for f in results:
                        ui.console.print(f"  • {f['fact']}")
            else:
                ui.print_info("Usage: /memory [add <fact> <relevance>|clear|search <query>]")
            return True

        case "/map":
            repo_map = get_repo_map(agent.cwd)
            ui.console.print(Panel(repo_map, title="[cyan]Repository Map[/cyan]", border_style="cyan"))
            return True

        case "/stats":
            stats = get_language_stats(agent.cwd)
            if stats:
                ui.console.print("[cyan]Language stats:[/cyan]")
                for lang, count in sorted(stats.items(), key=lambda x: -x[1]):
                    ui.console.print(f"  {lang}: {count} files")
            else:
                ui.print_info("No source files found")
            return True

        case "/git":
            from .tools import ToolExecutor
            executor = ToolExecutor(cwd=agent.cwd)
            status = executor.execute("get_git_status", {})
            ui.console.print(Panel(status, title="[cyan]Git Status[/cyan]", border_style="cyan"))
            return True

        case "/agent":
            from .agents import agent_manager
            if not arg:
                current = agent.current_agent
                ui.console.print(f"[cyan]Current agent:[/cyan] {current}")
                ui.console.print("\n[cyan]Available agents:[/cyan]")
                for a in agent_manager.list_agents():
                    marker = "✓" if a.name == current else " "
                    mode = "[primary]" if a.mode == "primary" else "[subagent]"
                    ui.console.print(f"  {marker} {a.name} {mode} - {a.description}")
                return True
            if agent.switch_agent(arg):
                ui.print_success(f"Switched to agent: {arg}")
            else:
                ui.print_error(f"Unknown agent: {arg}. Use /agent to list available agents.")
            return True

        case "/yolo":
            from .agents import agent_manager
            if "yolo" in agent_manager.agents:
                agent.switch_agent("yolo")
                config.agent_mode = "yolo"
                ui.print_success("YOLO mode enabled - auto-approved execution")
            else:
                ui.print_error("YOLO agent not available")
            return True

        case "/plan":
            agent.switch_agent("plan")
            config.agent_mode = "plan"
            ui.print_success("Plan mode enabled - read-only")
            return True

        case "/build":
            agent.switch_agent("build")
            config.agent_mode = "agent"
            ui.print_success("Build mode enabled - interactive with approval")
            return True

        case "/restore":
            from .workspace_rollback import WorkspaceRollback
            wb = WorkspaceRollback(agent.cwd)
            if arg:
                success = wb.restore_snapshot(arg)
                if success:
                    ui.print_success(f"Restored snapshot: {arg}")
                else:
                    ui.print_error(f"Failed to restore: {arg}")
            else:
                snapshots = wb.list_snapshots()
                if snapshots:
                    ui.console.print("[cyan]Available snapshots:[/cyan]")
                    for s in snapshots[-10:]:
                        ui.console.print(f"  {s['name']} - {s.get('label', '')}")
                else:
                    ui.print_info("No snapshots available")
            return True

        case "/revert":
            from .workspace_rollback import TurnTracker
            tt = TurnTracker(agent.cwd)
            turns = int(arg) if arg.isdigit() else 1
            if tt.revert_turn(turns):
                ui.print_success(f"Reverted {turns} turn(s)")
            else:
                ui.print_error("Failed to revert turn")
            return True

        case "/undo":
            from .git_undo import GitUndoManager
            gum = GitUndoManager(agent.cwd)
            if not gum.can_undo():
                ui.print_info("Nothing to undo")
                return True
            steps = int(arg) if arg.isdigit() else 1
            snapshot_id = gum.undo(steps)
            if snapshot_id:
                ui.print_success(f"Undone {steps} step(s)")
            else:
                ui.print_error("Failed to undo")
            return True

        case "/redo":
            from .git_undo import GitUndoManager
            gum = GitUndoManager(agent.cwd)
            if not gum.can_redo():
                ui.print_info("Nothing to redo")
                return True
            steps = int(arg) if arg.isdigit() else 1
            snapshot_id = gum.redo(steps)
            if snapshot_id:
                ui.print_success(f"Redone {steps} step(s)")
            else:
                ui.print_error("Failed to redo")
            return True

        case "/skills":
            from .skills_system import skills_manager
            skills = skills_manager.list_skills()
            if skills:
                ui.console.print("[cyan]Available skills:[/cyan]")
                for s in skills:
                    ui.console.print(f"  {s['name']} - {s['description']}")
            else:
                ui.print_info("No skills available")
            return True

        case "/github":
            from .github_integration import gh_automation
            if not arg:
                ui.print_info("Usage: /github <command> [args]")
                ui.print_info("Commands: issues, prs, create-issue, create-pr")
                return True
            parts = arg.split(maxsplit=1)
            cmd = parts[0]
            if cmd == "issues":
                issues = gh_automation.client.list_issues()
                for issue in issues:
                    ui.console.print(f"  #{issue.get('number')}: {issue.get('title')}")
            elif cmd == "prs":
                prs = gh_automation.client.list_prs()
                for pr in prs:
                    ui.console.print(f"  PR #{pr.get('number')}: {pr.get('title')}")
            else:
                ui.print_error(f"Unknown github command: {cmd}")
            return True

        case "/local":
            from .cost_local import local_manager
            if arg == "enable":
                local_manager.enable_local()
                ui.print_success("Local execution enabled")
            elif arg == "disable":
                local_manager.disable_local()
                ui.print_success("Local execution disabled")
            else:
                providers = local_manager.get_available_providers()
                status = "enabled" if local_manager.is_enabled() else "disabled"
                ui.console.print(f"Local execution: {status}")
                if providers:
                    ui.console.print(f"Available: {', '.join(providers.keys())}")
            return True

        case "/sessionsave":
            from .session import SessionManager
            sm = SessionManager()
            name = arg or "default"
            path = sm.save(agent, name)
            ui.print_success(f"Session saved: {path}")
            return True

        case "/sessionload":
            from .session import SessionManager
            sm = SessionManager()
            if arg:
                session = sm.load(arg)
                if session:
                    agent.history = session.get("history", [])
                    ui.print_success(f"Loaded session: {arg}")
                else:
                    ui.print_error(f"Session not found: {arg}")
            else:
                sessions = sm.list_sessions()
                ui.console.print("[cyan]Saved sessions:[/cyan]")
                for s in sessions:
                    ui.console.print(f"  {s['name']} - {s['timestamp']}")
            return True

        case "/tasks":
            from .task_queue import TaskQueue
            tq = TaskQueue()
            tasks = tq.list_tasks(limit=10)
            if tasks:
                ui.console.print("[cyan]Task queue:[/cyan]")
                for t in tasks:
                    status = t.status.value
                    ui.console.print(f"  {t.id}: {t.name} [{status}]")
            else:
                ui.print_info("No tasks in queue")
            return True

        case "/http":
            if arg == "start":
                ui.print_info("Starting HTTP API server...")
            else:
                ui.print_info("Usage: /http start - Start HTTP API server")
            return True

        case "/agents":
            from .agents import agent_manager
            from rich.table import Table
            table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Mode", style="white", width=10)
            table.add_column("Description", style="white")
            current = agent.current_agent
            for a in agent_manager.list_agents():
                marker = "✓" if a.name == current else ""
                table.add_row(f"{a.name} {marker}", a.mode, a.description)
            ui.console.print(table)
            return True

        case "/subagents":
            from .agents import agent_manager
            from rich.table import Table
            table = Table(title="Subagents (use @name to invoke)", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="cyan", width=12)
            table.add_column("Description", style="white")
            for a in agent_manager.list_agents("subagent"):
                table.add_row(a.name, a.description)
            ui.console.print(table)
            return True

        case "/help":
            ui.show_help()
            return True

        case "/exit" | "/quit":
            ui.print_info("Goodbye!")
            sys.exit(0)

        case _:
            if cmd.startswith("/"):
                ui.print_error(f"Unknown command: {cmd}. Type /help for available commands.")
                return True
            return False


async def run_repl_streaming(agent: Agent, ui: UI) -> None:
    history_file = Path.home() / ".apex" / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @bindings.add("tab")
    def cycle_agent(event):
        new_agent = agent.cycle_agent()
        ui.print_success(f"Switched to agent: {new_agent}")
        event.app.current_buffer.text = ""

    style = Style.from_dict({
        "prompt": "cyan bold",
        "continuation": "cyan",
    })

    session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=bindings,
        style=style,
        message="› ",
    )

    ui.show_banner(agent.model, str(agent.cwd), agent.current_agent)
    ui.print_info("Type /help for available commands. Press Tab to cycle agents, Ctrl+C to exit.\n")

    while True:
        try:
            user_input = session.prompt()
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if handle_command(user_input, agent, ui, session, use_stream=True):
                    continue
            ui.print_user(user_input)

            full_response = ""
            async for chunk in agent.chat_streaming(user_input):
                full_response += chunk
                ui.console.print(chunk, end="")
            ui.console.print()

        except KeyboardInterrupt:
            ui.print_info("\nType /exit to quit or /clear to clear history")
            continue
        except EOFError:
            break


def run_repl(agent: Agent, ui: UI, use_stream: bool = False) -> None:
    history_file = Path.home() / ".apex" / "history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    bindings = KeyBindings()

    @bindings.add("c-c")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @bindings.add("tab")
    def cycle_agent(event):
        new_agent = agent.cycle_agent()
        ui.print_success(f"Switched to agent: {new_agent}")
        event.app.current_buffer.text = ""

    style = Style.from_dict({
        "prompt": "cyan bold",
        "continuation": "cyan",
    })

    session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=bindings,
        style=style,
        message="› ",
    )

    ui.show_banner(agent.model, str(agent.cwd), agent.current_agent)
    ui.print_info("Type /help for available commands. Press Tab to cycle agents, Ctrl+C to exit.\n")

    while True:
        try:
            user_input = session.prompt()
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if handle_command(user_input, agent, ui, session, use_stream):
                    continue
            ui.print_user(user_input)
            with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = agent.chat(user_input)
            ui.print_response(response)
        except KeyboardInterrupt:
            ui.print_info("\nType /exit to quit or /clear to clear history")
            continue
        except EOFError:
            break


def run_one_shot(prompt: str, agent: Agent, ui: UI, use_stream: bool = False) -> None:
    if use_stream:
        full_response = ""
        ui.console.print("[cyan]Streaming response:[/cyan]")
        for chunk in agent.chat(prompt):
            full_response += chunk
            ui.console.print(chunk, end="")
        ui.console.print()
    else:
        with ui.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
            response = agent.chat(prompt)
        ui.print_response(response)


def run_cicd_mode(prompt: str, agent: Agent, ui: UI, output_format: str = "text", quiet: bool = False) -> None:
    """CI/CD mode - Direct prompt execution with optional JSON output."""
    try:
        with ui.console.status("[cyan]Processing...[/cyan]", spinner="dots") if not quiet else ui.console.status(""):
            response = agent.chat(prompt)

        if output_format == "json":
            result = {
                "success": True,
                "prompt": prompt,
                "response": response,
                "model": agent.model,
                "usage": agent.usage
            }
            print(json.dumps(result, indent=2))
        else:
            if not quiet:
                ui.print_response(response)
            else:
                print(response)

    except Exception as e:
        if output_format == "json":
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        else:
            ui.print_error(f"Error: {e}")


def run_textual_tui(agent: Agent, ui: UI) -> None:
    """Run APEX Textual TUI - The best terminal UI ever built."""
    try:
        from .tui import ApexApp
        ui.print_info("Starting APEX Textual TUI (Ctrl+C to exit)...")
        app = ApexApp(
            model=agent.config.model,
            cwd=str(agent.config.cwd),
            agent=agent,
        )
        app.run()
    except ImportError as e:
        ui.print_error(f"Textual TUI not available: {e}")
    except Exception as e:
        ui.print_error(f"TUI error: {e}")


def run_new_tui(agent: Agent, ui: UI) -> None:
    """Run APEX TUI — same as run_textual_tui (unified single TUI)."""
    run_textual_tui(agent, ui)


def run_apex_tui(agent: Agent, ui: UI) -> None:
    """Run APEX OpenTUI - Better than OpenCode!"""
    tui_path = Path(__file__).parent.parent / "tui-frontend" / "index.ts"
    if not tui_path.exists():
        ui.print_error("OpenTUI not found. Run: cd tui-frontend && bun install")
        return

    ui.print_info("Starting APEX TUI with OpenTUI (Ctrl+C to exit)...")

    bun_path = Path.home() / ".bun" / "bin" / "bun"
    if not bun_path.exists():
        ui.print_error("Bun not found. Install: curl -fsSL https://bun.sh/install | bash")
        return

    env = os.environ.copy()
    env["PATH"] = str(bun_path.parent) + ":" + env.get("PATH", "")

    try:
        proc = subprocess.Popen(
            [str(bun_path), str(tui_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

        proc.stdin.write(json.dumps({"type": "welcome", "content": "Connected to APEX!"}) + "\n")
        proc.stdin.flush()

        def read_output():
            try:
                for line in iter(proc.stdout.readline, ""):
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        if msg.get("type") == "user_input":
                            user_input = msg.get("content", "")
                            if user_input.startswith("/"):
                                handle_command(user_input, agent, ui)
                            else:
                                ui.print_user(user_input)
                                response = agent.chat(user_input)
                                proc.stdin.write(json.dumps({"type": "ai_message", "content": response}) + "\n")
                                proc.stdin.flush()
                        elif msg.get("type") == "quit":
                            proc.terminate()
                            return
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass

        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()

        while proc.poll() is None:
            import time
            time.sleep(0.1)

    except FileNotFoundError:
        ui.print_error("Bun not found. Install: curl -fsSL https://bun.sh/install | bash")
    except Exception as e:
        ui.print_error(f"OpenTUI error: {e}")


def main() -> None:
    args = parse_args()
    config = Config()
    if args.model:
        if args.model not in MODELS:
            print(f"Error: Unknown model '{args.model}'", file=sys.stderr)
            print("Use --list-models to see available models", file=sys.stderr)
            sys.exit(1)
        config.model = args.model
    if args.cwd:
        config.cwd = Path(args.cwd).expanduser().resolve()

    agent = Agent(config)
    ui = UI()

    if args.list_models:
        list_models(ui)
        sys.exit(0)

    if args.ui:
        run_textual_tui(agent, ui)
    elif args.tui:
        run_textual_tui(agent, ui)
    elif args.new_tui:
        run_textual_tui(agent, ui)
    elif args.prompt_direct:
        run_cicd_mode(args.prompt_direct, agent, ui, args.output_format, args.quiet)
    elif args.prompt:
        run_one_shot(args.prompt, agent, ui, args.stream)
    else:
        run_repl(agent, ui, args.stream)


if __name__ == "__main__":
    main()
