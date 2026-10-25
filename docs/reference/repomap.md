# Repository Map

APEX v2.5 introduces a **symbol-level repository map**: a compact, token-budgeted
view of a codebase containing file paths, module summaries, and declaration
signatures with line numbers — never file bodies.

The map is designed for LLM context windows. It gives the agent enough
structural knowledge to navigate a repository without spending thousands of
tokens on full files.

## Quick start

```python
from pathlib import Path

from apex.context import get_symbol_map
from apex.repomap import build_repo_map, collect_symbols

# Ready-to-inject text map (default budget: 2000 tokens)
print(get_symbol_map(Path(".")))

# Explicit budget
print(build_repo_map(Path("."), max_tokens=4000, use_cache=False))

# Structured data for custom tooling
for entry in collect_symbols(Path(".")):
    print(entry.path, len(entry.symbols))
```

From an agent session, the `repo_map` tool exposes the same engine:

```json
{
  "path": ".",
  "max_tokens": 2000
}
```

## How it works

1. **Scan** — walk the repository deterministically, skipping generated and
   dependency directories. The root `.gitignore` is honoured (comments,
   negation, directory-only rules, `/` anchors, and globs).
2. **Extract** — parse Python with `ast` (classes, functions, methods,
   decorators, signatures, module docstring summary). JavaScript, TypeScript,
   Rust, and Go use conservative, line-anchored regex extraction.
3. **Rank** — count cross-file references to top-level declarations. Files are
   sorted by reference count, then directory depth, then path. Definitions keep
   their source order inside a file.
4. **Render and trim** — one header line per file, one signature line per
   declaration. Lowest-ranked entries are removed until the estimated token
   count fits the budget (estimated as `ceil(characters / 4)`).
5. **Cache** — parsed symbols are cached per repository root to avoid reparsing
   unchanged files.

## Example output

```text
apex/context.py: Context builder for APEX - repository mapping and intelligent context.
  def get_repo_map(path: Path | None = None) -> str [L8]
  def get_symbol_map(path: Path | None = None, max_tokens: int = 2000) -> str [L...]
apex/repomap.py: Symbol-level repository map for token-budgeted context.
  class Symbol [L109]
  def build_repo_map(root: Path, max_tokens: int = DEFAULT_MAX_TOKENS, use_cache: bool = True) -> str [L874]
```

Each declaration line is `signature [Lline]`. Python decorators are rendered
inline. For non-Python languages the extracted signature is the declaration
line without its body.

## Cache

- Location: `~/.apex/cache/repomap/<sha256(absolute-root)>.json`
- Validity: per-file `mtime_ns` + size fingerprint; changed files are reparsed
- Writes are atomic (temporary file + replace), and corrupt or unreadable
  caches are silently ignored
- `use_cache=False` bypasses both reads and writes
- The cache never leaves `~/.apex` and never writes inside the target repository

## Supported languages

| Language | Extensions | Extraction |
|----------|------------|------------|
| Python | `.py`, `.pyi` | `ast` (classes, functions, methods, decorators, signatures) |
| JavaScript / TypeScript | `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts` | Regex (classes, functions, interfaces, types) |
| Rust | `.rs` | Regex (structs, enums, traits, impls, functions) |
| Go | `.go` | Regex (types, structs, interfaces, functions, methods) |

## Limits

- Non-Python extraction is heuristic: multi-line declarations, complex
  generics/templates, and some language-specific constructs may be missed.
- JavaScript/TypeScript class methods are not emitted as separate symbols.
- Only the **root** `.gitignore` is read; nested ignore files are not.
- Reference counting is textual, so comments and strings can inflate counts.
- Symlinked directories are skipped to avoid loops.
- A single top-ranked entry larger than the budget is omitted rather than
  partially truncated, so an extremely small budget can return an empty map.
- Cache freshness relies on `mtime` + size; same-size edits with preserved
  timestamps can remain stale until another change or `use_cache=False`.

## Tests

```bash
pytest tests/test_repomap.py -q
```

The suite covers Python/JS/TS/Rust/Go extraction, ignore rules, ranking,
budget trimming, cache hits/invalidation/corruption, malformed files, and
backward compatibility of the original `get_repo_map`.
