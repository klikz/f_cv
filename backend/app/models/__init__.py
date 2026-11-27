"""Barcha modellar shu yerda import qilinadi (Alembic autogenerate uchun)."""

from app.models.cameras import Camera, CameraStream, CoverageGap
from app.models.catalog import Annotation, DatasetImage, ModelVersion, Product, TrainingJob, TrainingMetric
from app.models.counting import CountEvent, CountingConfigProduct, ManualCount
from app.models.equipment import CycleEvent, EquipmentInterval, EquipmentMinuteStat
from app.models.settings import Setting
from app.models.shifts import Shift
from app.models.system import SystemEvent
from app.models.tasks import CameraTask, CountingConfig, EquipmentConfig
from app.models.telegram import NotificationOutbox, TelegramChat, TelegramSubscription

__all__ = [
    "Annotation",
    "Camera",
    "CameraStream",
    "CameraTask",
    "CountEvent",
    "CountingConfig",
    "CountingConfigProduct",
    "CoverageGap",
    "CycleEvent",
    "DatasetImage",
    "EquipmentConfig",
    "EquipmentInterval",
    "EquipmentMinuteStat",
    "ManualCount",
    "ModelVersion",
    "NotificationOutbox",
    "Product",
    "Setting",
    "Shift",
    "SystemEvent",
    "TelegramChat",
    "TelegramSubscription",
    "TrainingJob",
    "TrainingMetric",
]
