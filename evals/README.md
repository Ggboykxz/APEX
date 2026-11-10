# APEX Eval Fixtures

This directory contains evaluation fixtures for critical APEX flows.
Each subdirectory represents an eval scenario with input fixtures and
expected outputs.

## Eval: shell-security

Tests that dangerous shell commands are detected.

- `input/`: sample commands to analyze
- `expected/`: expected verdict (safe/dangerous)

## Eval: permission-system

Tests that the ALLOW/DENY/ASK permission system works correctly.

- `input/`: tool call scenarios
- `expected/`: expected permission decision

## Eval: snapshot-undo-redo

Tests Git-based snapshot undo/redo lifecycle.

- `input/`: file modifications
- `expected/`: restored file contents
