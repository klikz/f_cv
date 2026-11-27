"""inference-server processi: TRT engine menejeri, batch inference."""

import asyncio
import threading

from app.core.process import run_process

PROCESS_NAME = "inference-server"


async def _main(stop: asyncio.Event) -> None:
    from training.ml_env import setup_ultralytics_env
    from vision.inference.server import InferenceServer

    setup_ultralytics_env()
    import logging as _lg

    class _Drop(_lg.Filter):
        def filter(self, r: _lg.LogRecord) -> bool:
            return "deprecated" not in r.getMessage()

    _lg.getLogger("ultralytics").addFilter(_Drop())
    th_stop = threading.Event()
    srv = InferenceServer()
    th = threading.Thread(target=srv.run, args=(th_stop,), name="inference", daemon=True)
    th.start()
    await stop.wait()
    th_stop.set()
    await asyncio.to_thread(th.join, 10)


def main() -> None:
    run_process(PROCESS_NAME, _main)


if __name__ == "__main__":
    main()
