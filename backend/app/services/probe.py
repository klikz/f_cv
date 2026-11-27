"""Oqimni tekshirish (ffprobe) va bitta kadr olish (ffmpeg).

Faqat kamera qo'shish/tahrirlash paytida (video-service hali bu oqimni ochmagan) ishlatiladi.
"""

import asyncio
import json
import shutil
from dataclasses import dataclass

from app.core.urls import mask_url

FFPROBE = shutil.which("ffprobe") or "ffprobe"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


@dataclass
class ProbeResult:
    ok: bool
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    error: str | None = None


def humanize_error(stderr: str, url: str) -> str:
    s = stderr.lower()
    if "401" in s or "unauthorized" in s:
        return "Kameraga ulanib bo'lmadi: login yoki parol xato"
    if "404" in s or "not found" in s:
        return "Oqim topilmadi: manzil yo'li (path) xato"
    if "connection refused" in s:
        return "Kamera ulanishni rad etdi: IP yoki port xato, yoki RTSP o'chirilgan"
    if "no route to host" in s or "network is unreachable" in s or "host is down" in s:
        return "Kamera tarmoqda topilmadi: IP manzil va kabelni tekshiring"
    if "timed out" in s or "timeout" in s:
        return "Kamera javob bermadi (vaqt tugadi): IP manzil va tarmoqni tekshiring"
    if "invalid data" in s:
        return "Kamera noto'g'ri ma'lumot qaytardi: manzil RTSP oqimi ekanini tekshiring"
    if "name or service not known" in s or "failed to resolve" in s:
        return "Kamera manzili (host) topilmadi"
    last = stderr.strip().splitlines()[-1] if stderr.strip() else "noma'lum xato"
    return f"Oqimni ochib bo'lmadi ({mask_url(url)}): {last[:200]}"


def _input_args(url: str) -> list[str]:
    args = ["-rw_timeout", "8000000"]
    if url.startswith("rtsp"):
        args = ["-rtsp_transport", "tcp", "-timeout", "8000000"]
    return args


def _parse_fps(rate: str | None) -> float | None:
    if not rate or rate in {"0/0", "0"}:
        return None
    try:
        num, _, den = rate.partition("/")
        v = float(num) / float(den or 1)
        return round(v, 2) if v > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


async def probe_stream(url: str, timeout: float = 12.0) -> ProbeResult:
    cmd = [
        FFPROBE,
        "-v",
        "error",
        *_input_args(url),
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,avg_frame_rate,r_frame_rate",
        "-of",
        "json",
        url,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            return ProbeResult(False, error="Kamera javob bermadi (vaqt tugadi): IP manzil va tarmoqni tekshiring")
    except FileNotFoundError:
        return ProbeResult(False, error="ffprobe topilmadi — serverga ffmpeg o'rnatilmagan")
    if proc.returncode != 0:
        return ProbeResult(False, error=humanize_error(err.decode(errors="replace"), url))
    try:
        streams = json.loads(out or b"{}").get("streams") or []
    except json.JSONDecodeError:
        streams = []
    if not streams:
        return ProbeResult(False, error="Oqimda video topilmadi")
    s = streams[0]
    fps = _parse_fps(s.get("avg_frame_rate")) or _parse_fps(s.get("r_frame_rate"))
    return ProbeResult(True, codec=s.get("codec_name"), width=s.get("width"), height=s.get("height"), fps=fps)


async def grab_frame_jpeg(url: str, timeout: float = 15.0, max_width: int = 1280) -> tuple[bytes | None, str | None]:
    """Oqimdan bitta kadr (JPEG). Xato bo'lsa (None, xabar)."""
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",
        *_input_args(url),
        "-i",
        url,
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({max_width},iw)':-2",
        "-q:v",
        "4",
        "-f",
        "image2",
        "-c:v",
        "mjpeg",
        "-",
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return None, "Kamera javob bermadi (vaqt tugadi)"
    if proc.returncode != 0 or not out:
        return None, humanize_error(err.decode(errors="replace"), url)
    return out, None
