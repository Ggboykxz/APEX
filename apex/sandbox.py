"""Code execution sandbox for APEX - Run code safely."""

import subprocess
import tempfile
import os
import uuid
from pathlib import Path
from typing import Any


class CodeSandbox:
    LANGUAGES = {
        "python": {"ext": ".py", "run": ["python3", "{file}"]},
        "javascript": {"ext": ".js", "run": ["node", "{file}"]},
        "bash": {"ext": ".sh", "run": ["bash", "{file}"]},
        "ruby": {"ext": ".rb", "run": ["ruby", "{file}"]},
        "go": {"ext": ".go", "run": ["go", "run", "{file}"]},
        "rust": {"ext": ".rs", "run": ["rustc", "{file}", "-o", "{binary}"]},
    }

    def __init__(self, timeout: int = 30, max_output: int = 50000):
        self.timeout = timeout
        self.max_output = max_output
        self._temp_dir = Path(tempfile.gettempdir()) / "apex_sandbox"
        self._temp_dir.mkdir(exist_ok=True)

    def run_code(self, code: str, language: str = "python", args: list[str] | None = None) -> str:
        if language not in self.LANGUAGES:
            return f"ERROR: Unsupported language: {language}"

        lang_config = self.LANGUAGES[language]
        file_id = str(uuid.uuid4())[:8]
        file_path = self._temp_dir / f"{file_id}{lang_config['ext']}"

        try:
            file_path.write_text(code)

            if language == "rust":
                binary_path = self._temp_dir / f"{file_id}_binary"
                compile_cmd = ["rustc", str(file_path), "-o", str(binary_path)]
                result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    return f"ERROR: Compilation failed:\n{result.stderr}"
                run_cmd = [str(binary_path)]
            else:
                run_cmd = [cmd.format(file=str(file_path)) for cmd in lang_config["run"]]

            if args:
                run_cmd.extend(args)

            result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self._temp_dir
            )

            output = []
            if result.stdout:
                output.append(result.stdout[:self.max_output])
            if result.stderr:
                output.append(f"[STDERR]\n{result.stderr[:self.max_output]}")

            if result.returncode != 0:
                output.insert(0, f"[EXIT CODE: {result.returncode}]\n")

            return "\n".join(output) if output else "[no output]"

        except subprocess.TimeoutExpired:
            return f"ERROR: Execution timed out after {self.timeout} seconds"
        except FileNotFoundError:
            return f"ERROR: {language} runtime not found. Install it first."
        except Exception as e:
            return f"ERROR: Execution failed: {e}"
        finally:
            if file_path.exists():
                file_path.unlink()
            if language == "rust":
                binary_path = self._temp_dir / f"{file_id}_binary"
                if binary_path.exists():
                    binary_path.unlink()

    def run_python_snippet(self, code: str) -> str:
        return self.run_code(code, "python")

    def run_javascript_snippet(self, code: str) -> str:
        return self.run_code(code, "javascript")


class ShellSession:
    def __init__(self, cwd: Path | None = None, env: dict | None = None):
        self.cwd = cwd or Path.cwd()
        self.env = env or os.environ.copy()
        self.process: subprocess.Popen | None = None

    def start(self) -> bool:
        try:
            self.process = subprocess.Popen(
                ["bash", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
                text=True,
                bufsize=1
            )
            return True
        except Exception:
            return False

    def run(self, command: str, timeout: int = 30) -> str:
        if not self.process or not self.process.stdin:
            return "ERROR: Shell session not started"

        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

            output = []
            import time
            start = time.time()

            while time.time() - start < timeout:
                line = self.process.stdout.readline()
                if not line:
                    break
                output.append(line.rstrip())

            return "\n".join(output) if output else "[no output]"

        except Exception as e:
            return f"ERROR: {e}"

    def close(self) -> None:
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()


sandbox = CodeSandbox()