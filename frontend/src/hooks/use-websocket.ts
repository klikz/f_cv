import { useEffect, useLayoutEffect, useRef, useState } from 'react'

export type WsStatus = 'connecting' | 'open' | 'closed'

type Options<T> = {
  /** Kelgan xabar (JSON bo'lsa parse qilinadi, binary bo'lsa ArrayBuffer/Blob). */
  onMessage?: (data: T | ArrayBuffer | Blob | string, ev: MessageEvent) => void
  onOpen?: (ws: WebSocket) => void
  /** false bo'lsa ulanmaydi (masalan, sahifa yashirin bo'lsa). */
  enabled?: boolean
  binaryType?: BinaryType
  /** Qayta ulanish kutish vaqti chegaralari (ms). */
  minDelay?: number
  maxDelay?: number
}

function wsUrl(path: string) {
  if (/^wss?:\/\//.test(path)) return path
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const p = path.startsWith('/api') ? path : `/api${path}`
  return `${proto}//${window.location.host}${p}`
}

/**
 * WebSocket hook: uzilsa avtomatik qayta ulanadi (eksponensial kutish, jitter bilan).
 * Callback'lar ref orqali — ular o'zgarsa qayta ulanish bo'lmaydi.
 */
export function useWebSocket<T = unknown>(path: string | null, opts: Options<T> = {}) {
  const { enabled = true, binaryType = 'arraybuffer', minDelay = 500, maxDelay = 10_000 } = opts
  const [status, setStatus] = useState<WsStatus>('closed')
  const wsRef = useRef<WebSocket | null>(null)
  /** Ulanish ochilmagan paytda yuborilgan oxirgi xabar — ochilganda yuboriladi. */
  const pendingRef = useRef<string | ArrayBuffer | Blob | null>(null)
  const handlers = useRef(opts)
  useLayoutEffect(() => {
    handlers.current = opts
  })

  useEffect(() => {
    if (!path || !enabled) return
    let stopped = false
    let attempt = 0
    let timer: ReturnType<typeof setTimeout> | undefined

    const connect = () => {
      if (stopped) return
      setStatus('connecting')
      const ws = new WebSocket(wsUrl(path))
      ws.binaryType = binaryType
      wsRef.current = ws

      ws.onopen = () => {
        attempt = 0
        setStatus('open')
        if (pendingRef.current !== null) ws.send(pendingRef.current)
        handlers.current.onOpen?.(ws)
      }
      ws.onmessage = (ev) => {
        let data: unknown = ev.data
        if (typeof ev.data === 'string') {
          try {
            data = JSON.parse(ev.data)
          } catch {
            /* matn sifatida qoladi */
          }
        }
        handlers.current.onMessage?.(data as T, ev)
      }
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null
        if (stopped) return
        setStatus('closed')
        const delay = Math.min(maxDelay, minDelay * 2 ** attempt) * (0.75 + Math.random() * 0.5)
        attempt += 1
        timer = setTimeout(connect, delay)
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(timer)
      wsRef.current?.close()
      wsRef.current = null
      setStatus('closed')
    }
  }, [path, enabled, binaryType, minDelay, maxDelay])

  /** Yuborish; ulanish yopiq bo'lsa — oxirgi xabar saqlanib, ochilganda (va qayta ulanganda) yuboriladi. */
  const send = (data: unknown, opts2: { remember?: boolean } = { remember: true }) => {
    const payload = typeof data === 'string' || data instanceof ArrayBuffer || data instanceof Blob ? data : JSON.stringify(data)
    if (opts2.remember) pendingRef.current = payload
    const ws = wsRef.current
    if (ws?.readyState !== WebSocket.OPEN) return false
    ws.send(payload)
    return true
  }

  return { status, send }
}
