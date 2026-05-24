from __future__ import annotations


class Container:
    def __init__(self, id: str, name: str, image: str, status: str):
        self.id = id
        self.name = name
        self.image = image
        self.status = status

    def __repr__(self) -> str:
        return f"Container({self.name!r}, {self.status})"
