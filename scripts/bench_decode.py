"""Dekod benchmark (1.3): VAAPI / NVDEC / CPU — 15 sub + N main.

  cd backend && uv run python ../scripts/bench_decode.py --backends cpu nvdec --duration 60
Soxta kameralar kerak: FAKE_CONVEYOR=15 FAKE_PRESS=0 scripts/svc.sh restart fake
"""

import argparse
import json
import os
import threading
import time

import psutil
import pynvml

from vision.video.decoders import open_decoder

URL = "rtsp://127.0.0.1:8654/cam{}/{}"


def run(backend: str, n_sub: int, n_main: int, duration: float) -> dict:
    counts: dict[str, int] = {}
    errors: list[str] = []
    stop = threading.Event()

    def worker(i: int, kind: str) -> None:
        key = f"{kind}{i}"
        counts[key] = 0
        try:
            d = open_decoder(URL.format(i, kind), backend, 10.0)
            for _ in d.frames():
                counts[key] += 1
                if stop.is_set():
                    break
            d.close()
        except Exception as e:
            errors.append(f"{key}: {e}")

    threads = [threading.Thread(target=worker, args=(i, "sub"), daemon=True) for i in range(1, n_sub + 1)]
    threads += [threading.Thread(target=worker, args=(i, "main"), daemon=True) for i in range(1, n_main + 1)]
    proc = psutil.Process(os.getpid())
    pynvml.nvmlInit()
    h = pynvml.nvmlDeviceGetHandleByIndex(0)
    mem0 = pynvml.nvmlDeviceGetMemoryInfo(h).used
    for t in threads:
        t.start()
    time.sleep(5)  # ulanish va isinish
    base = dict(counts)
    proc.cpu_percent(None)
    gpu_samples, mem_samples, dec_samples = [], [], []
    t0 = time.time()
    while time.time() - t0 < duration:
        time.sleep(1)
        gpu_samples.append(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
        dec_samples.append(pynvml.nvmlDeviceGetDecoderUtilization(h)[0])
        mem_samples.append(pynvml.nvmlDeviceGetMemoryInfo(h).used)
    cpu = proc.cpu_percent(None)
    el = time.time() - t0
    stop.set()
    fps = {k: (counts[k] - base.get(k, 0)) / el for k in counts}
    for t in threads:
        t.join(5)
    pynvml.nvmlShutdown()
    expected = 10.0
    worst = min(fps.values()) if fps else 0
    avg = sum(fps.values()) / len(fps) if fps else 0
    return {
        "backend": backend, "sub": n_sub, "main": n_main,
        "cpu_pct": round(cpu, 1), "cpu_cores": round(cpu / 100, 2),
        "gpu_pct": round(sum(gpu_samples) / len(gpu_samples), 1),
        "nvdec_pct": round(sum(dec_samples) / len(dec_samples), 1),
        "vram_mb": round((max(mem_samples) - mem0) / 2**20),
        "avg_fps": round(avg, 2), "min_fps": round(worst, 2),
        "drop_pct": round(max(0.0, (expected - avg) / expected * 100), 1),
        "errors": errors[:3],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", nargs="+", default=["cpu", "nvdec"])
    ap.add_argument("--duration", type=float, default=60)
    ap.add_argument("--scenarios", default="15:0,15:5,15:10,15:15")
    ap.add_argument("--out", default="../data/logs/bench_decode.json")
    a = ap.parse_args()
    results = []
    for b in a.backends:
        for sc in a.scenarios.split(","):
            s, m = map(int, sc.split(":"))
            r = run(b, s, m, a.duration)
            print(json.dumps(r, ensure_ascii=False), flush=True)
            results.append(r)
            time.sleep(3)
    with open(a.out, "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
