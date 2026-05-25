"""Parse remote command output into domain objects."""

from __future__ import annotations

import json

from serverkit.processes.process import Process


def processes_from_psutil_json(payload: str) -> list[Process]:
    data = json.loads(payload)
    if isinstance(data, dict) and "processes" in data:
        rows = data["processes"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    return [_process_from_dict(row) for row in rows]


def processes_from_ps_aux(output: str) -> list[Process]:
    processes: list[Process] = []
    lines = output.strip().splitlines()
    if not lines:
        return processes
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        try:
            pid = int(parts[1])
            cpu_percent = float(parts[2])
            mem_percent = float(parts[3])
            memory_mb = mem_percent * 16  # rough when RSS unknown
            name = parts[10].split()[0] if parts[10] else "unknown"
            processes.append(
                Process(
                    pid=pid,
                    name=name,
                    memory_mb=memory_mb,
                    cpu_percent=cpu_percent,
                    ppid=None,
                    username=parts[0],
                )
            )
        except (ValueError, IndexError):
            continue
    return processes


def memory_from_psutil_json(payload: str) -> dict:
    data = json.loads(payload)
    if isinstance(data, dict) and "memory" in data:
        return data["memory"]
    if isinstance(data, dict) and "total_mb" in data:
        return data
    raise ValueError("No memory key in remote JSON")


def memory_from_free_m(output: str) -> dict:
    mem_row = None
    swap_row = None
    for line in output.splitlines():
        if line.startswith("Mem:"):
            mem_row = line.split()
        elif line.startswith("Swap:"):
            swap_row = line.split()
    if not mem_row or len(mem_row) < 4:
        raise ValueError("Cannot parse free -m output")
    total = float(mem_row[1])
    used = float(mem_row[2])
    available = float(mem_row[3]) if len(mem_row) > 3 else total - used
    percent = (used / total * 100) if total else 0.0
    swap_total = swap_used = swap_percent = 0.0
    if swap_row and len(swap_row) >= 4:
        swap_total = float(swap_row[1])
        swap_used = float(swap_row[2])
        swap_percent = (swap_used / swap_total * 100) if swap_total else 0.0
    return {
        "total_mb": total,
        "used_mb": used,
        "available_mb": available,
        "percent": percent,
        "swap_total_mb": swap_total,
        "swap_used_mb": swap_used,
        "swap_percent": swap_percent,
    }


def parse_systemctl_units(output: str) -> list:
    from serverkit.systemctl.service import Service

    services: list[Service] = []
    for line in output.strip().splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        services.append(
            Service(
                name=parts[0],
                load_state=parts[1],
                active_state=parts[2],
                description=parts[4] if len(parts) > 4 else "",
            )
        )
    return services


def _process_from_dict(row: dict) -> Process:
    return Process(
        pid=int(row["pid"]),
        name=str(row.get("name", "unknown")),
        memory_mb=float(row.get("memory_mb", 0)),
        cpu_percent=float(row.get("cpu_percent", 0)),
        ppid=int(row["ppid"]) if row.get("ppid") is not None else None,
        username=row.get("username"),
    )


PSUTIL_PROBE = "python3 -c 'import psutil' 2>/dev/null && echo ok"

PSUTIL_JSON_SCRIPT = r"""python3 -c "
import json, psutil
procs = []
for p in psutil.process_iter():
    try:
        with p.oneshot():
            username = None
            try:
                username = p.username()
            except Exception:
                pass
            procs.append({
                'pid': p.pid,
                'name': p.name(),
                'memory_mb': p.memory_info().rss / 1024 / 1024,
                'cpu_percent': p.cpu_percent(),
                'ppid': p.ppid(),
                'username': username,
            })
    except Exception:
        pass
vm = psutil.virtual_memory()
swap = psutil.swap_memory()
print(json.dumps({
    'processes': procs,
    'memory': {
        'total_mb': vm.total / 1024 / 1024,
        'used_mb': vm.used / 1024 / 1024,
        'available_mb': vm.available / 1024 / 1024,
        'percent': vm.percent,
        'swap_total_mb': swap.total / 1024 / 1024,
        'swap_used_mb': swap.used / 1024 / 1024,
        'swap_percent': swap.percent,
    },
}))
" """
