"""Avtomatik ishga tushish (Ubuntu 26.04, systemd + GNOME/GDM).

- services  — kompyuter yonganda F_CV servislari: `systemctl is-enabled fcv.target`; o'zgartirish root yordamchi
              skript orqali (`sudo -n /usr/local/sbin/fcv-autostart`, deploy/install.sh o'rnatadi).
- kiosk     — foydalanuvchi tizimga kirganda brauzerda UI ochilishi: ~/.config/autostart/fcv-kiosk.desktop
              (root kerak emas).
- autologin — GDM avtomatik kirish (/etc/gdm3/custom.conf), kiosk login oynasisiz ochilishi uchun; yordamchi orqali.
"""

from __future__ import annotations

import asyncio
import getpass
import os
import re
import shlex
import shutil
from pathlib import Path

from app.core.config import get_settings

HELPER = "/usr/local/sbin/fcv-autostart"
GDM_CONF = Path("/etc/gdm3/custom.conf")
DESKTOP_NAME = "fcv-kiosk.desktop"
# Ubuntu: snap paketlar /snap/bin da — systemd servis PATH ida bo'lmasligi mumkin
BROWSERS: list[tuple[str, list[str]]] = [
    ("google-chrome", ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]),
    ("chromium", ["/snap/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser"]),
    ("firefox", ["/snap/bin/firefox", "/usr/bin/firefox"]),
]


class AutostartError(RuntimeError):
    pass


async def _run(*args: str, timeout: float = 20) -> tuple[int, str]:
    try:
        p = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
    except FileNotFoundError:
        return 127, f"{args[0]} topilmadi"
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except TimeoutError:
        p.kill()
        return 124, "vaqt tugadi"
    return p.returncode or 0, out.decode(errors="replace").strip()


def _config_home() -> Path:
    x = os.environ.get("XDG_CONFIG_HOME")
    return Path(x) if x else Path.home() / ".config"


def desktop_path() -> Path:
    return _config_home() / "autostart" / DESKTOP_NAME


def ui_url() -> str:
    return f"http://localhost:{get_settings().api_port}/"


def available_browsers() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, paths in BROWSERS:
        found = next((p for p in paths if os.access(p, os.X_OK)), None) or shutil.which(name)
        if found:
            out[name] = found
    return out


def _browser_cmd(name: str, path: str, url: str, fullscreen: bool) -> list[str]:
    if name == "firefox":
        return [path, "--kiosk", url] if fullscreen else [path, "--new-window", url]
    flags = ["--noerrdialogs", "--disable-session-crashed-bubble", "--no-first-run"]
    return [path, *flags, "--kiosk", url] if fullscreen else [path, *flags, f"--app={url}"]


def _read_desktop() -> dict | None:
    p = desktop_path()
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    if re.search(r"^Hidden\s*=\s*true", text, re.M | re.I) or re.search(
        r"^X-GNOME-Autostart-enabled\s*=\s*false", text, re.M | re.I
    ):
        return None
    browser = next((m for m in re.findall(r"^X-FCV-Browser=(\S+)", text, re.M)), None)
    return {"browser": browser, "fullscreen": "--kiosk" in text}


def write_desktop(browser: str, fullscreen: bool) -> None:
    browsers = available_browsers()
    if browser not in browsers:
        raise AutostartError(f"Brauzer topilmadi: {browser}")
    url = ui_url()
    port = get_settings().api_port
    cmd = shlex.join(_browser_cmd(browser, browsers[browser], url, fullscreen))
    # API tayyor bo'lishini kutish (curl o'rnatilmagan bo'lishi mumkin — bash /dev/tcp)
    script = (
        f"for i in $(seq 1 120); do (exec 3<>/dev/tcp/127.0.0.1/{port}) 2>/dev/null && break; sleep 1; done; exec {cmd}"
    )
    text = "\n".join(
        [
            "[Desktop Entry]",
            "# F_CV: Umumiy sozlamalar → Avtomatik ishga tushish orqali yaratilgan",
            "Type=Application",
            "Name=F_CV",
            "Comment=F_CV kuzatuv paneli",
            f"Exec=bash -c {shlex.quote(script)}",
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "X-GNOME-Autostart-Delay=5",
            f"X-FCV-Browser={browser}",
            "",
        ]
    )
    from app.core.files import atomic_write_bytes

    atomic_write_bytes(desktop_path(), text.encode())


def remove_desktop() -> None:
    desktop_path().unlink(missing_ok=True)


def _gdm_autologin() -> dict:
    try:
        text = GDM_CONF.read_text(encoding="utf-8")
    except OSError:
        return {"supported": False, "enabled": False, "user": None}
    sect = re.search(r"^\[daemon\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S | re.I)
    body = sect.group(1) if sect else ""
    en = re.search(r"^\s*AutomaticLoginEnable\s*=\s*(\S+)", body, re.M)
    usr = re.search(r"^\s*AutomaticLogin\s*=\s*(\S+)", body, re.M)
    enabled = bool(en and en.group(1).lower() in ("true", "1", "yes"))
    return {"supported": True, "enabled": enabled, "user": usr.group(1) if usr else None}


async def helper_ready() -> bool:
    if not os.access(HELPER, os.X_OK):
        return False
    rc, _ = await _run("sudo", "-n", "-l", HELPER, timeout=5)
    return rc == 0


async def status() -> dict:
    rc, out = await _run("systemctl", "is-enabled", "fcv.target", timeout=5)
    state = out.splitlines()[-1] if out else "unknown"
    installed = state not in ("not-found", "unknown") and rc != 127
    rc_a, out_a = await _run("systemctl", "is-active", "fcv.target", timeout=5)
    gdm = _gdm_autologin()
    me = getpass.getuser()
    kiosk = _read_desktop()
    return {
        "user": me,
        "helper": await helper_ready(),
        "services": {
            "installed": installed,
            "enabled": state in ("enabled", "enabled-runtime", "static", "alias"),
            "state": state,
            "active": out_a.strip() == "active",
        },
        "kiosk": {
            "enabled": kiosk is not None,
            "browser": (kiosk or {}).get("browser"),
            "fullscreen": (kiosk or {}).get("fullscreen", True),
            "path": str(desktop_path()),
            "url": ui_url(),
            "browsers": list(available_browsers()),
        },
        "autologin": {
            **gdm,
            "enabled": gdm["enabled"] and gdm["user"] == me,
            "other_user": gdm["enabled"] and gdm["user"] not in (None, me),
        },
    }


async def run_helper(what: str, on: bool) -> None:
    if not await helper_ready():
        raise AutostartError(
            "Tizim sozlamasini o'zgartirish uchun ruxsat yo'q: serverda bir marta `sudo deploy/install.sh` ni ishga tushiring"
        )
    rc, out = await _run("sudo", "-n", HELPER, what, "on" if on else "off", timeout=60)
    if rc != 0:
        raise AutostartError(out or f"fcv-autostart xatosi ({rc})")
