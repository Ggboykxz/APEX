"""Repository map: symbol extraction, caching and rendering.

Split out of ``apex.repomap`` so that each module keeps one
responsibility.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .repomap_symbols import (
    _IDENTIFIER_RE,
    _JS_SUFFIXES,
    _PYTHON_SUFFIXES,
    _extract_file,
)
from .repomap_types import (
    _MODULE_DOC_CHARS,
    _WHITESPACE_RE,
    FileSymbols,
    Symbol,
    _collapse,
    _SourceFile,
    _summarize_doc,
)

__all__ = [
    "DEFAULT_MAX_TOKENS",
    "IGNORED_DIRS",
    "MAX_FILE_BYTES",
    "_CACHE_VERSION",
    "_IDENTIFIER_RE",
    "_JS_SUFFIXES",
    "_MODULE_DOC_CHARS",
    "_PYTHON_SUFFIXES",
    "_RANKABLE_KINDS",
    "_SOURCE_SUFFIXES",
    "_WHITESPACE_RE",
    "_GitIgnore",
    "_cache_dir",
    "_cache_path",
    "_collapse",
    "_entry_from_cache",
    "_entry_to_cache",
    "_is_cached_symbol",
    "_is_source_file",
    "_is_symlink",
    "_iter_source_files",
    "_kept_dirs",
    "_load_cache",
    "_normalize_root",
    "_parse_gitignore_rule",
    "_read_source",
    "_reference_counts",
    "_render_file",
    "_save_cache",
    "_scan",
    "_summarize_doc",
    "_symbol_from_cache",
    "_symbol_to_cache",
    "_tokens_for_chars",
    "build_repo_map",
    "collect_symbols",
    "estimate_tokens",
]

MAX_FILE_BYTES = 512 * 1024
DEFAULT_MAX_TOKENS = 2000
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
_SOURCE_SUFFIXES = _PYTHON_SUFFIXES | _JS_SUFFIXES | frozenset({".rs", ".go"})
_RANKABLE_KINDS = frozenset({"class", "enum", "function", "interface", "struct", "trait", "type"})


def _parse_gitignore_rule(raw: str) -> tuple[str, bool, bool, bool] | None:
    """Parse one .gitignore rule into ``(pattern, negated, dir_only, anchored)``."""
    line = _rule_text(raw)
    if line is None:
        return None

    negated = line.startswith("!")
    if negated:
        line = line[1:].strip()
        if not line:
            return None

    dir_only = line.endswith("/")
    if dir_only:
        line = line.rstrip("/")
    anchored = line.startswith("/")
    if anchored:
        line = line.lstrip("/")
    if not line:
        return None
    return line, negated, dir_only, anchored


def _rule_text(raw: str) -> str | None:
    """The pattern of a .gitignore line, or ``None`` when it carries none."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith(("\\#", "\\!")):
        line = line[1:]
    return line


def _rule_matches(rel_path: str, pattern: str, anchored: bool) -> bool:
    """Whether a .gitignore rule matches the path."""
    if anchored or "/" in pattern:
        return fnmatch.fnmatchcase(rel_path, pattern)
    return fnmatch.fnmatchcase(rel_path.rsplit("/", 1)[-1], pattern)


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
            rule = _parse_gitignore_rule(raw)
            if rule is not None:
                self._rules.append(rule)

    def is_ignored(self, rel_path: str, is_dir: bool) -> bool:
        """Return whether a relative POSIX path is ignored."""
        ignored = False
        for pattern, negated, dir_only, anchored in self._rules:
            if dir_only and not is_dir:
                continue
            if _rule_matches(rel_path, pattern, anchored):
                ignored = not negated
        return ignored


def estimate_tokens(text: str) -> int:
    """Estimate tokens for *text* as ``ceil(len(text) / 4)``."""
    return (len(text) + 3) // 4


def _tokens_for_chars(char_count: int) -> int:
    return (char_count + 3) // 4


def _normalize_root(root: Path | str) -> Path:
    try:
        return Path(root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return Path(root).expanduser().absolute()


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
        rel_dir = _relative_dir(current, root)
        dirnames[:] = _kept_dirs(current, rel_dir, dirnames, gitignore)
        found.extend(_source_files_of(current, rel_dir, filenames, gitignore))

    return sorted(found)


def _relative_dir(current: Path, root: Path) -> str:
    """The path of a directory relative to the scanned root."""
    try:
        rel_dir = current.relative_to(root).as_posix()
    except ValueError:
        return ""
    return "" if rel_dir == "." else rel_dir


def _source_files_of(
    current: Path, rel_dir: str, filenames: list[str], gitignore: _GitIgnore
) -> list[str]:
    """The scannable source files of one directory."""
    found = []
    for filename in sorted(filenames):
        rel_path = f"{rel_dir}/{filename}" if rel_dir else filename
        if _is_source_file(current, rel_dir, filename, gitignore):
            found.append(rel_path)
    return found


def _kept_dirs(
    current: Path, rel_dir: str, dirnames: list[str], gitignore: _GitIgnore
) -> list[str]:
    """The sub-directories that are worth scanning."""
    kept: list[str] = []
    for dirname in sorted(dirnames):
        if dirname in IGNORED_DIRS:
            continue
        if _is_symlink(current / dirname):
            continue
        rel_path = f"{rel_dir}/{dirname}" if rel_dir else dirname
        if gitignore.is_ignored(rel_path, True):
            continue
        kept.append(dirname)
    return kept


def _is_symlink(path: Path) -> bool:
    """Whether the path is a symbolic link."""
    try:
        return path.is_symlink()
    except OSError:
        return True


def _is_source_file(current: Path, rel_dir: str, filename: str, gitignore: _GitIgnore) -> bool:
    """Whether a file is a source file worth scanning."""
    if Path(filename).suffix.lower() not in _SOURCE_SUFFIXES:
        return False
    rel_path = f"{rel_dir}/{filename}" if rel_dir else filename
    return not gitignore.is_ignored(rel_path, False)


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


@dataclass(frozen=True)
class _CachedFields:
    """The symbol fields stored in the cache."""

    kind: object
    name: object
    line: object
    signature: object
    decorators: object
    parent: object


def _symbol_from_cache(raw: object) -> Symbol | None:
    if not isinstance(raw, dict):
        return None
    fields = _cached_fields(raw)
    if fields is None:
        return None
    if not _is_cached_symbol(fields):
        return None
    return Symbol(
        fields.kind,
        fields.name,
        fields.line,
        fields.signature,
        tuple(fields.decorators),
        fields.parent,
    )


def _cached_fields(raw: dict) -> _CachedFields | None:
    """The symbol fields read from the cache."""
    try:
        return _CachedFields(
            kind=raw["kind"],
            name=raw["name"],
            line=raw["line"],
            signature=raw["signature"],
            decorators=raw.get("decorators", []),
            parent=raw.get("parent", ""),
        )
    except KeyError:
        return None


def _is_cached_symbol(fields: _CachedFields) -> bool:
    """Whether the fields read from the cache describe a symbol."""
    if not _is_cached_identity(fields.kind, fields.name, fields.line):
        return False
    if not _is_cached_signature(fields.signature, fields.parent):
        return False
    return _is_cached_decorators(fields.decorators)


def _is_cached_identity(kind: object, name: object, line: object) -> bool:
    """Whether the cached identity fields describe a symbol."""
    if not isinstance(kind, str) or not isinstance(name, str):
        return False
    if not isinstance(line, int):
        return False
    return line >= 1


def _is_cached_signature(signature: object, parent: object) -> bool:
    """Whether the cached signature fields describe a symbol."""
    if not isinstance(signature, str):
        return False
    return isinstance(parent, str)


def _is_cached_decorators(decorators: object) -> bool:
    """Whether the cached decorators are a list of strings."""
    if not isinstance(decorators, list):
        return False
    return all(isinstance(decorator, str) for decorator in decorators)


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
    raw = _read_cache_file(root)
    if not _is_cache_for_root(raw, root):
        return {}
    files = raw.get("files")
    if not isinstance(files, dict):
        return {}
    return {
        key: value
        for key, value in files.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _read_cache_file(root: Path) -> dict[str, object]:
    """The raw cache payload of a root, or an empty mapping."""
    try:
        raw = json.loads(_cache_path(root).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, RecursionError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _is_cache_for_root(raw: dict[str, object], root: Path) -> bool:
    """Whether a cache payload was written for this root and this version."""
    if raw.get("version") != _CACHE_VERSION:
        return False
    return raw.get("root") == str(root)


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
        entry = _cached_entry(cached, rel_path, source)
        if entry is None:
            entry = _extract_entry(rel_path, source.text)
        token_counts[rel_path] = Counter(_IDENTIFIER_RE.findall(source.text))
        entries.append(entry)
        if use_cache:
            cache_payload[rel_path] = _entry_to_cache(entry, source.mtime_ns, source.size)

    if use_cache:
        _save_cache(root, cache_payload)
    return entries, token_counts


def _cached_entry(
    cached: dict[str, dict[str, object]], rel_path: str, source: _SourceFile
) -> FileSymbols | None:
    """The cached symbols of a file, when they are still up to date."""
    cached_entry = cached.get(rel_path)
    if cached_entry is None:
        return None
    if not _cache_matches(cached_entry, source):
        return None
    return _entry_from_cache(rel_path, cached_entry)


def _cache_matches(cached_entry: dict[str, object], source: _SourceFile) -> bool:
    """Whether the cache entry was written for this version of the file."""
    if cached_entry.get("mtime_ns") != source.mtime_ns:
        return False
    return cached_entry.get("size") == source.size


def _extract_entry(rel_path: str, text: str) -> FileSymbols:
    """Extract the symbols of one source file."""
    module_doc, symbols = _extract_file(rel_path, text)
    return FileSymbols(rel_path, module_doc, tuple(symbols))


def _rank_entries(entries: list[FileSymbols], counts: dict[str, int]) -> list[FileSymbols]:
    """The entries worth rendering, most referenced first."""
    return sorted(
        (entry for entry in entries if entry.symbols or entry.module_doc),
        key=lambda entry: (-counts.get(entry.path, 0), entry.path.count("/"), entry.path),
    )


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
    ranked = _rank_entries(entries, _reference_counts(entries, token_counts))
    blocks = [block for entry in ranked if (block := _render_file(entry))]
    if not blocks:
        return ""

    total_chars = sum(len(block) for block in blocks) + len(blocks) - 1
    while blocks and _tokens_for_chars(total_chars) > max_tokens:
        removed = blocks.pop()
        total_chars -= len(removed) + (1 if blocks else 0)
    return "\n".join(blocks)
