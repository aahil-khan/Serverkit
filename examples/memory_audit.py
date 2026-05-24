#!/usr/bin/env python3
"""Example: build and run a memory audit workflow."""

from serverkit import Server


def main() -> None:
    server = Server()
    server.workflow("memory_audit").processes().memory_above(500).sort_by_memory().summarize().save()
    result = server.run("memory_audit")
    print(result.get("summary", ""))


if __name__ == "__main__":
    main()
