"""Repository map: symbol extraction, caching and rendering.

Split out of ``apex.repomap`` so that each module keeps one
responsibility.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .repomap_types import (
    Symbol,
    _collapse,
    _summarize_doc,
)

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

_JS_SUFFIXES = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"})

_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})

__all__ = [
    "_GO_FUNC_RE",
    "_GO_TYPE_RE",
    "_JS_ARROW_RE",
    "_JS_CLASS_RE",
    "_JS_ENUM_RE",
    "_JS_FUNCTION_RE",
    "_JS_INTERFACE_RE",
    "_JS_TYPE_RE",
    "_RUST_ENUM_RE",
    "_RUST_FN_RE",
    "_RUST_IMPL_RE",
    "_RUST_STRUCT_RE",
    "_RUST_TRAIT_RE",
    "_RUST_TYPE_RE",
    "_RUST_VISIBILITY",
    "_declaration_signature",
    "_extract_file",
    "_extract_go",
    "_extract_javascript",
    "_extract_python",
    "_extract_rust",
    "_go_receiver_type",
    "_iter_code_lines",
    "_python_class_signature",
    "_python_decorators",
    "_python_function_signature",
    "_rust_impl_name",
]


def _python_decorators(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, ...]:
    decorators: list[str] = []
    for decorator in node.decorator_list:
        try:
            decorators.append(_collapse(ast.unparse(decorator)))
        except Exception:  # pragma: no cover - defensive for exotic AST nodes  # noqa: BLE001, S112
            continue
    return tuple(decorators)


def _python_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    try:
        arguments = ast.unparse(node.args)
    except Exception:  # pragma: no cover - defensive for exotic AST nodes  # noqa: BLE001
        arguments = ""
    returns = ""
    if node.returns is not None:
        try:
            returns = f" -> {ast.unparse(node.returns)}"
        except Exception:  # pragma: no cover - defensive for exotic AST nodes  # noqa: BLE001
            returns = ""
    return _collapse(f"{prefix} {node.name}({arguments}){returns}")


def _unparse(node: ast.AST) -> str | None:
    """The source of an AST node, or ``None`` when it cannot be rendered."""
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - defensive for exotic AST nodes  # noqa: BLE001
        return None


def _class_bases(node: ast.ClassDef) -> list[str]:
    """The rendered base classes of a class definition."""
    rendered = (_unparse(base) for base in node.bases)
    return [base for base in rendered if base is not None]


def _class_keywords(node: ast.ClassDef) -> list[str]:
    """The rendered keyword arguments of a class definition."""
    parts: list[str] = []
    for keyword in node.keywords:
        value = _unparse(keyword.value)
        if value is None:
            continue
        parts.append(f"{keyword.arg}={value}" if keyword.arg else f"**{value}")
    return parts


def _python_class_signature(node: ast.ClassDef) -> str:
    parts = [*_class_bases(node), *_class_keywords(node)]
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
        add_class_children(node, qualified)

    def add_class_children(node: ast.ClassDef, qualified: str) -> None:
        """Record the methods and nested classes of a class definition."""
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
        _add_module_node(node, symbols, add_class)

    symbols.sort(key=lambda symbol: symbol.line)
    return module_doc, symbols


def _add_module_node(
    node: ast.stmt, symbols: list[Symbol], add_class: Callable[[ast.ClassDef, str], None]
) -> None:
    """Record one top-level statement of a module."""
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

_GO_FUNC_RE = re.compile(r"^func\s+(?:\((?P<receiver>[^)]*)\)\s*)?(?P<name>[A-Za-z_]\w*)")
_GO_TYPE_RE = re.compile(r"^type\s+(?P<name>[A-Za-z_]\w*)(?:\[[^\]]*\])?\s+(?P<rest>\S.*)$")


def _rust_impl_name(signature: str) -> str:
    target = re.sub(r"^(?:unsafe\s+)?impl\s*", "", signature)
    target = re.sub(r"^<[^>]*>\s*", "", target)
    target = target.split(" where ", 1)[0]
    if " for " in target:
        target = target.split(" for ", 1)[1]
    target = target.split("<", 1)[0].strip().lstrip("!&").strip()
    parts = target.split()
    return parts[-1] if parts else "impl"


def _go_receiver_type(receiver: str | None) -> str:
    if not receiver:
        return ""
    identifiers = _IDENTIFIER_RE.findall(receiver.split("[", 1)[0])
    return identifiers[-1] if identifiers else ""


def _iter_code_lines(text: str) -> Iterator[str]:
    """Yield lines with C-style comments removed, preserving line numbers.

    This is deliberately lightweight: it protects declaration matching from
    commented-out code without trying to be a JavaScript/Rust/Go lexer. Odd
    files still yield lines and can never make the scan crash.
    """
    in_block = False
    for line in text.splitlines():
        in_block, code = _strip_block_comment(line, in_block)
        yield _strip_line_comment(code)


def _strip_block_comment(code: str, in_block: bool) -> tuple[bool, str]:
    """Remove the C-style block comments of a line."""
    if in_block:
        code, in_block = _resume_block(code)
        if in_block:
            return True, ""
    return _strip_inline_blocks(code)


def _strip_inline_blocks(code: str) -> tuple[bool, str]:
    """Remove the complete block comments of a line."""
    while True:
        start = code.find("/*")
        if start == -1:
            return False, code
        end = code.find("*/", start + 2)
        if end == -1:
            return True, code[:start]
        code = code[:start] + code[end + 2 :]


def _resume_block(code: str) -> tuple[str, bool]:
    """Skip the tail of a block comment, returning the code that follows."""
    end = code.find("*/")
    if end == -1:
        return "", True
    return code[end + 2 :], False


def _strip_line_comment(code: str) -> str:
    """Remove the ``//`` comment of a line."""
    line_comment = code.find("//")
    if line_comment != -1:
        return code[:line_comment]
    return code


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


@dataclass(frozen=True)
class _DeclarationRule:
    """One declaration pattern and how to turn a match into a symbol."""

    pattern: re.Pattern[str]
    make: Callable[[re.Match[str], str, int], Symbol]
    keep_arrow: bool = False


def _named_rule(pattern: re.Pattern[str], kind: str) -> _DeclarationRule:
    """A rule whose symbol name comes from the ``name`` group."""
    return _DeclarationRule(pattern, _named_symbol(kind))


def _named_symbol(kind: str) -> Callable[[re.Match[str], str, int], Symbol]:
    """Build the maker of a rule whose name comes from the ``name`` group."""

    def make(match: re.Match[str], signature: str, line_number: int) -> Symbol:
        return Symbol(kind, match.group("name"), line_number, signature)

    return make


def _rust_impl_symbol(_match: re.Match[str], signature: str, line_number: int) -> Symbol:
    """Build the symbol of a Rust ``impl`` block."""
    return Symbol("impl", _rust_impl_name(signature), line_number, signature)


def _go_func_symbol(match: re.Match[str], signature: str, line_number: int) -> Symbol:
    """Build the symbol of a Go function or method."""
    receiver = match.group("receiver")
    return Symbol(
        "method" if receiver else "function",
        match.group("name"),
        line_number,
        signature,
        parent=_go_receiver_type(receiver),
    )


def _go_type_kind(body: str) -> str:
    """The kind of a Go ``type`` declaration."""
    if body.startswith("struct"):
        return "struct"
    if body.startswith("interface"):
        return "interface"
    return "type"


def _go_type_symbol(match: re.Match[str], signature: str, line_number: int) -> Symbol:
    """Build the symbol of a Go ``type`` declaration."""
    body = match.group("rest").lstrip("= ").strip()
    return Symbol(_go_type_kind(body), match.group("name"), line_number, signature)


def _match_declaration(
    line: str, line_number: int, rules: tuple[_DeclarationRule, ...]
) -> Symbol | None:
    """The symbol a declaration line matches, if any."""
    for rule in rules:
        match = rule.pattern.match(line)
        if match is None:
            continue
        signature = _declaration_signature(line, keep_arrow=rule.keep_arrow)
        return rule.make(match, signature, line_number)
    return None


def _collect_declarations(text: str, rules: tuple[_DeclarationRule, ...]) -> list[Symbol]:
    """Every symbol the declaration rules find in a source text."""
    symbols: list[Symbol] = []
    for line_number, raw_line in enumerate(_iter_code_lines(text), start=1):
        line = raw_line.strip()
        if not line:
            continue
        symbol = _match_declaration(line, line_number, rules)
        if symbol is not None:
            symbols.append(symbol)
    return symbols


_JS_RULES = (
    _named_rule(_JS_CLASS_RE, "class"),
    _named_rule(_JS_FUNCTION_RE, "function"),
    _named_rule(_JS_INTERFACE_RE, "interface"),
    _named_rule(_JS_TYPE_RE, "type"),
    _named_rule(_JS_ENUM_RE, "enum"),
    _DeclarationRule(_JS_ARROW_RE, _named_symbol("function"), keep_arrow=True),
)

_RUST_RULES = (
    _named_rule(_RUST_STRUCT_RE, "struct"),
    _named_rule(_RUST_ENUM_RE, "enum"),
    _named_rule(_RUST_TRAIT_RE, "trait"),
    _DeclarationRule(_RUST_IMPL_RE, _rust_impl_symbol),
    _named_rule(_RUST_FN_RE, "function"),
    _named_rule(_RUST_TYPE_RE, "type"),
)

_GO_RULES = (
    _DeclarationRule(_GO_FUNC_RE, _go_func_symbol),
    _DeclarationRule(_GO_TYPE_RE, _go_type_symbol),
)


def _extract_javascript(text: str) -> tuple[str, list[Symbol]]:
    return "", _collect_declarations(text, _JS_RULES)


def _extract_rust(text: str) -> tuple[str, list[Symbol]]:
    return "", _collect_declarations(text, _RUST_RULES)


def _extract_go(text: str) -> tuple[str, list[Symbol]]:
    return "", _collect_declarations(text, _GO_RULES)


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
    except Exception:  # pragma: no cover - last-resort guard for odd input  # noqa: BLE001
        return "", []
    return "", []
