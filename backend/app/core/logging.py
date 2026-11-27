"""Yagona log formati: konsol (systemd ostida journald'ga tushadi) + aylanuvchi fayl.

Har qatorda process nomi bor: `2026-11-26 21:40:00 INFO [api] app.main: ...`
"""

import logging
import logging.handlers
import sys

from app.core.config import get_settings

_FORMAT = "%(asctime)s %(levelname)s [%(process_name)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


class _ProcessNameFilter(logging.Filter):
    def __init__(self, process_name: str) -> None:
        super().__init__()
        self.process_name = process_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.process_name = self.process_name
        return True


def setup_logging(process_name: str, *, to_file: bool = True) -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())

    flt = _ProcessNameFilter(process_name)
    fmt = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    console.addFilter(flt)
    root.addHandler(console)

    if to_file:
        log_dir = settings.data_subdir("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.TimedRotatingFileHandler(
            log_dir / f"{process_name}.log", when="midnight", backupCount=30, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        fh.addFilter(flt)
        root.addHandler(fh)

    # uvicorn o'z handler'larini qo'shmasin — hammasi root orqali o'tadi
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
