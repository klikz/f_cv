"""trainer processi: train navbati, TensorRT eksport, avto-belgilash."""

import asyncio

from app.core.process import run_process
from app.core.redis import get_redis

PROCESS_NAME = "trainer"


async def _main(stop: asyncio.Event) -> None:
    from training.service import TrainerService

    await TrainerService(get_redis()).run(stop)


def main() -> None:
    run_process(PROCESS_NAME, _main)


if __name__ == "__main__":
    main()
