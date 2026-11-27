"""telegram-service processi: long polling + outbox. Token bo'lmasa jim kutadi — tizim ishlayveradi."""

import asyncio

from app.core.process import run_process
from app.core.redis import get_redis

PROCESS_NAME = "telegram-service"


async def _main(stop: asyncio.Event) -> None:
    from telegram.service import TelegramService

    await TelegramService(get_redis()).run(stop)


def main() -> None:
    run_process(PROCESS_NAME, _main)


if __name__ == "__main__":
    main()
