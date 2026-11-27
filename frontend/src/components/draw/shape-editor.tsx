import type Konva from 'konva'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Circle, Group, Image as KImage, Layer, Line, Shape as KShape, Stage, Text } from 'react-konva'
import type { FeedHub } from '@/components/video/feed'
import { containRect, drawOverlay, overlayPalette, type Rect } from '@/components/video/overlay'
import type { FrameMeta, Point } from '@/lib/types'

export type ShapeKind = 'polygon' | 'line'
export type ShapeDef = { kind: ShapeKind; color: string; label: string; dash?: number[]; fillAlpha?: number }
export type ShapeMap = Record<string, Point[] | null>

type Props = {
  hub: FeedHub
  cameraId: number
  defs: Record<string, ShapeDef>
  shapes: ShapeMap
  /** commit=false — sudrash davomida (tarixga yozilmaydi) */
  onChange: (next: ShapeMap, commit: boolean) => void
  /** Chizilayotgan shakl kaliti (masalan 'roi'), null — faqat tahrirlash */
  tool: string | null
  onToolDone: () => void
  /** Chiziq strelkasi yo'nalishi */
  direction?: string
  /** Jonli test: aniqlashlar va harakat sohalari (geometriyasiz) */
  showLive?: boolean
  className?: string
}

const SNAP_PX = 10
const clamp01 = (v: number) => Math.min(1, Math.max(0, v))

function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

function stripGeometry(meta: FrameMeta | undefined): FrameMeta | undefined {
  if (!meta) return meta
  return {
    ...meta,
    counting: meta.counting ? { ...meta.counting, roi: null, line: null } : undefined,
    equipment: meta.equipment ? { ...meta.equipment, roi: null, control_zone: null, exclude_zones: [] } : undefined,
  }
}

/**
 * Video kadri ustida shakllarni chizish va tahrirlash.
 * Koordinatalar kadrga nisbatan 0–1 (tahlil oqimi kadri).
 *
 * Sichqoncha: bosish — nuqta qo'shish; birinchi nuqtani bosish yoki Enter — poligonni yopish;
 * nuqtani sudrash; shaklni ichidan sudrash — surish; qirraga ikki marta bosish — nuqta qo'shish;
 * g'ildirak — zoom; Space + sudrash — surish (pan); 0 — zoomni tiklash.
 * Klaviatura: Esc — chizishni bekor qilish, Delete — tanlangan nuqtani o'chirish.
 */
export function ShapeEditor({ hub, cameraId, defs, shapes, onChange, tool, onToolDone, direction = 'a_to_b', showLive = true, className }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<Konva.Stage>(null)
  const imgRef = useRef<Konva.Image>(null)
  const liveRef = useRef<Konva.Shape>(null)
  const metaRef = useRef<FrameMeta | undefined>(undefined)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null)
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 })
  const [space, setSpace] = useState(false)
  const [selected, setSelected] = useState<{ key: string; idx: number } | null>(null)
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null)
  const drawingStart = useRef<Point[] | null>(null)

  // konteyner o'lchami
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // kadrlar
  useEffect(() => {
    return hub.subscribe(cameraId, (f) => {
      metaRef.current = f.header.meta
      const node = imgRef.current
      if (node) {
        node.image(f.bitmap as unknown as HTMLImageElement)
        node.getLayer()?.batchDraw()
      }
      liveRef.current?.getLayer()?.batchDraw()
      setImgSize((s) => (s && s.w === f.header.src_w && s.h === f.header.src_h ? s : { w: f.header.src_w, h: f.header.src_h }))
    })
  }, [hub, cameraId])

  const rect: Rect = useMemo(() => {
    if (!imgSize || !size.w) return { x: 0, y: 0, w: size.w, h: size.h }
    return containRect(size.w, size.h, imgSize.w, imgSize.h)
  }, [imgSize, size])

  const toPx = useCallback((p: Point) => ({ x: rect.x + p[0] * rect.w, y: rect.y + p[1] * rect.h }), [rect])
  const toNorm = useCallback((x: number, y: number): Point => [clamp01((x - rect.x) / rect.w), clamp01((y - rect.y) / rect.h)], [rect])

  /** Sahna (zoom/pan hisobga olingan) koordinatasida ko'rsatkich. */
  const pointer = () => {
    const st = stageRef.current
    const p = st?.getPointerPosition()
    if (!st || !p) return null
    return { x: (p.x - st.x()) / st.scaleX(), y: (p.y - st.y()) / st.scaleY() }
  }

  const snap = (key: string, idx: number, px: { x: number; y: number }) => {
    const r = SNAP_PX / view.scale
    for (const [k, pts] of Object.entries(shapes)) {
      if (!pts) continue
      for (let i = 0; i < pts.length; i++) {
        if (k === key && i === idx) continue
        const q = toPx(pts[i])
        if (dist(q, px) < r) return q
      }
    }
    return px
  }

  // chizish rejimi boshlanganda — eski shaklni saqlab qo'yish (Esc qaytaradi)
  useEffect(() => {
    if (tool) {
      drawingStart.current = shapes[tool] ?? null
      onChange({ ...shapes, [tool]: [] }, false)
      setSelected(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tool])

  const finishPolygon = useCallback(() => {
    if (!tool) return
    const pts = shapes[tool] ?? []
    if (defs[tool]?.kind === 'polygon' && pts.length >= 3) {
      onChange({ ...shapes }, true)
      onToolDone()
    }
  }, [tool, shapes, defs, onChange, onToolDone])

  const cancelDrawing = useCallback(() => {
    if (!tool) return
    onChange({ ...shapes, [tool]: drawingStart.current }, false)
    onToolDone()
  }, [tool, shapes, onChange, onToolDone])

  // klaviatura
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const tgt = e.target as HTMLElement
      if (tgt && ['INPUT', 'TEXTAREA', 'SELECT'].includes(tgt.tagName)) return
      if (e.code === 'Space') {
        setSpace(true)
        e.preventDefault()
      } else if (e.key === 'Escape' && tool) {
        e.preventDefault()
        cancelDrawing()
      } else if (e.key === 'Enter' && tool) {
        e.preventDefault() // fokusdagi tugma "bosilib" ketmasin
        ;(document.activeElement as HTMLElement | null)?.blur?.()
        finishPolygon()
      } else if ((e.key === 'Delete' || e.key === 'Backspace') && selected) {
        const pts = shapes[selected.key]
        if (!pts) return
        const def = defs[selected.key]
        if (def.kind === 'polygon' && pts.length > 3) {
          onChange({ ...shapes, [selected.key]: pts.filter((_, i) => i !== selected.idx) }, true)
        }
        setSelected(null)
        e.preventDefault()
      } else if (e.key === '0' && !e.ctrlKey) {
        setView({ scale: 1, x: 0, y: 0 })
      }
    }
    const up = (e: KeyboardEvent) => e.code === 'Space' && setSpace(false)
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
  }, [tool, selected, shapes, defs, onChange, cancelDrawing, finishPolygon])

  const onStageClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (space || e.evt.button !== 0) return
    if (!tool) {
      if (e.target === e.target.getStage() || e.target === imgRef.current) setSelected(null)
      return
    }
    const p = pointer()
    if (!p) return
    const def = defs[tool]
    const pts = shapes[tool] ?? []
    if (def.kind === 'polygon') {
      if (pts.length >= 3 && dist(toPx(pts[0]), p) < SNAP_PX / view.scale) {
        finishPolygon()
        return
      }
      const sp = snap(tool, -1, p)
      onChange({ ...shapes, [tool]: [...pts, toNorm(sp.x, sp.y)] }, false)
    } else {
      const sp = snap(tool, -1, p)
      const next = [...pts, toNorm(sp.x, sp.y)]
      if (next.length >= 2) {
        onChange({ ...shapes, [tool]: next.slice(0, 2) }, true)
        onToolDone()
      } else onChange({ ...shapes, [tool]: next }, false)
    }
  }

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault()
    const st = stageRef.current
    const p = st?.getPointerPosition()
    if (!st || !p) return
    const old = view.scale
    const scale = Math.min(6, Math.max(1, old * (e.evt.deltaY < 0 ? 1.15 : 1 / 1.15)))
    const mx = (p.x - view.x) / old
    const my = (p.y - view.y) / old
    setView(scale === 1 ? { scale: 1, x: 0, y: 0 } : { scale, x: p.x - mx * scale, y: p.y - my * scale })
  }

  const insertPoint = (key: string) => {
    const pts = shapes[key]
    const p = pointer()
    if (!pts || !p || defs[key].kind !== 'polygon') return
    let best = 0
    let bestD = Infinity
    for (let i = 0; i < pts.length; i++) {
      const a = toPx(pts[i])
      const b = toPx(pts[(i + 1) % pts.length])
      // nuqtadan kesmagacha masofa
      const vx = b.x - a.x
      const vy = b.y - a.y
      const t = Math.max(0, Math.min(1, ((p.x - a.x) * vx + (p.y - a.y) * vy) / (vx * vx + vy * vy || 1)))
      const d = dist(p, { x: a.x + t * vx, y: a.y + t * vy })
      if (d < bestD) {
        bestD = d
        best = i
      }
    }
    const next = [...pts]
    next.splice(best + 1, 0, toNorm(p.x, p.y))
    onChange({ ...shapes, [key]: next }, true)
  }

  if (import.meta.env.DEV) (window as unknown as { __editor: unknown }).__editor = { shapes, tool }
  const pal = overlayPalette()
  const sw = 2 / view.scale
  const r = 5 / view.scale

  return (
    <div ref={wrapRef} className={className} style={{ cursor: space ? 'grab' : tool ? 'crosshair' : 'default' }}>
      {size.w > 0 && (
        <Stage
          ref={stageRef}
          width={size.w}
          height={size.h}
          scaleX={view.scale}
          scaleY={view.scale}
          x={view.x}
          y={view.y}
          draggable={space}
          onDragEnd={(e) => e.target === stageRef.current && setView((v) => ({ ...v, x: e.target.x(), y: e.target.y() }))}
          onClick={onStageClick}
          onWheel={onWheel}
          onMouseMove={() => tool && setHover(pointer())}
          onMouseLeave={() => setHover(null)}
        >
          <Layer listening>
            <KImage ref={imgRef} image={undefined} x={rect.x} y={rect.y} width={rect.w} height={rect.h} />
            {showLive && (
              <KShape
                ref={liveRef}
                listening={false}
                sceneFunc={(ctx) => {
                  drawOverlay(ctx._context as CanvasRenderingContext2D, rect, stripGeometry(metaRef.current))
                }}
              />
            )}
          </Layer>
          <Layer>
            {Object.entries(defs).map(([key, def]) => {
              const pts = shapes[key]
              if (!pts || pts.length === 0) return null
              const px = pts.flatMap((p) => {
                const q = toPx(p)
                return [q.x, q.y]
              })
              const drawing = tool === key
              const closed = def.kind === 'polygon' && !drawing
              const preview = drawing && hover ? [...px, hover.x, hover.y] : px
              return (
                <Group key={key}>
                  <Line
                    points={preview}
                    closed={closed}
                    stroke={def.color}
                    strokeWidth={def.kind === 'line' ? sw * 1.6 : sw}
                    dash={def.dash?.map((d) => d / view.scale)}
                    fill={closed ? def.color : undefined}
                    opacity={1}
                    fillEnabled={closed}
                    {...(closed ? { fill: def.color, opacity: 1 } : {})}
                    globalCompositeOperation="source-over"
                    hitStrokeWidth={12 / view.scale}
                    draggable={!tool && !space && closed}
                    onDblClick={() => insertPoint(key)}
                    onDragEnd={(e) => {
                      const dx = e.target.x() / rect.w
                      const dy = e.target.y() / rect.h
                      e.target.position({ x: 0, y: 0 })
                      const moved = pts.map(([x, y]) => [clamp01(x + dx), clamp01(y + dy)] as Point)
                      onChange({ ...shapes, [key]: moved }, true)
                    }}
                    shadowForStrokeEnabled={false}
                    perfectDrawEnabled={false}
                    {...(closed ? { fill: hexAlpha(def.color, def.fillAlpha ?? 0.12) } : {})}
                  />
                  {def.kind === 'line' && pts.length === 2 && <Arrow pts={pts} toPx={toPx} direction={direction} color={def.color} scale={view.scale} />}
                  {(def.kind === 'line' ? pts : pts).map((p, i) => {
                    const q = toPx(p)
                    const isSel = selected?.key === key && selected.idx === i
                    const first = drawing && i === 0 && pts.length >= 3
                    return (
                      <Group key={i}>
                        <Circle
                          x={q.x}
                          y={q.y}
                          radius={first ? r * 1.6 : isSel ? r * 1.4 : r}
                          fill={isSel ? pal.warning : def.color}
                          stroke="#000"
                          strokeWidth={1 / view.scale}
                          draggable={!space}
                          onMouseDown={(e) => {
                            e.cancelBubble = true
                            setSelected({ key, idx: i })
                          }}
                          onClick={(e) => {
                            if (first) {
                              e.cancelBubble = true
                              finishPolygon()
                            }
                          }}
                          onDragMove={(e) => {
                            const sp = snap(key, i, { x: e.target.x(), y: e.target.y() })
                            e.target.position(sp)
                            const next = [...pts]
                            next[i] = toNorm(sp.x, sp.y)
                            onChange({ ...shapes, [key]: next }, false)
                          }}
                          onDragEnd={() => onChange({ ...shapes }, true)}
                          onContextMenu={(e) => {
                            e.evt.preventDefault()
                            if (def.kind === 'polygon' && pts.length > 3) onChange({ ...shapes, [key]: pts.filter((_, j) => j !== i) }, true)
                          }}
                        />
                        {def.kind === 'line' && (
                          <Text x={q.x + 8 / view.scale} y={q.y - 18 / view.scale} text={i === 0 ? 'A' : 'B'} fontSize={13 / view.scale} fontStyle="bold" fill={def.color} listening={false} />
                        )}
                      </Group>
                    )
                  })}
                  {pts.length > 0 && !drawing && def.kind === 'polygon' && (
                    <Text x={toPx(pts[0]).x + 6 / view.scale} y={toPx(pts[0]).y + 6 / view.scale} text={def.label} fontSize={12 / view.scale} fill={def.color} listening={false} />
                  )}
                </Group>
              )
            })}
          </Layer>
        </Stage>
      )}
    </div>
  )
}

function hexAlpha(color: string, a: number) {
  // oklch(...) yoki boshqa CSS rang — color-mix bilan shaffoflik
  return `color-mix(in oklch, ${color} ${Math.round(a * 100)}%, transparent)`
}

function Arrow({ pts, toPx, direction, color, scale }: { pts: Point[]; toPx: (p: Point) => { x: number; y: number }; direction: string; color: string; scale: number }) {
  const a = toPx(pts[0])
  const b = toPx(pts[1])
  const mx = (a.x + b.x) / 2
  const my = (a.y + b.y) / 2
  const dx = b.x - a.x
  const dy = b.y - a.y
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len
  const ny = dx / len
  const L = Math.max(24, Math.min(70, len * 0.2)) / Math.max(1, scale * 0.7)
  const signs = direction === 'b_to_a' ? [-1] : direction === 'both' ? [1, -1] : [1]
  const hs = 9 / scale
  return (
    <>
      {signs.map((s) => {
        const tx = mx + nx * L * s
        const ty = my + ny * L * s
        const ang = Math.atan2(ty - my, tx - mx)
        return (
          <Group key={s} listening={false}>
            <Line points={[mx, my, tx, ty]} stroke={color} strokeWidth={2.5 / scale} />
            <Line
              points={[tx, ty, tx - hs * Math.cos(ang - 0.45), ty - hs * Math.sin(ang - 0.45), tx - hs * Math.cos(ang + 0.45), ty - hs * Math.sin(ang + 0.45)]}
              closed
              fill={color}
            />
          </Group>
        )
      })}
    </>
  )
}

/** Shakllar tarixi: undo/redo. */
export function useShapeHistory(initial: ShapeMap) {
  const [state, setState] = useState(initial)
  const past = useRef<ShapeMap[]>([])
  const future = useRef<ShapeMap[]>([])
  const committed = useRef(initial)
  const [, force] = useState(0)

  const reset = useCallback((s: ShapeMap) => {
    past.current = []
    future.current = []
    committed.current = s
    setState(s)
    force((n) => n + 1)
  }, [])

  const change = useCallback((next: ShapeMap, commit: boolean) => {
    setState(next)
    if (commit) {
      past.current.push(committed.current)
      if (past.current.length > 100) past.current.shift()
      future.current = []
      committed.current = next
      force((n) => n + 1)
    }
  }, [])

  const undo = useCallback(() => {
    const prev = past.current.pop()
    if (!prev) return
    future.current.push(committed.current)
    committed.current = prev
    setState(prev)
    force((n) => n + 1)
  }, [])

  const redo = useCallback(() => {
    const next = future.current.pop()
    if (!next) return
    past.current.push(committed.current)
    committed.current = next
    setState(next)
    force((n) => n + 1)
  }, [])

  return { shapes: state, change, undo, redo, reset, canUndo: past.current.length > 0, canRedo: future.current.length > 0 }
}
