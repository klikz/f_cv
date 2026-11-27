export type StreamKind = 'main' | 'sub'
export type StreamStatus = 'online' | 'connecting' | 'offline' | 'error'

export type StreamInfo = {
  kind: StreamKind
  codec: string | null
  width: number | null
  height: number | null
  fps: number | null
  status: StreamStatus | string
  last_error: string | null
}

export type OnvifInfo = {
  host: string | null
  port: number | null
  username: string | null
  manufacturer: string | null
  model: string | null
  serial: string | null
  main_profile: string | null
  sub_profile: string | null
}

export type Camera = {
  id: number
  name: string
  enabled: boolean
  position: number
  connection_type: 'rtsp' | 'onvif'
  main_rtsp_url: string
  sub_rtsp_url: string | null
  analysis_stream: StreamKind
  fov_match: boolean
  onvif: OnvifInfo | null
  streams: StreamInfo[]
  created_at: string
  updated_at: string
}

export type ProbeResult = {
  ok: boolean
  codec: string | null
  width: number | null
  height: number | null
  fps: number | null
  error: string | null
}

export type Point = [number, number]

/** WS orqali keladigan har soniyalik holat. */
export type LiveStreamState = {
  status: StreamStatus | string
  error?: string | null
  fps?: number | null
  width?: number | null
  height?: number | null
}

export type CountingLive = {
  total: number
  uncertain: number
  per_product: { product_id: number | null; name: string; count: number }[]
  paused?: boolean
  paused_reason?: string | null
  last_event?: { ts: number; product: string; status: string } | null
}

export type EquipmentLive = {
  state: 'running' | 'stopped' | 'unknown'
  state_since: number | null
  run_seconds: number
  stop_seconds: number
  cycles: number
  last_cycle_sec: number | null
  avg_cycle_sec: number | null
  reference_cycle_sec: number | null
  utilization_pct: number | null
  motion_pct: number | null
  micro_stops: number
}

export type CameraLive = {
  live: {
    ts: number
    tasks: string[]
    enabled: string[]
    counting?: CountingLive
    equipment?: EquipmentLive
  } | null
  streams: { main: LiveStreamState; sub: LiveStreamState }
}

export type FrameHeader = {
  cam: number
  profile: 'grid' | 'main' | 'analysis'
  stream: StreamKind
  seq: number
  ts: number
  w: number
  h: number
  src_w: number
  src_h: number
  meta: FrameMeta
}

export type Detection = {
  bbox: [number, number, number, number] // 0–1, tahlil oqimi kadriga nisbatan
  label: string
  score: number
  track_id?: number
  counted?: boolean
}

export type FrameMeta = {
  space?: StreamKind
  frame_kind?: StreamKind
  counting?: {
    roi: Point[] | null
    line: [Point, Point] | null
    direction: string
    detections: Detection[]
    flash?: boolean
    paused?: boolean
  }
  equipment?: {
    roi: Point[] | null
    control_zone: Point[] | null
    exclude_zones: Point[][]
    state: 'running' | 'stopped' | 'unknown'
    motion: Point[][] // harakat konturlari (0–1)
    motion_pct?: number
  }
}
