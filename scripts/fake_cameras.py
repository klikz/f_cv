"""Sinov uchun soxta IP kameralar (RTSP, main + sub oqim).

Haqiqiy kamerasiz butun zanjirni (dekod → belgilash → train → sanash → uskuna) sinash uchun:
  - `conveyor` sahnasi: konveyerda mahsulotlar chapdan o'ngga o'tadi (4 tur, ba'zilari qutida,
    ba'zan bir-biriga tegib), har siklda o'tgan mahsulotlar soni `truth.json` ga yoziladi;
  - `press` sahnasi: press ishlaydi (3 s sikl), har 60 s da 20 s to'xtaydi.

Foydalanish (backend venv bilan):
  cd backend && uv run python ../scripts/fake_cameras.py generate
  cd backend && uv run python ../scripts/fake_cameras.py serve --conveyor 2 --press 1
Manzillar: rtsp://127.0.0.1:8654/cam<N>/main va /cam<N>/sub
Kamerani "uzish": echo '[1]' > data/fake/offline.json  (qaytarish: echo '[]' > ...)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fake"
W, H, FPS = 1920, 1080, 25

PRODUCTS = {
    # kod: (nom, w, h)
    "TV55": ("Televizor 55", 380, 230),
    "TV43": ("Televizor 43", 290, 175),  # dizayni bir xil, o'lchami kichik
    "FRG1": ("Muzlatgich", 200, 340),
    "WSH1": ("Kir yuvish mashinasi", 250, 260),
}


@dataclass
class Item:
    code: str
    boxed: bool
    x0: float  # t0 paytidagi chap chet
    t0: float
    w: int
    h: int


def _draw_product(img: np.ndarray, it: Item, x: int, y_bottom: int) -> None:
    w, h = it.w, it.h
    x1, y1, x2, y2 = x, y_bottom - h, x + w, y_bottom
    if it.boxed:
        cv2.rectangle(img, (x1, y1), (x2, y2), (60, 120, 170), -1)  # karton
        cv2.rectangle(img, (x1, y1), (x2, y2), (40, 85, 125), 4)
        cv2.line(img, (x1, y1 + h // 5), (x2, y1 + h // 5), (40, 90, 130), 6)  # skotch
        cv2.rectangle(img, (x1 + w // 8, y1 + h // 3), (x1 + w // 2, y1 + h // 3 + h // 5), (235, 235, 235), -1)
        cv2.putText(img, it.code, (x1 + w // 8 + 6, y1 + h // 3 + h // 7), cv2.FONT_HERSHEY_SIMPLEX,
                    max(0.6, w / 300), (30, 30, 30), 2)
        # tepasida mahsulot belgisi
        cx, cy = x1 + int(w * 0.72), y1 + int(h * 0.55)
        if it.code.startswith("TV"):
            cv2.rectangle(img, (cx - w // 8, cy - h // 10), (cx + w // 8, cy + h // 10), (20, 20, 20), 3)
        elif it.code == "FRG1":
            cv2.rectangle(img, (cx - w // 12, cy - h // 6), (cx + w // 12, cy + h // 6), (20, 20, 20), 3)
        else:
            cv2.circle(img, (cx, cy), min(w, h) // 8, (20, 20, 20), 3)
        return
    if it.code.startswith("TV"):
        cv2.rectangle(img, (x1, y1), (x2, y2 - h // 8), (25, 25, 28), -1)
        m = max(6, w // 40)
        cv2.rectangle(img, (x1 + m, y1 + m), (x2 - m, y2 - h // 8 - m), (110, 70, 40), -1)  # ekran
        cv2.line(img, (x1 + m, y1 + m), (x1 + w // 3, y2 - h // 8 - m), (140, 100, 70), 3)
        cv2.rectangle(img, (x1 + w // 2 - w // 10, y2 - h // 8), (x1 + w // 2 + w // 10, y2), (40, 40, 45), -1)
    elif it.code == "FRG1":
        cv2.rectangle(img, (x1, y1), (x2, y2), (225, 228, 230), -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (150, 150, 155), 3)
        cv2.line(img, (x1, y1 + h // 3), (x2, y1 + h // 3), (150, 150, 155), 3)
        cv2.rectangle(img, (x2 - 26, y1 + 30), (x2 - 16, y1 + h // 3 - 20), (90, 90, 95), -1)
        cv2.rectangle(img, (x2 - 26, y1 + h // 3 + 25), (x2 - 16, y1 + h // 3 + 120), (90, 90, 95), -1)
    else:  # kir yuvish
        cv2.rectangle(img, (x1, y1), (x2, y2), (238, 238, 240), -1)
        cv2.rectangle(img, (x1, y1), (x2, y2), (160, 160, 165), 3)
        cv2.rectangle(img, (x1 + 10, y1 + 10), (x2 - 10, y1 + h // 6), (200, 200, 205), -1)
        cv2.circle(img, (x1 + w // 6, y1 + h // 12 + 5), 9, (60, 60, 200), -1)
        c = (x1 + w // 2, y1 + h // 2 + h // 12)
        cv2.circle(img, c, int(min(w, h) * 0.33), (70, 70, 75), 10)
        cv2.circle(img, c, int(min(w, h) * 0.25), (120, 90, 60), -1)


def conveyor_schedule(seed: int, loop_sec: float) -> list[Item]:
    rnd = random.Random(seed)
    items: list[Item] = []
    t = 1.0
    codes = list(PRODUCTS)
    while t < loop_sec - 14:
        code = rnd.choices(codes, weights=[3, 3, 2, 2])[0]
        boxed = rnd.random() < 0.3
        _, w, h = PRODUCTS[code]
        if boxed:
            w, h = int(w * 1.08), int(h * 1.08)
        items.append(Item(code, boxed, -w - 10, t, w, h))
        # ba'zan bir-biriga tegib keladi (oraliq kichik)
        gap = rnd.uniform(0.0, 0.15) if rnd.random() < 0.12 else rnd.uniform(2.5, 5.5)
        t += (w + 10) / SPEED + gap
    return items


SPEED = 210.0  # px/s
BELT_TOP, BELT_BOTTOM = 470, 860


def render_conveyor(t: float, items: list[Item], bg: np.ndarray) -> np.ndarray:
    img = bg.copy()
    # konveyer lentasi chiziqlari harakatlanadi
    off = int(t * SPEED) % 120
    for x in range(-120 + off, W, 120):
        cv2.line(img, (x, BELT_TOP + 8), (x, BELT_BOTTOM - 8), (78, 78, 82), 3)
    for it in items:
        x = it.x0 + (t - it.t0) * SPEED
        if t < it.t0 or x > W + 20:
            continue
        _draw_product(img, it, int(x), BELT_BOTTOM - 40)
    return img


def conveyor_bg() -> np.ndarray:
    rng = np.random.default_rng(1)
    img = np.full((H, W, 3), (58, 62, 66), np.uint8)
    img += rng.integers(0, 10, (H, W, 1), dtype=np.uint8)
    cv2.rectangle(img, (0, BELT_TOP), (W, BELT_BOTTOM), (52, 52, 55), -1)
    cv2.rectangle(img, (0, BELT_TOP - 14), (W, BELT_TOP), (30, 160, 220), -1)
    cv2.rectangle(img, (0, BELT_BOTTOM), (W, BELT_BOTTOM + 14), (30, 160, 220), -1)
    for x in range(80, W, 260):
        cv2.rectangle(img, (x, BELT_BOTTOM + 14), (x + 24, H), (40, 40, 44), -1)
    cv2.putText(img, "LINIYA-1", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (200, 200, 200), 3)
    return img


def press_bg() -> np.ndarray:
    img = np.full((H, W, 3), (64, 66, 70), np.uint8)
    cv2.rectangle(img, (700, 120), (1220, 200), (70, 75, 85), -1)  # tepa
    cv2.rectangle(img, (700, 120), (780, 900), (70, 75, 85), -1)  # ustunlar
    cv2.rectangle(img, (1140, 120), (1220, 900), (70, 75, 85), -1)
    cv2.rectangle(img, (760, 820), (1160, 900), (90, 95, 105), -1)  # stol
    cv2.putText(img, "PRESS-3", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (200, 200, 200), 3)
    cv2.circle(img, (1600, 300), 30, (40, 40, 40), -1)  # lampa joyi
    return img


PRESS_CYCLE = 3.0
PRESS_RUN = 39.0  # har 60 s dan 39 s ishlaydi (13 to'liq sikl)


def render_press(t: float, bg: np.ndarray) -> np.ndarray:
    img = bg.copy()
    lt = t % 60.0
    phase = (lt % PRESS_CYCLE) / PRESS_CYCLE if lt < PRESS_RUN else 0.0
    # 0..0.27 tushadi, 0.27..0.53 ko'tariladi, qolgani tayanchda
    if phase < 0.27:
        d = phase / 0.27
    elif phase < 0.53:
        d = 1 - (phase - 0.27) / 0.26
    else:
        d = 0.0
    y = int(220 + d * 430)
    cv2.rectangle(img, (800, 200), (1120, 200 + 20), (40, 40, 45), -1)
    cv2.rectangle(img, (930, 200), (990, y), (150, 155, 165), -1)  # shток
    cv2.rectangle(img, (820, y), (1100, y + 150), (30, 120, 230), -1)  # zarbdor
    cv2.rectangle(img, (820, y), (1100, y + 150), (20, 80, 160), 4)
    # miltillovchi lampa (istisno zonasi uchun)
    if int(t * 2) % 2 == 0:
        cv2.circle(img, (1600, 300), 30, (40, 220, 255), -1)
    return img


def _encoder(path_main: Path, path_sub: Path, codec: str) -> subprocess.Popen:
    vcodec = "libx265" if codec == "h265" else "libx264"
    extra = ["-x265-params", "log-level=error"] if codec == "h265" else []
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-filter_complex", "[0:v]split=2[a][b];[b]scale=640:360[s]",
        "-map", "[a]", "-c:v", vcodec, "-preset", "veryfast", "-g", "50", "-bf", "0", "-pix_fmt", "yuv420p",
        "-b:v", "4M", *extra, str(path_main),
        "-map", "[s]", "-c:v", vcodec, "-preset", "veryfast", "-g", "50", "-bf", "0", "-pix_fmt", "yuv420p",
        "-b:v", "600k", *extra, str(path_sub),
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def generate(codec: str = "h264") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    noise_rng = np.random.default_rng(7)
    truth = {}
    for scene, loop in (("conveyor", 75.0), ("press", 60.0)):
        main, sub = OUT / f"{scene}_main_{codec}.mp4", OUT / f"{scene}_sub_{codec}.mp4"
        print(f"Generatsiya: {scene} ({loop:.0f} s) → {main.name}, {sub.name}")
        enc = _encoder(main, sub, codec)
        assert enc.stdin
        if scene == "conveyor":
            bg = conveyor_bg()
            items = conveyor_schedule(42, loop)
            counts: dict[str, int] = {}
            for it in items:
                counts[it.code] = counts.get(it.code, 0) + 1
            truth["conveyor"] = {
                "loop_sec": loop,
                "per_loop": counts,
                "total_per_loop": len(items),
                "boxed": sum(1 for i in items if i.boxed),
                "products": {k: v[0] for k, v in PRODUCTS.items()},
                "direction": "left_to_right",
            }
        else:
            bg = press_bg()
            truth["press"] = {
                "loop_sec": loop,
                "cycle_sec": PRESS_CYCLE,
                "run_sec_per_loop": PRESS_RUN,
                "cycles_per_loop": int(PRESS_RUN // PRESS_CYCLE),
            }
        for f in range(int(loop * FPS)):
            t = f / FPS
            img = render_conveyor(t, items, bg) if scene == "conveyor" else render_press(t, bg)
            # yengil shovqin (haqiqiy kamera kabi)
            n = noise_rng.integers(0, 6, (H // 4, W // 4, 1), dtype=np.uint8)
            img = cv2.add(img, cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)[..., None].repeat(3, 2))
            enc.stdin.write(img.tobytes())
        enc.stdin.close()
        enc.wait()
    (OUT / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2))
    print("Tayyor:", OUT)


# ---------------------------------------------------------------------------
# Minimal RTSP server (faqat sinov uchun): H.264, RTP over TCP (interleaved).
# Barcha kameralar bitta portda: rtsp://127.0.0.1:8654/cam<N>/main | /sub
# "Jonli" vaqt: qayta ulanganda video boshidan emas, joriy joyidan davom etadi.
# Kamerani "uzish" (kabel uzilishi sinovi): data/fake/offline.json → [1, 3]
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
import base64  # noqa: E402
import struct  # noqa: E402

import av  # noqa: E402

RTSP_PORT = int(__import__("os").environ.get("FAKE_RTSP_PORT", "8654"))
OFFLINE_FILE = OUT / "offline.json"


class Media:
    """Fayldan H.264 kirish birliklarini (NAL ro'yxati) xotiraga yuklaydi."""

    def __init__(self, path: Path) -> None:
        c = av.open(str(path))
        vs = c.streams.video[0]
        if vs.codec_context.name != "h264":
            raise SystemExit(f"{path.name}: sinov serveri faqat H.264 ni qo'llaydi")
        extra = bytes(vs.codec_context.extradata or b"")
        self.sps, self.pps = self._parse_avcc(extra)
        self.width, self.height = vs.codec_context.width, vs.codec_context.height
        self.fps = float(vs.average_rate or FPS)
        self.frames: list[tuple[bool, list[bytes]]] = []
        for pkt in c.demux(vs):
            if pkt.size == 0:
                continue
            self.frames.append((bool(pkt.is_keyframe), self._split(bytes(pkt))))
        c.close()
        self.keyframes = [i for i, (k, _) in enumerate(self.frames) if k]

    @staticmethod
    def _parse_avcc(b: bytes) -> tuple[bytes, bytes]:
        n_sps = b[5] & 0x1F
        i = 6
        sps = b""
        for _ in range(n_sps):
            ln = struct.unpack(">H", b[i:i + 2])[0]
            sps = b[i + 2:i + 2 + ln]
            i += 2 + ln
        n_pps = b[i]
        i += 1
        pps = b""
        for _ in range(n_pps):
            ln = struct.unpack(">H", b[i:i + 2])[0]
            pps = b[i + 2:i + 2 + ln]
            i += 2 + ln
        return sps, pps

    @staticmethod
    def _split(data: bytes) -> list[bytes]:
        out, i = [], 0
        while i + 4 <= len(data):
            ln = struct.unpack(">I", data[i:i + 4])[0]
            out.append(data[i + 4:i + 4 + ln])
            i += 4 + ln
        return out

    def sdp(self, host: str) -> str:
        prof = self.sps[1:4].hex()
        sprop = base64.b64encode(self.sps).decode() + "," + base64.b64encode(self.pps).decode()
        return (
            "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=F_CV fake camera\r\nc=IN IP4 0.0.0.0\r\nt=0 0\r\n"
            "m=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n"
            f"a=fmtp:96 packetization-mode=1;profile-level-id={prof};sprop-parameter-sets={sprop}\r\n"
            f"a=framerate:{self.fps:g}\r\na=control:trackID=0\r\n"
        )


def _offline() -> set[int]:
    try:
        return set(json.loads(OFFLINE_FILE.read_text()))
    except Exception:
        return set()


class RtspServer:
    def __init__(self, cams: dict[int, str], codec: str) -> None:
        self.cams = cams  # cam_index -> scene
        self.media: dict[tuple[str, str], Media] = {}
        for scene in set(cams.values()):
            for kind in ("main", "sub"):
                self.media[(scene, kind)] = Media(OUT / f"{scene}_{kind}_{codec}.mp4")
        self.t0 = time.monotonic()

    def resolve(self, url: str) -> tuple[int, Media] | None:
        path = url.split("://", 1)[-1].split("/", 1)[-1].split("?")[0].rstrip("/")
        parts = [p for p in path.split("/") if p and not p.startswith("trackID")]
        if len(parts) < 2 or not parts[0].startswith("cam"):
            return None
        try:
            idx = int(parts[0][3:])
        except ValueError:
            return None
        scene = self.cams.get(idx)
        if scene is None or parts[1] not in ("main", "sub"):
            return None
        return idx, self.media[(scene, parts[1])]

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        sender: asyncio.Task | None = None
        session = str(random.randint(10**7, 10**8))
        target: tuple[int, Media] | None = None
        try:
            while True:
                first = await reader.readexactly(1)
                if first == b"$":  # RTCP (interleaved) — e'tiborsiz
                    hdr = await reader.readexactly(3)
                    await reader.readexactly(struct.unpack(">H", hdr[1:])[0])
                    continue
                line = first + await reader.readuntil(b"\r\n")
                headers = {}
                while True:
                    h = (await reader.readuntil(b"\r\n")).decode().strip()
                    if not h:
                        break
                    k, _, v = h.partition(":")
                    headers[k.strip().lower()] = v.strip()
                if int(headers.get("content-length", 0)):
                    await reader.readexactly(int(headers["content-length"]))
                method, url, _ = line.decode().split(" ", 2)
                cseq = headers.get("cseq", "0")
                res = self.resolve(url)
                if res is None or res[0] in _offline():
                    self._reply(writer, cseq, "404 Not Found")
                    continue
                target = res
                media = res[1]
                if method == "OPTIONS":
                    self._reply(writer, cseq, extra="Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN, GET_PARAMETER")
                elif method == "DESCRIBE":
                    body = media.sdp("127.0.0.1").encode()
                    self._reply(writer, cseq, extra=f"Content-Base: {url.rstrip('/')}/\r\nContent-Type: application/sdp",
                                body=body)
                elif method == "SETUP":
                    tr = headers.get("transport", "")
                    if "TCP" not in tr.upper():
                        self._reply(writer, cseq, "461 Unsupported Transport")
                        continue
                    self._reply(writer, cseq, extra=f"Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\nSession: {session};timeout=60")
                elif method == "PLAY":
                    self._reply(writer, cseq, extra=f"Session: {session}\r\nRange: npt=0.000-")
                    if sender is None:
                        sender = asyncio.create_task(self._send(writer, media, res[0]))
                elif method == "TEARDOWN":
                    self._reply(writer, cseq, extra=f"Session: {session}")
                    break
                else:  # GET_PARAMETER / SET_PARAMETER — keepalive
                    self._reply(writer, cseq, extra=f"Session: {session}")
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, asyncio.LimitOverrunError, ValueError):
            pass
        finally:
            if sender:
                sender.cancel()
            writer.close()
            _ = target

    @staticmethod
    def _reply(w: asyncio.StreamWriter, cseq: str, status: str = "200 OK", extra: str = "", body: bytes = b"") -> None:
        msg = f"RTSP/1.0 {status}\r\nCSeq: {cseq}\r\n"
        if extra:
            msg += extra + "\r\n"
        if body:
            msg += f"Content-Length: {len(body)}\r\n"
        w.write(msg.encode() + b"\r\n" + body)

    async def _send(self, w: asyncio.StreamWriter, m: Media, cam_idx: int) -> None:
        n = len(m.frames)
        dt = 1.0 / m.fps
        # joriy "jonli" joydan oldingi kalit kadrdan boshlash
        pos = int((time.monotonic() - self.t0) / dt) % n
        start = max([k for k in m.keyframes if k <= pos] or [0])
        seq = random.randint(0, 65535)
        ssrc = random.randint(0, 2**32 - 1)
        ts = random.randint(0, 2**31)
        i = start
        next_t = time.monotonic()
        try:
            while True:
                if cam_idx in _offline():
                    w.close()
                    return
                key, nals = m.frames[i]
                if key:
                    nals = [m.sps, m.pps, *nals]
                for j, nal in enumerate(nals):
                    last = j == len(nals) - 1
                    for payload, mark in self._packetize(nal, last):
                        hdr = struct.pack(">BBHII", 0x80, (0x80 if mark else 0) | 96, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
                        pkt = hdr + payload
                        w.write(b"$\x00" + struct.pack(">H", len(pkt)) + pkt)
                        seq += 1
                await w.drain()
                ts += int(90000 * dt)
                i = (i + 1) % n
                next_t += dt
                delay = next_t - time.monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                elif delay < -2:
                    next_t = time.monotonic()
        except (ConnectionError, asyncio.CancelledError):
            return

    @staticmethod
    def _packetize(nal: bytes, last: bool, mtu: int = 1400):
        if len(nal) <= mtu:
            yield nal, last
            return
        hdr = nal[0]
        fu_ind = (hdr & 0xE0) | 28
        typ = hdr & 0x1F
        data = nal[1:]
        pos = 0
        while pos < len(data):
            chunk = data[pos:pos + mtu]
            s = 0x80 if pos == 0 else 0
            e = 0x40 if pos + mtu >= len(data) else 0
            yield bytes([fu_ind, s | e | typ]) + chunk, (last and bool(e))
            pos += mtu


def serve(conveyor: int, press: int, codec: str) -> None:
    cams: dict[int, str] = {}
    idx = 1
    for scene, n in (("conveyor", conveyor), ("press", press)):
        for _ in range(n):
            cams[idx] = scene
            idx += 1
    srv = RtspServer(cams, codec)
    print(f"Soxta kameralar (rtsp://127.0.0.1:{RTSP_PORT}):", flush=True)
    for i, scene in cams.items():
        print(f"  cam{i} ({scene}): rtsp://127.0.0.1:{RTSP_PORT}/cam{i}/main  |  /cam{i}/sub", flush=True)

    async def run() -> None:
        server = await asyncio.start_server(srv.handle, "0.0.0.0", RTSP_PORT, limit=1 << 16)
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        loop.add_signal_handler(signal.SIGTERM, stop.set)
        loop.add_signal_handler(signal.SIGINT, stop.set)
        async with server:
            await stop.wait()

    asyncio.run(run())


def main() -> None:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("generate")
    g.add_argument("--codec", choices=["h264", "h265"], default="h264")
    s = sp.add_parser("serve")
    s.add_argument("--conveyor", type=int, default=2)
    s.add_argument("--press", type=int, default=1)
    s.add_argument("--codec", choices=["h264", "h265"], default="h264")
    a = ap.parse_args()
    if a.cmd == "generate":
        generate(a.codec)
    else:
        serve(a.conveyor, a.press, a.codec)


if __name__ == "__main__":
    _ = math
    main()
