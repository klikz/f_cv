"""Ultralytics uchun oflayn muhit (PLAN.md 1.12): internetga murojaat va avto-o'rnatish o'chiriladi.

Ultralytics sozlamalari foydalanuvchining umumiy ~/.config papkasiga emas, loyiha ichiga yoziladi.
"""

import os
from pathlib import Path

from app.core.config import get_settings


def base_weights_dir() -> Path:
    return get_settings().data_subdir("models") / "base"


def setup_ultralytics_env() -> dict[str, str]:
    s = get_settings()
    cfg = s.data_subdir("models") / "ultralytics"
    cfg.mkdir(parents=True, exist_ok=True)
    env = {
        "YOLO_CONFIG_DIR": str(cfg),
        "YOLO_OFFLINE": "1",
        "YOLO_AUTOINSTALL": "false",
        "YOLO_VERBOSE": "true",
        "HUB_API_KEY": "",
        "WANDB_DISABLED": "true",
        "COMET_MODE": "disabled",
    }
    os.environ.update(env)
    # ultralytics shriftni (Arial.ttf) internetdan yuklamasligi uchun — o'rnatishda base/ ga qo'yilgan nusxa
    font_dst = cfg / "Ultralytics" / "Arial.ttf"
    font_src = base_weights_dir() / "Arial.ttf"
    if not font_dst.exists() and font_src.exists():
        font_dst.parent.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy(font_src, font_dst)
    try:
        from ultralytics import settings as us

        us.update(
            {
                "sync": False,
                "weights_dir": str(base_weights_dir()),
                "runs_dir": str(s.data_subdir("models") / "runs"),
                "datasets_dir": str(s.data_subdir("datasets")),
                "hub": False,
                "wandb": False,
                "comet": False,
                "mlflow": False,
                "clearml": False,
                "neptune": False,
                "dvc": False,
                "tensorboard": False,
            }
        )
    except Exception:
        pass
    return env


def versions() -> dict[str, str]:
    """Engine yoniga yoziladigan versiyalar (drayver/TensorRT o'zgarsa qayta qurish uchun)."""
    out = {"trt": "", "driver": "", "cuda": ""}
    try:
        import tensorrt

        out["trt"] = tensorrt.__version__
    except Exception:
        pass
    try:
        import pynvml

        pynvml.nvmlInit()
        d = pynvml.nvmlSystemGetDriverVersion()
        out["driver"] = d.decode() if isinstance(d, bytes) else d
        out["gpu"] = pynvml.nvmlDeviceGetName(pynvml.nvmlDeviceGetHandleByIndex(0))
        if isinstance(out["gpu"], bytes):
            out["gpu"] = out["gpu"].decode()
        pynvml.nvmlShutdown()
    except Exception:
        pass
    return out
