from __future__ import annotations

from serverkit.core.collection import FluentCollection
from serverkit.core.display import display_table, export_table, resolve_use_rich
from serverkit.docker.container import Container
from serverkit.exceptions import OptionalDependencyError


def _client():
    try:
        import docker
    except ImportError as exc:
        raise OptionalDependencyError(
            "Install docker support: pip install serverkit[docker]"
        ) from exc
    return docker.from_env()


class ContainerCollection(FluentCollection[Container]):
    def running(self) -> ContainerCollection:
        self.data = [c for c in self.data if "up" in c.status.lower()]
        return self

    def summarize(self) -> str:
        return "\n".join(repr(c) for c in self.data[:20])

    def display(self, *, use_rich: bool | None = None) -> str:
        rows = [[c.name, c.image, c.status, c.id] for c in self.data]
        return display_table(
            "Containers",
            ["Name", "Image", "Status", "ID"],
            rows,
            use_rich=resolve_use_rich(use_rich),
        )

    def export(self, path: str, fmt: str = "csv") -> None:
        export_table(
            path,
            ["name", "image", "status", "id"],
            [[c.name, c.image, c.status, c.id] for c in self.data],
            fmt=fmt,
        )


class DockerManager:
    def containers(self) -> ContainerCollection:
        client = _client()
        items = [
            Container(
                id=c.id[:12],
                name=(c.name or ""),
                image=(c.image.tags[0] if c.image.tags else str(c.image.id)[:12]),
                status=c.status,
            )
            for c in client.containers.list(all=True)
        ]
        return ContainerCollection(items)

    def logs(self, name: str, tail: int = 100) -> str:
        client = _client()
        container = client.containers.get(name)
        return container.logs(tail=tail).decode("utf-8", errors="replace")

    def stats(self, name: str) -> dict:
        client = _client()
        container = client.containers.get(name)
        raw = container.stats(stream=False)
        mem = raw.get("memory_stats", {})
        return {
            "name": name,
            "memory_usage": mem.get("usage"),
            "memory_limit": mem.get("limit"),
        }
