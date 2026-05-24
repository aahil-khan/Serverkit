# ServerKit

Object-oriented Python SDK for Linux operations — processes, logs, workflows, and system resources with a fluent, chainable API.

Think **structured objects** instead of parsing `ps aux`, `grep`, and one-off shell pipelines.

## Architecture

| Layer | Owner | Path |
|-------|--------|------|
| **SDK (core)** | Dev 1 | `serverkit/*` resource modules |
| **Interactive shell** | Dev 2 | `serverkit/shell` |
| **AI (Ollama)** | Dev 2 | `serverkit/ai` |

Dev 2 consumes the SDK via `Server` — see [`docs/DEV2_CONTRACTS.md`](docs/DEV2_CONTRACTS.md).

## Server API

```python
from serverkit import Server

server = Server()

server.processes().memory_above(500).sort_by_memory().all()
server.logs("app.log").errors().match(r"timeout").all()
server.memory().summarize()
server.disk().usage_above(80).summarize()
server.network().interfaces().sort_by_traffic().summarize()
server.ports().listening().summarize()
server.systemctl().list_units().active().summarize()
server.cron().suspicious_only().all()
server.users().logged_in().summarize()
server.env().keys_matching("PATH").all()
server.docker().containers().running().summarize()  # needs [docker] extra

server.workflow("audit").processes().memory_above(1000).summarize().save()
server.run("audit", dry_run=True)
```

## Setup

Requires **Python 3.10+**.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"           # core + pytest
pip install -e ".[rich]"          # table output
pip install -e ".[docker]"        # container support
pip install -e ".[all]"           # everything
pytest
```

Config: `~/.serverkit/config.json` (executor, rich output, Ollama model defaults).

## OOP patterns used

| Pattern | Where |
|---------|--------|
| Facade | `Server` |
| Factory | `ProcessFactory`, `StepFactory` |
| Fluent collection | `ProcessCollection`, `LogFile`, `DiskCollection`, … |
| Composite | `Workflow` + `WorkflowStep` |
| Strategy | `SequentialExecutor` / `ParallelExecutor` |
| Builder | `WorkflowBuilder` |

## Design rules

- **Eager execution** — filters run immediately; `.all()` / `.summarize()` are terminal.
- **Workflow JSON** — `schema_version: 2` under `~/.serverkit/workflows/`.
- **Optional deps** — `rich`, `docker` fail with `OptionalDependencyError` if missing.

## Documentation

| Document | Description |
|----------|-------------|
| `docs/serverkit_main.pdf` | Full architecture |
| `docs/serverkit_dev1_sdk_core.pdf` | Dev 1 SDK spec |
| `docs/serverkit_dev2_shell_ai.pdf` | Dev 2 shell + AI |
| `docs/DEV2_CONTRACTS.md` | Stable integration API |

## License

TBD
