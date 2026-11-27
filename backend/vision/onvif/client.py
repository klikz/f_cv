"""ONVIF: tarmoqdan qidirish (WS-Discovery), qurilma ma'lumoti, profillar va RTSP manzillari.

ONVIF faqat sozlashni osonlashtiradi — natija baribir RTSP manzillari sifatida saqlanadi.
Kamera soati server soatidan farq qilsa, `adjust_time=True` bilan WS-Security vaqti moslanadi
(kamera vaqti hisobotlarda ishlatilmaydi).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import asdict, dataclass, field
from urllib.parse import unquote, urlsplit

from app.core.urls import with_credentials

log = logging.getLogger(__name__)


@dataclass
class DiscoveredDevice:
    host: str
    port: int
    xaddr: str
    manufacturer: str | None = None
    model: str | None = None
    name: str | None = None


@dataclass
class OnvifProfile:
    token: str
    name: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    codec: str | None = None
    rtsp_url: str | None = None


@dataclass
class OnvifDeviceInfo:
    manufacturer: str | None
    model: str | None
    serial: str | None
    firmware: str | None
    profiles: list[OnvifProfile] = field(default_factory=list)
    suggested_main: str | None = None
    suggested_sub: str | None = None
    time_offset_sec: float | None = None

    def as_dict(self) -> dict:
        return asdict(self)


class OnvifError(Exception):
    pass


def _scope_value(scopes: list[str], key: str) -> str | None:
    for s in scopes:
        m = re.search(rf"onvif://www\.onvif\.org/{key}/(.+)$", s)
        if m:
            return unquote(m.group(1)).replace("_", " ")
    return None


def _discover_sync(timeout: float) -> list[DiscoveredDevice]:
    from wsdiscovery import QName
    from wsdiscovery.discovery import ThreadedWSDiscovery

    wsd = ThreadedWSDiscovery()
    wsd.start()
    try:
        nvt = QName("http://www.onvif.org/ver10/network/wsdl", "NetworkVideoTransmitter")
        services = wsd.searchServices(types=[nvt], timeout=timeout)
    finally:
        wsd.stop()
    out: dict[str, DiscoveredDevice] = {}
    for svc in services:
        xaddrs = svc.getXAddrs() or []
        scopes = [str(s.getValue() if hasattr(s, "getValue") else s) for s in (svc.getScopes() or [])]
        for xa in xaddrs:
            u = urlsplit(xa)
            if not u.hostname or u.hostname.startswith("169.254") or ":" in (u.hostname or ""):
                continue
            port = u.port or 80
            out.setdefault(
                u.hostname,
                DiscoveredDevice(
                    host=u.hostname,
                    port=port,
                    xaddr=xa,
                    manufacturer=_scope_value(scopes, "mfr")
                    or _scope_value(scopes, "manufacturer")
                    or _scope_value(scopes, "name"),
                    model=_scope_value(scopes, "hardware"),
                    name=_scope_value(scopes, "name"),
                ),
            )
    return sorted(out.values(), key=lambda d: tuple(int(p) if p.isdigit() else 0 for p in d.host.split(".")))


async def discover(timeout: float = 3.0) -> list[DiscoveredDevice]:
    return await asyncio.to_thread(_discover_sync, timeout)


def _humanize(e: BaseException) -> str:
    s = f"{e.__class__.__name__}: {e}".lower()
    if "not authorized" in s or "unauthorized" in s or "401" in s or "sender not authorized" in s:
        return "ONVIF: login yoki parol xato"
    if "connect" in s and ("refused" in s or "cannot connect" in s):
        return "ONVIF ga ulanib bo'lmadi: port xato yoki ONVIF o'chirilgan"
    if "timeout" in s or "timed out" in s:
        return "ONVIF javob bermadi (vaqt tugadi): IP va portni tekshiring"
    if "time" in s and "invalid" in s:
        return "ONVIF: kamera soati juda farq qiladi"
    return f"ONVIF xatosi: {str(e)[:200]}"


def suggest_main_sub(profiles: list[OnvifProfile]) -> tuple[str | None, str | None]:
    """Eng katta o'lcham — main, keyingi kichigi — sub."""
    ps = [p for p in profiles if p.rtsp_url]
    if not ps:
        return None, None
    ps.sort(key=lambda p: (p.width or 0) * (p.height or 0), reverse=True)
    main = ps[0]
    sub = next((p for p in ps[1:] if (p.width or 0) * (p.height or 0) < (main.width or 0) * (main.height or 0)), None)
    return main.token, (sub.token if sub else None)


async def read_device(host: str, port: int, username: str, password: str, timeout: float = 15.0) -> OnvifDeviceInfo:
    from onvif import ONVIFCamera

    cam = ONVIFCamera(host, port, username, password, adjust_time=True)
    try:
        async with asyncio.timeout(timeout):
            await cam.update_xaddrs()
            dev = await cam.create_devicemgmt_service()
            offset = None
            try:
                dt = await dev.GetSystemDateAndTime()
                u = dt.UTCDateTime
                from datetime import UTC, datetime

                cam_time = datetime(
                    u.Date.Year, u.Date.Month, u.Date.Day, u.Time.Hour, u.Time.Minute, u.Time.Second, tzinfo=UTC
                )
                offset = round((cam_time - datetime.now(UTC)).total_seconds(), 1)
            except Exception:
                pass
            info = await dev.GetDeviceInformation()
            media = await cam.create_media_service()
            profiles_raw = await media.GetProfiles()
            profiles: list[OnvifProfile] = []
            for p in profiles_raw:
                vec = getattr(p, "VideoEncoderConfiguration", None)
                w = h = None
                fps = None
                codec = None
                if vec is not None:
                    res = getattr(vec, "Resolution", None)
                    if res is not None:
                        w, h = res.Width, res.Height
                    rc = getattr(vec, "RateControl", None)
                    if rc is not None:
                        fps = getattr(rc, "FrameRateLimit", None)
                    codec = getattr(vec, "Encoding", None)
                uri = None
                try:
                    r = await media.GetStreamUri(
                        {
                            "StreamSetup": {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}},
                            "ProfileToken": p.token,
                        }
                    )
                    uri = with_credentials(r.Uri, username, password)
                except Exception as e:
                    log.warning("GetStreamUri %s: %s", p.token, e)
                profiles.append(
                    OnvifProfile(p.token, getattr(p, "Name", p.token), w, h, fps, str(codec) if codec else None, uri)
                )
            main, sub = suggest_main_sub(profiles)
            return OnvifDeviceInfo(
                manufacturer=getattr(info, "Manufacturer", None),
                model=getattr(info, "Model", None),
                serial=getattr(info, "SerialNumber", None),
                firmware=getattr(info, "FirmwareVersion", None),
                profiles=profiles,
                suggested_main=main,
                suggested_sub=sub,
                time_offset_sec=offset,
            )
    except TimeoutError as e:
        raise OnvifError("ONVIF javob bermadi (vaqt tugadi): IP va portni tekshiring") from e
    except OnvifError:
        raise
    except Exception as e:
        raise OnvifError(_humanize(e)) from e
    finally:
        try:
            await cam.close()
        except Exception:
            pass
