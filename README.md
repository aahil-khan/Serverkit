# ServerKit

**A fluent Python SDK and shell for Linux server operations.**

Inspect processes, logs, disk, services, and more through chainable objects and saved workflows — instead of memorizing `ps`, `grep`, and one-off shell pipelines. Run commands interactively in the REPL, automate in scripts, or ask questions in plain English with local Ollama.

**Version 0.3.4** · Python **3.10+** · Linux

```bash
pip install "serverkit[rich]"
```

[`serverkit` on PyPI](https://pypi.org/project/serverkit/) · [User guide](docs/USER_GUIDE.md) · [Examples](examples/)

---

## Why ServerKit

| Instead of… | ServerKit gives you… |
|-------------|----------------------|
| `ps aux \| awk … \| grep …` | `server.processes().memory_above(500).sort_by_memory().summarize()` |
| Ad-hoc audit scripts you rewrite every time | Named workflows in `~/.serverkit/workflows/`, importable from a built-in catalog |
| SSH + shell one-liners per host | `Server.connect("host")` with the same API locally and remotely |
| Piping logs through `grep` and `tail` | `server.logs("app.log").errors().match(r"timeout").summarize()` |

Filters run eagerly; `.summarize()`, `.display()`, and `.all()` are terminal — you always know when work is done.

---

## Install

**Recommended** (SDK + interactive shell + formatted tables):

```bash
pip install "serverkit[rich]"
```

**Everything** (SSH remote, Docker, AI, Rich):

```bash
pip install "serverkit[all]"
```

| Extra | Adds |
|-------|------|
| `[rich]` | Formatted tables for `.display()` and the REPL |
| `[remote]` | `Server.connect()` / REPL `connect` over SSH |
| `[docker]` | Container listing, logs, and stats |
| `[ai]` | `Server.ask()` and REPL `ask …` via Ollama |
| `[dev]` | pytest and test dependencies |

Core install (`pip install serverkit`) includes the SDK and REPL with plain-text `.summarize()` output. For the full interactive experience, use at least `[rich]`.

After install, launch the shell:

```bash
serverkit
```

Config is created automatically at `~/.serverkit/config.json` on first use (commented template — edit values or uncomment optional lines).

---

## Quick start

### Python SDK

```python
from serverkit import Server

server = Server()

# Processes and memory
print(server.processes().memory_above(500).sort_by_memory().summarize())
print(server.memory().summarize())

# Logs
print(server.logs("/var/log/syslog").errors().tail(50).summarize())

# Disk and services
print(server.disk().usage_above(80).summarize())
print(server.systemctl().list_units().active().summarize())

# Workflows — import a catalog template and run it
server.import_workflow("memory_audit")
server.run("memory_audit")

# Or build and save your own
server.workflow("audit").processes().memory_above(1000).summarize().save()
server.run("audit", dry_run=True)
```

### Remote hosts

Requires `[remote]`:

```python
from serverkit import Server

with Server.connect("vm1.example", user="deploy", key_path="~/.ssh/id_ed25519") as remote:
    print(remote.processes().memory_above(200).summarize())
    print(remote.memory().summarize())
    remote.service("nginx").status()
    remote.run("memory_audit")
```

### Interactive shell

```bash
serverkit
```

```text
help
memory
processes().memory_above(500).summarize()
catalog
import memory_audit
run memory_audit
connect vm1.example --user deploy --key ~/.ssh/id_ed25519
disconnect
exit
```

### Natural language (optional)

Requires `[ai]` and a running [Ollama](https://ollama.com/) instance:

```python
from serverkit import Server
print(Server().ask("show processes with cpu above 10 percent"))
```

```text
ask list processes with cpu above 10 percent
ask largest files in /var/log limit 10
```

The AI layer routes requests through the SDK — it does not execute arbitrary shell from the model. Common phrases like CPU/memory thresholds use deterministic parsing so small models stay reliable.

---

## What's included

- **Resource facades** — processes, logs, memory, disk, network, ports, systemd, cron, users, environment, Docker
- **Fluent collections** — chain filters, then `.summarize()`, `.display()`, or `.all()`
- **Workflow engine** — JSON workflows (`schema_version: 2`), catalog templates, dry-run support
- **SSH remote** — broad parity with local metrics and workflow execution on remote hosts
- **REPL** — `serverkit` CLI with completions, fluent chains, and `connect` / `disconnect`
- **AI assistant** — intent routing, diagnostics, and workflow generation via Ollama

---

## Documentation

| Guide | Description |
|-------|-------------|
| [User guide](docs/USER_GUIDE.md) | Mental model, SDK, REPL, remote, AI, troubleshooting |
| [Examples](examples/) | Runnable sample scripts |

---

## Development

From a clone:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Integration tests (live OS): `pytest -m integration`

---

## License

MIT — see [LICENSE](LICENSE).
