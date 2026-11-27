"""Atomar fayl yozish (PLAN.md 1.14): vaqtinchalik fayl → fsync → nomini almashtirish."""

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _fsync_dir(path.parent)


def atomic_replace(src: Path, dst: Path) -> None:
    """Tayyor faylni (masalan, train natijasi) atomar ko'chirish."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f:
        os.fsync(f.fileno())
    os.replace(src, dst)
    _fsync_dir(dst.parent)


def _fsync_dir(d: Path) -> None:
    try:
        fd = os.open(d, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def cleanup_tmp_files(root: Path) -> int:
    """Elektr o'chganda qolgan yarim yozilgan `.tmp` fayllarni o'chirish."""
    n = 0
    if not root.exists():
        return 0
    for p in root.rglob(".*.tmp"):
        try:
            p.unlink()
            n += 1
        except OSError:
            pass
    return n
