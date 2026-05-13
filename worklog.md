# Worklog: Fix ruff lint errors (Task ID: 3)

## Summary
Fixed all 22 ruff lint errors across 9 test files. All checks now pass.

## Changes by File

### tests/test_project.py
- **F811**: Renamed duplicate `test_extract_info_exception_pyproject` → `test_extract_info_exception_pyproject_invalid_toml` (preserved test coverage)
- **F841**: Prefixed unused `result` with `_result` (line 250)
- **F841**: Prefixed unused `original_dtf` with `_original_dtf` (line 259)
- **F401**: Removed unused `from watchdog.observers.api import DEFAULT_OBSERVER_TIMEOUT` (line 332)
- **F401**: Removed unused `from watchdog.events import FileSystemEvent` (line 337)

### tests/test_sandbox.py
- **F401**: Removed unused `import pytest` (line 9)
- **F841**: Prefixed unused `sb` with `_sb` (line 22)

### tests/test_server.py
- **F841**: Prefixed unused `resp` with `_resp` (line 699)

### tests/test_session.py
- **E401**: Split `import json, base64` into separate lines: `import base64` then `import json` (line 365)

### tests/test_share.py
- **F401**: Removed unused `from pathlib import Path` (line 5)

### tests/test_skills.py
- **F841**: Prefixed unused `sm` with `_sm` (line 213)
- **F401**: Removed unused `import stat` (line 259)
- **F401**: Removed unused `import stat` (line 268)

### tests/test_tools.py
- **F811**: Renamed duplicate `test_create_directory_already_exists` → `test_create_directory_already_exists_subdir` (line 480)
- **F841**: Prefixed unused `original_run` with `_original_run` (line 974)
- **F811**: Removed duplicate `class UM` definition (line 1100), kept only one
- **F841**: Prefixed unused `issues_captured` with `_issues_captured` (line 1964)

### tests/test_tools_coverage.py
- **F401**: Removed unused `import sys` (line 5). This also resolved 6 downstream F811 errors where local `import sys` statements conflicted with the module-level import.

### tests/test_watcher.py
- **F401**: Removed unused `PropertyMock` from `from unittest.mock import patch, PropertyMock` (line 9)
- **F841**: Prefixed unused `before` with `_before` (line 445)
- **F841**: Prefixed unused `gitignore_patterns` with `_gitignore_patterns` (line 547)

## Verification
Ran `/home/z/.local/bin/ruff check` on all 9 files — **All checks passed!**
