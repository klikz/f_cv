from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Point = tuple[float, float]
TaskType = Literal["counting", "equipment"]


def _poly(v: list[Point] | None, name: str) -> list[Point] | None:
    if v is None:
        return None
    if len(v) < 3:
        raise ValueError(f"{name}: kamida 3 nuqta kerak")
    for x, y in v:
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError(f"{name}: nuqtalar kadr ichida bo'lishi kerak")
    return [(round(x, 5), round(y, 5)) for x, y in v]


class TaskState(BaseModel):
    enabled: bool
    configured: bool
    issues: list[str] = []


class TasksOut(BaseModel):
    camera_id: int
    analysis_stream: Literal["main", "sub"]
    has_sub: bool
    stream_sizes: dict[str, list[int] | None]
    tasks: dict[str, TaskState]


class TaskToggle(BaseModel):
    enabled: bool


class AnalysisStreamIn(BaseModel):
    stream: Literal["main", "sub"]
    keep_shapes: bool = False


class CountingConfigIO(BaseModel):
    stream: Literal["main", "sub"] = "main"
    roi_polygon: list[Point] | None = None
    line: list[Point] | None = None
    direction: Literal["a_to_b", "b_to_a", "both"] = "a_to_b"
    reverse_policy: Literal["ignore", "subtract", "separate"] = "ignore"
    max_angle: int = Field(60, ge=10, le=90)
    track_point: Literal["center", "bottom_center"] = "center"
    inference_fps: float = Field(5.0, ge=1, le=10)
    min_track_frames: int = Field(3, ge=1, le=30)
    min_distance: float = Field(0.01, ge=0, le=0.2)
    conf_threshold: float = Field(0.35, ge=0.05, le=0.95)
    uncertain_margin: float = Field(0.2, ge=0, le=1)
    min_winner_score: float = Field(0.5, ge=0, le=1)

    _roi = field_validator("roi_polygon")(classmethod(lambda cls, v: _poly(v, "ROI hududi")))

    @field_validator("line")
    @classmethod
    def _line(cls, v: list[Point] | None) -> list[Point] | None:
        if v is None:
            return None
        if len(v) != 2:
            raise ValueError("Kesib o'tish chizig'i 2 nuqtadan iborat bo'lishi kerak")
        (ax, ay), (bx, by) = v
        for x, y in v:
            if not (0 <= x <= 1 and 0 <= y <= 1):
                raise ValueError("Chiziq kadr ichida bo'lishi kerak")
        if abs(ax - bx) + abs(ay - by) < 0.02:
            raise ValueError("Chiziq juda qisqa")
        return [(round(x, 5), round(y, 5)) for x, y in v]


class EquipmentConfigIO(BaseModel):
    stream: Literal["main", "sub"] = "main"
    roi_polygon: list[Point] | None = None
    control_zone: list[Point] | None = None
    exclude_zones: list[list[Point]] = []
    motion_threshold: float = Field(2.0, ge=0.1, le=100)
    min_on_sec: float = Field(3.0, ge=0, le=600)
    min_off_sec: float = Field(10.0, ge=0, le=3600)
    cycle_mode: Literal["home", "peaks", "off"] = "home"
    returns_per_cycle: int = Field(1, ge=1, le=20)
    home_exit_threshold: float = Field(12.0, ge=0.5, le=100)
    home_return_threshold: float = Field(6.0, ge=0.1, le=100)
    peak_min_height: float = Field(5.0, ge=0.1, le=100)
    peak_min_distance_sec: float = Field(0.5, ge=0.1, le=60)
    reference_cycle_sec: float | None = Field(None, ge=0.1, le=3600)
    auto_reference: bool = True
    micro_stop_factor: float = Field(1.5, ge=1.05, le=10)
    home_reference: str | None = None

    _roi = field_validator("roi_polygon")(classmethod(lambda cls, v: _poly(v, "ROI hududi")))
    _cz = field_validator("control_zone")(classmethod(lambda cls, v: _poly(v, "Nazorat zonasi")))

    @field_validator("exclude_zones")
    @classmethod
    def _ex(cls, v: list[list[Point]]) -> list[list[Point]]:
        return [_poly(z, "Istisno zonasi") or [] for z in v]

    @model_validator(mode="after")
    def _thr(self):
        if self.home_return_threshold >= self.home_exit_threshold:
            raise ValueError("'Qaytdi' chegarasi 'chiqdi' chegarasidan kichik bo'lishi kerak")
        return self
