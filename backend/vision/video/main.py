"""video-service processi: dekod (asosiy/sub oqimlar), shared memory."""

import asyncio

from app.core.process import run_process
from app.core.redis import get_redis

PROCESS_NAME = "video-service"


async def _main(stop: asyncio.Event) -> None:
    from vision.video.service import VideoService

    await VideoService(get_redis()).run(stop)


def main() -> None:
    run_process(PROCESS_NAME, _main)


if __name__ == "__main__":
    main()
