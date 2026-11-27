"""Dekod backend'lari — bir xil interfeys: ochish → kadrlar (BGR, ≤10 fps) → yopish.

- `pyav`  : PyAV (FFmpeg kutubxonasi) — CPU yoki NVDEC (cuda) / QSV; bitta process ichida.
- `ffmpeg`: tashqi ffmpeg processi (rawvideo pipe) — VAAPI uchun (PyAV qurilmasida vaapi yo'q).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)

BACKENDS = ("cpu", "nvdec", "vaapi", "qsv")


@dataclass
class DecodedFrame:
    image: np.ndarray  # BGR
    ts: float  # server vaqti (unix)


class Decoder(Protocol):
    codec: str | None
    width: int
    height: int
    src_fps: float | None

    def frames(self) -> Iterator[DecodedFrame]: ...

    def close(self) -> None: ...


class StreamError(Exception):
    """Ulanish/dekod xatosi — foydalanuvchiga ko'rsatiladigan matn bilan."""


def humanize(e: BaseException) -> str:
    s = str(e).lower()
    if "401" in s or "unauthorized" in s:
        return "Login yoki parol xato"
    if "404" in s or "not found" in s:
        return "Oqim topilmadi (manzil yo'li xato)"
    if "refused" in s:
        return "Kamera ulanishni rad etdi"
    if "timed out" in s or "timeout" in s or "etimedout" in s:
        return "Kamera javob bermayapti (vaqt tugadi)"
    if "unreachable" in s or "no route" in s:
        return "Kamera tarmoqda topilmadi"
    if "end of file" in s or "eof" in s:
        return "Oqim uzildi"
    return str(e)[:200] or e.__class__.__name__


class _Decimator:
    """Kadrlarni server vaqti bo'yicha maqsadli FPS gacha siyraklashtiradi."""

    def __init__(self, fps: float) -> None:
        self.period = 1.0 / fps
        self.next = 0.0

    def take(self, now: float) -> bool:
        if now >= self.next:
            # orqada qolsak (masalan, qotishdan keyin) — tutib olishga urinmaymiz
            self.next = now + self.period if now - self.next > self.period else self.next + self.period
            return True
        return False


class PyAVDecoder:
    def __init__(self, url: str, backend: str = "cpu", target_fps: float = 10.0, read_timeout: float = 6.0) -> None:
        import av
        from av.codec.hwaccel import HWAccel

        hw = None
        if backend == "nvdec":
            hw = HWAccel(device_type="cuda", allow_software_fallback=True)
        elif backend == "qsv":
            hw = HWAccel(device_type="qsv", allow_software_fallback=True)
        opts = {"rtsp_transport": "tcp", "fflags": "nobuffer", "flags": "low_delay", "max_delay": "500000"}
        try:
            self.c = av.open(url, options=opts, timeout=(10.0, read_timeout), hwaccel=hw)
        except Exception as e:
            raise StreamError(humanize(e)) from e
        if not self.c.streams.video:
            self.c.close()
            raise StreamError("Oqimda video yo'q")
        self.s = self.c.streams.video[0]
        if backend == "cpu":
            self.s.thread_type = "AUTO"
        cc = self.s.codec_context
        self.codec = cc.name
        self.width, self.height = cc.width, cc.height
        self.src_fps = float(self.s.average_rate) if self.s.average_rate else None
        self.dec = _Decimator(target_fps)

    def frames(self) -> Iterator[DecodedFrame]:
        try:
            for frame in self.c.decode(self.s):
                now = time.time()
                if not self.dec.take(now):
                    continue
                img = frame.to_ndarray(format="bgr24")
                yield DecodedFrame(img, now)
        except Exception as e:
            raise StreamError(humanize(e)) from e
        raise StreamError("Oqim uzildi")

    def close(self) -> None:
        try:
            self.c.close()
        except Exception:
            pass


class FFmpegPipeDecoder:
    """VAAPI: `ffmpeg -hwaccel vaapi ... -vf fps=10 -f rawvideo bgr24 -`."""

    def __init__(self, url: str, backend: str = "vaapi", target_fps: float = 10.0, read_timeout: float = 6.0) -> None:
        from app.services.probe import FFPROBE

        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        probe = subprocess.run(
            [
                FFPROBE,
                "-v",
                "error",
                "-rtsp_transport",
                "tcp",
                "-timeout",
                "8000000",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height,avg_frame_rate",
                "-of",
                "csv=p=0",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            raise StreamError(humanize(Exception(probe.stderr.strip() or "probe xato")))
        codec, w, h, rate = probe.stdout.strip().split("\n")[0].split(",")[:4]
        self.codec, self.width, self.height = codec, int(w), int(h)
        try:
            num, den = rate.split("/")
            self.src_fps = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            self.src_fps = None
        hw = ["-hwaccel", "vaapi", "-hwaccel_device", "/dev/dri/renderD128"] if backend == "vaapi" else []
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-timeout",
            "8000000",
            *hw,
            "-i",
            url,
            "-vf",
            f"fps={target_fps}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-",
        ]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.frame_bytes = self.width * self.height * 3
        self.read_timeout = read_timeout
        self._stderr: list[str] = []
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        assert self.p.stderr
        for line in iter(self.p.stderr.readline, b""):
            self._stderr = [*self._stderr, line.decode(errors="replace").strip()][-5:]

    def frames(self) -> Iterator[DecodedFrame]:
        assert self.p.stdout
        buf = bytearray(self.frame_bytes)
        mv = memoryview(buf)
        while True:
            got = 0
            while got < self.frame_bytes:
                n = self.p.stdout.readinto(mv[got:])
                if not n:
                    raise StreamError(humanize(Exception(" ".join(self._stderr) or "Oqim uzildi")))
                got += n
            img = np.frombuffer(buf, np.uint8).reshape(self.height, self.width, 3).copy()
            yield DecodedFrame(img, time.time())

    def close(self) -> None:
        if self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(3)
            except subprocess.TimeoutExpired:
                self.p.kill()


def open_decoder(url: str, backend: str, target_fps: float = 10.0) -> Decoder:
    if backend == "vaapi":
        return FFmpegPipeDecoder(url, backend, target_fps)
    return PyAVDecoder(url, backend, target_fps)


def detect_backend() -> str:
    """`auto` uchun: VAAPI (Intel iGPU bo'lsa) → CPU.

    NVDEC benchmarkda chiqarildi: PyAV har oqimga alohida CUDA konteksti ochadi (~400 MB VRAM/oqim,
    15 sub = 6 GB) — 8 GB lik RTX 3070 da inference uchun joy qolmaydi. Majburan: FCV_DECODE_BACKEND=nvdec.
    """
    import os

    if os.path.exists("/dev/dri/renderD128") and shutil.which("vainfo"):
        r = subprocess.run(["vainfo"], capture_output=True, text=True)
        if "VAProfileH264" in r.stdout:
            return "vaapi"
    return "cpu"
