"""Package entry point — ``python -m mdk_bot <service>``.

Dispatches to the api, bot, scheduler, or worker process based on the
first positional argument.
"""

from __future__ import annotations

import asyncio
import sys

USAGE = "Usage: python -m mdk_bot {api|bot|scheduler|worker}"


def _usage(message: str | None = None) -> None:
    if message:
        print(message, file=sys.stderr)
    print(USAGE, file=sys.stderr)


def main() -> None:
    if len(sys.argv) < 2:
        _usage("error: missing service argument")
        sys.exit(1)

    service = sys.argv[1]

    if service == "api":
        import uvicorn

        uvicorn.run("mdk_bot.api.app:app", host="0.0.0.0", port=8000, reload=False)
    elif service == "bot":
        from mdk_bot.bot.app import run_bot

        run_bot()
    elif service == "scheduler":
        from mdk_bot.scheduler.app import run_scheduler

        asyncio.run(run_scheduler())
    elif service == "worker":
        print("Worker not implemented yet.", file=sys.stderr)
        sys.exit(1)
    else:
        _usage(f"error: unknown service {service!r}")
        sys.exit(1)


if __name__ == "__main__":
    main()
