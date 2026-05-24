# ServerKit

Object-oriented Python SDK for Linux operations — processes, logs, and reusable workflows with a fluent, chainable API.

Think **structured objects** instead of parsing `ps aux`, `grep`, and one-off shell pipelines.

## Architecture

| Layer | Owner | Path |
|-------|--------|------|
| **SDK (core)** | Dev 1 | `serverkit/core`, `processes`, `logs`, `workflows` |
| **Interactive shell** | Dev 2 | `serverkit/shell` |
| **AI (Ollama)** | Dev 2 | `serverkit/ai` |

Dev 2 consumes the SDK only (`server.processes()`, `server.logs()`, `server.workflow()`). The core layer must stay a clean, self-documenting API.

## Project layout

```
serverkit/
├── core/server.py          # Server entry point
├── processes/              # Process, ProcessCollection, ProcessManager
├── logs/                   # LogFile, LogManager
├── workflows/              # Workflow, steps, builder, manager
├── shell/                  # Dev 2 — REPL, parser, autocomplete
└── ai/                     # Dev 2 — Ollama client, analyzer

tests/                      # Milestone tests
examples/                   # Usage examples
docs/                       # Project PDFs (main + dev guides)
```

## Setup

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage (target API)

```python
from serverkit import Server

server = Server()

# Processes
server.processes().memory_above(500).sort_by_memory().all()

# Logs
server.logs("app.log").errors().tail(50).all()

# Workflows (saved under ~/.serverkit/workflows/)
(
    server.workflow("memory_audit")
    .processes()
    .memory_above(1000)
    .sort_by_memory()
    .summarize()
    .save()
)
server.run("memory_audit")
```

## Dev 1 build order

1. `Process` + `ProcessCollection`
2. `ProcessFactory` + `ProcessManager`
3. `Server` (processes)
4. `LogFile` + `LogManager`
5. `WorkflowStep` subclasses
6. `Workflow` serialization
7. `WorkflowBuilder`
8. `WorkflowManager.run()`

See `docs/serverkit_dev1_sdk_core.pdf` for interfaces and reference implementations.

## Design rules

- **Eager execution** — chain methods filter immediately and return `self`; only `.all()` / `.summarize()` are terminal.
- **Workflow JSON** — canonical schema in the main doc; stored at `~/.serverkit/workflows/{name}.json`.
- **Shared contracts** — do not change public method signatures without coordinating with Dev 2.

## Documentation

| Document | Description |
|----------|-------------|
| `docs/serverkit_main.pdf` | Full architecture and contracts |
| `docs/serverkit_dev1_sdk_core.pdf` | SDK + workflow engine (Dev 1) |
| `docs/serverkit_dev2_shell_ai.pdf` | Shell + AI layer (Dev 2) |

## License

TBD
