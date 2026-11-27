"""Yagona kirish nuqtasi: `fcv <process> [argumentlar]`."""

import sys

USAGE = """Foydalanish: fcv <process> [argumentlar]

Processlar:
  api                 FastAPI REST + WebSocket
  video-service       video dekod
  inference-server    GPU inference
  camera-logic        kamera logikasi (--camera-id N)
  trainer             train navbati
  telegram-service    Telegram bot
"""


def _api() -> None:
    import uvicorn

    from app.core.config import get_settings
    from app.core.logging import setup_logging

    s = get_settings()
    s.ensure_data_dirs()
    setup_logging("api")
    uvicorn.run("app.main:app", host=s.api_host, port=s.api_port, log_config=None, proxy_headers=False)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(USAGE)
        sys.exit(0 if len(sys.argv) >= 2 else 1)
    name, rest = sys.argv[1], sys.argv[2:]
    if name == "api":
        _api()
    elif name == "video-service":
        from vision.video.main import main as m

        m()
    elif name == "inference-server":
        from vision.inference.main import main as m

        m()
    elif name == "camera-logic":
        from vision.logic.main import main as m

        m(rest)
    elif name == "trainer":
        from training.main import main as m

        m()
    elif name == "telegram-service":
        from telegram.main import main as m

        m()
    else:
        print(f"Noma'lum process: {name}\n\n{USAGE}")
        sys.exit(2)


if __name__ == "__main__":
    main()
