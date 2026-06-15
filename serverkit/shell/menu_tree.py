"""Declarative menu tree for the interactive REPL menu."""

from __future__ import annotations

import importlib.util
import platform
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Union

from serverkit.shell.state import ReplState

ArgKind = Literal["string", "number", "path", "choice", "text"]
Availability = Callable[[ReplState], bool]


def _is_local(state: ReplState) -> bool:
    return state.remote is None


def _has_method(state: ReplState, name: str) -> bool:
    return hasattr(state.active, name)


def _has_extra(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _docker_available(state: ReplState) -> bool:
    """Local docker needs the docker-py extra; remote uses the host docker CLI."""
    if not _has_method(state, "docker"):
        return False
    if state.remote is not None:
        return True
    return _has_extra("docker")


def _default_log_path() -> str:
    if platform.system() == "Windows":
        return "C:\\Windows\\Temp\\app.log"
    return "/var/log/syslog"


@dataclass(frozen=True)
class MenuArg:
    name: str
    label: str
    kind: ArgKind = "string"
    default: str = ""
    choices: tuple[str, ...] = ()


@dataclass
class MenuNode:
    label: str


@dataclass
class MenuCategory(MenuNode):
    description: str = ""
    children: list[AnyMenuNode] = field(default_factory=list)
    available: Availability | None = None


@dataclass
class SetBase(MenuNode):
    template: str
    args: list[MenuArg] = field(default_factory=list)
    children: list[AnyMenuNode] = field(default_factory=list)
    description: str = ""


@dataclass
class ChainStep(MenuNode):
    suffix_template: str
    args: list[MenuArg] = field(default_factory=list)
    description: str = ""


@dataclass
class TerminalAction(MenuNode):
    suffix: str = ""
    description: str = ""


@dataclass
class FixedCommand(MenuNode):
    command: str
    description: str = ""


@dataclass
class WizardCommand(MenuNode):
    template: str
    args: list[MenuArg] = field(default_factory=list)
    available: Availability | None = None
    description: str = ""


AnyMenuNode = Union[
    MenuCategory,
    SetBase,
    ChainStep,
    TerminalAction,
    FixedCommand,
    WizardCommand,
]

_TERMINALS: list[AnyMenuNode] = [
    TerminalAction("Summarize", ".summarize()"),
    TerminalAction("Display table", ".display()"),
    TerminalAction("List all (.all())", ".all()"),
]

_LOG_TERMINALS: list[AnyMenuNode] = [
    TerminalAction("Summarize", ".summarize()"),
    TerminalAction("Display table", ".display()"),
    TerminalAction("List all lines", ".all()"),
]

_PROCESS_CHAIN: list[AnyMenuNode] = [
    ChainStep(
        "Filter: memory above (MB)",
        ".memory_above({n})",
        [MenuArg("n", "Memory threshold (MB)", "number", "500")],
    ),
    ChainStep(
        "Filter: CPU above (%)",
        ".cpu_above({n})",
        [MenuArg("n", "CPU threshold (%)", "number", "10")],
    ),
    ChainStep(
        "Filter: name contains",
        '.named({name})',
        [MenuArg("name", "Process name", "string", "python")],
    ),
    ChainStep(
        "Filter: for user",
        '.for_user({user})',
        [MenuArg("user", "Username", "string", "root")],
    ),
    ChainStep("Sort by memory", ".sort_by_memory()"),
    ChainStep("Sort by CPU", ".sort_by_cpu()"),
    *_TERMINALS,
]

_LOG_CHAIN: list[AnyMenuNode] = [
    ChainStep("Show errors only", ".errors()"),
    ChainStep("Show warnings only", ".warnings()"),
    ChainStep(
        "Contains text",
        '.contains({text})',
        [MenuArg("text", "Substring to find", "string", "error")],
    ),
    ChainStep(
        "Tail last N lines",
        ".tail({n})",
        [MenuArg("n", "Number of lines", "number", "20")],
    ),
    *_LOG_TERMINALS,
]

_DISK_CHAIN: list[AnyMenuNode] = [
    ChainStep(
        "Usage above (%)",
        ".usage_above({n})",
        [MenuArg("n", "Usage percent", "number", "80")],
    ),
    ChainStep(
        "Mount path contains",
        '.mount_contains({text})',
        [MenuArg("text", "Mount substring", "string", "/home")],
    ),
    ChainStep("Sort by used space", ".sort_by_used()"),
    *_TERMINALS,
]

_PORTS_CHAIN: list[AnyMenuNode] = [
    ChainStep("Listening only", ".listening()"),
    ChainStep(
        "Specific port",
        ".port({n})",
        [MenuArg("n", "Port number", "number", "443")],
    ),
    *_TERMINALS,
]

_SERVICES_CHAIN: list[AnyMenuNode] = [
    ChainStep("Active only", ".active()"),
    ChainStep(
        "Name contains",
        '.named({text})',
        [MenuArg("text", "Service name", "string", "nginx")],
    ),
    *_TERMINALS,
]

_CRON_CHAIN: list[AnyMenuNode] = [
    ChainStep("Suspicious jobs only", ".suspicious_only()"),
    *_TERMINALS,
]

_ENV_CHAIN: list[AnyMenuNode] = [
    ChainStep(
        "Variable names matching",
        '.keys_matching({text})',
        [MenuArg("text", "Name substring", "string", "PATH")],
    ),
    ChainStep(
        "Values containing",
        '.contains({text})',
        [MenuArg("text", "Value substring", "string", "python")],
    ),
    *_TERMINALS,
]

_NETWORK_INTERFACES: list[AnyMenuNode] = [
    ChainStep("Sort by traffic", ".sort_by_traffic()"),
    *_TERMINALS,
]

_NETWORK_CONNECTIONS: list[AnyMenuNode] = [
    ChainStep("Listening only", ".listening()"),
    ChainStep("Established only", ".established()"),
    ChainStep(
        "On port",
        ".on_port({n})",
        [MenuArg("n", "Port number", "number", "443")],
    ),
    *_TERMINALS,
]

_DOCKER_CHAIN: list[AnyMenuNode] = [
    ChainStep("Running containers", ".running()"),
    *_TERMINALS,
]


def root_categories() -> list[MenuCategory]:
    """Top-level menu categories."""
    return [
        MenuCategory(
            "Processes",
            "Inspect and filter running processes",
            children=[
                FixedCommand("List all processes (classic)", "processes.all()"),
                SetBase(
                    "Build a process chain",
                    "processes()",
                    children=_PROCESS_CHAIN,
                ),
            ],
        ),
        MenuCategory(
            "Logs",
            "Search and summarize log files",
            children=[
                SetBase(
                    "Open a log file",
                    'logs({path})',
                    [MenuArg("path", "Log file path", "path", _default_log_path())],
                    children=_LOG_CHAIN,
                ),
            ],
        ),
        MenuCategory(
            "Memory",
            "RAM and swap snapshot",
            children=[
                FixedCommand("Memory summary", "memory"),
                FixedCommand("Memory as JSON", "memory.json"),
            ],
        ),
        MenuCategory(
            "Disk & ports",
            "Storage and open ports",
            available=lambda s: _has_method(s, "disk") or _has_method(s, "ports"),
            children=[
                SetBase("Disk partitions", "disk()", children=_DISK_CHAIN),
                SetBase("Open ports", "ports()", children=_PORTS_CHAIN),
            ],
        ),
        MenuCategory(
            "Network & services",
            "Interfaces, connections, systemd services",
            children=[
                SetBase(
                    "Network interfaces",
                    "network.interfaces()",
                    children=_NETWORK_INTERFACES,
                ),
                SetBase(
                    "Network connections",
                    "network.connections()",
                    children=_NETWORK_CONNECTIONS,
                ),
                SetBase("System services", "services()", children=_SERVICES_CHAIN),
                WizardCommand(
                    "Control one service",
                    "service {unit} {action}",
                    [
                        MenuArg("unit", "Service unit", "text", "nginx.service"),
                        MenuArg(
                            "action",
                            "Action",
                            "choice",
                            "status",
                            ("status", "start", "stop", "restart", "is_active"),
                        ),
                    ],
                ),
            ],
        ),
        MenuCategory(
            "Cron, users & environment",
            "Scheduled jobs, sessions, env vars",
            available=lambda s: _has_method(s, "cron")
            or _has_method(s, "users")
            or _has_method(s, "env"),
            children=[
                SetBase("Cron jobs", "cron()", children=_CRON_CHAIN),
                SetBase(
                    "Logged-in users",
                    "users.logged_in()",
                    children=_TERMINALS,
                ),
                SetBase(
                    "Failed login attempts",
                    "users.failed_logins()",
                    children=_TERMINALS,
                ),
                SetBase("Environment variables", "env()", children=_ENV_CHAIN),
            ],
        ),
        MenuCategory(
            "Docker",
            "Container inspection (requires docker extra)",
            available=_docker_available,
            children=[
                SetBase(
                    "Docker containers",
                    "docker().containers()",
                    children=_DOCKER_CHAIN,
                ),
                WizardCommand(
                    "Container logs",
                    'docker.logs({name}, {tail})',
                    [
                        MenuArg("name", "Container name", "string", "mycontainer"),
                        MenuArg("tail", "Tail lines", "number", "100"),
                    ],
                ),
                WizardCommand(
                    "Container stats",
                    'docker.stats({name})',
                    [MenuArg("name", "Container name", "string", "mycontainer")],
                ),
            ],
        ),
        MenuCategory(
            "Workflows",
            "Saved and catalog workflows",
            children=[
                FixedCommand("List saved workflows", "workflow list"),
                FixedCommand("List catalog templates", "catalog"),
                WizardCommand(
                    "Run a workflow",
                    "run {name}",
                    [MenuArg("name", "Workflow name", "text", "memory_audit")],
                ),
                WizardCommand(
                    "Import catalog template",
                    "import {name}",
                    [MenuArg("name", "Catalog name", "text", "memory_audit")],
                    available=_is_local,
                ),
            ],
        ),
        MenuCategory(
            "Remote SSH",
            "Connect to a remote host",
            available=lambda _: _has_extra("paramiko"),
            children=[
                WizardCommand(
                    "Connect to host",
                    "connect {host}",
                    [
                        MenuArg("host", "Hostname or IP", "text", "192.168.1.10"),
                        MenuArg("user", "SSH user (optional)", "text", ""),
                    ],
                ),
                FixedCommand("Disconnect", "disconnect"),
            ],
        ),
        MenuCategory(
            "AI assistant",
            "Natural language queries (requires ai extra)",
            available=lambda _: _has_extra("requests"),
            children=[
                WizardCommand(
                    "Ask a question",
                    "ask {question}",
                    [
                        MenuArg(
                            "question",
                            "Your question",
                            "text",
                            "show top memory processes",
                        ),
                    ],
                ),
            ],
        ),
    ]


def is_terminal(node: AnyMenuNode) -> bool:
    return isinstance(node, (TerminalAction, FixedCommand, WizardCommand))


def node_available(node: AnyMenuNode, state: ReplState) -> bool:
    available = getattr(node, "available", None)
    if callable(available) and not available(state):
        return False
    if isinstance(node, MenuCategory) and node.available and not node.available(state):
        return False
    if isinstance(node, SetBase):
        if node.template.startswith("disk") and not _has_method(state, "disk"):
            return False
        if node.template.startswith("ports") and not _has_method(state, "ports"):
            return False
        if node.template.startswith("cron") and not _has_method(state, "cron"):
            return False
        if node.template.startswith("users") and not _has_method(state, "users"):
            return False
        if node.template.startswith("env") and not _has_method(state, "env"):
            return False
        if node.template.startswith("network") and not _has_method(state, "network"):
            return False
        if node.template.startswith("services") and not _has_method(state, "services"):
            return False
        if node.template.startswith("docker") and not _docker_available(state):
            return False
    return True


def filter_nodes(nodes: list[AnyMenuNode], state: ReplState) -> list[AnyMenuNode]:
    return [node for node in nodes if node_available(node, state)]


def filter_categories(state: ReplState) -> list[MenuCategory]:
    return [
        cat
        for cat in root_categories()
        if (cat.available is None or cat.available(state))
        and filter_nodes(cat.children, state)
    ]
