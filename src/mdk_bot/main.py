"""Process entry point — dispatches to api/bot/scheduler/worker by argv."""

from __future__ import annotations

import argparse
import asyncio
import sys

from mdk_bot.shared.logging import configure_logging


def main() -> None:
    """Dispatch ``python -m mdk_bot <service>``."""
    parser = argparse.ArgumentParser(prog="mdk_bot")
    parser.add_argument(
        "service",
        choices=["api", "bot", "scheduler", "worker"],
        help="Which service to launch.",
    )
    args = parser.parse_args()

    configure_logging()

    if args.service == "api":
        import uvicorn

        uvicorn.run("mdk_bot.api.app:app", host="0.0.0.0", port=8000, reload=False)
    elif args.service == "bot":
        from mdk_bot.bot.app import run_bot

        run_bot()
    elif args.service == "scheduler":
        from mdk_bot.scheduler.app import run_scheduler

        asyncio.run(run_scheduler())
    elif args.service == "worker":
        # Reserved for Phase 4+ (Playwright RPA jobs, etc).
        print("Worker not implemented yet.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
