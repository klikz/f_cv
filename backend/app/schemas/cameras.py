from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

StreamKind = Literal["main", "sub"]


def _check_url(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    if not v.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        raise ValueError("Manzil rtsp:// bilan boshlanishi kerak")
    return v


class StreamInfo(BaseModel):
    kind: StreamKind
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    status: str = "offline"
    last_error: str | None = None


class OnvifInfo(BaseModel):
    host: str | None = None
    port: int | None = None
    username: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    main_profile: str | None = None
    sub_profile: str | None = None


class CameraOut(BaseModel):
    id: int
    name: str
    enabled: bool
    position: int
    connection_type: str
    main_rtsp_url: str  # parol yashirilgan
    sub_rtsp_url: str | None
    analysis_stream: StreamKind
    fov_match: bool
    onvif: OnvifInfo | None
    streams: list[StreamInfo]
    created_at: datetime
    updated_at: datetime


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    main_rtsp_url: str
    sub_rtsp_url: str | None = None
    fov_match: bool = False

    _v_main = field_validator("main_rtsp_url")(classmethod(lambda cls, v: _check_url(v)))
    _v_sub = field_validator("sub_rtsp_url")(classmethod(lambda cls, v: _check_url(v)))


class CameraCreate(CameraBase):
    connection_type: Literal["rtsp", "onvif"] = "rtsp"
    onvif_host: str | None = None
    onvif_port: int | None = None
    onvif_username: str | None = None
    onvif_password: str | None = None
    onvif_manufacturer: str | None = None
    onvif_model: str | None = None
    onvif_serial: str | None = None
    onvif_main_profile: str | None = None
    onvif_sub_profile: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None
    main_rtsp_url: str | None = None
    sub_rtsp_url: str | None = None
    fov_match: bool | None = None
    clear_sub: bool = False
    onvif_host: str | None = None
    onvif_port: int | None = None
    onvif_username: str | None = None
    onvif_password: str | None = None
    onvif_main_profile: str | None = None
    onvif_sub_profile: str | None = None

    _v_main = field_validator("main_rtsp_url")(classmethod(lambda cls, v: _check_url(v)))
    _v_sub = field_validator("sub_rtsp_url")(classmethod(lambda cls, v: _check_url(v)))


class ReorderIn(BaseModel):
    ids: list[int]


class ProbeIn(BaseModel):
    url: str | None = None
    camera_id: int | None = None
    kind: StreamKind | None = None


class ProbeOut(BaseModel):
    ok: bool
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    error: str | None = None


class PreviewIn(BaseModel):
    main_url: str | None = None
    sub_url: str | None = None
    camera_id: int | None = None


class PreviewOut(BaseModel):
    main: str | None = None  # data:image/jpeg;base64,...
    sub: str | None = None
    main_error: str | None = None
    sub_error: str | None = None
