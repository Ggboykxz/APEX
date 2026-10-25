"""Symbol-level repository maps for APEX context.

The map is intentionally small and deterministic. A scan walks every supported
source file below a repository root, extracts declaration signatures with line
numbers, ranks the files, and renders a compact text map that fits a token
budget.

Supported languages
-------------------
* Python (``.py``/``.pyi``) through :mod:`ast`: classes, functions, methods,
  decorators, parameter signatures and the module docstring summary.
* JavaScript/TypeScript (``.js``/``.jsx``/``.mjs``/``.cjs``/``.ts``/``.tsx``/
  ``.mts``/``.cts``) through conservative, line-anchored regular expressions:
  classes, functions, arrow functions, interfaces, type aliases and enums.
* Rust (``.rs``): structs, enums, traits, impls, functions and type aliases.
* Go (``.go``): functions, methods, structs, interfaces and type aliases.

Files larger than :data:`MAX_FILE_BYTES` (512 KiB), binary files and files that
are not valid UTF-8 are skipped without failing the scan. Directories such as
``.git``, ``node_modules``, ``target`` and virtual environments are always
ignored, and the repository's root ``.gitignore`` is applied with basic git
semantics (comments, negations, directory patterns and globs). Nested
``.gitignore`` files are not read.

Ranking heuristic
-----------------
Files are ordered by:

1. descending reference count — how often the file's top-level declaration
   names appear in other scanned files (imports and identifier mentions), then
2. ascending directory depth (files closer to the root first), then
3. ascending relative POSIX path for a stable tie-break.

Definitions always stay in source order inside a file. References are counted
on identifier boundaries from the raw text, so they are a cheap heuristic, not
a compiler-grade dependency graph.

Token budget
------------
Tokens are estimated as ``ceil(len(text) / 4)``. The lowest-ranked file entries
are dropped whole until the rendered map fits ``max_tokens``. A single entry
that cannot fit is dropped too, which can yield an empty string for an extreme
budget. No bodies are emitted, only signatures and line numbers.

Cache
-----
Parsed symbols are cached as JSON under ``~/.apex/cache/repomap/<sha256>.json``,
where ``<sha256>`` is the digest of the absolute root path. Each entry stores
the file's ``mtime_ns`` and size. Changed files are reparsed, unchanged files
reuse their cached symbols, and malformed cache data is silently ignored. Set
``use_cache=False`` to bypass both cache reads and writes.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "FileSymbols",
    "Symbol",
    "build_repo_map",
    "collect_symbols",
    "estimate_tokens",
]

MAX_FILE_BYTES = 512 * 1024
DEFAULT_MAX_TOKENS = 2000
_MODULE_DOC_CHARS = 120
_CACHE_VERSION = 1

IGNORED_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "target",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "coverage",
        "htmlcov",
    }
)

_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})
_JS_SUFFIXES = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"})
_SOURCE_SUFFIXES = _PYTHON_SUFFIXES | _JS_SUFFIXES | frozenset({".rs", ".go"})
_RANKABLE_KINDS = frozenset({"class", "enum", "function", "interface", "struct", "trait", "type"})

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Symbol:
    """A declaration found in a source file.

    Attributes:
        kind: Declaration kind (``class``, ``method``, ``function``,
            ``interface``, ``type``, ``struct``, ``enum``, ``trait`` or
            ``impl``).
        name: Simple declared name (no parent qualification).
        line: 1-based line number of the declaration.
        signature: Single-line declaration signature without a body.
        decorators: Python decorator expressions, without the leading ``@``.
        parent: Enclosing class/type name when known, otherwise ``""``.
    """

    kind: str
    name: str
    line: int
    signature: str
    decorators: tuple[str, ...] = ()
    parent: str = ""


@dataclass(frozen=True, slots=True)
class FileSymbols:
    """Symbols and module summary for one scanned source file.

    ``path`` is relative to the scanned root and always uses POSIX separators,
    which keeps maps and cache keys stable across operating systems.
    """

    path: str
    module_doc: str = ""
    symbols: tuple[Symbol, ...] = ()


class _GitIgnore:
    """Minimal matcher for the root ``.gitignore``.

    Supports blank lines, comments, negations, directory-only patterns,
    leading-slash anchoring and shell-style globs. A pattern without a slash
    matches the basename at any depth, mirroring git's basic behavior.
    """

    def __init__(self, root: Path) -> None:
        self._rules: list[tuple[str, bool, bool, bool]] = []
        try:
            content = (root / ".gitignore").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        for raw in content.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("\\#", "\\!")):
                line = line[1:]

            negated = line.startswith("!")
            if negated:
                line = line[1:].strip()
                if not line:
                    continue

            dir_only = line.endswith("/")
            if dir_only:
                line = line.rstrip("/")
            anchored = line.startswith("/")
            if anchored:
                line = line.lstrip("/")
            if line:
                self._rules.append((line, negated, dir_only, anchored))

    def is_ignored(self, rel_path: str, is_dir: bool) -> bool:
        """Return whether a relative POSIX path is ignored."""
        ignored = False
        for pattern, negated, dir_only, anchored in self._rules:
            if dir_only and not is_dir:
                continue
            if anchored or "/" in pattern:
                matched = fnmatch.fnmatchcase(rel_path, pattern)
            else:
                matched = fnmatch.fnmatchcase(rel_path.rsplit("/", 1)[-1], pattern)
            if matched:
                ignored = not negated
        return ignored


@dataclass(frozen=True, slots=True)
class _SourceFile:
    path: str
    text: str
    mtime_ns: int
    size: int


def estimate_tokens(text: str) -> int:
    """Estimate tokens for *text* as ``ceil(len(text) / 4)``."""
    return (len(text) + 3) // 4


def _tokens_for_chars(char_count: int) -> int:
    return (char_count + 3) // 4


def _collapse(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _summarize_doc(doc: str | None) -> str:
    if not doc:
        return ""
    for line in doc.splitlines():
        compact = _collapse(line)
        if compact:
            return _truncate(compact, _MODULE_DOC_CHARS)
    return ""


def _normalize_root(root: Path | str) -> Path:
    try:
        return Path(root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return Path(root).expanduser().absolute()


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def _iter_source_files(root: Path) -> list[str]:
    """Return sorted relative POSIX paths of scannable source files."""
    gitignore = _GitIgnore(root)
    found: list[str] = []

    def onerror(_error: OSError) -> None:
        return None

    for dirpath, dirnames, filenames in os.walk(
        root, topdown=True, onerror=onerror, followlinks=False
    ):
        current = Path(dirpath)
        try:
            rel_dir = current.relative_to(root).as_posix()
        except ValueError:
            rel_dir = ""
        if rel_dir == ".":
            rel_dir = ""

        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            if dirname in IGNORED_DIRS:
                continue
            try:
                if (current / dirname).is_symlink():
                    continue
            except OSError:
                continue
            rel_path = f"{rel_dir}/{dirname}" if rel_dir else dirname
            if gitignore.is_ignored(rel_path, True):
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            if Path(filename).suffix.lower() not in _SOURCE_SUFFIXES:
                continue
            rel_path = f"{rel_dir}/{filename}" if rel_dir else filename
            if gitignore.is_ignored(rel_path, False):
                continue
            found.append(rel_path)

    return sorted(found)


def _read_source(root: Path, rel_path: str) -> _SourceFile | None:
    """Read one UTF-8 source file, or return ``None`` when it must be skipped."""
    path = root / rel_path
    try:
        stat = path.stat()
        if stat.st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None

    if b"\x00" in data:
        return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    return _SourceFile(rel_path, text, stat.st_mtime_ns, len(data))


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------


def _python_decorators(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    decorators: list[str] = []
    for decorator in node.decorator_list:
        try:
            decorators.append(_collapse(ast.unparse(decorator)))
        except Exception:  # pragma: no cover - defensive for exotic AST nodes
            continue
    return tuple(decorators)


def _python_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    try:
        arguments = ast.unparse(node.args)
    except Exception:  # pragma: no cover - defensive for exotic AST nodes
        arguments = ""
    returns = ""
    if node.returns is not None:
        try:
            returns = f" -> {ast.unparse(node.returns)}"
        except Exception:  # pragma: no cover - defensive for exotic AST nodes
            returns = ""
    return _collapse(f"{prefix} {node.name}({arguments}){returns}")


def _python_class_signature(node: ast.ClassDef) -> str:
    parts: list[str] = []
    for base in node.bases:
        try:
            parts.append(ast.unparse(base))
        except Exception:  # pragma: no cover - defensive for exotic AST nodes
            continue
    for keyword in node.keywords:
        try:
            value = ast.unparse(keyword.value)
        except Exception:  # pragma: no cover - defensive for exotic AST nodes
            continue
        parts.append(f"{keyword.arg}={value}" if keyword.arg else f"**{value}")
    suffix = f"({', '.join(parts)})" if parts else ""
    return _collapse(f"class {node.name}{suffix}")


def _extract_python(text: str) -> tuple[str, list[Symbol]]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return "", []

    module_doc = _summarize_doc(ast.get_docstring(tree, clean=True))
    symbols: list[Symbol] = []

    def add_class(node: ast.ClassDef, parent: str) -> None:
        qualified = f"{parent}.{node.name}" if parent else node.name
        symbols.append(
            Symbol(
                "class",
                node.name,
                node.lineno,
                _python_class_signature(node),
                _python_decorators(node),
                parent,
            )
        )
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    Symbol(
                        "method",
                        child.name,
                        child.lineno,
                        _python_function_signature(child),
                        _python_decorators(child),
                        qualified,
                    )
                )
            elif isinstance(child, ast.ClassDef):
                add_class(child, qualified)

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            add_class(node, "")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                Symbol(
                    "function",
                    node.name,
                    node.lineno,
                    _python_function_signature(node),
                    _python_decorators(node),
                )
            )

    symbols.sort(key=lambda symbol: symbol.line)
    return module_doc, symbols


# ---------------------------------------------------------------------------
# JavaScript / TypeScript extraction
# ---------------------------------------------------------------------------

_JS_CLASS_RE = re.compile(
    r"^(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:abstract\s+)?"
    r"class\s+(?P<name>[A-Za-z_$][\w$]*)"
)
_JS_FUNCTION_RE = re.compile(
    r"^(?:export\s+(?:default\s+)?)?(?:declare\s+)?(?:async\s+)?"
    r"function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)"
)
_JS_INTERFACE_RE = re.compile(
    r"^(?:export\s+(?:default\s+)?)?(?:declare\s+)?interface\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)"
)
_JS_TYPE_RE = re.compile(r"^(?:export\s+)?(?:declare\s+)?type\s+(?P<name>[A-Za-z_$][\w$]*)")
_JS_ENUM_RE = re.compile(
    r"^(?:export\s+)?(?:declare\s+)?(?:const\s+)?enum\s+(?P<name>[A-Za-z_$][\w$]*)"
)
_JS_ARROW_RE = re.compile(
    r"^(?:export\s+)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)"
    r"(?:\s*:\s*[^=]+)?\s*=\s*(?:async\s*)?"
    r"(?:<[^>]*>\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*(?::\s*[^=]+)?=>"
)


def _iter_code_lines(text: str) -> Iterator[str]:
    """Yield lines with C-style comments removed, preserving line numbers.

    This is deliberately lightweight: it protects declaration matching from
    commented-out code without trying to be a JavaScript/Rust/Go lexer. Odd
    files still yield lines and can never make the scan crash.
    """
    in_block = False
    for line in text.splitlines():
        code = line
        if in_block:
            end = code.find("*/")
            if end == -1:
                yield ""
                continue
            code = code[end + 2 :]
            in_block = False

        while True:
            start = code.find("/*")
            if start == -1:
                break
            end = code.find("*/", start + 2)
            if end == -1:
                code = code[:start]
                in_block = True
                break
            code = code[:start] + code[end + 2 :]

        line_comment = code.find("//")
        if line_comment != -1:
            code = code[:line_comment]
        yield code


def _declaration_signature(line: str, *, keep_arrow: bool = False) -> str:
    """Trim a declaration line to a body-free, single-line signature."""
    text = line.strip()
    brace = text.find("{")
    if brace != -1:
        text = text[:brace]
    if keep_arrow:
        arrow = text.find("=>")
        if arrow != -1:
            text = text[: arrow + 2]
    text = _collapse(text.rstrip(" ;"))
    if text.endswith("="):
        text = text[:-1].rstrip()
    return text


def _extract_javascript(text: str) -> tuple[str, list[Symbol]]:
    symbols: list[Symbol] = []
    for line_number, raw_line in enumerate(_iter_code_lines(text), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if match := _JS_CLASS_RE.match(line):
            symbols.append(
                Symbol("class", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _JS_FUNCTION_RE.match(line):
            symbols.append(
                Symbol("function", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _JS_INTERFACE_RE.match(line):
            symbols.append(
                Symbol("interface", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _JS_TYPE_RE.match(line):
            symbols.append(
                Symbol("type", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _JS_ENUM_RE.match(line):
            symbols.append(
                Symbol("enum", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _JS_ARROW_RE.match(line):
            symbols.append(
                Symbol(
                    "function",
                    match.group("name"),
                    line_number,
                    _declaration_signature(line, keep_arrow=True),
                )
            )
    return "", symbols


# ---------------------------------------------------------------------------
# Rust extraction
# ---------------------------------------------------------------------------

_RUST_VISIBILITY = r"(?:pub(?:\([^)]*\))?\s+)?"
_RUST_STRUCT_RE = re.compile(rf"^{_RUST_VISIBILITY}(?:struct|union)\s+(?P<name>[A-Za-z_]\w*)")
_RUST_ENUM_RE = re.compile(rf"^{_RUST_VISIBILITY}enum\s+(?P<name>[A-Za-z_]\w*)")
_RUST_TRAIT_RE = re.compile(
    rf"^{_RUST_VISIBILITY}(?:unsafe\s+)?(?:auto\s+)?trait\s+(?P<name>[A-Za-z_]\w*)"
)
_RUST_IMPL_RE = re.compile(r"^(?:unsafe\s+)?impl(?:\s*<[^>]*>)?\s+")
_RUST_FN_RE = re.compile(
    rf"^{_RUST_VISIBILITY}(?:(?:const|async|unsafe|extern\s+\"[^\"]*\")\s+)*"
    r"fn\s+(?P<name>[A-Za-z_]\w*)"
)
_RUST_TYPE_RE = re.compile(rf"^{_RUST_VISIBILITY}type\s+(?P<name>[A-Za-z_]\w*)")


def _rust_impl_name(signature: str) -> str:
    target = re.sub(r"^(?:unsafe\s+)?impl\s*", "", signature)
    target = re.sub(r"^<[^>]*>\s*", "", target)
    target = target.split(" where ", 1)[0]
    if " for " in target:
        target = target.split(" for ", 1)[1]
    target = target.split("<", 1)[0].strip().lstrip("!&").strip()
    parts = target.split()
    return parts[-1] if parts else "impl"


def _extract_rust(text: str) -> tuple[str, list[Symbol]]:
    symbols: list[Symbol] = []
    for line_number, raw_line in enumerate(_iter_code_lines(text), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if match := _RUST_STRUCT_RE.match(line):
            symbols.append(
                Symbol("struct", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _RUST_ENUM_RE.match(line):
            symbols.append(
                Symbol("enum", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _RUST_TRAIT_RE.match(line):
            symbols.append(
                Symbol("trait", match.group("name"), line_number, _declaration_signature(line))
            )
        elif _RUST_IMPL_RE.match(line):
            signature = _declaration_signature(line)
            symbols.append(Symbol("impl", _rust_impl_name(signature), line_number, signature))
        elif match := _RUST_FN_RE.match(line):
            symbols.append(
                Symbol("function", match.group("name"), line_number, _declaration_signature(line))
            )
        elif match := _RUST_TYPE_RE.match(line):
            symbols.append(
                Symbol("type", match.group("name"), line_number, _declaration_signature(line))
            )
    return "", symbols


# ---------------------------------------------------------------------------
# Go extraction
# ---------------------------------------------------------------------------

_GO_FUNC_RE = re.compile(r"^func\s+(?:\((?P<receiver>[^)]*)\)\s*)?(?P<name>[A-Za-z_]\w*)")
_GO_TYPE_RE = re.compile(r"^type\s+(?P<name>[A-Za-z_]\w*)(?:\[[^\]]*\])?\s+(?P<rest>\S.*)$")


def _go_receiver_type(receiver: str | None) -> str:
    if not receiver:
        return ""
    identifiers = _IDENTIFIER_RE.findall(receiver.split("[", 1)[0])
    return identifiers[-1] if identifiers else ""


def _extract_go(text: str) -> tuple[str, list[Symbol]]:
    symbols: list[Symbol] = []
    for line_number, raw_line in enumerate(_iter_code_lines(text), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if match := _GO_FUNC_RE.match(line):
            receiver = match.group("receiver")
            symbols.append(
                Symbol(
                    "method" if receiver else "function",
                    match.group("name"),
                    line_number,
                    _declaration_signature(line),
                    parent=_go_receiver_type(receiver),
                )
            )
        elif match := _GO_TYPE_RE.match(line):
            body = match.group("rest").lstrip("= ").strip()
            if body.startswith("struct"):
                kind = "struct"
            elif body.startswith("interface"):
                kind = "interface"
            else:
                kind = "type"
            symbols.append(
                Symbol(kind, match.group("name"), line_number, _declaration_signature(line))
            )
    return "", symbols


def _extract_file(rel_path: str, text: str) -> tuple[str, list[Symbol]]:
    """Dispatch extraction for one file; extraction never breaks the scan."""
    suffix = Path(rel_path).suffix.lower()
    try:
        if suffix in _PYTHON_SUFFIXES:
            return _extract_python(text)
        if suffix in _JS_SUFFIXES:
            return _extract_javascript(text)
        if suffix == ".rs":
            return _extract_rust(text)
        if suffix == ".go":
            return _extract_go(text)
    except Exception:  # pragma: no cover - last-resort guard for odd input
        return "", []
    return "", []


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _cache_dir() -> Path:
    return Path.home() / ".apex" / "cache" / "repomap"


def _cache_path(root: Path) -> Path:
    digest = hashlib.sha256(str(root).encode("utf-8", "surrogatepass")).hexdigest()
    return _cache_dir() / f"{digest}.json"


def _symbol_to_cache(symbol: Symbol) -> dict[str, object]:
    return {
        "kind": symbol.kind,
        "name": symbol.name,
        "line": symbol.line,
        "signature": symbol.signature,
        "decorators": list(symbol.decorators),
        "parent": symbol.parent,
    }


def _symbol_from_cache(raw: object) -> Symbol | None:
    if not isinstance(raw, dict):
        return None
    try:
        kind = raw["kind"]
        name = raw["name"]
        line = raw["line"]
        signature = raw["signature"]
        decorators = raw.get("decorators", [])
        parent = raw.get("parent", "")
    except KeyError:
        return None
    if not isinstance(kind, str) or not isinstance(name, str) or not isinstance(line, int):
        return None
    if not isinstance(signature, str) or not isinstance(parent, str):
        return None
    if line < 1 or not isinstance(decorators, list):
        return None
    if not all(isinstance(decorator, str) for decorator in decorators):
        return None
    return Symbol(kind, name, line, signature, tuple(decorators), parent)


def _entry_to_cache(entry: FileSymbols, mtime_ns: int, size: int) -> dict[str, object]:
    return {
        "mtime_ns": int(mtime_ns),
        "size": int(size),
        "module_doc": entry.module_doc,
        "symbols": [_symbol_to_cache(symbol) for symbol in entry.symbols],
    }


def _entry_from_cache(rel_path: str, raw: dict[str, object]) -> FileSymbols | None:
    module_doc = raw.get("module_doc", "")
    raw_symbols = raw.get("symbols", [])
    if not isinstance(module_doc, str) or not isinstance(raw_symbols, list):
        return None
    symbols: list[Symbol] = []
    for raw_symbol in raw_symbols:
        symbol = _symbol_from_cache(raw_symbol)
        if symbol is None:
            return None
        symbols.append(symbol)
    return FileSymbols(rel_path, module_doc, tuple(symbols))


def _load_cache(root: Path) -> dict[str, dict[str, object]]:
    try:
        raw = json.loads(_cache_path(root).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, RecursionError):
        return {}
    if not isinstance(raw, dict) or raw.get("version") != _CACHE_VERSION:
        return {}
    if raw.get("root") != str(root):
        return {}
    files = raw.get("files")
    if not isinstance(files, dict):
        return {}
    return {
        key: value
        for key, value in files.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _save_cache(root: Path, files: dict[str, dict[str, object]]) -> None:
    payload = {
        "version": _CACHE_VERSION,
        "root": str(root),
        "files": {path: files[path] for path in sorted(files)},
    }
    temp_path: str | None = None
    try:
        cache_path = _cache_path(root)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_path = tempfile.mkstemp(
            prefix=f"{cache_path.name}.", suffix=".tmp", dir=str(cache_path.parent)
        )
        os.close(descriptor)
        Path(temp_path).write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )
        os.replace(temp_path, cache_path)
        temp_path = None
    except (OSError, TypeError, ValueError):
        return
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Collection, ranking and rendering
# ---------------------------------------------------------------------------


def _scan(root: Path, *, use_cache: bool) -> tuple[list[FileSymbols], dict[str, Counter[str]]]:
    rel_paths = _iter_source_files(root)
    cached = _load_cache(root) if use_cache else {}
    entries: list[FileSymbols] = []
    token_counts: dict[str, Counter[str]] = {}
    cache_payload: dict[str, dict[str, object]] = {}

    for rel_path in rel_paths:
        source = _read_source(root, rel_path)
        if source is None:
            continue

        token_counts[rel_path] = Counter(_IDENTIFIER_RE.findall(source.text))
        cached_entry = cached.get(rel_path)
        entry: FileSymbols | None = None
        if cached_entry is not None:
            if (
                cached_entry.get("mtime_ns") == source.mtime_ns
                and cached_entry.get("size") == source.size
            ):
                entry = _entry_from_cache(rel_path, cached_entry)
        if entry is None:
            module_doc, symbols = _extract_file(rel_path, source.text)
            entry = FileSymbols(rel_path, module_doc, tuple(symbols))

        entries.append(entry)
        if use_cache:
            cache_payload[rel_path] = _entry_to_cache(entry, source.mtime_ns, source.size)

    if use_cache:
        _save_cache(root, cache_payload)
    return entries, token_counts


def _reference_counts(
    entries: list[FileSymbols], token_counts: dict[str, Counter[str]]
) -> dict[str, int]:
    names_by_file: dict[str, set[str]] = {}
    all_names: set[str] = set()
    for entry in entries:
        names = {
            symbol.name
            for symbol in entry.symbols
            if not symbol.parent and symbol.kind in _RANKABLE_KINDS
        }
        names_by_file[entry.path] = names
        all_names.update(names)

    totals = {
        name: sum(counter.get(name, 0) for counter in token_counts.values()) for name in all_names
    }
    counts: dict[str, int] = {}
    for entry in entries:
        own_counts = token_counts.get(entry.path, Counter())
        counts[entry.path] = sum(
            totals.get(name, 0) - own_counts.get(name, 0) for name in names_by_file[entry.path]
        )
    return counts


def _render_file(entry: FileSymbols) -> str:
    if not entry.symbols and not entry.module_doc:
        return ""
    header = entry.path
    if entry.module_doc:
        header = f"{header}: {entry.module_doc}"
    lines = [header]
    for symbol in entry.symbols:
        signature = symbol.signature
        if symbol.decorators:
            decorators = " ".join(f"@{decorator}" for decorator in symbol.decorators)
            signature = f"{decorators} {signature}"
        lines.append(f"  {signature} [L{symbol.line}]")
    return "\n".join(lines)


def collect_symbols(root: Path) -> list[FileSymbols]:
    """Collect symbols for every scanned source file under *root*.

    The result is sorted by relative POSIX path and is independent of the
    cache (this function always parses fresh content). Files with syntax
    errors, unsupported content or no declarations are still represented by
    an entry with no symbols, unless the file itself had to be skipped.

    Args:
        root: Repository root. A missing or non-directory path returns ``[]``.

    Returns:
        A list of :class:`FileSymbols`, one per readable supported source file.
    """
    root_path = _normalize_root(root)
    if not root_path.is_dir():
        return []
    entries, _ = _scan(root_path, use_cache=False)
    return entries


def build_repo_map(root: Path, max_tokens: int = DEFAULT_MAX_TOKENS, use_cache: bool = True) -> str:
    """Build a compact, symbol-level repository map under a token budget.

    Files are ranked by reference count, then closeness to the root, then path
    (see the module docstring for details). The rendered map contains one
    header line per file and one line per declaration, with no bodies.
    Low-ranked entries are removed until ``ceil(len(map) / 4) <= max_tokens``.

    Args:
        root: Repository root. A missing or non-directory path returns ``""``.
        max_tokens: Maximum estimated tokens for the returned map.
        use_cache: Read/write the per-root JSON symbol cache. ``False``
            bypasses both reads and writes.

    Returns:
        The rendered map, or ``""`` when the repository has nothing to show or
        even the top-ranked entry cannot fit the budget.
    """
    if max_tokens <= 0:
        return ""
    root_path = _normalize_root(root)
    if not root_path.is_dir():
        return ""

    entries, token_counts = _scan(root_path, use_cache=use_cache)
    counts = _reference_counts(entries, token_counts)
    ranked = sorted(
        (entry for entry in entries if entry.symbols or entry.module_doc),
        key=lambda entry: (-counts.get(entry.path, 0), entry.path.count("/"), entry.path),
    )
    blocks = [block for entry in ranked if (block := _render_file(entry))]
    if not blocks:
        return ""

    total_chars = sum(len(block) for block in blocks) + len(blocks) - 1
    while blocks and _tokens_for_chars(total_chars) > max_tokens:
        removed = blocks.pop()
        total_chars -= len(removed) + (1 if blocks else 0)
    return "\n".join(blocks)
