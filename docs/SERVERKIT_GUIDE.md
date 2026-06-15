# ServerKit guide (short)

This file is a **compact index** for ServerKit **v0.3.0**. For depth, use the linked docs — they are the maintained source of truth.

## Start here

| Topic | Document |
|--------|----------|
| Mental model, SDK, REPL, remote, AI, troubleshooting | [`USER_GUIDE.md`](USER_GUIDE.md) |
| Shell / AI integration rules, `Server` vs `RemoteServer`, workflow context | [`DEV2_CONTRACTS.md`](DEV2_CONTRACTS.md) |
| Ollama install, AI tests, JSON / model issues | [`AI_TESTING.md`](AI_TESTING.md) |
| REPL copy-paste checks | [`REPL_VERIFICATION.md`](REPL_VERIFICATION.md) |

## Status (v0.3.0)

- **REPL** (`serverkit` CLI): shipped — pattern-matched commands to the SDK, not a full Python REPL.
- **Remote SSH**: broad parity with local facades for metrics and workflows (`run` passes the remote object as `_server`).
- **Workflow `parallel` executor**: deprecated; configuration still accepted but execution stays **sequential** with a runtime warning (shared mutable step context).

## Examples

See [`../examples/README.md`](../examples/README.md) for runnable scripts.
