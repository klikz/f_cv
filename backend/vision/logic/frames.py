"""camera-logic uchun kadr manbasi: Redis'dagi oqim holatidan shm nomini olib, oxirgi kadrni o'qiydi."""

from __future__ import annotations

import time

import numpy as np
from redis import Redis

from app.core import keys
from vision.video.shm import ReaderCache


class FrameSource:
    def __init__(self, redis: Redis, camera_id: int) -> None:
        self.r = redis
        self.camera_id = camera_id
        self.cache = ReaderCache()
        self.status: dict[str, dict[str, str]] = {"main": {}, "sub": {}}
        self._last_refresh = 0.0
        self.last_seq: dict[str, int] = {"main": 0, "sub": 0}

    def refresh(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_refresh < 1.0:
            return
        self._last_refresh = now
        for kind in ("main", "sub"):
            self.status[kind] = self.r.hgetall(keys.stream_status(self.camera_id, kind)) or {}

    def online(self, kind: str) -> bool:
        return self.status.get(kind, {}).get("status") == "online"

    def size(self, kind: str) -> tuple[int, int] | None:
        st = self.status.get(kind) or {}
        try:
            return int(st["width"]), int(st["height"])
        except (KeyError, ValueError):
            return None

    def latest(self, kind: str, *, only_new: bool = False, copy: bool = False) -> tuple[int, float, np.ndarray] | None:
        if not self.online(kind):
            return None
        reader = self.cache.get(self.status[kind].get("shm"))
        if reader is None:
            return None
        seq = reader.latest_seq
        if only_new and seq <= self.last_seq[kind]:
            return None
        res = reader.read(copy=copy)
        if res is None:
            return None
        if only_new:
            self.last_seq[kind] = res[0]
        return res

    def by_seq(self, kind: str, seq: int) -> tuple[int, float, np.ndarray] | None:
        reader = self.cache.get(self.status.get(kind, {}).get("shm"))
        return reader.read(seq) if reader else None

    def close(self) -> None:
        self.cache.close()
