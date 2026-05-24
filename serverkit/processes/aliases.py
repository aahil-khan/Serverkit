"""Map child process names to parent app labels (task-manager style)."""

from __future__ import annotations

# psutil name -> display app name
CHILD_TO_APP: dict[str, str] = {
    "Isolated Web Co": "firefox",
    "WebExtensions": "firefox",
    "Privileged Cont": "firefox",
    "forkserver": "firefox",
    "Socket Process": "firefox",
    "RDD Process": "firefox",
    "Utility Process": "firefox",
    "missioncenter-magpie-glibc": "missioncenter",
}


def app_name(process_name: str) -> str:
    """Return the app label for a psutil process name."""
    return CHILD_TO_APP.get(process_name, process_name)
