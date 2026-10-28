# Python-written Fernet session fixtures

`python_session.enc` and `python_session_legacy.enc` are produced by Python's
`cryptography.fernet.Fernet`, i.e. by the same library `apex/session.py` uses.
They prove that the Rust loader reads Python-written sessions, not just its own
round-trips.

| File | Purpose |
| --- | --- |
| `fernet.key` | 44-char urlsafe-base64 Fernet key, derived from `sha256("apex-rust-fixture-key")` |
| `python_session.enc` | Session encrypted with `fernet.key` |
| `legacy.key` | Legacy raw 32-byte key (`apex-legacy-fixture-key-00000000`) |
| `python_session_legacy.enc` | Session encrypted with `sha256(legacy.key + b":fernet")`, the legacy derivation both implementations share |

The payload mirrors `SessionManager.save`: compact JSON with `name`,
`timestamp`, `model`, `cwd`, `history` and `usage`. The values are fixed test
data; the keys are not secrets.

Regenerate from `rust/apex-rs`:

```bash
python tests/fixtures/session/generate.py
```

The HTTP-auth and E2E suites load these files through the compiled binary with
a temporary `HOME`, so the developer's real `~/.apex` is never touched.
