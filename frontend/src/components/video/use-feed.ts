import { useEffect, useMemo, useState } from 'react'
import { useWebSocket } from '@/hooks/use-websocket'
import type { CameraLive } from '@/lib/types'
import { FeedHub } from './feed'

type StateMsg = { type: 'state'; data: Record<string, CameraLive> }
type JsonMsg = StateMsg | { type: 'stream_status' | 'event'; data: Record<string, unknown> }

function useHubSocket(path: string | null, onOpen?: (ws: WebSocket) => void, onEvent?: (m: JsonMsg) => void) {
  const hub = useMemo(() => new FeedHub(), [])
  const [states, setStates] = useState<Record<number, CameraLive>>({})
  useEffect(() => () => hub.clear(), [hub])
  const { status, send } = useWebSocket<JsonMsg>(path, {
    onOpen,
    onMessage: (data) => {
      if (data instanceof ArrayBuffer) {
        hub.push(data)
        return
      }
      if (typeof data === 'object' && data && 'type' in data) {
        const m = data as JsonMsg
        if (m.type === 'state') {
          const next: Record<number, CameraLive> = {}
          for (const [k, v] of Object.entries(m.data)) next[Number(k)] = v
          setStates((prev) => ({ ...prev, ...next }))
        } else onEvent?.(m)
      }
    },
  })
  return { hub, states, status, send }
}

/** Grid: bitta WS, ko'rinib turgan kameralar ro'yxati va AI Vision holati yuboriladi. */
export function useGridFeed(cameraIds: number[], ai: boolean, onEvent?: (m: JsonMsg) => void) {
  const { hub, states, status, send } = useHubSocket('/ws/grid', undefined, onEvent)
  const key = cameraIds.join(',')
  useEffect(() => {
    send({ cameras: cameraIds, ai })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, ai])
  return { hub, states, status }
}

/** Kamera sahifasi (main) yoki sozlash sahifalari (tahlil oqimi). */
export function useCameraFeed(cameraId: number, profile: 'main' | 'analysis', onEvent?: (m: JsonMsg) => void) {
  return useHubSocket(Number.isFinite(cameraId) ? `/ws/camera/${cameraId}?profile=${profile}` : null, undefined, onEvent)
}
