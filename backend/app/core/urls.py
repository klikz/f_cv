"""RTSP manzillari bilan ishlash: parolni yashirish, login/parol qo'shish."""

from urllib.parse import quote, unquote, urlsplit, urlunsplit


def mask_url(url: str | None) -> str | None:
    """`rtsp://admin:secret@host/...` → `rtsp://admin:•••@host/...`"""
    if not url:
        return url
    try:
        p = urlsplit(url)
    except ValueError:
        return url
    if p.password is None:
        return url
    user = p.username or ""
    host = p.hostname or ""
    if p.port:
        host = f"{host}:{p.port}"
    return urlunsplit((p.scheme, f"{user}:•••@{host}", p.path, p.query, p.fragment))


def with_credentials(url: str, username: str | None, password: str | None) -> str:
    """Manzilda login bo'lmasa — qo'shadi (ONVIF GetStreamUri ko'pincha loginsiz qaytaradi)."""
    if not username:
        return url
    p = urlsplit(url)
    if p.username:
        return url
    host = p.hostname or ""
    if p.port:
        host = f"{host}:{p.port}"
    cred = quote(username, safe="")
    if password:
        cred += ":" + quote(password, safe="")
    return urlunsplit((p.scheme, f"{cred}@{host}", p.path, p.query, p.fragment))


def host_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlsplit(url).hostname
    except ValueError:
        return None


def credentials_of(url: str) -> tuple[str | None, str | None]:
    p = urlsplit(url)
    return (unquote(p.username) if p.username else None, unquote(p.password) if p.password else None)
