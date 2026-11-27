"""UI sinovi: headless Chrome (CDP) — sahifani ochish, kutish, amallar, skrinshot.

  uv run python ../scripts/ui_shot.py URL OUT.png [--wait 4] [--size 1600x900] [--js "..."] [--dark|--light]
Bir nechta qadam: --steps steps.json  ([{"url":..}, {"wait":2}, {"js":"..."}, {"click":"css"}, {"key":"Enter"}, {"shot":"a.png"}])
"""

import argparse
import asyncio
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

import websockets

PORT = 9333


def start_chrome(w: int, h: int) -> subprocess.Popen:
    prof = tempfile.mkdtemp(prefix="fcv-chrome-")
    return subprocess.Popen(
        ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", f"--remote-debugging-port={PORT}",
         f"--user-data-dir={prof}", f"--window-size={w},{h}", "--hide-scrollbars", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--wait", type=float, default=4)
    ap.add_argument("--size", default="1600x900")
    ap.add_argument("--js", default=None)
    ap.add_argument("--light", action="store_true")
    ap.add_argument("--steps", default=None)
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))
    chrome = start_chrome(w, h)
    try:
        for _ in range(50):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        async with websockets.connect(ws_url, max_size=None) as ws:
            mid = 0
            logs: list[str] = []

            async def cmd(method: str, params: dict | None = None):
                nonlocal mid
                mid += 1
                my = mid
                await ws.send(json.dumps({"id": my, "method": method, "params": params or {}}))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("method") == "Runtime.consoleAPICalled":
                        args = " ".join(str(x.get("value", x.get("description", ""))) for x in m["params"]["args"])
                        logs.append(f"[{m['params']['type']}] {args}")
                    elif m.get("method") == "Runtime.exceptionThrown":
                        logs.append("[exception] " + json.dumps(m["params"]["exceptionDetails"].get("exception", {}).get("description", ""))[:400])
                    if m.get("id") == my:
                        return m.get("result", {})

            await cmd("Runtime.enable")
            await cmd("Page.enable")
            await cmd("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
            steps = json.load(open(a.steps)) if a.steps else [{"url": a.url}, {"wait": a.wait}] + ([{"js": a.js}, {"wait": 1}] if a.js else []) + [{"shot": a.out}]
            first_url = True
            for st in steps:
                if "url" in st:
                    if first_url and a.light:
                        await cmd("Page.navigate", {"url": st["url"]})
                        await asyncio.sleep(0.5)
                        await cmd("Runtime.evaluate", {"expression": "localStorage.setItem('fcv.theme', JSON.stringify('light'))"})
                    first_url = False
                    await cmd("Page.navigate", {"url": st["url"]})
                elif "init" in st:
                    await cmd("Page.addScriptToEvaluateOnNewDocument", {"source": st["init"]})
                elif "wait" in st:
                    end = time.time() + st["wait"]
                    while time.time() < end:
                        await cmd("Runtime.evaluate", {"expression": "1"})
                        await asyncio.sleep(0.2)
                elif "js" in st:
                    r = await cmd("Runtime.evaluate", {"expression": st["js"], "awaitPromise": True, "returnByValue": True})
                    val = r.get("result", {}).get("value")
                    if val is not None:
                        print("JS:", json.dumps(val, ensure_ascii=False)[:2000])
                elif "click" in st:
                    r = await cmd("Runtime.evaluate", {"expression": f"(() => {{ const e = document.querySelector({json.dumps(st['click'])}); if (!e) return null; const b = e.getBoundingClientRect(); return [b.x + b.width/2, b.y + b.height/2] }})()", "returnByValue": True})
                    xy = r.get("result", {}).get("value")
                    if not xy:
                        print("CLICK: topilmadi", st["click"])
                        continue
                    xy = [xy[0] + st.get("dx", 0), xy[1] + st.get("dy", 0)]
                    for t in ("mousePressed", "mouseReleased"):
                        await cmd("Input.dispatchMouseEvent", {"type": t, "x": xy[0], "y": xy[1], "button": "left", "clickCount": st.get("count", 1)})
                elif "clickxy" in st:
                    x, y = st["clickxy"]
                    for t in ("mousePressed", "mouseReleased"):
                        await cmd("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": st.get("count", 1)})
                    await asyncio.sleep(0.15)
                elif "key" in st:
                    k = st["key"]
                    await cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": k, "code": st.get("code", k), "windowsVirtualKeyCode": st.get("vk", 0), "modifiers": st.get("mod", 0)})
                    await cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": k, "code": st.get("code", k), "modifiers": st.get("mod", 0)})
                elif "type" in st:
                    await cmd("Input.insertText", {"text": st["type"]})
                elif "shot" in st:
                    r = await cmd("Page.captureScreenshot", {"format": "png"})
                    with open(st["shot"], "wb") as f:
                        f.write(base64.b64decode(r["data"]))
                    print("SHOT:", st["shot"])
            errs = [l for l in logs if l.startswith(("[error]", "[exception]"))]
            if errs:
                print("KONSOL XATOLARI:")
                for e in errs[:15]:
                    print("  ", e[:400])
    finally:
        chrome.terminate()


if __name__ == "__main__":
    asyncio.run(main())
