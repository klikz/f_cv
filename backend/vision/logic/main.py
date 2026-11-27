"""camera-logic: `--supervisor` — har faol kamera uchun process boshqaruvchisi;
`--camera-id N` — bitta kamera logikasi (tracker, sanash, harakat/sikl, JPEG).
"""

import argparse
import asyncio
import logging
import threading

from app.core.process import run_process

log = logging.getLogger(__name__)


def _camera_main(camera_id: int):
    async def _main(stop: asyncio.Event) -> None:
        from vision.logic.worker import CameraLogic

        th_stop = threading.Event()
        logic = CameraLogic(camera_id)

        def runner() -> None:
            try:
                logic.run(th_stop)
            except Exception:
                log.exception("camera-logic yiqildi")
                raise
            finally:
                logic.close()

        th = threading.Thread(target=runner, name=f"logic-{camera_id}", daemon=True)
        th.start()
        while th.is_alive() and not stop.is_set():  # noqa: ASYNC110
            await asyncio.sleep(0.5)
        th_stop.set()
        await asyncio.to_thread(th.join, 10)
        if not stop.is_set():
            raise SystemExit(1)  # thread yiqildi — supervisor qayta ko'taradi

    return _main


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="fcv camera-logic")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--camera-id", type=int)
    g.add_argument("--supervisor", action="store_true")
    args = p.parse_args(argv)
    if args.supervisor:
        from vision.logic.supervisor import supervisor_main

        run_process("camera-logic", supervisor_main)
    else:
        run_process(f"camera-logic:{args.camera_id}", _camera_main(args.camera_id))


if __name__ == "__main__":
    main()
