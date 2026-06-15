"""SSH-backed disk collections (remote ``find`` / ``du``, not local ``os.walk``)."""

from __future__ import annotations

import shlex

from serverkit.disk.manager import DiskCollection, FileEntryCollection
from serverkit.disk.partition import FileEntry, Partition
from serverkit.remote.connection import SSHConnection
from serverkit.remote.host_parsers import file_entries_from_find_printf_output


class RemoteDiskCollection(DiskCollection):
    """Disk partitions from remote ``df``; largest files via remote ``find``."""

    def __init__(self, connection: SSHConnection, partitions: list[Partition]) -> None:
        super().__init__(partitions)
        self._conn = connection

    def largest_files(self, root: str, limit: int = 20) -> FileEntryCollection:
        q = shlex.quote(root)
        lim = max(1, min(int(limit), 500))
        # GNU find (typical on Linux remotes); avoids scanning the operator's machine.
        cmd = f"find {q} -type f -printf '%s\\t%p\\n' 2>/dev/null | sort -nr | head -n {lim}"
        out = self._conn.run(cmd, check=False)
        entries = file_entries_from_find_printf_output(out, limit=lim)
        return FileEntryCollection(entries)

    def dir_size(self, path: str) -> float:
        q = shlex.quote(path)
        out = self._conn.run(f"du -sk {q} 2>/dev/null | head -n 1", check=False).strip()
        if not out:
            return 0.0
        first = out.split()[0]
        try:
            kb = float(first)
        except ValueError:
            return 0.0
        return kb / 1024
