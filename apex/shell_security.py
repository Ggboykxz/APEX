"""Shell command security analysis for APEX."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CommandCategory(Enum):
    WORKING_DIR = "working_dir"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK = "network"
    SYSTEM = "system"
    PROCESS = "process"
    GIT = "git"
    BUILD = "build"
    PACKAGE = "package"
    CONTAINER = "container"
    DANGEROUS = "dangerous"


@dataclass
class CommandAnalysis:
    safe: bool
    category: CommandCategory
    command: str
    args: list[str]
    warnings: list[str]
    requires_confirmation: bool
    description: str | None = None


@dataclass
class _AnalysisState:
    """The mutable result of analyzing one command."""

    safe: bool = True
    category: CommandCategory = CommandCategory.WORKING_DIR
    warnings: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    description: str | None = None


class ShellSecurityAnalyzer:
    DANGEROUS_PATTERNS = [  # noqa: RUF012
        (
            r"rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$|--no-preserve-root)?",
            "Destructive system-wide deletion",
        ),
        (r":\(\)\{\s*:\|:\s*&\s*\};:.*", "Fork bomb"),
        (r">\s*/dev/sd[a-z]", "Direct disk write detected"),
        (r"dd\s+if=.*of=/dev/", "Direct device write"),
        (r"mkfs\.", "Filesystem formatting"),
        (r"chattr\s+-i", "Immutable file removal"),
        (r"wget\b.*\|\s*(sudo\s+)?(?:ba)?sh\b", "Download and pipe to shell (wget)"),
        (r"curl\b.*\|\s*(sudo\s+)?(?:ba)?sh\b", "Download and pipe to shell (curl)"),
        (r"eval\s+\$\(", "Dynamic code execution"),
        (r"exec\s+\$\(", "Dynamic exec"),
        (r"\|\s*(?:sudo\s+)?bash\b", "Pipe to bash"),
        (r"\|\s*(?:sudo\s+)?sh\b", "Pipe to shell"),
        (r">\s*/etc/(?:passwd|shadow|ssh|ssl|gshadow|hosts|sudoers)", "System file modification"),
        (r">\s*/etc/ssl/private/", "SSL private key modification"),
        (r"chmod\s+777\s+/(?:etc|var|usr)", "Overly permissive permissions"),
        (r"nc\s+-[el].*\d+", "Netcat listener (potential backdoor)"),
        (r"curl.*\.sh\s*\|\s*(sudo\s+)?(?:ba)?sh", "Download and execute script"),
        (r"wget.*\.sh\s*\|\s*(sudo\s+)?(?:ba)?sh", "Download and execute script"),
    ]

    NETWORK_PATTERNS = [  # noqa: RUF012
        r"\bcurl\b.*-X\s*(POST|PUT|PATCH|DELETE)",
        r"\bwget\b",
        r"\bnetcat\b",
        r"\bnc\b",
        r"\btelnet\b",
        r"\bssh\b.*@",
        r"\bscp\b",
        r"\brsync\b",
        r"\bftp\b",
        r"\bsftp\b",
    ]

    SYSTEM_PATTERNS = [  # noqa: RUF012
        r"\bsudo\b",
        r"\bchmod\b",
        r"\bchown\b",
        r"\bsystemctl\b",
        r"\bservice\b",
        r"\bkillall\b",
        r"\bpkill\b",
        r"\breboot\b",
        r"\bshutdown\b",
        r"\binit\b",
        r"\bvisudo\b",
        r"\bpasswd\b",
    ]

    FILE_DELETE_PATTERNS = [  # noqa: RUF012
        r"\brm\s+",
        r"\brmdir\b",
        r"\bunlink\b",
        r"\bdel\b",
    ]

    FILE_WRITE_PATTERNS = [  # noqa: RUF012
        r"\btee\b",
        r">\s*[a-zA-Z]?",
        r"\bcat\b.*>",
        r"\bnano\b",
        r"\bvim?\b",
        r"\bemacs\b",
        r"\bsed\s+-i\b",
    ]

    PROCESS_PATTERNS = [  # noqa: RUF012
        r"\bkill\b",
        r"\bps\b",
        r"\btop\b",
        r"\bhtop\b",
        r"\bkillall\b",
        r"\bpkill\b",
        r"\bkill\b",
        r"\bexec\b",
        r"\bspawn\b",
    ]

    GIT_PATTERNS = [  # noqa: RUF012
        # Note: "push" is intentionally NOT in the safe list so that any
        # `git push` (plain or forced) is classified GIT and triggers the
        # `if "push" in command` confirmation branch below.
        r"\bgit\s+(?!init|status|diff|log|show|branch|checkout|add|commit|pull|clone|fetch|merge|rebase|config|remote|stash)\w+",
        r"\bgit\s+push\s+-f\b",
        r"\bgit\s+push\s+--force\b",
        r"\bgit\s+filter-branch\b",
        r"\bgit\s+push\s+--all\b",
    ]

    BUILD_PATTERNS = [  # noqa: RUF012
        r"\bnpm\s+(?:run|build|test|start|dev)",
        r"\byarn\s+(?:run|build|start|dev)",
        r"\bpnpm\s+(?:run|build|start|dev)",
        r"\bmake\b",
        r"\bcmake\b",
        r"\bgradle\b",
        r"\bmvn\b",
        r"\bnpm\s+publish\b",
        r"\bpip\s+install\b",
        r"\bpip\s+upload\b",
        r"\bupload.*pypi\b",
    ]

    CONTAINER_PATTERNS = [  # noqa: RUF012
        r"\bdocker\b",
        r"\bpodman\b",
        r"\bkubectl\b",
        r"\bdocker\s+run\b",
        r"\bdocker\s+exec\b",
        r"\bkubernetes\b",
    ]

    SAFE_COMMANDS = [  # noqa: RUF012
        "ls",
        "pwd",
        "cd",
        "echo",
        "cat",
        "head",
        "tail",
        "grep",
        "find",
        "which",
        "whoami",
        "id",
        "uname",
        "date",
        "history",
        "man",
        "help",
        "env",
        "printenv",
        "type",
        "alias",
        "export",
        "source",
        "read",
        "printf",
        "test",
        "true",
        "false",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self._dangerous_re = self._compile_many(self.DANGEROUS_PATTERNS, first=True)
        self._network_re = self._compile_many(self.NETWORK_PATTERNS)
        self._system_re = self._compile_many(self.SYSTEM_PATTERNS)
        self._file_delete_re = self._compile_many(self.FILE_DELETE_PATTERNS)
        self._file_write_re = self._compile_many(self.FILE_WRITE_PATTERNS)
        self._process_re = self._compile_many(self.PROCESS_PATTERNS)
        self._git_re = self._compile_many(self.GIT_PATTERNS)
        self._build_re = self._compile_many(self.BUILD_PATTERNS)
        self._container_re = self._compile_many(self.CONTAINER_PATTERNS)

    @staticmethod
    def _compile_many(patterns: list, first: bool = False) -> list[re.Pattern]:
        """Compile a list of patterns, optionally taking the first element."""
        source = [pattern[0] if first else pattern for pattern in patterns]
        return [re.compile(pattern, re.IGNORECASE) for pattern in source]

    def analyze(self, command: str) -> CommandAnalysis:
        command = command.strip()
        parts = command.split()
        cmd = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        state = _AnalysisState()

        self._check_dangerous(command, state)
        self._check_network(command, state)
        self._check_system(command, state)
        self._check_file_delete(command, state)
        self._check_file_write(command, state)
        self._check_process(command, state)
        self._check_git(command, state)
        self._check_build(command, state)
        self._check_container(command, state)
        self._check_safe_command(cmd, state)
        self._check_sudo(command, state)
        self._check_chaining(command, state)

        return CommandAnalysis(
            safe=state.safe,
            category=state.category,
            command=command,
            args=args,
            warnings=state.warnings,
            requires_confirmation=state.requires_confirmation,
            description=state.description,
        )

    def _check_dangerous(self, command: str, state: _AnalysisState) -> None:
        for index, (_pattern, warning) in enumerate(self.DANGEROUS_PATTERNS):
            if self._dangerous_re[index].search(command):
                state.warnings.append(warning)
                state.safe = False
                state.category = CommandCategory.DANGEROUS
                state.requires_confirmation = True
                state.description = "DANGEROUS: " + warning

    def _check_network(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._network_re:
            if re_obj.search(command):
                state.category = CommandCategory.NETWORK
                state.requires_confirmation = True
                state.warnings.append("Network operation")
                return

    def _check_system(self, command: str, state: _AnalysisState) -> None:
        if not state.safe or state.category != CommandCategory.WORKING_DIR:
            return
        for re_obj in self._system_re:
            if re_obj.search(command):
                state.category = CommandCategory.SYSTEM
                state.requires_confirmation = True
                state.warnings.append("System modification")
                return

    def _check_file_delete(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._file_delete_re:
            if re_obj.search(command):
                state.category = CommandCategory.FILE_DELETE
                if "node_modules" not in command and ".git" not in command:
                    state.requires_confirmation = True
                else:
                    state.warnings.append("Recursive deletion may affect dependencies")
                return

    def _check_file_write(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._file_write_re:
            if re_obj.search(command):
                state.category = CommandCategory.FILE_WRITE
                return

    def _check_process(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._process_re:
            if re_obj.search(command):
                state.category = CommandCategory.PROCESS
                state.requires_confirmation = True
                state.warnings.append("Process manipulation")
                return

    def _check_git(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._git_re:
            if re_obj.search(command):
                state.category = CommandCategory.GIT
                state.warnings.append("Git operation")
                if "push" in command:
                    state.requires_confirmation = True
                return

    def _check_build(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._build_re:
            if re_obj.search(command):
                state.category = CommandCategory.BUILD
                return

    def _check_container(self, command: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        for re_obj in self._container_re:
            if re_obj.search(command):
                state.category = CommandCategory.CONTAINER
                state.requires_confirmation = True
                state.warnings.append("Container operation")
                return

    def _check_safe_command(self, cmd: str, state: _AnalysisState) -> None:
        if not state.safe:
            return
        if cmd in self.SAFE_COMMANDS:
            state.category = CommandCategory.FILE_READ
        elif cmd in ("cd", "pushd", "popd"):
            state.category = CommandCategory.WORKING_DIR

    def _check_sudo(self, command: str, state: _AnalysisState) -> None:
        if "sudo" in command:
            state.warnings.append("Requires elevated privileges")
            state.requires_confirmation = True

    def _check_chaining(self, command: str, state: _AnalysisState) -> None:
        if _has_chaining(command):
            state.warnings.append("Multiple commands chained")

    def is_safe(self, command: str) -> bool:
        analysis = self.analyze(command)
        return analysis.safe and not analysis.requires_confirmation

    def get_allowed_commands(self) -> list[str]:
        return list(
            set(self.SAFE_COMMANDS + ["npm", "pip", "git", "make", "cargo", "go", "python", "node"])
        )


def _has_chaining(command: str) -> bool:
    """Whether the command chains several sub-commands."""
    return "&&" in command or "||" in command or ";" in command


shell_analyzer = ShellSecurityAnalyzer()
