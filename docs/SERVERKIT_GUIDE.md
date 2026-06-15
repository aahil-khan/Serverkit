# ServerKit — Complete Beginner Guide

**Version:** 0.3.0 · **Project:** `opscript` / package `serverkit`  
Read this on your phone. No prior Python or OOP required.

---

## Part 1 — What is this project?

**ServerKit** is a Python library for talking to a **Linux server** in a structured way.

Instead of memorizing shell one-liners:

```bash
ps aux | awk ... | grep ...
```

you write:

```python
from serverkit import Server

server = Server()
server.processes().memory_above(500).sort_by_memory().summarize()
```

The library wraps real OS tools (`psutil`, `systemctl`, SSH, etc.) behind **objects** you can chain, filter, save as workflows, and run again later.

### What lives where

| Folder | Purpose |
|--------|---------|
| `serverkit/` | The SDK (main code) |
| `serverkit/shell/` | CLI / REPL (interactive terminal UI) |
| `serverkit/ai/` | Ollama / natural-language helpers |
| `tests/` | Automated checks |
| `examples/` | Small runnable scripts |
| `docs/` | PDF specs + this guide |

**Install (dev machine):**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # core + tests
pip install -e ".[all]"      # rich tables, docker, SSH remote
```

**CLI:** `serverkit` → REPL entry (shell layer; may still be WIP).

**Config:** `~/.serverkit/config.json`

---

## Part 2 — OOP from zero

**OOP = Object-Oriented Programming.** You group **data** and **actions** into **classes**.

### The four words you need

| Word | Meaning | Example in ServerKit |
|------|---------|----------------------|
| **Class** | Blueprint | `class Process:` |
| **Object** | One real instance | A process with pid=1234 |
| **Attribute** | Data on the object | `process.pid`, `process.name` |
| **Method** | Function on the object | `process.kill()` |

### Create and use

```python
# "Make one Server object"
server = Server()

# "Ask it for processes, then filter"
collection = server.processes()
collection.memory_above(500)
```

The **dot** means “on this object”: `thing.method()` or `thing.attribute`.

### `self`

Inside a class method, **`self`** means “this specific object”:

```python
class Process:
    def kill(self):
        os.kill(self.pid, ...)  # THIS process's pid
```

When you call `p.kill()`, Python passes `p` as `self` automatically.

### Why bother?

1. **Readable** — `proc.kill()` vs `kill_pid(proc.pid)`
2. **Reusable** — one `Process` class for every process
3. **Organized** — managers, collections, workflows each have one job

---

## Part 3 — The architecture (big picture)

Think of a **toolbox with labeled drawers**:

```
YOU
  │
  ▼
Server  ←── front door (facade)
  │
  ├── ProcessManager  → ProcessCollection → Process
  ├── LogManager      → LogFile
  ├── WorkflowManager → Workflow / WorkflowBuilder
  ├── MemoryManager   → MemorySnapshot
  ├── DiskManager     → DiskCollection
  ├── ServicesManager → ServiceHandle
  ├── RemoteServer    → same idea over SSH
  └── … (network, ports, cron, users, env, docker)
```

### The repeating pattern (memorize this)

Every resource area follows the same shape:

1. **`Server`** — you start here
2. **`*Manager`** — loads data from OS/API
3. **Domain object** — one thing (`Process`, `Container`, …)
4. **`*Collection` or fluent object** — many things, chainable filters

**Typical flow:**

```
Server → Manager → Collection → .filter().filter() → .summarize()
                                              ↓
                                         single Process → .kill()
```

### Design rules (how the SDK behaves)

- **Eager** — filters run **immediately** when you call them, not lazily later
- **Fluent** — `.a().b().c()` each returns the same collection so you can chain
- **Terminal** — `.all()`, `.summarize()`, `.display()` finish the chain (get a result)
- **Optional extras** — `rich`, `docker`, `paramiko` (remote); missing → clear error

---

## Part 4 — `Server` (the front door)

File: `serverkit/core/server.py`

```python
from serverkit import Server

server = Server()
```

`Server` is a **facade**: it does not implement everything itself. It **owns managers** and **delegates**.

### Main methods (local machine)

| Method | What you get |
|--------|----------------|
| `processes()` | All processes, filterable |
| `logs("app.log")` | One log file, filterable |
| `memory()` | RAM snapshot |
| `disk()` | Partitions / usage |
| `network()` | Network manager |
| `ports()` | Listening ports |
| `systemctl()` | Low-level systemd |
| `services()` | Friendly service list |
| `service("nginx")` | One service handle |
| `cron()` | Cron jobs |
| `users()` | Logged-in users, etc. |
| `env()` | Environment variables |
| `docker()` / `containers()` | Docker (needs `[docker]`) |
| `workflow("name")` | Start building a saved workflow |
| `import_workflow("memory_audit")` | Load bundled template |
| `run("name", dry_run=False)` | Execute saved workflow |

### Remote (SSH)

```python
with Server.connect("vm1", user="deploy", key_path="~/.ssh/id_ed25519") as remote:
    remote.processes().memory_above(200).summarize()
    remote.service("nginx").status()
    remote.run("memory_audit")
```

`RemoteServer` mirrors **some** local methods (`processes`, `logs`, `memory`, `services`, `run`). It runs commands over SSH and parses output into the **same object types** where possible.

---

## Part 5 — Domain objects (one real thing)

### `Process` — one running program

File: `serverkit/processes/process.py`

**Attributes:** `pid`, `name`, `memory_mb`, `cpu_percent`, `ppid`, `username`

**Methods:**

| Method | Does |
|--------|------|
| `kill()` | SIGKILL |
| `terminate()` | SIGTERM |
| `children()` | Child `Process` list |
| `parent()` | Parent `Process` or None |
| `details()` | Dict of fields |

Built by **`ProcessFactory`** from raw `psutil` data (hides permission errors, etc.).

### `ServiceHandle` — one systemd service

File: `serverkit/services/handle.py`

```python
server.service("nginx").status()
server.service("nginx").restart()
server.service("nginx").is_active()
```

Wraps `SystemctlManager` so you do not think about `.service` suffixes.

### `LogFile` — one log path

File: `serverkit/logs/logfile.py`

Chain: `.errors()`, `.warnings()`, `.match(regex)`, `.tail(n)`, `.summarize()`, `.display()`

Remote logs use `LogFile.from_lines(...)` after SSH `tail`/`cat`.

### `Workflow` — saved pipeline

File: `serverkit/workflows/workflow.py`

- Steps stored as JSON under `~/.serverkit/workflows/{name}.json`
- `schema_version: 2`
- `.save()`, `.run(server=...)`

### Smaller objects (same idea)

| Class | One of… |
|-------|---------|
| `Container` | Docker container |
| `CronJob` | Cron entry |
| `MemorySnapshot` | RAM stats |
| `Port` | Network port |
| `Partition` | Disk partition |

Each = **data + methods that make sense for that thing**.

---

## Part 6 — Collections (many things, chained)

### Base: `FluentCollection`

File: `serverkit/core/collection.py`

Shared behavior for all collections:

- `.all()` → list
- `for x in collection:` works
- `len(collection)` works

Subclasses add filters and return **`self`** so you chain.

### Example: `ProcessCollection`

File: `serverkit/processes/manager.py`

```python
server.processes() \
    .named("python") \
    .memory_above(100) \
    .sort_by_memory() \
    .summarize()
```

| Method | Filter / action |
|--------|-----------------|
| `named(name)` | Name contains string |
| `memory_above(mb)` | RSS over threshold |
| `cpu_above(percent)` | CPU over threshold |
| `for_user(username)` | Owning user |
| `sort_by_memory()` / `sort_by_cpu()` | Sort |
| `group_by_user()` | Dict of collections |
| `group_by_name()` | Group by app name |
| `display_by_name()` | Task-manager style RSS per app |
| `kill_all()` / `terminate_all()` | Dangerous — kills matched |
| `summarize()` | Text report |
| `display()` | Table (Rich if installed) |
| `export(path)` | CSV etc. |

**App names:** `serverkit/processes/aliases.py` maps child process names (e.g. Firefox helpers) to one app label.

### Terminal methods (end of chain)

| Method | Result |
|--------|--------|
| `.all()` | Python `list` |
| `.summarize()` | `str` (print it in REPL) |
| `.summarise()` | British alias |
| `.display()` | Formatted table string |
| `.export(path, fmt="csv")` | Writes file |

---

## Part 7 — Managers and factories

### Manager

**Job:** Talk to OS/API once, build domain objects, return a collection.

```python
class ProcessManager:
    def all(self) -> ProcessCollection:
        # loop psutil.process_iter()
        # ProcessFactory.create(each) → list → ProcessCollection
```

Other managers: `LogManager`, `WorkflowManager`, `DiskManager`, `MemoryManager`, …

### Factory

**Job:** Convert messy external data → clean domain object.

```python
ProcessFactory.create(psutil_process)  # → Process | None
StepFactory.from_dict(step_json)       # → WorkflowStep
```

**Static method** = call on class, no instance: `ProcessFactory.create(...)`.

---

## Part 8 — OOP patterns used (name → meaning)

| Pattern | Plain English | Where |
|---------|---------------|-------|
| **Facade** | One simple entry hiding many parts | `Server`, `RemoteServer` |
| **Factory** | Central place to build objects | `ProcessFactory`, `StepFactory` |
| **Fluent API** | Chain methods, each returns same object | Collections, `LogFile`, `WorkflowBuilder` |
| **Inheritance** | Child class extends parent | `ProcessCollection(FluentCollection)`, executors |
| **Composition** | Object contains other objects | `Workflow.steps`, collection `.data` |
| **Strategy** | Swap algorithm, same interface | `SequentialExecutor` vs `ParallelExecutor` |
| **Builder** | Step-by-step construction | `WorkflowBuilder` |
| **Protocol** | “Anything with these methods” (typing) | `ServerFacade` in `core/protocol.py` |
| **ABC** | Abstract base — must implement methods | `WorkflowStep`, `WorkflowExecutor` |

### Inheritance example — exceptions

```python
class ServerKitError(Exception): ...
class ProcessNotFound(ServerKitError): ...
class WorkflowNotFound(ServerKitError): ...
```

Catch `ServerKitError` for any library error; catch specific ones when you only care about one case.

### Inheritance example — workflow steps

```python
class WorkflowStep(ABC):
    def execute(self, context: dict) -> dict: ...  # must implement

class ProcessFilterStep(WorkflowStep):
    def execute(self, context): ...
```

Each step type is its own class; executor loops and calls `.execute(context)`.

### Inheritance example — executors

```python
class WorkflowExecutor(ABC):
    def execute(workflow, server, dry_run=False) -> dict: ...

class SequentialExecutor(WorkflowExecutor):
    # run steps one after another

class ParallelExecutor(WorkflowExecutor):
    # run steps in parallel (where safe)
```

**Polymorphism** = caller uses `get_executor(name).execute(...)` without caring which class.

---

## Part 9 — Workflows

### Build in code (fluent builder)

```python
server.workflow("audit") \
    .processes() \
    .memory_above(1000) \
    .sort_by_memory() \
    .summarize() \
    .save()

result = server.run("audit")
result = server.run("audit", dry_run=True)  # print only, no side effects
```

`WorkflowBuilder` turns each chain call into a **step object** (`ProcessFilterStep`, `SortStep`, …).

### Import from catalog (bundled templates)

```python
server.import_workflow("memory_audit")
server.run("memory_audit")
```

Templates live in `serverkit/workflows/catalog/`:

- `memory_audit.json`
- `log_error_scan.json`
- `nginx_health_check.json`

Saved copy goes to `~/.serverkit/workflows/`.

### Step types (JSON `type` field)

| type | Purpose |
|------|---------|
| `process_filter` | Filter processes |
| `sort` | Sort by field |
| `log_filter` | Filter log lines |
| `tail` | Last N lines |
| `summary` | Build summary string |
| `export` | Write output file |
| `chain` | Nested sub-steps |
| `conditional` | if/else on context |

### Runtime

Executor passes a **`context` dict** between steps. Often includes `"_server": server` so steps can call `server.processes()` again on local or remote.

Config key `workflow.executor`: `"sequential"` (default) or `"parallel"`.

---

## Part 10 — Layer map (all packages)

```
serverkit/
├── __init__.py          → exports Server
├── config.py            → ~/.serverkit/config.json
├── exceptions.py        → ServerKitError hierarchy
├── core/
│   ├── server.py        → Server facade
│   ├── collection.py    → FluentCollection base
│   ├── protocol.py      → ServerFacade typing
│   └── display.py       → tables / export helpers
├── processes/           → Process, ProcessManager, factory, aliases, history
├── logs/                → LogFile, LogManager
├── memory/              → MemorySnapshot, MemoryManager
├── disk/                → Partition, DiskCollection, largest_files
├── network/             → connections, interfaces
├── ports/               → Port, PortCollection
├── systemctl/           → low-level systemd
├── services/            → ServiceHandle, ServicesManager (friendly)
├── cron/                → CronJob, CronCollection
├── users/               → sessions, logged-in users
├── env/                 → environment snapshot
├── docker/              → Container, DockerManager (optional)
├── workflows/           → Workflow, builder, steps, executors, catalog, validator
├── remote/              → SSH connection, RemoteServer, parsers
├── output/              → theme, tables, exporters, progress spinner
├── shell/               → REPL, parser, autocomplete (Dev 2)
└── ai/                  → Ollama client, analyzer (Dev 2)
```

---

## Part 11 — Copy-paste recipes

### Processes

```python
from serverkit import Server
s = Server()

# Top memory hogs
print(s.processes().sort_by_memory().summarize())

# Kill heavy python (careful!)
s.processes().named("python").memory_above(2000).kill_all()

# App-level view (like Mission Center)
print(s.processes().display_by_name())
```

### Logs

```python
print(s.logs("app.log").errors().tail(50).summarize())
print(s.logs("/var/log/syslog").warnings().match(r"fail").summarize())
```

### Memory & disk

```python
print(s.memory().summarize())
print(s.disk().usage_above(80).summarize())
print(s.disk().largest_files("/home", limit=10).display())
```

### Services

```python
print(s.services().active().summarize())
s.service("nginx").restart()
print(s.service("nginx").is_active())
```

### Workflow end-to-end

```python
s = Server()
s.import_workflow("nginx_health_check")
print(s.run("nginx_health_check", dry_run=True))
print(s.run("nginx_health_check"))
```

### Remote audit

```python
with Server.connect("192.168.1.10", user="admin") as r:
    print(r.memory().summarize())
    print(r.processes().memory_above(500).summarize())
    r.run("memory_audit")
```

---

## Part 12 — How to read new code

When you open any file, ask:

1. **Is it a thing?** → `Process`, `LogFile`, `ServiceHandle`
2. **Is it a list of things?** → `*Collection`, extends `FluentCollection`
3. **Is it a finder?** → `*Manager`
4. **Is it a builder?** → `*Factory`, `WorkflowBuilder`
5. **Is it the door?** → `Server`, `RemoteServer`
6. **Is it a step/executor?** → `workflows/steps.py`, `executors/`

### File → role cheat sheet

| File | Role |
|------|------|
| `core/server.py` | Local facade |
| `remote/server.py` | SSH facade |
| `processes/process.py` | One process |
| `processes/manager.py` | Manager + ProcessCollection |
| `processes/factory.py` | psutil → Process |
| `workflows/builder.py` | Chain → steps |
| `workflows/workflow.py` | Save/load/run |
| `workflows/executors/*.py` | How steps run |
| `workflows/step.py` | Abstract step |
| `services/handle.py` | One service |
| `exceptions.py` | All errors |

---

## Part 13 — Glossary

| Term | Meaning |
|------|---------|
| Instantiate | `Server()` — create object from class |
| Delegate | Server calls manager instead of doing work itself |
| Fluent | Methods return `self` for chaining |
| Eager | Filter runs when you call it, not later |
| Facade | Simple API over complex subsystems |
| Generic `[T]` | Collection holds type T (e.g. Process) |
| Protocol | Interface contract (for type checkers) |
| ABC | Abstract base class — subclasses must fill in methods |
| Polymorphism | Same method name, different classes |
| Context (workflow) | Shared `dict` passed step to step |
| Dry run | Workflow prints what it would do, skips side effects |
| Optional dependency | Feature needs extra `pip install` extra |

---

## Part 14 — Tests & examples

**Run tests (offline by default):**

```bash
pytest
pytest -m integration   # touches real OS
```

**Examples:**

| Script | Shows |
|--------|-------|
| `examples/memory_audit.py` | Build + run workflow |
| `examples/log_audit.py` | Log filtering |
| `examples/process_apps.py` | App-name grouping |
| `examples/import_catalog_workflow.py` | Catalog import |
| `examples/remote_audit.py` | SSH remote |

---

## Part 15 — Dev split (who owns what)

| Owner | Path | Responsibility |
|-------|------|----------------|
| Dev 1 (SDK) | Most of `serverkit/` | Resources, workflows, remote, collections |
| Dev 2 (Shell/AI) | `shell/`, `ai/` | REPL, Ollama; **uses** `Server` only |

Integration contract: `docs/DEV2_CONTRACTS.md`  
Long PDF specs: `docs/serverkit_main.pdf`, `serverkit_dev1_sdk_core.pdf`, `serverkit_dev2_shell_ai.pdf`

---

## Quick reference card

```
from serverkit import Server
s = Server()

s.processes().memory_above(500).summarize()
s.logs("app.log").errors().summarize()
s.memory().summarize()
s.disk().usage_above(90).summarize()
s.services().active().summarize()
s.service("nginx").restart()
s.import_workflow("memory_audit")
s.run("memory_audit", dry_run=True)

with Server.connect("host", user="u") as r:
    r.processes().summarize()
    r.run("memory_audit")
```

---

*End of guide. Project path on disk: `/home/aahil/projects/opscript` · Package: `serverkit` v0.3.0*
