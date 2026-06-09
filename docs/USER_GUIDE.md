# ServerKit — User guide

This guide explains **how ServerKit works** and **how to use it** (Python SDK, REPL, workflows, optional AI, optional remote SSH). For integration rules used by the shell and AI, see [`DEV2_CONTRACTS.md`](DEV2_CONTRACTS.md). For AI-only testing and troubleshooting, see [`AI_TESTING.md`](AI_TESTING.md).

---

## 1. What ServerKit is

ServerKit is a **Python library** plus a small **terminal app** (`serverkit`) that wraps common **Linux-style host operations** in a **structured API**:

- You call **`Server()`** (or **`RemoteServer`** over SSH) and chain methods on **collections** (processes, log lines, disks, …).
- You define or import **workflows** (JSON pipelines) and run them with one **`run("name")`**.
- Optionally you use **natural language** (`ask` / `Server.ask`) backed by **local Ollama**; the SDK still performs all real work — the model does not execute arbitrary shell.

**Version:** 0.3.0 (see `pyproject.toml`).

---

## 2. How it works (mental model)

### 2.1 Layers

| Layer | Role |
|-------|------|
| **Facade** | `Server` (local) or `RemoteServer` (SSH) — one object for “talk to this machine.” |
| **Fluent collections** | e.g. `ProcessCollection`, `LogFile` — filters **mutate in place** and return `self` so you can chain `.memory_above(500).sort_by_memory().summarize()`. |
| **Terminal methods** | `.all()`, `.summarize()`, `.display()`, `.export(...)` — produce lists, text, tables, or files. |
| **Workflows** | JSON under `~/.serverkit/workflows/`; steps (process_filter, sort, summary, …) run in order with a shared **context** dict; workflows receive **`_server`** so they work on local or remote. |
| **Shell** | Thin parser: maps typed lines to SDK calls; **`state.active`** is either local `Server` or connected `RemoteServer`. |
| **AI (optional)** | `Analyzer` builds prompts → Ollama returns JSON or prose → JSON is parsed defensively; common **“cpu/memory above N”** phrases use a **regex shortcut** so small models cannot corrupt those requests. |

### 2.2 Execution flow (local)

1. Your code or the REPL calls **`server.processes()`** (or another entry).
2. The **manager** builds a **collection** (often an eager snapshot, e.g. all processes).
3. Each **filter** narrows the in-memory list.
4. A **terminal** method returns a string or list for display/export.
5. **`server.run("wf")`** loads JSON, validates steps, runs the executor (sequential or parallel per config), merges results into the context dict.

### 2.3 Execution flow (remote)

1. **`Server.connect(...)`** opens **SSH** (Paramiko) and returns **`RemoteServer`**.
2. The same method names (`processes()`, `logs()`, `run()`, …) run **remote commands** or fetch data over the session where implemented.
3. **Workflow JSON files** still live on **your** machine; **`run`** passes the remote facade as **`_server`** inside the workflow so steps execute **on the remote host**.

### 2.4 Execution flow (AI)

1. **`ask …`** (REPL) or **`Server().ask("…")`** (Python) enters **`Analyzer`**.
2. The query is routed: **workflow phrase** → generate workflow JSON; **“why / diagnose”** → diagnostic prompt with top processes; else **intent** → JSON action for processes/logs.
3. Parsed actions call **`server.processes()` / `server.logs()`** etc. — same as if you typed SDK code yourself.

---

## 3. Installation

**Requirements:** Python **3.10+**.

```bash
cd opscript   # repository root containing pyproject.toml
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -e ".[dev]"         # editable install + pytest + requests (for AI tests)
```

**Optional extras** (install what you need):

| Extra | Purpose |
|-------|---------|
| `[rich]` | Nicer tables for `.display()` |
| `[docker]` | `server.docker()` / `containers()` |
| `[remote]` | `Server.connect()` / SSH |
| `[ai]` | `requests` + natural language `ask` / `Server.ask` (Ollama runs separately) |
| `[all]` | All of the above |

```bash
pip install -e ".[ai,remote]"
```

**Windows:** If `pip install -e ".[ai]"` fails with **WinError 32** on `serverkit.exe`, **exit the `serverkit` REPL** (or any process using that venv), then reinstall.

---

## 4. How to use — Python SDK

### 4.1 Entry point

```python
from serverkit import Server

server = Server()   # reads ~/.serverkit/config.json merged with defaults
```

### 4.2 Fluent chains (processes example)

```python
# Snapshot → filter → sort → terminal
print(server.processes().memory_above(200).sort_by_memory().summarize())
print(server.processes().display_by_name())   # app-style RSS grouping
rows = server.processes().cpu_above(5).all()  # list of Process objects
```

**Idea:** filters are **eager** — each step runs immediately; nothing lazy-fetches later unless you call the entry again.

### 4.3 Logs

```python
print(server.logs("/var/log/syslog").errors().tail(50).summarize())
```

Paths must exist on the **target** machine (local or remote after `connect`).

### 4.4 Workflows

**Import from catalog** (bundled templates):

```python
server.import_workflow("memory_audit")
server.run("memory_audit", dry_run=True)
server.run("memory_audit")
```

**Build and save** (fluent builder, local):

```python
server.workflow("my_audit").processes().memory_above(500).sort_by_memory().summarize().save()
server.run("my_audit")
```

Files live under **`~/.serverkit/workflows/`** (see `DEV2_CONTRACTS.md` for layout).

### 4.5 Remote SSH

```python
from serverkit import Server

with Server.connect("192.168.1.10", user="deploy", key_path="~/.ssh/id_ed25519") as remote:
    print(remote.processes().memory_above(300).summarize())
    remote.run("memory_audit")   # workflow uses remote as _server
```

Requires **`pip install serverkit[remote]`** and a reachable SSH server.

### 4.6 Optional natural language

```python
# Requires [ai], Ollama running, model pulled (see AI_TESTING.md)
print(server.ask("list processes with cpu above 10 percent"))
```

---

## 5. How to use — `serverkit` REPL

Start:

```bash
serverkit
```

### 5.1 Meta

| Input | Effect |
|--------|--------|
| `help` | Show built-in help text |
| `exit` / `quit` | Leave the shell |
| *Ctrl+C* / *EOF* | Exit (Ctrl+C also aborts current line) |

### 5.2 Processes & memory (use **`active`**: local or post-`connect` remote)

| Command | Effect |
|---------|--------|
| `processes.all()` | Table-style summary of processes |
| `processes.memory_above(500)` | Filter by RSS (MB) |
| `processes.cpu_above(10)` | Filter by CPU % |
| `processes.named("python")` | Name substring filter |
| `processes.sort_by_memory().all()` | Sort then list |
| `memory` | RAM / swap snapshot + table |

### 5.3 Logs

Use a **real path** on the target machine, double quotes:

```text
logs("C:\Windows\Logs\DISM\dism.log").summarize()
logs("C:\path\app.log").errors().tail(20)
```

### 5.4 Workflows

| Command | Effect |
|---------|--------|
| `catalog` | List bundled template names |
| `import memory_audit` | Copy catalog template to `~/.serverkit/workflows/` |
| `workflow list` | List saved workflow names |
| `run memory_audit` | Run on **active** target (`--dry-run` optional) |
| `workflow create NAME` | Interactive step loop (`save` / `cancel`) — see `help` |

### 5.5 Remote

| Command | Effect |
|---------|--------|
| `connect HOST --user U --key PATH [--port N]` | Open SSH; **active** becomes remote |
| `disconnect` | Close SSH; **active** returns to local `Server` |

### 5.6 AI (`[ai]` + Ollama)

| Command | Effect |
|---------|--------|
| `ask <question>` | Route through `Analyzer` (intent / diagnose / workflow NL) |

Examples:

```text
ask list processes with cpu above 10 percent
ask why might memory be high?
ask create a workflow to find high memory processes
```

Plain English **without** the `ask ` prefix is **not** sent to the AI — it will be “unknown command.”

---

## 6. Configuration

**Path:** `~/.serverkit/config.json` (merged with defaults in `serverkit/config.py`).

Common keys:

| Key area | Purpose |
|----------|---------|
| `output.use_rich` | Table rendering |
| `output.show_progress` | Progress spinner on long scans |
| `workflow.executor` | `sequential` or `parallel` |
| `workflow.versioning` | Version snapshots on save |
| `remote.*` | Default user, key, port for `connect` |
| `ollama.model` | Default model name for AI |

Environment: **`OLLAMA_HOST`** overrides Ollama base URL (default `http://127.0.0.1:11434`).

---

## 7. Where to read next

| Doc | Use when |
|-----|----------|
| [`DEV2_CONTRACTS.md`](DEV2_CONTRACTS.md) | You extend the shell/AI or need exact `Server` / collection / workflow contracts |
| [`AI_TESTING.md`](AI_TESTING.md) | You set up Ollama, run AI tests, or debug model / JSON issues |
| [`../README.md`](../README.md) | Overview, architecture diagram, repo layout |
| PDFs in `docs/` | Original full specs |

---

## 8. Quick troubleshooting

| Symptom | What to check |
|---------|----------------|
| `ModuleNotFoundError: serverkit` | Activate venv; `pip install -e .` from repo root |
| `OptionalDependencyError` | Install the named extra, e.g. `[remote]` or `[ai]` |
| `WinError 32` on `serverkit.exe` during pip | Exit `serverkit` / close handles on `.venv\Scripts\serverkit.exe` |
| `connect` times out | Firewall, SSH daemon, correct IP/port, security group |
| `ask` returns bad JSON / essays | Use **`ask … cpu/memory above N`** (deterministic path); upgrade `ollama.model`; see `AI_TESTING.md` |
| `Unknown command` in REPL | Use exact commands from `help` or prefix AI with **`ask `** |

---

*This guide reflects ServerKit **0.3.0**. For API details beyond the shell, follow the Python modules under `serverkit/` and the PDF / contract docs.*
