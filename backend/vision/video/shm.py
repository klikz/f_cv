"""Shared memory halqa-bufer: har (kamera, oqim) uchun bitta segment.

Tuzilma:
  sarlavha (64 B):  magic 'FCV1' | slots u32 | width u32 | height u32 | channels u32 | ... | write_seq u64 @32
  slot meta (slots × 32 B):  seq u64 | ts f64 (unix vaqt) | ...
  ma'lumot (slots × w×h×c):  BGR kadrlar

Yozuvchi (video-service) bitta, o'quvchilar (camera-logic, inference-server) ko'p.
Seqlock: yozuvchi slot seq ni 0 qiladi → kadrni yozadi → seq = n → write_seq = n.
O'quvchi nusxa olishdan oldin va keyin slot seq ni tekshiradi — yarim yozilgan kadr o'qilmaydi.

Segment nomi Redis'dagi oqim holatida (`shm` maydoni) e'lon qilinadi; o'lcham o'zgarsa
yozuvchi yangi nom bilan qayta yaratadi.
"""

from __future__ import annotations

import contextlib
import os
import struct
import time
from multiprocessing import resource_tracker, shared_memory

import numpy as np

MAGIC = b"FCV1"
HEADER = 64
SLOT_META = 32
WRITE_SEQ_OFF = 32


def segment_name(camera_id: int, kind: str, gen: int) -> str:
    return f"fcv_{camera_id}_{kind}_{gen}"


def _untrack(shm: shared_memory.SharedMemory) -> None:
    # Python 3.12: o'quvchi yopilganda ham resource_tracker segmentni o'chirib yubormasin
    with contextlib.suppress(Exception):
        resource_tracker.unregister(shm._name, "shared_memory")  # type: ignore[attr-defined]


def _unlink(name: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(os.path.join("/dev/shm", name.lstrip("/")))


def cleanup_stale(prefix: str = "fcv_") -> int:
    """Yiqilgan processdan qolgan segmentlarni tozalash (video-service ishga tushganda)."""
    n = 0
    try:
        names = os.listdir("/dev/shm")
    except OSError:
        return 0
    for name in names:
        if name.startswith(prefix):
            with contextlib.suppress(OSError):
                os.unlink(os.path.join("/dev/shm", name))
                n += 1
    return n


class FrameRingWriter:
    def __init__(self, name: str, width: int, height: int, slots: int = 12, channels: int = 3) -> None:
        self.name, self.w, self.h, self.c, self.slots = name, width, height, channels, slots
        self.frame_bytes = width * height * channels
        size = HEADER + slots * SLOT_META + slots * self.frame_bytes
        with contextlib.suppress(FileNotFoundError):
            old = shared_memory.SharedMemory(name=name)
            _untrack(old)
            old.close()
            _unlink(name)
        self.shm = shared_memory.SharedMemory(name=name, create=True, size=size)
        _untrack(self.shm)
        buf = self.shm.buf
        struct.pack_into("<4sIIII", buf, 0, MAGIC, slots, width, height, channels)
        struct.pack_into("<Q", buf, WRITE_SEQ_OFF, 0)
        self._meta = np.ndarray((slots, 4), dtype=np.uint64, buffer=buf, offset=HEADER)
        self._ts = np.ndarray((slots, 4), dtype=np.float64, buffer=buf, offset=HEADER)
        self._data = np.ndarray(
            (slots, height, width, channels), dtype=np.uint8, buffer=buf, offset=HEADER + slots * SLOT_META
        )
        self._wseq = np.ndarray((1,), dtype=np.uint64, buffer=buf, offset=WRITE_SEQ_OFF)
        self.seq = 0

    def write(self, frame: np.ndarray, ts: float | None = None) -> int:
        if frame.shape != (self.h, self.w, self.c):
            raise ValueError(f"kadr o'lchami {frame.shape} != {(self.h, self.w, self.c)}")
        self.seq += 1
        slot = self.seq % self.slots
        self._meta[slot, 0] = 0  # yozilmoqda
        self._data[slot][...] = frame
        self._ts[slot, 1] = ts if ts is not None else time.time()
        self._meta[slot, 0] = self.seq
        self._wseq[0] = self.seq
        return self.seq

    def close(self, unlink: bool = True) -> None:
        for a in ("_meta", "_ts", "_data", "_wseq"):
            setattr(self, a, None)
        with contextlib.suppress(Exception):
            self.shm.close()
        if unlink:
            _unlink(self.name)


class FrameRingReader:
    def __init__(self, name: str) -> None:
        self.name = name
        self.shm = shared_memory.SharedMemory(name=name)
        _untrack(self.shm)
        buf = self.shm.buf
        magic, slots, w, h, c = struct.unpack_from("<4sIIII", buf, 0)
        if magic != MAGIC:
            self.shm.close()
            raise ValueError("segment formati noto'g'ri")
        self.slots, self.w, self.h, self.c = slots, w, h, c
        self._meta = np.ndarray((slots, 4), dtype=np.uint64, buffer=buf, offset=HEADER)
        self._ts = np.ndarray((slots, 4), dtype=np.float64, buffer=buf, offset=HEADER)
        self._data = np.ndarray((slots, h, w, c), dtype=np.uint8, buffer=buf, offset=HEADER + slots * SLOT_META)
        self._wseq = np.ndarray((1,), dtype=np.uint64, buffer=buf, offset=WRITE_SEQ_OFF)

    @property
    def latest_seq(self) -> int:
        return int(self._wseq[0])

    def read(self, seq: int | None = None, copy: bool = True) -> tuple[int, float, np.ndarray] | None:
        """Berilgan (yoki oxirgi) kadr. Kadr buferdan chiqib ketgan bo'lsa None."""
        for _ in range(3):
            want = self.latest_seq if seq is None else seq
            if want <= 0:
                return None
            slot = want % self.slots
            if int(self._meta[slot, 0]) != want:
                if seq is not None:
                    return None
                continue
            ts = float(self._ts[slot, 1])
            data = self._data[slot].copy() if copy else self._data[slot]
            if int(self._meta[slot, 0]) == want:
                return want, ts, data
        return None

    def close(self) -> None:
        for a in ("_meta", "_ts", "_data", "_wseq"):
            setattr(self, a, None)
        with contextlib.suppress(Exception):
            self.shm.close()


class ReaderCache:
    """Segment nomi o'zgarsa qayta ochadigan o'quvchilar keshi."""

    def __init__(self) -> None:
        self._readers: dict[str, FrameRingReader] = {}

    def get(self, name: str | None) -> FrameRingReader | None:
        if not name:
            return None
        r = self._readers.get(name)
        if r is not None:
            return r
        try:
            r = FrameRingReader(name)
        except (FileNotFoundError, ValueError):
            return None
        # eski nomlarni (shu kamera/oqimning oldingi avlodi) yopish
        prefix = name.rsplit("_", 1)[0] + "_"
        for old in [n for n in self._readers if n.startswith(prefix) and n != name]:
            self._readers.pop(old).close()
        self._readers[name] = r
        return r

    def drop(self, name: str) -> None:
        r = self._readers.pop(name, None)
        if r:
            r.close()

    def close(self) -> None:
        for r in self._readers.values():
            r.close()
        self._readers.clear()
