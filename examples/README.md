# Examples

Runnable scripts that use the **Python SDK** (`from serverkit import Server`). Install from repo root: `pip install -e ".[dev,remote,docker,ai]"` (trim extras to what you need).

| Script | What it shows |
|--------|-----------------|
| [`import_catalog_workflow.py`](import_catalog_workflow.py) | `import_workflow` from the bundled catalog, `dry_run`, then `run` |
| [`log_audit.py`](log_audit.py) | `logs(path)` fluent chain (errors, tail, summarize) |
| [`memory_audit.py`](memory_audit.py) | `memory()` and process filters |
| [`process_apps.py`](process_apps.py) | `processes()` grouping / display helpers |
| [`remote_audit.py`](remote_audit.py) | `Server.connect` → `RemoteServer` workflow or checks over SSH |

Add new scripts here when they illustrate a public API or a common ops pattern worth copying.
