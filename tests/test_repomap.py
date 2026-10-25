"""Tests for the symbol-level repository map engine."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apex import repomap
from apex.context import get_repo_map, get_symbol_map
from apex.repomap import (
    MAX_FILE_BYTES,
    build_repo_map,
    collect_symbols,
    estimate_tokens,
)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Keep cache reads/writes out of the real home directory."""
    cache = tmp_path / "cache"
    monkeypatch.setattr(repomap, "_cache_dir", lambda: cache)
    return cache


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write(repo: Path, name: str, content: str) -> Path:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _entry(repo: Path, name: str):
    return next(entry for entry in collect_symbols(repo) if entry.path == name)


def _symbol(repo: Path, file_name: str, symbol_name: str):
    return next(symbol for symbol in _entry(repo, file_name).symbols if symbol.name == symbol_name)


PYTHON_SOURCE = '''"""Geometry helpers.

Longer module documentation that should not be emitted.
"""

from dataclasses import dataclass


@dataclass
class Point(Base):
    def norm(self, scale: float = 1.0) -> float:
        return 0.0

    @staticmethod
    async def load(path: str) -> "Point":
        return Point()

    class Meta:
        pass


@app.route("/")
def index(name: str = "world") -> str:
    return name
'''


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------


class TestPythonSymbols:
    def test_classes_functions_methods_and_signatures(self, repo):
        _write(repo, "shapes.py", PYTHON_SOURCE)

        entry = _entry(repo, "shapes.py")
        point = _symbol(repo, "shapes.py", "Point")
        norm = _symbol(repo, "shapes.py", "norm")
        load = _symbol(repo, "shapes.py", "load")
        index = _symbol(repo, "shapes.py", "index")

        assert point.kind == "class"
        assert point.signature == "class Point(Base)"
        assert point.decorators == ("dataclass",)
        assert point.parent == ""
        assert point.line == 10

        assert norm.kind == "method"
        assert norm.parent == "Point"
        assert "scale: float=1.0" in norm.signature
        assert norm.signature.endswith("-> float")
        assert norm.line == 11

        assert load.kind == "method"
        assert "async def load" in load.signature
        assert "path: str" in load.signature
        assert load.decorators == ("staticmethod",)
        assert load.line == 15

        assert index.kind == "function"
        assert index.decorators == ("app.route('/')",)
        assert index.line == 23

        assert [symbol.name for symbol in entry.symbols] == [
            "Point",
            "norm",
            "load",
            "Meta",
            "index",
        ]

    def test_module_docstring_summary(self, repo):
        _write(repo, "shapes.py", PYTHON_SOURCE)
        assert _entry(repo, "shapes.py").module_doc == "Geometry helpers."

        _write(
            repo,
            "long_doc.py",
            '"""A first line that is useful. ' + "x" * 200 + '"""\n\ndef f():\n    pass\n',
        )
        summary = _entry(repo, "long_doc.py").module_doc
        assert summary.startswith("A first line that is useful.")
        assert summary.endswith("...")
        assert len(summary) <= 120

    def test_map_emits_decorators_and_line_numbers_in_source_order(self, repo):
        _write(repo, "shapes.py", PYTHON_SOURCE)
        result = build_repo_map(repo, use_cache=False)

        assert "@dataclass class Point(Base) [L10]" in result
        assert "@staticmethod async def load(path: str) -> 'Point' [L15]" in result
        assert "@app.route('/') def index(name: str='world') -> str [L23]" in result
        assert "return" not in result
        assert result.index("class Point") < result.index("def norm")
        assert result.index("def norm") < result.index("async def load")
        assert result.index("async def load") < result.index("class Meta")
        assert result.index("class Meta") < result.index("def index")

    def test_syntax_error_file_is_skipped_without_crashing(self, repo):
        _write(repo, "broken.py", "def broken(:\n")
        _write(repo, "good.py", "def fine():\n    pass\n")

        entries = {entry.path: entry for entry in collect_symbols(repo)}
        assert entries["broken.py"].symbols == ()
        assert "def fine()" in build_repo_map(repo, use_cache=False)
        assert "broken.py" not in build_repo_map(repo, use_cache=False)

    def test_non_utf8_and_binary_files_are_skipped(self, repo):
        (repo / "latin.py").write_bytes(b"def caf\xe9():\n    pass\n")
        (repo / "binary.py").write_bytes(b"def bin():\n\x00\x01\x02\n")
        _write(repo, "good.py", "def good():\n    pass\n")

        paths = {entry.path for entry in collect_symbols(repo)}
        assert paths == {"good.py"}

    def test_oversized_file_is_skipped(self, repo):
        _write(repo, "big.py", "# " + "x" * MAX_FILE_BYTES)
        _write(repo, "small.py", "def small():\n    pass\n")

        paths = {entry.path for entry in collect_symbols(repo)}
        assert "big.py" not in paths
        assert "small.py" in paths


# ---------------------------------------------------------------------------
# JavaScript / TypeScript / TSX
# ---------------------------------------------------------------------------


class TestJavaScriptAndTypeScript:
    def test_js_ts_declarations(self, repo):
        _write(
            repo,
            "app.ts",
            """import { Base } from "./base";

// export class Commented {}
/*
export class Ghost {}
*/
export interface Props extends Base {
  value: number;
}

export type ID = string;
export enum Role {
  Admin,
}

export class View extends Base {
  render() {}
}

export async function load(id: ID): Promise<Props> {
  return { value: 1 };
}

export const make = (value: number): View => {
  return new View();
};
""",
        )

        entry = _entry(repo, "app.ts")
        names = {symbol.name: symbol for symbol in entry.symbols}
        assert set(names) == {"Props", "ID", "Role", "View", "load", "make"}
        assert "Commented" not in names
        assert "Ghost" not in names
        assert names["Props"].kind == "interface"
        assert names["ID"].kind == "type"
        assert names["Role"].kind == "enum"
        assert names["View"].kind == "class"
        assert names["load"].kind == "function"
        assert names["make"].kind == "function"
        assert names["load"].line == 20
        assert "async function load" in names["load"].signature
        assert "=>" in names["make"].signature

    def test_tsx_is_scanned(self, repo):
        _write(
            repo,
            "App.tsx",
            "export function App(): JSX.Element {\n  return <div />;\n}\n",
        )
        result = build_repo_map(repo, use_cache=False)
        assert "App.tsx" in result
        assert "export function App(): JSX.Element" in result


# ---------------------------------------------------------------------------
# Rust / Go
# ---------------------------------------------------------------------------


class TestRustAndGo:
    def test_rust_declarations(self, repo):
        _write(
            repo,
            "lib.rs",
            """pub struct Config {
    pub name: String,
}

pub enum Mode {
    Fast,
}

pub trait Runner {
    fn run(&self);
}

impl Runner for Config {
    pub fn run(&self) {}
}

// pub fn hidden() {}
pub async fn load(path: &str) -> Result<Config> {
    todo!()
}

pub type Alias = Config;
""",
        )

        symbols = _entry(repo, "lib.rs").symbols
        names = {symbol.name for symbol in symbols}
        assert {"Config", "Mode", "Runner", "load", "Alias"} <= names
        assert "hidden" not in names
        assert any(
            symbol.kind == "impl" and symbol.signature == "impl Runner for Config"
            for symbol in symbols
        )
        assert any(
            symbol.kind == "function" and symbol.signature.startswith("pub async fn load")
            for symbol in symbols
        )
        assert _symbol(repo, "lib.rs", "Config").line == 1
        assert _symbol(repo, "lib.rs", "Alias").line == 22

        result = build_repo_map(repo, use_cache=False)
        assert "impl Runner for Config [L13]" in result
        assert "pub async fn load(path: &str) -> Result<Config> [L18]" in result

    def test_go_declarations_and_method_receiver(self, repo):
        _write(
            repo,
            "server.go",
            """package main

type Server struct {
    name string
}

type Handler interface {
    Handle() error
}

func main() {
}

func (s *Server) Start(ctx context.Context) error {
    return nil
}

type ID = string

type Cache[K comparable, V any] struct {
    items map[K]V
}
""",
        )

        entry = _entry(repo, "server.go")
        start = next(symbol for symbol in entry.symbols if symbol.name == "Start")
        assert start.kind == "method"
        assert start.parent == "Server"
        assert "func (s *Server) Start" in start.signature

        kinds = {symbol.name: symbol.kind for symbol in entry.symbols}
        assert kinds["Server"] == "struct"
        assert kinds["Handler"] == "interface"
        assert kinds["main"] == "function"
        assert kinds["ID"] == "type"
        assert kinds["Cache"] == "struct"

        result = build_repo_map(repo, use_cache=False)
        assert "type Server struct [L3]" in result
        assert "func (s *Server) Start(ctx context.Context) error [L14]" in result
        assert "type Cache[K comparable, V any] struct [L20]" in result


# ---------------------------------------------------------------------------
# Scanning / ignoring
# ---------------------------------------------------------------------------


class TestScanning:
    def test_ignored_directories(self, repo):
        for directory in repomap.IGNORED_DIRS:
            target = repo / directory
            target.mkdir(parents=True, exist_ok=True)
            (target / "hidden.py").write_text("def hidden():\n    pass\n", encoding="utf-8")
        _write(repo, "src/app.py", "def app():\n    pass\n")

        paths = {entry.path for entry in collect_symbols(repo)}
        assert paths == {"src/app.py"}

    def test_gitignore_names_globs_directories_and_negation(self, repo):
        _write(
            repo,
            ".gitignore",
            """# generated files
secret.py
secret_*.py
!secret_keep.py
*.gen.py
docs/generated/
/root_only.py
""",
        )
        _write(repo, "secret.py", "def secret():\n    pass\n")
        _write(repo, "secret_drop.py", "def dropped():\n    pass\n")
        _write(repo, "secret_keep.py", "def kept():\n    pass\n")
        _write(repo, "models.gen.py", "def generated():\n    pass\n")
        _write(repo, "keep.py", "def keep():\n    pass\n")
        _write(repo, "app.py", "def app():\n    pass\n")
        _write(repo, "docs/generated/deep.py", "def deep():\n    pass\n")
        _write(repo, "docs/normal.py", "def normal():\n    pass\n")
        _write(repo, "root_only.py", "def root_only():\n    pass\n")
        _write(repo, "sub/root_only.py", "def nested_root_only():\n    pass\n")

        paths = {entry.path for entry in collect_symbols(repo)}
        assert "keep.py" in paths
        assert "app.py" in paths
        assert "secret_keep.py" in paths
        assert "docs/normal.py" in paths
        assert "sub/root_only.py" in paths
        assert "secret.py" not in paths
        assert "secret_drop.py" not in paths
        assert "models.gen.py" not in paths
        assert "docs/generated/deep.py" not in paths
        assert "root_only.py" not in paths

    def test_collect_symbols_is_sorted_and_deterministic(self, repo):
        _write(repo, "z.py", "def z():\n    pass\n")
        _write(repo, "a/nested.py", "def nested():\n    pass\n")
        _write(repo, "m.py", "def m():\n    pass\n")

        first = [entry.path for entry in collect_symbols(repo)]
        second = [entry.path for entry in collect_symbols(repo)]
        assert first == ["a/nested.py", "m.py", "z.py"]
        assert first == second


# ---------------------------------------------------------------------------
# Ranking and token budget
# ---------------------------------------------------------------------------


class TestRankingAndBudget:
    def test_reference_count_then_depth_then_path(self, repo):
        _write(repo, "core.py", "class Widget:\n    pass\n")
        _write(repo, "alpha.py", "def alpha():\n    pass\n")
        _write(repo, "main.py", "from core import Widget\n\ndef main():\n    Widget()\n")
        _write(repo, "nested/deep.py", "def deep():\n    pass\n")

        result = build_repo_map(repo, use_cache=False)
        assert result.index("core.py") < result.index("alpha.py")
        assert result.index("alpha.py") < result.index("main.py")
        assert result.index("main.py") < result.index("nested/deep.py")

    def test_budget_trims_lowest_ranked_entries_and_is_deterministic(self, repo):
        for index in range(12):
            _write(
                repo,
                f"file_{index:02d}.py",
                f'"""Module {index}."""\n\ndef function_{index}() -> None:\n    pass\n',
            )

        first = build_repo_map(repo, max_tokens=45, use_cache=False)
        second = build_repo_map(repo, max_tokens=45, use_cache=False)

        assert first == second
        assert estimate_tokens(first) <= 45
        assert "file_00.py" in first
        assert "file_11.py" not in first

    def test_zero_or_tiny_budget_returns_empty(self, repo):
        _write(repo, "main.py", "def main():\n    pass\n")
        assert build_repo_map(repo, max_tokens=0, use_cache=False) == ""
        assert build_repo_map(repo, max_tokens=1, use_cache=False) == ""

    def test_estimate_tokens_rounds_up(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("a") == 1
        assert estimate_tokens("abcd") == 1
        assert estimate_tokens("abcde") == 2


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_cache_is_created_keyed_by_root_and_hit_skips_extraction(
        self, repo, tmp_path, monkeypatch
    ):
        _write(repo, "mod.py", "def hello():\n    pass\n")
        calls: list[str] = []
        original = repomap._extract_file

        def counting_extract(path, text):
            calls.append(path)
            return original(path, text)

        monkeypatch.setattr(repomap, "_extract_file", counting_extract)

        first = build_repo_map(repo)
        expected_name = hashlib.sha256(str(repo.resolve()).encode("utf-8")).hexdigest()
        cache_file = tmp_path / "cache" / f"{expected_name}.json"
        assert cache_file.exists()

        second = build_repo_map(repo)
        assert calls == ["mod.py"]
        assert second == first

        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert payload["root"] == str(repo.resolve())
        assert payload["files"]["mod.py"]["size"] == (repo / "mod.py").stat().st_size

    def test_cache_invalidates_changed_file(self, repo):
        path = _write(repo, "mod.py", "def first():\n    pass\n")
        assert "def first()" in build_repo_map(repo)

        path.write_text("def second():\n    pass\n", encoding="utf-8")
        result = build_repo_map(repo)
        assert "def second()" in result
        assert "def first()" not in result

    def test_corrupt_cache_is_silently_ignored(self, repo, tmp_path):
        _write(repo, "mod.py", "def hello():\n    pass\n")
        build_repo_map(repo)
        cache_file = next((tmp_path / "cache").glob("*.json"))
        cache_file.write_text("{ this is not json", encoding="utf-8")

        result = build_repo_map(repo)
        assert "def hello()" in result
        assert json.loads(cache_file.read_text(encoding="utf-8"))["version"] == 1

    def test_corrupt_file_entry_is_reparsed(self, repo, tmp_path):
        _write(repo, "mod.py", "def hello():\n    pass\n")
        build_repo_map(repo)
        cache_file = next((tmp_path / "cache").glob("*.json"))
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        payload["files"]["mod.py"]["symbols"] = "not-a-list"
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        result = build_repo_map(repo)
        assert "def hello()" in result

    def test_use_cache_false_bypasses_reads_and_writes(self, repo, tmp_path, monkeypatch):
        _write(repo, "mod.py", "def hello():\n    pass\n")
        read_calls: list[Path] = []
        write_calls: list[dict] = []
        monkeypatch.setattr(repomap, "_load_cache", lambda root: read_calls.append(root) or {})
        monkeypatch.setattr(repomap, "_save_cache", lambda root, files: write_calls.append(files))

        assert "def hello()" in build_repo_map(repo, use_cache=False)
        assert read_calls == []
        assert write_calls == []
        assert not (tmp_path / "cache").exists()

    def test_different_roots_have_different_cache_files(self, repo, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        _write(repo, "one.py", "def one():\n    pass\n")
        _write(other, "two.py", "def two():\n    pass\n")

        build_repo_map(repo)
        build_repo_map(other)
        assert len(list((tmp_path / "cache").glob("*.json"))) == 2


# ---------------------------------------------------------------------------
# Public API and integration
# ---------------------------------------------------------------------------


class TestPublicAPI:
    def test_empty_and_missing_roots(self, repo, tmp_path):
        assert build_repo_map(repo) == ""
        assert collect_symbols(repo) == []
        assert build_repo_map(tmp_path / "missing") == ""
        assert collect_symbols(tmp_path / "missing") == []

        a_file = _write(repo, "main.py", "def main():\n    pass\n")
        assert build_repo_map(a_file) == ""
        assert collect_symbols(a_file) == []

    def test_collect_symbols_does_not_use_cache(self, repo, monkeypatch):
        _write(repo, "mod.py", "def hello():\n    pass\n")
        monkeypatch.setattr(
            repomap,
            "_load_cache",
            lambda root: (_ for _ in ()).throw(AssertionError("cache should not be read")),
        )
        assert collect_symbols(repo)[0].symbols[0].name == "hello"

    def test_get_symbol_map_delegates_and_honours_budget(self, repo):
        _write(repo, "main.py", "def main():\n    pass\n")
        result = get_symbol_map(repo, max_tokens=40)
        assert "def main()" in result
        assert estimate_tokens(result) <= 40

        assert get_symbol_map(repo / "missing").startswith("ERROR:")
        file_path = repo / "main.py"
        assert get_symbol_map(file_path).startswith("ERROR: Not a directory:")

    def test_get_repo_map_keeps_its_original_format(self, repo):
        _write(repo, "main.py", "print('hello')\n")
        _write(repo, "settings.json", "{}")

        result = get_repo_map(repo)
        assert result.startswith(f"Repository: {repo.name}")
        assert "[SOURCE FILES]" in result
        assert "main.py" in result
        assert "[CONFIG FILES]" in result
        assert "settings.json" in result
        assert "def main" not in result


class TestToolIntegration:
    def test_repo_map_tool_is_registered_and_dispatches(self, repo):
        from apex.tools import TOOL_SCHEMAS, ToolExecutor

        names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
        assert "repo_map" in names

        _write(repo, "main.py", "def main():\n    pass\n")
        executor = ToolExecutor(cwd=repo)
        result = executor.execute("repo_map", {"max_tokens": 200})
        assert "def main()" in result

    def test_repo_map_tool_reports_missing_path(self, repo):
        from apex.tools import ToolExecutor

        executor = ToolExecutor(cwd=repo)
        result = executor.execute("repo_map", {"path": "does-not-exist"})
        assert result.startswith("ERROR:")
