import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import type { FrameHeader } from '@/lib/types'
import type { FeedHub, FrameData } from './feed'
import { containRect, drawOverlay, type Rect } from './overlay'

type Props = {
  hub: FeedHub
  cameraId: number
  showAi?: boolean
  className?: string
  children?: ReactNode
  /** Kadr chizilgandan keyin qo'shimcha chizish (masalan, sozlash sahifasida). */
  onRect?: (r: Rect, header: FrameHeader | null) => void
  /** Kadr kelmay qolganini bildirish (ms). */
  staleMs?: number
  onStale?: (stale: boolean) => void
}

/** Video katagi: JPEG kadr + AI qatlami canvas'da (kadr va metadata doim mos). */
export function VideoCanvas({ hub, cameraId, showAi = false, className, children, onRect, staleMs = 6000, onStale }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const frameRef = useRef<FrameData | null>(null)
  const sizeRef = useRef({ w: 0, h: 0, dpr: 1 })
  const rafRef = useRef(0)
  const [hasFrame, setHasFrame] = useState(false)
  const opts = useRef({ showAi, onRect })
  opts.current = { showAi, onRect }

  const draw = () => {
    rafRef.current = 0
    const cv = canvasRef.current
    const f = frameRef.current
    if (!cv) return
    const { w, h, dpr } = sizeRef.current
    const ctx = cv.getContext('2d')
    if (!ctx || !w || !h) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    if (!f) return
    const r = containRect(w, h, f.bitmap.width, f.bitmap.height)
    ctx.imageSmoothingQuality = 'medium'
    ctx.drawImage(f.bitmap, r.x, r.y, r.w, r.h)
    if (opts.current.showAi) drawOverlay(ctx, r, f.header.meta)
    opts.current.onRect?.(r, f.header)
    // yonib-o'chish animatsiyasi uchun qayta chizish
    if (opts.current.showAi && f.header.meta?.counting?.flash) schedule()
  }
  const schedule = () => {
    if (!rafRef.current) rafRef.current = requestAnimationFrame(draw)
  }

  useEffect(() => {
    const wrap = wrapRef.current
    const cv = canvasRef.current
    if (!wrap || !cv) return
    const ro = new ResizeObserver(() => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = wrap.clientWidth
      const h = wrap.clientHeight
      sizeRef.current = { w, h, dpr }
      cv.width = Math.round(w * dpr)
      cv.height = Math.round(h * dpr)
      cv.style.width = `${w}px`
      cv.style.height = `${h}px`
      schedule()
    })
    ro.observe(wrap)
    return () => ro.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    frameRef.current = hub.getLatest(cameraId) ?? null
    setHasFrame(!!frameRef.current)
    const unsub = hub.subscribe(cameraId, (f) => {
      frameRef.current = f
      setHasFrame(true)
      schedule()
    })
    return () => {
      unsub()
      cancelAnimationFrame(rafRef.current)
      rafRef.current = 0
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hub, cameraId])

  useEffect(() => schedule(), [showAi]) // eslint-disable-line react-hooks/exhaustive-deps

  // kadr kelmay qolsa (aloqa yo'q)
  useEffect(() => {
    if (!onStale) return
    const id = setInterval(() => {
      const f = frameRef.current
      onStale(!f || performance.now() - f.receivedAt > staleMs)
    }, 1000)
    return () => clearInterval(id)
  }, [onStale, staleMs])

  return (
    <div ref={wrapRef} className={cn('relative h-full w-full overflow-hidden bg-video-bg', className)} data-has-frame={hasFrame}>
      <canvas ref={canvasRef} className="absolute inset-0 block" />
      {children}
    </div>
  )
}
