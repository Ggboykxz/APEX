## Summary

<!-- What changed, why, and which issue/milestone it closes. -->

Closes #

## Type of change

- [ ] `feat` — new capability
- [ ] `fix` — defect fix
- [ ] `refactor` — no behavior change
- [ ] `perf` — performance
- [ ] `docs` — documentation only
- [ ] `test` — tests only
- [ ] `ci` / `build` / `chore` — tooling

## Definition of Done

- [ ] Python: `ruff check` and `ruff format --check` pass
- [ ] Python: `pytest` passes (new tests added when behavior changes)
- [ ] Rust: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test` pass
- [ ] TUI: `npm run typecheck` and `bun test` pass
- [ ] Website: `eslint .` and `next build` pass (when `src/**` is touched)
- [ ] Docs updated (`AGENTS.md`, mkdocs, or an ADR for architectural decisions)
- [ ] No secrets, `.env` files, or generated artifacts committed
- [ ] All required workflows are green

## Testing

<!-- Commands run and their results. -->

## Screenshots / recordings

<!-- For TUI or website changes. -->

## Notes for reviewers
