#!/usr/bin/env python3
"""Example: log error audit workflow."""

from serverkit import Server


def main() -> None:
    server = Server()
    path = "app.log"
    (
        server.workflow("log_audit")
        .logs(path)
        .errors()
        .tail(20)
        .summarize()
        .save()
    )
    ctx = server.run("log_audit")
    print(ctx.get("summary", ""))


if __name__ == "__main__":
    main()
