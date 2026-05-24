#!/usr/bin/env python3
"""Example: per-PID vs app-aggregated memory view."""

from serverkit import Server


def main() -> None:
    server = Server()
    procs = server.processes().sort_by_memory()

    print("=== Per PID (top 5) ===")
    print(procs.display(use_rich=False))

    print("\n=== By app name (RSS summed) ===")
    print(procs.display_by_name(use_rich=False))


if __name__ == "__main__":
    main()
